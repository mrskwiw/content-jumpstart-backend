"""
Pydantic schemas for the AI assistant (conversations, messages, chat requests).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatStreamRequest(BaseModel):
    """Request body for the streaming chat endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(..., min_length=1, max_length=8000)
    # Existing conversation to continue; a new one is created when omitted.
    conversation_id: Optional[str] = None
    # Current page context (page name, ids, etc.) — mirrors the legacy /chat body.
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MessageOut(BaseModel):
    """A single persisted message."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    created_at: Optional[datetime] = None


class ConversationSummary(BaseModel):
    """Lightweight conversation entry for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: Optional[str] = None
    page_context: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConversationDetail(ConversationSummary):
    """A conversation plus its messages."""

    messages: List[MessageOut] = Field(default_factory=list)


class ConversationListResponse(BaseModel):
    """Paginated list of a user's conversations."""

    conversations: List[ConversationSummary] = Field(default_factory=list)
    total: int = 0
