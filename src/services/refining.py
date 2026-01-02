"""Design refining service."""

import base64
import logging
import tempfile
from typing import Optional
from uuid import uuid4
from pathlib import Path

from src.services.flux_client import get_flux_client

logger = logging.getLogger(__name__)


class RefiningService:
    """Service for generating refined variations of designs."""
    
    def __init__(self):
        self.client = get_flux_client()
    
    async def refine(
        self,
        image_uri: str,
        prompt: str,
        strength: float = 0.7,
        num_variations: int = 3,
    ) -> list[dict]:
        """
        Generate refined variations of a design using FLUX.1.
        
        Args:
            image_uri: Source image URI
            prompt: Refinement instructions
            strength: Refinement intensity (0.1 - 1.0)
            num_variations: Number of variations to generate
        
        Returns:
            List of generated variations with URIs
        """
        variations = []
        
        # FLUX.1 might not support batch generation in one call depending on the API,
        # so we'll loop.
        
        for i in range(num_variations):
            # Vary the prompt slightly for diversity
            varied_prompt = f"{prompt} (Variation {i + 1})"
            
            logger.info(f"Generating variation {i + 1}/{num_variations} with prompt: {varied_prompt}")
            
            # Use edit_image to refine existing image
            result = await self.client.edit_image(
                image_url=image_uri,
                prompt=varied_prompt,
                mask_url=None
            )
            
            logger.debug(f"FLUX API response for variation {i + 1}: {result}")
            logger.info(f"Response top-level keys: {list(result.keys())}")
            
            # Check for errors in the response
            if result.get("success") == False:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"FLUX API returned error for variation {i + 1}: {error_msg}")
                raise Exception(f"FLUX API error: {error_msg}")
            
            asset_id = str(uuid4())
            asset_uri = ""
            thumbnail_uri = ""
            
            # Try to extract the image from various possible response formats
            if "data" in result and len(result["data"]) > 0:
                logger.info(f"Found 'data' field with {len(result['data'])} items")
                logger.info(f"First data item keys: {list(result['data'][0].keys())}")
                data_item = result["data"][0]
                
                
                # Format 1: URL (OpenAI format)
                if "url" in data_item and data_item["url"]:
                    asset_uri = data_item["url"]
                    logger.info(f"Got image URL: {asset_uri[:100] if len(asset_uri) > 100 else asset_uri}")
                
                # Format 2: Base64 encoded (b64_json) - fallback if URL is empty
                elif "b64_json" in data_item and data_item["b64_json"]:
                    logger.info("Got base64 image, saving to file...")
                    b64_data = data_item["b64_json"]
                    file_path = self._save_base64_image(b64_data, asset_id)
                    # Convert local file path to HTTP URL
                    asset_uri = f"/generated/{Path(file_path).name}"
                    logger.info(f"Saved base64 image, accessible at: {asset_uri}")
                
                # Format 3: Direct image field (base64)
                elif "image" in data_item:
                    logger.info("Got base64 image in 'image' field, saving to file...")
                    b64_data = data_item["image"]
                    file_path = self._save_base64_image(b64_data, asset_id)
                    # Convert local file path to HTTP URL
                    asset_uri = f"/generated/{Path(file_path).name}"
                    logger.info(f"Saved base64 image, accessible at: {asset_uri}")
                
                else:
                    logger.warning(f"Unknown response format. Available keys: {list(data_item.keys())}")
                    logger.warning(f"Full data item: {data_item}")
                
                thumbnail_uri = asset_uri
            else:
                logger.error(f"No data in FLUX response. Full response: {result}")
            
            # Validate that we got a valid asset_uri
            if not asset_uri:
                logger.error(f"Failed to extract asset_uri from FLUX response: {result}")
                raise Exception(
                    f"FLUX API returned invalid response - no image URL or data found. "
                    f"Response keys: {list(result.keys())}"
                )

            variations.append({
                "asset_id": asset_id,
                "asset_uri": asset_uri,
                "thumbnail_uri": thumbnail_uri,
                "variation_index": i,
                "generation_result": result,
            })
            
            logger.info(f"Successfully generated variation {i + 1} with asset_uri: {asset_uri[:100]}...")
        
        return variations
    
    def _save_base64_image(self, b64_data: str, asset_id: str) -> str:
        """
        Save a base64-encoded image to a temporary file.
        
        Args:
            b64_data: Base64-encoded image data
            asset_id: Unique asset identifier
            
        Returns:
            File path to the saved image
        """
        # Create temp directory if it doesn't exist
        temp_dir = Path(tempfile.gettempdir()) / "kratorai_generated"
        temp_dir.mkdir(exist_ok=True)
        
        # Decode base64 data
        try:
            image_bytes = base64.b64decode(b64_data)
        except Exception as e:
            logger.error(f"Failed to decode base64 data: {e}")
            raise Exception(f"Invalid base64 image data: {e}")
        
        # Save to file
        file_path = temp_dir / f"{asset_id}.png"
        file_path.write_bytes(image_bytes)
        
        return str(file_path)
