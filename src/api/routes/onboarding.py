from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.services.onboarding_service import OnboardingService
from src.api.schemas.voice import VoiceConversationResponse, AIResponse
from src.api.schemas.business import BusinessProfile

router = APIRouter()
onboarding_service = OnboardingService()

class OnboardingTurnRequest(BaseModel):
    session_id: str
    user_text: str

@router.post("/onboarding/start", response_model=VoiceConversationResponse)
async def start_onboarding():
    """Start a new business onboarding voice session."""
    try:
        session_id, ai_response = onboarding_service.start_session()
        return VoiceConversationResponse(
            session_id=session_id,
            ai_response=ai_response,
            state="gathering_info",
            extracted_info={},  # Placeholder as we use BusinessProfile
            conversation_complete=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/onboarding/turn")
async def process_onboarding_turn(request: OnboardingTurnRequest):
    """Process a turn in the onboarding conversation."""
    try:
        ai_response, profile, is_complete = await onboarding_service.process_turn(
            request.session_id, request.user_text
        )
        
        return {
            "session_id": request.session_id,
            "ai_response": ai_response,
            "profile": profile,
            "is_complete": is_complete
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/onboarding/{session_id}")
async def get_onboarding_session(session_id: str):
    """Get the current state of an onboarding session."""
    try:
        return onboarding_service.get_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
