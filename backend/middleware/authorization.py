"""
Authorization Middleware (TR-021)

Prevents IDOR (Insecure Direct Object Reference) vulnerabilities by verifying
resource ownership before allowing access.

OWASP Top 10 2021: A01:2021 - Broken Access Control

IMPORTANT: This module requires user_id fields to be added to models:
- Project.user_id (ForeignKey to users.id)
- Client.user_id (ForeignKey to users.id)

Until these fields are added, authorization checks will not function properly.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Project, Client, Post, Deliverable, Run
from backend.middleware.auth_dependency import get_current_user
from backend.utils.logger import logger


# ==================== Authorization Helpers ====================


def _check_ownership(resource_type: str, resource, current_user: User) -> bool:
    """
    Check if user owns a resource or is a superuser.

    Args:
        resource_type: Type of resource (for logging)
        resource: The resource instance to check
        current_user: The authenticated user

    Returns:
        True if user has access, False otherwise

    NOTE: Requires user_id field on resource model
    """
    # Superusers have access to all resources
    if current_user.is_superuser:
        logger.debug(f"Superuser {current_user.email} granted access to {resource_type}")
        return True

    # Check if resource has user_id field
    if not hasattr(resource, "user_id"):
        logger.error(
            f"SECURITY ERROR: {resource_type} model missing user_id field - "
            f"denying access as security precaution (TR-021)"
        )
        # SECURITY FIX: Fail closed (deny access) if user_id is missing (TR-021)
        # This prevents IDOR vulnerabilities if a model is missing authorization fields
        return False

    # Check ownership
    if resource.user_id != current_user.id:
        logger.warning(
            f"Authorization denied: User {current_user.email} attempted to access "
            f"{resource_type} owned by user_id={resource.user_id}"
        )
        return False

    return True


# ==================== Project Ownership ====================


async def verify_project_ownership(
    project_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Project:
    """
    Verify user owns project, return project if authorized.

    Raises:
        HTTPException 404: Project not found
        HTTPException 403: User doesn't own project

    Returns:
        Project instance if authorized
    """
    from backend.services import crud

    project = crud.get_project(db, project_id)

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not _check_ownership("Project", project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't own this project",
        )

    return project


# ==================== Client Ownership ====================


async def verify_client_ownership(
    client_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Client:
    """
    Verify user owns client, return client if authorized.

    Raises:
        HTTPException 404: Client not found
        HTTPException 403: User doesn't own client

    Returns:
        Client instance if authorized
    """
    from backend.services import crud

    client = crud.get_client(db, client_id)

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    if not _check_ownership("Client", client, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You don't own this client"
        )

    return client


# ==================== Post Ownership (via Project) ====================


async def verify_post_ownership(
    post_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Post:
    """
    Verify user owns post (via project ownership), return post if authorized.

    Posts are owned indirectly through project ownership.

    Raises:
        HTTPException 404: Post not found
        HTTPException 403: User doesn't own post's project

    Returns:
        Post instance if authorized
    """
    from backend.services import crud

    post = crud.get_post(db, post_id)

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Get project to check ownership
    project = crud.get_project(db, post.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post's project not found"
        )

    if not _check_ownership("Project", project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You don't own this post"
        )

    return post


# ==================== Deliverable Ownership (via Project) ====================


async def verify_deliverable_ownership(
    deliverable_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Deliverable:
    """
    Verify user owns deliverable (via project ownership).

    Deliverables are owned indirectly through project ownership.

    Raises:
        HTTPException 404: Deliverable not found
        HTTPException 403: User doesn't own deliverable's project

    Returns:
        Deliverable instance if authorized
    """
    from backend.services import crud

    deliverable = crud.get_deliverable(db, deliverable_id)

    if not deliverable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable not found")

    # Get project to check ownership
    project = crud.get_project(db, deliverable.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable's project not found"
        )

    if not _check_ownership("Project", project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't own this deliverable",
        )

    return deliverable


# ==================== Run Ownership (via Project) ====================


async def verify_run_ownership(
    run_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Run:
    """
    Verify user owns run (via project ownership).

    Runs are owned indirectly through project ownership.

    Raises:
        HTTPException 404: Run not found
        HTTPException 403: User doesn't own run's project

    Returns:
        Run instance if authorized
    """
    from backend.services import crud

    run = crud.get_run(db, run_id)

    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    # Get project to check ownership
    project = crud.get_project(db, run.project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run's project not found")

    if not _check_ownership("Project", project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You don't own this run"
        )

    return run


# ==================== List Operations Authorization ====================


def filter_user_projects(db: Session, current_user: User):
    """
    Filter query to show only user's projects.

    Apply this to list operations to ensure users only see their own data.

    Example:
        query = db.query(Project)
        query = filter_user_projects(query, current_user)

    NOTE: Requires user_id field on Project model
    """
    from backend.models import Project

    # Superusers see all
    if current_user.is_superuser:
        return db.query(Project)

    # Regular users see only their own
    query = db.query(Project)

    # Check if model has user_id field
    if not hasattr(Project, "user_id"):
        logger.warning("Project model missing user_id field - returning all projects (INSECURE)")
        return query

    return query.filter(Project.user_id == current_user.id)


def filter_user_clients(db: Session, current_user: User):
    """
    Filter query to show only user's clients.

    Apply this to list operations to ensure users only see their own data.

    NOTE: Requires user_id field on Client model
    """
    from backend.models import Client

    # Superusers see all
    if current_user.is_superuser:
        return db.query(Client)

    # Regular users see only their own
    query = db.query(Client)

    # Check if model has user_id field
    if not hasattr(Client, "user_id"):
        logger.warning("Client model missing user_id field - returning all clients (INSECURE)")
        return query

    return query.filter(Client.user_id == current_user.id)


def filter_user_deliverables(db: Session, current_user: User):
    """
    Filter query to show only user's deliverables (via project ownership).

    Apply this to list operations to ensure users only see their own data.

    Deliverables are owned indirectly through project ownership.

    NOTE: Requires user_id field on Project model
    """
    from backend.models import Deliverable, Project

    # Superusers see all
    if current_user.is_superuser:
        return db.query(Deliverable)

    # Regular users see only deliverables from their own projects
    query = db.query(Deliverable).join(Project, Deliverable.project_id == Project.id)

    # Check if Project model has user_id field
    if not hasattr(Project, "user_id"):
        logger.warning(
            "Project model missing user_id field - returning all deliverables (INSECURE)"
        )
        return db.query(Deliverable)

    return query.filter(Project.user_id == current_user.id)


def filter_user_runs(db: Session, current_user: User):
    """
    Filter query to show only user's runs (via project ownership).

    Apply this to list operations to ensure users only see their own data.

    Runs are owned indirectly through project ownership.

    NOTE: Requires user_id field on Project model
    """
    from backend.models import Run, Project

    # Superusers see all
    if current_user.is_superuser:
        return db.query(Run)

    # Regular users see only runs from their own projects
    query = db.query(Run).join(Project, Run.project_id == Project.id)

    # Check if Project model has user_id field
    if not hasattr(Project, "user_id"):
        logger.warning("Project model missing user_id field - returning all runs (INSECURE)")
        return db.query(Run)

    return query.filter(Project.user_id == current_user.id)


def filter_user_posts(db: Session, current_user: User):
    """
    Filter query to show only user's posts (via project ownership).

    Apply this to list operations to ensure users only see their own data.

    Posts are owned indirectly through project ownership.

    NOTE: Requires user_id field on Project model
    """
    from backend.models import Post, Project

    # Superusers see all
    if current_user.is_superuser:
        return db.query(Post)

    # Regular users see only posts from their own projects
    query = db.query(Post).join(Project, Post.project_id == Project.id)

    # Check if Project model has user_id field
    if not hasattr(Project, "user_id"):
        logger.warning("Project model missing user_id field - returning all posts (INSECURE)")
        return db.query(Post)

    return query.filter(Project.user_id == current_user.id)


# ==================== Brief Ownership (via Project) ====================


async def verify_brief_ownership(
    brief_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Verify user owns brief (via project ownership).

    Briefs are owned indirectly through project ownership.

    Raises:
        HTTPException 404: Brief not found
        HTTPException 403: User doesn't own brief's project

    Returns:
        Brief instance if authorized
    """
    from backend.services import crud

    brief = crud.get_brief(db, brief_id)

    if not brief:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")

    # Get project to check ownership
    project = crud.get_project(db, brief.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Brief's project not found"
        )

    if not _check_ownership("Project", project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You don't own this brief"
        )

    return brief


