"""Client brief data models for content generation"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class TonePreference(str, Enum):
    """Tone preferences"""

    APPROACHABLE = "approachable"
    DIRECT = "direct"
    AUTHORITATIVE = "authoritative"
    WITTY = "witty"
    VULNERABLE = "vulnerable"
    DATA_DRIVEN = "data_driven"
    CONVERSATIONAL = "conversational"


class Platform(str, Enum):
    """Social media platforms"""

    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    BLOG = "blog"
    EMAIL = "email"
    MULTI = "multi"  # Generate for all platforms

    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup"""
        value = str(value).lower()
        for member in cls:
            if member.value.lower() == value:
                return member
        return None


class DataUsagePreference(str, Enum):
    """How much data/statistics to use"""

    HEAVY = "heavy"
    MODERATE = "moderate"
    MINIMAL = "minimal"


class ClientBrief(BaseModel):
    """Structured client brief data"""

    # Basic Info
    company_name: str = Field(..., description="Company or client name")
    founder_name: Optional[str] = Field(None, description="Founder or primary voice")
    website: Optional[str] = Field(None, description="Website or LinkedIn URL")
    business_description: str = Field(..., description="One-sentence business description")

    # Audience
    ideal_customer: str = Field(..., description="Ideal customer profile")
    main_problem_solved: str = Field(..., description="Main problem the business solves")
    customer_pain_points: List[str] = Field(
        default_factory=list, description="Customer pain points (unlimited)"
    )

    # Voice & Tone
    brand_personality: List[TonePreference] = Field(
        default_factory=list, description="Brand personality traits"
    )
    tone_to_avoid: Optional[str] = Field(None, description="What tone to avoid")
    key_phrases: List[str] = Field(default_factory=list, description="Client's common phrases")
    role_model_communicator: Optional[str] = Field(None, description="Communication role model")

    # Content Topics
    customer_questions: List[str] = Field(
        default_factory=list, description="Top 5 questions customers ask"
    )
    misconceptions: List[str] = Field(
        default_factory=list, description="Industry misconceptions to correct"
    )
    measurable_results: Optional[str] = Field(
        None, description="Results delivered in measurable terms"
    )

    # Platform & Delivery
    target_platforms: List[Platform] = Field(default_factory=list, description="Target platforms")
    posting_frequency: Optional[str] = Field(None, description="Desired posting frequency")
    data_usage: DataUsagePreference = Field(
        DataUsagePreference.MODERATE, description="Data/stats usage preference"
    )

    # CTAs & Goals
    main_cta: Optional[str] = Field(None, description="Primary call-to-action")
    lead_magnets: List[str] = Field(
        default_factory=list, description="Available lead magnets/freebies"
    )

    # Stories & Examples
    stories: List[str] = Field(
        default_factory=list, description="Personal stories or customer wins"
    )
    case_studies: List[str] = Field(
        default_factory=list, description="Case study links or summaries"
    )

    # Metadata
    delivery_date: Optional[str] = Field(None, description="Requested delivery date")

    @field_validator("customer_questions")
    @classmethod
    def limit_list_length(cls, v: List[str], info) -> List[str]:
        """Ensure customer_questions list doesn't exceed reasonable limits"""
        max_len = 10
        if len(v) > max_len:
            raise ValueError(f"{info.field_name} should have at most {max_len} items")
        return v

    def get_missing_fields(self) -> List[str]:
        """Identify which optional fields are missing"""
        missing = []
        if not self.founder_name:
            missing.append("founder_name")
        if not self.stories:
            missing.append("stories (needed for personal story templates)")
        if not self.main_cta:
            missing.append("main_cta")
        if not self.measurable_results:
            missing.append("measurable_results")
        return missing

    def to_context_dict(self) -> dict:
        """Convert to dictionary suitable for template rendering"""
        return {
            "company_name": self.company_name,
            "ideal_customer": self.ideal_customer,
            "problem_solved": self.main_problem_solved,
            "brand_voice": ", ".join([t.value for t in self.brand_personality]),
            "pain_points": self.customer_pain_points,
            "key_phrases": self.key_phrases,
            "stories": self.stories,
            "main_cta": self.main_cta or "engage with us",
            "data_preference": self.data_usage.value,
            "misconceptions": self.misconceptions,
            "customer_questions": self.customer_questions,
            "results": self.measurable_results,
        }
