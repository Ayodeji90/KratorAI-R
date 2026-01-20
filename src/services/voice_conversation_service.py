"""
Voice Conversation Service

Handles conversational AI interactions for voice-based design creation.
Manages multi-turn dialogues, extracts information, and constructs prompts.
"""

import json
import uuid
from typing import Dict, Optional, Tuple
from datetime import datetime

from src.services.o3_mini_client import O3MiniClient
from src.api.schemas.voice import (
    VoiceConversationHistory,
    ConversationMessage,
    ExtractedDesignInfo,
    VoiceExecutionParams,
    AIResponse,
    ConversationState
)
from src.prompts.voice_prompts import (
    VOICE_CONVERSATION_SYSTEM_PROMPT,
    FIRST_QUESTION_TEMPLATES,
    CONFIRMATION_TEMPLATE,
    COMPLETENESS_REQUIREMENTS,
    MAX_CONVERSATION_TURNS,
    DEFAULT_PROMPT_TEMPLATES
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class VoiceConversationService:
    """Service for managing voice conversations."""
    
    def __init__(self):
        self.o3_client = O3MiniClient()
        # In-memory session storage (use Redis in production)
        self.sessions: Dict[str, VoiceConversationHistory] = {}
    
    def start_conversation(self, initial_message: Optional[str] = None) -> Tuple[str, AIResponse]:
        """
        Start a new voice conversation session.
        
        Args:
            initial_message: Optional initial user message
            
        Returns:
            Tuple of (session_id, ai_response)
        """
        session_id = f"conv_{uuid.uuid4().hex[:12]}"
        
        # Initialize conversation history
        conversation = VoiceConversationHistory(
            session_id=session_id,
            state=ConversationState.GATHERING_INFO,
            messages=[],
            extracted_info=ExtractedDesignInfo(),
            turn_count=0
        )
        
        # If there's an initial message, process it
        if initial_message:
            ai_response_text = self._generate_first_response(initial_message, conversation)
        else:
            ai_response_text = "Hi! I'm here to help you create or edit your design. What would you like to make today?"
        
        ai_response = AIResponse(text=ai_response_text, should_speak=True)
        
        # Save session
        self.sessions[session_id] = conversation
        
        logger.info(f"Started conversation session: {session_id}")
        return session_id, ai_response
    
    async def process_turn(self, session_id: str, user_text: str) -> Tuple[AIResponse, str, ExtractedDesignInfo, bool]:
        """
        Process a conversation turn.
        
        Args:
            session_id: Conversation session ID
            user_text: User's transcribed voice input
            
        Returns:
            Tuple of (ai_response, state, extracted_info, conversation_complete)
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        conversation = self.sessions[session_id]
        conversation.turn_count += 1
        conversation.updated_at = datetime.utcnow()
        
        # Add user message to history
        user_message = ConversationMessage(role="user", content=user_text)
        conversation.messages.append(user_message)
        
        # Generate AI response using o3-mini
        ai_response_text, extracted_info, is_complete = await self._generate_ai_response(
            conversation, user_text
        )
        
        # Update extracted info
        conversation.extracted_info = extracted_info
        
        # Add AI message to history
        ai_message = ConversationMessage(role="ai", content=ai_response_text)
        conversation.messages.append(ai_message)
        
        # Update state
        if is_complete:
            conversation.state = ConversationState.READY
        
        ai_response = AIResponse(text=ai_response_text, should_speak=True)
        
        logger.info(f"Processed turn {conversation.turn_count} for session {session_id}")
        
        return ai_response, conversation.state, extracted_info, is_complete
    
    def confirm_and_prepare_execution(self, session_id: str) -> VoiceExecutionParams:
        """
        User confirmed - prep the final execution parameters.
        
        Args:
            session_id: Conversation session ID
            
        Returns:
            VoiceExecutionParams with action and optimized prompt
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        conversation = self.sessions[session_id]
        conversation.state = ConversationState.CONFIRMED
        
        # Construct the optimized prompt from all gathered information
        prompt = self._construct_prompt(conversation.extracted_info)
        
        # Prepare execution parameters
        execution_params = VoiceExecutionParams(
            action=conversation.extracted_info.intent or "refine",
            prompt=prompt,
            strength=conversation.extracted_info.strength,
            num_variations=conversation.extracted_info.num_variations
        )
        
        logger.info(f"Prepared execution for session {session_id}: {execution_params.action}")
        
        return execution_params
    
    def get_conversation(self, session_id: str) -> VoiceConversationHistory:
        """Get full conversation history."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        return self.sessions[session_id]
    
    def reset_conversation(self, session_id: str) -> None:
        """Reset a conversation to start fresh."""
        if session_id in self.sessions:
            conversation = self.sessions[session_id]
            conversation.messages = []
            conversation.extracted_info = ExtractedDesignInfo()
            conversation.turn_count = 0
            conversation.state = ConversationState.GATHERING_INFO
            logger.info(f"Reset conversation {session_id}")
    
    def delete_conversation(self, session_id: str) -> None:
        """Delete a conversation session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted conversation {session_id}")
    
    # Private helper methods
    
    def _generate_first_response(self, initial_message: str, conversation: VoiceConversationHistory) -> str:
        """Generate the first AI response based on initial user message."""
        # Quick intent classification
        intent = self._classify_intent(initial_message)
        conversation.extracted_info.intent = intent
        
        # Extract any initial details
        if "flyer" in initial_message.lower():
            conversation.extracted_info.design_type = "flyer"
        elif "poster" in initial_message.lower():
            conversation.extracted_info.design_type = "poster"
        elif "social" in initial_message.lower():
            conversation.extracted_info.design_type = "social_media"
        
        # Generate appropriate first question
        return "Great! I can help you with that. What style are you going for? Modern, traditional African patterns, or something else?"
    
    def _classify_intent(self, text: str) -> str:
        """Classify user's intent from their message."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["create", "make", "design", "new"]):
            return "template"
        elif any(word in text_lower for word in ["refine", "improve", "enhance", "better"]):
            return "refine"
        elif any(word in text_lower for word in ["edit", "change", "modify", "update", "add"]):
            return "edit"
        elif any(word in text_lower for word in ["combine", "mix", "blend", "breed"]):
            return "breed"
        elif any(word in text_lower for word in ["describe", "what's in", "analyze"]):
            return "describe"
        else:
            return "template"  # Default
    
    async def _generate_ai_response(
        self, 
        conversation: VoiceConversationHistory, 
        user_text: str
    ) -> Tuple[str, ExtractedDesignInfo, bool]:
        """
        Generate AI response using o3-mini.
        
        Returns:
            Tuple of (ai_response_text, updated_extracted_info, is_complete)
        """
        # Build context from conversation history
        context = self._build_context(conversation)
        
        # Create user prompt for o3-mini
        user_prompt = f"""Conversation context:
{context}

User's latest message: {user_text}

Respond with JSON containing ai_message, extracted_info, and conversation_complete."""
        
        try:
            # Call o3-mini for response using the correct method
            result = await self.o3_client.generate_completion(
                system_prompt=VOICE_CONVERSATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_format={"type": "json_object"}
            )
            
            # Check for errors
            if "error" in result:
                logger.error(f"O3-mini error: {result['error']}")
                raise Exception(result['error'])
            
            ai_message = result.get("ai_message", "I see. Can you tell me more?")
            extracted_info_dict = result.get("extracted_info", {})
            is_complete = result.get("conversation_complete", False)
            
            # Update extracted info
            extracted_info = self._update_extracted_info(
                conversation.extracted_info,
                extracted_info_dict,
                user_text
            )
            
            # Check if we should force completion (max turns)
            if conversation.turn_count >= MAX_CONVERSATION_TURNS and not is_complete:
                is_complete = True
                ai_message = self._generate_confirmation_message(extracted_info)
            
            return ai_message, extracted_info, is_complete
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}", exc_info=True)
            # Fallback response
            return "Could you tell me more about what you'd like?", conversation.extracted_info, False
    
    def _build_context(self, conversation: VoiceConversationHistory) -> str:
        """Build conversation context for LLM."""
        context_parts = [f"Turn {conversation.turn_count + 1} of max {MAX_CONVERSATION_TURNS}"]
        
        # Add conversation history
        if conversation.messages:
            context_parts.append("\nConversation so far:")
            for msg in conversation.messages[-6:]:  # Last 6 messages
                context_parts.append(f"{msg.role.upper()}: {msg.content}")
        
        # Add extracted info
        if conversation.extracted_info.intent:
            context_parts.append(f"\nIntent: {conversation.extracted_info.intent}")
        if conversation.extracted_info.design_type:
            context_parts.append(f"Design type: {conversation.extracted_info.design_type}")
        if conversation.extracted_info.style:
            context_parts.append(f"Style: {conversation.extracted_info.style}")
        
        return "\n".join(context_parts)
    
    def _update_extracted_info(
        self, 
        current_info: ExtractedDesignInfo, 
        new_info: dict,
        user_text: str
    ) -> ExtractedDesignInfo:
        """Update extracted information with new details."""
        # Merge new information
        for key, value in new_info.items():
            if value and hasattr(current_info, key):
                setattr(current_info, key, value)
        
        # Extract additional details from user text using simple keyword matching
        text_lower = user_text.lower()
        
        # Extract colors
        colors = current_info.colors or []
        for color in ["red", "blue", "green", "gold", "yellow", "orange", "purple", "black", "white"]:
            if color in text_lower and color not in colors:
                colors.append(color)
        if colors:
            current_info.colors = colors
        
        # Extract African patterns/styles
        if any(word in text_lower for word in ["kente", "ankara", "adinkra", "traditional african"]):
            if "kente" in text_lower:
                current_info.style = "Kente patterns"
            elif "ankara" in text_lower:
                current_info.style = "Ankara patterns"
            elif "adinkra" in text_lower:
                current_info.style = "Adinkra symbols"
        
        return current_info
    
    def _generate_confirmation_message(self, info: ExtractedDesignInfo) -> str:
        """Generate confirmation message summarizing all collected info."""
        parts = []
        
        # Build description
        if info.design_type:
            parts.append(f"a {info.design_type}")
        else:
            parts.append("your design")
        
        if info.style:
            parts.append(f"with {info.style}")
        
        if info.colors:
            color_str = " and ".join(info.colors)
            parts.append(f"in {color_str}")
        
        if info.text_content:
            parts.append(f"featuring '{info.text_content}'")
        
        if info.mood:
            parts.append(f"with a {info.mood} mood")
        
        description = " ".join(parts)
        
        return f"Perfect! Let me confirm: I'm creating {description}. Should I proceed?"
    
    def _construct_prompt(self, info: ExtractedDesignInfo) -> str:
        """Construct optimized image generation prompt from extracted info."""
        prompt_parts = []
        
        # Start with base description
        if info.design_type:
            prompt_parts.append(f"Create a professional {info.design_type}")
        else:
            prompt_parts.append("Create a professional design")
        
        # Add style
        if info.style:
            prompt_parts.append(f"with {info.style}")
        
        # Add colors
        if info.colors:
            color_str = ", ".join(info.colors)
            prompt_parts.append(f"using {color_str} colors")
        
        # Add mood
        if info.mood:
            prompt_parts.append(f"with a {info.mood} aesthetic")
        
        # Add text content
        if info.text_content:
            prompt_parts.append(f"Include the text: '{info.text_content}'")
        
        # Add branding
        if info.branding_elements:
            brand_str = ", ".join(info.branding_elements)
            prompt_parts.append(f"Incorporate branding elements: {brand_str}")
        
        # Add additional details
        if info.additional_details:
            prompt_parts.append(info.additional_details)
        
        # Construct final prompt
        prompt = ". ".join(prompt_parts)
        
        # Ensure it's well-formatted
        if not prompt.endswith("."):
            prompt += "."
        
        prompt += " High quality, professional design with attention to detail and visual appeal."
        
        return prompt
