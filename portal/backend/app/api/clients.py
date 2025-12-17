"""Client management API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, get_db
from ..models.brief import Brief
from ..models.project import Project
from ..models.user import User
from ..schemas.client import ClientDetailResponse, ClientListResponse, ClientResponse

router = APIRouter(prefix="/api/clients", tags=["Clients"])


@router.get("/", response_model=ClientListResponse)
async def list_clients(
    search: Optional[str] = Query(None, description="Search by client name, company, or email"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get list of unique clients for the current user.

    Returns distinct clients based on client_name from projects.
    Supports search across name, company, and email.
    """
    # Base query - get distinct clients from projects
    query = (
        db.query(
            Project.client_name,
            Project.client_company,
            Project.client_email,
            func.count(Project.project_id).label("projects_count"),
            func.max(Project.submitted_at).label("last_activity"),
        )
        .filter(Project.user_id == current_user.user_id)
        .group_by(Project.client_name, Project.client_company, Project.client_email)
    )

    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Project.client_name.ilike(search_term),
                Project.client_company.ilike(search_term),
                Project.client_email.ilike(search_term),
            )
        )

    # Get total count
    total = query.count()

    # Apply pagination and order
    clients = (
        query.order_by(func.max(Project.submitted_at).desc()).limit(limit).offset(offset).all()
    )

    # Format response
    client_list = [
        ClientResponse(
            client_name=client.client_name,
            client_company=client.client_company,
            client_email=client.client_email,
            projects_count=client.projects_count,
            last_activity=client.last_activity,
        )
        for client in clients
    ]

    return ClientListResponse(total=total, clients=client_list, limit=limit, offset=offset)


@router.get("/{client_name}", response_model=ClientDetailResponse)
async def get_client_detail(
    client_name: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific client.

    Includes:
    - All projects for this client
    - Parsed briefs from all projects
    - Project statistics
    """
    # Get all projects for this client
    projects = (
        db.query(Project)
        .filter(Project.user_id == current_user.user_id, Project.client_name == client_name)
        .order_by(Project.submitted_at.desc())
        .all()
    )

    if not projects:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No projects found for client: {client_name}",
        )

    # Get briefs for all projects
    project_ids = [p.project_id for p in projects]
    briefs = db.query(Brief).filter(Brief.project_id.in_(project_ids)).all()

    # Create brief lookup
    brief_map = {b.project_id: b for b in briefs}

    # Format projects with their briefs
    project_details = []
    for project in projects:
        brief = brief_map.get(project.project_id)
        project_details.append(
            {
                "project_id": project.project_id,
                "status": project.status,
                "package_tier": project.package_tier,
                "posts_count": project.posts_count,
                "submitted_at": project.submitted_at,
                "completed_at": project.completed_at,
                "brief": {
                    "tone_descriptors": brief.tone_descriptors if brief else None,
                    "audience_type": brief.audience_type if brief else None,
                    "pain_points": brief.pain_points if brief else None,
                    "key_topics": brief.key_topics if brief else None,
                    "conversion_goal": brief.conversion_goal if brief else None,
                }
                if brief
                else None,
            }
        )

    # Calculate statistics
    total_posts = sum(p.posts_count or 0 for p in projects)
    completed_projects = sum(1 for p in projects if p.status in ["completed", "delivered"])

    return ClientDetailResponse(
        client_name=client_name,
        client_company=projects[0].client_company,
        client_email=projects[0].client_email,
        total_projects=len(projects),
        completed_projects=completed_projects,
        total_posts_generated=total_posts,
        projects=project_details,
        first_project_date=projects[-1].submitted_at if projects else None,
        last_activity=projects[0].submitted_at if projects else None,
    )
