"""Client Memory Data Models

Tracks client preferences, patterns, and learnings across multiple projects.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ClientMemory(BaseModel):
    """Aggregated memory for a client across all projects"""

    # Identity
    client_name: str = Field(..., description="Client name")

    # Project history
    total_projects: int = Field(default=0, ge=0, description="Total number of projects completed")
    total_posts_generated: int = Field(
        default=0, ge=0, description="Total posts generated across all projects"
    )
    total_revisions: int = Field(
        default=0, ge=0, description="Total revision requests across all projects"
    )

    # Dates
    first_project_date: Optional[datetime] = Field(None, description="Date of first project")
    last_project_date: Optional[datetime] = Field(None, description="Date of most recent project")
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Last update to memory"
    )

    # Template preferences (learned from revision patterns)
    preferred_templates: List[int] = Field(
        default_factory=list, description="Template IDs that work well (low revision rate)"
    )
    avoided_templates: List[int] = Field(
        default_factory=list, description="Template IDs that get revised frequently"
    )
    template_performance: Dict[int, float] = Field(
        default_factory=dict, description="template_id -> revision_rate mapping"
    )

    # Voice adjustments (learned from feedback)
    voice_adjustments: Dict[str, str] = Field(
        default_factory=dict, description="Persistent voice tweaks"
    )
    # Example: {"tone": "more_casual", "length": "shorter", "data_usage": "minimal", "emoji": "add"}

    # Structural preferences
    optimal_word_count_min: int = Field(
        default=150, ge=75, le=200, description="Minimum optimal word count for this client"
    )
    optimal_word_count_max: int = Field(
        default=250, ge=200, le=350, description="Maximum optimal word count for this client"
    )
    preferred_cta_types: List[str] = Field(
        default_factory=list, description="Preferred CTA types: question, engagement, direct"
    )

    # Voice patterns (synthesized from voice_samples)
    voice_archetype: Optional[str] = Field(
        None, description="Brand archetype: Expert, Friend, Innovator, Guide, Motivator"
    )
    average_readability_score: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Average Flesch Reading Ease score"
    )
    signature_phrases: List[str] = Field(
        default_factory=list, description="Client's consistent phrases across projects"
    )

    # Quality profile evolution
    custom_quality_profile_json: Optional[str] = Field(
        None, description="JSON-serialized custom QualityProfile"
    )

    # Business metrics
    lifetime_value: float = Field(default=0.0, ge=0.0, description="Total revenue from this client")
    average_satisfaction: Optional[float] = Field(
        None, ge=1.0, le=10.0, description="Average satisfaction score (1-10)"
    )
    next_project_discount: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Discount percentage for next project (0.0-1.0)"
    )

    # Notes
    notes: Optional[str] = Field(None, description="Additional notes about this client")

    @property
    def is_repeat_client(self) -> bool:
        """Check if this is a repeat client (has completed at least one project)"""
        return self.total_projects > 0

    @property
    def avg_revisions_per_project(self) -> float:
        """Calculate average revisions per project"""
        if self.total_projects == 0:
            return 0.0
        return round(self.total_revisions / self.total_projects, 2)

    @property
    def is_high_value_client(self) -> bool:
        """Check if this is a high-value client (3+ projects or $5k+ LTV)"""
        return self.total_projects >= 3 or self.lifetime_value >= 5000.0

    def add_project(
        self, num_posts: int, project_value: float, project_date: Optional[datetime] = None
    ):
        """Update memory after completing a project

        Args:
            num_posts: Number of posts in this project
            project_value: Revenue from this project
            project_date: Project completion date (defaults to now)
        """
        self.total_projects += 1
        self.total_posts_generated += num_posts
        self.lifetime_value += project_value

        if project_date is None:
            project_date = datetime.now()

        if self.first_project_date is None:
            self.first_project_date = project_date

        self.last_project_date = project_date
        self.last_updated = datetime.now()

    def add_revisions(self, revision_count: int):
        """Update memory after revisions

        Args:
            revision_count: Number of revisions for this project
        """
        self.total_revisions += revision_count
        self.last_updated = datetime.now()

    def update_template_preference(self, template_id: int, revision_rate: float):
        """Update template performance tracking

        Args:
            template_id: Template ID
            revision_rate: Revision rate for this template (0.0-1.0)
        """
        self.template_performance[template_id] = revision_rate

        # Update preferred/avoided lists
        if revision_rate <= 0.2 and template_id not in self.preferred_templates:
            # Low revision rate = good template
            self.preferred_templates.append(template_id)
            # Remove from avoided if it was there
            if template_id in self.avoided_templates:
                self.avoided_templates.remove(template_id)

        elif revision_rate >= 0.5 and template_id not in self.avoided_templates:
            # High revision rate = problematic template
            self.avoided_templates.append(template_id)
            # Remove from preferred if it was there
            if template_id in self.preferred_templates:
                self.preferred_templates.remove(template_id)

        self.last_updated = datetime.now()

    def update_voice_adjustment(self, adjustment_type: str, adjustment_value: str):
        """Add or update a voice adjustment

        Args:
            adjustment_type: Type of adjustment (tone, length, data_usage, emoji, etc.)
            adjustment_value: Adjustment value ("more_casual", "shorter", etc.)
        """
        self.voice_adjustments[adjustment_type] = adjustment_value
        self.last_updated = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            "client_name": self.client_name,
            "total_projects": self.total_projects,
            "total_posts_generated": self.total_posts_generated,
            "total_revisions": self.total_revisions,
            "first_project_date": self.first_project_date.isoformat()
            if self.first_project_date
            else None,
            "last_project_date": self.last_project_date.isoformat()
            if self.last_project_date
            else None,
            "last_updated": self.last_updated.isoformat(),
            "preferred_templates": json.dumps(self.preferred_templates),
            "avoided_templates": json.dumps(self.avoided_templates),
            "voice_adjustments": json.dumps(self.voice_adjustments),
            "optimal_word_count_min": self.optimal_word_count_min,
            "optimal_word_count_max": self.optimal_word_count_max,
            "preferred_cta_types": json.dumps(self.preferred_cta_types),
            "voice_archetype": self.voice_archetype,
            "average_readability_score": self.average_readability_score,
            "signature_phrases": json.dumps(self.signature_phrases),
            "custom_quality_profile_json": self.custom_quality_profile_json,
            "lifetime_value": self.lifetime_value,
            "average_satisfaction": self.average_satisfaction,
            "next_project_discount": self.next_project_discount,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClientMemory":
        """Create from database dictionary"""
        # Parse JSON fields
        if isinstance(data.get("preferred_templates"), str):
            try:
                data["preferred_templates"] = json.loads(data["preferred_templates"])
            except (json.JSONDecodeError, TypeError):
                data["preferred_templates"] = []

        if isinstance(data.get("avoided_templates"), str):
            try:
                data["avoided_templates"] = json.loads(data["avoided_templates"])
            except (json.JSONDecodeError, TypeError):
                data["avoided_templates"] = []

        if isinstance(data.get("voice_adjustments"), str):
            try:
                data["voice_adjustments"] = json.loads(data["voice_adjustments"])
            except (json.JSONDecodeError, TypeError):
                data["voice_adjustments"] = {}

        if isinstance(data.get("preferred_cta_types"), str):
            try:
                data["preferred_cta_types"] = json.loads(data["preferred_cta_types"])
            except (json.JSONDecodeError, TypeError):
                data["preferred_cta_types"] = []

        if isinstance(data.get("signature_phrases"), str):
            try:
                data["signature_phrases"] = json.loads(data["signature_phrases"])
            except (json.JSONDecodeError, TypeError):
                data["signature_phrases"] = []

        # Parse timestamps
        if data.get("first_project_date") and isinstance(data["first_project_date"], str):
            data["first_project_date"] = datetime.fromisoformat(data["first_project_date"])

        if data.get("last_project_date") and isinstance(data["last_project_date"], str):
            data["last_project_date"] = datetime.fromisoformat(data["last_project_date"])

        if data.get("last_updated") and isinstance(data["last_updated"], str):
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])

        return cls(**data)


class FeedbackTheme(BaseModel):
    """A recurring feedback pattern detected across revisions"""

    theme_type: str = Field(
        ..., description="Theme category: tone, length, cta, data_usage, structure, emoji"
    )
    feedback_phrase: str = Field(..., description="Actual feedback phrase from client")
    occurrence_count: int = Field(
        default=1, ge=1, description="Number of times this theme appeared"
    )
    first_seen: datetime = Field(default_factory=datetime.now, description="First occurrence")
    last_seen: datetime = Field(default_factory=datetime.now, description="Most recent occurrence")

    def increment(self):
        """Increment occurrence count and update last_seen"""
        self.occurrence_count += 1
        self.last_seen = datetime.now()

    def to_dict(self, client_name: str) -> dict:
        """Convert to dictionary for database storage"""
        return {
            "client_name": client_name,
            "theme_type": self.theme_type,
            "feedback_phrase": self.feedback_phrase,
            "occurrence_count": self.occurrence_count,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FeedbackTheme":
        """Create from database dictionary"""
        # Parse timestamps
        if data.get("first_seen") and isinstance(data["first_seen"], str):
            data["first_seen"] = datetime.fromisoformat(data["first_seen"])

        if data.get("last_seen") and isinstance(data["last_seen"], str):
            data["last_seen"] = datetime.fromisoformat(data["last_seen"])

        # Remove client_name as it's not part of the model
        data.pop("client_name", None)

        return cls(**data)


class VoiceSample(BaseModel):
    """Voice analysis snapshot from a completed project"""

    client_name: str = Field(..., description="Client name")
    project_id: str = Field(..., description="Project ID")
    generated_at: datetime = Field(default_factory=datetime.now, description="Analysis timestamp")

    # Voice Metrics
    average_readability: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Flesch Reading Ease"
    )
    voice_archetype: Optional[str] = Field(
        None, description="Expert, Friend, Innovator, Guide, Motivator"
    )
    dominant_tone: Optional[str] = Field(None, description="Dominant tone from voice guide")
    average_word_count: int = Field(default=0, ge=0, description="Average post length")
    question_usage_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="% of posts with questions"
    )

    # Patterns (stored as lists)
    common_hooks: List[str] = Field(default_factory=list, description="Opening hook patterns")
    common_transitions: List[str] = Field(default_factory=list, description="Transition phrases")
    common_ctas: List[str] = Field(default_factory=list, description="CTA patterns")
    key_phrases: List[str] = Field(default_factory=list, description="Recurring key phrases")

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            "client_name": self.client_name,
            "project_id": self.project_id,
            "generated_at": self.generated_at.isoformat(),
            "average_readability": self.average_readability,
            "voice_archetype": self.voice_archetype,
            "dominant_tone": self.dominant_tone,
            "average_word_count": self.average_word_count,
            "question_usage_rate": self.question_usage_rate,
            "common_hooks": json.dumps(self.common_hooks),
            "common_transitions": json.dumps(self.common_transitions),
            "common_ctas": json.dumps(self.common_ctas),
            "key_phrases": json.dumps(self.key_phrases),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceSample":
        """Create from database dictionary"""
        # Parse JSON fields
        if isinstance(data.get("common_hooks"), str):
            try:
                data["common_hooks"] = json.loads(data["common_hooks"])
            except (json.JSONDecodeError, TypeError):
                data["common_hooks"] = []

        if isinstance(data.get("common_transitions"), str):
            try:
                data["common_transitions"] = json.loads(data["common_transitions"])
            except (json.JSONDecodeError, TypeError):
                data["common_transitions"] = []

        if isinstance(data.get("common_ctas"), str):
            try:
                data["common_ctas"] = json.loads(data["common_ctas"])
            except (json.JSONDecodeError, TypeError):
                data["common_ctas"] = []

        if isinstance(data.get("key_phrases"), str):
            try:
                data["key_phrases"] = json.loads(data["key_phrases"])
            except (json.JSONDecodeError, TypeError):
                data["key_phrases"] = []

        # Parse timestamp
        if data.get("generated_at") and isinstance(data["generated_at"], str):
            data["generated_at"] = datetime.fromisoformat(data["generated_at"])

        return cls(**data)
