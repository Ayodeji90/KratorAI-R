"""Design editing service."""

from typing import Optional
from uuid import uuid4

from src.services.gemini_client import get_gemini_client


class EditingService:
    """Service for targeted design editing."""
    
    SUPPORTED_EDIT_TYPES = ["inpaint", "style_transfer", "color_swap"]
    
    def __init__(self):
        self.client = get_gemini_client()
    
    async def edit(
        self,
        image_uri: str,
        prompt: str,
        mask_uri: Optional[str] = None,
        edit_type: str = "inpaint",
    ) -> dict:
        """
        Apply targeted edits to a design.
        
        Args:
            image_uri: Source image URI
            prompt: Edit instructions
            mask_uri: Optional mask for inpainting
            edit_type: Type of edit (inpaint, style_transfer, color_swap)
        
        Returns:
            Edited asset with URI and metadata
        """
        if edit_type not in self.SUPPORTED_EDIT_TYPES:
            raise ValueError(f"Unsupported edit type: {edit_type}. Use one of {self.SUPPORTED_EDIT_TYPES}")
        
        result = await self.client.edit_image(
            image_uri=image_uri,
            prompt=prompt,
            mask_uri=mask_uri,
            edit_type=edit_type,
        )
        
        asset_id = str(uuid4())
        
        return {
            "asset_id": asset_id,
            "asset_uri": f"gs://kratorai-assets/edited/{asset_id}.png",
            "thumbnail_uri": f"gs://kratorai-assets/thumbnails/{asset_id}_thumb.png",
            "edit_type": edit_type,
            "generation_result": result,
        }
