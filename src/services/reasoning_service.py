"""Reasoning service - uses o3-mini to generate design descriptions from vision data."""

from typing import Dict
from src.services.o3_mini_client import get_o3_mini_client


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
                "category": "unknown",
                "style": [],
                "editable_elements": [],
                "design_quality": "unknown",
                "target_audience": "unknown",
                "source": "vision-only"
            }
        
        # Build system prompt
        system_prompt = """You are an expert design analyst specializing in flyers, posters, and graphic designs.

Given structured visual data from image analysis, you must generate a comprehensive design analysis.

Respond ONLY with valid JSON containing:
- description: Clear, human-readable description of the design (2-3 sentences)
- category: Type of design (event_flyer, business_promo, social_media_post, product_ad, informational_poster, or other)
- style: Array of 2-5 style tags (e.g., modern, vintage, minimal, professional, bold, colorful, tech, creative)
- editable_elements: Array of key elements that can be edited (e.g., headline, background, CTA, colors, logo, text)
- design_quality: Assessment (high, medium, low) based on structure and composition
- target_audience: Inferred primary audience (e.g., tech professionals, consumers, students, general public)

Be concise, professional, and accurate. Base your analysis strictly on the provided visual data."""

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
                "category": "unknown",
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
        result.setdefault("category", "other")
        result.setdefault("style", [])
        result.setdefault("editable_elements", [])
        result.setdefault("design_quality", "medium")
        result.setdefault("target_audience", "general public")
        
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
