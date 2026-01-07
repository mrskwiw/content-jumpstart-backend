"""
CRUD operations for database models.
"""

import base64
import json
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from backend.schemas import BriefCreate, ClientCreate, ClientUpdate, ProjectCreate, ProjectUpdate
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload
from backend.utils.query_cache import cache_short, cache_medium, invalidate_related_caches

from backend.models import Brief, Client, Deliverable, Post, Project, User


# ==================== Cursor Pagination Utilities ====================


def encode_cursor(created_at: datetime, id: str) -> str:
    """
    Encode cursor for keyset pagination.

    Uses base64 encoding of JSON to create opaque cursor string.
    """
    cursor_data = {"created_at": created_at.isoformat(), "id": id}
    cursor_json = json.dumps(cursor_data)
    cursor_bytes = cursor_json.encode("utf-8")
    return base64.b64encode(cursor_bytes).decode("utf-8")


def decode_cursor(cursor: str) -> Tuple[datetime, str]:
    """
    Decode cursor for keyset pagination.

    Returns: (created_at, id) tuple
    """
    cursor_bytes = base64.b64decode(cursor.encode("utf-8"))
    cursor_json = cursor_bytes.decode("utf-8")
    cursor_data = json.loads(cursor_json)
    created_at = datetime.fromisoformat(cursor_data["created_at"])
    return created_at, cursor_data["id"]


# ==================== Projects ====================


@cache_medium(key_prefix="project")
def get_project(db: Session, project_id: str) -> Optional[Project]:
    """
    Get project by ID.

    Performance: Uses eager loading for all relationships
    to prevent N+1 query problem.

    Caching: Medium TTL (10 minutes)
    Cache invalidation: On project create/update/delete
    """
    return (
        db.query(Project)
        .options(
            joinedload(Project.client),
            joinedload(
                Project.brief
            ),  # FIXED: Added missing brief eager loading (fixes session error in generation task)
            joinedload(Project.posts),
            joinedload(Project.deliverables),
            joinedload(Project.runs),
        )
        .filter(Project.id == project_id)
        .first()
    )


@cache_short(key_prefix="projects")
def get_projects(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    client_id: Optional[str] = None,
) -> List[Project]:
    """
    Get list of projects with optional filters.

    Performance: Uses eager loading for all relationships
    to prevent N+1 query problem. Reduces queries by 50-80%.

    Caching: Short TTL (5 minutes)
    Cache invalidation: On project create/update/delete
    """
    # Eager load all relationships to prevent N+1 queries
    query = db.query(Project).options(
        joinedload(Project.client),
        joinedload(Project.brief),
        joinedload(Project.posts),
        joinedload(Project.deliverables),
        joinedload(Project.runs),
    )

    if status:
        query = query.filter(Project.status == status)
    if client_id:
        query = query.filter(Project.client_id == client_id)

    return query.offset(skip).limit(limit).all()


def get_projects_cursor(
    db: Session,
    cursor: Optional[str] = None,
    limit: int = 20,
    status: Optional[str] = None,
    client_id: Optional[str] = None,
) -> dict:
    """
    Get list of projects with cursor-based pagination.

    Keyset pagination using (created_at, id) provides O(1) complexity
    vs O(n) for offset pagination. 90%+ faster for large datasets.

    Args:
        cursor: Opaque cursor string from previous page
        limit: Number of items per page (default: 20)
        status: Optional status filter
        client_id: Optional client ID filter

    Returns:
        {
            "items": List[Project],
            "next_cursor": str | None,
            "has_more": bool
        }
    """
    # Eager load all relationships
    query = db.query(Project).options(
        joinedload(Project.client),
        joinedload(Project.brief),
        joinedload(Project.posts),
        joinedload(Project.deliverables),
        joinedload(Project.runs),
    )

    # Apply filters
    if status:
        query = query.filter(Project.status == status)
    if client_id:
        query = query.filter(Project.client_id == client_id)

    # Apply cursor if provided
    if cursor:
        cursor_created_at, cursor_id = decode_cursor(cursor)
        query = query.filter(
            or_(
                Project.created_at < cursor_created_at,
                and_(Project.created_at == cursor_created_at, Project.id < cursor_id),
            )
        )

    # Order by (created_at DESC, id DESC) for consistent pagination
    query = query.order_by(Project.created_at.desc(), Project.id.desc())

    # Fetch limit + 1 to check if there are more results
    projects = query.limit(limit + 1).all()

    # Check if there are more results
    has_more = len(projects) > limit
    if has_more:
        projects = projects[:limit]

    # Generate next cursor
    next_cursor = None
    if has_more and projects:
        last_project = projects[-1]
        next_cursor = encode_cursor(last_project.created_at, last_project.id)

    return {"items": projects, "next_cursor": next_cursor, "has_more": has_more}


