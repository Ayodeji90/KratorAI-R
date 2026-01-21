"""
Voice Audio Routes - REST API with GPT-4o Audio Preview

Uses standard /chat/completions endpoint with audio modalities.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import uuid

from src.services.audio_preview_client import get_audio_client
from src.utils.logging import get_logger
from src.prompts.voice_prompts import VOICE_CONVERSATION_SYSTEM_PROMPT

logger = get_logger(__name__)

router = APIRouter()


class AudioStartRequest(BaseModel):
    """Request to start audio conversation."""
    pass


class AudioStartResponse(BaseModel):
    """Response with session ID and greeting."""
    session_id: str
    greeting: str
    greeting_audio: Optional[str] = None


class AudioTurnRequest(BaseModel):
    """Request for audio conversation turn."""
    session_id: str
    audio_data: str  # Base64 encoded audio
    audio_format: str = "wav"


class AudioTurnResponse(BaseModel):
    """Response with AI audio and text."""
    response_text: str
    response_audio: Optional[str] = None  # Base64 encoded audio
    conversation_complete: bool = False
    final_prompt: Optional[str] = None


class AudioConfirmRequest(BaseModel):
    """Request to confirm and get final prompt."""
    session_id: str


class AudioConfirmResponse(BaseModel):
    """Response with final prompt."""
    prompt: str


@router.post("/audio/start", response_model=AudioStartResponse)
async def start_audio_conversation():
    """Start a new audio conversation session."""
    audio_client = get_audio_client()
    
    if not audio_client.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audio Preview API not configured"
        )
    
    # Generate session ID
    session_id = f"audio_{uuid.uuid4().hex[:12]}"
    
    # Create session
    success = await audio_client.create_session(
        session_id=session_id,
        system_prompt=VOICE_CONVERSATION_SYSTEM_PROMPT
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create audio session"
        )
    
    # Greeting text (no audio for initial greeting to save API call)
    greeting = "Hi! I'm your design assistant. Tell me what changes you'd like to make to your design."
    
    return AudioStartResponse(
        session_id=session_id,
        greeting=greeting,
        greeting_audio=None
    )


@router.post("/audio/turn", response_model=AudioTurnResponse)
async def process_audio_turn(request: AudioTurnRequest):
    """Process an audio turn in the conversation."""
    audio_client = get_audio_client()
    
    if not audio_client.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audio Preview API not configured"
        )
    
    # Process the audio
    result = await audio_client.process_audio_turn(
        session_id=request.session_id,
        audio_base64=request.audio_data,
        audio_format=request.audio_format
    )
    
    if result.get("error"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    # Get final prompt if conversation is complete
    final_prompt = None
    if result.get("conversation_complete"):
        final_prompt = audio_client.get_final_prompt(request.session_id)
    
    return AudioTurnResponse(
        response_text=result.get("response_text", ""),
        response_audio=result.get("response_audio"),
        conversation_complete=result.get("conversation_complete", False),
        final_prompt=final_prompt
    )


@router.post("/audio/confirm", response_model=AudioConfirmResponse)
async def confirm_audio_conversation(request: AudioConfirmRequest):
    """Confirm conversation and get final prompt."""
    audio_client = get_audio_client()
    
    prompt = audio_client.get_final_prompt(request.session_id)
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or no prompt available"
        )
    
    # Close session
    audio_client.close_session(request.session_id)
    
    return AudioConfirmResponse(prompt=prompt)
