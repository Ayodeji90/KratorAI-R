"""Design breeding endpoint."""

import tempfile
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from uuid import uuid4

from src.api.schemas import BreedRequest, GeneratedAsset, RoyaltyShare, ImageInput
from src.services.breeding import BreedingService
from src.lineage.royalty_graph import RoyaltyGraph


router = APIRouter()
breeding_service = BreedingService()
royalty_graph = RoyaltyGraph()


@router.post("/", response_model=GeneratedAsset)
async def breed_designs(request: BreedRequest):
    """
    Breed multiple designs together to create a hybrid asset.
    
    Combines visual "DNA" from input designs proportionally based on weights,
    generating novel designs while maintaining cultural authenticity.
    """
    try:
        # Generate bred design
        result = await breeding_service.breed(
            images=[(img.uri, img.weight) for img in request.images],
            prompt=request.prompt,
            preserve_cultural=request.preserve_cultural_elements,
        )
        
        # Generate unique ID for new asset
        asset_id = str(uuid4())
        parent_ids = [f"parent_{i}" for i in range(len(request.images))]  # TODO: Extract from metadata
        
        # Compute royalty shares from lineage graph
        royalties = royalty_graph.compute_shares(parent_ids, request.images)
        
        return GeneratedAsset(
            asset_id=asset_id,
            asset_uri=result["asset_uri"],
            thumbnail_uri=result.get("thumbnail_uri"),
            parent_ids=parent_ids,
            royalties=royalties,
            metadata={
                "prompt": request.prompt,
                "preserve_cultural": request.preserve_cultural_elements,
                "generation_model": "gemini",
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Breeding failed: {str(e)}")


@router.post("/multi", response_model=list[GeneratedAsset])
async def breed_multiple(requests: list[BreedRequest]):
    """Batch breed multiple design combinations."""
    results = []
    for req in requests:
        result = await breed_designs(req)
        results.append(result)
    return results


@router.post("/upload", response_model=GeneratedAsset)
async def breed_uploaded_designs(
    files: Optional[List[UploadFile]] = File(None, description="Image files to breed"),
    image_urls: Optional[List[str]] = Form(None, description="URLs of images to breed"),
    prompt: Optional[str] = Form(None, description="Additional styling prompt"),
    preserve_cultural: bool = Form(default=True, description="Prioritize African motifs"),
):
    """
    Upload multiple images or provide URLs to breed them together.
    
    This endpoint accepts multipart form data for direct file uploads and URLs.
    """
    # Collect all image URIs
    image_inputs = []
    temp_paths = []
    
    try:
        # Handle file uploads
        if files:
            temp_dir = Path(tempfile.gettempdir()) / "kratorai_breeding"
            temp_dir.mkdir(exist_ok=True)
            
            for file in files:
                if not file.content_type or not file.content_type.startswith("image/"):
                    continue
                
                file_ext = Path(file.filename or "upload.png").suffix or ".png"
                temp_path = temp_dir / f"{uuid4()}{file_ext}"
                
                content = await file.read()
                temp_path.write_bytes(content)
                temp_paths.append(temp_path)
                
                # Default weight is 1.0 / total count (will be normalized in service)
                image_inputs.append(ImageInput(uri=str(temp_path), weight=0.5))
        
        # Handle image URLs
        if image_urls:
            for url in image_urls:
                image_inputs.append(ImageInput(uri=url, weight=0.5))
        
        if len(image_inputs) < 2:
            raise HTTPException(status_code=400, detail="At least two images (files or URLs) are required for breeding")
        
        # Create a BreedRequest-like call to the service
        result = await breeding_service.breed(
            images=[(img.uri, img.weight) for img in image_inputs],
            prompt=prompt,
            preserve_cultural=preserve_cultural,
        )
        
        # Generate unique ID for new asset
        asset_id = str(uuid4())
        parent_ids = [f"parent_{i}" for i in range(len(image_inputs))]
        
        # Compute royalty shares
        royalties = royalty_graph.compute_shares(parent_ids, image_inputs)
        
        return GeneratedAsset(
            asset_id=asset_id,
            asset_uri=result["asset_uri"],
            thumbnail_uri=result.get("thumbnail_uri"),
            parent_ids=parent_ids,
            royalties=royalties,
            metadata={
                "prompt": prompt,
                "preserve_cultural": preserve_cultural,
                "generation_model": "gemini",
                "input_count": len(image_inputs)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Breeding failed: {str(e)}")
    finally:
        # Clean up temp files
        for path in temp_paths:
            if path.exists():
                path.unlink()
