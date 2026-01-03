"""Configuration management for KratorAI Gemini Integration."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Azure AI (FLUX.1)
    azure_ai_endpoint: str
    azure_ai_key: str
    azure_ai_deployment: str = "FLUX.1-Kontext-pro"
    azure_ai_api_version: str = "2025-04-01-preview"
    
    # Azure Computer Vision
    azure_vision_endpoint: str | None = None
    azure_vision_key: str | None = None
    
    # Google Cloud Storage
    gcs_bucket_name: str = "kratorai-assets"
    google_application_credentials: str | None = None
    
    # Database
    database_url: str = "postgresql+asyncpg://localhost:5432/kratorai"
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # Production Settings
    request_timeout: int = 60
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    rate_limit_per_minute: int = 60
    
    # Model Settings
    max_images_per_breed: int = 5
    default_breed_weight: float = 0.5
    
    # App Settings
    app_name: str = "KratorAI"
    app_version: str = "1.0.0"
    environment: str = "development"
    cors_origins: str = "*"
    
    # Performance
    flux_timeout_seconds: int = 30
    max_concurrent_requests: int = 5
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore other extra fields if any


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
