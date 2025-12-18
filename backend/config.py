"""
Backend configuration settings loaded from environment variables.
"""
import os
import tempfile
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings

# Allow selecting an alternate env file for local/remote runs.
ENV_FILE = os.getenv("ENV_FILE", ".env")

# Get backend directory for relative paths
BACKEND_DIR = Path(__file__).parent
DATA_DIR = BACKEND_DIR / "data"

# Try to create data directory, fallback to temp if permission denied
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    DATA_DIR = Path(tempfile.gettempdir()) / "content_jumpstart"
    DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """Application settings"""

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_TITLE: str = "Content Jumpstart API"
    API_VERSION: str = "1.0.0"
    DEBUG_MODE: bool = True

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Database (use DATA_DIR constant defined at module level)
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'operator.db'}"

    # Database Connection Pool Settings
    # These settings optimize connection management for production PostgreSQL
    # For SQLite (default), pooling is limited due to single-threaded nature
    DB_POOL_SIZE: int = 20  # Number of connections to keep open
    DB_MAX_OVERFLOW: int = 40  # Max additional connections beyond pool_size
    DB_POOL_RECYCLE: int = 3600  # Recycle connections after 1 hour (seconds)
    DB_POOL_PRE_PING: bool = True  # Test connections before using (detect stale)
    DB_ECHO_POOL: bool = False  # Log connection pool operations (debug only)
    DB_POOL_TIMEOUT: int = 30  # Seconds to wait for connection from pool

    # JWT Authentication
    # CRITICAL SECURITY: SECRET_KEY must be cryptographically random and unique
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    # NEVER use default values in production
    SECRET_KEY: str  # No default - must be set via environment variable
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate SECRET_KEY is not a known weak/default value"""
        # Known weak/default values that must be rejected
        weak_keys = [
            "dev-secret-key-change-in-production",
            "your-secret-key-here-change-in-production",
            "your-secret-key-here",
            "change-me",
            "secret",
            "password",
            "admin",
            "test",
            "demo",
        ]

        # Check if key is in known weak list (case-insensitive)
        if v.lower() in weak_keys:
            raise ValueError(
                f"CRITICAL SECURITY ERROR: Detected weak/default SECRET_KEY '{v}'. "
                "Generate a secure key with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )

        # Enforce minimum length (32 characters for 256-bit equivalent)
        if len(v) < 32:
            raise ValueError(
                f"SECRET_KEY must be at least 32 characters (got {len(v)}). "
                "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )

        return v

    # Anthropic API
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # Rate Limiting (70% of Anthropic limits)
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 2800
    RATE_LIMIT_TOKENS_PER_MINUTE: int = 280000

    # Content Generation
    PARALLEL_GENERATION: bool = True
    MAX_CONCURRENT_API_CALLS: int = 5

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_BRIEF_EXTENSIONS: str = ".txt,.md"

    @property
    def allowed_extensions_list(self) -> List[str]:
        """Parse allowed extensions from comma-separated string"""
        return [ext.strip() for ext in self.ALLOWED_BRIEF_EXTENSIONS.split(",")]

    # Paths (use DATA_DIR constant defined at module level)
    BRIEFS_DIR: str = str(DATA_DIR / "briefs")
    OUTPUTS_DIR: str = str(DATA_DIR / "outputs")
    LOGS_DIR: str = str(BACKEND_DIR / "logs")

    # Cache Configuration
    # Tuned for production load: 10 concurrent projects, 300 total posts
    # Week 3 optimization: Increased from initial values (100/50/20)

    # Cache TTLs (Time To Live) in seconds
    CACHE_TTL_SHORT: int = 300   # 5 minutes - frequently changing data
    CACHE_TTL_MEDIUM: int = 600  # 10 minutes - semi-static data
    CACHE_TTL_LONG: int = 3600   # 1 hour - static data

    # Cache size limits (max entries per tier)
    # Short: Projects list, posts list, runs (high volume, frequent changes)
    CACHE_MAX_SIZE_SHORT: int = 500
    # Medium: Individual projects, clients (moderate volume, occasional changes)
    CACHE_MAX_SIZE_MEDIUM: int = 200
    # Long: Templates, system data (low volume, rare changes)
    CACHE_MAX_SIZE_LONG: int = 100

    class Config:
        env_file = ENV_FILE
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()
