"""Project and Revision Data Models

Tracks deliverable projects, revision requests, and scope management.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    """Project status"""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class RevisionStatus(str, Enum):
    """Revision request status"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(BaseModel):
    """A content generation project (30 posts deliverable)"""

    project_id: str = Field(
        ..., description="Unique project identifier (ClientName_YYYYMMDD_HHMMSS)"
    )
    client_name: str = Field(..., description="Client name")
    created_at: datetime = Field(default_factory=datetime.now)
    deliverable_path: str = Field(..., description="Path to generated deliverable files")
    brief_path: Optional[str] = Field(None, description="Path to client brief file")
    num_posts: int = Field(..., description="Number of posts generated")
    quality_profile_name: Optional[str] = Field(None, description="Quality profile used")
    status: ProjectStatus = Field(default=ProjectStatus.COMPLETED)
    notes: Optional[str] = Field(None, description="Project notes")

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            "project_id": self.project_id,
            "client_name": self.client_name,
            "created_at": self.created_at.isoformat(),
            "deliverable_path": self.deliverable_path,
            "brief_path": self.brief_path,
            "num_posts": self.num_posts,
            "quality_profile_name": self.quality_profile_name,
            "status": self.status.value,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Create from database dictionary"""
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["status"] = ProjectStatus(data["status"])
        return cls(**data)


class RevisionPost(BaseModel):
    """A single post that was revised"""

    post_index: int = Field(..., description="Post number (1-30)")
    template_id: int = Field(..., description="Template ID used")
    template_name: str = Field(..., description="Template name")
    original_content: str = Field(..., description="Original post content")
    original_word_count: int = Field(..., description="Original word count")
    revised_content: str = Field(..., description="Revised post content")
    revised_word_count: int = Field(..., description="Revised word count")
    changes_summary: Optional[str] = Field(None, description="Summary of changes made")

    def to_dict(self, revision_id: str) -> dict:
        """Convert to dictionary for database storage"""
        return {
            "revision_id": revision_id,
            "post_index": self.post_index,
            "template_id": self.template_id,
            "template_name": self.template_name,
            "original_content": self.original_content,
            "original_word_count": self.original_word_count,
            "revised_content": self.revised_content,
            "revised_word_count": self.revised_word_count,
            "changes_summary": self.changes_summary,
        }


class Revision(BaseModel):
    """A revision request for a project"""

    revision_id: str = Field(..., description="Unique revision identifier")
    project_id: str = Field(..., description="Parent project ID")
    attempt_number: int = Field(..., ge=1, le=10, description="Revision attempt number (1-10)")
    status: RevisionStatus = Field(default=RevisionStatus.PENDING)
    feedback: str = Field(..., description="Client's revision feedback")
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(None, description="When revision was completed")
    cost: float = Field(default=0.0, description="API cost for this revision")
    posts: List[RevisionPost] = Field(default_factory=list, description="Posts that were revised")

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            "revision_id": self.revision_id,
            "project_id": self.project_id,
            "attempt_number": self.attempt_number,
            "status": self.status.value,
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "cost": self.cost,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Revision":
        """Create from database dictionary"""
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        data["status"] = RevisionStatus(data["status"])
        data["posts"] = []  # Posts loaded separately
        return cls(**data)

    def mark_completed(self):
        """Mark revision as completed"""
        self.status = RevisionStatus.COMPLETED
        self.completed_at = datetime.now()

    def mark_failed(self):
        """Mark revision as failed"""
        self.status = RevisionStatus.FAILED
        self.completed_at = datetime.now()


class RevisionScope(BaseModel):
    """Tracks revision scope limits for a project"""

    project_id: str = Field(..., description="Project ID")
    allowed_revisions: int = Field(default=5, description="Allowed revisions per contract")
    used_revisions: int = Field(default=0, description="Revisions used so far")
    scope_exceeded: bool = Field(default=False, description="Whether scope limit exceeded")
    upsell_offered: bool = Field(default=False, description="Whether upsell was offered")
    upsell_accepted: bool = Field(default=False, description="Whether client accepted upsell")

    @property
    def remaining_revisions(self) -> int:
        """Calculate remaining revisions"""
        return max(0, self.allowed_revisions - self.used_revisions)

    @property
    def is_at_limit(self) -> bool:
        """Check if at or over limit"""
        return self.used_revisions >= self.allowed_revisions

    @property
    def is_near_limit(self) -> bool:
        """Check if near limit (1 revision remaining)"""
        return self.remaining_revisions == 1

    def increment_usage(self):
        """Increment revision usage count"""
        self.used_revisions += 1
        if self.used_revisions > self.allowed_revisions:
            self.scope_exceeded = True

    def add_revisions(self, count: int):
        """Add more revisions (after upsell purchase)"""
        self.allowed_revisions += count
        self.scope_exceeded = False
        self.upsell_accepted = True

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            "project_id": self.project_id,
            "allowed_revisions": self.allowed_revisions,
            "used_revisions": self.used_revisions,
            "remaining_revisions": self.remaining_revisions,
            "scope_exceeded": self.scope_exceeded,
            "upsell_offered": self.upsell_offered,
            "upsell_accepted": self.upsell_accepted,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RevisionScope":
        """Create from database dictionary"""
        # Remove remaining_revisions as it's a computed property
        data.pop("remaining_revisions", None)
        return cls(**data)


class RevisionDiff(BaseModel):
    """Represents changes between original and revised post"""

    post_index: int
    template_name: str
    original_length: int
    revised_length: int
    word_count_change: int
    changes: List[str]  # List of specific changes
    improvement_score: Optional[float] = None  # 0.0-1.0 if calculable

    def to_markdown(self) -> str:
        """Generate markdown summary of changes"""
        md = f"### Post #{self.post_index}: {self.template_name}\n\n"
        md += f"**Length:** {self.original_length} → {self.revised_length} words "
        md += f"({self.word_count_change:+d} words)\n\n"

        if self.changes:
            md += "**Changes Made:**\n"
            for change in self.changes:
                md += f"- {change}\n"

        if self.improvement_score:
            md += f"\n**Quality Improvement:** {self.improvement_score*100:.0f}%\n"

        return md
