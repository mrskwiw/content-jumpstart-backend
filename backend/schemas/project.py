"""
Pydantic schemas for Project API.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    field_serializer,
)
from backend.schemas.enums import Platform
from backend.utils.input_validators import (
    validate_string_field,
    validate_id_field,
    validate_integer_field,
    validate_float_field,
)
from src.config.pricing import KNOWN_TOOL_IDS, PricingConfig, calculate_tools_cost


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
        default=PricingConfig().PRICE_PER_POST,
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

    # Pricing breakdown fields (granular cost tracking)
    posts_cost: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("postsCost", "posts_cost"),
        description="Post generation cost (num_posts * price_per_post)",
    )
    research_addon_cost: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("researchAddonCost", "research_addon_cost"),
        description="Per-post topic research cost (num_posts * research_price_per_post)",
    )
    tools_cost: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("toolsCost", "tools_cost"),
        description="Research tool cost after bundle discounts",
    )
    discount_amount: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("discountAmount", "discount_amount"),
        description="Bundle discount savings amount",
    )
    selected_tools: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("selectedTools", "selected_tools"),
        description="List of selected research tool IDs",
    )

    # Configuration - None defaults so actual DB values are not overridden
    platforms: Optional[List[Platform]] = None
    target_platform: Optional[Platform] = Field(  # type: ignore[assignment]
        default="blog",
        validation_alias=AliasChoices("targetPlatform", "target_platform"),
        description="Single target platform for generation optimization",
    )
    tone: Optional[str] = None

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
            return v

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

    @field_validator("selected_tools")
    @classmethod
    def validate_selected_tools(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate selected_tools: max 20 items, each must be a known tool ID."""
        if v is None:
            return v

        if len(v) > 20:
            raise ValueError("selected_tools cannot contain more than 20 items")

        unknown = [tid for tid in v if tid not in KNOWN_TOOL_IDS]
        if unknown:
            raise ValueError(f"Unknown tool IDs: {', '.join(unknown)}")

        return v

    @model_validator(mode="after")
    def calculate_derived_fields(self):
        """Auto-calculate pricing breakdown fields from inputs."""

        # --- num_posts ---
        if self.num_posts is None and self.template_quantities:
            self.num_posts = sum(self.template_quantities.values())

        price_per_post = (
            self.price_per_post
            if self.price_per_post is not None
            else PricingConfig().PRICE_PER_POST
        )
        research_price = (
            self.research_price_per_post if self.research_price_per_post is not None else 0.0
        )
        num_posts = self.num_posts or 0

        # --- posts_cost ---
        if self.posts_cost is None and num_posts > 0:
            self.posts_cost = num_posts * price_per_post

        # --- research_addon_cost ---
        if self.research_addon_cost is None:
            self.research_addon_cost = num_posts * research_price if research_price > 0 else 0.0

        # --- tools_cost / discount_amount from selected_tools ---
        if self.selected_tools is not None and self.tools_cost is None:
            result = calculate_tools_cost(self.selected_tools)
            self.tools_cost = result["tools_cost"]
            self.discount_amount = result["discount_amount"]

        # --- total_price ---
        if self.total_price is None and num_posts > 0:
            self.total_price = (
                (self.posts_cost or 0.0)
                + (self.research_addon_cost or 0.0)
                + (self.tools_cost or 0.0)
            )

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

    # Pricing breakdown fields
    posts_cost: Optional[float] = Field(
        default=None, validation_alias=AliasChoices("postsCost", "posts_cost")
    )
    research_addon_cost: Optional[float] = Field(
        default=None, validation_alias=AliasChoices("researchAddonCost", "research_addon_cost")
    )
    tools_cost: Optional[float] = Field(
        default=None, validation_alias=AliasChoices("toolsCost", "tools_cost")
    )
    discount_amount: Optional[float] = Field(
        default=None, validation_alias=AliasChoices("discountAmount", "discount_amount")
    )
    selected_tools: Optional[List[str]] = Field(
        default=None, validation_alias=AliasChoices("selectedTools", "selected_tools")
    )

    # Configuration
    platforms: Optional[List[Platform]] = None
    target_platform: Optional[Platform] = Field(
        default=None, validation_alias=AliasChoices("targetPlatform", "target_platform")
    )
    tone: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",  # TR-022: Reject unknown fields like user_id, client_id
    )

    # TR-003: Input validation (same as ProjectBase)
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate project name if provided"""
        if v is None:
            return v
        return validate_string_field(v, field_name="name", min_length=3, max_length=200)

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
        """Validate tone field if provided"""
        if v is None:
            return v
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

    @field_validator("selected_tools")
    @classmethod
    def validate_selected_tools(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate selected_tools: max 20 items, each must be a known tool ID."""
        if v is None:
            return v

        if len(v) > 20:
            raise ValueError("selected_tools cannot contain more than 20 items")

        unknown = [tid for tid in v if tid not in KNOWN_TOOL_IDS]
        if unknown:
            raise ValueError(f"Unknown tool IDs: {', '.join(unknown)}")

        return v


class ProjectResponse(BaseModel):
    """
    Schema for project response.

    TR-022: Includes all fields including read-only ones
    """

    id: str
    name: str
    client_id: str = Field(..., serialization_alias="clientId")

    # Template selection
    templates: Optional[List[str]] = None  # DEPRECATED: Legacy support
    template_quantities: Optional[Dict[str, int]] = Field(
        default=None, serialization_alias="templateQuantities"
    )
    num_posts: Optional[int] = Field(default=None, serialization_alias="numPosts")

    # Pricing
    price_per_post: Optional[float] = Field(
        default=PricingConfig().PRICE_PER_POST, serialization_alias="pricePerPost"
    )
    research_price_per_post: Optional[float] = Field(
        default=0.0, serialization_alias="researchPricePerPost"
    )
    total_price: Optional[float] = Field(default=None, serialization_alias="totalPrice")

    # Pricing breakdown
    posts_cost: Optional[float] = Field(default=None, serialization_alias="postsCost")
    research_addon_cost: Optional[float] = Field(
        default=None, serialization_alias="researchAddonCost"
    )
    tools_cost: Optional[float] = Field(default=None, serialization_alias="toolsCost")
    discount_amount: Optional[float] = Field(default=None, serialization_alias="discountAmount")
    selected_tools: Optional[List[str]] = Field(default=None, serialization_alias="selectedTools")

    # Configuration
    platforms: Optional[List[Platform]] = None
    target_platform: Optional[Platform] = Field(  # type: ignore[assignment]
        default="blog", serialization_alias="targetPlatform"
    )
    tone: Optional[str] = None

    # Status and timestamps
    status: str
    created_at: datetime = Field(..., serialization_alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, serialization_alias="updatedAt")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
    )

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value, _info):
        """Serialize datetime with UTC timezone."""
        if value is None:
            return None
        from datetime import timezone

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
