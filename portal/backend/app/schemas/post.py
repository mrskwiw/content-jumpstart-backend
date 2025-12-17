"""Post schemas for request/response validation."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PostUpdate(BaseModel):
    """Schema for updating a post."""

    content: str = Field(..., min_length=1, description="Updated post content")
    status: Optional[str] = Field(None, description="Post status (draft, final, needs_revision)")


class PostResponse(BaseModel):
    """Schema for post response."""

    post_id: str
    project_id: str
    post_number: int
    content: str
    template_name: Optional[str]
    platform: str
    word_count: int
    status: str
    revision_of: Optional[str]
    version: int
    generated_at: datetime
    last_edited_at: Optional[datetime]
    edited_by: Optional[str]

    class Config:
        from_attributes = True  # Enable ORM mode for SQLAlchemy models


class PostListResponse(BaseModel):
    """Schema for listing posts."""

    total: int = Field(..., description="Total number of posts")
    posts: List[PostResponse] = Field(..., description="List of posts")


class GeneratePostsRequest(BaseModel):
    """Schema for generating posts for a project."""

    num_posts: int = Field(default=30, ge=1, le=50, description="Number of posts to generate")
    platform: str = Field(
        default="LinkedIn", description="Target platform (LinkedIn, Twitter, etc.)"
    )
    regenerate: bool = Field(default=False, description="Whether to regenerate existing posts")
