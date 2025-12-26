"""
Shared enums for API schemas.
"""
from enum import Enum


class Platform(str, Enum):
    """Social media platforms supported by the system"""

    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    BLOG = "blog"
    EMAIL = "email"
    GENERIC = "generic"  # Generic/multi-platform content


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
