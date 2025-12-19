"""Base model interface for KratorAI generative models."""

from abc import ABC, abstractmethod
from typing import Optional
from PIL import Image


class BaseGenerativeModel(ABC):
    """Abstract base class for all generative models."""
    
    @abstractmethod
    def load(self) -> None:
        """Load model weights and initialize."""
        pass
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        **kwargs,
    ) -> Image.Image:
        """Generate an image from prompt."""
        pass
    
    @abstractmethod
    def img2img(
        self,
        image: Image.Image,
        prompt: str,
        strength: float = 0.7,
        **kwargs,
    ) -> Image.Image:
        """Transform an image based on prompt."""
        pass
    
    @abstractmethod
    def inpaint(
        self,
        image: Image.Image,
        mask: Image.Image,
        prompt: str,
        **kwargs,
    ) -> Image.Image:
        """Inpaint masked region of image."""
        pass
    
    def unload(self) -> None:
        """Unload model to free memory."""
        pass
