from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from src.api.schemas.describe import DescribeResponse
from src.services.pipeline_orchestrator import get_pipeline_orchestrator
from src.security.auth import verify_token
from src.security.validators import validate_image_upload

router = APIRouter()

# Initialize pipeline orchestrator
pipeline = get_pipeline_orchestrator()

@router.post("/describe", response_model=DescribeResponse, dependencies=[Depends(verify_token)])
async def describe_design(
    file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None)
):
    """
    Generate a comprehensive design description using multi-stage AI pipeline.
    
    **Authentication Required**: Bearer token must be provided in Authorization header.
    
    Pipeline:
    1. Azure Vision AI: Extracts structured visual data (OCR, layout, colors)
    2. o3-mini: Reasons over visual data to generate description and analysis
    
    Returns:
        - description: Human-readable design description
        - category: Design type classification 
        - style: Style tags
        - editable_elements: Suggested editable elements
        - design_quality: Quality assessment
        - target_audience: Inferred audience
        - vision_data: Raw visual extraction data
        - source: "vision+o3-mini"
    """
    if not file and not image_url:
        raise HTTPException(status_code=400, detail="Either file or image_url must be provided")
    
    # Validate file upload if provided
    if file:
        await validate_image_upload(file)
    
    try:
        # Get image data if file was uploaded
        image_data = None
        if file:
            image_data = await file.read()
        
        # Run through multi-stage pipeline
        result = await pipeline.process_design_upload(
            image_data=image_data,
            image_url=image_url
        )
        
        return DescribeResponse(
            description=result.get("description", "No description available"),
            category=result.get("category", "Posters & Flyers"),
            category_id=result.get("category_id", "691cce9dd92ef6f4ab51"),
            style=result.get("style", []),
            editable_elements=result.get("editable_elements", []),
            design_quality=result.get("design_quality", "unknown"),
            target_audience=result.get("target_audience", "unknown"),
            vision_data=result.get("vision_data", result),  # Include vision data
            source=result.get("source", "vision+o3-mini")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze image: {str(e)}")