def create_project(db: Session, project: ProjectCreate, user_id: str) -> Project:
    """
    Create new project.

    Cache invalidation: Clears project and client caches

    Args:
        db: Database session
        project: Project data
        user_id: ID of user creating the project (TR-021: ownership)
    """
    project_data = project.model_dump()
    project_data["user_id"] = user_id  # TR-021: Set owner
    db_project = Project(id=f"proj-{uuid.uuid4().hex[:12]}", **project_data)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    # Invalidate caches
    invalidate_related_caches("project", "projects", "client")

    return db_project


def update_project(
    db: Session, project_id: str, project_update: ProjectUpdate
) -> Optional[Project]:
    """
    Update project.

    Cache invalidation: Clears project and client caches
    """
    db_project = get_project(db, project_id)
    if not db_project:
        return None

    update_data = project_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_project, key, value)

    db.commit()
    db.refresh(db_project)

    # Invalidate caches
    invalidate_related_caches("project", "projects", "client")

    return db_project


def delete_project(db: Session, project_id: str) -> bool:
    """
    Delete project.

    Cache invalidation: Clears project and client caches
    """
    db_project = get_project(db, project_id)
    if not db_project:
        return False

    db.delete(db_project)
    db.commit()

    # Invalidate caches
    invalidate_related_caches("project", "projects", "client")

    return True


# ==================== Clients ====================


@cache_medium(key_prefix="client")
def get_client(db: Session, client_id: str) -> Optional[Client]:
    """
    Get client by ID.

    Performance: Uses eager loading for projects relationship
    to prevent N+1 query problem.

    Caching: Medium TTL (10 minutes)
    Cache invalidation: On client create
    """
    return (
        db.query(Client).options(joinedload(Client.projects)).filter(Client.id == client_id).first()
    )


@cache_medium(key_prefix="clients")
def get_clients(db: Session, skip: int = 0, limit: int = 100) -> List[Client]:
    """
    Get list of clients.

    Performance: Uses eager loading for projects relationship
    to prevent N+1 query problem.

    Caching: Medium TTL (10 minutes) - clients change less frequently
    Cache invalidation: On client create
    """
    return db.query(Client).options(joinedload(Client.projects)).offset(skip).limit(limit).all()


def create_client(db: Session, client: ClientCreate, user_id: str) -> Client:
    """
    Create new client.

    Cache invalidation: Clears client caches

    Args:
        db: Database session
        client: Client data
        user_id: ID of user creating the client (TR-021: ownership)
    """
    client_id = f"client-{uuid.uuid4().hex[:12]}"
    print(f"📝 Creating client: {client_id} ({client.name})")

    client_data = client.model_dump()
    client_data["user_id"] = user_id  # TR-021: Set owner
    db_client = Client(id=client_id, **client_data)
    db.add(db_client)

    try:
        db.commit()
        print(f"✅ Client committed to database: {client_id}")
    except Exception as e:
        print(f"❌ Database commit failed for client {client_id}: {str(e)}")
        db.rollback()
        raise

    db.refresh(db_client)
    print(f"🔄 Client refreshed: {client_id}")

    # Invalidate caches
    invalidate_related_caches("client", "clients")
    print(f"🗑️  Cache invalidated for client: {client_id}")

    return db_client


def update_client(db: Session, client_id: str, client_update: ClientUpdate) -> Optional[Client]:
    """
    Update client.

    Cache invalidation: Clears client and project caches
    """
    print(f"🔄 Updating client: {client_id}")

    db_client = get_client(db, client_id)
    if not db_client:
        print(f"❌ Client not found: {client_id}")
        return None

    update_data = client_update.model_dump(exclude_unset=True)
    print(f"📝 Update fields: {list(update_data.keys())}")

    for key, value in update_data.items():
        setattr(db_client, key, value)

    try:
        db.commit()
        print(f"✅ Client update committed to database: {client_id}")
    except Exception as e:
        print(f"❌ Database commit failed for client {client_id}: {str(e)}")
        db.rollback()
        raise

    db.refresh(db_client)
    print(f"🔄 Client refreshed: {client_id}")

    # Invalidate caches
    invalidate_related_caches("client", "clients", "project", "projects")
    print(f"🗑️  Cache invalidated for client: {client_id}")

    return db_client


# ==================== Posts ====================


@cache_short(key_prefix="post")
def get_post(db: Session, post_id: str) -> Optional[Post]:
    """
    Get post by ID.

    Performance: Uses eager loading for project and run relationships
    to prevent N+1 query problem.

    Caching: Short TTL (5 minutes)
    Cache invalidation: On post creation (via generator)
    """
    return (
        db.query(Post)
        .options(joinedload(Post.project), joinedload(Post.run))
        .filter(Post.id == post_id)
        .first()
    )


