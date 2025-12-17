"""Posts router"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from middleware.auth_dependency import get_current_user
from schemas.post import PostResponse
from services import crud
from sqlalchemy.orm import Session
from utils.caching import CacheConfig, create_cacheable_response
from utils.pagination import paginate_hybrid, get_pagination_params

from database import get_db
from models import Post, User

router = APIRouter()


@router.get("/")
async def list_posts(
    request: Request,
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed, for offset pagination)"),
    cursor: Optional[str] = Query(None, description="Pagination cursor (for cursor-based pagination)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    run_id: Optional[str] = Query(None, description="Filter by run ID"),
    status: Optional[str] = Query(None, description="Filter by status (approved, flagged)"),
    platform: Optional[str] = Query(None, description="Filter by platform (linkedin, twitter, facebook, blog)"),
    has_cta: Optional[bool] = Query(None, description="Filter by CTA presence"),
    template_name: Optional[str] = Query(None, description="Filter by template name (partial match)"),
    needs_review: Optional[bool] = Query(None, description="Filter posts with/without review flags"),
    search: Optional[str] = Query(None, description="Search in post content"),
    min_word_count: Optional[int] = Query(None, ge=0, description="Minimum word count"),
    max_word_count: Optional[int] = Query(None, ge=0, description="Maximum word count"),
    min_readability: Optional[float] = Query(None, ge=0, le=100, description="Minimum readability score"),
    max_readability: Optional[float] = Query(None, ge=0, le=100, description="Maximum readability score"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    List posts with comprehensive filtering options.

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

    # Build base query
    query = db.query(Post)

    # Apply filters
    if project_id:
        query = query.filter(Post.project_id == project_id)
    if run_id:
        query = query.filter(Post.run_id == run_id)
    if status:
        query = query.filter(Post.status == status)
    if platform:
        query = query.filter(Post.target_platform == platform)
    if has_cta is not None:
        query = query.filter(Post.has_cta == has_cta)
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
            query = query.filter(
                or_(Post.flags.is_(None), Post.flags == [])
            )
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
        order_direction="desc"
    )

    # Convert items to response schema
    posts_data = [PostResponse.model_validate(p).model_dump() for p in paginated["items"]]

    # Prepare response with pagination metadata
    response_data = {
        "items": posts_data,
        "metadata": paginated["metadata"].model_dump()
    }

    # Return cacheable response with ETag
    return create_cacheable_response(
        data=response_data,
        cache_config=CacheConfig.POSTS,
        request=request,
    )


@router.get("/{post_id}")
async def get_post(
    post_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get post by ID.

    Caching:
    - max-age: 300 seconds (5 minutes)
    - ETag support for 304 Not Modified responses
    """
    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Convert to dict for caching
    post_data = PostResponse.model_validate(post).model_dump()

    # Return cacheable response
    return create_cacheable_response(
        data=post_data,
        cache_config=CacheConfig.POSTS,
        request=request,
    )
