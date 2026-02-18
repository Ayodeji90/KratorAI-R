"""
Business Onboarding via GPT Realtime Audio

WebSocket endpoint for business onboarding using Azure OpenAI Realtime API.
EXACT COPY of voice_realtime.py with onboarding prompt.
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

# Realtime instructions for business onboarding - BUSINESS PROFILE COLLECTION
ONBOARDING_REALTIME_INSTRUCTIONS = """You are a professional Business Consultant for KratorAI, helping business owners create their profile through natural voice conversation.

YOUR GOAL: Collect essential business information to build a complete Business Profile.

CONVERSATION FLOW:
1. Greet warmly: "Hi there! Welcome to KratorAI. I'm your AI Business Consultant. Let's get your business profile set up — it'll only take a minute. What's the name of your business?"
2. Ask ONE question at a time to gather missing information
3. Be conversational — if they give a short answer, ask a quick follow-up
4. Once you have all core information, summarize and ask for confirmation
5. When confirmed, give a PROPER FAREWELL (see below)

BE CONCISE - Keep questions short and clear for spoken conversation.

INFORMATION TO COLLECT:
1. Business Name
2. Industry/Niche (Fashion, Food, Tech, etc.)
3. Description (what the business does)
4. Target Audience (ideal customers)
5. Brand Voice (Professional, Playful, Luxury, etc.)
6. Key Offerings (main products or services)

SUMMARY FORMAT:
When you have all information, say:
"Great! Let me confirm your profile: [Business Name] is a [Industry] business that [Description]. Your target audience is [Target Audience], your brand voice is [Brand Voice], and you offer [Key Offerings]. Does that sound right?"

IMPORTANT CONSTRAINTS:
- DO NOT generate user turns or simulate user speech.
- ONLY respond as the AI assistant.
- NEVER include "User:" or "AI:" prefixes in your spoken response.
- If you hear silence or noise that isn't speech, do not respond.
- Stay in character as the Business Consultant.

COMPLETION — FAREWELL:
When the user confirms their profile is correct, you MUST give a warm, enthusiastic farewell. Say something like:
"Wonderful! Your business profile has been saved and you're all set. Welcome aboard KratorAI! You can now start creating stunning designs for your business. I can't wait to see what you create. Have a great day!"

The farewell MUST include the phrase "welcome aboard KratorAI" — this is the signal that onboarding is complete.

Be friendly, professional, and focused on building their complete profile!"""


@router.websocket("/onboarding/realtime")
async def onboarding_realtime(websocket: WebSocket):
    """
    WebSocket endpoint for business onboarding with real-time voice.
    
    Handles bidirectional audio streaming with Azure OpenAI Realtime API.
    """
    await websocket.accept()
    
    # Generate session ID
    session_id = f"onb_rt_{uuid.uuid4().hex[:12]}"
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
            instructions=ONBOARDING_REALTIME_INSTRUCTIONS,
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
                    
                    # Check for conversation completion via audio transcript
                    if event.get("type") == "response.audio_transcript.done":
                        transcript = event.get("transcript", "")
                        
                        # Detect the farewell — AI says "welcome aboard kratorai" only at the very end
                        if "welcome aboard kratorai" in transcript.lower():
                            logger.info(f"Detected onboarding farewell: {transcript[:100]}...")
                            # Send completion AFTER the transcript (audio already queued on client)
                            await websocket.send_json({
                                "type": "onboarding.complete",
                                "final_summary": transcript
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
        logger.error(f"Error in onboarding realtime WebSocket: {e}")
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