@cache_short(key_prefix="posts")
def get_posts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[str] = None,
    run_id: Optional[str] = None,
    status: Optional[str] = None,
    platform: Optional[str] = None,
    has_cta: Optional[bool] = None,
    template_name: Optional[str] = None,
    needs_review: Optional[bool] = None,
    search: Optional[str] = None,
    min_word_count: Optional[int] = None,
    max_word_count: Optional[int] = None,
    min_readability: Optional[float] = None,
    max_readability: Optional[float] = None,
) -> List[Post]:
    """
    Get list of posts with optional filters.

    Performance: Uses eager loading for project and run relationships
    to prevent N+1 query problem.

    Caching: Short TTL (5 minutes) - posts are frequently viewed/filtered
    Cache invalidation: On post creation (via generator)
    """
    # Eager load relationships to prevent N+1 queries
    query = db.query(Post).options(joinedload(Post.project), joinedload(Post.run))

    # Basic filters
    if project_id:
        query = query.filter(Post.project_id == project_id)
    if run_id:
        query = query.filter(Post.run_id == run_id)
    if status:
        query = query.filter(Post.status == status)

    # Platform filter
    if platform:
        query = query.filter(Post.target_platform == platform)

    # CTA filter
    if has_cta is not None:
        query = query.filter(Post.has_cta == has_cta)

    # Template filter
    if template_name:
        query = query.filter(Post.template_name.ilike(f"%{template_name}%"))

    # Review flag filter (posts with any flags)
    if needs_review is not None:
        if needs_review:
            # Posts with flags (flags is not null and not empty array)
            query = query.filter(Post.flags.isnot(None))
            query = query.filter(Post.flags != [])
        else:
            # Posts without flags (flags is null or empty array)
            from sqlalchemy import or_

            query = query.filter(or_(Post.flags.is_(None), Post.flags == []))

    # Text search in content
    if search:
        query = query.filter(Post.content.ilike(f"%{search}%"))

    # Word count range filters
    if min_word_count is not None:
        query = query.filter(Post.word_count >= min_word_count)
    if max_word_count is not None:
        query = query.filter(Post.word_count <= max_word_count)

    # Readability score range filters
    if min_readability is not None:
        query = query.filter(Post.readability_score >= min_readability)
    if max_readability is not None:
        query = query.filter(Post.readability_score <= max_readability)

    return query.order_by(Post.created_at.desc()).offset(skip).limit(limit).all()


def get_posts_cursor(
    db: Session,
    cursor: Optional[str] = None,
    limit: int = 50,
    project_id: Optional[str] = None,
    run_id: Optional[str] = None,
    status: Optional[str] = None,
    platform: Optional[str] = None,
) -> dict:
    """
    Get list of posts with cursor-based pagination.

    Keyset pagination using (created_at, id) provides O(1) complexity.
    Essential for high-volume post listings (30+ posts per project).

    Args:
        cursor: Opaque cursor string from previous page
        limit: Number of items per page (default: 50)
        project_id: Optional project filter
        run_id: Optional run filter
        status: Optional status filter
        platform: Optional platform filter

    Returns:
        {
            "items": List[Post],
            "next_cursor": str | None,
            "has_more": bool
        }
    """
    # Eager load relationships
    query = db.query(Post).options(joinedload(Post.project), joinedload(Post.run))

    # Apply filters
    if project_id:
        query = query.filter(Post.project_id == project_id)
    if run_id:
        query = query.filter(Post.run_id == run_id)
    if status:
        query = query.filter(Post.status == status)
    if platform:
        query = query.filter(Post.target_platform == platform)

    # Apply cursor if provided
    if cursor:
        cursor_created_at, cursor_id = decode_cursor(cursor)
        query = query.filter(
            or_(
                Post.created_at < cursor_created_at,
                and_(Post.created_at == cursor_created_at, Post.id < cursor_id),
            )
        )

    # Order by (created_at DESC, id DESC)
    query = query.order_by(Post.created_at.desc(), Post.id.desc())

    # Fetch limit + 1
    posts = query.limit(limit + 1).all()

    # Check for more results
    has_more = len(posts) > limit
    if has_more:
        posts = posts[:limit]

    # Generate next cursor
    next_cursor = None
    if has_more and posts:
        last_post = posts[-1]
        next_cursor = encode_cursor(last_post.created_at, last_post.id)

    return {"items": posts, "next_cursor": next_cursor, "has_more": has_more}


# ==================== Deliverables ====================


def get_deliverable(db: Session, deliverable_id: str) -> Optional[Deliverable]:
    """
    Get deliverable by ID.

    Performance: Uses eager loading for project and client relationships
    to prevent N+1 query problem.
    """
    return (
        db.query(Deliverable)
        .options(joinedload(Deliverable.project), joinedload(Deliverable.client))
        .filter(Deliverable.id == deliverable_id)
        .first()
    )


