"""Quality Profile: Configurable quality thresholds for post regeneration

This module defines quality profiles that control when posts should be
automatically regenerated. Different profiles can be created for different
client types, industries, or quality standards.
"""

from pydantic import BaseModel, Field, validator


class QualityProfile(BaseModel):
    """Quality thresholds and settings for post regeneration

    Attributes:
        profile_name: Name of this quality profile
        description: What this profile is optimized for

        # Readability thresholds (Flesch Reading Ease 0-100)
        min_readability: Minimum readability score (lower = harder to read)
        max_readability: Maximum readability score (higher = easier to read)

        # Length constraints
        min_words: Minimum word count
        max_words: Maximum word count

        # Engagement requirements
        min_engagement_score: Minimum headline engagement elements (0-3)
        require_cta: Whether posts must have clear call-to-action

        # Regeneration behavior
        max_attempts: Maximum regeneration attempts per post (1-5)
        enabled: Whether auto-regeneration is enabled
    """

    profile_name: str = Field(..., description="Name of this quality profile")
    description: str = Field(..., description="What this profile is for")

    # Readability constraints (Flesch Reading Ease)
    min_readability: float = Field(
        50.0,
        ge=0.0,
        le=100.0,
        description="Minimum readability score (0=very difficult, 100=very easy)",
    )
    max_readability: float = Field(
        65.0, ge=0.0, le=100.0, description="Maximum readability score (keeps professional tone)"
    )

    # Length constraints
    min_words: int = Field(150, ge=50, le=2000, description="Minimum word count")
    max_words: int = Field(300, ge=100, le=3000, description="Maximum word count")

    # Engagement requirements
    min_engagement_score: int = Field(
        2,
        ge=0,
        le=3,
        description="Minimum headline engagement elements (questions, numbers, power words)",
    )
    require_cta: bool = Field(True, description="Whether posts must have clear call-to-action")

    # Regeneration behavior
    max_attempts: int = Field(2, ge=1, le=5, description="Maximum regeneration attempts per post")
    enabled: bool = Field(True, description="Whether auto-regeneration is enabled for this profile")

    @validator("max_readability")
    def readability_max_must_exceed_min(cls, v, values):
        """Ensure max readability is greater than min"""
        if "min_readability" in values and v <= values["min_readability"]:
            raise ValueError(
                f"max_readability ({v}) must be greater than min_readability ({values['min_readability']})"
            )
        return v

    @validator("max_words")
    def max_words_must_exceed_min(cls, v, values):
        """Ensure max words is greater than min"""
        if "min_words" in values and v <= values["min_words"]:
            raise ValueError(
                f"max_words ({v}) must be greater than min_words ({values['min_words']})"
            )
        return v

    class Config:
        """Pydantic model configuration with example schema"""

        json_schema_extra = {
            "example": {
                "profile_name": "professional_linkedin",
                "description": "Professional B2B LinkedIn content with balanced readability",
                "min_readability": 50.0,
                "max_readability": 65.0,
                "min_words": 150,
                "max_words": 300,
                "min_engagement_score": 2,
                "require_cta": True,
                "max_attempts": 2,
                "enabled": True,
            }
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for API usage"""
        return self.model_dump()

    @classmethod
    def from_file(cls, file_path: str) -> "QualityProfile":
        """Load quality profile from JSON file

        Args:
            file_path: Path to JSON profile file

        Returns:
            QualityProfile instance

        Raises:
            FileNotFoundError: If profile file doesn't exist
            ValueError: If profile file is invalid
        """
        import json
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Quality profile not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in profile file: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load profile: {e}")

    def save_to_file(self, file_path: str) -> None:
        """Save quality profile to JSON file

        Args:
            file_path: Path where to save profile
        """
        import json
        from pathlib import Path

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)


# Predefined quality profiles
DEFAULT_PROFILES = {
    "professional_linkedin": QualityProfile(
        profile_name="professional_linkedin",
        description="Professional B2B LinkedIn content with balanced readability",
        min_readability=50.0,
        max_readability=65.0,
        min_words=150,
        max_words=300,
        min_engagement_score=2,
        require_cta=True,
        max_attempts=2,
        enabled=True,
    ),
    "casual_linkedin": QualityProfile(
        profile_name="casual_linkedin",
        description="More casual, conversational LinkedIn content",
        min_readability=60.0,
        max_readability=75.0,
        min_words=120,
        max_words=250,
        min_engagement_score=2,
        require_cta=True,
        max_attempts=2,
        enabled=True,
    ),
    "executive_linkedin": QualityProfile(
        profile_name="executive_linkedin",
        description="Executive-level content with sophisticated language",
        min_readability=40.0,
        max_readability=60.0,
        min_words=180,
        max_words=350,
        min_engagement_score=1,
        require_cta=False,
        max_attempts=2,
        enabled=True,
    ),
    "twitter": QualityProfile(
        profile_name="twitter",
        description="Twitter/X content - ultra-concise and punchy",
        min_readability=65.0,
        max_readability=85.0,
        min_words=50,
        max_words=100,
        min_engagement_score=2,
        require_cta=True,
        max_attempts=2,
        enabled=True,
    ),
    "blog": QualityProfile(
        profile_name="blog",
        description="Long-form blog content with depth",
        min_readability=50.0,
        max_readability=70.0,
        min_words=800,
        max_words=2000,
        min_engagement_score=2,
        require_cta=True,
        max_attempts=2,
        enabled=True,
    ),
    "permissive": QualityProfile(
        profile_name="permissive",
        description="Permissive profile - minimal regeneration",
        min_readability=30.0,
        max_readability=85.0,
        min_words=75,
        max_words=500,
        min_engagement_score=0,
        require_cta=False,
        max_attempts=1,
        enabled=False,
    ),
}


def get_default_profile(profile_name: str = "professional_linkedin") -> QualityProfile:
    """Get a predefined quality profile by name

    Args:
        profile_name: Name of profile to retrieve

    Returns:
        QualityProfile instance

    Raises:
        ValueError: If profile name is unknown
    """
    if profile_name not in DEFAULT_PROFILES:
        available = ", ".join(DEFAULT_PROFILES.keys())
        raise ValueError(f"Unknown profile '{profile_name}'. Available profiles: {available}")
    return DEFAULT_PROFILES[profile_name]
