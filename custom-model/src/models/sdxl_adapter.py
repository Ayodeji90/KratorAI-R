"""SDXL adapter with ControlNet and IP-Adapter support."""

from typing import Optional
from PIL import Image
import torch

from src.models.base_model import BaseGenerativeModel
from src.config import get_settings


class SDXLAdapter(BaseGenerativeModel):
    """
    SDXL model wrapper with ControlNet and IP-Adapter integration.
    
    Provides the core generative capabilities for KratorAI:
    - Text-to-image generation with cultural LoRA
    - Image-to-image transformation  
    - Multi-image blending via IP-Adapter
    - Structure-preserving generation via ControlNet
    - Inpainting with SDXL inpaint model
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.pipeline = None
        self.controlnet = None
        self.ip_adapter = None
        self.cultural_lora = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    def load(self) -> None:
        """Load SDXL pipeline with extensions."""
        # Lazy imports to avoid loading when not needed
        from diffusers import (
            StableDiffusionXLPipeline,
            StableDiffusionXLImg2ImgPipeline,
            StableDiffusionXLInpaintPipeline,
            ControlNetModel,
        )
        
        # Load base SDXL
        self.pipeline = StableDiffusionXLPipeline.from_pretrained(
            self.settings.sdxl_model_path,
            torch_dtype=torch.float16,
            use_auth_token=self.settings.hf_token,
        ).to(self.device)
        
        # Load ControlNet (optional)
        try:
            self.controlnet = ControlNetModel.from_pretrained(
                self.settings.controlnet_model_path,
                torch_dtype=torch.float16,
            ).to(self.device)
        except Exception as e:
            print(f"ControlNet not loaded: {e}")
        
        # Load cultural LoRA (if available)
        try:
            self.pipeline.load_lora_weights(self.settings.cultural_lora_path)
            self.cultural_lora = True
        except Exception as e:
            print(f"Cultural LoRA not loaded: {e}")
            self.cultural_lora = False
    
    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        width: int = 1024,
        height: int = 1024,
        **kwargs,
    ) -> Image.Image:
        """Generate image from text prompt."""
        if self.pipeline is None:
            self.load()
        
        # Add cultural context to prompt if LoRA is loaded
        if self.cultural_lora:
            prompt = f"{prompt}, African aesthetic, cultural motifs"
        
        result = self.pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt or "blurry, low quality, distorted",
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            **kwargs,
        )
        
        return result.images[0]
    
    def img2img(
        self,
        image: Image.Image,
        prompt: str,
        strength: float = 0.7,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        **kwargs,
    ) -> Image.Image:
        """Transform image based on prompt."""
        from diffusers import StableDiffusionXLImg2ImgPipeline
        
        # Use img2img pipeline
        img2img_pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            self.settings.sdxl_model_path,
            torch_dtype=torch.float16,
        ).to(self.device)
        
        if self.cultural_lora:
            img2img_pipe.load_lora_weights(self.settings.cultural_lora_path)
        
        result = img2img_pipe(
            prompt=prompt,
            image=image,
            strength=strength,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            **kwargs,
        )
        
        return result.images[0]
    
    def inpaint(
        self,
        image: Image.Image,
        mask: Image.Image,
        prompt: str,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        **kwargs,
    ) -> Image.Image:
        """Inpaint masked region."""
        from diffusers import StableDiffusionXLInpaintPipeline
        
        inpaint_pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16,
        ).to(self.device)
        
        result = inpaint_pipe(
            prompt=prompt,
            image=image,
            mask_image=mask,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            **kwargs,
        )
        
        return result.images[0]
    
    def blend_with_ip_adapter(
        self,
        images: list[Image.Image],
        weights: list[float],
        prompt: str = "",
        **kwargs,
    ) -> Image.Image:
        """Blend multiple images using IP-Adapter."""
        # TODO: Implement IP-Adapter blending
        # This requires loading IP-Adapter weights and using
        # the IP-Adapter pipeline for multi-image conditioning
        raise NotImplementedError("IP-Adapter blending coming soon")
    
    def unload(self) -> None:
        """Free GPU memory."""
        if self.pipeline:
            del self.pipeline
            self.pipeline = None
        if self.controlnet:
            del self.controlnet
            self.controlnet = None
        torch.cuda.empty_cache()
