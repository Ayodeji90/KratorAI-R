from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from src.api.schemas.describe import DescribeResponse
from src.services.azure_vision_client import AzureVisionClient

router = APIRouter()

# Initialize Azure Vision client
vision_client = AzureVisionClient()

@router.post("/describe", response_model=DescribeResponse)
async def describe_design(
    file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None)
):
    """
    Generate a description for an uploaded design/work or a design URL using Azure Computer Vision.
    
    Returns:
        - description: Main description of the image
        - tags: List of detected visual elements
        - extracted_text: OCR text from the image (if any)
    """
    if not file and not image_url:
        raise HTTPException(status_code=400, detail="Either file or image_url must be provided")
    
    try:
        # Get image data if file was uploaded
        image_data = None
        if file:
            image_data = await file.read()
        
        # Analyze image using Azure Vision
        result = await vision_client.analyze_image(
            image_data=image_data,
            image_url=image_url
        )
        
        return DescribeResponse(
            description=result["description"],
            tags=result.get("tags", []),
            extracted_text=result.get("extracted_text", "")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze image: {str(e)}")
