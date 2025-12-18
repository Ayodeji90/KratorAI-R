"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional


class ImageInput(BaseModel):
    """Single image input with optional weight."""
    uri: str = Field(..., description="GCS URI or URL of the image")
    weight: float = Field(default=0.5, ge=0.0, le=1.0, description="Blend weight (0-1)")


class BreedRequest(BaseModel):
    """Request schema for design breeding."""
    images: list[ImageInput] = Field(..., min_length=2, max_length=5, description="Images to breed")
    prompt: Optional[str] = Field(None, description="Additional styling prompt")
    preserve_cultural_elements: bool = Field(default=True, description="Prioritize African motifs")


class RefineRequest(BaseModel):
    """Request schema for design refining."""
    image_uri: str = Field(..., description="Source image URI")
    prompt: str = Field(..., description="Refinement instructions (e.g., 'infuse Lagos street vibes')")
    strength: float = Field(default=0.7, ge=0.1, le=1.0, description="Refinement intensity")
    num_variations: int = Field(default=3, ge=1, le=5, description="Number of variations to generate")


class EditRequest(BaseModel):
    """Request schema for targeted editing."""
    image_uri: str = Field(..., description="Source image URI")
    mask_uri: Optional[str] = Field(None, description="Mask image URI for inpainting")
    prompt: str = Field(..., description="Edit instructions")
    edit_type: str = Field(default="inpaint", description="Edit type: inpaint, style_transfer, color_swap")


class RoyaltyShare(BaseModel):
    """Royalty share for a parent design."""
    design_id: str
    owner_id: str
    share_percentage: float


class GeneratedAsset(BaseModel):
    """Response schema for generated assets."""
    asset_id: str
    asset_uri: str
    thumbnail_uri: Optional[str] = None
    parent_ids: list[str] = []
    royalties: list[RoyaltyShare] = []
    metadata: dict = {}


class VariationResponse(BaseModel):
    """Response for refinement variations."""
    source_id: str
    variations: list[GeneratedAsset]
