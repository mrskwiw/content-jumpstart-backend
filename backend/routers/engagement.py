"""
Phase 11 — Multi-Platform Analytics & Engagement API.

Engagement metrics for the authenticated user's published content: collect
(stub until real platform collectors land), then overview / by-platform /
by-template / top-posts. Distinct from the app-observability `/api/metrics`
router and the internal-ops mock `Analytics.tsx` page.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.services.analytics import business, collectors, engine, report

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Engagement"])


@router.post("/collect")
def collect(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Collect the latest engagement metrics for the user's published posts."""
    return collectors.collect_for_user(db, current_user.id)


@router.get("/business-summary")
def business_summary(
    days: int = 90,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Real project/post/client/template activity for the internal-ops Analytics page
    (GAP-UI-01). Scoped to the user's own resources; revenue/quality are intentionally
    absent (not tracked). ``days`` is clamped to [1, 366]."""
    return business.business_summary(db, current_user.id, days=days)


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


@router.get("/benchmarks")
def benchmarks(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Per-platform totals annotated with each platform's benchmark tier."""
    return engine.by_platform_with_benchmark(db, current_user.id)


@router.get("/daily")
def daily(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Engagement time series, one point per collection day."""
    return engine.daily_series(db, current_user.id, days=min(max(days, 1), 365))


@router.get("/trend")
def trend(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Recent-vs-prior engagement-rate trend."""
    return engine.trend(db, current_user.id)


@router.get("/insights")
def insights(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Auto-generated plain-language observations."""
    return {"insights": engine.insights(db, current_user.id)}


@router.get("/report.pdf")
def report_pdf(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Download a one-page PDF engagement report."""
    pdf = report.build_pdf(db, current_user.id)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="engagement-report.pdf"'},
    )
