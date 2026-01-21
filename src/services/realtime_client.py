"""Azure OpenAI Realtime API client for voice conversations.

Handles WebSocket connections, audio streaming, and real-time events.
"""

import asyncio
import base64
import json
import logging
from typing import Optional, AsyncIterator, Dict, Any
import websockets
from websockets.client import WebSocketClientProtocol

from src.config import get_settings

logger = logging.getLogger(__name__)


class RealtimeClient:
    """Client for Azure OpenAI Realtime API (gpt-realtime-mini)."""
    
    def __init__(self):
        """Initialize the Realtime API client."""
        settings = get_settings()
        
        if not settings.azure_realtime_endpoint or not settings.azure_realtime_key:
            self.enabled = False
            logger.warning("Azure Realtime API not configured")
        else:
            self.endpoint = settings.azure_realtime_endpoint
            self.api_key = settings.azure_realtime_key
            self.deployment = settings.azure_realtime_deployment
            self.api_version = settings.azure_realtime_api_version
            self.enabled = True
            
        # Active sessions
        self.sessions: Dict[str, WebSocketClientProtocol] = {}
    
    def _get_websocket_url(self) -> str:
        """Construct WebSocket URL for Azure Realtime API."""
        # Clean the endpoint
        base_url = self.endpoint
        
        # Remove any query params
        if '?' in base_url:
            base_url = base_url.split('?')[0]
        
        # Remove any trailing slashes or paths
        base_url = base_url.rstrip('/')
        
        # Remove common path suffixes if accidentally included
        suffixes_to_remove = ['/openai/realtime', '/openai', '/realtime']
        for suffix in suffixes_to_remove:
            if base_url.endswith(suffix):
                base_url = base_url[:-len(suffix)]
        
        # Convert protocol
        if base_url.startswith("https://"):
            base_url = base_url.replace("https://", "wss://")
        elif base_url.startswith("http://"):
            base_url = base_url.replace("http://", "ws://")
        
        # Construct final URL
        ws_url = f"{base_url}/openai/realtime?api-version={self.api_version}&deployment={self.deployment}"
        logger.info(f"Constructed WebSocket URL: {ws_url}")
        return ws_url
    
    async def create_session(
        self,
        session_id: str,
        instructions: str,
        voice: str = "alloy",
        temperature: float = 0.7
    ) -> bool:
        """
        Create a new realtime session with WebSocket connection.
        
        Args:
            session_id: Unique session identifier
            instructions: System instructions for the AI
            voice: Voice to use for TTS (alloy, echo, shimmer, etc.)
            temperature: Sampling temperature
            
        Returns:
            True if session created successfully
        """
        if not self.enabled:
            logger.error("Realtime API not configured")
            return False
        
        try:
            # Create WebSocket connection
            url = self._get_websocket_url()
            logger.info(f"Connecting to Azure Realtime API: {url}")
            
            headers = {
                "api-key": self.api_key
            }
            
            ws = await websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            
            # Configure session
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": instructions,
                    "voice": voice,
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    },
                    "temperature": temperature
                }
            }
            
            await ws.send(json.dumps(session_config))
            
            # Store session
            self.sessions[session_id] = ws
            
            logger.info(f"Created realtime session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create realtime session: {e}")
            return False
    
    async def send_audio_chunk(self, session_id: str, audio_base64: str):
        """
        Send audio chunk to the realtime session.
        
        Args:
            session_id: Session identifier
            audio_base64: Base64-encoded audio data
        """
        if session_id not in self.sessions:
            logger.error(f"Session {session_id} not found")
            return
        
        ws = self.sessions[session_id]
        
        try:
            message = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }
            await ws.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
    
    async def commit_audio(self, session_id: str):
        """
        Commit audio buffer and trigger response generation.
        
        Args:
            session_id: Session identifier
        """
        if session_id not in self.sessions:
            return
        
        ws = self.sessions[session_id]
        
        try:
            message = {"type": "input_audio_buffer.commit"}
            await ws.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to commit audio: {e}")
    
    async def create_response(self, session_id: str):
        """
        Request response generation.
        
        Args:
            session_id: Session identifier
        """
        if session_id not in self.sessions:
            return
        
        ws = self.sessions[session_id]
        
        try:
            message = {"type": "response.create"}
            await ws.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to create response: {e}")
    
    async def listen(self, session_id: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Listen for events from the realtime session.
        
        Args:
            session_id: Session identifier
            
        Yields:
            Event dictionaries from the realtime API
        """
        if session_id not in self.sessions:
            logger.error(f"Session {session_id} not found")
            return
        
        ws = self.sessions[session_id]
        
        try:
            async for message in ws:
                try:
                    event = json.loads(message)
                    yield event
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from realtime API: {message}")
                    continue
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Realtime session {session_id} closed")
        except Exception as e:
            logger.error(f"Error listening to session: {e}")
    
    async def close_session(self, session_id: str):
        """
        Close a realtime session.
        
        Args:
            session_id: Session identifier
        """
        if session_id not in self.sessions:
            return
        
        ws = self.sessions[session_id]
        
        try:
            await ws.close()
            del self.sessions[session_id]
            logger.info(f"Closed realtime session: {session_id}")
        except Exception as e:
            logger.error(f"Error closing session: {e}")
    
    async def cleanup(self):
        """Close all active sessions."""
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self.close_session(session_id)


# Singleton
_realtime_client: Optional[RealtimeClient] = None

def get_realtime_client() -> RealtimeClient:
    """Get the singleton realtime client."""
    global _realtime_client
    if _realtime_client is None:
        _realtime_client = RealtimeClient()
    return _realtime_client
