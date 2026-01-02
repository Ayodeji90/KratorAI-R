"""Design breeding service."""

from typing import Optional
from uuid import uuid4

from src.services.flux_client import get_flux_client


class BreedingService:
    """Service for breeding multiple designs together."""
    
    def __init__(self):
        self.client = get_flux_client()
    
    async def breed(
        self,
        images: list[tuple[str, float]],
        prompt: Optional[str] = None,
        preserve_cultural: bool = True,
    ) -> dict:
        """
        Breed multiple designs to create a hybrid using FLUX.1.
        
        Args:
            images: List of (uri, weight) tuples
            prompt: Additional styling prompt
            preserve_cultural: Prioritize African motifs
        
        Returns:
            Generated asset with URI and metadata
        """
        # Construct a blending prompt since FLUX.1 is text-to-image (mostly)
        # In a real scenario, we might use an image-to-image endpoint if supported
        # or just describe the blend.
        
        blend_prompt = "Create a hybrid design that blends elements from multiple sources. "
        blend_prompt += "Combine patterns, colors, and styles into a cohesive image. "
        
        if preserve_cultural:
            blend_prompt += "Ensure African cultural motifs (Adinkra, Kente, etc.) are preserved and highlighted. "
        if prompt:
            blend_prompt += f"Also incorporate this style: {prompt}"
            
        # Call FLUX.1 for generation
        result = await self.client.generate_image(
            prompt=blend_prompt,
            size="1024x1024",
            quality="hd"
        )
        
        asset_id = str(uuid4())
        asset_uri = ""
        
        if "data" in result and len(result["data"]) > 0:
            asset_uri = result["data"][0].get("url", "")
        
        return {
            "asset_id": asset_id,
            "asset_uri": asset_uri,
            "thumbnail_uri": asset_uri,
            "generation_result": result,
        }
