"""Design refining endpoint."""

import os
import tempfile
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from uuid import uuid4

from src.api.schemas import RefineRequest, GeneratedAsset, VariationResponse
from src.services.refining import RefiningService
from src.services.pipeline_orchestrator import get_pipeline_orchestrator
from src.security.auth import verify_token
from src.security.validators import validate_prompt, validate_image_upload, validate_strength, validate_num_variations


router = APIRouter()
refining_service = RefiningService()
pipeline = get_pipeline_orchestrator()


@router.post("/", response_model=VariationResponse, dependencies=[Depends(verify_token)])
async def refine_design(request: RefineRequest):
    """
    Generate refined variations of a design based on a prompt.
    
    **Authentication Required**: Bearer token must be provided in Authorization header.
    
    NEW: User prompts are refined by o3-mini before FLUX generation.
    
    Enhances existing templates while maintaining structural integrity
    and adapting to cultural or thematic nuances.
    """
    try:
        # Validate inputs
        validate_prompt(request.prompt)
        validate_strength(request.strength)
        validate_num_variations(request.num_variations)
        # Refine the prompt using o3-mini (extract vision data from image_uri)
        # Note: For URI-based requests, we handle refinement inside the service
        # This endpoint will be enhanced when we add full support for URI-based refinement
        
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


@router.post("/upload", response_model=VariationResponse, dependencies=[Depends(verify_token)])
async def refine_uploaded_design(
    file: Optional[UploadFile] = File(None, description="Main image file to refine"),
    files: Optional[list[UploadFile]] = File(None, description="Additional reference images (logos, etc.)"),
    image_url: Optional[str] = Form(None, description="URL of image to refine"),
    prompt: str = Form(default="Enhance this design with vibrant African patterns"),
    strength: float = Form(default=0.7, ge=0.1, le=1.0),
    num_variations: int = Form(default=3, ge=1, le=5),
):
    """
    Upload an image and generate refined variations.
    
    **Authentication Required**: Bearer token must be provided in Authorization header.
    
    NEW: Prompts are refined using o3-mini before FLUX generation.
    Supports multiple reference images (logos, assets) to be incorporated.
    """
    if not file and not image_url:
        raise HTTPException(status_code=400, detail="Either file or image_url must be provided")
    
    # Validate inputs
    validate_prompt(prompt)
    validate_strength(strength)
    validate_num_variations(num_variations)
    if file:
        await validate_image_upload(file)
    if files:
        for f in files:
            await validate_image_upload(f)

    try:
        temp_path = None
        image_data = None
        reference_images_data = []
        
        if file:
            # Validate file type
            if not file.content_type or not file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
                
            # Read file data for pipeline
            image_data = await file.read()
            
            # Save uploaded file temporarily for FLUX
            temp_dir = Path(tempfile.gettempdir()) / "kratorai_uploads"
            temp_dir.mkdir(exist_ok=True)
            
            file_ext = Path(file.filename or "upload.png").suffix or ".png"
            temp_path = temp_dir / f"{uuid4()}{file_ext}"
            temp_path.write_bytes(image_data)
            image_uri = str(temp_path)
        else:
            image_uri = image_url

        # Read reference images
        if files:
            for f in files:
                ref_data = await f.read()
                reference_images_data.append(ref_data)
        
        try:
            # STAGE 1 & 2: Refine the prompt using the pipeline
            refinement_result = await pipeline.process_refinement_request(
                user_prompt=prompt,
                image_data=image_data,
                image_url=image_url,
                reference_images_data=reference_images_data
            )
            
            refined_prompt = refinement_result["refined_prompt"]
            prompt_refinement = refinement_result["prompt_refinement"]
            
            print(f"Original prompt: {prompt}")
            print(f"Refined prompt: {refined_prompt}")
            
            # STAGE 3: Process the image with FLUX using refined prompt
            variations = await refining_service.refine(
                image_uri=image_uri,
                prompt=refined_prompt,  # Use refined prompt instead of original
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
                        "original_prompt": prompt,
                        "refined_prompt": refined_prompt,
                        "strength": strength,
                        "variation_index": i,
                        "original_filename": file.filename if file else None,
                    }
                )
                for i, var in enumerate(variations)
            ]
            
            return VariationResponse(
                source_id=source_id,
                variations=generated_assets,
                prompt_refinement=prompt_refinement  # Include refinement details
            )
        
        finally:
            # Clean up temp file
            if temp_path and temp_path.exists():
                temp_path.unlink()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refining failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Refining failed: {str(e)}")
