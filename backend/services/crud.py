"""
CRUD operations for database models.
"""
import uuid
from typing import List, Optional

from schemas import BriefCreate, ClientCreate, ProjectCreate, ProjectUpdate
from sqlalchemy.orm import Session, joinedload
from utils.query_cache import cache_short, cache_medium, invalidate_related_caches

from models import Brief, Client, Deliverable, Post, Project, User

# ==================== Projects ====================


@cache_medium(key_prefix="project")
def get_project(db: Session, project_id: str) -> Optional[Project]:
    """
    Get project by ID.

    Caching: Medium TTL (10 minutes)
    Cache invalidation: On project create/update/delete
    """
    return db.query(Project).filter(Project.id == project_id).first()


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

    Performance: Uses eager loading for client relationship
    to prevent N+1 query problem.

    Caching: Short TTL (5 minutes)
    Cache invalidation: On project create/update/delete
    """
    # Eager load client relationship
    query = db.query(Project).options(joinedload(Project.client))

    if status:
        query = query.filter(Project.status == status)
    if client_id:
        query = query.filter(Project.client_id == client_id)

    return query.offset(skip).limit(limit).all()


def create_project(db: Session, project: ProjectCreate) -> Project:
    """
    Create new project.

    Cache invalidation: Clears project and client caches
    """
    db_project = Project(id=f"proj-{uuid.uuid4().hex[:12]}", **project.model_dump())
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

    Caching: Medium TTL (10 minutes)
    Cache invalidation: On client create
    """
    return db.query(Client).filter(Client.id == client_id).first()


@cache_medium(key_prefix="clients")
def get_clients(db: Session, skip: int = 0, limit: int = 100) -> List[Client]:
    """
    Get list of clients.

    Caching: Medium TTL (10 minutes) - clients change less frequently
    Cache invalidation: On client create
    """
    return db.query(Client).offset(skip).limit(limit).all()


def create_client(db: Session, client: ClientCreate) -> Client:
    """
    Create new client.

    Cache invalidation: Clears client caches
    """
    db_client = Client(id=f"client-{uuid.uuid4().hex[:12]}", **client.model_dump())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)

    # Invalidate caches
    invalidate_related_caches("client", "clients")

    return db_client


# ==================== Posts ====================


@cache_short(key_prefix="post")
def get_post(db: Session, post_id: str) -> Optional[Post]:
    """
    Get post by ID.

    Caching: Short TTL (5 minutes)
    Cache invalidation: On post creation (via generator)
    """
    return db.query(Post).filter(Post.id == post_id).first()


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
    query = db.query(Post).options(
        joinedload(Post.project),
        joinedload(Post.run)
    )

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
            query = query.filter(
                or_(Post.flags.is_(None), Post.flags == [])
            )

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


# ==================== Deliverables ====================


def get_deliverable(db: Session, deliverable_id: str) -> Optional[Deliverable]:
    """Get deliverable by ID"""
    return db.query(Deliverable).filter(Deliverable.id == deliverable_id).first()


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
        joinedload(Deliverable.project),
        joinedload(Deliverable.client)
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
    """Get brief by ID"""
    return db.query(Brief).filter(Brief.id == brief_id).first()


def get_brief_by_project(db: Session, project_id: str) -> Optional[Brief]:
    """Get brief by project ID"""
    return db.query(Brief).filter(Brief.project_id == project_id).first()


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
    """Get run by ID"""
    from models import Run
    return db.query(Run).filter(Run.id == run_id).first()


def get_runs(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
):
    """Get list of runs with optional filters"""
    from models import Run
    query = db.query(Run)

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
    from models import Run
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


def create_user(db: Session, email: str, hashed_password: str, full_name: str) -> User:
    """Create new user"""
    db_user = User(
        id=f"user-{uuid.uuid4().hex[:12]}",
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
