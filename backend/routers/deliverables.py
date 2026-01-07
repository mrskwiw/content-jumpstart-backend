"""Deliverables router"""

from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from backend.middleware.auth_dependency import get_current_user
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
                status_code=status.HTTP_403_FORBIDDEN, detail="Access to this file is forbidden"
            )
    except (ValueError, OSError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid file path: {str(e)}"
        )

    # Check if file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {deliverable.path}"
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
