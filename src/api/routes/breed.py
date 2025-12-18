"""Design breeding endpoint."""

from fastapi import APIRouter, HTTPException
from uuid import uuid4

from src.api.schemas import BreedRequest, GeneratedAsset, RoyaltyShare
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
