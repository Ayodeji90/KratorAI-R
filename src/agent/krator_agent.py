"""
KratorAI Agent - Main orchestrator for the AI image editing assistant.

This module provides the core agent implementation that:
- Handles user conversations with context
- Dispatches tool calls for image operations
- Manages streaming responses
"""

import google.generativeai as genai
from typing import Optional, AsyncGenerator
import json
import logging

from src.config import get_settings
from src.agent.system_prompt import get_system_prompt, get_tool_definitions
from src.agent.memory import ConversationMemory, ImageReference, get_session_manager

logger = logging.getLogger(__name__)


class KratorAgent:
    """
    Main KratorAI agent orchestrator.
    
    Uses Gemini's function calling to provide an intelligent
    image editing assistant experience.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        settings = get_settings()
        
        # Configure Gemini
        genai.configure(api_key=settings.gemini_api_key)
        
        # Initialize the model with function calling
        self.model = genai.GenerativeModel(
            model_name=settings.gemini_model,
            system_instruction=get_system_prompt(),
        )
        
        # Get or create session memory
        session_manager = get_session_manager()
        self.memory = session_manager.get_or_create_session(session_id)
        
        # Tool handlers registry
        self._tool_handlers = {
            "generate_image": self._handle_generate_image,
            "edit_image": self._handle_edit_image,
            "enhance_image": self._handle_enhance_image,
            "breed_designs": self._handle_breed_designs,
            "analyze_image": self._handle_analyze_image,
        }
        
        logger.info(f"KratorAgent initialized for session: {self.memory.session_id}")
    
    @property
    def session_id(self) -> str:
        """Get the current session ID."""
        return self.memory.session_id
    
    async def chat(
        self,
        message: str,
        images: Optional[list[dict]] = None,
    ) -> dict:
        """
        Process a user message and return the agent's response.
        
        Args:
            message: The user's text message
            images: Optional list of image data dicts with 'data' and 'mime_type'
        
        Returns:
            Response dict with 'text', 'images', and 'tool_calls'
        """
        # Track user message in memory
        image_refs = []
        if images:
            for img_data in images:
                ref = ImageReference(
                    image_id=img_data.get("id", str(id(img_data))),
                    uri=img_data.get("uri", "uploaded"),
                    source="upload",
                )
                image_refs.append(ref)
                self.memory.add_image(ref)
        
        self.memory.add_user_message(message, image_refs)
        
        # Build content parts for Gemini
        content_parts = [message]
        if images:
            import httpx
            from PIL import Image
            import io
            
            async with httpx.AsyncClient() as client:
                for img_data in images:
                    if "data" in img_data:
                        content_parts.append({
                            "inline_data": {
                                "mime_type": img_data.get("mime_type", "image/png"),
                                "data": img_data.get("data"),
                            }
                        })
                    elif "url" in img_data:
                        try:
                            response = await client.get(img_data["url"])
                            if response.status_code == 200:
                                image = Image.open(io.BytesIO(response.content))
                                content_parts.append(image)
                        except Exception as e:
                            logger.error(f"Failed to fetch image from URL {img_data['url']}: {e}")
        
        try:
            # Get conversation history for context
            history = self.memory.get_conversation_history(max_messages=20)
            
            # Start chat with history
            chat = self.model.start_chat(history=history[:-1] if len(history) > 1 else [])
            
            # Send message and get response
            response = chat.send_message(content_parts)
            
            # Process the response
            result = await self._process_response(response)
            
            # Track assistant response in memory
            self.memory.add_assistant_message(
                content=result.get("text", ""),
                images=result.get("image_refs", []),
                tool_calls=result.get("tool_calls", []),
                tool_results=result.get("tool_results", []),
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            error_response = {
                "text": f"I apologize, but I encountered an error: {str(e)}. Please try again.",
                "images": [],
                "tool_calls": [],
                "error": str(e),
            }
            return error_response
    
    async def chat_stream(
        self,
        message: str,
        images: Optional[list[dict]] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream the agent's response token by token.
        
        Yields partial response dicts as they become available.
        """
        # Track user message
        self.memory.add_user_message(message, [])
        
        content_parts = [message]
        if images:
            import httpx
            from PIL import Image
            import io
            
            async with httpx.AsyncClient() as client:
                for img_data in images:
                    if "data" in img_data:
                        content_parts.append({
                            "inline_data": {
                                "mime_type": img_data.get("mime_type", "image/png"),
                                "data": img_data.get("data"),
                            }
                        })
                    elif "url" in img_data:
                        try:
                            response = await client.get(img_data["url"])
                            if response.status_code == 200:
                                image = Image.open(io.BytesIO(response.content))
                                content_parts.append(image)
                        except Exception as e:
                            logger.error(f"Failed to fetch image from URL {img_data['url']}: {e}")
        
        try:
            history = self.memory.get_conversation_history(max_messages=20)
            chat = self.model.start_chat(history=history[:-1] if len(history) > 1 else [])
            
            response = chat.send_message(content_parts, stream=True)
            
            accumulated_text = ""
            for chunk in response:
                if chunk.text:
                    accumulated_text += chunk.text
                    yield {
                        "type": "text_delta",
                        "content": chunk.text,
                        "accumulated": accumulated_text,
                    }
            
            # Final response
            yield {
                "type": "complete",
                "text": accumulated_text,
                "images": [],
            }
            
            self.memory.add_assistant_message(content=accumulated_text)
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield {
                "type": "error",
                "error": str(e),
            }
    
    async def _process_response(self, response) -> dict:
        """Process the Gemini response, handling any function calls."""
        result = {
            "text": "",
            "images": [],
            "tool_calls": [],
            "tool_results": [],
            "image_refs": [],
        }
        
        # Extract text content
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        result["text"] += part.text
                    
                    # Handle function calls
                    if hasattr(part, "function_call") and part.function_call:
                        func_call = part.function_call
                        tool_call = {
                            "name": func_call.name,
                            "args": dict(func_call.args) if func_call.args else {},
                        }
                        result["tool_calls"].append(tool_call)
                        
                        # Execute the tool
                        tool_result = await self._execute_tool(
                            func_call.name,
                            dict(func_call.args) if func_call.args else {}
                        )
                        result["tool_results"].append(tool_result)
                        
                        # If tool generated an image, track it
                        if "image" in tool_result:
                            result["images"].append(tool_result["image"])
        
        return result
    
    async def _execute_tool(self, name: str, args: dict) -> dict:
        """Execute a tool by name with given arguments."""
        handler = self._tool_handlers.get(name)
        if not handler:
            logger.warning(f"Unknown tool: {name}")
            return {"error": f"Unknown tool: {name}"}
        
        try:
            return await handler(**args)
        except Exception as e:
            logger.error(f"Tool execution error ({name}): {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # Tool Handlers
    # =========================================================================
    
    async def _handle_generate_image(
        self,
        prompt: str,
        style: str = "headshot",
        aspect_ratio: str = "1:1",
        quality: str = "high",
    ) -> dict:
        """Handle image generation requests."""
        from src.services.gemini_client import get_gemini_client
        
        logger.info(f"Generating image: {prompt[:50]}...")
        
        client = get_gemini_client()
        
        # Build enhanced prompt based on style
        enhanced_prompt = self._enhance_prompt_for_style(prompt, style)
        
        try:
            # Use the Gemini client to generate
            result = await client.generate_with_images(
                prompt=enhanced_prompt,
                image_uris=[],
                generation_config={"temperature": 0.7}
            )
            
            # Create image reference
            from uuid import uuid4
            image_id = str(uuid4())
            
            image_ref = ImageReference(
                image_id=image_id,
                uri=f"gs://kratorai-assets/generated/{image_id}.png",
                source="generated",
                metadata={
                    "prompt": prompt,
                    "style": style,
                    "quality": quality,
                }
            )
            self.memory.add_image(image_ref)
            
            return {
                "success": True,
                "image_id": image_id,
                "image": {
                    "id": image_id,
                    "uri": image_ref.uri,
                    "prompt": prompt,
                },
                "message": f"Generated {style} image successfully.",
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_edit_image(
        self,
        image_id: str,
        instruction: str,
        edit_type: str = "general",
        mask_region: Optional[str] = None,
    ) -> dict:
        """Handle image editing requests."""
        from src.services.editing import EditingService
        
        logger.info(f"Editing image {image_id}: {instruction[:50]}...")
        
        # Get the image from memory
        image_ref = self.memory.get_image(image_id)
        if not image_ref:
            # Try to find by partial match
            latest = self.memory.get_latest_image()
            if latest:
                image_ref = latest
            else:
                return {"success": False, "error": f"Image not found: {image_id}"}
        
        editing_service = EditingService()
        
        try:
            result = await editing_service.edit(
                image_uri=image_ref.uri,
                prompt=instruction,
                edit_type=edit_type if edit_type != "general" else "inpaint",
            )
            
            # Create new image reference for edited version
            new_ref = ImageReference(
                image_id=result["asset_id"],
                uri=result["asset_uri"],
                source="edited",
                metadata={
                    "parent_id": image_id,
                    "instruction": instruction,
                    "edit_type": edit_type,
                }
            )
            self.memory.add_image(new_ref)
            
            return {
                "success": True,
                "image_id": result["asset_id"],
                "image": {
                    "id": result["asset_id"],
                    "uri": result["asset_uri"],
                },
                "message": f"Applied {edit_type} edit successfully.",
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_enhance_image(
        self,
        image_id: str,
        enhancements: list[str],
    ) -> dict:
        """Handle image enhancement requests."""
        from src.services.refining import RefiningService
        
        logger.info(f"Enhancing image {image_id}: {enhancements}")
        
        image_ref = self.memory.get_image(image_id)
        if not image_ref:
            latest = self.memory.get_latest_image()
            if latest:
                image_ref = latest
            else:
                return {"success": False, "error": f"Image not found: {image_id}"}
        
        refining_service = RefiningService()
        
        # Build enhancement prompt
        enhancement_prompt = f"Apply the following enhancements: {', '.join(enhancements)}"
        
        try:
            results = await refining_service.refine(
                image_uri=image_ref.uri,
                prompt=enhancement_prompt,
                strength=0.6,
                num_variations=1,
            )
            
            if results:
                result = results[0]
                new_ref = ImageReference(
                    image_id=result["asset_id"],
                    uri=result["asset_uri"],
                    source="edited",
                    metadata={
                        "parent_id": image_id,
                        "enhancements": enhancements,
                    }
                )
                self.memory.add_image(new_ref)
                
                return {
                    "success": True,
                    "image_id": result["asset_id"],
                    "image": {
                        "id": result["asset_id"],
                        "uri": result["asset_uri"],
                    },
                    "message": f"Applied enhancements: {', '.join(enhancements)}",
                }
            
            return {"success": False, "error": "Enhancement failed"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_breed_designs(
        self,
        image_ids: list[str],
        weights: Optional[list[float]] = None,
        style_prompt: Optional[str] = None,
        preserve_cultural: bool = True,
    ) -> dict:
        """Handle design breeding requests."""
        from src.services.breeding import BreedingService
        
        logger.info(f"Breeding designs: {image_ids}")
        
        # Resolve image URIs
        image_data = []
        for img_id in image_ids:
            ref = self.memory.get_image(img_id)
            if ref:
                image_data.append(ref.uri)
        
        if len(image_data) < 2:
            return {"success": False, "error": "Need at least 2 images for breeding"}
        
        # Default weights if not provided
        if not weights:
            weights = [1.0 / len(image_data)] * len(image_data)
        
        breeding_service = BreedingService()
        
        try:
            result = await breeding_service.breed(
                images=list(zip(image_data, weights)),
                prompt=style_prompt,
                preserve_cultural=preserve_cultural,
            )
            
            new_ref = ImageReference(
                image_id=result["asset_id"],
                uri=result["asset_uri"],
                source="generated",
                metadata={
                    "parent_ids": image_ids,
                    "weights": weights,
                    "style_prompt": style_prompt,
                }
            )
            self.memory.add_image(new_ref)
            
            return {
                "success": True,
                "image_id": result["asset_id"],
                "image": {
                    "id": result["asset_id"],
                    "uri": result["asset_uri"],
                },
                "message": f"Created hybrid design from {len(image_ids)} images.",
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_analyze_image(
        self,
        image_id: str,
        analysis_type: str = "full",
    ) -> dict:
        """Handle image analysis requests."""
        from src.services.gemini_client import get_gemini_client
        
        logger.info(f"Analyzing image {image_id}: {analysis_type}")
        
        image_ref = self.memory.get_image(image_id)
        if not image_ref:
            latest = self.memory.get_latest_image()
            if latest:
                image_ref = latest
            else:
                return {"success": False, "error": f"Image not found: {image_id}"}
        
        analysis_prompts = {
            "quality": "Analyze this image's technical quality including resolution, noise, sharpness, and exposure.",
            "composition": "Analyze this image's composition including framing, rule of thirds, leading lines, and balance.",
            "style": "Describe the artistic style, color palette, mood, and any cultural design elements in this image.",
            "faces": "Analyze any faces in this image including expression, lighting on face, and portrait quality.",
            "full": "Provide a comprehensive analysis of this image including quality, composition, style, and content.",
        }
        
        prompt = analysis_prompts.get(analysis_type, analysis_prompts["full"])
        
        client = get_gemini_client()
        
        try:
            result = await client.generate_with_images(
                prompt=prompt,
                image_uris=[image_ref.uri],
            )
            
            return {
                "success": True,
                "analysis_type": analysis_type,
                "analysis": result.get("text", "Analysis not available"),
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _enhance_prompt_for_style(self, prompt: str, style: str) -> str:
        """Enhance a prompt based on the desired style."""
        style_enhancers = {
            "headshot": (
                f"Professional headshot photograph: {prompt}. "
                "Studio lighting, sharp focus on face, slightly blurred background, "
                "professional and approachable expression, high resolution."
            ),
            "portrait": (
                f"Artistic portrait: {prompt}. "
                "Beautiful lighting, thoughtful composition, emotional depth, "
                "high quality photography style."
            ),
            "creative": (
                f"Creative artistic image: {prompt}. "
                "Unique visual style, vibrant colors, imaginative composition."
            ),
            "product": (
                f"Product photography: {prompt}. "
                "Clean background, professional lighting, sharp details."
            ),
            "abstract": (
                f"Abstract art: {prompt}. "
                "Non-representational, focus on color, shape, and texture."
            ),
        }
        
        return style_enhancers.get(style, prompt)
    
    def get_session_summary(self) -> dict:
        """Get a summary of the current session."""
        return {
            "session_id": self.session_id,
            "message_count": len(self.memory.messages),
            "image_count": len(self.memory.images),
            "context_summary": self.memory.get_context_summary(),
        }


# Global agent instances by session
_agents: dict[str, KratorAgent] = {}


def get_agent(session_id: Optional[str] = None) -> KratorAgent:
    """Get or create an agent for the given session."""
    if session_id and session_id in _agents:
        return _agents[session_id]
    
    agent = KratorAgent(session_id)
    _agents[agent.session_id] = agent
    return agent
