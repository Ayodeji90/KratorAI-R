"""Reasoning service - uses o3-mini to generate design descriptions from vision data."""

from typing import Dict
from src.services.o3_mini_client import get_o3_mini_client
from src.prompts.reasoning_prompts import DESIGN_ANALYSIS_PROMPT


# Predefined category mapping with IDs
CATEGORY_MAPPING = {
    "Professional Headshots": "691cce06000958fbe4ab",
    "Casual Portraits": "691cce1c0039d32fdc33",
    "Avatars & Characters": "691cce9dd928966d96eb",
    "Marketing Banners": "691cce9dd92dedfb123e",
    "Posters & Flyers": "691cce9dd92ef6f4ab51",
    "Social Media Graphics": "691cce9dd92fc8863542",
    "Logos & Icons": "691cce9dd9307e861459",
    "Product Mockups": "691cce9dd931393bece9",
    "E-commerce Visuals": "691cce9dd932150db6b9",
    "Food Photography": "691cce9dd932cc54cc6c",
    "Fashion & Accessories": "691cce9dd9337ac0cb4d",
    "Landscapes & Cityscapes": "691cce9dd9343303585f",
    "Interior Design": "691cce9dd934e7f1e1c6",
    "Event Backdrops": "691cce9dd93690dd2df1",
    "Concept Art": "691cce9dd9374b9d915b",
    "Digital Art & Illustration": "691cce9dd937f47353b0",
    "Cartoons & Comics": "691cce9dd93896d2200b",
    "Fantasy Creatures": "691cce9dd9399fde6ac0",
    "Infographics": "691cce9dd93a45bccfd6",
    "Presentation Backgrounds": "691cce9dd93b0b79fcae",
    "Educational Diagrams": "691cce9dd93bbf6d2002",
    "UI/UX Mockups": "691cce9dd93c5551ea7c"
}


class ReasoningService:
    """Service for reasoning over visual data to generate descriptions."""
    
    def __init__(self):
        self.o3_client = get_o3_mini_client()
    
    async def generate_design_description(self, vision_data: dict) -> dict:
        """
        Generate a comprehensive design description from vision data.
        
        Args:
            vision_data: Structured output from Azure Vision AI
            
        Returns:
            Dictionary containing:
                - description: Human-readable description
                - category: Design type classification
                - style: List of style tags
                - editable_elements: Suggested editable elements
                - design_quality: Quality assessment
                - target_audience: Inferred audience
                - source: "vision+o3-mini"
        """
        if not self.o3_client.enabled:
            return {
                "description": "AI reasoning is not configured.",
                "category": "Posters & Flyers",
                "category_id": "691cce9dd92ef6f4ab51",
                "style": [],
                "editable_elements": [],
                "design_quality": "unknown",
                "target_audience": "unknown",
                "source": "vision-only"
            }
        
        # Build system prompt
        # Build system prompt
        system_prompt = DESIGN_ANALYSIS_PROMPT

        # Build user prompt with vision data
        user_prompt = f"""Analyze this design based on the following visual data:

**Image Specifications:**
- Size: {vision_data.get('image_size', 'unknown')}
- Layout: {vision_data.get('layout', 'unknown')}
- Text Density: {vision_data.get('text_density', 'unknown')}

**Detected Text:**
{self._format_text_blocks(vision_data.get('text_blocks', []))}

**Visual Tags:**
{', '.join(vision_data.get('basic_tags', []))}

**Contains Images/Graphics:** {vision_data.get('has_images', False)}

**Dominant Colors:** {', '.join(vision_data.get('dominant_colors', []))}

Generate a comprehensive design analysis in JSON format."""

        # Call o3-mini
        result = await self.o3_client.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format={"type": "json_object"}
        )
        
        # Handle errors
        if "error" in result:
            return {
                "description": f"Failed to generate description: {result['error']}",
                "category": "Posters & Flyers",
                "category_id": "691cce9dd92ef6f4ab51",
                "style": [],
                "editable_elements": [],
                "design_quality": "unknown",
                "target_audience": "unknown",
                "source": "vision-only"
            }
        
        # Add source tag
        result["source"] = "vision+o3-mini"
        
        # Ensure all required fields exist with defaults
        result.setdefault("description", "No description available")
        result.setdefault("category", "Posters & Flyers")  # Default to most common category
        result.setdefault("style", [])
        result.setdefault("editable_elements", [])
        result.setdefault("design_quality", "medium")
        result.setdefault("target_audience", "general public")
        
        # Map category name to category ID
        category_name = result.get("category", "Posters & Flyers")
        category_id = CATEGORY_MAPPING.get(category_name)
        
        # If exact match not found, try to find partial match
        if not category_id:
            for cat_name, cat_id in CATEGORY_MAPPING.items():
                if cat_name.lower() in category_name.lower() or category_name.lower() in cat_name.lower():
                    category_id = cat_id
                    result["category"] = cat_name  # Update to exact match
                    break
        
        # If still not found, default to "Posters & Flyers"
        if not category_id:
            category_id = CATEGORY_MAPPING["Posters & Flyers"]
            result["category"] = "Posters & Flyers"
        
        result["category_id"] = category_id
        
        return result
    
    def _format_text_blocks(self, text_blocks: list) -> str:
        """Format text blocks for the prompt."""
        if not text_blocks:
            return "No text detected"
        
        # Limit to first 10 blocks to avoid token overflow
        formatted_blocks = []
        for i, block in enumerate(text_blocks[:10]):
            text = block.get('text', '')
            formatted_blocks.append(f"{i+1}. \"{text}\"")
        
        if len(text_blocks) > 10:
            formatted_blocks.append(f"...and {len(text_blocks) - 10} more text blocks")
        
        return "\n".join(formatted_blocks)


# Singleton
_reasoning_service = None

def get_reasoning_service() -> ReasoningService:
    """Get the singleton reasoning service."""
    global _reasoning_service
    if _reasoning_service is None:
        _reasoning_service = ReasoningService()
    return _reasoning_service
