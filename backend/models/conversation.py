"""
Conversation model for the AI assistant.

A conversation groups the messages exchanged between an operator and the AI
assistant. Conversations are keyed to the user who started them so history can be
listed, resumed, and (soft-)deleted per user.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base
from backend.models.mixins import SoftDeleteMixin


class Conversation(Base, SoftDeleteMixin):
    """A single AI-assistant chat thread owned by a user."""

    __tablename__ = "conversations"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Auto-derived from the first user message; may be null until the first turn.
    title = Column(String, nullable=True)

    # The dashboard page the chat was started on (e.g. "projects"), for context.
    page_context = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships (fully qualified paths to avoid clashing with Pydantic models
    # in src.models). Deleting a conversation cascades to its messages.
    messages = relationship(
        "backend.models.message.Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="backend.models.message.Message.created_at",
    )

    __table_args__ = (
        # List a user's conversations most-recent first.
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<Conversation {self.id} user={self.user_id}>"
