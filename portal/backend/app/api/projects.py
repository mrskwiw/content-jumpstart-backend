"""Project management API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, get_db
from ..models.brief import Brief
from ..models.deliverable import Deliverable
from ..models.file_upload import FileUpload
from ..models.project import Project
from ..models.user import User
from ..schemas.dashboard import DashboardResponse, DashboardStats
from ..schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatusUpdate,
)

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    status_filter: Optional[str] = Query(None, description="Filter by project status"),
    skip: int = Query(0, ge=0, description="Number of projects to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of projects to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get list of projects for the current user.

    - **status_filter**: Optional filter by status (brief_submitted, processing, etc.)
    - **skip**: Pagination offset (default 0)
    - **limit**: Maximum projects to return (default 100, max 100)

    Returns list of projects with total count.
    """
    # Base query for user's projects
    query = db.query(Project).filter(Project.user_id == current_user.user_id)

    # Apply status filter if provided
    if status_filter:
        query = query.filter(Project.status == status_filter)

    # Get total count
    total = query.count()

    # Get paginated projects ordered by submission date (newest first)
    projects = query.order_by(Project.submitted_at.desc()).offset(skip).limit(limit).all()

    return ProjectListResponse(
        total=total, projects=[ProjectResponse.model_validate(p) for p in projects]
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific project.

    - **project_id**: The project ID to retrieve

    Returns project details if user owns the project.
    """
    # Get project
    project = db.query(Project).filter(Project.project_id == project_id).first()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Verify user owns this project
    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this project",
        )

    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}/status", response_model=ProjectResponse)
async def update_project_status(
    project_id: str,
    status_update: ProjectStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the status of a project.

    - **project_id**: The project ID to update
    - **status**: New status value

    Valid statuses:
    - brief_submitted: Initial state after brief submission
    - processing: Content generation in progress
    - qa_review: Quality assurance review
    - ready_for_delivery: Content ready, pending delivery
    - delivered: Content delivered to client
    - completed: Project fully completed

    Returns updated project details.
    """
    # Get project
    project = db.query(Project).filter(Project.project_id == project_id).first()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Verify user owns this project
    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this project",
        )

    # Validate status value
    valid_statuses = [
        "brief_submitted",
        "processing",
        "qa_review",
        "ready_for_delivery",
        "delivered",
        "completed",
    ]

    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    # Update status
    project.status = status_update.status

    # Update timestamps based on status
    if status_update.status == "processing" and not project.processing_started_at:
        project.processing_started_at = datetime.utcnow()
    elif status_update.status == "ready_for_delivery" and not project.completed_at:
        project.completed_at = datetime.utcnow()
    elif status_update.status == "delivered" and not project.delivered_at:
        project.delivered_at = datetime.utcnow()

    db.commit()
    db.refresh(project)

    return ProjectResponse.model_validate(project)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new project.

    - **client_name**: Client/company name
    - **client_company**: Client company name
    - **client_email**: Client email address
    - **package_tier**: Package level (Starter, Professional, Premium, Enterprise)
    - **package_price**: Package price in USD (auto-set if not provided)
    - **posts_count**: Number of posts to generate (default 30)
    - **revision_limit**: Maximum revision rounds (default 1)
    - **brief_data**: Optional brief content data

    Returns created project details.
    """
    # Map package tier to price if not provided
    package_prices = {
        "Starter": 1200.0,
        "Professional": 1800.0,
        "Premium": 2500.0,
        "Enterprise": 3500.0,
    }

    package_price = project_data.package_price
    if package_price is None:
        package_price = package_prices.get(project_data.package_tier, 1800.0)

    # Create new project
    new_project = Project(
        user_id=current_user.user_id,
        client_name=project_data.client_name,
        client_company=project_data.client_company,
        client_email=project_data.client_email,
        package_tier=project_data.package_tier,
        package_price=package_price,
        posts_count=project_data.posts_count,
        revision_limit=project_data.revision_limit,
        status="brief_submitted",
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    # Create brief if brief_data provided
    if project_data.brief_data:
        brief = Brief(project_id=new_project.project_id, voice_notes=project_data.brief_data)
        db.add(brief)
        db.commit()

    return ProjectResponse.model_validate(new_project)


@router.get("/{project_id}/dashboard", response_model=DashboardResponse)
async def get_project_dashboard(
    project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get aggregated dashboard data for a project.

    - **project_id**: The project ID to get dashboard for

    Returns comprehensive dashboard with project details, stats, and brief status.
    """
    # Get project
    project = db.query(Project).filter(Project.project_id == project_id).first()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Verify user owns this project
    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this project's dashboard",
        )

    # Get brief if exists
    brief = db.query(Brief).filter(Brief.project_id == project_id).first()

    # Count files
    file_count = db.query(FileUpload).filter(FileUpload.project_id == project_id).count()

    # Count deliverables
    deliverable_count = db.query(Deliverable).filter(Deliverable.project_id == project_id).count()

    # Calculate days since created
    submitted_at = project.submitted_at or datetime.utcnow()
    days_since_created = (datetime.utcnow() - submitted_at).days

    # Build stats
    stats = DashboardStats(
        total_files=file_count,
        total_deliverables=deliverable_count,
        brief_submitted=brief is not None,
        days_since_created=days_since_created,
    )

    # Build response
    return DashboardResponse(
        project_id=project.project_id,
        client_name=project.client_name,
        package_tier=project.package_tier,
        package_price=project.package_price,
        status=project.status,
        created_at=submitted_at,
        updated_at=getattr(project, "updated_at", submitted_at),
        stats=stats,
        brief_id=brief.brief_id if brief else None,
    )
