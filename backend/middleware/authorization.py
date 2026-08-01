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

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Project, Client, Post, Deliverable, Run
from backend.models.team import WRITE_ROLES
from backend.middleware.auth_dependency import get_current_user
from backend.utils.logger import logger

# HTTP methods that MUTATE a resource — a team "viewer" is blocked from these.
_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _is_write(request: Request | None) -> bool:
    return request is not None and request.method.upper() in _WRITE_METHODS


# ==================== Authorization Helpers ====================


def _check_ownership(
    resource_type: str,
    resource,
    current_user: User,
    db: Session | None = None,
    *,
    is_write: bool = False,
) -> bool:
    """Check whether ``current_user`` may access ``resource`` (COLLAB-01, team-aware).

    Access is by TEAM now, not by the single ``user_id`` creator:
    - superusers → always allowed;
    - a resource with a ``team_id`` → the caller must belong to that team, and for a
      **write** (``is_write``) their role must permit mutation (a ``viewer`` is 403'd);
    - a legacy resource with ``team_id IS NULL`` (pre-backfill) → fall back to the old
      creator check (``resource.user_id == current_user.id``);
    - a model with neither field → fail closed.

    ``db`` is needed to resolve the caller's membership/role for the team path; when it
    is omitted (e.g. the assistant helpers) only the superuser + legacy paths apply.
    """
    if current_user.is_superuser:
        logger.debug(f"Superuser {current_user.email} granted access to {resource_type}")
        return True

    has_team = hasattr(resource, "team_id")
    has_user = hasattr(resource, "user_id")
    if not has_team and not has_user:
        logger.error(f"SECURITY ERROR: {resource_type} missing team_id/user_id - denying (TR-021)")
        return False

    resource_team_id = getattr(resource, "team_id", None) if has_team else None

    # Legacy row not yet backfilled onto a team → creator-based check (unchanged).
    if resource_team_id is None:
        owner_id = getattr(resource, "user_id", None) if has_user else None
        if owner_id != current_user.id:
            logger.warning(
                f"Authorization denied: {current_user.email} -> {resource_type} "
                f"(legacy owner_id={owner_id})"
            )
            return False
        return True

    # Team-owned: the caller must be a member of the resource's team.
    from backend.services import team_service

    membership = team_service.get_membership(db, current_user.id) if db is not None else None
    if membership is None or membership.team_id != resource_team_id:
        logger.warning(
            f"Authorization denied: {current_user.email} not in team {resource_team_id} "
            f"for {resource_type}"
        )
        return False
    if is_write and membership.role not in WRITE_ROLES:
        logger.warning(
            f"Authorization denied: {current_user.email} role={membership.role} "
            f"may not write {resource_type} (viewer is read-only)"
        )
        return False
    return True


def _team_scope(query, model_cls, db: Session, current_user: User):
    """Scope a list query to the caller's team (COLLAB-01).

    Returns rows owned by the caller's team, plus any legacy un-backfilled rows the
    caller created (``team_id IS NULL AND user_id == me``) so nothing disappears during
    the migration window. ``model_cls`` must expose ``team_id`` + ``user_id`` (Client /
    Project — the indirect resources scope through Project).
    """
    from backend.services import team_service

    team_id = team_service.user_team_id(db, current_user.id)
    if team_id is None:
        return query.filter(model_cls.user_id == current_user.id)
    return query.filter(
        (model_cls.team_id == team_id)
        | (model_cls.team_id.is_(None) & (model_cls.user_id == current_user.id))
    )


# ==================== Project Ownership ====================


async def verify_project_ownership(
    request: Request,
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    if not _check_ownership("Project", project, current_user, db, is_write=_is_write(request)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't own this project",
        )

    return project


# ==================== Client Ownership ====================


async def verify_client_ownership(
    request: Request,
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    if not _check_ownership("Client", client, current_user, db, is_write=_is_write(request)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You don't own this client"
        )

    return client


# ==================== Post Ownership (via Project) ====================


async def verify_post_ownership(
    request: Request,
    post_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    if not _check_ownership("Project", project, current_user, db, is_write=_is_write(request)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You don't own this post"
        )

    return post


# ==================== Deliverable Ownership (via Project) ====================


async def verify_deliverable_ownership(
    request: Request,
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

    if not _check_ownership("Project", project, current_user, db, is_write=_is_write(request)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't own this deliverable",
        )

    return deliverable


# ==================== Run Ownership (via Project) ====================


async def verify_run_ownership(
    request: Request,
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    if not _check_ownership("Project", project, current_user, db, is_write=_is_write(request)):
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

    # COLLAB-01: the caller's whole team, not just their own rows.
    return _team_scope(db.query(Project), Project, db, current_user)


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

    # COLLAB-01: the caller's whole team, not just their own rows.
    return _team_scope(db.query(Client), Client, db, current_user)


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

    # COLLAB-01: scope through the parent project's team.
    query = db.query(Deliverable).join(Project, Deliverable.project_id == Project.id)
    return _team_scope(query, Project, db, current_user)


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

    # COLLAB-01: scope through the parent project's team.
    query = db.query(Run).join(Project, Run.project_id == Project.id)
    return _team_scope(query, Project, db, current_user)


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

    # COLLAB-01: scope through the parent project's team.
    query = db.query(Post).join(Project, Post.project_id == Project.id)
    return _team_scope(query, Project, db, current_user)


# ==================== Brief Ownership (via Project) ====================


async def verify_brief_ownership(
    request: Request,
    brief_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    if not _check_ownership("Project", project, current_user, db, is_write=_is_write(request)):
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
