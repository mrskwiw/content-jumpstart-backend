"""
Cost Reporting API Router

Provides endpoints for querying token usage and API costs across projects,
runs, and research tools.
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import Post, ResearchResult, Run
from backend.models.project import Project
from backend.models.user import User
from backend.middleware.auth_dependency import get_current_user
from backend.services import crud
from backend.schemas.costs import (
    ProjectCostSummary,
    RunCostBreakdown,
    UserCostSummary,
    CostTrend,
    ResearchCostSummary,
)

router = APIRouter(prefix="/api/costs", tags=["costs"])

logger = logging.getLogger(__name__)


@router.get("/project/{project_id}", response_model=ProjectCostSummary)
def get_project_costs(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get cost summary for a specific project

    Returns aggregated token usage and costs across all runs for the project.
    """
    # Verify project exists and user owns it (using CRUD for eager loading)
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        # Aggregate run costs
        run_stats = (
            db.query(
                func.count(Run.id).label("total_runs"),
                func.sum(Run.total_input_tokens).label("total_input_tokens"),
                func.sum(Run.total_output_tokens).label("total_output_tokens"),
                func.sum(Run.total_cache_creation_tokens).label("total_cache_creation_tokens"),
                func.sum(Run.total_cache_read_tokens).label("total_cache_read_tokens"),
                func.sum(Run.total_cost_usd).label("total_cost_usd"),
            )
            .filter(Run.project_id == project_id)
            .first()
        )

        # Count posts generated
        total_posts = db.query(func.count(Post.id)).filter(Post.project_id == project_id).scalar()

        # Get research costs for this project
        research_stats = (
            db.query(
                func.count(ResearchResult.id).label("total_research_tools"),
                func.sum(ResearchResult.actual_cost_usd).label("total_research_cost"),
            )
            .filter(ResearchResult.project_id == project_id)
            .first()
        )

        # Calculate cost per post
        cost_per_post = None
        if total_posts and run_stats.total_cost_usd:
            cost_per_post = run_stats.total_cost_usd / total_posts

        return ProjectCostSummary(
            project_id=project_id,
            project_name=project.name,
            total_runs=run_stats.total_runs or 0,
            total_posts=total_posts or 0,
            total_input_tokens=run_stats.total_input_tokens or 0,
            total_output_tokens=run_stats.total_output_tokens or 0,
            total_cache_creation_tokens=run_stats.total_cache_creation_tokens or 0,
            total_cache_read_tokens=run_stats.total_cache_read_tokens or 0,
            total_generation_cost_usd=run_stats.total_cost_usd or 0.0,
            total_research_tools=research_stats.total_research_tools or 0,
            total_research_cost_usd=research_stats.total_research_cost or 0.0,
            total_cost_usd=(run_stats.total_cost_usd or 0.0)
            + (research_stats.total_research_cost or 0.0),
            cost_per_post=cost_per_post,
        )
    except Exception as e:
        logger.error(f"Error fetching costs for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve project costs")


