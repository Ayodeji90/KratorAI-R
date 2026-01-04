"""
Refactored Azure Computer Vision client for structured visual perception.
Returns structured JSON only - NO human-friendly descriptions.
"""

import io
import asyncio
from typing import Optional
from PIL import Image
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials
from src.config import get_settings


class AzureVisionClient:
    """Client for Azure Computer Vision - Pure Visual Perception."""
    
    def __init__(self):
        """Initialize the Azure Computer Vision client."""
        settings = get_settings()
        
        if not settings.azure_vision_endpoint or not settings.azure_vision_key:
            self.client = None
            self.enabled = False
        else:
            credentials = CognitiveServicesCredentials(settings.azure_vision_key)
            self.client = ComputerVisionClient(settings.azure_vision_endpoint, credentials)
            self.enabled = True
    
    async def extract_visual_data(
        self,
        image_data: Optional[bytes] = None,
        image_url: Optional[str] = None
    ) -> dict:
        """
        Extract structured visual data from an image.
        
        Returns ONLY structured JSON - NO human-friendly descriptions.
        
        Args:
            image_data: Image file as bytes
            image_url: URL to the image
            
        Returns:
            Structured dictionary containing:
                - image_size: "widthxheight"
                - layout: "portrait" | "landscape" | "square"
                - text_density: "high" | "medium" | "low" | "none"
                - text_blocks: List of {text, bounding_box, confidence}
                - basic_tags: List of simple visual tags
                - has_images: Boolean
                - dominant_colors: List of hex colors
        """
        if not self.enabled:
            return {
                "error": "Azure Vision is not configured",
                "image_size": "unknown",
                "layout": "unknown",
                "text_density": "unknown",
                "text_blocks": [],
                "basic_tags": [],
                "has_images": False,
                "dominant_colors": []
            }
        
        try:
            # Get image dimensions
            image_size, layout = self._get_image_dimensions(image_data, image_url)
            
            # Define features for analysis
            features = [
                VisualFeatureTypes.tags,
                VisualFeatureTypes.color,
                VisualFeatureTypes.image_type
            ]
            
            # Analyze image
            if image_url:
                analysis = self.client.analyze_image(image_url, visual_features=features)
            elif image_data:
                image_stream = io.BytesIO(image_data)
                analysis = self.client.analyze_image_in_stream(image_stream, visual_features=features)
            else:
                return {
                    "error": "No image provided",
                    "image_size": "unknown",
                    "layout": "unknown",
                    "text_density": "unknown",
                    "text_blocks": [],
                    "basic_tags": [],
                    "has_images": False,
                    "dominant_colors": []
                }
            
            # Extract basic visual tags (no reasoning, just facts)
            basic_tags = self._extract_basic_tags(analysis.tags) if analysis.tags else []
            
            # Extract dominant colors
            dominant_colors = []
            if analysis.color:
                dominant_colors = analysis.color.dominant_colors or []
            
            # Check if image contains photos/clipart
            has_images = False
            if analysis.image_type:
                has_images = (
                    analysis.image_type.clip_art_type > 0 or 
                    analysis.image_type.line_drawing_type == 0
                )
            
            # Extract OCR text with bounding boxes
            text_blocks = await self._extract_text_blocks(image_data, image_url)
            
            # Calculate text density
            text_density = self._calculate_text_density(text_blocks, image_size)
            
            return {
                "image_size": image_size,
                "layout": layout,
                "text_density": text_density,
                "text_blocks": text_blocks,
                "basic_tags": basic_tags,
                "has_images": has_images,
                "dominant_colors": dominant_colors
            }
            
        except Exception as e:
            print(f"Azure Vision extraction error: {e}")
            return {
                "error": str(e),
                "image_size": "unknown",
                "layout": "unknown",
                "text_density": "unknown",
                "text_blocks": [],
                "basic_tags": [],
                "has_images": False,
                "dominant_colors": []
            }
    
    def _get_image_dimensions(
        self, 
        image_data: Optional[bytes],
        image_url: Optional[str]
    ) -> tuple[str, str]:
        """Get image dimensions and layout orientation."""
        try:
            if image_data:
                img = Image.open(io.BytesIO(image_data))
                width, height = img.size
            elif image_url:
                import requests
                response = requests.get(image_url, timeout=5)
                img = Image.open(io.BytesIO(response.content))
                width, height = img.size
            else:
                return "unknown", "unknown"
            
            # Determine layout
            if width > height * 1.2:
                layout = "landscape"
            elif height > width * 1.2:
                layout = "portrait"
            else:
                layout = "square"
            
            return f"{width}x{height}", layout
            
        except Exception as e:
            print(f"Failed to get image dimensions: {e}")
            return "unknown", "unknown"
    
    def _extract_basic_tags(self, tags) -> list[str]:
        """Extract only factual visual tags (no interpretation)."""
        # Filter for high-confidence tags
        basic_tags = []
        for tag in tags:
            if tag.confidence > 0.7:
                # Only include simple, factual tags
                tag_name = tag.name.lower()
                if tag_name in [
                    "text", "poster", "flyer", "design", "graphic",
                    "colorful", "minimal", "professional", "modern",
                    "vintage", "abstract", "geometric", "pattern"
                ]:
                    basic_tags.append(tag_name)
        
        return basic_tags[:10]  # Limit to top 10
    
    async def _extract_text_blocks(
        self,
        image_data: Optional[bytes],
        image_url: Optional[str]
    ) -> list[dict]:
        """Extract OCR text with bounding boxes."""
        text_blocks = []
        
        try:
            # Use Read API for OCR
            if image_url:
                read_result = self.client.read(image_url, raw=True)
            elif image_data:
                image_stream = io.BytesIO(image_data)
                read_result = self.client.read_in_stream(image_stream, raw=True)
            else:
                return []
            
            # Get operation location
            operation_location = read_result.headers["Operation-Location"]
            operation_id = operation_location.split("/")[-1]
            
            # Wait for operation to complete (with timeout)
            max_wait = 5  # 5 second max wait
            wait_count = 0
            
            while wait_count < max_wait:
                result = self.client.get_read_result(operation_id)
                if result.status.lower() not in ['notstarted', 'running']:
                    break
                await asyncio.sleep(1)
                wait_count += 1
            
            # Extract text and bounding boxes
            if result.analyze_result:
                for page in result.analyze_result.read_results:
                    for line in page.lines:
                        # Get bounding box
                        bbox = line.bounding_box  # [x1, y1, x2, y2...]
                        if len(bbox) >= 8:
                            # Convert to [x, y, width, height]
                            x = min(bbox[0], bbox[6])
                            y = min(bbox[1], bbox[3])
                            width = max(bbox[2], bbox[4]) - x
                            height = max(bbox[5], bbox[7]) - y
                            
                            text_blocks.append({
                                "text": line.text,
                                "bounding_box": [int(x), int(y), int(width), int(height)],
                                "confidence": 0.95  # Read API doesn't return per-line confidence
                            })
        
        except Exception as e:
            print(f"OCR extraction failed: {e}")
        
        return text_blocks
    
    def _calculate_text_density(self, text_blocks: list[dict], image_size: str) -> str:
        """Calculate text density based on number of text blocks."""
        if not text_blocks:
            return "none"
        
        num_blocks = len(text_blocks)
        total_chars = sum(len(block["text"]) for block in text_blocks)
        
        # Calculate density based on character count
        if total_chars > 200 or num_blocks > 10:
            return "high"
        elif total_chars > 50 or num_blocks > 3:
            return "medium"
        elif total_chars > 0:
            return "low"
        else:
            return "none"
