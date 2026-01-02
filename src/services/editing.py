"""Design editing service."""

from typing import Optional
from uuid import uuid4

from src.services.flux_client import get_flux_client


class EditingService:
    """Service for targeted design editing."""
    
    SUPPORTED_EDIT_TYPES = ["inpaint", "style_transfer", "color_swap"]
    
    def __init__(self):
        self.client = get_flux_client()
    
    async def edit(
        self,
        image_uri: str,
        prompt: str,
        mask_uri: Optional[str] = None,
        edit_type: str = "inpaint",
    ) -> dict:
        """
        Apply targeted edits to a design using FLUX.1.
        
        Args:
            image_uri: Source image URI
            prompt: Edit instructions
            mask_uri: Optional mask for inpainting
            edit_type: Type of edit (inpaint, style_transfer, color_swap)
        
        Returns:
            Edited asset with URI and metadata
        """
        # FLUX.1 supports editing via prompt and optional mask
        
        result = await self.client.edit_image(
            image_url=image_uri,
            prompt=prompt,
            mask_url=mask_uri,
        )
        
        asset_id = str(uuid4())
        asset_uri = ""
        
        if "data" in result and len(result["data"]) > 0:
            asset_uri = result["data"][0].get("url", "")
        
        return {
            "asset_id": asset_id,
            "asset_uri": asset_uri,
            "thumbnail_uri": asset_uri,
            "edit_type": edit_type,
            "generation_result": result,
        }
