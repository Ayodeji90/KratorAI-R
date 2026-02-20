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
from src.prompts.voice_prompts import ONBOARDING_REALTIME_INSTRUCTIONS

logger = get_logger(__name__)

router = APIRouter()


# TOOL DEFINITIONS - ONBOARDING SPEC V2
PROFILE_UPDATE_TOOL = {
    "type": "function",
    "name": "update_profile",
    "description": "Updates a specific field in the user's business profile.",
    "parameters": {
        "type": "object",
        "properties": {
            "field_name": {
                "type": "string",
                "enum": [
                    "company_name", "industry", "team_size", 
                    "brand_name", "voice_tone", "logo_status", "palette_preference",
                    "target_audience_tags", "marketing_objective", "ideal_customer_description",
                    "aesthetic_style"
                ]
            },
            "value": {
                "type": "string",
                "description": "The value to set (can be a string description for tags)"
            }
        },
        "required": ["field_name", "value"]
    }
}

ONBOARDING_STATUS_TOOL = {
    "type": "function",
    "name": "update_onboarding_status",
    "description": "Updates the UI state, navigation, and missing fields for the current onboarding page.",
    "parameters": {
        "type": "object",
        "properties": {
            "page_completed": {
                "type": "boolean",
                "description": "Whether all required fields for the current page are filled"
            },
            "highlight_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Which input field to focus/highlight next"
            },
            "missing_required_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of required fields still missing on this page"
            },
            "suggested_options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Options to suggest for the current field (e.g. industry names or tags)"
            }
        },
        "required": ["page_completed", "missing_required_fields"]
    }
}


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
        # Create realtime session with tools
        success = await realtime_client.create_session(
            session_id=session_id,
            instructions=ONBOARDING_REALTIME_INSTRUCTIONS,
            voice="alloy",
            temperature=0.7,
            tools=[PROFILE_UPDATE_TOOL, ONBOARDING_STATUS_TOOL]
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
        
        # Internal state to batch updates if needed
        current_onboarding_update = {
            "prefill_fields": {},
            "highlight_fields": [],
            "suggested_options": [],
            "page_completed": False,
            "missing_required_fields": []
        }
        
        # Create tasks for bidirectional streaming
        async def client_to_server():
            """Forward client messages/audio to realtime API."""
            try:
                while True:
                    data = await websocket.receive_json()
                    
                    if data.get("type") == "input_audio_buffer.append":
                        await realtime_client.send_audio_chunk(session_id, data.get("audio", ""))
                    elif data.get("type") == "input_audio_buffer.commit":
                        await realtime_client.commit_audio(session_id)
                        await realtime_client.create_response(session_id)
                    elif data.get("type") == "response.create":
                        await realtime_client.create_response(session_id)
                    
            except WebSocketDisconnect:
                logger.info(f"Client disconnected: {session_id}")
            except Exception as e:
                logger.error(f"Error in client_to_server: {e}")
        
        async def server_to_client():
            """Forward realtime API events to client."""
            nonlocal current_onboarding_update
            try:
                async for event in realtime_client.listen(session_id):
                    # Forward all events to client
                    await websocket.send_json(event)
                    
                    # Handle Tool Calls (function calls)
                    if event.get("type") == "response.output_item.done":
                        item = event.get("item", {})
                        if item.get("type") == "function_call":
                            call_id = item.get("call_id")
                            func_name = item.get("name")
                            args_str = item.get("arguments", "{}")
                            
                            try:
                                args = json.loads(args_str)
                                
                                # Handle Profile Updates
                                if func_name == "update_profile":
                                    field = args.get("field_name")
                                    value = args.get("value")
                                    current_onboarding_update["prefill_fields"][field] = value
                                    logger.info(f"Extracted field: {field} = {value}")
                                
                                # Handle Status Updates
                                elif func_name == "update_onboarding_status":
                                    current_onboarding_update.update({
                                        "page_completed": args.get("page_completed", False),
                                        "highlight_fields": args.get("highlight_fields", []),
                                        "missing_required_fields": args.get("missing_required_fields", []),
                                        "suggested_options": args.get("suggested_options", [])
                                    })
                                    logger.info(f"UI Status Update: Page Completed={args.get('page_completed')}")

                                # 1. Send the unified onboarding.update event
                                await websocket.send_json({
                                    "type": "onboarding.update",
                                    **current_onboarding_update
                                })
                                
                                # 2. Provide tool response back to AI
                                ws = realtime_client.sessions.get(session_id)
                                if ws:
                                    response_event = {
                                        "type": "conversation.item.create",
                                        "item": {
                                            "type": "function_call_output",
                                            "call_id": call_id,
                                            "output": json.dumps({"status": "success"})
                                        }
                                    }
                                    await ws.send(json.dumps(response_event))
                                    
                            except json.JSONDecodeError:
                                logger.error(f"Failed to parse tool arguments: {args_str}")

                    # Check for conversation completion
                    if event.get("type") == "response.audio_transcript.done":
                        transcript = event.get("transcript", "")
                        if "welcome aboard kratorai" in transcript.lower():
                            logger.info(f"Detected onboarding farewell")
                            await websocket.send_json({
                                "type": "onboarding.complete",
                                "final_summary": transcript
                            })
                    
            except WebSocketDisconnect:
                logger.info(f"Realtime API disconnected: {session_id}")
            except Exception as e:
                logger.error(f"Error in server_to_client: {e}")
        
        await asyncio.gather(client_to_server(), server_to_client())
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Error in onboarding realtime WebSocket: {e}")
        await websocket.send_json({"type": "error", "error": str(e)})
    finally:
        await realtime_client.close_session(session_id)
        try:
            await websocket.close()
        except:
            pass
