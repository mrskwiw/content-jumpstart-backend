"""
Media cost model & budget guardrails (Phase 12 — REQUIRED, not optional).

Generative video is the real cost risk (60 s of Veo ≈ $24; a single cinematic
clip can blow a client's margin). Every provider call is gated by
`enforce_budget()` BEFORE it runs:

  * per-job ceiling  — `MEDIA_MAX_JOB_COST_CENTS`
  * per-user/client monthly ceiling — `MEDIA_MAX_MONTHLY_COST_CENTS`

`estimate_cost()` is a pure projection (real published rates) used both for the
`/generate` estimate the caller must confirm and for the gate. Actual spend is
whatever the provider reports back (0 for the dry-run stub), persisted on the job.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.media import MediaJob
from backend.services.media.providers import MediaKind, _default_seconds


class BudgetExceededError(Exception):
    """Raised when a projected media spend exceeds a configured ceiling.

    The router maps this to HTTP 402 (Payment Required).
    """


# Projected spend in **cents per second** of produced media, by provider name.
# Indicative 2026 rates from the plan (docs/explore-media-generation.md §2/§6);
# re-verify at real-integration time — video pricing moves monthly.
_RATE_CENTS_PER_SEC: dict[str, float] = {
    "stub": 0.0,
    "elevenlabs_isolator": 0.2,
    "elevenlabs_tts": 1.0,
    "elevenlabs_dub": 0.8,
    "auphonic": 0.3,  # credit-tiered; cheap per file
    "cleanvoice": 0.3,
    "sync": 0.5,
    "heygen": 3.0,  # cheap per finished minute (avatar)
    "kling": 12.0,  # primary b-roll
    "veo": 30.0,  # premium b-roll (60 s ≈ $18–24)
    "ffmpeg": 0.0,  # local assembly
    # IMAGE-GEN: images are priced per unit; GEN_IMAGE defaults to 1s so this reads as a
    # flat per-image cost. ~5¢/image is an indicative Flux rate — re-verify at integration.
    "flux": 5.0,
}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def estimate_cost(kind: MediaKind, provider: str, *, seconds: Optional[float] = None) -> int:
    """Projected spend in **cents** for one provider call.

    Falls back to the kind's default duration when `seconds` is unknown, and to a
    conservative rate for an unmapped provider so estimates never silently read $0.
    """
    secs = _default_seconds(kind) if seconds is None else max(0.0, float(seconds))
    rate = _RATE_CENTS_PER_SEC.get(provider)
    if rate is None:
        rate = 30.0  # unknown provider: assume premium-video rates, not free
    return int(round(rate * secs))


def month_to_date_cents(db: Session, user_id: str, client_id: Optional[str] = None) -> int:
    """Sum of media spend already committed this calendar month (UTC)."""
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    q = db.query(func.coalesce(func.sum(MediaJob.cost_cents), 0)).filter(
        MediaJob.user_id == user_id,
        MediaJob.created_at >= month_start,
    )
    if client_id:
        q = q.filter(MediaJob.client_id == client_id)
    return int(q.scalar() or 0)


def enforce_budget(
    db: Session,
    user_id: str,
    client_id: Optional[str],
    est_cents: int,
) -> None:
    """Reject an over-budget spend BEFORE any provider call. Raises on violation.

    Ceilings are disabled when their env var is unset/0 (dev default), so the
    dry-run backbone runs unconstrained; production sets real caps per instance.
    """
    per_job_cap = _int_env("MEDIA_MAX_JOB_COST_CENTS", 0)
    if per_job_cap > 0 and est_cents > per_job_cap:
        raise BudgetExceededError(
            f"Estimated cost {est_cents}¢ exceeds the per-job cap {per_job_cap}¢."
        )

    monthly_cap = _int_env("MEDIA_MAX_MONTHLY_COST_CENTS", 0)
    if monthly_cap > 0:
        projected = month_to_date_cents(db, user_id, client_id) + est_cents
        if projected > monthly_cap:
            raise BudgetExceededError(
                f"Estimated cost {est_cents}¢ would bring this month's media spend to "
                f"{projected}¢, over the cap {monthly_cap}¢."
            )
