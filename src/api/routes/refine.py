"""Design refining endpoint."""

import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from uuid import uuid4

from src.api.schemas import RefineRequest, GeneratedAsset, VariationResponse
from src.services.refining import RefiningService


router = APIRouter()
refining_service = RefiningService()


@router.post("/", response_model=VariationResponse)
async def refine_design(request: RefineRequest):
    """
    Generate refined variations of a design based on a prompt.
    
    Enhances existing templates while maintaining structural integrity
    and adapting to cultural or thematic nuances.
    """
    try:
        variations = await refining_service.refine(
            image_uri=request.image_uri,
            prompt=request.prompt,
            strength=request.strength,
            num_variations=request.num_variations,
        )
        
        source_id = str(uuid4())  # TODO: Extract from request metadata
        
        generated_assets = [
            GeneratedAsset(
                asset_id=str(uuid4()),
                asset_uri=var["asset_uri"],
                thumbnail_uri=var.get("thumbnail_uri"),
                parent_ids=[source_id],
                royalties=[],
                metadata={
                    "prompt": request.prompt,
                    "strength": request.strength,
                    "variation_index": i,
                }
            )
            for i, var in enumerate(variations)
        ]
        
        return VariationResponse(
            source_id=source_id,
            variations=generated_assets,
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refining failed: {str(e)}")


@router.post("/upload", response_model=VariationResponse)
async def refine_uploaded_design(
    file: Optional[UploadFile] = File(None, description="Image file to refine"),
    image_url: Optional[str] = Form(None, description="URL of image to refine"),
    prompt: str = Form(default="Enhance this design with vibrant African patterns"),
    strength: float = Form(default=0.7, ge=0.1, le=1.0),
    num_variations: int = Form(default=3, ge=1, le=5),
):
    """
    Upload an image and generate refined variations.
    
    This endpoint accepts multipart form data for direct file uploads,
    making it easy to integrate with web UIs.
    """
    if not file and not image_url:
        raise HTTPException(status_code=400, detail="Either file or image_url must be provided")

    try:
        temp_path = None
        if file:
            # Validate file type
            if not file.content_type or not file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
                
            # Save uploaded file temporarily
            temp_dir = Path(tempfile.gettempdir()) / "kratorai_uploads"
            temp_dir.mkdir(exist_ok=True)
            
            file_ext = Path(file.filename or "upload.png").suffix or ".png"
            temp_path = temp_dir / f"{uuid4()}{file_ext}"
            
            content = await file.read()
            temp_path.write_bytes(content)
            image_uri = str(temp_path)
        else:
            image_uri = image_url
        
        try:
            # Process the image
            variations = await refining_service.refine(
                image_uri=image_uri,
                prompt=prompt,
                strength=strength,
                num_variations=num_variations,
            )
            
            source_id = str(uuid4())
            
            generated_assets = [
                GeneratedAsset(
                    asset_id=str(uuid4()),
                    asset_uri=var["asset_uri"],
                    thumbnail_uri=var.get("thumbnail_uri"),
                    parent_ids=[source_id],
                    royalties=[],
                    metadata={
                        "prompt": prompt,
                        "strength": strength,
                        "variation_index": i,
                        "original_filename": file.filename,
                    }
                )
                for i, var in enumerate(variations)
            ]
            
            return VariationResponse(
                source_id=source_id,
                variations=generated_assets,
            )
        
        finally:
            # Clean up temp file
            if temp_path and temp_path.exists():
                temp_path.unlink()
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refining failed: {str(e)}")
