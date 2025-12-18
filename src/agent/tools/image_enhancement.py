"""
Image enhancement tool for KratorAI agent.

Handles quality improvements including upscaling, denoising,
sharpening, lighting correction, and retouching.
"""

from typing import Optional
from uuid import uuid4

from src.agent.tools.base_tool import BaseTool, ToolResult
from src.services.refining import RefiningService


class ImageEnhancementTool(BaseTool):
    """Tool for enhancing image quality."""
    
    def __init__(self):
        self._refining_service = RefiningService()
    
    @property
    def name(self) -> str:
        return "enhance_image"
    
    @property
    def description(self) -> str:
        return (
            "Improve the quality and appearance of an image through "
            "various enhancement techniques like upscaling, denoising, and color correction."
        )
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "image_id": {
                    "type": "string",
                    "description": "The ID of the image to enhance."
                },
                "enhancements": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["upscale", "denoise", "sharpen", "light_correct", "color_correct", "retouch"]
                    },
                    "description": "List of enhancements to apply."
                }
            },
            "required": ["image_id", "enhancements"]
        }
    
    async def execute(
        self,
        image_id: str,
        enhancements: list[str],
    ) -> ToolResult:
        """Apply enhancements to an image."""
        
        if not enhancements:
            return ToolResult(
                success=False,
                error="No enhancements specified."
            )
        
        # Build enhancement prompt
        enhancement_prompt = self._build_enhancement_prompt(enhancements)
        
        # Calculate strength based on number of enhancements
        strength = min(0.3 + (len(enhancements) * 0.1), 0.8)
        
        try:
            # For now, use a placeholder URI
            image_uri = f"gs://kratorai-assets/images/{image_id}.png"
            
            results = await self._refining_service.refine(
                image_uri=image_uri,
                prompt=enhancement_prompt,
                strength=strength,
                num_variations=1,
            )
            
            if results:
                result = results[0]
                return ToolResult(
                    success=True,
                    data={
                        "image_id": result["asset_id"],
                        "image_uri": result["asset_uri"],
                        "thumbnail_uri": result.get("thumbnail_uri"),
                        "original_id": image_id,
                        "enhancements_applied": enhancements,
                        "strength": strength,
                    },
                    message=f"Applied enhancements: {', '.join(enhancements)}"
                )
            
            return ToolResult(
                success=False,
                error="Enhancement produced no results."
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message="Failed to enhance image."
            )
    
    def _build_enhancement_prompt(self, enhancements: list[str]) -> str:
        """Build a detailed enhancement prompt."""
        
        enhancement_descriptions = {
            "upscale": "Increase resolution and add fine details",
            "denoise": "Remove noise and grain while preserving details",
            "sharpen": "Enhance sharpness and clarity",
            "light_correct": "Fix lighting issues, balance exposure, recover shadows and highlights",
            "color_correct": "Adjust color balance, enhance vibrancy, ensure natural skin tones",
            "retouch": "Subtle skin retouching, blemish removal while maintaining natural appearance",
        }
        
        prompt_parts = ["Enhance this image with the following improvements:"]
        
        for enhancement in enhancements:
            if enhancement in enhancement_descriptions:
                prompt_parts.append(f"- {enhancement_descriptions[enhancement]}")
        
        prompt_parts.append("Maintain natural appearance and avoid over-processing.")
        
        return "\n".join(prompt_parts)