@router.get("/run/{run_id}", response_model=RunCostBreakdown)
def get_run_costs(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed cost breakdown for a specific run

    Returns run-level token usage and per-post cost estimates.
    """
    # Get run with eager-loaded project to avoid N+1 query
    run = db.query(Run).options(joinedload(Run.project)).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Access the eager-loaded project relationship
    if not run.project or run.project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get posts for this run with token data
    posts = db.query(Post).filter(Post.run_id == run_id).all()

    # Calculate posts with token data
    posts_with_tokens = sum(1 for p in posts if p.input_tokens is not None)

    # Calculate average cost per post
    avg_cost_per_post = None
    if run.total_cost_usd and len(posts) > 0:
        avg_cost_per_post = run.total_cost_usd / len(posts)

    # Calculate cache savings
    cache_savings_usd = None
    if run.total_cache_read_tokens:
        # Cache reads are ~10x cheaper than input tokens
        # $0.30 vs $3.00 per 1M tokens = $2.70 savings per 1M cache read tokens
        cache_savings_usd = (run.total_cache_read_tokens / 1_000_000) * 2.70

    return RunCostBreakdown(
        run_id=run_id,
        project_id=run.project.id,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        total_input_tokens=run.total_input_tokens or 0,
        total_output_tokens=run.total_output_tokens or 0,
        total_cache_creation_tokens=run.total_cache_creation_tokens or 0,
        total_cache_read_tokens=run.total_cache_read_tokens or 0,
        total_cost_usd=run.total_cost_usd or 0.0,
        estimated_cost_usd=run.estimated_cost_usd,
        total_posts=len(posts),
        posts_with_token_data=posts_with_tokens,
        avg_cost_per_post=avg_cost_per_post,
        cache_savings_usd=cache_savings_usd,
    )


@router.get("/summary", response_model=UserCostSummary)
def get_user_cost_summary(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get cost summary across all user's projects

    Returns aggregated costs, trends, and top spending projects.
    """
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Get all user's projects
    project_ids = db.query(Project.id).filter(Project.user_id == current_user.id).all()
    project_id_list = [p.id for p in project_ids]

    # Aggregate run costs
    run_stats = (
        db.query(
            func.count(Run.id).label("total_runs"),
            func.sum(Run.total_input_tokens).label("total_input_tokens"),
            func.sum(Run.total_output_tokens).label("total_output_tokens"),
            func.sum(Run.total_cost_usd).label("total_cost_usd"),
        )
        .filter(
            Run.project_id.in_(project_id_list),
            Run.started_at >= start_date,
        )
        .first()
    )

    # Aggregate research costs
    research_stats = (
        db.query(
            func.count(ResearchResult.id).label("total_research_tools"),
            func.sum(ResearchResult.actual_cost_usd).label("total_research_cost"),
        )
        .filter(
            ResearchResult.project_id.in_(project_id_list),
            ResearchResult.created_at >= start_date,
        )
        .first()
    )

    # Get top 5 most expensive projects
    top_projects = (
        db.query(
            Project.id,
            Project.name,
            func.sum(Run.total_cost_usd).label("project_cost"),
        )
        .join(Run, Run.project_id == Project.id)
        .filter(
            Project.user_id == current_user.id,
            Run.started_at >= start_date,
        )
        .group_by(Project.id, Project.name)
        .order_by(func.sum(Run.total_cost_usd).desc())
        .limit(5)
        .all()
    )

    top_projects_list = [
        {"project_id": p.id, "project_name": p.name, "cost_usd": float(p.project_cost or 0)}
        for p in top_projects
    ]

    # Calculate daily costs for trend (last 7 days)
    daily_costs = (
        db.query(
            func.date(Run.started_at).label("date"),
            func.sum(Run.total_cost_usd).label("daily_cost"),
        )
        .filter(
            Run.project_id.in_(project_id_list),
            Run.started_at >= end_date - timedelta(days=7),
        )
        .group_by(func.date(Run.started_at))
        .order_by(func.date(Run.started_at))
        .all()
    )

    cost_trend = [
        CostTrend(date=str(d.date), cost_usd=float(d.daily_cost or 0)) for d in daily_costs
    ]

    return UserCostSummary(
        user_id=current_user.id,
        period_days=days,
        total_projects=len(project_id_list),
        total_runs=run_stats.total_runs or 0,
        total_input_tokens=run_stats.total_input_tokens or 0,
        total_output_tokens=run_stats.total_output_tokens or 0,
        total_generation_cost_usd=run_stats.total_cost_usd or 0.0,
        total_research_tools=research_stats.total_research_tools or 0,
        total_research_cost_usd=research_stats.total_research_cost or 0.0,
        total_cost_usd=(run_stats.total_cost_usd or 0.0)
        + (research_stats.total_research_cost or 0.0),
        top_projects=top_projects_list,
        cost_trend=cost_trend,
    )


@router.get("/research/{client_id}", response_model=ResearchCostSummary)
def get_research_costs(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get research cost summary for a client

    Shows all research tools executed and their actual API costs vs business pricing.
    """
    # Verify client exists and user owns it (using CRUD for consistency)
    client = crud.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if client.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get all research results for this client
    research_results = (
        db.query(ResearchResult)
        .filter(ResearchResult.client_id == client_id)
        .order_by(ResearchResult.created_at.desc())
        .all()
    )

    # Aggregate costs
    # Group by tool name
    tools_summary = {}
    for r in research_results:
        if r.tool_name not in tools_summary:
            tools_summary[r.tool_name] = {
                "tool_name": r.tool_name,
                "tool_label": r.tool_label,
                "execution_count": 0,
                "total_business_price": 0.0,
                "total_actual_cost": 0.0,
                "total_tokens": 0,
            }

        tools_summary[r.tool_name]["execution_count"] += 1
        # tools_summary[r.tool_name]["total_business_price"] removed (Bug #51)
        tools_summary[r.tool_name]["total_actual_cost"] += r.actual_cost_usd or 0
        tools_summary[r.tool_name]["total_tokens"] += (r.input_tokens or 0) + (r.output_tokens or 0)

    return ResearchCostSummary(
        client_id=client_id,
        client_name=client.name,
        total_research_tools=len(research_results),
        tools_breakdown=list(tools_summary.values()),
    )
