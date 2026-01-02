from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from src.api.schemas.describe import DescribeResponse

router = APIRouter()

@router.post("/describe", response_model=DescribeResponse)
async def describe_design(
    file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None)
):
    """
    Generate a brief description for an uploaded design/work or a design URL.
    
    NOTE: Image description is currently disabled as the system uses FLUX.1 (image-only).
    """
    if not file and not image_url:
        raise HTTPException(status_code=400, detail="Either file or image_url must be provided")

    # Return a static message since we don't have a vision model anymore
    return DescribeResponse(description="Image description is not supported with the current FLUX.1 model configuration.")
