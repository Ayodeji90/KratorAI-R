from pydantic import BaseModel, Field
from typing import Optional, List

class BusinessProfile(BaseModel):
    """Business profile information collected during onboarding."""
    business_name: Optional[str] = Field(None, description="Name of the business")
    industry: Optional[str] = Field(None, description="Industry or niche (e.g., Fashion, Food, Tech)")
    description: Optional[str] = Field(None, description="Short description of what the business does")
    target_audience: Optional[str] = Field(None, description="Who the business serves")
    brand_voice: Optional[str] = Field(None, description="Tone of voice (e.g., Professional, Playful, Luxury)")
    key_offerings: Optional[List[str]] = Field(default_factory=list, description="Main products or services")
    social_media_handles: Optional[List[str]] = Field(default_factory=list, description="Social media handles if mentioned")
    website: Optional[str] = Field(None, description="Website URL if mentioned")
    
    # Metadata
    onboarding_completed: bool = Field(False, description="Whether all essential info has been collected")
    confidence_score: float = Field(0.0, description="Confidence in the collected data")
