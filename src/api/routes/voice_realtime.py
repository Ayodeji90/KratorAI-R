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

# Realtime instructions for design conversation - PROMPT CONSTRUCTION
REALTIME_INSTRUCTIONS = """You are an AI prompt engineer for KratorAI, helping users create detailed prompts for image editing through natural voice conversation.

YOUR GOAL: Gather information about what the user wants to change, then construct a DETAILED, PROFESSIONAL prompt for the image editing AI model.

CONVERSATION FLOW:
1. Listen to what the user wants to change/edit
2. Ask ONE clarifying question if needed (colors, style, text, etc.)
3. Once you understand, construct a detailed image editing prompt
4. Present the prompt and ask for confirmation

BE CONCISE - Maximum 2-3 turns of conversation.

INFORMATION TO GATHER:
- What to change (colors, text, layout, add elements, remove elements)
- Style preferences (vibrant, professional, African patterns, modern, minimalist)
- Specific colors if mentioned
- Text content changes
- Logo or branding elements

PROMPT CONSTRUCTION:
When you have enough information, create a detailed prompt like:
"Edit this design to [specific changes]. Use [colors/style]. [Additional details about composition, mood, elements to add/remove]. Maintain [what to preserve]."

EXAMPLES OF GOOD PROMPTS:
- "Edit this flyer to change the background to a vibrant orange gradient with traditional Kente patterns. Update the headline text to 'Grand Opening Sale' in bold white letters. Add a decorative border with gold accents. Maintain the existing logo placement."
- "Refine this poster with a professional blue and gold color scheme. Add African-inspired geometric patterns to the corners. Make the text more prominent with a drop shadow effect. Keep the central image but enhance its contrast."
- "Edit the social media post to feature green and yellow colors. Add 'Summer Deals!' as the headline. Include subtle floral patterns in the background. Preserve the product image but brighten the overall composition."

FINAL RESPONSE:
When ready, say: "Here's the prompt I've created: [YOUR DETAILED PROMPT]. Should I proceed with this edit?"

Be friendly, efficient, and focused on creating the best possible prompt!"""


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
