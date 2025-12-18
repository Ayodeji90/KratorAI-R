"""Design refining service."""

from typing import Optional
from uuid import uuid4
from pathlib import Path

from src.services.gemini_client import get_gemini_client


class RefiningService:
    """Service for generating refined variations of designs."""
    
    def __init__(self):
        self.client = get_gemini_client()
    
    async def refine(
        self,
        image_uri: str,
        prompt: str,
        strength: float = 0.7,
        num_variations: int = 3,
    ) -> list[dict]:
        """
        Generate refined variations of a design.
        
        Args:
            image_uri: Source image URI
            prompt: Refinement instructions
            strength: Refinement intensity (0.1 - 1.0)
            num_variations: Number of variations to generate
        
        Returns:
            List of generated variations with URIs
        """
        variations = []
        
        for i in range(num_variations):
            # Vary the prompt slightly for diversity
            varied_prompt = f"{prompt} (Variation {i + 1})"
            
            result = await self.client.refine_image(
                image_uri=image_uri,
                prompt=varied_prompt,
                strength=strength,
            )
            
            asset_id = str(uuid4())
            
            # Default URIs
            asset_uri = f"gs://kratorai-assets/variations/{asset_id}.png"
            thumbnail_uri = f"gs://kratorai-assets/thumbnails/{asset_id}_thumb.png"
            
            # Save image if available
            if result.get("images"):
                try:
                    img = result["images"][0]
                    # Save to static/generated
                    output_dir = Path("src/static/generated")
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    filename = f"{asset_id}.png"
                    filepath = output_dir / filename
                    img.save(filepath)
                    
                    asset_uri = f"/static/generated/{filename}"
                    thumbnail_uri = asset_uri
                except Exception as e:
                    print(f"Failed to save image: {e}")

            variations.append({
                "asset_id": asset_id,
                "asset_uri": asset_uri,
                "thumbnail_uri": thumbnail_uri,
                "variation_index": i,
                "generation_result": result,
            })
        
        return variations
