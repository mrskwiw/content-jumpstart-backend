"""API endpoints package."""

from .auth import router as auth_router
from .briefs import router as briefs_router
from .deliverables import router as deliverables_router
from .posts import router as posts_router
from .projects import router as projects_router
from .uploads import router as uploads_router

__all__ = [
    "auth_router",
    "projects_router",
    "briefs_router",
    "uploads_router",
    "deliverables_router",
    "posts_router",
]