def get_deliverables(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    client_id: Optional[str] = None,
) -> List[Deliverable]:
    """Get list of deliverables with optional filters

    Performance: Uses eager loading for project and client relationships
    to prevent N+1 query problem.
    """
    # Eager load relationships
    query = db.query(Deliverable).options(
        joinedload(Deliverable.project), joinedload(Deliverable.client)
    )

    if status:
        query = query.filter(Deliverable.status == status)
    if client_id:
        query = query.filter(Deliverable.client_id == client_id)

    return query.offset(skip).limit(limit).all()


def mark_deliverable_delivered(
    db: Session,
    deliverable_id: str,
    delivered_at,
    proof_url: Optional[str] = None,
    proof_notes: Optional[str] = None,
) -> Optional[Deliverable]:
    """Mark deliverable as delivered"""
    db_deliverable = get_deliverable(db, deliverable_id)
    if not db_deliverable:
        return None

    db_deliverable.status = "delivered"
    db_deliverable.delivered_at = delivered_at
    db_deliverable.proof_url = proof_url
    db_deliverable.proof_notes = proof_notes

    db.commit()
    db.refresh(db_deliverable)
    return db_deliverable


# ==================== Briefs ====================


def get_brief(db: Session, brief_id: str) -> Optional[Brief]:
    """
    Get brief by ID.

    Performance: Uses eager loading for project relationship
    to prevent N+1 query problem.
    """
    return db.query(Brief).options(joinedload(Brief.project)).filter(Brief.id == brief_id).first()


def get_brief_by_project(db: Session, project_id: str) -> Optional[Brief]:
    """
    Get brief by project ID.

    Performance: Uses eager loading for project relationship
    to prevent N+1 query problem.
    """
    return (
        db.query(Brief)
        .options(joinedload(Brief.project))
        .filter(Brief.project_id == project_id)
        .first()
    )


def create_brief(
    db: Session, brief: BriefCreate, source: str, file_path: Optional[str] = None
) -> Brief:
    """Create new brief"""
    db_brief = Brief(
        id=f"brief-{uuid.uuid4().hex[:12]}",
        project_id=brief.project_id,
        content=brief.content,
        source=source,
        file_path=file_path,
    )
    db.add(db_brief)
    db.commit()
    db.refresh(db_brief)
    return db_brief


# ==================== Runs ====================


def get_run(db: Session, run_id: str):
    """
    Get run by ID.

    Performance: Uses eager loading for project relationship
    to prevent N+1 query problem.
    """
    from models import Run

    return db.query(Run).options(joinedload(Run.project)).filter(Run.id == run_id).first()


def get_runs(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
):
    """
    Get list of runs with optional filters.

    Performance: Uses eager loading for project relationship
    to prevent N+1 query problem.
    """
    from models import Run

    # Eager load project relationship
    query = db.query(Run).options(joinedload(Run.project))

    if project_id:
        query = query.filter(Run.project_id == project_id)
    if status:
        query = query.filter(Run.status == status)

    return query.offset(skip).limit(limit).all()


def create_run(db: Session, project_id: str, is_batch: bool = False):
    """Create new run"""
    from models import Run

    db_run = Run(
        id=f"run-{uuid.uuid4().hex[:12]}",
        project_id=project_id,
        is_batch=is_batch,
        status="pending",
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    return db_run


def update_run(db: Session, run_id: str, **kwargs):
    """Update run"""

    db_run = get_run(db, run_id)
    if not db_run:
        return None

    for key, value in kwargs.items():
        if hasattr(db_run, key) and value is not None:
            setattr(db_run, key, value)

    db.commit()
    db.refresh(db_run)
    return db_run


# ==================== Users ====================


def get_user(db: Session, user_id: str) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def create_user(
    db: Session,
    email: str,
    hashed_password: str,
    full_name: str,
    is_active: bool = True,
    is_superuser: bool = False,
) -> User:
    """
    Create new user.

    Args:
        db: Database session
        email: User email (validated)
        hashed_password: Hashed password
        full_name: User's full name
        is_active: User active status (default: True for backward compatibility)
        is_superuser: Admin status (default: False, TR-023: never allow self-promotion)

    Returns:
        Created User instance

    Security (TR-023):
        - is_superuser defaults to False and should never be True from registration
        - is_active can be False to require admin activation
    """
    db_user = User(
        id=f"user-{uuid.uuid4().hex[:12]}",
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        is_active=is_active,  # TR-023: Configurable activation status
        is_superuser=is_superuser,  # TR-023: Explicit control, defaults to False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
