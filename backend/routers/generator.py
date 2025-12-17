"""
Generator API endpoints.

Handles content generation, regeneration, and export operations.
"""
import asyncio
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth_dependency import get_current_user
from models import User
from schemas.run import RunResponse
from schemas.deliverable import DeliverableResponse
from services import crud
from services.generator_service import generator_service
from utils.logger import logger

router = APIRouter()


class GenerateAllInput(BaseModel):
    """Input for generate-all endpoint"""
    project_id: str
    client_id: str
    is_batch: bool = True


class RegenerateInput(BaseModel):
    """Input for regenerate endpoint"""
    project_id: str
    post_ids: list[str]


class ExportInput(BaseModel):
    """Input for export endpoint"""
    project_id: str
    format: str = "txt"  # txt, docx, pdf


@router.post("/generate-all", response_model=RunResponse)
async def generate_all(
    input: GenerateAllInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate all posts for a project.

    This endpoint:
    1. Creates a Run record
    2. Triggers the CLI content generator
    3. Updates Run status
    4. Creates Post records
    """
    # Verify project exists
    project = crud.get_project(db, input.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {input.project_id} not found"
        )

    # Verify client exists
    client = crud.get_client(db, input.client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {input.client_id} not found"
        )

    # Create Run record
    db_run = crud.create_run(db, project_id=input.project_id, is_batch=input.is_batch)

    # Update run status to running
    crud.update_run(db, db_run.id, status="running")

    try:
        logger.info(f"Starting content generation for project {input.project_id}")

        # Execute content generation via service
        result = await generator_service.generate_all_posts(
            db=db,
            project_id=input.project_id,
            client_id=input.client_id,
            num_posts=30,  # TODO: Make configurable via input
        )

        # Update run status to succeeded
        logs = [
            "Generation started",
            f"CLI execution completed",
            f"Created {result['posts_created']} post records",
            f"Output directory: {result['output_dir']}",
        ]

        crud.update_run(
            db,
            db_run.id,
            status="succeeded",
            logs=logs
        )

        # Refresh to get updated data
        db.refresh(db_run)

        logger.info(f"Content generation completed successfully for run {db_run.id}")
        return db_run

    except Exception as e:
        # Update run status to failed
        crud.update_run(
            db,
            db_run.id,
            status="failed",
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}"
        )


@router.post("/regenerate", response_model=RunResponse)
async def regenerate(
    input: RegenerateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Regenerate specific posts.

    Used for quality gate - regenerate flagged posts.
    """
    # Verify project exists
    project = crud.get_project(db, input.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {input.project_id} not found"
        )

    # Create Run record for regeneration
    db_run = crud.create_run(db, project_id=input.project_id, is_batch=False)

    # Update run status to running
    crud.update_run(db, db_run.id, status="running")

    try:
        logger.info(f"Starting regeneration for {len(input.post_ids)} posts in project {input.project_id}")

        # Execute regeneration via service
        result = await generator_service.regenerate_posts(
            db=db,
            project_id=input.project_id,
            post_ids=input.post_ids,
        )

        # Update run status to succeeded
        logs = [
            "Regeneration started",
            f"Regenerated {result.get('posts_regenerated', 0)} posts",
            f"Status: {result.get('status', 'completed')}",
        ]

        crud.update_run(
            db,
            db_run.id,
            status="succeeded",
            logs=logs
        )

        db.refresh(db_run)
        logger.info(f"Regeneration completed successfully for run {db_run.id}")
        return db_run

    except Exception as e:
        logger.error(f"Regeneration failed: {str(e)}", exc_info=True)
        crud.update_run(
            db,
            db_run.id,
            status="failed",
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Regeneration failed: {str(e)}"
        )


@router.post("/export", response_model=DeliverableResponse)
async def export_package(
    input: ExportInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export deliverable package.

    Creates a deliverable file (TXT/DOCX/PDF) from generated posts.
    """
    try:
        # Verify project exists
        project = crud.get_project(db, input.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {input.project_id} not found"
            )

        logger.info(f"Creating deliverable export for project {input.project_id} in format {input.format}")

        # TODO: Implement actual file export logic
        # For now, create a deliverable record with placeholder path
        # Future: Generate actual file from posts in database

        from models import Deliverable
        import uuid
        from datetime import datetime

        # Generate deliverable path based on project name and format
        deliverable_path = f"data/outputs/{project.name}/deliverable_{input.format}"

        # Create deliverable record
        db_deliverable = Deliverable(
            id=f"del-{uuid.uuid4().hex[:12]}",
            project_id=input.project_id,
            client_id=project.client_id,
            format=input.format,
            path=deliverable_path,
            status="ready",
            created_at=datetime.utcnow()
        )

        db.add(db_deliverable)
        db.commit()
        db.refresh(db_deliverable)

        logger.info(f"Deliverable created successfully: {db_deliverable.id}")
        return db_deliverable

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )
