"""
Blend Tool - Combines multiple designs using ControlNet + IP-Adapter.
"""

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional


class BlendInput(BaseModel):
    """Input schema for blend tool."""
    image_uris: list[str] = Field(..., description="List of image URIs to blend")
    weights: list[float] = Field(default=None, description="Blend weights for each image")
    prompt: Optional[str] = Field(None, description="Additional styling prompt")
    preserve_structure: bool = Field(default=True, description="Preserve structural elements")


class BlendTool(BaseTool):
    """
    Tool for blending multiple designs into a hybrid.
    
    Uses ControlNet for structure preservation and IP-Adapter
    for style blending, creating harmonious combinations of
    African design elements.
    """
    
    name: str = "blend_designs"
    description: str = """
    Blend multiple designs together to create a hybrid. 
    Useful for combining Adinkra patterns with Kente motifs,
    mixing color schemes, or creating novel variations.
    
    Input: List of image URIs with optional weights and prompt.
    Output: URI of the blended design.
    """
    args_schema: type[BaseModel] = BlendInput
    
    def _run(
        self,
        image_uris: list[str],
        weights: list[float] | None = None,
        prompt: str | None = None,
        preserve_structure: bool = True,
    ) -> dict:
        """Synchronous blend execution."""
        # Normalize weights
        if weights is None:
            weights = [1.0 / len(image_uris)] * len(image_uris)
        else:
            total = sum(weights)
            weights = [w / total for w in weights]
        
        # TODO: Implement actual blending with ControlNet + IP-Adapter
        # Placeholder response
        return {
            "status": "success",
            "asset_uri": "gs://kratorai-assets/blended/placeholder.png",
            "blend_weights": dict(zip(image_uris, weights)),
            "prompt_used": prompt,
        }
    
    async def _arun(
        self,
        image_uris: list[str],
        weights: list[float] | None = None,
        prompt: str | None = None,
        preserve_structure: bool = True,
    ) -> dict:
        """Async blend execution."""
        return self._run(image_uris, weights, prompt, preserve_structure)
