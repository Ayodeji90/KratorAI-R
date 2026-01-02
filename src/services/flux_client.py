"""
FLUX.1 Client for Azure AI.
Handles image generation requests using the FLUX.1 Kontext Pro model on Azure.
"""

import httpx
import logging
import asyncio
from typing import Optional, Dict, Any
from src.config import get_settings

logger = logging.getLogger(__name__)

class FluxClient:
    """Client for interacting with FLUX.1 on Azure AI."""
    
    def __init__(self):
        self.settings = get_settings()
        self.endpoint = self.settings.azure_ai_endpoint.rstrip("/")
        self.api_key = self.settings.azure_ai_key
        self.deployment = self.settings.azure_ai_deployment
        self.api_version = self.settings.azure_ai_api_version
        
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1
    ) -> Dict[str, Any]:
        """
        Generate an image using FLUX.1.
        
        Args:
            prompt: The text prompt for generation.
            size: Image size (e.g., "1024x1024").
            quality: Image quality.
            n: Number of images to generate.
            
        Returns:
            Dict containing the generated image URL/data.
        """
        # Construct the URL for the Azure AI inference endpoint
        # Note: The exact path depends on the specific Azure AI deployment for FLUX.1
        # Typically it follows a pattern like:
        # POST {endpoint}/openai/deployments/{deployment-id}/images/generations?api-version={api-version}
        # However, for non-OpenAI models on Azure AI Studio (MaaS), it might differ.
        # Assuming standard Azure AI Model Inference API structure for now.
        
        url = f"{self.endpoint}/images/generations?api-version={self.api_version}"
        
        # If using the deployments path style:
        # url = f"{self.endpoint}/openai/deployments/{self.deployment}/images/generations?api-version={self.api_version}"
        
        # Based on typical Azure AI MaaS for FLUX:
        # It often uses the standard /images/generations path with the endpoint specific to the model.
        
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }
        
        payload = {
            "prompt": prompt,
            "size": size,
            "n": n,
            # FLUX specific parameters might go here or in 'extra_parameters'
        }
        
        logger.info(f"Sending request to FLUX.1: {url}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    headers=headers, 
                    json=payload, 
                    timeout=60.0
                )
                
                if response.status_code != 200:
                    logger.error(f"FLUX.1 Error: {response.status_code}")
                    logger.error(f"Response body: {response.text}")
                    raise Exception(f"FLUX.1 API Error: {response.status_code} - {response.text}")
                
                response_data = response.json()
                logger.info(f"FLUX.1 Response received with {len(response_data.get('data', []))} images")
                logger.debug(f"Full FLUX.1 Response: {response_data}")
                
                # Add success flag for consistency
                if "success" not in response_data:
                    response_data["success"] = True
                    
                return response_data
                
            except httpx.RequestError as e:
                logger.error(f"Request error: {e}")
                raise Exception(f"Failed to connect to FLUX.1 endpoint: {str(e)}")

    async def edit_image(
        self,
        image_url: str,
        prompt: str,
        mask_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Edit an image using FLUX.1 (Inpainting).
        """
        # Note: Check if the specific FLUX deployment supports inpainting via API.
        # If not, we might need to use a different endpoint or method.
        # For now, implementing a placeholder that attempts the standard edit endpoint.
        
        # Try standard MaaS endpoint first
        url = f"{self.endpoint}/images/edits?api-version={self.api_version}"
        
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }
        
        # Helper to get base64 image data
        async def get_image_data(image_input: str) -> str:
            logger.info(f"Processing image input: {image_input[:100]}...")
            if image_input.startswith("http"):
                async with httpx.AsyncClient() as client:
                    resp = await client.get(image_input)
                    if resp.status_code == 200:
                        import base64
                        encoded = base64.b64encode(resp.content).decode("utf-8")
                        logger.info(f"Encoded image from URL. Length: {len(encoded)}")
                        return encoded
                    raise Exception(f"Failed to download image from {image_input}")
            
            # Check if it's a data URI and strip header if needed
            if image_input.startswith("data:image"):
                logger.info("Input is a Data URI, stripping header...")
                return image_input.split(",")[1]
                
            # Check if it looks like a file path
            if image_input.startswith("/") or image_input.startswith("file://"):
                logger.info(f"Reading local file: {image_input}")
                file_path = image_input.replace("file://", "")
                try:
                    import aiofiles
                    import base64
                    async with aiofiles.open(file_path, "rb") as f:
                        content = await f.read()
                        encoded = base64.b64encode(content).decode("utf-8")
                        logger.info(f"Encoded local file. Length: {len(encoded)}")
                        return encoded
                except ImportError:
                    # Fallback if aiofiles not installed
                    import base64
                    with open(file_path, "rb") as f:
                        content = f.read()
                        encoded = base64.b64encode(content).decode("utf-8")
                        logger.info(f"Encoded local file (sync). Length: {len(encoded)}")
                        return encoded
                except Exception as e:
                    logger.error(f"Failed to read local file: {e}")
                    raise Exception(f"Failed to read local file {image_input}: {e}")
            
            # Check if it's a gs:// URI (not supported directly here yet)
            if image_input.startswith("gs://"):
                logger.warning(f"gs:// URIs not supported for direct upload: {image_input}")
                raise Exception(f"gs:// URIs not supported. Please provide a URL or local path.")
            
            logger.info(f"Assuming input is raw base64. Length: {len(image_input)}")
            return image_input 
            
        try:
            image_data = await get_image_data(image_url)
            logger.info(f"Final image_data preview: {image_data[:50]}...")
            
            payload = {
                "image": image_data, 
                "prompt": prompt,
                "n": 1,
            }
            
            if mask_url:
                payload["mask"] = await get_image_data(mask_url)
                
        except Exception as e:
             return {
                "success": False,
                "error": f"Failed to prepare image data: {str(e)}",
                "data": []
            }
            
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Attempting edit at: {url}")
                logger.info(f"Request payload keys: {list(payload.keys())}")
                logger.info(f"Prompt: {prompt}")
                
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                
                if response.status_code == 404:
                    # Try fallback to deployment-specific path
                    logger.warning("Standard endpoint 404, trying deployment path...")
                    url = f"{self.endpoint}/openai/deployments/{self.deployment}/images/edits?api-version={self.api_version}"
                    logger.info(f"Attempting edit at: {url}")
                    
                    response = await client.post(
                        url,
                        headers=headers,
                        json=payload,
                        timeout=60.0
                    )
                 
                if response.status_code != 200:
                    logger.error(f"FLUX.1 Edit Error: {response.status_code}")
                    logger.error(f"Response body: {response.text}")
                    # If still 404, it likely means editing is not supported
                    if response.status_code == 404:
                        return {
                            "success": False, 
                            "error": "Image editing is not supported by this model endpoint.",
                            "data": []
                        }
                    return {
                        "success": False,
                        "error": f"FLUX.1 Edit API Error: {response.status_code} - {response.text}",
                        "data": []
                    }
                    
                response_data = response.json()
                logger.info(f"FLUX.1 Edit Response received")
                logger.debug(f"Full FLUX.1 Edit Response: {response_data}")
                
                # Add success flag for consistency
                if "success" not in response_data:
                    response_data["success"] = True
                    
                return response_data
            except httpx.RequestError as e:
                logger.error(f"Request error during edit: {e}")
                return {
                    "success": False,
                    "error": f"Network error: {str(e)}",
                    "data": []
                }
            except Exception as e:
                logger.error(f"Edit failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "data": []
                }

# Singleton
_flux_client: Optional[FluxClient] = None

def get_flux_client() -> FluxClient:
    global _flux_client
    if _flux_client is None:
        _flux_client = FluxClient()
    return _flux_client
