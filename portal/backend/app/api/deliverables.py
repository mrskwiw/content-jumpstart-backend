"""Deliverable download API endpoints."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, get_db
from ..models.deliverable import Deliverable
from ..models.project import Project
from ..models.user import User
from ..schemas.deliverable import DeliverableListResponse, DeliverableResponse

router = APIRouter(prefix="/api/deliverables", tags=["Deliverables"])


@router.get("/project/{project_id}", response_model=DeliverableListResponse)
async def list_deliverables(
    project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get list of deliverables for a project.

    - **project_id**: The project ID to retrieve deliverables for

    Returns list of deliverables with metadata.
    """
    # Verify project exists and user owns it
    project = db.query(Project).filter(Project.project_id == project_id).first()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this project's deliverables",
        )

    # Get deliverables
    deliverables = (
        db.query(Deliverable)
        .filter(Deliverable.project_id == project_id)
        .order_by(Deliverable.created_at.desc())
        .all()
    )

    return DeliverableListResponse(
        total=len(deliverables),
        deliverables=[DeliverableResponse.model_validate(d) for d in deliverables],
    )


@router.get("/{deliverable_id}", response_model=DeliverableResponse)
async def get_deliverable(
    deliverable_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get deliverable metadata.

    - **deliverable_id**: The deliverable ID to retrieve

    Returns deliverable metadata.
    """
    # Get deliverable
    deliverable = db.query(Deliverable).filter(Deliverable.deliverable_id == deliverable_id).first()

    if not deliverable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable not found")

    # Verify user owns the project
    project = db.query(Project).filter(Project.project_id == deliverable.project_id).first()
    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this deliverable",
        )

    return DeliverableResponse.model_validate(deliverable)


@router.get("/{deliverable_id}/download")
async def download_deliverable(
    deliverable_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Download a deliverable file.

    - **deliverable_id**: The deliverable ID to download

    Returns file download.
    """
    # Get deliverable
    deliverable = db.query(Deliverable).filter(Deliverable.deliverable_id == deliverable_id).first()

    if not deliverable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable not found")

    # Verify user owns the project
    project = db.query(Project).filter(Project.project_id == deliverable.project_id).first()
    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to download this deliverable",
        )

    # Check if file exists
    file_path = Path(deliverable.file_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable file not found on disk"
        )

    # Update download count and timestamp
    deliverable.download_count += 1
    deliverable.last_downloaded_at = datetime.utcnow()
    db.commit()

    # Determine media type from file format
    media_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
        "pdf": "application/pdf",
        "md": "text/markdown",
    }
    media_type = media_types.get(deliverable.file_format, "application/octet-stream")

    # Generate filename
    filename = f"{project.client_name}_{deliverable.deliverable_type}.{deliverable.file_format}"

    # Return file
    return FileResponse(path=file_path, filename=filename, media_type=media_type)
