"""Pipeline orchestrator - coordinates multi-stage AI processing."""

import hashlib
import asyncio
from typing import Optional, Dict, List
from src.services.azure_vision_client import AzureVisionClient
from src.services.reasoning_service import get_reasoning_service
from src.services.prompt_refinement_service import get_prompt_refinement_service


class PipelineOrchestrator:
    """Orchestrates the multi-stage AI pipeline."""
    
    def __init__(self):
        self.vision_client = AzureVisionClient()
        self.reasoning_service = get_reasoning_service()
        self.prompt_refinement_service = get_prompt_refinement_service()
        
        # Simple in-memory cache (can be replaced with Redis in production)
        self.vision_cache: Dict[str, dict] = {}
        self.cache_ttl = 3600  # 1 hour
    
    async def process_design_upload(
        self,
        image_data: Optional[bytes] = None,
        image_url: Optional[str] = None
    ) -> dict:
        """
        Process a design upload through the full pipeline.
        
        Stages:
        1. Azure Vision: Extract visual data
        2. o3-mini: Generate description and analysis
        
        Args:
            image_data: Image as bytes
            image_url: Image URL
            
        Returns:
            Combined vision + reasoning data
        """
        try:
            # Stage 1: Vision Perception
            vision_data = await self._get_vision_data(image_data, image_url)
            
            # Check for errors
            if "error" in vision_data and vision_data.get("text_blocks") is None:
                return {
                    **vision_data,
                    "description": f"Vision analysis failed: {vision_data['error']}",
                    "category": "Posters & Flyers",
                    "category_id": "691cce9dd92ef6f4ab51",
                    "style": [],
                    "editable_elements": []
                }
            
            # Stage 2: Reasoning & Description
            description_data = await self.reasoning_service.generate_design_description(vision_data)
            
            # Combine both stages
            return {
                **vision_data,
                **description_data
            }
            
        except Exception as e:
            print(f"Pipeline error in process_design_upload: {e}")
            return {
                "error": str(e),
                "description": f"Pipeline processing failed: {str(e)}",
                "category": "Posters & Flyers",
                "category_id": "691cce9dd92ef6f4ab51",
                "style": [],
                "editable_elements": []
            }
    
    async def process_refinement_request(
        self,
        user_prompt: str,
        image_data: Optional[bytes] = None,
        image_url: Optional[str] = None,
        reference_images_data: Optional[list[bytes]] = None
    ) -> dict:
        """
        Process a refinement request with prompt refinement.
        
        Stages:
        1. Azure Vision: Extract visual data for main image
        2. Azure Vision: Extract visual data for reference images (logos, etc.)
        3. o3-mini: Refine user prompt incorporating reference assets
        
        Args:
            user_prompt: User's original prompt
            image_data: Main image as bytes
            image_url: Main image URL
            reference_images_data: List of reference images as bytes
            
        Returns:
            Dictionary with vision_data and refinement details
        """
        try:
            # Stage 1: Main Image Vision Perception
            vision_data = await self._get_vision_data(image_data, image_url)
            
            # Stage 2: Reference Images Vision Perception
            reference_assets = []
            if reference_images_data:
                for i, ref_data in enumerate(reference_images_data):
                    ref_vision = await self.vision_client.extract_visual_data(image_data=ref_data)
                    # Get a simple description for each reference asset
                    ref_desc = await self.reasoning_service.generate_design_description(ref_vision)
                    reference_assets.append({
                        "id": f"asset_{i+1}",
                        "category": ref_desc.get("category", "asset"),
                        "description": ref_desc.get("description", "A reference visual asset"),
                        "vision_data": ref_vision
                    })
            
            # Stage 3: Prompt Refinement
            refinement_data = await self.prompt_refinement_service.refine_user_prompt(
                user_prompt=user_prompt,
                vision_data=vision_data,
                reference_assets=reference_assets
            )
            
            return {
                "vision_data": vision_data,
                "reference_assets": reference_assets,
                "prompt_refinement": refinement_data,
                "refined_prompt": refinement_data["refined_prompt"]
            }
            
        except Exception as e:
            print(f"Pipeline error in process_refinement_request: {e}")
            return {
                "vision_data": {},
                "reference_assets": [],
                "prompt_refinement": {
                    "original_prompt": user_prompt,
                    "refined_prompt": user_prompt,
                    "refinement_rationale": f"Refinement failed: {str(e)}",
                    "detected_intent": "unknown",
                    "preserved_elements": []
                },
                "refined_prompt": user_prompt
            }
    
    async def _get_vision_data(
        self,
        image_data: Optional[bytes],
        image_url: Optional[str]
    ) -> dict:
        """Get vision data with caching."""
        # Generate cache key
        cache_key = self._generate_cache_key(image_data, image_url)
        
        # Check cache
        if cache_key in self.vision_cache:
            print(f"Vision cache HIT for key: {cache_key[:16]}...")
            return self.vision_cache[cache_key]
        
        # Cache miss - extract vision data
        print(f"Vision cache MISS for key: {cache_key[:16]}...")
        vision_data = await self.vision_client.extract_visual_data(
            image_data=image_data,
            image_url=image_url
        )
        
        # Store in cache
        self.vision_cache[cache_key] = vision_data
        
        # Simple cache cleanup (remove if cache gets too large)
        if len(self.vision_cache) > 100:
            # Remove oldest entries (first 20)
            keys_to_remove = list(self.vision_cache.keys())[:20]
            for key in keys_to_remove:
                del self.vision_cache[key]
        
        return vision_data
    
    def _generate_cache_key(
        self,
        image_data: Optional[bytes],
        image_url: Optional[str]
    ) -> str:
        """Generate a cache key for an image."""
        if image_data:
            # Hash the image bytes
            return hashlib.md5(image_data).hexdigest()
        elif image_url:
            # Hash the URL
            return hashlib.md5(image_url.encode()).hexdigest()
        return "no_image"


# Singleton
_pipeline_orchestrator = None

def get_pipeline_orchestrator() -> PipelineOrchestrator:
    """Get the singleton pipeline orchestrator."""
    global _pipeline_orchestrator
    if _pipeline_orchestrator is None:
        _pipeline_orchestrator = PipelineOrchestrator()
    return _pipeline_orchestrator
