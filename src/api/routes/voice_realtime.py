"""
Voice Conversation Routes - Real-time Audio with GPT-4o Realtime API

WebSocket-based voice interface using Azure OpenAI Realtime API.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from typing import Optional
import json
import uuid
import asyncio
import logging

from src.services.realtime_client import get_realtime_client
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Realtime instructions for design conversation
REALTIME_INSTRUCTIONS = """You are a helpful AI design consultant for KratorAI, assisting African creatives with their graphic design needs through natural voice conversation.

Your role is to:
1. Engage in friendly, natural conversation to understand what changes the user wants to make to their design
2. Ask clarifying questions ONE at a time to gather complete information
3. Extract design details (style, colors, content, branding, mood, etc.)
4. Recognize when you have enough information to proceed

CONVERSATIONAL GUIDELINES:
- Be warm, friendly, and encouraging
- Ask ONE question at a time
- Keep questions clear and specific
- Listen for implicit information in user responses
- Maximum 3 conversation turns - be efficient
- When you have enough core information, provide a confirmation summary

INFORMATION TO GATHER:
- What the user wants to change (colors, text, logos, layout)
- Style preferences (traditional African patterns, modern, minimalist, etc.)
- Specific colors if mentioned
- Text content changes
- Logo or branding elements to add

When you have gathered enough information, provide a clear confirmation summary that can be used as a design prompt. Say: "Perfect! I'll help you [summary of changes]. Should I proceed?"

Be concise and conversational. Users appreciate brevity and clarity!"""


@router.websocket("/realtime")
async def voice_realtime(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice conversations.
    
    Handles bidirectional audio streaming with Azure OpenAI Realtime API.
    """
    await websocket.accept()
    
    # Generate session ID
    session_id = f"rt_{uuid.uuid4().hex[:12]}"
    realtime_client = get_realtime_client()
    
    if not realtime_client.enabled:
        await websocket.send_json({
            "type": "error",
            "error": "Realtime API not configured"
        })
        await websocket.close()
        return
    
    try:
        # Create realtime session
        success = await realtime_client.create_session(
            session_id=session_id,
            instructions=REALTIME_INSTRUCTIONS,
            voice="alloy",
            temperature=0.7
        )
        
        if not success:
            await websocket.send_json({
                "type": "error",
                "error": "Failed to create realtime session"
            })
            await websocket.close()
            return
        
        # Send session created event
        await websocket.send_json({
            "type": "session.created",
            "sessionid": session_id
        })
        
        # Create tasks for bidirectional streaming
        async def client_to_server():
            """Forward client messages/audio to realtime API."""
            try:
                while True:
                    data = await websocket.receive_json()
                    
                    if data.get("type") == "input_audio_buffer.append":
                        # Forward audio chunk to realtime API
                        await realtime_client.send_audio_chunk(
                            session_id,
                            data.get("audio", "")
                        )
                    elif data.get("type") == "input_audio_buffer.commit":
                        # Commit audio and request response
                        await realtime_client.commit_audio(session_id)
                        await realtime_client.create_response(session_id)
                    elif data.get("type") == "response.create":
                        # Request response generation
                        await realtime_client.create_response(session_id)
                    
            except WebSocketDisconnect:
                logger.info(f"Client disconnected: {session_id}")
            except Exception as e:
                logger.error(f"Error in client_to_server: {e}")
        
        async def server_to_client():
            """Forward realtime API events to client."""
            try:
                async for event in realtime_client.listen(session_id):
                    # Forward all events to client
                    await websocket.send_json(event)
                    
                    # Check for conversation completion
                    if event.get("type") == "conversation.item.completed":
                        # Check if AI has enough information
                        item = event.get("item", {})
                        content = item.get("content", [])
                        
                        for c in content:
                            if c.get("type") == "text":
                                text = c.get("text", "")
                                # If AI is asking for confirmation, prepare final prompt
                                if "should i proceed" in text.lower() or "shall i proceed" in text.lower():
                                    await websocket.send_json({
                                        "type": "conversation.complete",
                                        "final_prompt": text
                                    })
                    
            except WebSocketDisconnect:
                logger.info(f"Realtime API disconnected: {session_id}")
            except Exception as e:
                logger.error(f"Error in server_to_client: {e}")
        
        # Run both tasks concurrently
        await asyncio.gather(
            client_to_server(),
            server_to_client()
        )
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Error in  realtime WebSocket: {e}")
        await websocket.send_json({
            "type": "error",
            "error": str(e)
        })
    finally:
        # Cleanup
        await realtime_client.close_session(session_id)
        try:
            await websocket.close()
        except:
            pass
