"""
Shared enums for API schemas.
"""

from enum import Enum


class Platform(str, Enum):
    """Social media platforms supported by the system"""

    LINKEDIN = "linkedin"
    LINKEDIN_POSTS = "linkedin-posts"
    LINKEDIN_ARTICLES = "linkedin-articles"
    TWITTER = "twitter"
    TWITTER_THREADS = "twitter-threads"
    FACEBOOK = "facebook"
    BLOG = "blog"
    EMAIL = "email"
    GENERIC = "generic"  # Generic/multi-platform content
    DOCX = "docx"  # Export format
    MARKDOWN = "markdown"  # Export format
    TXT = "txt"  # Export format


class PostStatus(str, Enum):
    """Post status values"""

    PENDING = "pending"
    FLAGGED = "flagged"
    APPROVED = "approved"
    REGENERATING = "regenerating"


class ProjectStatus(str, Enum):
    """Project status values"""

    DRAFT = "draft"
    READY = "ready"
    GENERATING = "generating"
    QA = "qa"
    EXPORTED = "exported"
    DELIVERED = "delivered"
    ERROR = "error"


class DeliverableStatus(str, Enum):
    """Deliverable status values"""

    DRAFT = "draft"
    READY = "ready"
    DELIVERED = "delivered"
