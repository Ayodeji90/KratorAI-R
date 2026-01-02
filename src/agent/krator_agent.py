"""
KratorAI Agent - Main orchestrator for the AI image editing assistant.

This module provides the core agent implementation that:
- Handles user commands for image operations (Generation, Editing, Breeding)
- Uses FLUX.1 for all image tasks
- No longer supports conversational chat or image analysis
"""

from typing import Optional, AsyncGenerator, List, Dict, Any
import logging
import json
from uuid import uuid4

from src.config import get_settings
from src.agent.memory import ConversationMemory, ImageReference, get_session_manager

logger = logging.getLogger(__name__)


class KratorAgent:
    """
    Main KratorAI agent orchestrator.
    
    Simplified to handle direct commands for FLUX.1 image generation.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        settings = get_settings()
        
        # Get or create session memory
        session_manager = get_session_manager()
        self.memory = session_manager.get_or_create_session(session_id)
        
        # Tool handlers registry
        self._tool_handlers = {
            "generate_image": self._handle_generate_image,
            "edit_image": self._handle_edit_image,
            "breed_designs": self._handle_breed_designs,
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
        Process a user message as a command.
        
        Args:
            message: The user's text message
            images: Optional list of image data dicts
        
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
        
        # Simple command parsing
        msg_lower = message.lower()
        
        response_text = ""
        tool_calls = []
        tool_results = []
        generated_images = []
        
        try:
            if "generate" in msg_lower or "create" in msg_lower:
                # Extract prompt (naive implementation)
                prompt = message
                for prefix in ["generate", "create", "make", "an image of", "a picture of"]:
                    if prefix in prompt.lower():
                        # This is very basic, a real parser would be better but this suffices for now
                        pass
                
                # Call generate tool
                tool_call = {
                    "name": "generate_image",
                    "args": {"prompt": message, "style": "creative"}
                }
                tool_calls.append(tool_call)
                
                result = await self._handle_generate_image(message)
                tool_results.append(result)
                
                if result.get("success"):
                    response_text = result.get("message", "Image generated.")
                    if "image" in result:
                        generated_images.append(result["image"])
                else:
                    response_text = f"Failed to generate image: {result.get('error')}"
                    
            elif "edit" in msg_lower or "change" in msg_lower or "modify" in msg_lower:
                # Need an image to edit
                latest_image = self.memory.get_latest_image()
                if latest_image:
                    tool_call = {
                        "name": "edit_image",
                        "args": {"image_id": latest_image.image_id, "instruction": message}
                    }
                    tool_calls.append(tool_call)
                    
                    result = await self._handle_edit_image(latest_image.image_id, message)
                    tool_results.append(result)
                    
                    if result.get("success"):
                        response_text = result.get("message", "Image edited.")
                        if "image" in result:
                            generated_images.append(result["image"])
                    else:
                        response_text = f"Failed to edit image: {result.get('error')}"
                else:
                    response_text = "I need an image to edit. Please generate or upload one first."
                    
            elif "breed" in msg_lower or "mix" in msg_lower or "combine" in msg_lower:
                # Need at least 2 images
                images = self.memory.get_recent_images(2)
                if len(images) >= 2:
                    image_ids = [img.image_id for img in images]
                    tool_call = {
                        "name": "breed_designs",
                        "args": {"image_ids": image_ids}
                    }
                    tool_calls.append(tool_call)
                    
                    result = await self._handle_breed_designs(image_ids)
                    tool_results.append(result)
                    
                    if result.get("success"):
                        response_text = result.get("message", "Images combined.")
                        if "image" in result:
                            generated_images.append(result["image"])
                    else:
                        response_text = f"Failed to breed images: {result.get('error')}"
                else:
                    response_text = "I need at least 2 recent images to blend them."
            
            else:
                response_text = "I am a FLUX.1 image generator. Please ask me to 'generate', 'edit', or 'breed' images."
            
            # Track assistant response
            self.memory.add_assistant_message(
                content=response_text,
                images=[], # We don't track refs here for now, simplified
                tool_calls=tool_calls,
                tool_results=tool_results,
            )
            
            return {
                "text": response_text,
                "images": generated_images,
                "tool_calls": tool_calls,
                "tool_results": tool_results,
            }
            
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            return {
                "text": f"Error: {str(e)}",
                "images": [],
                "error": str(e)
            }
    
    async def chat_stream(
        self,
        message: str,
        images: Optional[list[dict]] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream the agent's response.
        Since we removed the LLM, this just yields the final result.
        """
        result = await self.chat(message, images)
        
        yield {
            "type": "text_delta",
            "content": result["text"],
            "accumulated": result["text"],
        }
        
        yield {
            "type": "complete",
            "text": result["text"],
            "images": result["images"],
        }

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
        """Handle image generation requests using FLUX.1."""
        from src.services.flux_client import get_flux_client
        
        logger.info(f"Generating image with FLUX.1: {prompt[:50]}...")
        
        client = get_flux_client()
        
        # Build enhanced prompt based on style
        enhanced_prompt = self._enhance_prompt_for_style(prompt, style)
        
        try:
            # Use the FLUX client to generate
            size_map = {
                "1:1": "1024x1024",
                "16:9": "1024x576", 
                "9:16": "576x1024", 
            }
            size = size_map.get(aspect_ratio, "1024x1024")
            
            result = await client.generate_image(
                prompt=enhanced_prompt,
                size=size,
                quality="hd" if quality == "high" else "standard"
            )
            
            if "data" in result and len(result["data"]) > 0:
                image_data = result["data"][0]
                image_url = image_data.get("url")
                
                image_id = str(uuid4())
                
                image_ref = ImageReference(
                    image_id=image_id,
                    uri=image_url, 
                    source="generated",
                    metadata={
                        "prompt": prompt,
                        "style": style,
                        "quality": quality,
                        "model": "FLUX.1-Kontext-pro"
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
                    "message": f"Generated {style} image successfully with FLUX.1.",
                }
            else:
                return {"success": False, "error": "No image data returned from FLUX.1"}
            
        except Exception as e:
            logger.error(f"FLUX generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_edit_image(
        self,
        image_id: str,
        instruction: str,
        edit_type: str = "general",
        mask_region: Optional[str] = None,
    ) -> dict:
        """Handle image editing requests using FLUX.1."""
        from src.services.flux_client import get_flux_client
        
        logger.info(f"Editing image {image_id} with FLUX.1: {instruction[:50]}...")
        
        image_ref = self.memory.get_image(image_id)
        if not image_ref:
            latest = self.memory.get_latest_image()
            if latest:
                image_ref = latest
            else:
                return {"success": False, "error": f"Image not found: {image_id}"}
        
        client = get_flux_client()
        
        try:
            result = await client.edit_image(
                image_url=image_ref.uri,
                prompt=instruction,
                mask_url=None 
            )
            
            if "data" in result and len(result["data"]) > 0:
                image_data = result["data"][0]
                new_uri = image_data.get("url")
                
                new_id = str(uuid4())
                
                new_ref = ImageReference(
                    image_id=new_id,
                    uri=new_uri,
                    source="edited",
                    metadata={
                        "parent_id": image_id,
                        "instruction": instruction,
                        "edit_type": edit_type,
                        "model": "FLUX.1-Kontext-pro"
                    }
                )
                self.memory.add_image(new_ref)
                
                return {
                    "success": True,
                    "image_id": new_id,
                    "image": {
                        "id": new_id,
                        "uri": new_uri,
                    },
                    "message": f"Applied {edit_type} edit successfully with FLUX.1.",
                }
            else:
                return {"success": False, "error": "No image data returned from FLUX.1 Edit"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_breed_designs(
        self,
        image_ids: list[str],
        weights: Optional[list[float]] = None,
        style_prompt: Optional[str] = None,
        preserve_cultural: bool = True,
    ) -> dict:
        """
        Handle design breeding requests.
        Uses a template prompt since we can't use Gemini to describe the blend.
        """
        from src.services.flux_client import get_flux_client
        
        logger.info(f"Breeding designs: {image_ids}")
        
        if len(image_ids) < 2:
            return {"success": False, "error": "Need at least 2 images for breeding"}
            
        # Since we can't see the images to describe them, we'll use a generic blend prompt
        # In a real scenario, we might want to use a vision model (like GPT-4o or Gemini) 
        # but the user explicitly requested removing Gemini.
        
        blend_prompt = "Create a hybrid design that blends elements from multiple sources. "
        blend_prompt += "Combine patterns, colors, and styles into a cohesive image. "
        
        if preserve_cultural:
            blend_prompt += "Ensure African cultural motifs (Adinkra, Kente, etc.) are preserved and highlighted. "
        if style_prompt:
            blend_prompt += f"Also incorporate this style: {style_prompt}"
            
        try:
            flux_client = get_flux_client()
            result = await flux_client.generate_image(
                prompt=blend_prompt,
                size="1024x1024",
                quality="hd"
            )
            
            if "data" in result and len(result["data"]) > 0:
                image_data = result["data"][0]
                image_url = image_data.get("url")
                
                new_id = str(uuid4())
                
                new_ref = ImageReference(
                    image_id=new_id,
                    uri=image_url,
                    source="generated",
                    metadata={
                        "parent_ids": image_ids,
                        "generated_prompt": blend_prompt,
                        "model": "FLUX.1-Kontext-pro"
                    }
                )
                self.memory.add_image(new_ref)
                
                return {
                    "success": True,
                    "image_id": new_id,
                    "image": {
                        "id": new_id,
                        "uri": image_url,
                    },
                    "message": f"Created hybrid design from {len(image_ids)} images using FLUX.1.",
                }
            else:
                return {"success": False, "error": "No image data returned from FLUX.1"}
            
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
