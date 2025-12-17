"""
Application configuration using Pydantic Settings.
Loads configuration from environment variables.
"""

from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Content Jumpstart Portal"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite:///./portal.db"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""

    # SendGrid
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "no-reply@yourplatform.com"
    SENDGRID_FROM_NAME: str = "Content Jumpstart"

    # File Storage
    UPLOAD_DIR: str = "../data/portal_uploads"
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_MIME_TYPES: str = "application/pdf,image/png,image/jpeg,audio/mpeg,text/plain"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # Admin
    ADMIN_EMAIL: str = "admin@yourplatform.com"
    SUPPORT_EMAIL: str = "support@yourplatform.com"

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def parse_allowed_origins(cls, v: str) -> List[str]:
        """Parse comma-separated origins into list."""
        return [origin.strip() for origin in v.split(",")]

    @field_validator("ALLOWED_MIME_TYPES")
    @classmethod
    def parse_allowed_mime_types(cls, v: str) -> List[str]:
        """Parse comma-separated MIME types into list."""
        return [mime.strip() for mime in v.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
