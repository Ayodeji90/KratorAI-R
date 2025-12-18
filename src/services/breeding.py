"""Design breeding service."""

from typing import Optional
from uuid import uuid4

from src.services.gemini_client import get_gemini_client


class BreedingService:
    """Service for breeding multiple designs together."""
    
    def __init__(self):
        self.client = get_gemini_client()
    
    async def breed(
        self,
        images: list[tuple[str, float]],
        prompt: Optional[str] = None,
        preserve_cultural: bool = True,
    ) -> dict:
        """
        Breed multiple designs to create a hybrid.
        
        Args:
            images: List of (uri, weight) tuples
            prompt: Additional styling prompt
            preserve_cultural: Prioritize African motifs
        
        Returns:
            Generated asset with URI and metadata
        """
        # Validate weights sum approximately to 1
        total_weight = sum(w for _, w in images)
        if not (0.9 <= total_weight <= 1.1):
            # Normalize weights
            images = [(uri, w / total_weight) for uri, w in images]
        
        # Call Gemini for breeding
        result = await self.client.breed_images(
            image_uris=images,
            style_prompt=prompt,
            preserve_cultural=preserve_cultural,
        )
        
        # TODO: Save generated image to GCS
        # For now, return placeholder
        asset_id = str(uuid4())
        
        return {
            "asset_id": asset_id,
            "asset_uri": f"gs://kratorai-assets/generated/{asset_id}.png",
            "thumbnail_uri": f"gs://kratorai-assets/thumbnails/{asset_id}_thumb.png",
            "generation_result": result,
        }
