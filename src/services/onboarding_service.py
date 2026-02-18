import uuid
from typing import Dict, Tuple, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from src.services.o3_mini_client import O3MiniClient
from src.api.schemas.business import BusinessProfile
from src.api.schemas.voice import ConversationMessage, AIResponse
from src.prompts.voice_prompts import BUSINESS_ONBOARDING_SYSTEM_PROMPT, ONBOARDING_FIRST_GREETING
from src.utils.logging import get_logger

logger = get_logger(__name__)

class OnboardingSession(BaseModel):
    session_id: str
    messages: list[ConversationMessage] = Field(default_factory=list)
    profile: BusinessProfile = Field(default_factory=BusinessProfile)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    turn_count: int = 0
    is_complete: bool = False

class OnboardingService:
    def __init__(self):
        self.o3_client = O3MiniClient()
        self.sessions: Dict[str, OnboardingSession] = {}

    def start_session(self) -> Tuple[str, AIResponse]:
        session_id = f"onb_{uuid.uuid4().hex[:12]}"
        
        session = OnboardingSession(session_id=session_id)
        self.sessions[session_id] = session
        
        # Initial greeting
        ai_response = AIResponse(text=ONBOARDING_FIRST_GREETING, should_speak=True)
        session.messages.append(ConversationMessage(role="ai", content=ONBOARDING_FIRST_GREETING))
        
        logger.info(f"Started onboarding session: {session_id}")
        return session_id, ai_response

    async def process_turn(self, session_id: str, user_text: str) -> Tuple[AIResponse, BusinessProfile, bool]:
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
            
        session = self.sessions[session_id]
        session.turn_count += 1
        
        # Add user message
        session.messages.append(ConversationMessage(role="user", content=user_text))
        
        # Build context
        context = self._build_context(session)
        user_prompt = f"Conversation context:\n{context}\n\nUser's latest message: {user_text}\n\nRespond with JSON."
        
        try:
            result = await self.o3_client.generate_completion(
                system_prompt=BUSINESS_ONBOARDING_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_format={"type": "json_object"}
            )
            
            if "error" in result:
                raise Exception(result['error'])
                
            ai_message_text = result.get("ai_message", "Could you tell me more?")
            extracted_info = result.get("extracted_info", {})
            is_complete = result.get("onboarding_completed", False)
            
            # Update profile
            self._update_profile(session.profile, extracted_info)
            session.is_complete = is_complete
            
            # Add AI message
            session.messages.append(ConversationMessage(role="ai", content=ai_message_text))
            
            return AIResponse(text=ai_message_text), session.profile, is_complete
            
        except Exception as e:
            logger.error(f"Error in onboarding turn: {e}", exc_info=True)
            return AIResponse(text="I'm having trouble understanding. Could you repeat that?"), session.profile, False

    def get_session(self, session_id: str) -> OnboardingSession:
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        return self.sessions[session_id]

    def _build_context(self, session: OnboardingSession) -> str:
        parts = []
        if session.messages:
            parts.append("Conversation so far:")
            for msg in session.messages[-8:]: # Keep last 8 messages
                parts.append(f"{msg.role.upper()}: {msg.content}")
        
        # Add current profile state
        profile_dump = session.profile.model_dump(exclude_none=True)
        parts.append(f"\nCurrent Profile State: {profile_dump}")
        
        return "\n".join(parts)

    def _update_profile(self, profile: BusinessProfile, new_info: dict):
        for key, value in new_info.items():
            if value and hasattr(profile, key):
                # For lists, append unique items
                if isinstance(value, list) and isinstance(getattr(profile, key), list):
                    current_list = getattr(profile, key) or []
                    for item in value:
                        if item not in current_list:
                            current_list.append(item)
                    setattr(profile, key, current_list)
                else:
                    setattr(profile, key, value)
