"""Brief schemas for request/response validation."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class BriefCreate(BaseModel):
    """Schema for creating a new brief."""

    project_id: str = Field(..., description="Associated project ID")

    # Voice & Tone
    tone_descriptors: Optional[List[str]] = Field(
        None, description="List of tone descriptors (e.g., professional, friendly)"
    )
    voice_notes: Optional[str] = Field(None, description="Additional voice guidance")

    # Audience (ICP)
    audience_type: Optional[str] = Field(None, description="Target audience type")
    audience_title: Optional[str] = Field(None, description="Job title of target audience")
    audience_industry: Optional[str] = Field(None, description="Industry vertical")
    pain_points: Optional[List[str]] = Field(None, description="List of audience pain points")

    # Topics & Content
    key_topics: Optional[List[str]] = Field(None, max_length=5, description="Up to 5 key topics")
    content_examples: Optional[str] = Field(None, description="Links to existing content examples")

    # Platform & Goals
    target_platforms: Optional[List[str]] = Field(None, description="Target social platforms")
    posting_frequency: Optional[str] = Field(None, description="Desired posting cadence")
    conversion_goal: Optional[str] = Field(None, description="Main conversion objective")
    cta_preference: Optional[str] = Field(None, description="CTA style preference")

    # Stories
    customer_stories: Optional[List[str]] = Field(None, description="Customer success stories")
    personal_stories: Optional[List[str]] = Field(None, description="Personal/founder stories")


class BriefUpdate(BaseModel):
    """Schema for updating brief fields."""

    # Voice & Tone
    tone_descriptors: Optional[List[str]] = Field(None, description="List of tone descriptors")
    voice_notes: Optional[str] = Field(None, description="Additional voice guidance")

    # Audience (ICP)
    audience_type: Optional[str] = Field(None, description="Target audience type")
    audience_title: Optional[str] = Field(None, description="Job title of target audience")
    audience_industry: Optional[str] = Field(None, description="Industry vertical")
    pain_points: Optional[List[str]] = Field(None, description="List of audience pain points")

    # Topics & Content
    key_topics: Optional[List[str]] = Field(None, max_length=5, description="Up to 5 key topics")
    content_examples: Optional[str] = Field(None, description="Links to existing content examples")

    # Platform & Goals
    target_platforms: Optional[List[str]] = Field(None, description="Target social platforms")
    posting_frequency: Optional[str] = Field(None, description="Desired posting cadence")
    conversion_goal: Optional[str] = Field(None, description="Main conversion objective")
    cta_preference: Optional[str] = Field(None, description="CTA style preference")

    # Stories
    customer_stories: Optional[List[str]] = Field(None, description="Customer success stories")
    personal_stories: Optional[List[str]] = Field(None, description="Personal/founder stories")


class BriefResponse(BaseModel):
    """Schema for brief response."""

    brief_id: str
    project_id: str

    # Voice & Tone
    tone_descriptors: Optional[List[str]]
    voice_notes: Optional[str]

    # Audience (ICP)
    audience_type: Optional[str]
    audience_title: Optional[str]
    audience_industry: Optional[str]
    pain_points: Optional[List[str]]

    # Topics & Content
    key_topics: Optional[List[str]]
    content_examples: Optional[str]

    # Platform & Goals
    target_platforms: Optional[List[str]]
    posting_frequency: Optional[str]
    conversion_goal: Optional[str]
    cta_preference: Optional[str]

    # Stories
    customer_stories: Optional[List[str]]
    personal_stories: Optional[List[str]]

    created_at: datetime

    class Config:
        from_attributes = True  # Enable ORM mode for SQLAlchemy models

    @classmethod
    def model_validate(cls, obj):
        """
        Convert SQLAlchemy model to Pydantic schema.
        Handles JSON string fields by parsing them to lists.
        """
        import json

        # Helper function to parse JSON strings
        def parse_json_field(value):
            if value is None:
                return None
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return None
            return value

        return cls(
            brief_id=obj.brief_id,
            project_id=obj.project_id,
            tone_descriptors=parse_json_field(obj.tone_descriptors),
            voice_notes=obj.voice_notes,
            audience_type=obj.audience_type,
            audience_title=obj.audience_title,
            audience_industry=obj.audience_industry,
            pain_points=parse_json_field(obj.pain_points),
            key_topics=parse_json_field(obj.key_topics),
            content_examples=obj.content_examples,
            target_platforms=parse_json_field(obj.target_platforms),
            posting_frequency=obj.posting_frequency,
            conversion_goal=obj.conversion_goal,
            cta_preference=obj.cta_preference,
            customer_stories=parse_json_field(obj.customer_stories),
            personal_stories=parse_json_field(obj.personal_stories),
            created_at=obj.created_at,
        )
