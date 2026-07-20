"""
Engagement metric collectors (Phase 11).

Real collectors hit each platform's insights API (Twitter/Meta/TikTok/YouTube)
or scrape (LinkedIn) — those need platform apps + approvals, so they're
scaffolded. The `StubCollector` produces deterministic (non-random) metrics from
the post id so the collect → aggregate → serve loop works and is testable now.
Enable stub collection with env `ANALYTICS_DRY_RUN=true` (default on until real
collectors are wired).
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy.orm import Session

from backend.models import Post
from backend.models.analytics import PostMetric
from backend.models.distribution import PostedContent, ScheduledPost

logger = logging.getLogger(__name__)


def dry_run_enabled() -> bool:
    # Default ON: without real platform collectors, stub is the only source.
    return os.getenv("ANALYTICS_DRY_RUN", "true").strip().lower() in ("1", "true", "yes")


def _stub_metrics(seed: str) -> Dict[str, int]:
    """Deterministic, plausible engagement numbers derived from a seed."""
    h = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16)
    impressions = 500 + (h % 4500)
    like_rate = ((h >> 8) % 8 + 1) / 100.0  # 1%–8%
    likes = int(impressions * like_rate)
    comments = int(likes * 0.10) + (h % 5)
    shares = int(likes * 0.05) + (h % 3)
    reach = int(impressions * 0.8)
    return {
        "impressions": impressions,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "reach": reach,
    }


def _template_for(db: Session, pc: PostedContent) -> Optional[str]:
    """Best-effort template name via posted_content → scheduled_post → post."""
    sp = db.query(ScheduledPost).filter(ScheduledPost.id == pc.scheduled_post_id).first()
    if sp and sp.post_id:
        post = db.query(Post).filter(Post.id == sp.post_id).first()
        if post:
            return post.template_name
    return None


def collect_for_user(db: Session, user_id: str) -> Dict[str, int]:
    """Collect (stub) metrics for every published post the user owns.

    Idempotent per (posted_content, day): re-running the same day updates the
    existing snapshot rather than duplicating it.
    """
    if not dry_run_enabled():
        # Real collectors would branch per platform here.
        logger.info("Analytics collection skipped: real collectors not configured")
        return {"collected": 0, "skipped": True}

    today = datetime.now(timezone.utc).date()
    posted = db.query(PostedContent).filter(PostedContent.user_id == user_id).all()
    collected = 0
    for pc in posted:
        metrics = _stub_metrics(pc.platform_post_id or pc.id)
        existing = (
            db.query(PostMetric)
            .filter(
                PostMetric.posted_content_id == pc.id,
                PostMetric.metric_date == today,
            )
            .first()
        )
        if existing:
            for k, v in metrics.items():
                setattr(existing, k, v)
        else:
            db.add(
                PostMetric(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    posted_content_id=pc.id,
                    scheduled_post_id=pc.scheduled_post_id,
                    platform=pc.platform,
                    template_name=_template_for(db, pc),
                    metric_date=today,
                    **metrics,
                )
            )
        collected += 1
    db.commit()
    return {"collected": collected, "skipped": False}
