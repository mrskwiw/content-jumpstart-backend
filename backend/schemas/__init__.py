"""
Pydantic schemas for API validation.
"""

from .auth import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserUpdate,
    UserResponse,
)
from .brief import BriefCreate, BriefUpdate, BriefResponse
from .client import ClientCreate, ClientUpdate, ClientResponse
from .deliverable import (
    DeliverableCreate,
    DeliverableUpdate,
    DeliverableResponse,
    MarkDeliveredRequest,
)
from .post import PostCreate, PostUpdate, PostResponse
from .project import ProjectCreate, ProjectResponse, ProjectUpdate
from .research_schemas import (
    VoiceAnalysisParams,
    SEOKeywordParams,
    CompetitiveAnalysisParams,
    ContentGapParams,
    ContentAuditParams,
    ContentPiece,
    MarketTrendsParams,
    PlatformStrategyParams,
    ContentCalendarParams,
    AudienceResearchParams,
    ICPWorkshopParams,
    StoryMiningParams,
    BrandArchetypeParams,
)
from .run import RunCreate, RunUpdate, RunResponse

__all__ = [
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "PostCreate",
    "PostUpdate",
    "PostResponse",
    "DeliverableCreate",
    "DeliverableUpdate",
    "DeliverableResponse",
    "MarkDeliveredRequest",
    "ClientCreate",
    "ClientUpdate",
    "ClientResponse",
    "BriefCreate",
    "BriefUpdate",
    "BriefResponse",
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "RunCreate",
    "RunUpdate",
    "RunResponse",
    # Research tool validation schemas
    "VoiceAnalysisParams",
    "SEOKeywordParams",
    "CompetitiveAnalysisParams",
    "ContentGapParams",
    "ContentAuditParams",
    "ContentPiece",
    "MarketTrendsParams",
    "PlatformStrategyParams",
    "ContentCalendarParams",
    "AudienceResearchParams",
    "ICPWorkshopParams",
    "StoryMiningParams",
    "BrandArchetypeParams",
]
