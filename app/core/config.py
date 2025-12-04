"""
Application configuration using Pydantic Settings.
Handles environment variables with type validation.
"""

from pathlib import Path
from typing import List, Optional
from pydantic import Field, field_validator, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# Resolve project root so .env can be loaded regardless of CWD
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "Discuzz.ai API"
    app_version: str = "1.0.0"
    debug: bool = False
    enable_docs: bool = False
    environment: str = "production"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    # Database
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: Optional[str] = None

    # Authentication
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Social Auth
    google_client_id: Optional[str] = None
    google_application_credentials_json: Optional[str] = None
    firebase_project_id: Optional[str] = None

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: str = "noreply@discuzz.ai"

    # File Storage
    upload_dir: str = "uploads"
    max_upload_size: int = 10485760  # 10MB
    allowed_image_types: str = "image/jpeg,image/png,image/gif,image/webp"

    @property
    def allowed_image_types_list(self) -> List[str]:
        return [t.strip() for t in self.allowed_image_types.split(",")]

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60

    # Security
    bcrypt_rounds: int = 12
    password_min_length: int = 8


    # AI Services
    openai_api_key: Optional[str] = Field(
        default=None,
        alias="NEXT_PUBLIC_OPENAI_API_KEY",
        description="OpenAI API key sourced from NEXT_PUBLIC_OPENAI_API_KEY"
    )
    gemini_api_key: Optional[str] = None

@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
