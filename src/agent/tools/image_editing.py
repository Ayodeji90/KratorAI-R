"""
Image editing tool for KratorAI agent.

Handles various image editing operations including inpainting,
style transfer, background changes, and color adjustments.
"""

from typing import Optional
from uuid import uuid4

from src.agent.tools.base_tool import BaseTool, ToolResult
from src.services.editing import EditingService


class ImageEditingTool(BaseTool):
    """Tool for editing existing images."""
    
    def __init__(self):
        self._editing_service = EditingService()
    
    @property
    def name(self) -> str:
        return "edit_image"
    
    @property
    def description(self) -> str:
        return (
            "Modify an existing image based on instructions. "
            "Use for inpainting, style changes, background replacement, or targeted edits."
        )
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "image_id": {
                    "type": "string",
                    "description": "The ID of the image to edit."
                },
                "instruction": {
                    "type": "string",
                    "description": "Detailed instructions for what changes to make."
                },
                "edit_type": {
                    "type": "string",
                    "enum": ["inpaint", "style_transfer", "color_adjustment", "background", "general"],
                    "description": "The type of edit to perform."
                },
                "mask_region": {
                    "type": "string",
                    "enum": ["face", "background", "clothing", "hair", "full"],
                    "description": "The region of the image to focus the edit on."
                }
            },
            "required": ["image_id", "instruction"]
        }
    
    async def execute(
        self,
        image_id: str,
        instruction: str,
        edit_type: str = "general",
        mask_region: Optional[str] = None,
    ) -> ToolResult:
        """Apply edits to an image based on instructions."""
        
        # Build the edit prompt based on type and region
        edit_prompt = self._build_edit_prompt(instruction, edit_type, mask_region)
        
        # Map edit types to service types
        service_type_map = {
            "inpaint": "inpaint",
            "style_transfer": "style_transfer",
            "color_adjustment": "color_swap",
            "background": "inpaint",
            "general": "inpaint",
        }
        
        service_edit_type = service_type_map.get(edit_type, "inpaint")
        
        try:
            # For now, use a placeholder URI based on image_id
            # In production, this would resolve from storage
            image_uri = f"gs://kratorai-assets/images/{image_id}.png"
            
            result = await self._editing_service.edit(
                image_uri=image_uri,
                prompt=edit_prompt,
                edit_type=service_edit_type,
            )
            
            return ToolResult(
                success=True,
                data={
                    "image_id": result["asset_id"],
                    "image_uri": result["asset_uri"],
                    "thumbnail_uri": result.get("thumbnail_uri"),
                    "original_id": image_id,
                    "edit_type": edit_type,
                    "instruction": instruction,
                },
                message=f"Applied {edit_type} edit successfully."
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message="Failed to edit image."
            )
    
    def _build_edit_prompt(
        self,
        instruction: str,
        edit_type: str,
        mask_region: Optional[str],
    ) -> str:
        """Build a detailed edit prompt."""
        
        # Edit type specific prefixes
        type_prefixes = {
            "inpaint": "Inpaint the specified area: ",
            "style_transfer": "Apply the following style transformation: ",
            "color_adjustment": "Adjust the colors as follows: ",
            "background": "Modify the background: ",
            "general": "Edit the image: ",
        }
        
        prefix = type_prefixes.get(edit_type, "Edit: ")
        
        # Region specific guidance
        region_guidance = ""
        if mask_region:
            region_map = {
                "face": "Focus on the face area. ",
                "background": "Target the background only, preserve the subject. ",
                "clothing": "Modify clothing/attire only. ",
                "hair": "Focus on hair styling changes. ",
                "full": "Apply to the entire image. ",
            }
            region_guidance = region_map.get(mask_region, "")
        
        return f"{prefix}{instruction} {region_guidance}"
