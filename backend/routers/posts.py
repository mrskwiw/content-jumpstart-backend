"""Posts router"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from backend.utils.logger import logger
from backend.middleware.auth_dependency import get_current_user
from src.validators.prompt_injection_defense import sanitize_prompt_input
from backend.middleware.authorization import (
    verify_post_ownership,
    filter_user_posts,
)  # TR-021: Authorization
from backend.schemas.atomize import AtomizeRequest, AtomizeResponse
from backend.schemas.post import PostResponse, PostUpdate
from backend.services import crud
from backend.services.atomize import pull_quotes, to_thread
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from backend.utils.pagination import paginate_hybrid, get_pagination_params

from backend.database import get_db
from backend.models import Post, User
from backend.utils.http_rate_limiter import lenient_limiter

router = APIRouter()


@router.post("/atomize", response_model=AtomizeResponse)
@lenient_limiter.limit("500/hour")  # TR-004: cheap, stateless CPU-only transform
async def atomize_content(
    request: Request,
    body: AtomizeRequest,
    current_user: User = Depends(get_current_user),
) -> AtomizeResponse:
    """Repurpose long-form content into a numbered thread + pull-quotes (ATOMIZE-01).

    Deterministic, no LLM call and no persistence — a stateless transform over the
    supplied text, so it needs auth but no ownership check.
    """
    if not body.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="text must not be blank"
        )
    thread = to_thread(body.text, max_chars=body.max_chars)
    quotes = pull_quotes(body.text, limit=body.max_quotes)
    return AtomizeResponse(thread=thread, thread_count=len(thread), pull_quotes=quotes)


@router.get("/")
@lenient_limiter.limit("1000/hour")  # TR-004: Cheap read operation
async def list_posts(
    request: Request,
    page: Optional[int] = Query(
        None, ge=1, description="Page number (1-indexed, for offset pagination)"
    ),
    cursor: Optional[str] = Query(
        None, description="Pagination cursor (for cursor-based pagination)"
    ),
    page_size: int = Query(20, ge=1, le=500, description="Number of items per page"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    run_id: Optional[str] = Query(None, description="Filter by run ID"),
    status: Optional[str] = Query(None, description="Filter by status (approved, flagged)"),
    platform: Optional[str] = Query(
        None, description="Filter by platform (linkedin, twitter, facebook, blog)"
    ),
    has_cta: Optional[bool] = Query(None, description="Filter by CTA presence"),
    template_id: Optional[str] = Query(None, description="Filter by template ID"),
    template_name: Optional[str] = Query(
        None, description="Filter by template name (partial match)"
    ),
    needs_review: Optional[bool] = Query(
        None, description="Filter posts with/without review flags"
    ),
    search: Optional[str] = Query(None, description="Search in post content"),
    min_word_count: Optional[int] = Query(None, ge=0, description="Minimum word count"),
    max_word_count: Optional[int] = Query(None, ge=0, description="Maximum word count"),
    min_readability: Optional[float] = Query(
        None, ge=0, le=100, description="Minimum readability score"
    ),
    max_readability: Optional[float] = Query(
        None, ge=0, le=100, description="Maximum readability score"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    List posts with comprehensive filtering options.

    Rate limit: 1000/hour (cheap read operation)

    Pagination:
    - Hybrid approach: offset pagination for first 5 pages, cursor for deeper pagination
    - Use 'page' parameter for traditional pagination (e.g., page=1, page=2)
    - Use 'cursor' parameter for efficient deep pagination (get cursor from previous response)
    - Automatically switches to cursor pagination when page >= 6

    Supports filtering by:
    - Project, run, status
    - Platform (linkedin, twitter, facebook, blog)
    - CTA presence
    - Template name (partial match)
    - Review flags (needs_review=true for flagged posts)
    - Content search
    - Word count range
    - Readability score range

    Caching:
    - max-age: 300 seconds (5 minutes)
    - stale-while-revalidate: 600 seconds (10 minutes)
    - ETag support for 304 Not Modified responses

    Example:
        GET /api/posts?page=1&page_size=20&project_id=proj-123
        GET /api/posts?cursor=2025-12-15T10:30:00:post-abc123&page_size=20
    """
    # Validate pagination params
    pagination_params = get_pagination_params(page=page, cursor=cursor, page_size=page_size)

    # TR-021: Build base query filtered by user ownership
    # Users can only see posts from projects they own
    query = filter_user_posts(db, current_user)

    # Additional filter by project_id if specified
    if project_id:
        # Verify user owns the project before showing its posts
        project = crud.get_project(db, project_id)
        if project:
            # Reattach detached object to session for attribute access
            project = db.merge(project)
            if project.user_id != current_user.id and not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You don't own this project",
                )
        query = query.filter(Post.project_id == project_id)
    if run_id:
        query = query.filter(Post.run_id == run_id)
    if status:
        query = query.filter(Post.status == status)
    if platform:
        query = query.filter(Post.target_platform == platform)
    if has_cta is not None:
        query = query.filter(Post.has_cta == has_cta)
    if template_id is not None:
        query = query.filter(Post.template_id == template_id)
    if template_name:
        query = query.filter(Post.template_name.ilike(f"%{template_name}%"))
    if needs_review is not None:
        if needs_review:
            # Posts with flags (flags is not null and not empty array)
            query = query.filter(Post.flags.isnot(None))
            query = query.filter(Post.flags != [])
        else:
            # Posts without flags (flags is null or empty array)
            from sqlalchemy import or_

            query = query.filter(or_(Post.flags.is_(None), Post.flags == []))
    if search:
        query = query.filter(Post.content.ilike(f"%{search}%"))
    if min_word_count is not None:
        query = query.filter(Post.word_count >= min_word_count)
    if max_word_count is not None:
        query = query.filter(Post.word_count <= max_word_count)
    if min_readability is not None:
        query = query.filter(Post.readability_score >= min_readability)
    if max_readability is not None:
        query = query.filter(Post.readability_score <= max_readability)

    # Apply pagination
    paginated = paginate_hybrid(
        query=query,
        page=pagination_params["page"],
        cursor=pagination_params["cursor"],
        page_size=pagination_params["page_size"],
        order_by_field="created_at",
        order_direction="desc",
    )

    # Batch-fetch team-review status for the whole page in ONE query (PostApproval.post_id is
    # unique + indexed) so the content-review grid can show per-row approval status WITHOUT an
    # N+1 per-post fetch (the per-post review panel stays lazy — Decision #217).
    from backend.models.post_approval import PostApproval

    items = paginated["items"]
    post_ids = [p.id for p in items]
    approval_by_post: Dict[str, str] = {}
    if post_ids:
        for row in (
            db.query(PostApproval.post_id, PostApproval.status)
            .filter(PostApproval.post_id.in_(post_ids))
            .all()
        ):
            approval_by_post[row[0]] = row[1]

    # Convert items to response schema (mode="json" ensures datetime serialization)
    posts_data = []
    for p in items:
        item = PostResponse.model_validate(p).model_dump(mode="json")
        item["approval_status"] = approval_by_post.get(p.id)
        posts_data.append(item)

    # Prepare response with pagination metadata
    response_data = {
        "items": posts_data,
        "metadata": paginated["metadata"].model_dump(mode="json"),
    }

    return JSONResponse(content=response_data)


