"""Gemini API client wrapper for KratorAI."""

import google.generativeai as genai
from PIL import Image
import io
import base64
from typing import Optional
import httpx

from src.config import get_settings


class GeminiClient:
    """Wrapper for Google Gemini API interactions."""
    
    def __init__(self):
        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.vision_model = genai.GenerativeModel("gemini-2.0-flash")
    
    async def generate_with_images(
        self,
        prompt: str,
        image_uris: list[str],
        generation_config: Optional[dict] = None,
    ) -> dict:
        """
        Generate content from multiple images with a prompt.
        
        Args:
            prompt: Text prompt for generation
            image_uris: List of image URIs (GCS or URLs)
            generation_config: Optional generation parameters
        
        Returns:
            Generated content with image data
        """
        # Load images
        images = await self._load_images(image_uris)
        
        # Build content parts
        content_parts = [prompt]
        for img in images:
            content_parts.append(img)
        
        # Generate
        response = self.model.generate_content(
            content_parts,
            generation_config=generation_config or {},
        )
        
        # Safely extract text and images from response
        text_content = None
        images = []
        try:
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_content = part.text
                        if hasattr(part, 'inline_data') and part.inline_data:
                            img_data = part.inline_data.data
                            img = Image.open(io.BytesIO(img_data))
                            images.append(img)
        except Exception:
            pass
        
        return {
            "text": text_content,
            "images": images,
            "candidates": response.candidates if hasattr(response, 'candidates') else [],
            "prompt_feedback": getattr(response, 'prompt_feedback', None),
        }

    async def generate_content(
        self,
        parts: list,
        generation_config: Optional[dict] = None,
    ) -> dict:
        """
        Generate content from a list of parts (text, images, etc.).
        
        Args:
            parts: List of content parts
            generation_config: Optional generation parameters
        
        Returns:
            Generated content with image data
        """
        # Generate
        response = self.model.generate_content(
            parts,
            generation_config=generation_config or {},
        )
        
        # Safely extract text and images from response
        text_content = None
        images = []
        try:
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_content = part.text
                        if hasattr(part, 'inline_data') and part.inline_data:
                            img_data = part.inline_data.data
                            img = Image.open(io.BytesIO(img_data))
                            images.append(img)
        except Exception:
            pass
        
        return {
            "text": text_content,
            "images": images,
            "candidates": response.candidates if hasattr(response, 'candidates') else [],
            "prompt_feedback": getattr(response, 'prompt_feedback', None),
        }
    
    async def breed_images(
        self,
        image_uris: list[tuple[str, float]],
        style_prompt: Optional[str] = None,
        preserve_cultural: bool = True,
    ) -> dict:
        """
        Breed multiple images together based on weights.
        
        Args:
            image_uris: List of (uri, weight) tuples
            style_prompt: Additional styling instructions
            preserve_cultural: Whether to prioritize African motifs
        
        Returns:
            Generated hybrid image data
        """
        # Build breeding prompt
        base_prompt = self._build_breeding_prompt(image_uris, style_prompt, preserve_cultural)
        
        # Extract just URIs for loading
        uris = [uri for uri, _ in image_uris]
        
        result = await self.generate_with_images(base_prompt, uris)
        
        return result
    
    async def refine_image(
        self,
        image_uri: str,
        prompt: str,
        strength: float = 0.7,
    ) -> dict:
        """
        Refine an image with a prompt.
        
        Args:
            image_uri: Source image URI
            prompt: Refinement instructions
            strength: Refinement intensity (0.1 - 1.0)
        
        Returns:
            Refined image data
        """
        refine_prompt = f"""
        Refine this design with the following instructions:
        {prompt}
        
        Refinement intensity: {strength * 100}%
        Maintain the core structure while applying the requested changes.
        Preserve any African cultural motifs (Adinkra, Kente, etc.) present.
        """
        
        result = await self.generate_with_images(refine_prompt, [image_uri])
        return result
    
    async def edit_image(
        self,
        image_uri: str,
        prompt: str,
        mask_uri: Optional[str] = None,
        edit_type: str = "inpaint",
    ) -> dict:
        """
        Edit an image with optional mask.
        
        Args:
            image_uri: Source image URI
            prompt: Edit instructions
            mask_uri: Optional mask for inpainting
            edit_type: Type of edit (inpaint, style_transfer, color_swap)
        
        Returns:
            Edited image data
        """
        edit_prompts = {
            "inpaint": f"Inpaint the masked region: {prompt}",
            "style_transfer": f"Apply style transfer: {prompt}",
            "color_swap": f"Change colors as follows: {prompt}",
        }
        
        full_prompt = edit_prompts.get(edit_type, prompt)
        full_prompt += "\nEnsure the result remains culturally authentic and visually cohesive."
        
        uris = [image_uri]
        if mask_uri:
            uris.append(mask_uri)
        
        result = await self.generate_with_images(full_prompt, uris)
        return result
    
    def _build_breeding_prompt(
        self,
        image_uris: list[tuple[str, float]],
        style_prompt: Optional[str],
        preserve_cultural: bool,
    ) -> str:
        """Build the breeding prompt with weight instructions."""
        weight_desc = []
        for i, (_, weight) in enumerate(image_uris):
            weight_desc.append(f"Image {i+1}: {weight * 100:.0f}%")
        
        prompt = f"""
        Create a hybrid design by blending the following images:
        {', '.join(weight_desc)}
        
        Blend the visual elements proportionally based on the weights.
        Combine patterns, colors, and compositional elements from each source.
        """
        
        if preserve_cultural:
            prompt += """
            IMPORTANT: Preserve and prioritize African cultural motifs such as:
            - Adinkra symbols from Ghana
            - Kente weaving patterns
            - Ankara/African wax print designs
            - Traditional color palettes
            """
        
        if style_prompt:
            prompt += f"\n\nAdditional styling: {style_prompt}"
        
        return prompt
    
    async def _load_images(self, uris: list[str]) -> list:
        """Load images from URIs."""
        images = []
        async with httpx.AsyncClient() as client:
            for uri in uris:
                if uri.startswith("gs://"):
                    # GCS URI - would need GCS client
                    # For now, placeholder
                    pass
                elif uri.startswith("http"):
                    # HTTP URL
                    response = await client.get(uri)
                    img = Image.open(io.BytesIO(response.content))
                    images.append(img)
                else:
                    # Local file path
                    img = Image.open(uri)
                    images.append(img)
        
        return images


# Singleton instance
_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """Get or create the Gemini client singleton."""
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
