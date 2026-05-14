"""Deliverables router"""

from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from backend.middleware.auth_dependency import get_current_user
from backend.services.export_service import generate_export_file
from backend.utils.logger import logger
from backend.middleware.authorization import (
    verify_deliverable_ownership,
    filter_user_deliverables,
)  # TR-021: Authorization
from backend.schemas.deliverable import (
    DeliverableResponse,
    DeliverableDetailResponse,
    MarkDeliveredRequest,
)
from backend.services import crud
from backend.services.deliverable_service import get_deliverable_details
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Deliverable, User
from backend.utils.http_rate_limiter import standard_limiter

router = APIRouter()


@router.get("/", response_model=List[DeliverableResponse])
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def list_deliverables(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List deliverables with optional filters.

    Rate limit: 100/hour per IP+user (standard operation)
    Authorization: TR-021 - User can only see deliverables from their own projects
    """
    # TR-021: Filter to user's deliverables only (via project ownership)
    from backend.models import Deliverable
    from sqlalchemy.orm import joinedload

    query = filter_user_deliverables(db, current_user)

    # Eager load relationships to prevent N+1 queries
    query = query.options(joinedload(Deliverable.project), joinedload(Deliverable.client))

    # Apply additional filters
    if status:
        query = query.filter(Deliverable.status == status)
    if client_id:
        query = query.filter(Deliverable.client_id == client_id)
    if project_id:
        query = query.filter(Deliverable.project_id == project_id)

    # Apply pagination
    deliverables = query.offset(skip).limit(limit).all()

    return deliverables


@router.get("/{deliverable_id}", response_model=DeliverableResponse)
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def get_deliverable(
    request: Request,
    deliverable_id: str,
    deliverable: Deliverable = Depends(verify_deliverable_ownership),  # TR-021: Authorization check
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get deliverable by ID.

    Rate limit: 100/hour per IP+user (standard operation)
    Authorization: TR-021 - User must own deliverable's project
    """
    # TR-021: deliverable already verified by dependency
    return deliverable


@router.patch("/{deliverable_id}/mark-delivered", response_model=DeliverableResponse)
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def mark_delivered(
    request: Request,
    deliverable_id: str,
    mark_request: MarkDeliveredRequest,
    deliverable: Deliverable = Depends(verify_deliverable_ownership),  # TR-021: Authorization check
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark deliverable as delivered.

    Rate limit: 100/hour per IP+user (standard operation)
    Authorization: TR-021 - User must own deliverable's project
    """
    # TR-021: deliverable already verified by dependency
    updated_deliverable = crud.mark_deliverable_delivered(
        db,
        deliverable_id,
        mark_request.delivered_at,
        mark_request.proof_url,
        mark_request.proof_notes,
    )
    if not updated_deliverable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable not found")
    return updated_deliverable


@router.get("/{deliverable_id}/download")
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def download_deliverable(
    request: Request,
    deliverable_id: str,
    deliverable: Deliverable = Depends(verify_deliverable_ownership),  # TR-021: Authorization check
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download deliverable file.

    Rate limit: 100/hour per IP+user (standard operation)
    Authorization: TR-021 - User must own deliverable's project

    Returns the file as an attachment with appropriate headers.
    Validates file existence and path security.
    """
    # TR-021: deliverable already verified by dependency

    # Construct file path
    # Assuming files are stored in data/outputs/ relative to project root
    base_path = Path("data/outputs")
    file_path = base_path / deliverable.path

    # Security: Ensure the resolved path is within the base directory
    try:
        resolved_path = file_path.resolve()
        resolved_base = base_path.resolve()
        if not str(resolved_path).startswith(str(resolved_base)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to this file is forbidden",
            )
    except (ValueError, OSError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file path: {str(e)}",
        )

    # Check if file exists — if not, regenerate from DB (handles ephemeral storage loss)
    if not file_path.exists():
        logger.warning(f"Deliverable file missing, regenerating: {deliverable.path}")
        try:
            project = crud.get_project(db, deliverable.project_id)
            client = crud.get_client(db, deliverable.client_id)
            if not project or not client:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File is missing and cannot be regenerated: project or client not found",
                )

            # Research-only deliverables have no run_id and no associated posts.
            # Detect them by the absence of a run_id, then regenerate with research content.
            is_research_only = deliverable.run_id is None
            posts = []
            if not is_research_only:
                posts = crud.get_posts(
                    db,
                    project_id=deliverable.project_id,
                    run_id=deliverable.run_id,
                    limit=500,
                )
                # Exclude placeholder posts (failed generation) from deliverables
                posts = [p for p in posts if not p.is_placeholder]
                if not posts:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="File is missing and cannot be regenerated: no posts found for this run",
                    )

            await generate_export_file(
                posts=posts,
                client=client,
                project=project,
                format=deliverable.format,
                relative_path=deliverable.path,
                include_research=is_research_only,
                is_research_only=is_research_only,
                db=db,
            )
            logger.info(f"Regenerated deliverable file: {deliverable.path}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to regenerate deliverable {deliverable.id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File is missing and could not be regenerated",
            )

    # Determine media type based on file extension
    media_types = {
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".json": "application/json",
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".ics": "text/calendar",
    }

    file_extension = file_path.suffix.lower()
    media_type = media_types.get(file_extension, "application/octet-stream")

    # Return file as download
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=file_path.name,
        headers={"Content-Disposition": f'attachment; filename="{file_path.name}"'},
    )


