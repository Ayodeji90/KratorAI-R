"""
Image generation tool for KratorAI agent.

Handles generating new images from text descriptions using
Gemini's image generation capabilities.
"""

from typing import Optional
from uuid import uuid4

from src.agent.tools.base_tool import BaseTool, ToolResult



class ImageGenerationTool(BaseTool):
    """Tool for generating images from text descriptions."""
    
    @property
    def name(self) -> str:
        return "generate_image"
    
    @property
    def description(self) -> str:
        return (
            "Generate a new image from a text description. "
            "Use this for creating headshots, portraits, or creative designs from scratch."
        )
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Detailed description of the image to generate. "
                        "Be specific about subject, style, lighting, background."
                    )
                },
                "style": {
                    "type": "string",
                    "enum": ["headshot", "portrait", "creative", "product", "abstract"],
                    "description": "The style preset for the image generation."
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["1:1", "4:5", "5:4", "16:9", "9:16"],
                    "description": "The aspect ratio of the generated image."
                },
                "quality": {
                    "type": "string",
                    "enum": ["standard", "high", "ultra"],
                    "description": "Output quality level."
                }
            },
            "required": ["prompt"]
        }
    
    async def execute(
        self,
        prompt: str,
        style: str = "headshot",
        aspect_ratio: str = "1:1",
        quality: str = "high",
    ) -> ToolResult:
        """Generate an image from the given prompt."""
        
        # Enhance the prompt based on style
        enhanced_prompt = self._build_styled_prompt(prompt, style)
        
        from src.services.flux_client import get_flux_client
        client = get_flux_client()
        
        try:
            # Generate using FLUX.1
            result = await client.generate_image(
                prompt=enhanced_prompt,
                size="1024x1024", # Defaulting size for now
                quality="hd" if quality == "high" else "standard"
            )
            
            # Create a unique ID for the generated image
            image_id = str(uuid4())
            image_uri = ""
            thumbnail_uri = ""
            
            if "data" in result and len(result["data"]) > 0:
                image_uri = result["data"][0].get("url", "")
                thumbnail_uri = image_uri
            
            return ToolResult(
                success=True,
                data={
                    "image_id": image_id,
                    "image_uri": image_uri,
                    "thumbnail_uri": thumbnail_uri,
                    "prompt": prompt,
                    "enhanced_prompt": enhanced_prompt,
                    "style": style,
                    "aspect_ratio": aspect_ratio,
                    "quality": quality,
                    "generation_result": result,
                },
                message=f"Generated {style} image successfully."
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message="Failed to generate image."
            )
    
    def _build_styled_prompt(self, prompt: str, style: str) -> str:
        """Build an enhanced prompt based on the style."""
        
        style_prefixes = {
            "headshot": (
                "Professional headshot photograph. Studio lighting, "
                "sharp focus on face, clean background. "
            ),
            "portrait": (
                "Artistic portrait photography. Beautiful natural lighting, "
                "thoughtful composition, emotional depth. "
            ),
            "creative": (
                "Creative artistic image. Unique visual style, "
                "vibrant colors, imaginative composition. "
            ),
            "product": (
                "Professional product photography. Clean white background, "
                "perfect lighting, sharp details. "
            ),
            "abstract": (
                "Abstract art. Non-representational visuals, "
                "focus on color, shape, and texture. "
            ),
        }
        
        prefix = style_prefixes.get(style, "")
        
        # Add common quality modifiers
        suffix = " High resolution, professional quality."
        
        return f"{prefix}{prompt}{suffix}"
