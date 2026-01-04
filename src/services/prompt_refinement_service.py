"""Prompt refinement service - uses o3-mini to refine vague user prompts."""

from typing import Dict
from src.services.o3_mini_client import get_o3_mini_client


class PromptRefinementService:
    """Service for refining user prompts before FLUX generation."""
    
    def __init__(self):
        self.o3_client = get_o3_mini_client()
    
    async def refine_user_prompt(
        self,
        user_prompt: str,
        vision_data: dict
    ) -> dict:
        """
        Refine a user's prompt to be clear, explicit, and design-safe.
        
        Args:
            user_prompt: Original user prompt (may be vague)
            vision_data: Structured visual data from Azure Vision
            
        Returns:
            Dictionary containing:
                - original_prompt: The user's original prompt
                - refined_prompt: Enhanced, explicit version
                - refinement_rationale: Explanation of changes
                - detected_intent: What the user wants to achieve
                - preserved_elements: Important elements to keep
        """
        if not self.o3_client.enabled:
            # Graceful degradation: return original prompt
            return {
                "original_prompt": user_prompt,
                "refined_prompt": user_prompt,
                "refinement_rationale": "AI refinement not available",
                "detected_intent": "unknown",
                "preserved_elements": []
            }
        
        # Build system prompt
        system_prompt = """You are a design prompt refinement expert. Your job is to transform vague or incomplete user prompts into clear, explicit instructions for an image generation AI.

Rules:
1. PRESERVE user intent - don't invent requirements they didn't ask for
2. Make prompts EXPLICIT and SPECIFIC (colors, placement, style)
3. Ensure SAFETY - preserve important elements from the original design
4. ALIGN with detected layout and structure
5. Be DESIGN-AWARE (contrast, readability, composition)

Respond ONLY with valid JSON containing:
- refined_prompt: Enhanced version of the prompt (detailed and explicit)
- refinement_rationale: Brief explanation of changes made
- detected_intent: Primary goal (aesthetic_improvement, content_change, color_adjustment, layout_redesign, text_modification, or other)
- preserved_elements: Array of design elements that should be kept (e.g., headline, logo, CTA, date)

Be concise and professional."""

        # Build user prompt with context
        user_prompt_formatted = f"""User's original prompt: "{user_prompt}"

**Design Context (from visual analysis):**
- Layout: {vision_data.get('layout', 'unknown')}
- Text Density: {vision_data.get('text_density', 'unknown')}
- Detected Text: {self._summarize_text(vision_data.get('text_blocks', []))}
- Visual Tags: {', '.join(vision_data.get('basic_tags', []))}
- Has Images: {vision_data.get('has_images', False)}

Refine the user's prompt to be clear and explicit while preserving their intent. Output JSON only."""

        # Call o3-mini with deterministic temperature
        result = await self.o3_client.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt_formatted,
            response_format={"type": "json_object"},
            temperature=0.0  # Fully deterministic for consistent refinement
        )
        
        # Handle errors
        if "error" in result:
            return {
                "original_prompt": user_prompt,
                "refined_prompt": user_prompt,
                "refinement_rationale": f"Refinement failed: {result['error']}",
                "detected_intent": "unknown",
                "preserved_elements": []
            }
        
        # Add original prompt and ensure defaults
        result["original_prompt"] = user_prompt
        result.setdefault("refined_prompt", user_prompt)
        result.setdefault("refinement_rationale", "No changes needed")
        result.setdefault("detected_intent", "unknown")
        result.setdefault("preserved_elements", [])
        
        return result
    
    def _summarize_text(self, text_blocks: list) -> str:
        """Summarize detected text for context."""
        if not text_blocks:
            return "No text"
        
        # Get first 3 text blocks
        texts = [block.get('text', '')[:50] for block in text_blocks[:3]]
        summary = ', '.join(f'"{t}"' for t in texts if t)
        
        if len(text_blocks) > 3:
            summary += f" (+{len(text_blocks)-3} more)"
        
        return summary


# Singleton
_prompt_refinement_service = None

def get_prompt_refinement_service() -> PromptRefinementService:
    """Get the singleton prompt refinement service."""
    global _prompt_refinement_service
    if _prompt_refinement_service is None:
        _prompt_refinement_service = PromptRefinementService()
    return _prompt_refinement_service