@router.get("/{deliverable_id}/details", response_model=DeliverableDetailResponse)
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def get_deliverable_details_endpoint(
    request: Request,
    deliverable_id: str,
    deliverable: Deliverable = Depends(verify_deliverable_ownership),  # TR-021: Authorization check
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get deliverable with extended details including:

    Rate limit: 100/hour per IP+user (standard operation)
    Authorization: TR-021 - User must own deliverable's project

    - File preview (first 5000 characters)
    - Related posts from the same run
    - QA summary statistics
    - File modification timestamp

    This endpoint is used by the enhanced deliverable drawer
    to display comprehensive information about a deliverable.
    """
    # TR-021: deliverable already verified by dependency
    details = get_deliverable_details(db, deliverable_id)
    if not details:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable not found")
    return details


@router.post("/from-research")
@standard_limiter.limit("10/hour")  # TR-004: Research report generation (expensive)
async def generate_research_report(
    request: Request,
    client_id: str = Query(...),
    tools: str = Query(...),  # Comma-separated tool names
    format: str = Query("md", regex="^(md|docx|pdf)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate standalone research report from completed research tools.

    Queries ResearchResult for specified client's completed tools,
    formats them into a deliverable report, and returns download URL.

    Rate limit: 10/hour per IP+user (expensive report generation)
    Authorization: TR-021 - User must own the client
    """
    import uuid

    # TR-021: Verify user owns the client
    client = crud.get_client(db, client_id)
    if not client or client.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't own this client",
        )

    # Get or create research project for this client
    research_project = crud.get_or_create_research_project(db, client_id, current_user.id)

    # Generate research-only report (no posts, research context only)
    try:
        from datetime import datetime as _dt

        timestamp = _dt.now().strftime("%Y%m%d_%H%M%S")
        safe_name = client.name.replace(" ", "_")
        output_path = f"{safe_name}/{safe_name}_research_report_{timestamp}.{format}"
        file_path, file_size = await generate_export_file(
            posts=[],  # No posts - research only
            client=client,
            project=research_project,  # Use research project
            format=format,
            relative_path=output_path,
            include_audit_log=False,
            include_research=True,  # Include research data
            is_research_only=True,
            db=db,
        )

        # Store the ACTUAL path/format — export_service may fall back (e.g. python-docx
        # absent → .txt) and return a different extension than what was requested.
        actual_format = file_path.suffix.lstrip(".")
        actual_path = file_path.relative_to(Path("data/outputs")).as_posix()

        # Create deliverable record
        deliverable = Deliverable(
            id=f"del-{uuid.uuid4().hex[:12]}",
            project_id=research_project.id,  # Use research project
            client_id=client.id,
            path=actual_path,
            format=actual_format,
            status="ready",
            file_size_bytes=file_size,
        )
        db.add(deliverable)
        db.commit()
        db.refresh(deliverable)

        logger.info(f"Generated research report for client {client_id}: {file_path}")

        return {
            "download_url": f"/api/deliverables/{deliverable.id}/download",
            "file_name": file_path.name,
            "deliverable_id": deliverable.id,
        }

    except Exception as e:
        logger.error(f"Failed to generate research report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate research report: {str(e)}",
        )
