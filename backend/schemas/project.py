"""
Pydantic schemas for Project API.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator
from backend.utils.input_validators import (
    validate_string_field,
    validate_id_field,
    validate_integer_field,
    validate_float_field,
)


class ProjectBase(BaseModel):
    """Base project schema"""

    name: str
    client_id: str = Field(validation_alias=AliasChoices("clientId", "client_id"))

    # Template selection (NEW: template_quantities replaces templates)
    templates: Optional[List[str]] = None  # DEPRECATED: Legacy support, use template_quantities
    template_quantities: Optional[Dict[str, int]] = Field(
        default=None,
        validation_alias=AliasChoices("templateQuantities", "template_quantities"),
        description="Dict mapping template_id (str) to quantity (int)",
    )
    num_posts: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("numPosts", "num_posts"),
        description="Total post count (auto-calculated from template_quantities)",
    )

    # Pricing (NEW: flexible per-post pricing)
    price_per_post: Optional[float] = Field(
        default=40.0,
        validation_alias=AliasChoices("pricePerPost", "price_per_post"),
        description="Base price per post",
    )
    research_price_per_post: Optional[float] = Field(
        default=0.0,
        validation_alias=AliasChoices("researchPricePerPost", "research_price_per_post"),
        description="Research add-on per post",
    )
    total_price: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("totalPrice", "total_price"),
        description="Total project price (auto-calculated)",
    )

    # Configuration
    platforms: Optional[List[str]] = []
    tone: Optional[str] = "professional"

    model_config = ConfigDict(
        populate_by_name=True,  # Allow both snake_case and camelCase for validation
    )

    # TR-003: Input validation
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate project name (prevent XSS, SQL injection)"""
        return validate_string_field(v, field_name="name", min_length=3, max_length=200)

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, v: str) -> str:
        """Validate client ID format"""
        return validate_id_field(
            v, field_name="client_id", prefix="client-", min_length=8, max_length=50
        )

    @field_validator("num_posts")
    @classmethod
    def validate_num_posts(cls, v: Optional[int]) -> Optional[int]:
        """Validate post count is within reasonable bounds"""
        if v is None:
            return v
        return validate_integer_field(v, field_name="num_posts", min_value=1, max_value=1000)

    @field_validator("price_per_post", "research_price_per_post", "total_price")
    @classmethod
    def validate_prices(cls, v: Optional[float], info) -> Optional[float]:
        """Validate pricing fields are positive"""
        if v is None:
            return v
        return validate_float_field(v, field_name=info.field_name, min_value=0.0, max_value=10000.0)

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, v: Optional[str]) -> Optional[str]:
        """Validate tone field (free-form text for brand voice description)"""
        if v is None:
            return "professional"

        # Tone is free-form text to allow brand-specific descriptions
        # Examples: professional, casual, friendly, innovative, technical, empathetic,
        #          authoritative, educational, motivational, analytical, inspirational, etc.
        return validate_string_field(
            v, field_name="tone", min_length=3, max_length=100, allow_empty=False
        )

    @field_validator("template_quantities")
    @classmethod
    def validate_template_quantities(cls, v: Optional[Dict[str, int]]) -> Optional[Dict[str, int]]:
        """Validate template quantities dict"""
        if v is None:
            return v

        # Check size (DoS prevention)
        if len(v) > 50:
            raise ValueError("template_quantities cannot exceed 50 templates")

        # Validate each entry
        for template_id, quantity in v.items():
            # Validate template ID format
            try:
                template_id_int = int(template_id)
                if template_id_int < 1 or template_id_int > 100:
                    raise ValueError(f"Invalid template_id: {template_id}")
            except ValueError:
                raise ValueError(f"template_id must be numeric: {template_id}")

            # Validate quantity
            validate_integer_field(
                quantity,
                field_name=f"quantity for template {template_id}",
                min_value=0,
                max_value=100,
            )

        return v

    @model_validator(mode="after")
    def calculate_derived_fields(self):
        """Auto-calculate num_posts and total_price from template_quantities"""

        # Calculate num_posts if not provided
        if self.num_posts is None and self.template_quantities:
            self.num_posts = sum(self.template_quantities.values())

        # Calculate total_price if not provided
        if self.total_price is None and self.num_posts and self.num_posts > 0:
            price_per_post = self.price_per_post if self.price_per_post is not None else 40.0
            research_price = (
                self.research_price_per_post if self.research_price_per_post is not None else 0.0
            )
            self.total_price = self.num_posts * (price_per_post + research_price)

        return self


class ProjectCreate(ProjectBase):
    """
    Schema for creating a project.

    TR-022: Mass assignment protection
    - Only allows: name, client_id, templates, template_quantities, num_posts,
                   price_per_post, research_price_per_post, total_price, platforms, tone
    - Protected fields set by system: id, user_id, status, created_at, updated_at
    """

    model_config = ConfigDict(
        populate_by_name=True, extra="forbid"  # TR-022: Reject unknown fields
    )


class ProjectUpdate(BaseModel):
    """
    Schema for updating a project.

    TR-022: Mass assignment protection
    - Only allows: name, status, templates, template_quantities, num_posts,
                   price_per_post, research_price_per_post, total_price, platforms, tone
    - Protected fields (never updatable): id, user_id, client_id, created_at, updated_at
    """

    name: Optional[str] = None
    status: Optional[str] = None

    # Template selection
    templates: Optional[List[str]] = None  # DEPRECATED: Legacy support
    template_quantities: Optional[Dict[str, int]] = Field(
        default=None, validation_alias=AliasChoices("templateQuantities", "template_quantities")
    )
    num_posts: Optional[int] = Field(
        default=None, validation_alias=AliasChoices("numPosts", "num_posts")
    )

    # Pricing
    price_per_post: Optional[float] = Field(
        default=None, validation_alias=AliasChoices("pricePerPost", "price_per_post")
    )
    research_price_per_post: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("researchPricePerPost", "research_price_per_post"),
    )
    total_price: Optional[float] = Field(
        default=None, validation_alias=AliasChoices("totalPrice", "total_price")
    )

    # Configuration
    platforms: Optional[List[str]] = None
    tone: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",  # TR-022: Reject unknown fields like user_id, client_id
    )


class ProjectResponse(ProjectBase):
    """
    Schema for project response.

    TR-022: Includes all fields including read-only ones
    """

    id: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
        alias_generator=lambda field_name: "".join(
            word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split("_"))
        ),  # Convert snake_case to camelCase
    )
