"""Schemas for the content atomization / repurposing endpoint (ATOMIZE-01)."""

from typing import List

from pydantic import BaseModel, Field


class AtomizeRequest(BaseModel):
    """Repurpose one long-form piece into platform atoms."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="Long-form content to repurpose (<=50k chars; ~8k words)",
    )
    max_chars: int = Field(
        270, ge=50, le=5000, description="Max characters per thread post (default X-friendly 270)"
    )
    max_quotes: int = Field(3, ge=1, le=10, description="Max pull-quotes to return")


class AtomizeResponse(BaseModel):
    """A numbered thread plus standalone pull-quote candidates."""

    thread: List[str] = Field(..., description="Numbered thread posts, each within max_chars")
    thread_count: int = Field(..., description="Number of posts in the thread")
    pull_quotes: List[str] = Field(..., description="Punchy standalone sentences for graphics")
