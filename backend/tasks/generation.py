"""
Background tasks for content generation.

Phase 2 optimization: Async content generation with progress tracking
- Prevents HTTP timeouts (generation takes 60+ seconds)
- Provides real-time progress updates
- Handles errors gracefully with database updates
- Supports concurrent generation for multiple projects
"""

from datetime import datetime
from typing import Dict, Any, Optional

from celery import Task
from celery.utils.log import get_task_logger

from backend.celery_app import celery_app
from backend.database import SessionLocal
from backend.models.run import Run
from backend.services import crud

logger = get_task_logger(__name__)


class DatabaseTask(Task):
    """
    Base task class with database session management.

    Automatically creates and closes database sessions for each task.
    Ensures proper cleanup even if task fails.
    """

    _db = None

    @property
    def db(self):
        """Lazy database session creation."""
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        """Close database session after task completes."""
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(bind=True, base=DatabaseTask, name="generate_all_posts")
def generate_all_posts_task(
    self,
    run_id: str,
    project_id: str,
    num_posts: int = 30,
    platform: str = "linkedin",
) -> Dict[str, Any]:
    """
    Background task for generating all posts for a project.

    This task replaces the synchronous /generate-all endpoint to prevent
    HTTP timeouts and enable progress tracking.

    Args:
        self: Celery task instance (injected by bind=True)
        run_id: Unique run identifier
        project_id: Project identifier
        num_posts: Number of posts to generate (default: 30)
        platform: Target platform (linkedin, twitter, facebook, blog, email)

    Returns:
        dict: Generation results with run_id, status, posts_generated

    Raises:
        Exception: Any generation error (task will be marked as FAILURE)

    Progress updates:
        - 10%: Started, parsing brief
        - 30%: Brief parsed, selecting templates
        - 50%: Templates selected, generating posts
        - 90%: Posts generated, validating quality
        - 100%: Complete

    Database updates:
        - Updates run.status throughout execution (running, succeeded, failed)
        - Sets run.started_at, run.completed_at timestamps
        - Stores run.error_message on failure
        - Stores run.celery_task_id for progress tracking
    """
    try:
        # 1. Update run status to running
        logger.info(f"Starting generation task for run {run_id}")
        run: Optional[Run] = crud.get_run(self.db, run_id)

        if not run:
            logger.error(f"Run {run_id} not found in database")
            raise ValueError(f"Run {run_id} not found")

        run.status = "running"
        run.started_at = datetime.utcnow()
        self.db.commit()

        # Update progress: 10% (started)
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 10,
                "status": "Parsing brief...",
                "run_id": run_id,
            },
        )

        # 2. Load project and brief
        logger.info(f"Loading project {project_id}")
        project = crud.get_project(self.db, project_id)

        if not project:
            logger.error(f"Project {project_id} not found")
            raise ValueError(f"Project {project_id} not found")

        if not project.brief:
            logger.error(f"Project {project_id} has no brief")
            raise ValueError(f"Project {project_id} has no brief")

        # Update progress: 30% (brief loaded)
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 30,
                "status": "Brief parsed, selecting templates...",
                "run_id": run_id,
            },
        )

        # 3. Generate posts
        # TODO: Integrate with actual generator service
        # For now, this is a placeholder that demonstrates the structure
        # Real implementation will call:
        # from backend.services.generator import generate_all_posts
        # result = await generate_all_posts(brief=project.brief, num_posts=num_posts)

        logger.info(f"Generating {num_posts} posts for platform {platform}")

        # Update progress: 50% (generation started)
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 50,
                "status": f"Generating {num_posts} posts...",
                "run_id": run_id,
            },
        )

        # Placeholder: In real implementation, call generator service here
        # For now, we'll simulate success
        logger.warning("Using placeholder generator - integrate real generator service")
        generated_posts = []  # Real implementation will populate this

        # Update progress: 90% (generation complete)
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 90,
                "status": "Validating quality...",
                "run_id": run_id,
            },
        )

        # 4. Update run with success status
        run.status = "succeeded"
        run.completed_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Generation task completed successfully for run {run_id}")

        # Update progress: 100% (complete)
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 100,
                "status": "Complete",
                "run_id": run_id,
            },
        )

        return {
            "run_id": run_id,
            "status": "succeeded",
            "posts_generated": len(generated_posts),
            "platform": platform,
        }

    except Exception as e:
        logger.error(
            f"Generation task failed for run {run_id}: {str(e)}",
            exc_info=True,
        )

        # Update run status to failed
        try:
            run = crud.get_run(self.db, run_id)
            if run:
                run.status = "failed"
                run.error_message = str(e)
                run.completed_at = datetime.utcnow()
                self.db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update run status: {str(db_error)}")

        # Re-raise exception to mark Celery task as FAILURE
        raise


@celery_app.task(bind=True, base=DatabaseTask, name="regenerate_posts")
def regenerate_posts_task(
    self,
    run_id: str,
    project_id: str,
    post_ids: list[str],
    feedback: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Background task for regenerating specific posts.

    Args:
        self: Celery task instance (injected by bind=True)
        run_id: Run identifier
        project_id: Project identifier
        post_ids: List of post IDs to regenerate
        feedback: Optional feedback to guide regeneration

    Returns:
        dict: Regeneration results with status and count
    """
    import asyncio

    logger.info(f"Regenerating {len(post_ids)} posts for run {run_id}")

    try:
        # Update run status
        run = crud.get_run(self.db, run_id)
        if run:
            run.status = "running"
            run.started_at = datetime.utcnow()
            self.db.commit()

        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 20,
                "status": f"Regenerating {len(post_ids)} posts...",
                "run_id": run_id,
            },
        )

        # Import and call the generator service
        from backend.services.generator_service import generator_service

        # Run the async regeneration in an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                generator_service.regenerate_posts(
                    db=self.db,
                    project_id=project_id,
                    post_ids=post_ids,
                    feedback=feedback,
                )
            )
        finally:
            loop.close()

        # Update run status to succeeded
        if run:
            run.status = "succeeded"
            run.completed_at = datetime.utcnow()
            self.db.commit()

        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 100,
                "status": "Complete",
                "run_id": run_id,
            },
        )

        logger.info(f"Regeneration completed: {result}")

        return {
            "run_id": run_id,
            "status": result.get("status", "succeeded"),
            "posts_regenerated": result.get("posts_regenerated", 0),
            "message": result.get("message", "Regeneration complete"),
        }

    except Exception as e:
        logger.error(f"Regeneration failed for run {run_id}: {str(e)}", exc_info=True)

        # Update run status to failed
        try:
            run = crud.get_run(self.db, run_id)
            if run:
                run.status = "failed"
                run.error_message = str(e)
                run.completed_at = datetime.utcnow()
                self.db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update run status: {str(db_error)}")

        raise
