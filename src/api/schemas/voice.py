# Voice Conversation Schemas

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


class VoiceConversationStart(BaseModel):
    """Request to start a new voice conversation."""
    user_id: Optional[str] = Field(None, description="Optional user identifier for tracking")
    initial_message: Optional[str] = Field(None, description="Optional initial user message")


class VoiceConversationTurn(BaseModel):
    """User's voice input for the current turn."""
    session_id: str = Field(..., description="Conversation session ID")
    user_text: str = Field(..., description="Transcribed text from user's voice")


class ConversationMessage(BaseModel):
    """Single message in the conversation."""
    role: Literal["user", "ai"] = Field(..., description="Who sent the message")
    content: str = Field(..., description="Message text content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationState(str):
    """Current state of the conversation."""
    GATHERING_INFO = "gathering_info"
    READY = "ready"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"


class ExtractedDesignInfo(BaseModel):
    """Structured information collected from conversation."""
    intent: Optional[Literal["breed", "refine", "edit", "describe", "template"]] = None
    design_type: Optional[str] = Field(None, description="Type of design (flyer, poster, social media, etc.)")
    style: Optional[str] = Field(None, description="Visual style (traditional, modern, Kente, Ankara, etc.)")
    colors: Optional[List[str]] = Field(default_factory=list, description="Color preferences")
    text_content: Optional[str] = Field(None, description="Text to include in design")
    branding_elements: Optional[List[str]] = Field(default_factory=list, description="Logos, brand elements")
    mood: Optional[str] = Field(None, description="Overall mood/feeling")
    dimensions: Optional[str] = Field(None, description="Size/dimensions preference")
    additional_details: Optional[str] = Field(None, description="Any other relevant details")
    strength: float = Field(0.7, ge=0.0, le=1.0, description="Refinement strength")
    num_variations: int = Field(3, ge=1, le=5, description="Number of variations to generate")


class AIResponse(BaseModel):
    """AI's response with text and optional voice URL."""
    text: str = Field(..., description="AI response text")
    voice_url: Optional[str] = Field(None, description="URL to TTS audio (if server-side TTS)")
    should_speak: bool = Field(True, description="Whether to speak this response")


class VoiceConversationHistory(BaseModel):
    """Full conversation context and state."""
    session_id: str
    state: str = ConversationState.GATHERING_INFO
    messages: List[ConversationMessage] = Field(default_factory=list)
    extracted_info: ExtractedDesignInfo = Field(default_factory=ExtractedDesignInfo)
    turn_count: int = Field(0, description="Number of conversation turns")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VoiceConversationResponse(BaseModel):
    """Unified response for each conversation turn."""
    session_id: str
    ai_response: AIResponse
    state: str
    extracted_info: ExtractedDesignInfo
    conversation_complete: bool = Field(False, description="Whether conversation is ready for confirmation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "conv_123abc",
                "ai_response": {
                    "text": "Great! What style would you like? Traditional African patterns or something modern?",
                    "should_speak": True
                },
                "state": "gathering_info",
                "extracted_info": {
                    "intent": "template",
                    "design_type": "flyer"
                },
                "conversation_complete": False
            }
        }


class VoiceConfirmation(BaseModel):
    """User's confirmation to proceed with generation."""
    session_id: str
    confirmed: bool = Field(True, description="Whether user confirmed")
    modifications: Optional[str] = Field(None, description="Any requested modifications")


class VoiceExecutionParams(BaseModel):
    """Parameters to execute the actual image generation."""
    action: Literal["breed", "refine", "edit", "describe", "template"]
    prompt: str = Field(..., description="Optimized prompt constructed from conversation")
    strength: float = Field(0.7, ge=0.0, le=1.0)
    num_variations: int = Field(3, ge=1, le=5)
    additional_params: Dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters")


class VoiceExecutionResponse(BaseModel):
    """Response after confirming conversation - tells frontend which endpoint to call."""
    session_id: str
    execution_params: VoiceExecutionParams
    message: str = Field(..., description="Human-readable message about what will be generated")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "conv_123abc",
                "execution_params": {
                    "action": "refine",
                    "prompt": "Create a vibrant traditional Nigerian restaurant flyer with green and gold Ankara patterns. Include 'Mama's Kitchen - Authentic Nigerian Cuisine' as the headline and 'Grand Opening - 20% Off All Meals' as a special offer. Use warm, inviting design with Nigerian cultural elements.",
                    "strength": 0.75,
                    "num_variations": 3
                },
                "message": "Creating your traditional Nigerian restaurant flyer with Ankara patterns..."
            }
        }
