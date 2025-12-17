"""File upload API endpoints."""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..core.deps import get_current_user, get_db
from ..models.file_upload import FileUpload
from ..models.project import Project
from ..models.user import User
from ..schemas.file_upload import FileListResponse, FileUploadResponse

router = APIRouter(prefix="/api/uploads", tags=["File Uploads"])


# Ensure upload directory exists
UPLOAD_BASE_PATH = Path(settings.UPLOAD_DIR)
UPLOAD_BASE_PATH.mkdir(parents=True, exist_ok=True)


def validate_file(file: UploadFile) -> None:
    """
    Validate uploaded file against size and MIME type restrictions.

    Args:
        file: The uploaded file

    Raises:
        HTTPException: If file validation fails
    """
    # Check MIME type
    if file.content_type not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file.content_type}' not allowed. "
            f"Allowed types: {', '.join(settings.ALLOWED_MIME_TYPES)}",
        )

    # Check file size (read first chunk to get size)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size ({file_size / 1024 / 1024:.2f} MB) exceeds maximum "
            f"allowed size ({settings.MAX_FILE_SIZE_MB} MB)",
        )


@router.post(
    "/{project_id}", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED
)
async def upload_file(
    project_id: str,
    file_type: str = Query(..., description="Type of file (voice_sample, brand_asset, brief)"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a file for a project.

    - **project_id**: The project to attach this file to
    - **file_type**: Type of file (voice_sample, brand_asset, brief)
    - **file**: The file to upload

    Returns uploaded file details.
    """
    # Verify project exists and user owns it
    project = db.query(Project).filter(Project.project_id == project_id).first()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to upload files to this project",
        )

    # Validate file type parameter
    valid_file_types = ["voice_sample", "brand_asset", "brief"]
    if file_type not in valid_file_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file_type. Must be one of: {', '.join(valid_file_types)}",
        )

    # Validate file
    validate_file(file)

    # Generate unique filename
    file_extension = Path(file.filename).suffix
    stored_filename = f"{uuid.uuid4().hex}{file_extension}"

    # Determine storage path based on file type
    file_type_dir = file_type + "s" if not file_type.endswith("s") else file_type
    storage_dir = UPLOAD_BASE_PATH / file_type_dir
    storage_dir.mkdir(parents=True, exist_ok=True)

    file_path = storage_dir / stored_filename

    # Save file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )

    # Get file size
    file_size = file_path.stat().st_size

    # Create database record
    new_file = FileUpload(
        project_id=project_id,
        file_type=file_type,
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_path=str(file_path.relative_to(UPLOAD_BASE_PATH)),
        file_size=file_size,
        mime_type=file.content_type,
    )

    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    return FileUploadResponse.model_validate(new_file)


@router.get("/project/{project_id}", response_model=FileListResponse)
async def list_files(
    project_id: str,
    file_type: str = Query(
        None, description="Filter by file type (voice_sample, brand_asset, brief)"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get list of uploaded files for a project.

    - **project_id**: The project ID to retrieve files for
    - **file_type**: Optional filter by file type

    Returns list of uploaded files.
    """
    # Verify project exists and user owns it
    project = db.query(Project).filter(Project.project_id == project_id).first()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this project's files",
        )

    # Build query
    query = db.query(FileUpload).filter(FileUpload.project_id == project_id)

    if file_type:
        query = query.filter(FileUpload.file_type == file_type)

    # Get files
    files = query.order_by(FileUpload.uploaded_at.desc()).all()

    return FileListResponse(
        total=len(files), files=[FileUploadResponse.model_validate(f) for f in files]
    )


@router.get("/{file_id}/download")
async def download_file(
    file_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Download an uploaded file.

    - **file_id**: The file ID to download

    Returns file download.
    """
    # Get file record
    file_upload = db.query(FileUpload).filter(FileUpload.file_id == file_id).first()

    if not file_upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # Verify user owns the project
    project = db.query(Project).filter(Project.project_id == file_upload.project_id).first()
    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this file",
        )

    # Check if file exists on disk
    file_path = UPLOAD_BASE_PATH / file_upload.file_path
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    # Return file
    return FileResponse(
        path=file_path, filename=file_upload.original_filename, media_type=file_upload.mime_type
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Delete an uploaded file.

    - **file_id**: The file ID to delete

    Returns 204 No Content on success.
    """
    # Get file record
    file_upload = db.query(FileUpload).filter(FileUpload.file_id == file_id).first()

    if not file_upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # Verify user owns the project
    project = db.query(Project).filter(Project.project_id == file_upload.project_id).first()
    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this file",
        )

    # Delete file from disk
    file_path = UPLOAD_BASE_PATH / file_upload.file_path
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            # Log error but continue with database deletion
            print(f"Warning: Failed to delete file from disk: {e}")

    # Delete database record
    db.delete(file_upload)
    db.commit()

    return None
