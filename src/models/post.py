"""Post data model with metadata and quality tracking"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from .client_brief import Platform


class Post(BaseModel):
    """A generated social media post"""

    # Core Content
    content: str = Field(..., description="The post content")
    template_id: int = Field(..., description="Template used (1-15)")
    template_name: str = Field(..., description="Template name")
    variant: int = Field(1, description="Variant number (1 or 2)")

    # Metadata
    word_count: int = Field(0, description="Word count")
    character_count: int = Field(0, description="Character count")
    has_cta: bool = Field(False, description="Whether post has a CTA")

    # Platform targeting (optional - defaults to LinkedIn)
    target_platform: Optional[Platform] = Field(
        None, description="Target platform (linkedin, twitter, facebook, blog, email)"
    )

    # Blog linking (for cross-platform content)
    related_blog_post_id: Optional[int] = Field(
        None, description="ID of related blog post (for social teasers)"
    )
    blog_link_placeholder: Optional[str] = Field(
        None, description="Link placeholder e.g. [BLOG_LINK_1]"
    )
    blog_title: Optional[str] = Field(None, description="Title of related blog post")

    # Context
    client_name: str = Field(..., description="Client name")
    generated_at: datetime = Field(default_factory=datetime.now, description="Generation timestamp")

    # Quality Flags
    needs_review: bool = Field(False, description="Flagged for manual review")
    review_reason: Optional[str] = Field(None, description="Reason for review flag")

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        """Ensure content is not empty"""
        if not v or not v.strip():
            raise ValueError("Post content cannot be empty")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Calculate fields after initialization"""
        if self.content:
            self.word_count = len(self.content.split())
            self.character_count = len(self.content)
            self.has_cta = self._detect_cta(self.content)

    @staticmethod
    def _detect_cta(content: str) -> bool:
        """Detect if post has a CTA"""
        content_lower = content.lower()
        cta_indicators = [
            "?",
            "reply",
            "comment",
            "share",
            "click",
            "book",
            "sign up",
            "download",
            "learn more",
            "contact",
            "dm me",
            "reach out",
        ]
        return any(indicator in content_lower for indicator in cta_indicators)

    def flag_for_review(self, reason: str) -> None:
        """Flag post for manual review"""
        self.needs_review = True
        self.review_reason = reason

    def to_formatted_string(self, include_metadata: bool = False) -> str:
        """Format post for output"""
        output = f"{self.content}\n"

        if include_metadata:
            output += "\n--- Metadata ---\n"
            output += (
                f"Template: {self.template_name} (#{self.template_id}, Variant {self.variant})\n"
            )
            output += f"Words: {self.word_count} | Characters: {self.character_count}\n"
            if self.target_platform:
                output += f"Platform: {self.target_platform.value}\n"
            output += f"Has CTA: {self.has_cta}\n"
            if self.needs_review:
                output += f"[!] NEEDS REVIEW: {self.review_reason}\n"

        return output
