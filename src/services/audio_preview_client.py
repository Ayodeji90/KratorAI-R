"""Azure OpenAI GPT-4o Audio Preview client for voice conversations.

Uses REST API (/chat/completions) with audio modalities.
"""

import base64
import httpx
import logging
from typing import Optional, Dict, Any

from src.config import get_settings

logger = logging.getLogger(__name__)


class AudioPreviewClient:
    """Client for Azure OpenAI GPT-4o Audio Preview model."""
    
    def __init__(self):
        """Initialize the Audio Preview client."""
        settings = get_settings()
        
        # Use dedicated audio preview credentials
        self.endpoint = settings.azure_audio_endpoint
        self.api_key = settings.azure_audio_key
        self.deployment = settings.azure_audio_deployment
        self.api_version = settings.azure_audio_api_version
        
        if not self.endpoint or not self.api_key:
            self.enabled = False
            logger.warning("Azure Audio Preview API not configured")
        else:
            self.enabled = True
            logger.info(f"Audio Preview client initialized: {self.deployment}")
        
        # Conversation history per session
        self.sessions: Dict[str, list] = {}
    
    def _get_api_url(self) -> str:
        """Construct API URL for chat completions."""
        base_url = self.endpoint.rstrip('/')
        return f"{base_url}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
    
    async def create_session(self, session_id: str, system_prompt: str) -> bool:
        """Create a new conversation session."""
        if not self.enabled:
            logger.error("Audio Preview API not configured")
            return False
        
        self.sessions[session_id] = [{
            "role": "system",
            "content": system_prompt
        }]
        logger.info(f"Created audio session: {session_id}")
        return True
    
    async def process_audio_turn(
        self,
        session_id: str,
        audio_base64: str,
        audio_format: str = "wav"
    ) -> Dict[str, Any]:
        """
        Process an audio turn and get AI response with audio.
        
        Args:
            session_id: Session identifier
            audio_base64: Base64-encoded audio data
            audio_format: Audio format (wav, mp3, etc.)
            
        Returns:
            Dict with transcript, response_text, response_audio, and any errors
        """
        if not self.enabled:
            return {"error": "Audio Preview API not configured"}
        
        if session_id not in self.sessions:
            return {"error": f"Session {session_id} not found"}
        
        try:
            # Add user audio message to history
            self.sessions[session_id].append({
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_base64,
                            "format": audio_format
                        }
                    }
                ]
            })
            
            # Prepare request
            url = self._get_api_url()
            headers = {
                "api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "messages": self.sessions[session_id],
                "modalities": ["text", "audio"],
                "audio": {
                    "voice": "alloy",
                    "format": "wav"
                },
                "max_completion_tokens": 2000,
                "temperature": 0.7
            }
            
            logger.info(f"Sending audio request to {url}")
            
            # Make API call
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"Audio API error {response.status_code}: {error_text}")
                    return {"error": f"API error: {response.status_code}"}
                
                data = response.json()
            
            # Extract response
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            
            # Get text transcript and audio
            response_text = ""
            response_audio = ""
            
            # Parse audio response
            audio_data = message.get("audio", {})
            if audio_data:
                response_text = audio_data.get("transcript", "")
                response_audio = audio_data.get("data", "")
            
            # Also check content for text
            content = message.get("content", "")
            if content and not response_text:
                response_text = content
            
            # Add assistant response to history (text only for future turns)
            self.sessions[session_id].append({
                "role": "assistant",
                "content": response_text
            })
            
            # Check if conversation should complete
            conversation_complete = False
            lower_text = response_text.lower()
            if "should i proceed" in lower_text or "shall i proceed" in lower_text or "ready to generate" in lower_text:
                conversation_complete = True
            
            logger.info(f"Audio response: {response_text[:100]}...")
            
            return {
                "response_text": response_text,
                "response_audio": response_audio,
                "conversation_complete": conversation_complete,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error processing audio turn: {e}")
            return {"error": str(e)}
    
    def get_final_prompt(self, session_id: str) -> Optional[str]:
        """Extract the final design prompt from conversation."""
        if session_id not in self.sessions:
            return None
        
        # Combine all user and assistant messages into a summary
        conversation_text = []
        for msg in self.sessions[session_id]:
            if msg.get("role") in ["user", "assistant"]:
                content = msg.get("content", "")
                if isinstance(content, str) and content:
                    conversation_text.append(content)
        
        # Return last assistant message as the prompt
        for msg in reversed(self.sessions[session_id]):
            if msg.get("role") == "assistant":
                return msg.get("content", "")
        
        return None
    
    def close_session(self, session_id: str):
        """Close a conversation session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Closed audio session: {session_id}")


# Singleton
_audio_client: Optional[AudioPreviewClient] = None

def get_audio_client() -> AudioPreviewClient:
    """Get the singleton audio client."""
    global _audio_client
    if _audio_client is None:
        _audio_client = AudioPreviewClient()
    return _audio_client
