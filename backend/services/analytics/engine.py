"""
Analytics engine (Phase 11).

Aggregates the latest engagement snapshot per published post into overview,
per-platform, per-template, and top-post views. Uses the most recent snapshot
per post (not a sum across days) so re-collection doesn't inflate totals.
"""

from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from backend.models.analytics import PostMetric
from backend.models.distribution import PostedContent


def engagement_rate(likes: int, comments: int, shares: int, impressions: int) -> float:
    if not impressions:
        return 0.0
    return round((likes + comments + shares) / impressions, 4)


def _latest_metrics(db: Session, user_id: str) -> List[PostMetric]:
    """Latest snapshot per posted_content for a user."""
    rows = (
        db.query(PostMetric)
        .filter(PostMetric.user_id == user_id)
        .order_by(PostMetric.metric_date.desc())
        .all()
    )
    latest: Dict[str, PostMetric] = {}
    for m in rows:
        key = m.posted_content_id or m.id
        if key not in latest:  # first seen = most recent (desc order)
            latest[key] = m
    return list(latest.values())


def _totals(metrics: List[PostMetric]) -> Dict:
    likes = sum(m.likes for m in metrics)
    comments = sum(m.comments for m in metrics)
    shares = sum(m.shares for m in metrics)
    impressions = sum(m.impressions for m in metrics)
    reach = sum(m.reach for m in metrics)
    return {
        "posts": len(metrics),
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "impressions": impressions,
        "reach": reach,
        "engagement": likes + comments + shares,
        "engagement_rate": engagement_rate(likes, comments, shares, impressions),
    }


def overview(db: Session, user_id: str) -> Dict:
    return _totals(_latest_metrics(db, user_id))


def by_platform(db: Session, user_id: str) -> List[Dict]:
    groups: Dict[str, List[PostMetric]] = {}
    for m in _latest_metrics(db, user_id):
        groups.setdefault(m.platform, []).append(m)
    return [{"platform": p, **_totals(ms)} for p, ms in sorted(groups.items())]


def by_template(db: Session, user_id: str) -> List[Dict]:
    groups: Dict[str, List[PostMetric]] = {}
    for m in _latest_metrics(db, user_id):
        groups.setdefault(m.template_name or "untagged", []).append(m)
    out = [{"template": t, **_totals(ms)} for t, ms in groups.items()]
    # Best-performing templates first.
    return sorted(out, key=lambda r: r["engagement_rate"], reverse=True)


def top_posts(db: Session, user_id: str, limit: int = 10) -> List[Dict]:
    metrics = _latest_metrics(db, user_id)
    ranked = sorted(
        metrics,
        key=lambda m: engagement_rate(m.likes, m.comments, m.shares, m.impressions),
        reverse=True,
    )[:limit]
    out = []
    for m in ranked:
        pc = (
            db.query(PostedContent).filter(PostedContent.id == m.posted_content_id).first()
            if m.posted_content_id
            else None
        )
        out.append(
            {
                "platform": m.platform,
                "template": m.template_name,
                "likes": m.likes,
                "comments": m.comments,
                "shares": m.shares,
                "impressions": m.impressions,
                "engagement_rate": engagement_rate(m.likes, m.comments, m.shares, m.impressions),
                "platform_url": pc.platform_url if pc else None,
            }
        )
    return out
