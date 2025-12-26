"""
Pydantic schemas for Authentication API.
"""
from __future__ import annotations  # Enable forward references
from pydantic import BaseModel, EmailStr, field_validator
from utils.input_validators import validate_string_field


class LoginRequest(BaseModel):
    """Schema for login request"""

    email: EmailStr
    password: str

    # TR-003: Input validation
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password is not empty"""
        if not v or len(v) < 1:
            raise ValueError("Password cannot be empty")
        if len(v) > 200:
            raise ValueError("Password too long")
        return v


class UserResponse(BaseModel):
    """Schema for user response"""

    id: str
    email: str
    full_name: str
    is_active: bool

    class Config:
        from_attributes = True


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


class UserCreate(BaseModel):
    """Schema for creating a user"""

    email: EmailStr
    password: str
    full_name: str

    # TR-003: Input validation
    @field_validator('password')
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

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Validate full name"""
        return validate_string_field(v, field_name="full_name", min_length=2, max_length=100)
