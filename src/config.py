"""Configuration management for KratorAI Gemini Integration."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Gemini API
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
