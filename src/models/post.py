"""Post data model with metadata and quality tracking"""

import re
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

    # Twitter/X share copy (blog posts only, ≤280 chars with [YOUR_BLOG_URL] placeholder)
    twitter_share_copy: Optional[str] = Field(
        None, description="Ready-to-post tweet to drive traffic to this blog post"
    )

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
            # Only auto-calculate if not explicitly set
            if self.word_count == 0:
                self.word_count = len(self.content.split())
            if self.character_count == 0:
                self.character_count = len(self.content)
            # Only auto-detect CTA if has_cta is False (default)
            # This preserves explicitly set has_cta=True values
            if not self.has_cta:
                self.has_cta = self._detect_cta(self.content)

    @staticmethod
    def _detect_cta(content: str) -> bool:
        """Detect if post has a CTA.

        Scans only the final two lines (where CTAs are placed) and uses
        word-boundary regex for short words to avoid false positives from
        substrings like 'already' (read), 'industry' (try), 'started' (start).
        Aligned with CTAValidator.CTA_PATTERNS.
        """
        lines = content.strip().split("\n")
        cta_section = "\n".join(lines[-2:]).lower()

        # Patterns that are specific enough for substring matching
        substring_indicators = [
            "?",  # engagement question (broad; statement CTAs preferred)
            "drop a comment",
            "leave a comment",
            "dm me",
            "message me",
            "reach out",
            "tap the link",
            "check out",
            "set up a call",
            "set up a meeting",
            "sign up",
            "subscribe",
            "get your",
            "get the",
            "learn more",
            "find out",
            "listen to",
            # Soft/service CTAs added to match CTAValidator.CTA_PATTERNS
            "ask us",
            "ask me",
            "ask your",  # covers "ask your dentist/doctor/team/..."
            "ask our team",  # CTAValidator also accepts "our team" form
            "let’s ",  # ASCII apostrophe
            "let’s ",  # right curly quote (common in LLM output)
            "give us a",
            "give me a",
            "give us your",  # CTAValidator accepts give ... your
            "give me your",
        ]
        if any(ind in cta_section for ind in substring_indicators):
            return True

        # Word-boundary patterns for short words that appear inside other words.
        # "appointment" and "consultation" are here (not in substring_indicators)
        # to avoid false matches inside e.g. "disappointment".
        word_patterns = [
            r"\breply\b",
            r"\bcomment\b",
            r"\bcontact\b",
            r"\bclick\b",
            r"\bbook\b",
            r"\bschedule\b",
            r"\bjoin\b",
            r"\bdownload\b",
            r"\bshare\b",
            r"\bread\b",
            r"\bwatch\b",
            r"\btry\b",
            r"\bstart\b",
            r"\bbegin\b",
            r"\bexplore\b",
            r"\bvisit\b",
            r"\bfollow\b",
            r"\bconnect\b",
            r"\bregister\b",
            r"\bapply\b",
            r"\bdm\b",
            r"\bsession\b",
            r"\bappointment\b",
            r"\bconsultation\b",
        ]
        return any(re.search(pat, cta_section) for pat in word_patterns)

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
