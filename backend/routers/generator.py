"""
Generator API endpoints.

Handles content generation, regeneration, and export operations.
"""
import asyncio
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, SessionLocal
from middleware.auth_dependency import get_current_user
from models import User
from schemas.run import RunResponse
from schemas.deliverable import DeliverableResponse
from services import crud
from services.generator_service import generator_service
from utils.logger import logger
from utils.http_rate_limiter import limiter

router = APIRouter()


class GenerateAllInput(BaseModel):
    """Input for generate-all endpoint"""
    project_id: str
    client_id: str
    is_batch: bool = True
    template_quantities: Optional[dict[str, int]] = None  # Optional template quantities from frontend


class RegenerateInput(BaseModel):
    """Input for regenerate endpoint"""
    project_id: str
    post_ids: list[str]


class ExportInput(BaseModel):
    """Input for export endpoint"""
    project_id: str
    format: str = "txt"  # txt, docx, pdf


async def run_generation_background(
    run_id: str,
    project_id: str,
    client_id: str,
    num_posts: int = 30,
    template_quantities: Optional[dict[str, int]] = None,
):
    """
    Background task to run content generation.

    This prevents HTTP timeouts by running generation asynchronously.
    Updates the Run record with progress and results.
    """
    # Create new DB session for background task
    db = SessionLocal()

    try:
        logger.info(f"Background generation started for run {run_id}")
        if template_quantities:
            logger.info(f"Using template quantities from request: {template_quantities}")

        # Execute content generation via service
        result = await generator_service.generate_all_posts(
            db=db,
            project_id=project_id,
            client_id=client_id,
            num_posts=num_posts,
            template_quantities=template_quantities,
        )

        # Update run status to succeeded (use LogEntry format)
        from datetime import datetime
        from schemas.run import LogEntry

        timestamp = datetime.now().isoformat()
        logs = [
            LogEntry(timestamp=timestamp, message="Generation started"),
            LogEntry(timestamp=timestamp, message="CLI execution completed"),
            LogEntry(timestamp=timestamp, message=f"Created {result['posts_created']} post records"),
            LogEntry(timestamp=timestamp, message=f"Output directory: {result['output_dir']}"),
        ]

        crud.update_run(
            db,
            run_id,
            status="succeeded",
            logs=[log.model_dump() for log in logs]
        )

        logger.info(f"Background generation completed successfully for run {run_id}")

    except Exception as e:
        logger.error(f"Background generation failed for run {run_id}: {str(e)}", exc_info=True)

        # Update run status to failed
        crud.update_run(
            db,
            run_id,
            status="failed",
            error_message=str(e)
        )

    finally:
        db.close()


@router.post("/generate-all", response_model=RunResponse)
@limiter.limit("10/hour")  # TR-004: Rate limit expensive generation operations
async def generate_all(
    request: Request,
    background_tasks: BackgroundTasks,
    input: GenerateAllInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate all posts for a project.

    This endpoint:
    1. Creates a Run record with status="pending"
    2. Queues background task to run generation
    3. Returns immediately with run_id
    4. Client polls GET /api/runs/{run_id} for status updates

    Prevents HTTP timeouts by running generation asynchronously.
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

    # Create Run record with status="pending"
    db_run = crud.create_run(db, project_id=input.project_id, is_batch=input.is_batch)

    logger.info(f"Created run {db_run.id} for project {input.project_id}")

    # Queue background task (returns immediately)
    background_tasks.add_task(
        run_generation_background,
        run_id=db_run.id,
        project_id=input.project_id,
        client_id=input.client_id,
        num_posts=30,  # TODO: Make configurable via input
        template_quantities=input.template_quantities,  # Pass template quantities from frontend
    )

    # Update run status to running (background task will update to succeeded/failed)
    crud.update_run(db, db_run.id, status="running")

    # Refresh to get updated data
    db.refresh(db_run)

    logger.info(f"Queued background generation task for run {db_run.id}")

    return db_run


@router.post("/regenerate", response_model=RunResponse)
@limiter.limit("20/hour")  # TR-004: Rate limit regeneration (less strict than full generation)
async def regenerate(
    request: Request,
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

        # Update run status to succeeded (use LogEntry format)
        timestamp = datetime.now().isoformat()
        logs = [
            LogEntry(timestamp=timestamp, message="Regeneration started"),
            LogEntry(timestamp=timestamp, message=f"Regenerated {result.get('posts_regenerated', 0)} posts"),
            LogEntry(timestamp=timestamp, message=f"Status: {result.get('status', 'completed')}"),
        ]

        crud.update_run(
            db,
            db_run.id,
            status="succeeded",
            logs=[log.model_dump() for log in logs]  # Convert to dicts for JSON serialization
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
@limiter.limit("30/hour")  # TR-004: Rate limit export operations
async def export_package(
    request: Request,
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
        from utils.file_utils import calculate_file_size

        # Generate deliverable path based on project name and format
        # Path is relative to data/ directory (download endpoint will prepend data/outputs/)
        deliverable_path = f"{project.name}/deliverable_{input.format}"

        # Calculate file size if file exists (use full path for file size calculation)
        full_path = f"data/outputs/{deliverable_path}"
        file_size = calculate_file_size(full_path)

        # Create deliverable record
        db_deliverable = Deliverable(
            id=f"del-{uuid.uuid4().hex[:12]}",
            project_id=input.project_id,
            client_id=project.client_id,
            format=input.format,
            path=deliverable_path,
            status="ready",
            created_at=datetime.utcnow(),
            file_size_bytes=file_size
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
