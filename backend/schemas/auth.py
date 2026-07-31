"""
Pydantic schemas for Authentication API.
"""

from __future__ import annotations  # Enable forward references
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, field_serializer
from backend.utils.input_validators import validate_string_field


class LoginRequest(BaseModel):
    """Schema for login request"""

    email: EmailStr
    password: str
    # Bug #126: optional TOTP code for MFA-enabled accounts
    totp_code: Optional[str] = None

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
    # S-01.4f: True when the operator must set their own password (control-plane
    # seeded admin on first login). The frontend forces a reset while this is set.
    must_change_password: bool = False

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=lambda field_name: "".join(
            word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split("_"))
        ),
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


class TokenResponse(BaseModel):
    """Schema for token response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse  # Include user data in login response
    # Set when a policy-required account has not yet configured MFA.
    # mfa_setup_token is a 15-min limited token accepted ONLY by /mfa/enroll.
    # access_token and refresh_token will be empty strings in this case.
    mfa_setup_required: bool = False
    mfa_setup_token: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""

    refresh_token: str


class LogoutRequest(BaseModel):
    """Schema for server-side logout (GAP-AUTH-03).

    ``refresh_token`` is optional — when supplied it is blacklisted alongside the
    caller's current access token so a stored refresh token can't outlive logout.
    """

    refresh_token: Optional[str] = None


class RefreshTokenResponse(BaseModel):
    """Schema for refresh token response (does not include user)"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserStatsResponse(BaseModel):
    """Schema for user statistics response (admin only)"""

    total: int
    active: int
    inactive: int
    admins: int


class AdminUserCreate(BaseModel):
    """
    Schema for admin creating a user.

    Extends UserCreate to allow setting is_superuser.
    Only admins can use this endpoint.
    """

    email: EmailStr
    password: str
    full_name: str
    is_superuser: bool = False

    model_config = ConfigDict(extra="forbid")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if not v or len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 200:
            raise ValueError("Password too long (max 200 characters)")

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
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase"""
        return v.lower()


class ChangePasswordRequest(BaseModel):
    """
    Schema for a user changing their OWN password (self-service).

    Requires the current password for re-authentication and enforces the
    strong-password policy on the new password.
    """

    current_password: str
    new_password: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate new password strength (mirrors PasswordResetRequest)."""
        if not v or len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 200:
            raise ValueError("Password too long (max 200 characters)")

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit"
            )

        return v


class PasswordResetRequest(BaseModel):
    """
    Schema for admin resetting a user's password.

    Admin-only endpoint to reset user passwords.
    Enforces password strength requirements.
    """

    new_password: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if not v or len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 200:
            raise ValueError("Password too long (max 200 characters)")

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit"
            )

        return v


class ForgotPasswordRequest(BaseModel):
    """
    Schema for requesting a self-service password-reset link (GAP-AUTH-01).

    Only the email is accepted. The endpoint always returns a generic success
    response regardless of whether the email maps to an account, so this schema
    intentionally reveals nothing.
    """

    email: EmailStr

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase (matches registration/login handling)."""
        return v.lower()


class ResetPasswordRequest(BaseModel):
    """
    Schema for completing a self-service password reset (GAP-AUTH-01).

    ``token`` is the single-use "password_reset" JWT delivered by email;
    ``new_password`` must satisfy the same strength rules as every other
    password-setting path.
    """

    token: str
    new_password: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate new password strength (mirrors ChangePasswordRequest)."""
        if not v or len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 200:
            raise ValueError("Password too long (max 200 characters)")

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit"
            )

        return v
