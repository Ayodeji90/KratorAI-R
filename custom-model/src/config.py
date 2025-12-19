"""Configuration for custom model."""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings."""
    
    # Model paths
    sdxl_model_path: str = "stabilityai/stable-diffusion-xl-base-1.0"
    controlnet_model_path: str = "lllyasviel/sd-controlnet-canny"
    ip_adapter_path: str = "h94/IP-Adapter"
    sam_checkpoint_path: str = "models/base/sam_vit_h.pth"
    
    # Custom finetuned
    cultural_lora_path: str = "models/finetuned/cultural_lora_v1"
    
    # HuggingFace
    hf_token: str | None = None
    
    # GCS
    gcs_bucket_name: str = "kratorai-assets"
    google_application_credentials: str | None = None
    
    # Database
    database_url: str = "postgresql+asyncpg://localhost:5432/kratorai"
    
    # Training
    wandb_api_key: str | None = None
    wandb_project: str = "kratorai-custom"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    debug: bool = False
    
    # GPU
    cuda_visible_devices: str = "0"
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
