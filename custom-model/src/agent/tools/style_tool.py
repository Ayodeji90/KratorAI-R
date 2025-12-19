"""
Style Tool - Style transfer using IP-Adapter for African aesthetics.
"""

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional


class StyleInput(BaseModel):
    """Input schema for style tool."""
    image_uri: str = Field(..., description="Source image URI")
    style_reference: Optional[str] = Field(None, description="Style reference image URI")
    style_prompt: Optional[str] = Field(None, description="Style description prompt")
    style_strength: float = Field(default=0.7, ge=0.1, le=1.0, description="Style transfer intensity")
    preserve_content: bool = Field(default=True, description="Preserve original content structure")


class StyleTool(BaseTool):
    """
    Tool for applying style transfers to designs.
    
    Uses IP-Adapter for reference-based style transfer,
    allowing designers to apply specific African aesthetic
    styles (e.g., Adinkra, Kente, Ankara) to their work.
    """
    
    name: str = "apply_style"
    description: str = """
    Apply a style transformation to a design.
    Can use a reference image or text prompt to define the style.
    Great for applying cultural aesthetics like:
    - Adinkra symbols and patterns
    - Kente weaving motifs
    - Ankara/African wax print styles
    - Traditional color palettes
    
    Input: Content image, style reference or prompt.
    Output: URI of the stylized design.
    """
    args_schema: type[BaseModel] = StyleInput
    
    # African style presets
    STYLE_PRESETS = {
        "adinkra": "Ghanaian Adinkra symbols, geometric patterns, black and gold",
        "kente": "Ghanaian Kente cloth weaving, vibrant stripes, royal patterns",
        "ankara": "African wax print, bold colors, geometric and floral motifs",
        "bogolan": "Malian mud cloth, earth tones, tribal patterns",
        "ndebele": "South African Ndebele, bright geometric shapes, symmetrical designs",
    }
    
    def _run(
        self,
        image_uri: str,
        style_reference: str | None = None,
        style_prompt: str | None = None,
        style_strength: float = 0.7,
        preserve_content: bool = True,
    ) -> dict:
        """Synchronous style transfer execution."""
        # Resolve style source
        style_source = "reference" if style_reference else "prompt"
        
        # Check for preset styles
        effective_prompt = style_prompt
        if style_prompt and style_prompt.lower() in self.STYLE_PRESETS:
            effective_prompt = self.STYLE_PRESETS[style_prompt.lower()]
        
        # TODO: Implement actual style transfer with IP-Adapter
        
        return {
            "status": "success",
            "asset_uri": "gs://kratorai-assets/styled/placeholder.png",
            "style_source": style_source,
            "effective_prompt": effective_prompt,
            "strength": style_strength,
            "content_preserved": preserve_content,
        }
    
    async def _arun(
        self,
        image_uri: str,
        style_reference: str | None = None,
        style_prompt: str | None = None,
        style_strength: float = 0.7,
        preserve_content: bool = True,
    ) -> dict:
        """Async style transfer execution."""
        return self._run(image_uri, style_reference, style_prompt, style_strength, preserve_content)
