"""Design editing endpoint."""

from fastapi import APIRouter, HTTPException
from uuid import uuid4

from src.api.schemas import EditRequest, GeneratedAsset
from src.services.editing import EditingService


router = APIRouter()
editing_service = EditingService()


@router.post("/", response_model=GeneratedAsset)
async def edit_design(request: EditRequest):
    """
    Apply targeted edits to a design.
    
    Supports inpainting, style transfer, and color manipulation
    while ensuring outputs remain culturally resonant.
    """
    try:
        result = await editing_service.edit(
            image_uri=request.image_uri,
            mask_uri=request.mask_uri,
            prompt=request.prompt,
            edit_type=request.edit_type,
        )
        
        source_id = str(uuid4())  # TODO: Extract from request metadata
        
        return GeneratedAsset(
            asset_id=str(uuid4()),
            asset_uri=result["asset_uri"],
            thumbnail_uri=result.get("thumbnail_uri"),
            parent_ids=[source_id],
            royalties=[],
            metadata={
                "prompt": request.prompt,
                "edit_type": request.edit_type,
                "has_mask": request.mask_uri is not None,
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Editing failed: {str(e)}")


@router.post("/inpaint", response_model=GeneratedAsset)
async def inpaint_design(image_uri: str, mask_uri: str, prompt: str):
    """Convenience endpoint for inpainting."""
    request = EditRequest(
        image_uri=image_uri,
        mask_uri=mask_uri,
        prompt=prompt,
        edit_type="inpaint",
    )
    return await edit_design(request)


@router.post("/style-transfer", response_model=GeneratedAsset)
async def style_transfer(image_uri: str, style_prompt: str):
    """Convenience endpoint for style transfer."""
    request = EditRequest(
        image_uri=image_uri,
        prompt=style_prompt,
        edit_type="style_transfer",
    )
    return await edit_design(request)
