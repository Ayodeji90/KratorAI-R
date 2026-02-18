"""
Voice Conversation Routes

FastAPI routes for conversational voice interface.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Optional

from src.api.schemas.voice import (
    VoiceConversationStart,
    VoiceConversationTurn,
    VoiceConversationResponse,
    VoiceConfirmation,
    VoiceExecutionResponse,
    VoiceConversationHistory,
    AIResponse,
    ConversationState
)
from src.services.voice_conversation_service import VoiceConversationService
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Initialize service
voice_service = VoiceConversationService()


@router.post("/conversation/start", response_model=VoiceConversationResponse)
async def start_conversation(request: VoiceConversationStart):
    """
    Start a new voice conversation session.
    
    The AI will greet the user and be ready to help them create their design.
    """
    try:
        session_id, ai_response = voice_service.start_conversation(
            initial_message=request.initial_message,
            context=request.context
        )
        
        conversation = voice_service.get_conversation(session_id)
        
        return VoiceConversationResponse(
            session_id=session_id,
            ai_response=ai_response,
            state=conversation.state,
            extracted_info=conversation.extracted_info,
            conversation_complete=False
        )
    
    except Exception as e:
        logger.error(f"Error starting conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start conversation: {str(e)}"
        )


@router.post("/conversation/turn", response_model=VoiceConversationResponse)
async def process_conversation_turn(request: VoiceConversationTurn):
    """
    Process a user's voice input and get AI's response.
    
    This endpoint handles each back-and-forth turn in the conversation.
    The AI will ask follow-up questions until it has enough information,
    then it will provide a confirmation summary.
    """
    try:
        ai_response, state, extracted_info, is_complete = voice_service.process_turn(
            session_id=request.session_id,
            user_text=request.user_text
        )
        
        return VoiceConversationResponse(
            session_id=request.session_id,
            ai_response=ai_response,
            state=state,
            extracted_info=extracted_info,
            conversation_complete=is_complete
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing conversation turn: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process turn: {str(e)}"
        )


@router.get("/conversation/{session_id}", response_model=VoiceConversationHistory)
async def get_conversation(session_id: str):
    """
    Get the full conversation history and current state.
    
    Useful for debugging or displaying the conversation to the user.
    """
    try:
        conversation = voice_service.get_conversation(session_id)
        return conversation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/conversation/confirm", response_model=VoiceExecutionResponse)
async def confirm_conversation(request: VoiceConfirmation):
    """
    User confirms the AI's summary - prepare execution parameters.
    
    Returns the action type and optimized prompt that should be sent
    to the existing image generation endpoints (/refine, /edit, /breed, etc.).
    
    Frontend should then call the appropriate endpoint with the returned parameters.
    """
    try:
        if not request.confirmed:
            # User wants to make modifications
            if request.modifications:
                # Could restart conversation with modifications as context
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User requested modifications - restart conversation"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User did not confirm"
            )
        
        # Prepare execution parameters
        execution_params = voice_service.confirm_and_prepare_execution(request.session_id)
        
        # Generate human-readable message
        message = f"Creating your {execution_params.action} with the optimized prompt..."
        
        return VoiceExecutionResponse(
            session_id=request.session_id,
            execution_params=execution_params,
            message=message
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm: {str(e)}"
        )


@router.post("/conversation/reset")
async def reset_conversation(session_id: str):
    """
    Reset a conversation to start fresh.
    
    Clears all messages and extracted information.
    """
    try:
        voice_service.reset_conversation(session_id)
        return {"message": "Conversation reset successfully", "session_id": session_id}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/conversation/{session_id}")
async def delete_conversation(session_id: str):
    """
    Delete a conversation session.
    
    Removes all data for this session from storage.
    """
    try:
        voice_service.delete_conversation(session_id)
        return {"message": "Conversation deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        return {"message": "Conversation deleted or not found"}
