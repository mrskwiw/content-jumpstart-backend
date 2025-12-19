"""Deliverables router"""
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from middleware.auth_dependency import get_current_user
from schemas.deliverable import DeliverableResponse, MarkDeliveredRequest
from services import crud
from sqlalchemy.orm import Session

from database import get_db
from models import User

router = APIRouter()


@router.get("/", response_model=List[DeliverableResponse])
async def list_deliverables(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List deliverables with optional filters"""
    return crud.get_deliverables(db, skip=skip, limit=limit, status=status, client_id=client_id)


@router.get("/{deliverable_id}", response_model=DeliverableResponse)
async def get_deliverable(
    deliverable_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get deliverable by ID"""
    deliverable = crud.get_deliverable(db, deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable not found")
    return deliverable


@router.patch("/{deliverable_id}/mark-delivered", response_model=DeliverableResponse)
async def mark_delivered(
    deliverable_id: str,
    request: MarkDeliveredRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark deliverable as delivered"""
    deliverable = crud.mark_deliverable_delivered(
        db, deliverable_id, request.delivered_at, request.proof_url, request.proof_notes
    )
    if not deliverable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable not found")
    return deliverable


@router.get("/{deliverable_id}/download")
async def download_deliverable(
    deliverable_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download deliverable file.

    Returns the file as an attachment with appropriate headers.
    Validates file existence and path security.
    """
    # Get deliverable from database
    deliverable = crud.get_deliverable(db, deliverable_id)
    if not deliverable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deliverable not found"
        )

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
                detail="Access to this file is forbidden"
            )
    except (ValueError, OSError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file path: {str(e)}"
        )

    # Check if file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {deliverable.path}"
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
        headers={
            "Content-Disposition": f'attachment; filename="{file_path.name}"'
        }
    )