@router.get("/{post_id}")
@lenient_limiter.limit("1000/hour")  # TR-004: Cheap read operation
async def get_post(
    post_id: str,
    request: Request,
    post: Post = Depends(verify_post_ownership),  # TR-021: Authorization check
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get post by ID.

    Rate limit: 1000/hour (cheap read operation)
    Authorization: TR-021 - User must own post's project
    """
    # TR-021: post already verified by dependency
    post_data = PostResponse.model_validate(post).model_dump(mode="json")
    return JSONResponse(content=post_data)


@router.patch("/{post_id}")
@lenient_limiter.limit("1000/hour")  # TR-004: Cheap operation (write but infrequent)
async def update_post(
    request: Request,
    post_id: str,
    post_update: PostUpdate,
    post: Post = Depends(verify_post_ownership),  # TR-021: Authorization check
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PostResponse:
    """
    Update a post's content.

    Rate limit: 1000/hour (cheap operation)
    Authorization: TR-021 - User must own post's project

    Updates the content field and recalculates:
    - word_count
    - readability_score
    - has_cta

    Returns the updated post.
    """
    # TR-021: post already verified by dependency

    # Update content
    # TR-005: Sanitize post content to prevent prompt injection

    # Update content
    try:
        # Update content
        post.content = sanitize_prompt_input(post_update.content, strict=False)

    # Update content
    except ValueError as e:
        # Update content
        logger.warning(f"Prompt injection detected in post update: {e}")

        # Update content
        raise HTTPException(
            # Update content
            status_code=status.HTTP_400_BAD_REQUEST,
            # Update content
            detail="Post content contains potentially unsafe patterns. Please rephrase.",
            # Update content
        )

    # Recalculate word count
    post.word_count = len(post_update.content.split())

    # Recalculate readability score (Flesch Reading Ease)
    words = post.word_count
    sentences = len([s for s in post_update.content.split(".") if s.strip()])
    if sentences == 0:
        sentences = 1

    # Simple syllable estimation
    syllables = sum(max(1, len(word) // 3) for word in post_update.content.split())

    if words > 0:
        avg_words_per_sentence = words / sentences
        avg_syllables_per_word = syllables / words
        readability = 206.835 - 1.015 * avg_words_per_sentence - 84.6 * avg_syllables_per_word
        post.readability_score = max(0, min(100, round(readability, 1)))
    else:
        post.readability_score = 0

    # Recalculate CTA presence — delegate to Post._detect_cta so that backend
    # and validator share the same last-2-lines detection logic.
    from src.models.post import Post as _CLIPost

    post.has_cta = _CLIPost._detect_cta(post_update.content)

    # Operator override: clear flags and force approved status so a human
    # judgment call can bypass automatic validation results.
    if post_update.approve_override:
        post.status = "approved"
        post.flags = None
        logger.info(f"Post {post.id} manually approved by {current_user.email} (override)")

    # Commit changes
    db.commit()
    db.refresh(post)

    return PostResponse.model_validate(post)
