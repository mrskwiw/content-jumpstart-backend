"""
Analytics engine (Phase 11).

Aggregates the latest engagement snapshot per published post into overview,
per-platform, per-template, and top-post views. Uses the most recent snapshot
per post (not a sum across days) so re-collection doesn't inflate totals.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List

from sqlalchemy.orm import Session

from backend.models.analytics import PostMetric
from backend.models.distribution import PostedContent

# Reference engagement-rate benchmarks per platform as (low, median, high).
# Code-defined and tunable — kept here rather than a materialized table so they
# always resolve (no seed dependency) and never go stale against derived rollups.
# Rough industry medians; adjust as real data accrues.
_BENCHMARKS: Dict[str, tuple] = {
    "linkedin": (0.020, 0.040, 0.060),
    "twitter": (0.003, 0.009, 0.020),
    "facebook": (0.005, 0.012, 0.030),
    "instagram": (0.010, 0.030, 0.060),
    "tiktok": (0.030, 0.060, 0.120),
    "youtube": (0.010, 0.020, 0.040),
    "stub": (0.020, 0.040, 0.060),
}
_DEFAULT_BENCHMARK = (0.010, 0.025, 0.050)


def engagement_rate(likes: int, comments: int, shares: int, impressions: int) -> float:
    if not impressions:
        return 0.0
    return round((likes + comments + shares) / impressions, 4)


def benchmark_tier(platform: str, rate: float) -> str:
    """Classify an engagement rate against the platform's reference band."""
    low, median, high = _BENCHMARKS.get(platform, _DEFAULT_BENCHMARK)
    if rate < low:
        return "poor"
    if rate < median:
        return "average"
    if rate < high:
        return "good"
    return "excellent"


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


def by_platform_with_benchmark(db: Session, user_id: str) -> List[Dict]:
    """Per-platform totals annotated with the benchmark tier for its rate."""
    rows = by_platform(db, user_id)
    for row in rows:
        row["benchmark_tier"] = benchmark_tier(row["platform"], row["engagement_rate"])
    return rows


def daily_series(db: Session, user_id: str, days: int = 30) -> List[Dict]:
    """Engagement time series: one point per collection day (all snapshots, not
    latest-per-post), so it shows how engagement accrued over time.

    Bounded by a SQL date predicate (the `metric_date` index) so it never scans
    a user's full metric history as data accumulates.
    """
    cutoff = date.today() - timedelta(days=days)
    rows = (
        db.query(PostMetric)
        .filter(PostMetric.user_id == user_id, PostMetric.metric_date >= cutoff)
        .order_by(PostMetric.metric_date.asc())
        .all()
    )
    by_day: Dict[str, List[PostMetric]] = {}
    for m in rows:
        by_day.setdefault(m.metric_date.isoformat(), []).append(m)
    return [{"date": day, **_totals(ms)} for day, ms in sorted(by_day.items())]


def trend(db: Session, user_id: str, window_days: int = 7) -> Dict:
    """Compare the most recent `window_days` of collection to the prior window.

    Returns direction + percentage change in engagement rate. Each window's rate
    is volume-weighted (summed engagements / summed impressions), NOT an average
    of daily rates — so a single low-volume spike day can't flip the direction.
    """
    series = daily_series(db, user_id, days=window_days * 2)
    # Split by CALENDAR date, not by count of present days — otherwise sparse days
    # make the two halves span unequal time and skew the comparison. `recent` is
    # the last `window_days` days; `prior` is the window_days before that.
    recent_cutoff = (date.today() - timedelta(days=window_days - 1)).isoformat()
    recent = [p for p in series if p["date"] >= recent_cutoff]
    prior = [p for p in series if p["date"] < recent_cutoff]
    if not recent or not prior:
        return {"direction": "flat", "change_pct": 0.0, "recent_rate": 0.0, "prior_rate": 0.0}

    def _weighted_rate(rows: List[Dict]) -> float:
        eng = sum(r["engagement"] for r in rows)
        impr = sum(r["impressions"] for r in rows)
        return round(eng / impr, 4) if impr else 0.0

    recent_rate, prior_rate = _weighted_rate(recent), _weighted_rate(prior)
    if prior_rate == 0:
        change = 100.0 if recent_rate > 0 else 0.0
    else:
        change = round((recent_rate - prior_rate) / prior_rate * 100, 1)
    direction = "up" if change > 1 else "down" if change < -1 else "flat"
    return {
        "direction": direction,
        "change_pct": change,
        "recent_rate": recent_rate,
        "prior_rate": prior_rate,
    }


def insights(db: Session, user_id: str) -> List[str]:
    """Auto-generated plain-language observations from the aggregates."""
    ov = overview(db, user_id)
    out: List[str] = []
    if ov["posts"] == 0:
        return [
            "No published content yet — connect an account and schedule posts to see analytics."
        ]

    out.append(
        f"{ov['posts']} published posts drove {ov['engagement']:,} engagements "
        f"across {ov['impressions']:,} impressions ({ov['engagement_rate'] * 100:.1f}% rate)."
    )

    platforms = by_platform_with_benchmark(db, user_id)
    if platforms:
        best = max(platforms, key=lambda r: r["engagement_rate"])
        out.append(
            f"{best['platform'].title()} is your strongest platform at "
            f"{best['engagement_rate'] * 100:.1f}% ({best['benchmark_tier']} vs benchmark)."
        )

    templates = [t for t in by_template(db, user_id) if t["template"] != "untagged"]
    if templates:
        top = templates[0]
        out.append(
            f"Template '{top['template']}' performs best at "
            f"{top['engagement_rate'] * 100:.1f}% engagement."
        )

    tr = trend(db, user_id)
    if tr["direction"] != "flat":
        arrow = "up" if tr["direction"] == "up" else "down"
        out.append(f"Engagement is trending {arrow} {abs(tr['change_pct'])}% vs the prior period.")

    return out
