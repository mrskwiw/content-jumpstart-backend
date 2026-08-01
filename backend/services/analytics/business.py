"""Business-summary aggregation for the internal-ops Analytics page (GAP-UI-01).

Real project / post / client / template counts computed from the authenticated
user's own resources (scoped by ``user_id``, matching the rest of this router).

Intentionally OMITTED: revenue and quality-score. The platform persists neither as
real data, so the page must not render fabricated figures — the mock page's revenue
and qualityScore columns are dropped rather than invented here.

Aggregation is done in Python (not SQL ``GROUP BY``/date functions) so the same code
runs identically on SQLite (tests) and PostgreSQL (prod) without dialect-specific
month extraction.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models import Client, Post, Project


def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize a possibly tz-aware timestamp to naive UTC for portable comparison
    (SQLite returns naive values; Postgres returns tz-aware)."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(tz=None).replace(tzinfo=None)
    return dt


def _month_key(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


def business_summary(db: Session, user_id: str, days: int = 90) -> Dict:
    """Project/post/client/template activity for the user over the last ``days``."""
    days = max(1, min(days, 366))
    cutoff = datetime.utcnow() - timedelta(days=days)

    clients = db.query(Client).filter(Client.user_id == user_id).all()
    client_name = {c.id: c.name for c in clients}

    projects = db.query(Project).filter(Project.user_id == user_id).all()
    project_client = {p.id: p.client_id for p in projects}
    project_ids = list(project_client.keys())

    posts: List[Post] = (
        db.query(Post).filter(Post.project_id.in_(project_ids)).all() if project_ids else []
    )

    # ── Windowed aggregation ────────────────────────────────────────────────────
    monthly: Dict[str, Dict[str, int]] = defaultdict(lambda: {"projects": 0, "posts": 0})
    client_agg: Dict[str, Dict[str, int]] = defaultdict(lambda: {"projects": 0, "posts": 0})
    template_agg: Dict[str, int] = defaultdict(int)
    active_clients: set = set()
    total_projects = 0
    total_posts = 0

    for p in projects:
        created = _to_naive_utc(p.created_at)
        if created is None or created < cutoff:
            continue
        total_projects += 1
        monthly[_month_key(created)]["projects"] += 1
        cid = p.client_id
        if cid is not None:
            client_agg[cid]["projects"] += 1
            active_clients.add(cid)

    for post in posts:
        created = _to_naive_utc(post.created_at)
        if created is None or created < cutoff:
            continue
        total_posts += 1
        monthly[_month_key(created)]["posts"] += 1
        cid = project_client.get(post.project_id)
        if cid is not None:
            client_agg[cid]["posts"] += 1
            active_clients.add(cid)
        template = post.template_name or post.template_id or "Unknown"
        template_agg[template] += 1

    monthly_list = [
        {"month": m, "projects": v["projects"], "posts": v["posts"]}
        for m, v in sorted(monthly.items())
    ]
    by_client = sorted(
        (
            {
                "client_name": client_name.get(cid, "Unknown"),
                "projects": v["projects"],
                "posts": v["posts"],
            }
            for cid, v in client_agg.items()
        ),
        key=lambda r: (r["posts"], r["projects"]),
        reverse=True,
    )
    by_template = sorted(
        ({"template_name": name, "usage_count": count} for name, count in template_agg.items()),
        key=lambda r: r["usage_count"],
        reverse=True,
    )

    return {
        "days": days,
        "totals": {
            "projects": total_projects,
            "posts": total_posts,
            "clients": len(active_clients),
        },
        "monthly": monthly_list,
        "by_client": by_client,
        "by_template": by_template,
    }
