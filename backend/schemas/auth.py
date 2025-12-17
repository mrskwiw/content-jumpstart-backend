"""
Pydantic schemas for Authentication API.
"""
from __future__ import annotations  # Enable forward references
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Schema for login request"""

    email: EmailStr
    password: str


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


class UserCreate(BaseModel):
    """Schema for creating a user"""

    email: EmailStr
    password: str
    full_name: str
