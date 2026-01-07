"""
Pydantic schemas for Authentication API.
"""

from __future__ import annotations  # Enable forward references
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from backend.utils.input_validators import validate_string_field


class LoginRequest(BaseModel):
    """Schema for login request"""

    email: EmailStr
    password: str

    # TR-003: Input validation
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password is not empty"""
        if not v or len(v) < 1:
            raise ValueError("Password cannot be empty")
        if len(v) > 200:
            raise ValueError("Password too long")
        return v


class UserCreate(BaseModel):
    """
    Schema for creating a user.

    TR-022: Mass assignment protection
    - Only allows: email, password, full_name
    - Protected fields set by system: id, is_active, is_superuser, created_at, updated_at
    """

    email: EmailStr
    password: str
    full_name: str

    model_config = ConfigDict(extra="forbid")  # TR-022: Reject unknown fields

    # TR-003: Input validation
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if not v or len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 200:
            raise ValueError("Password too long (max 200 characters)")

        # Check for minimum complexity
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit"
            )

        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Validate full name"""
        return validate_string_field(v, field_name="full_name", min_length=2, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        """
        Optional: Restrict registration to specific email domains (TR-023).

        To enable domain restrictions, uncomment and configure the allowed_domains list.
        This is useful for internal tools where only company emails should register.

        Example:
            allowed_domains = ['company.com', 'example.com']
            domain = v.split('@')[1].lower()
            if domain not in allowed_domains:
                raise ValueError(
                    f'Registration restricted to domains: {", ".join(allowed_domains)}'
                )
        """
        # TR-023: Email domain restriction (disabled by default)
        # Uncomment this block to restrict registration to specific domains:
        #
        # allowed_domains = ['company.com', 'example.com']
        # domain = v.split('@')[1].lower()
        # if domain not in allowed_domains:
        #     raise ValueError(
        #         f'Registration restricted to domains: {", ".join(allowed_domains)}'
        #     )

        return v.lower()  # Normalize email to lowercase


class UserUpdate(BaseModel):
    """
    Schema for updating a user (all fields optional).

    TR-022: Mass assignment protection
    - Only allows: email, full_name
    - Protected fields (never updatable): id, hashed_password, is_active, is_superuser, created_at, updated_at
    - Password changes must use separate change-password endpoint
    """

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None

    model_config = ConfigDict(extra="forbid")  # TR-022: Reject unknown fields like is_superuser

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate full name if provided"""
        if v is None:
            return v
        return validate_string_field(v, field_name="full_name", min_length=2, max_length=100)


class UserResponse(BaseModel):
    """
    Schema for user response.

    TR-022: Includes all fields including read-only ones
    """

    id: str
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema for token response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse  # Include user data in login response


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""

    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Schema for refresh token response (does not include user)"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
