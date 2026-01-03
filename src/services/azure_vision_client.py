"""Azure Computer Vision service client for image analysis."""

import io
from typing import Optional
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials
from src.config import get_settings


class AzureVisionClient:
    """Client for Azure Computer Vision image analysis."""
    
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
    
    async def analyze_image(
        self,
        image_data: Optional[bytes] = None,
        image_url: Optional[str] = None
    ) -> dict:
        """
        Analyze an image using Azure Computer Vision.
        
        Args:
            image_data: Image file as bytes
            image_url: URL to the image
            
        Returns:
            Dictionary containing:
                - description: Main description of the image
                - tags: List of detected visual tags
                - extracted_text: OCR text from the image (if any)
        """
        if not self.enabled:
            return {
                "description": "Azure Vision is not configured. Please add AZURE_VISION_ENDPOINT and AZURE_VISION_KEY to your .env file.",
                "tags": [],
                "extracted_text": ""
            }
        
        try:
            # Define features to analyze
            features = [
                VisualFeatureTypes.description,
                VisualFeatureTypes.tags,
                VisualFeatureTypes.objects
            ]
            
            # Analyze image
            if image_url:
                analysis = self.client.analyze_image(image_url, visual_features=features)
            elif image_data:
                image_stream = io.BytesIO(image_data)
                analysis = self.client.analyze_image_in_stream(image_stream, visual_features=features)
            else:
                return {
                    "description": "No image provided for analysis.",
                    "tags": [],
                    "extracted_text": ""
                }
            
            # Extract description
            description = ""
            if analysis.description and analysis.description.captions:
                # Get the caption with highest confidence
                best_caption = max(analysis.description.captions, key=lambda x: x.confidence)
                description = best_caption.text.capitalize()
            
            # Extract tags
            tags = []
            if analysis.tags:
                # Get tags with confidence > 0.5
                tags = [tag.name for tag in analysis.tags if tag.confidence > 0.5]
            
            # Try to extract text using OCR (Read API)
            extracted_text = ""
            try:
                if image_url:
                    read_result = self.client.read(image_url, raw=True)
                elif image_data:
                    image_stream = io.BytesIO(image_data)
                    read_result = self.client.read_in_stream(image_stream, raw=True)
                else:
                    read_result = None
                
                if read_result:
                    # Get operation location
                    operation_location = read_result.headers["Operation-Location"]
                    operation_id = operation_location.split("/")[-1]
                    
                    # Wait for the operation to complete
                    import time
                    while True:
                        result = self.client.get_read_result(operation_id)
                        if result.status.lower() not in ['notstarted', 'running']:
                            break
                        time.sleep(1)
                    
                    # Extract text
                    if result.analyze_result:
                        text_lines = []
                        for page in result.analyze_result.read_results:
                            for line in page.lines:
                                text_lines.append(line.text)
                        extracted_text = " ".join(text_lines)
            except Exception as ocr_error:
                # OCR is optional, don't fail if it doesn't work
                print(f"OCR extraction failed: {ocr_error}")
            
            return {
                "description": description or "Unable to generate a description for this image.",
                "tags": tags,
                "extracted_text": extracted_text
            }
            
        except Exception as e:
            print(f"Azure Vision analysis error: {e}")
            return {
                "description": f"Failed to analyze image: {str(e)}",
                "tags": [],
                "extracted_text": ""
            }
