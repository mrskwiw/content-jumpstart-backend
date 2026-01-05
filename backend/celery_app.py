"""
Celery application configuration for background job processing.

Phase 2 optimization: Background job queue implementation
- Prevents HTTP timeouts during long-running content generation
- Enables progress tracking and status updates
- Supports concurrent generation for multiple projects
- Uses Redis as message broker and result backend

Usage:
    # Start Celery worker (development)
    celery -A backend.celery_app worker --loglevel=info

    # Start Celery worker (production with concurrency)
    celery -A backend.celery_app worker --loglevel=info --concurrency=4

    # Start Flower monitoring UI (optional)
    celery -A backend.celery_app flower --port=5555
"""
from celery import Celery
from backend.config import settings

# Initialize Celery application
celery_app = Celery(
    "content_jumpstart",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task tracking
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_send_sent_event=settings.CELERY_TASK_SEND_SENT_EVENT,

    # Time limits
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,

    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Store additional task metadata

    # Worker configuration
    worker_prefetch_multiplier=1,  # One task at a time (long-running tasks)
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (memory management)

    # Task routing (for future expansion to multiple queues)
    task_routes={
        "backend.tasks.generation.*": {"queue": "generation"},  # Content generation queue
        "backend.tasks.email.*": {"queue": "email"},            # Email queue (future)
        "backend.tasks.export.*": {"queue": "export"},          # Export queue (future)
    },

    # Default queue
    task_default_queue="generation",

    # Retry configuration
    task_acks_late=True,  # Acknowledge task only after completion (safe for crashes)
    task_reject_on_worker_lost=True,  # Requeue task if worker dies
)

# Auto-discover tasks in these modules
celery_app.autodiscover_tasks(["backend.tasks"])

# Health check task for monitoring
@celery_app.task(name="health_check")
def health_check():
    """Simple health check task for monitoring Celery worker availability."""
    return {"status": "healthy", "message": "Celery worker is running"}
