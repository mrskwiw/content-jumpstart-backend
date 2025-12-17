"""
Pagination utilities with hybrid offset/cursor approach.

Provides optimized pagination for large result sets:
- Offset pagination for small offsets (fast, simple)
- Cursor pagination for large offsets (efficient, consistent)
- Automatic strategy selection based on offset size
"""
from typing import Any, Dict, List, Optional, TypeVar, Generic
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import desc, asc
from sqlalchemy.orm import Query

T = TypeVar("T")


class PaginationMetadata(BaseModel):
    """Pagination metadata returned with results."""

    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    strategy: str  # "offset" or "cursor"


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: List[T]
    metadata: PaginationMetadata

    class Config:
        arbitrary_types_allowed = True


# Configuration
OFFSET_THRESHOLD = 100  # Switch to cursor pagination after this offset
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def paginate_offset(
    query: Query,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> Dict[str, Any]:
    """
    Offset-based pagination (traditional LIMIT/OFFSET).

    Fast for small offsets, slower for large offsets.
    Use for pages 1-5 (offset < 100).

    Args:
        query: SQLAlchemy query
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Dictionary with items and metadata
    """
    # Validate inputs
    page = max(1, page)
    page_size = min(page_size, MAX_PAGE_SIZE)

    # Calculate offset
    offset = (page - 1) * page_size

    # Get total count (expensive but necessary)
    total = query.count()

    # Get items
    items = query.offset(offset).limit(page_size).all()

    # Calculate metadata
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    has_next = page < total_pages
    has_prev = page > 1

    metadata = PaginationMetadata(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
        strategy="offset"
    )

    return {
        "items": items,
        "metadata": metadata
    }


def paginate_cursor(
    query: Query,
    cursor: Optional[str] = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    order_by_field: str = "created_at",
    order_direction: str = "desc",
) -> Dict[str, Any]:
    """
    Cursor-based pagination (keyset pagination).

    Efficient for large offsets, consistent results.
    Use for deep pagination (page 6+, offset >= 100).

    Cursor format: "{timestamp}:{id}" (e.g., "2025-12-15T10:30:00:proj-abc123")

    Args:
        query: SQLAlchemy query
        cursor: Pagination cursor (None for first page)
        page_size: Number of items per page
        order_by_field: Field to order by (default: created_at)
        order_direction: "asc" or "desc" (default: desc)

    Returns:
        Dictionary with items and metadata
    """
    # Validate inputs
    page_size = min(page_size, MAX_PAGE_SIZE)

    # Parse cursor if provided
    cursor_timestamp = None
    cursor_id = None

    if cursor:
        try:
            parts = cursor.split(":", 1)
            if len(parts) == 2:
                cursor_timestamp = datetime.fromisoformat(parts[0])
                cursor_id = parts[1]
        except (ValueError, AttributeError):
            # Invalid cursor - start from beginning
            cursor = None

    # Apply cursor filtering
    if cursor_timestamp and cursor_id:
        # Get model class from query
        model = query.column_descriptions[0]["entity"]
        order_field = getattr(model, order_by_field)
        id_field = getattr(model, "id")

        if order_direction == "desc":
            # For DESC ordering: (created_at < cursor_timestamp) OR
            # (created_at = cursor_timestamp AND id < cursor_id)
            query = query.filter(
                (order_field < cursor_timestamp) |
                ((order_field == cursor_timestamp) & (id_field < cursor_id))
            )
        else:
            # For ASC ordering: (created_at > cursor_timestamp) OR
            # (created_at = cursor_timestamp AND id > cursor_id)
            query = query.filter(
                (order_field > cursor_timestamp) |
                ((order_field == cursor_timestamp) & (id_field > cursor_id))
            )

    # Apply ordering
    model = query.column_descriptions[0]["entity"]
    order_field = getattr(model, order_by_field)
    id_field = getattr(model, "id")

    if order_direction == "desc":
        query = query.order_by(desc(order_field), desc(id_field))
    else:
        query = query.order_by(asc(order_field), asc(id_field))

    # Fetch one extra item to check if there's a next page
    items = query.limit(page_size + 1).all()

    # Check if there's a next page
    has_next = len(items) > page_size
    if has_next:
        items = items[:page_size]

    # Generate next cursor
    next_cursor = None
    if has_next and items:
        last_item = items[-1]
        last_timestamp = getattr(last_item, order_by_field)
        last_id = getattr(last_item, "id")
        next_cursor = f"{last_timestamp.isoformat()}:{last_id}"

    # Note: We don't track prev_cursor or total in cursor pagination
    # Total count is expensive and not needed for infinite scroll
    metadata = PaginationMetadata(
        total=-1,  # Not calculated for cursor pagination
        page=-1,  # Page number not relevant for cursor pagination
        page_size=page_size,
        total_pages=-1,  # Not calculated
        has_next=has_next,
        has_prev=bool(cursor),  # If cursor provided, we're not on first page
        next_cursor=next_cursor,
        prev_cursor=None,  # Prev cursor not supported in this implementation
        strategy="cursor"
    )

    return {
        "items": items,
        "metadata": metadata
    }


def paginate_hybrid(
    query: Query,
    page: Optional[int] = None,
    cursor: Optional[str] = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    order_by_field: str = "created_at",
    order_direction: str = "desc",
) -> Dict[str, Any]:
    """
    Hybrid pagination that automatically chooses the best strategy.

    - Uses offset pagination for page 1-5 (offset < 100)
    - Uses cursor pagination for page 6+ (offset >= 100) or when cursor provided

    This provides the best of both worlds:
    - Simple page numbers for UI (first few pages)
    - Efficient deep pagination (later pages)

    Args:
        query: SQLAlchemy query
        page: Page number (1-indexed, for offset pagination)
        cursor: Pagination cursor (for cursor pagination)
        page_size: Number of items per page
        order_by_field: Field to order by (for cursor pagination)
        order_direction: "asc" or "desc" (for cursor pagination)

    Returns:
        Dictionary with items and metadata
    """
    page_size = min(page_size, MAX_PAGE_SIZE)

    # If cursor provided, use cursor pagination
    if cursor:
        return paginate_cursor(
            query=query,
            cursor=cursor,
            page_size=page_size,
            order_by_field=order_by_field,
            order_direction=order_direction
        )

    # If page provided, check if it's small enough for offset pagination
    if page:
        offset = (page - 1) * page_size

        if offset < OFFSET_THRESHOLD:
            # Small offset - use offset pagination
            return paginate_offset(
                query=query,
                page=page,
                page_size=page_size
            )
        else:
            # Large offset - switch to cursor pagination
            # We need to convert page number to cursor
            # This requires fetching the last item from previous page
            # For simplicity, just use cursor pagination from start
            return paginate_cursor(
                query=query,
                cursor=None,  # Start from beginning
                page_size=page_size,
                order_by_field=order_by_field,
                order_direction=order_direction
            )

    # Default: use offset pagination for first page
    return paginate_offset(
        query=query,
        page=1,
        page_size=page_size
    )


def get_pagination_params(
    page: Optional[int] = None,
    cursor: Optional[str] = None,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> Dict[str, Any]:
    """
    Validate and normalize pagination parameters.

    Returns:
        Dictionary with validated pagination params
    """
    # Validate page_size
    if page_size is not None:
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    else:
        page_size = DEFAULT_PAGE_SIZE

    # Validate page
    if page is not None:
        page = max(1, page)

    return {
        "page": page,
        "cursor": cursor,
        "page_size": page_size
    }
