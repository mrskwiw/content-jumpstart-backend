"""
Pydantic schemas for Client API.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    AliasChoices,
    field_serializer,
)
from backend.schemas.enums import Platform


class ClientBase(BaseModel):
    """Base client schema with camelCase/snake_case bidirectional support"""

    name: str = Field(
        ...,
        validation_alias=AliasChoices("name", "companyName"),
        description="Client company name",
    )
    email: Optional[EmailStr] = Field(
        default=None,
        validation_alias=AliasChoices("email"),
    )
    business_description: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("business_description", "businessDescription"),
    )
    ideal_customer: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ideal_customer", "idealCustomer", "targetAudience"),
    )
    main_problem_solved: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("main_problem_solved", "mainProblemSolved"),
    )
    tone_preference: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("tone_preference", "tonePreference"),
    )
    platforms: Optional[List[Platform]] = Field(
        default=None,
        validation_alias=AliasChoices("platforms"),
    )
    customer_pain_points: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("customer_pain_points", "customerPainPoints"),
    )
    customer_questions: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("customer_questions", "customerQuestions"),
    )
    industry: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("industry"),
    )
    keywords: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("keywords"),
    )
    competitors: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("competitors"),
    )
    location: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("location"),
    )
    founder_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("founder_name", "founderName"),
    )
    brand_personality: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("brand_personality", "brandPersonality"),
    )
    tone_to_avoid: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("tone_to_avoid", "toneToAvoid"),
    )
    data_usage: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("data_usage", "dataUsage"),
    )
    stories: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("stories"),
    )
    misconceptions: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("misconceptions"),
    )
    measurable_results: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("measurable_results", "measurableResults"),
    )
    posting_frequency: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("posting_frequency", "postingFrequency"),
    )
    main_cta: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("main_cta", "mainCta"),
    )
    key_phrases: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("key_phrases", "keyPhrases"),
    )

    model_config = ConfigDict(
        populate_by_name=True,  # Accept both snake_case and camelCase
    )


class ClientCreate(ClientBase):
    """
    Schema for creating a client.

    TR-022: Mass assignment protection
    - Only allows: name, email, business_description, ideal_customer, main_problem_solved,
                   tone_preference, platforms, customer_pain_points, customer_questions
    - Protected fields set by system: id, user_id, created_at
    """

    model_config = ConfigDict(extra="forbid")  # TR-022: Reject unknown fields


class ClientUpdate(BaseModel):
    """
    Schema for updating a client (all fields optional).

    TR-022: Mass assignment protection
    - Only allows: name, email, business_description, ideal_customer, main_problem_solved,
                   tone_preference, platforms, customer_pain_points, customer_questions
    - Protected fields (never updatable): id, user_id, created_at
    """

    name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("name", "companyName"),
    )
    email: Optional[EmailStr] = Field(
        default=None,
        validation_alias=AliasChoices("email"),
    )
    business_description: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("business_description", "businessDescription"),
    )
    ideal_customer: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ideal_customer", "idealCustomer", "targetAudience"),
    )
    main_problem_solved: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("main_problem_solved", "mainProblemSolved"),
    )
    tone_preference: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("tone_preference", "tonePreference"),
    )
    platforms: Optional[List[Platform]] = Field(
        default=None,
        validation_alias=AliasChoices("platforms"),
    )
    customer_pain_points: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("customer_pain_points", "customerPainPoints"),
    )
    customer_questions: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("customer_questions", "customerQuestions"),
    )
    industry: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("industry"),
    )
    keywords: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("keywords"),
    )
    competitors: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("competitors"),
    )
    location: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("location"),
    )
    founder_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("founder_name", "founderName"),
    )
    brand_personality: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("brand_personality", "brandPersonality"),
    )
    tone_to_avoid: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("tone_to_avoid", "toneToAvoid"),
    )
    data_usage: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("data_usage", "dataUsage"),
    )
    stories: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("stories"),
    )
    misconceptions: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("misconceptions"),
    )
    measurable_results: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("measurable_results", "measurableResults"),
    )
    posting_frequency: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("posting_frequency", "postingFrequency"),
    )
    main_cta: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("main_cta", "mainCta"),
    )
    key_phrases: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("key_phrases", "keyPhrases"),
    )

    model_config = ConfigDict(
        populate_by_name=True,  # Accept both snake_case and camelCase
        extra="forbid",  # TR-022: Reject unknown fields like user_id
    )


class ClientResponse(BaseModel):
    """
    Schema for client response.

    TR-022: Includes all fields including read-only ones
    """

    id: str
    name: str = Field(..., serialization_alias="companyName")
    email: Optional[EmailStr] = None
    business_description: Optional[str] = Field(
        default=None, serialization_alias="businessDescription"
    )
    ideal_customer: Optional[str] = Field(default=None, serialization_alias="idealCustomer")
    main_problem_solved: Optional[str] = Field(
        default=None, serialization_alias="mainProblemSolved"
    )
    tone_preference: Optional[str] = Field(default=None, serialization_alias="tonePreference")
    platforms: Optional[List[Platform]] = None
    customer_pain_points: Optional[List[str]] = Field(
        default=None, serialization_alias="customerPainPoints"
    )
    customer_questions: Optional[List[str]] = Field(
        default=None, serialization_alias="customerQuestions"
    )
    industry: Optional[str] = None
    keywords: Optional[List[str]] = None
    competitors: Optional[List[str]] = None
    location: Optional[str] = None
    founder_name: Optional[str] = Field(default=None, serialization_alias="founderName")
    brand_personality: Optional[List[str]] = Field(
        default=None, serialization_alias="brandPersonality"
    )
    tone_to_avoid: Optional[str] = Field(default=None, serialization_alias="toneToAvoid")
    data_usage: Optional[str] = Field(default=None, serialization_alias="dataUsage")
    stories: Optional[List[str]] = None
    misconceptions: Optional[List[str]] = None
    measurable_results: Optional[str] = Field(default=None, serialization_alias="measurableResults")
    posting_frequency: Optional[str] = Field(default=None, serialization_alias="postingFrequency")
    main_cta: Optional[str] = Field(default=None, serialization_alias="mainCta")
    key_phrases: Optional[List[str]] = Field(default=None, serialization_alias="keyPhrases")
    created_at: datetime = Field(..., serialization_alias="createdAt")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
    )

    @field_serializer("created_at")
    def serialize_datetime(self, value, _info):
        """Serialize datetime with UTC timezone."""
        if value is None:
            return None
        from datetime import timezone

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
