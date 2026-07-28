"""Research spend monitor (GAP-PAY-02).

A SOFT guardrail on a user's ACTUAL research API dollar-spend. The credit balance
already prevents spending beyond purchased credits, and the count limiter caps
call velocity; this adds visibility into real API $-cost velocity so a runaway
pattern (compromised account, automation bug) is surfaced early.

Design (see docs/explore-spend-caps.md, decided with user 2026-07-27):
- **Dollar-based:** sums ``ResearchResult.actual_cost_usd`` (the real API cost),
  not the credit price.
- **Cache hits exempt:** ``is_cached_result`` rows and NULL-cost rows contribute
  nothing (they cost ~$0), so caching is never penalised.
- **Soft alert:** on a cap breach it writes a ``warning`` AuditLog entry + logs,
  but NEVER blocks the request and NEVER raises (a monitor must not break
  research).

Caps are configured via ``RESEARCH_DAILY_SPEND_CAP_USD`` /
``RESEARCH_MONTHLY_SPEND_CAP_USD`` (backend.config).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.research_result import ResearchResult
from backend.services import audit_service
from backend.utils.logger import logger


@dataclass
class SpendStatus:
    """A user's research API spend vs. caps for the current day and month."""

    daily_spend_usd: float
    daily_cap_usd: float
    monthly_spend_usd: float
    monthly_cap_usd: float

    @property
    def daily_over(self) -> bool:
        return self.daily_spend_usd > self.daily_cap_usd

    @property
    def monthly_over(self) -> bool:
        return self.monthly_spend_usd > self.monthly_cap_usd

    @property
    def over_cap(self) -> bool:
        return self.daily_over or self.monthly_over


def _window_starts(now: datetime) -> Tuple[datetime, datetime]:
    """Return (start-of-day, start-of-month) for ``now`` (UTC, tz-aware)."""
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = day_start.replace(day=1)
    return day_start, month_start


def _spend_query(db: Session, user_id: str, since: datetime):
    """Base filter: a user's real (non-cached, costed) research runs since ``since``."""
    return db.query(ResearchResult).filter(
        ResearchResult.user_id == user_id,
        ResearchResult.created_at >= since,
        ResearchResult.actual_cost_usd.isnot(None),
        ResearchResult.is_cached_result.isnot(True),
    )


def get_user_spend_usd(db: Session, user_id: str, since: datetime) -> float:
    """Sum a user's ACTUAL research API cost since ``since``, excluding cache hits."""
    total = (
        _spend_query(db, user_id, since)
        .with_entities(func.coalesce(func.sum(ResearchResult.actual_cost_usd), 0.0))
        .scalar()
    )
    return float(total or 0.0)


def get_spend_by_tool(db: Session, user_id: str, since: datetime) -> Dict[str, float]:
    """Per-tool actual $-spend since ``since`` (for alert context / reporting)."""
    rows = (
        _spend_query(db, user_id, since)
        .with_entities(
            ResearchResult.tool_name,
            func.coalesce(func.sum(ResearchResult.actual_cost_usd), 0.0),
        )
        .group_by(ResearchResult.tool_name)
        .all()
    )
    return {name: float(cost or 0.0) for name, cost in rows}


def get_spend_status(db: Session, user_id: str, now: Optional[datetime] = None) -> SpendStatus:
    """Compute a user's day + month spend against the configured caps."""
    now = now or datetime.now(timezone.utc)
    day_start, month_start = _window_starts(now)
    return SpendStatus(
        daily_spend_usd=get_user_spend_usd(db, user_id, day_start),
        daily_cap_usd=float(settings.RESEARCH_DAILY_SPEND_CAP_USD),
        monthly_spend_usd=get_user_spend_usd(db, user_id, month_start),
        monthly_cap_usd=float(settings.RESEARCH_MONTHLY_SPEND_CAP_USD),
    )


def check_and_alert(
    db: Session,
    user_id: str,
    user_email: Optional[str] = None,
    now: Optional[datetime] = None,
) -> SpendStatus:
    """Compute spend and, on a cap breach, write a warning AuditLog + log.

    SOFT: always returns; never blocks and never raises. Call it AFTER the run's
    ``actual_cost_usd`` has been recorded so the current run is included.
    """
    try:
        now = now or datetime.now(timezone.utc)
        status = get_spend_status(db, user_id, now=now)
        if not status.over_cap:
            return status

        _, month_start = _window_starts(now)
        by_tool = get_spend_by_tool(db, user_id, month_start)
        windows = []
        if status.daily_over:
            windows.append(f"daily ${status.daily_spend_usd:.2f}/${status.daily_cap_usd:.2f}")
        if status.monthly_over:
            windows.append(f"monthly ${status.monthly_spend_usd:.2f}/${status.monthly_cap_usd:.2f}")
        detail = "Research API spend cap exceeded: " + "; ".join(windows)
        logger.warning(f"[SPEND-CAP] user={user_id} {detail}")
        audit_service.log_action(
            db,
            user_id=user_id,
            user_email=user_email,
            action="Research spend cap exceeded",
            action_type="system",
            resource_type="research",
            status="warning",
            details=detail,
            metadata={
                "daily_spend_usd": round(status.daily_spend_usd, 4),
                "daily_cap_usd": status.daily_cap_usd,
                "monthly_spend_usd": round(status.monthly_spend_usd, 4),
                "monthly_cap_usd": status.monthly_cap_usd,
                "daily_over": status.daily_over,
                "monthly_over": status.monthly_over,
                "spend_by_tool_month": {k: round(v, 4) for k, v in by_tool.items()},
            },
        )
        return status
    except Exception:
        logger.exception("research_spend_monitor.check_and_alert failed (non-critical)")
        return SpendStatus(
            daily_spend_usd=0.0,
            daily_cap_usd=float(settings.RESEARCH_DAILY_SPEND_CAP_USD),
            monthly_spend_usd=0.0,
            monthly_cap_usd=float(settings.RESEARCH_MONTHLY_SPEND_CAP_USD),
        )
