"""
Message model for the AI assistant.

Stores each turn of an assistant conversation. Rows may be:
- role="user": an operator message
- role="assistant": a model reply (may carry proposed/executed tool calls)
- role="tool": the result of a tool execution, linked to its call via tool_call_id
"""

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base
from backend.models.mixins import SoftDeleteMixin


class Message(Base, SoftDeleteMixin):
    """A single message within an assistant conversation."""

    __tablename__ = "messages"

    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False, index=True)

    # "user" | "assistant" | "tool"
    role = Column(String, nullable=False)
    content = Column(Text, nullable=True)

    # Assistant tool-use blocks proposed/executed this turn (list of dicts), or
    # null for plain text turns. Mirrors the Anthropic tool_use content blocks.
    tool_calls = Column(JSON, nullable=True)

    # For role="tool" rows: the id of the tool_use block this result answers.
    tool_call_id = Column(String, nullable=True)

    # Per-message cost (LLM tokens and/or billable tool execution), if known.
    cost_usd = Column(Numeric, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship(
        "backend.models.conversation.Conversation", back_populates="messages"
    )

    __table_args__ = (
        # Fetch a conversation's messages in chronological order.
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<Message {self.id} {self.role} conv={self.conversation_id}>"