# ==================== AI Assistant Data Scoping ====================


def assistant_scope_query(query, model, current_user: User):
    """Scope an AI-assistant data query according to ENFORCE_RESOURCE_OWNERSHIP.

    The assistant must never expose data the same user couldn't reach through the
    normal API. Its visibility follows the app-wide ownership policy from a single
    source (``settings.ENFORCE_RESOURCE_OWNERSHIP``):

    - Flag OFF (default / "global" mode): every authenticated operator shares the
      instance's data — return the query unfiltered.
    - Flag ON (per-user isolation): filter to rows owned by ``current_user`` via
      the model's ``user_id`` column. Superusers always see everything.

    Unlike the per-endpoint IDOR guards (``verify_*_ownership`` / ``filter_user_*``),
    this helper is the assistant's single scoping point and honors the toggle so
    the assistant's reach matches whatever policy the deployment runs.

    Args:
        query: A SQLAlchemy Query to scope.
        model: The mapped model being queried (must expose ``user_id`` to scope).
        current_user: The authenticated user the assistant is acting for.

    Returns:
        The (possibly filtered) query.
    """
    from backend.config import settings

    # Global mode or superuser: no scoping.
    if not settings.ENFORCE_RESOURCE_OWNERSHIP or getattr(current_user, "is_superuser", False):
        return query

    # Per-user mode: fail closed if the model can't be scoped, mirroring
    # _check_ownership's security-first posture.
    if not hasattr(model, "user_id"):
        logger.error(
            f"SECURITY: assistant_scope_query called for {getattr(model, '__name__', model)} "
            f"which has no user_id column while ENFORCE_RESOURCE_OWNERSHIP is on - "
            f"returning no rows (fail closed)"
        )
        return query.filter(False)

    return query.filter(model.user_id == current_user.id)


def assistant_can_access(resource, current_user: User) -> bool:
    """Return True if the assistant may surface ``resource`` for ``current_user``.

    Object-level counterpart to :func:`assistant_scope_query` for single-row
    checks. Honors ENFORCE_RESOURCE_OWNERSHIP: always True in global mode or for
    superusers; otherwise delegates to the shared ``_check_ownership`` logic.
    """
    from backend.config import settings

    if not settings.ENFORCE_RESOURCE_OWNERSHIP or getattr(current_user, "is_superuser", False):
        return True

    return _check_ownership(type(resource).__name__, resource, current_user)
