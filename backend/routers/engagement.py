"""
Phase 11 — Multi-Platform Analytics & Engagement API.

Engagement metrics for the authenticated user's published content: collect
(stub until real platform collectors land), then overview / by-platform /
by-template / top-posts. Distinct from the app-observability `/api/metrics`
router and the internal-ops mock `Analytics.tsx` page.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.services.analytics import collectors, engine

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Engagement"])


@router.post("/collect")
def collect(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Collect the latest engagement metrics for the user's published posts."""
    return collectors.collect_for_user(db, current_user.id)


@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return engine.overview(db, current_user.id)


@router.get("/by-platform")
def by_platform(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return engine.by_platform(db, current_user.id)


@router.get("/by-template")
def by_template(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return engine.by_template(db, current_user.id)


@router.get("/top-posts")
def top_posts(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return engine.top_posts(db, current_user.id, limit=min(limit, 50))
