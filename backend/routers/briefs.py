"""Briefs router"""
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from middleware.auth_dependency import get_current_user
from schemas.brief import BriefCreate, BriefResponse
from services import crud
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User

router = APIRouter()


@router.post("/create", response_model=BriefResponse, status_code=status.HTTP_201_CREATED)
async def create_brief_from_text(
    brief: BriefCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create brief from pasted text"""
    # Verify project exists
    project = crud.get_project(db, brief.project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Check if brief already exists for this project
    existing_brief = crud.get_brief_by_project(db, brief.project_id)
    if existing_brief:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Brief already exists for this project"
        )

    # Save brief to file
    briefs_dir = Path(settings.BRIEFS_DIR)
    briefs_dir.mkdir(parents=True, exist_ok=True)
    file_path = briefs_dir / f"{brief.project_id}.txt"
    file_path.write_text(brief.content, encoding="utf-8")

    return crud.create_brief(db, brief, source="paste", file_path=str(file_path))


@router.post("/upload", response_model=BriefResponse, status_code=status.HTTP_201_CREATED)
async def upload_brief_file(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload brief file"""
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {settings.ALLOWED_BRIEF_EXTENSIONS}",
        )

    # Read file content
    content = await file.read()
    text_content = content.decode("utf-8")

    # Save file
    briefs_dir = Path(settings.BRIEFS_DIR)
    briefs_dir.mkdir(parents=True, exist_ok=True)
    file_path = briefs_dir / f"{project_id}{file_ext}"
    file_path.write_bytes(content)

    # Create brief record
    brief_data = BriefCreate(project_id=project_id, content=text_content)
    return crud.create_brief(db, brief_data, source="upload", file_path=str(file_path))


@router.get("/{brief_id}", response_model=BriefResponse)
async def get_brief(
    brief_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get brief by ID"""
    brief = crud.get_brief(db, brief_id)
    if not brief:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")
    return brief
