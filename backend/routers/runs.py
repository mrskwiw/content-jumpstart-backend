"""
Runs router - CRUD operations for generation runs.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from backend.middleware.auth_dependency import get_current_user
from backend.middleware.authorization import (
    verify_run_ownership,
)  # TR-021: Authorization
from backend.schemas.run import RunCreate, RunResponse, RunUpdate
from backend.services import crud
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Run, User

router = APIRouter()


@router.get("/", response_model=List[RunResponse])
async def list_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    project_id: Optional[str] = Query(None, alias="projectId"),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all runs with optional filters"""
    runs = crud.get_runs(db, skip=skip, limit=limit, project_id=project_id, status=status)
    return runs


@router.post("/", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    run: RunCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new run"""
    # Verify project exists
    project = crud.get_project(db, run.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {run.project_id} not found",
        )

    db_run = crud.create_run(db, project_id=run.project_id, is_batch=run.is_batch)
    return db_run


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    run: Run = Depends(verify_run_ownership),  # TR-021: Authorization check
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get run by ID.

    Authorization: TR-021 - User must own run's project
    """
    # TR-021: run already verified by dependency
    return run


@router.patch("/{run_id}", response_model=RunResponse)
async def update_run(
    run_id: str,
    run_update: RunUpdate,
    run: Run = Depends(verify_run_ownership),  # TR-021: Authorization check
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update run.

    Authorization: TR-021 - User must own run's project
    """
    # TR-021: run already verified by dependency
    update_data = run_update.model_dump(exclude_unset=True)
    updated_run = crud.update_run(db, run_id, **update_data)
    if not updated_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )
    return updated_run
