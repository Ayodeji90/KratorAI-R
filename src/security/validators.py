"""Request validation utilities for KratorAI backend.

This module provides validation functions to protect against abuse:
- Oversized prompts
- Invalid file uploads
- Out-of-range parameters
"""

from typing import Optional
from fastapi import HTTPException, UploadFile, status

from src.config import get_settings

# Constants
MAX_PROMPT_LENGTH = 2000
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]


def validate_prompt(prompt: Optional[str], required: bool = False) -> None:
    """
    Validate prompt length.
    
    Args:
        prompt: The prompt text to validate
        required: If True, raise error if prompt is None or empty
        
    Raises:
        HTTPException: 400 if prompt is too long or missing when required
    """
    if required and not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt is required"
        )
    
    if prompt and len(prompt) > MAX_PROMPT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters"
        )


async def validate_image_upload(file: UploadFile) -> None:
    """
    Validate uploaded image file.
    
    Checks:
    - File has valid content type
    - File size is within limits
    
    Args:
        file: The uploaded file to validate
        
    Raises:
        HTTPException: 400 if validation fails
    """
    # Check content type
    if not file.content_type or file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    
    # Check file size by reading into memory
    # Note: For very large files, consider streaming validation
    content = await file.read()
    file_size = len(content)
    
    # Reset file pointer for later reading
    await file.seek(0)
    
    settings = get_settings()
    max_size = settings.max_upload_size
    
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size ({file_size} bytes) exceeds maximum of {max_size} bytes"
        )


def validate_strength(strength: float) -> None:
    """
    Validate strength parameter for image refinement.
    
    Args:
        strength: Refinement strength (should be between 0.1 and 1.0)
        
    Raises:
        HTTPException: 400 if strength is out of range
    """
    if not (0.1 <= strength <= 1.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strength must be between 0.1 and 1.0"
        )


def validate_num_variations(num_variations: int) -> None:
    """
    Validate number of variations parameter.
    
    Args:
        num_variations: Number of variations to generate
        
    Raises:
        HTTPException: 400 if num_variations is out of range
    """
    if not (1 <= num_variations <= 5):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Number of variations must be between 1 and 5"
        )
