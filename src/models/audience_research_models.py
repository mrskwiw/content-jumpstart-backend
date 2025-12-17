"""Data models for audience research"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class AgeRange(str, Enum):
    """Age range categories"""

    GEN_Z = "18-24"  # Gen Z
    MILLENNIALS_YOUNG = "25-34"  # Young Millennials
    MILLENNIALS_OLD = "35-44"  # Older Millennials
    GEN_X = "45-54"  # Gen X
    BABY_BOOMERS = "55-64"  # Baby Boomers
    SENIORS = "65+"  # Seniors


class IncomeLevel(str, Enum):
    """Income level categories"""

    LOW = "low"  # < $50k
    MIDDLE = "middle"  # $50k-$100k
    UPPER_MIDDLE = "upper_middle"  # $100k-$200k
    HIGH = "high"  # > $200k


class EducationLevel(str, Enum):
    """Education level categories"""

    HIGH_SCHOOL = "high_school"
    SOME_COLLEGE = "some_college"
    BACHELORS = "bachelors"
    MASTERS = "masters"
    DOCTORATE = "doctorate"


class Demographics(BaseModel):
    """Demographic profile"""

    primary_age_ranges: List[AgeRange] = Field(
        default_factory=list, description="Primary age ranges (1-3 ranges)"
    )
    gender_distribution: str = Field(..., description="Gender distribution description")
    locations: List[str] = Field(
        default_factory=list, description="Geographic locations (countries, regions, cities)"
    )
    income_levels: List[IncomeLevel] = Field(
        default_factory=list, description="Income level distribution"
    )
    education_levels: List[EducationLevel] = Field(
        default_factory=list, description="Education level distribution"
    )
    job_titles: List[str] = Field(
        default_factory=list, description="Common job titles and roles (5-10 items)"
    )
    company_sizes: List[str] = Field(
        default_factory=list,
        description="Company size preferences (e.g., 'startup', 'SMB', 'enterprise')",
    )


class Psychographics(BaseModel):
    """Psychographic profile"""

    values: List[str] = Field(
        default_factory=list, description="Core values and beliefs (5-7 items)"
    )
    interests: List[str] = Field(
        default_factory=list, description="Hobbies and interests (5-10 items)"
    )
    lifestyle: str = Field(..., description="Lifestyle description")
    personality_traits: List[str] = Field(
        default_factory=list, description="Common personality traits (5-7 items)"
    )
    motivations: List[str] = Field(
        default_factory=list, description="Key motivations and drivers (5-7 items)"
    )


class BehavioralProfile(BaseModel):
    """Behavioral patterns"""

    content_consumption: str = Field(..., description="How they consume content")
    preferred_platforms: List[str] = Field(
        default_factory=list,
        description="Preferred social media and content platforms (5-10 items)",
    )
    online_behavior: str = Field(..., description="Online behavior patterns")
    purchase_behavior: str = Field(..., description="Buying behavior and decision process")
    engagement_patterns: str = Field(..., description="How they engage with brands")


class AudienceSegment(BaseModel):
    """A specific audience segment"""

    segment_name: str = Field(..., description="Segment name (e.g., 'Tech-Savvy Entrepreneurs')")
    segment_size: str = Field(..., description="Estimated size (e.g., '35% of total audience')")
    description: str = Field(..., description="Segment description (2-3 sentences)")
    key_characteristics: List[str] = Field(
        default_factory=list, description="Defining characteristics (3-5 items)"
    )
    content_preferences: List[str] = Field(
        default_factory=list, description="Content preferences for this segment (3-5 items)"
    )
    messaging_recommendations: str = Field(..., description="How to message this segment")


class AudienceResearch(BaseModel):
    """Complete audience research report"""

    business_name: str = Field(..., description="Client business name")
    industry: str = Field(..., description="Industry/vertical")
    target_description: str = Field(..., description="Original target audience description")
    analysis_date: str = Field(..., description="Date of analysis")

    # Executive summary
    executive_summary: str = Field(..., description="High-level audience insights (2-3 paragraphs)")
    audience_size_estimate: str = Field(
        ..., description="Estimated total addressable audience size"
    )

    # Demographics
    demographics: Demographics = Field(..., description="Demographic profile")

    # Psychographics
    psychographics: Psychographics = Field(..., description="Psychographic profile")

    # Behavioral
    behavioral_profile: BehavioralProfile = Field(..., description="Behavioral patterns")

    # Pain points
    pain_points: List[str] = Field(
        default_factory=list, description="Top pain points and challenges (7-10 items)"
    )

    # Goals
    goals_aspirations: List[str] = Field(
        default_factory=list, description="Goals and aspirations (7-10 items)"
    )

    # Content preferences
    content_preferences: List[str] = Field(
        default_factory=list, description="Content format and topic preferences (7-10 items)"
    )

    # Decision factors
    decision_factors: List[str] = Field(
        default_factory=list, description="Key decision-making factors (5-7 items)"
    )

    # Information sources
    information_sources: List[str] = Field(
        default_factory=list, description="Where they get information (5-10 sources)"
    )

    # Influencers
    influencers_brands: List[str] = Field(
        default_factory=list, description="Influencers and brands they follow (7-10 items)"
    )

    # Segments
    audience_segments: List[AudienceSegment] = Field(
        default_factory=list, description="3-5 distinct audience segments"
    )

    # Messaging recommendations
    messaging_framework: str = Field(
        ..., description="Overall messaging framework and tone recommendations"
    )

    # Content strategy
    content_strategy_recommendations: List[str] = Field(
        default_factory=list, description="Strategic content recommendations (5-7 items)"
    )

    # Engagement tactics
    engagement_tactics: List[str] = Field(
        default_factory=list, description="Tactics to engage this audience (5-7 items)"
    )

    # Key insights
    key_insights: List[str] = Field(
        default_factory=list, description="Key strategic insights (5-7 items)"
    )

    # Avoid list
    what_to_avoid: List[str] = Field(
        default_factory=list, description="What to avoid with this audience (3-5 items)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "business_name": "Acme Corp",
                "industry": "B2B SaaS",
                "target_description": "Marketing managers at tech companies",
                "analysis_date": "2025-12-07",
                "audience_size_estimate": "2.5M marketing professionals in tech sector",
            }
        }
