"""Hashtag Models

Data structures for the generation-step hashtag research system (HASHTAG-02).

A per-post research pass produces a small set of platform-appropriate hashtags
fitted to a specific post, drawn from client context. For the LinkedIn + X slice
the research backend is the LLM (neither platform exposes a usable hashtag API),
so ``signal_source`` is ``estimated`` throughout. Measured signals arrive when
external providers are wired (see docs/explore-hashtag-research.md §9, P2).
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class HashtagTier(str, Enum):
    """Role a hashtag plays in the mix (see platform_specs.HASHTAG_TIERS)."""

    BROAD = "broad"  # High-volume industry term (reach, high competition)
    NICHE = "niche"  # Specific, lower-volume, higher-intent
    BRANDED = "branded"  # Client's own brand/campaign tag
    TRENDING = "trending"  # Time-sensitive conversation/challenge tag


class SignalSource(str, Enum):
    """Where a hashtag's volume/competition signals came from.

    Never present an ``estimated`` signal as if it were ``measured``.
    """

    MEASURED = "measured"  # From an external provider API
    ESTIMATED = "estimated"  # Inferred by the LLM (no provider)


class HashtagCandidate(BaseModel):
    """A single researched hashtag with its metadata."""

    tag: str = Field(..., description="Hashtag text WITHOUT a leading '#'")
    tier: HashtagTier = Field(..., description="Role in the tier mix")
    signal_source: SignalSource = Field(
        SignalSource.ESTIMATED, description="Provenance of the volume/competition signals"
    )
    volume: Optional[int] = Field(
        None, description="Est./measured monthly usage; None when unknown"
    )
    competition: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="0=low, 1=saturated; None when unknown"
    )
    banned: bool = Field(False, description="Flagged on a banned/shadowban list")
    rationale: Optional[str] = Field(
        None, description="Short reason this tag fits the post (for transparency/debug)"
    )

    @field_validator("tag")
    @classmethod
    def _normalize_tag(cls, v: str) -> str:
        """Strip a leading '#', surrounding whitespace, and inner spaces.

        Hashtags cannot contain spaces; callers may pass '#Foo Bar' or ' Foo '.
        We store the display form without the '#'. Raises on an empty result so a
        blank tag never reaches the bank.
        """
        cleaned = v.strip().lstrip("#").strip()
        cleaned = cleaned.replace(" ", "")
        if not cleaned:
            raise ValueError("hashtag cannot be empty after normalization")
        return cleaned

    @property
    def display(self) -> str:
        """The tag rendered for output, e.g. '#B2BContentMarketing'."""
        return f"#{self.tag}"


class HashtagSet(BaseModel):
    """The final, policy-compliant set of hashtags chosen for one post."""

    platform: str = Field(..., description="Target platform value, e.g. 'linkedin'")
    tags: List[HashtagCandidate] = Field(
        default_factory=list, description="Chosen tags, in output order (may be empty)"
    )

    @property
    def display_tags(self) -> List[str]:
        """Chosen tags as display strings, deduped case-insensitively in order."""
        seen: set[str] = set()
        out: List[str] = []
        for c in self.tags:
            key = c.tag.lower()
            if key not in seen:
                seen.add(key)
                out.append(c.display)
        return out

    def as_suffix(self) -> str:
        """Tags joined for appending to a post, e.g. '#A #B #C' (empty if none)."""
        return " ".join(self.display_tags)
