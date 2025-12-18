"""Image processing utilities."""

from PIL import Image
import io
import base64
from typing import Optional


def resize_for_api(image: Image.Image, max_size: int = 1024) -> Image.Image:
    """Resize image to fit within max dimensions while preserving aspect ratio."""
    width, height = image.size
    
    if width <= max_size and height <= max_size:
        return image
    
    if width > height:
        new_width = max_size
        new_height = int(height * (max_size / width))
    else:
        new_height = max_size
        new_width = int(width * (max_size / height))
    
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def base64_to_image(base64_str: str) -> Image.Image:
    """Convert base64 string to PIL Image."""
    image_data = base64.b64decode(base64_str)
    return Image.open(io.BytesIO(image_data))


def create_thumbnail(image: Image.Image, size: tuple[int, int] = (256, 256)) -> Image.Image:
    """Create a thumbnail from an image."""
    thumb = image.copy()
    thumb.thumbnail(size, Image.Resampling.LANCZOS)
    return thumb


def validate_image_format(image: Image.Image, allowed_formats: Optional[list[str]] = None) -> bool:
    """Validate that image is in an allowed format."""
    if allowed_formats is None:
        allowed_formats = ["PNG", "JPEG", "WEBP"]
    
    return image.format in allowed_formats if image.format else True
