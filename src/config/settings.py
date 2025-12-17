"""Application configuration and environment settings"""
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Anthropic API
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"  # Claude 3.5 Sonnet (latest)
    MAX_TOKENS: int = 4096
    TEMPERATURE: float = 0.7
    MAX_RETRIES: int = 3
    TIMEOUT_SECONDS: int = 120

    # Generation-specific temperatures
    POST_GENERATION_TEMPERATURE: float = 0.7  # Balanced creativity for posts
    BRIEF_PARSING_TEMPERATURE: float = 0.3  # Lower temperature for accurate extraction

    # Quality thresholds
    MIN_POST_WORD_COUNT: int = 75  # LinkedIn/Twitter minimum for engagement
    MAX_POST_WORD_COUNT: int = 350  # LinkedIn character limit consideration
    OPTIMAL_POST_MIN_WORDS: int = 150  # Sweet spot minimum
    OPTIMAL_POST_MAX_WORDS: int = 250  # Sweet spot maximum

    # Paths (relative to /project/ directory)
    TEMPLATE_LIBRARY_PATH: str = "../02_POST_TEMPLATE_LIBRARY.md"
    CLIENT_BRIEF_TEMPLATE_PATH: str = "../01_CLIENT_BRIEF_TEMPLATE.md"
    DELIVERABLE_TEMPLATE_PATH: str = "../Jumpstart_Deliverable_Template.docx"
    DEFAULT_OUTPUT_DIR: str = "data/outputs"
    DEFAULT_BRIEFS_DIR: str = "data/briefs"
    PROJECTS_DIR: str = "data/projects"  # Completed client deliverables

    # Application
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = "logs/content_jumpstart.log"
    DEBUG_MODE: bool = False

    # Generation Settings
    DEFAULT_TEMPLATE_COUNT: int = 15
    DEFAULT_POST_COUNT: int = 30
    DEFAULT_OUTPUT_FORMAT: str = "txt"
    RANDOMIZE_OUTPUT: bool = True

    # Performance
    CACHE_PROMPTS: bool = True
    PARALLEL_GENERATION: bool = True  # Phase 2 - Async parallel generation
    MAX_CONCURRENT_API_CALLS: int = 5  # Limit concurrent API requests
    BATCH_SIZE: int = 10  # Number of posts per batch

    # API Response Caching (dev/testing only)
    ENABLE_RESPONSE_CACHE: bool = False  # Enable disk-based response cache
    RESPONSE_CACHE_DIR: str = ".cache/api_responses"  # Cache directory
    RESPONSE_CACHE_TTL: int = 86400  # Cache TTL in seconds (24 hours)

    # Anthropic Prompt Caching
    ENABLE_PROMPT_CACHING: bool = True  # Use Anthropic's prompt caching API
    CACHE_SYSTEM_PROMPTS: bool = True  # Cache system prompts
    CACHE_CLIENT_CONTEXT: bool = True  # Cache client brief context

    class Config:
        """Pydantic settings configuration"""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from backend .env


# Global settings instance
settings = Settings()
