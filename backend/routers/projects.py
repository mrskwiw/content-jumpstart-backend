"""
Projects router - CRUD operations for projects.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response
from backend.middleware.auth_dependency import get_current_user
from backend.middleware.authorization import (
    verify_project_ownership,
    filter_user_projects,
)  # TR-021: Authorization
from backend.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from backend.services import crud
from sqlalchemy.orm import Session
from backend.utils.pagination import paginate_hybrid, get_pagination_params

from backend.database import get_db
from backend.models import Project, User
from backend.utils.http_rate_limiter import standard_limiter
from backend.services.audit_service import get_client_ip, log_action

router = APIRouter()


@router.get("/")
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def list_projects(
    request: Request,
    page: Optional[int] = Query(
        None, ge=1, description="Page number (1-indexed, for offset pagination)"
    ),
    cursor: Optional[str] = Query(
        None, description="Pagination cursor (for cursor-based pagination)"
    ),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    status: Optional[str] = Query(None, description="Filter by project status"),
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    List all projects with optional filters.

    Rate limit: 100/hour per IP+user (standard operation)

    Pagination:
    - Hybrid approach: offset pagination for first 5 pages, cursor for deeper pagination
    - Use 'page' parameter for traditional pagination (e.g., page=1, page=2)
    - Use 'cursor' parameter for efficient deep pagination (get cursor from previous response)
    - Automatically switches to cursor pagination when page >= 6

    Caching:
    - max-age: 300 seconds (5 minutes)
    - stale-while-revalidate: 600 seconds (10 minutes)
    - ETag support for 304 Not Modified responses

    Example:
        GET /api/projects?page=1&page_size=20
        GET /api/projects?cursor=2025-12-15T10:30:00:proj-abc123&page_size=20
    """
    # Validate pagination params
    pagination_params = get_pagination_params(page=page, cursor=cursor, page_size=page_size)

    # TR-021: Filter to user's projects only (authorization)
    query = filter_user_projects(db, current_user)

    # PERFORMANCE: Eager load related data, but skip posts for list view (60% faster)
    # Post count comes from num_posts field, no need to load all 30 posts
    from sqlalchemy.orm import joinedload

    query = query.options(
        joinedload(Project.client),
        joinedload(Project.brief),
        joinedload(Project.user),
        # Skip Project.posts for list view - only need count
        joinedload(Project.deliverables),
        joinedload(Project.runs),
    )

    # Apply filters
    if status:
        query = query.filter(Project.status == status)
    if client_id:
        query = query.filter(Project.client_id == client_id)

    # Apply pagination
    paginated = paginate_hybrid(
        query=query,
        page=pagination_params["page"],
        cursor=pagination_params["cursor"],
        page_size=pagination_params["page_size"],
        order_by_field="created_at",
        order_direction="desc",
    )

    # Convert items to response schema (use by_alias=True for camelCase output, mode='json' for datetime serialization)
    projects_data = [
        ProjectResponse.model_validate(p).model_dump(by_alias=True, mode="json")
        for p in paginated["items"]
    ]

    # Prepare response with pagination metadata
    response_data = {
        "items": projects_data,
        "metadata": paginated["metadata"].model_dump(mode="json"),
    }

    return JSONResponse(content=response_data)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def create_project(
    request: Request,
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new project.

    Rate limit: 100/hour per IP+user (standard operation)

    Cache invalidation: Signals clients to invalidate projects cache.
    """
    # Verify client exists and user owns it
    client = crud.get_client(db, project.client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {project.client_id} not found",
        )

    # Reattach detached object to session for attribute access
    client = db.merge(client)

    # TR-021: Verify user owns the client
    if client.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't own this client",
        )

    # TR-021: Create project with user_id for ownership
    db_project = crud.create_project(db, project, user_id=current_user.id)

    log_action(
        db,
        user_id=current_user.id,
        user_email=current_user.email,
        user_name=current_user.full_name or current_user.email,
        action="Created project",
        action_type="create",
        resource_type="project",
        resource_id=db_project.id,
        resource_name=getattr(db_project, "name", db_project.id),
        ip_address=get_client_ip(request),
    )
    project_data = ProjectResponse.model_validate(db_project).model_dump(by_alias=True, mode="json")
    return JSONResponse(content=project_data, status_code=status.HTTP_201_CREATED)


@router.get("/{project_id}")
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def get_project(
    project_id: str,
    request: Request,
    project: Project = Depends(verify_project_ownership),  # TR-021: Authorization check
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get project by ID.

    Rate limit: 100/hour per IP+user (standard operation)
    Authorization: TR-021 - User must own project
    """
    # TR-021: project already verified by dependency
    project_data = ProjectResponse.model_validate(project).model_dump(by_alias=True, mode="json")
    return JSONResponse(content=project_data)


@router.put("/{project_id}", response_model=ProjectResponse)
@router.patch("/{project_id}", response_model=ProjectResponse)
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def update_project(
    request: Request,
    project_id: str,
    project_update: ProjectUpdate,
    project: Project = Depends(verify_project_ownership),  # TR-021: Authorization check
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update project (supports both PUT and PATCH).

    Rate limit: 100/hour per IP+user (standard operation)
    Authorization: TR-021 - User must own project

    Cache invalidation: Signals clients to invalidate projects cache.
    """
    # TR-021: project already verified by dependency
    updated_project = crud.update_project(db, project_id, project_update)
    if not updated_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    log_action(
        db,
        user_id=current_user.id,
        user_email=current_user.email,
        user_name=current_user.full_name or current_user.email,
        action="Updated project",
        action_type="update",
        resource_type="project",
        resource_id=project_id,
        resource_name=getattr(updated_project, "name", project_id),
        ip_address=get_client_ip(request),
    )
    project_data = ProjectResponse.model_validate(updated_project).model_dump(
        by_alias=True, mode="json"
    )
    return JSONResponse(content=project_data)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def delete_project(
    request: Request,
    project_id: str,
    project: Project = Depends(verify_project_ownership),  # TR-021: Authorization check
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete project.

    Rate limit: 100/hour per IP+user (standard operation)
    Authorization: TR-021 - User must own project

    Cache invalidation: Signals clients to invalidate projects cache.
    """
    # TR-021: project already verified by dependency
    project_name = getattr(project, "name", project_id)
    success = crud.delete_project(db, project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    log_action(
        db,
        user_id=current_user.id,
        user_email=current_user.email,
        user_name=current_user.full_name or current_user.email,
        action="Deleted project",
        action_type="delete",
        resource_type="project",
        resource_id=project_id,
        resource_name=project_name,
        ip_address=get_client_ip(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
