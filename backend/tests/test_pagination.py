"""
Unit tests for pagination utility (Week 3).

Tests cover:
- Offset pagination
- Cursor pagination
- Hybrid pagination strategy
- Parameter validation
- Metadata generation
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from utils.pagination import (
    paginate_offset,
    paginate_cursor,
    paginate_hybrid,
    get_pagination_params,
    PaginationMetadata,
    PaginatedResponse,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    OFFSET_THRESHOLD,
)


class MockModel:
    """Mock SQLAlchemy model for testing"""
    def __init__(self, id: str, created_at: datetime):
        self.id = id
        self.created_at = created_at


@pytest.fixture
def mock_query():
    """Create mock SQLAlchemy query"""
    query = MagicMock()
    query.column_descriptions = [{"entity": MockModel}]
    return query


@pytest.fixture
def mock_items():
    """Create mock items for pagination"""
    base_time = datetime(2025, 12, 15, 10, 0, 0)
    items = []
    for i in range(50):
        item = MockModel(
            id=f"item-{i:03d}",
            created_at=datetime(2025, 12, 15, 10, 0, i)
        )
        items.append(item)
    return items


class TestOffsetPagination:
    """Test offset-based pagination"""

    def test_offset_pagination_first_page(self, mock_query, mock_items):
        """Test first page of offset pagination"""
        mock_query.count.return_value = 50
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_items[:20]

        result = paginate_offset(mock_query, page=1, page_size=20)

        assert len(result["items"]) == 20
        assert result["metadata"].page == 1
        assert result["metadata"].page_size == 20
        assert result["metadata"].total == 50
        assert result["metadata"].total_pages == 3
        assert result["metadata"].has_next is True
        assert result["metadata"].has_prev is False
        assert result["metadata"].strategy == "offset"

    def test_offset_pagination_middle_page(self, mock_query, mock_items):
        """Test middle page of offset pagination"""
        mock_query.count.return_value = 50
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_items[20:40]

        result = paginate_offset(mock_query, page=2, page_size=20)

        assert len(result["items"]) == 20
        assert result["metadata"].page == 2
        assert result["metadata"].has_next is True
        assert result["metadata"].has_prev is True

        # Verify offset was called correctly
        mock_query.offset.assert_called_once_with(20)

    def test_offset_pagination_last_page(self, mock_query, mock_items):
        """Test last page of offset pagination"""
        mock_query.count.return_value = 50
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_items[40:50]

        result = paginate_offset(mock_query, page=3, page_size=20)

        assert len(result["items"]) == 10
        assert result["metadata"].page == 3
        assert result["metadata"].has_next is False
        assert result["metadata"].has_prev is True

    def test_offset_pagination_empty_results(self, mock_query):
        """Test offset pagination with no results"""
        mock_query.count.return_value = 0
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        result = paginate_offset(mock_query, page=1, page_size=20)

        assert len(result["items"]) == 0
        assert result["metadata"].total == 0
        assert result["metadata"].total_pages == 0
        assert result["metadata"].has_next is False
        assert result["metadata"].has_prev is False

    def test_offset_pagination_validates_page(self, mock_query, mock_items):
        """Test that page number is validated to minimum 1"""
        mock_query.count.return_value = 50
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_items[:20]

        # Page 0 should be treated as page 1
        result = paginate_offset(mock_query, page=0, page_size=20)

        assert result["metadata"].page == 1
        mock_query.offset.assert_called_once_with(0)

    def test_offset_pagination_validates_page_size(self, mock_query, mock_items):
        """Test that page size is capped at MAX_PAGE_SIZE"""
        mock_query.count.return_value = 50
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_items[:MAX_PAGE_SIZE]

        # Request 500 items, should be capped at MAX_PAGE_SIZE
        result = paginate_offset(mock_query, page=1, page_size=500)

        assert result["metadata"].page_size == MAX_PAGE_SIZE
        mock_query.limit.assert_called_once_with(MAX_PAGE_SIZE)

    def test_offset_pagination_total_pages_calculation(self, mock_query):
        """Test total pages calculation edge cases"""
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query

        # Exactly divisible
        mock_query.count.return_value = 100
        mock_query.all.return_value = []
        result = paginate_offset(mock_query, page=1, page_size=20)
        assert result["metadata"].total_pages == 5

        # Not evenly divisible
        mock_query.count.return_value = 95
        result = paginate_offset(mock_query, page=1, page_size=20)
        assert result["metadata"].total_pages == 5


class TestCursorPagination:
    """Test cursor-based pagination"""

    def test_cursor_pagination_first_page(self, mock_query, mock_items):
        """Test first page with no cursor"""
        # Return 21 items (20 + 1 to check has_next)
        mock_query.limit.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_items[:21]

        result = paginate_cursor(
            mock_query,
            cursor=None,
            page_size=20,
            order_by_field="created_at",
            order_direction="desc"
        )

        assert len(result["items"]) == 20  # 21st item used for has_next
        assert result["metadata"].has_next is True
        assert result["metadata"].has_prev is False
        assert result["metadata"].strategy == "cursor"
        assert result["metadata"].next_cursor is not None

    def test_cursor_pagination_with_cursor(self, mock_query, mock_items):
        """Test pagination with cursor provided"""
        cursor = "2025-12-15T10:00:20:item-020"

        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_items[21:41]

        result = paginate_cursor(
            mock_query,
            cursor=cursor,
            page_size=20,
            order_by_field="created_at",
            order_direction="desc"
        )

        assert len(result["items"]) == 20
        assert result["metadata"].has_prev is True  # Cursor provided = not first page
        mock_query.filter.assert_called_once()

    def test_cursor_pagination_last_page(self, mock_query, mock_items):
        """Test last page (less than page_size items)"""
        mock_query.limit.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_items[40:50]  # Only 10 items

        result = paginate_cursor(
            mock_query,
            cursor=None,
            page_size=20,
            order_by_field="created_at",
            order_direction="desc"
        )

        assert len(result["items"]) == 10
        assert result["metadata"].has_next is False
        assert result["metadata"].next_cursor is None

    def test_cursor_pagination_cursor_encoding(self, mock_query, mock_items):
        """Test cursor encoding format"""
        mock_query.limit.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_items[:21]

        result = paginate_cursor(mock_query, cursor=None, page_size=20)

        # Cursor should be in format: "{timestamp}:{id}"
        cursor = result["metadata"].next_cursor
        assert cursor is not None
        assert ":" in cursor
        parts = cursor.split(":", 1)
        assert len(parts) == 2
        # First part should be ISO timestamp
        datetime.fromisoformat(parts[0])  # Should not raise

    def test_cursor_pagination_invalid_cursor(self, mock_query, mock_items):
        """Test handling of invalid cursor format"""
        invalid_cursor = "invalid-format"

        mock_query.limit.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_items[:21]

        # Should not raise, should treat as first page
        result = paginate_cursor(
            mock_query,
            cursor=invalid_cursor,
            page_size=20
        )

        assert len(result["items"]) == 20
        # Should not have called filter (invalid cursor ignored)
        mock_query.filter.assert_not_called()

    def test_cursor_pagination_asc_ordering(self, mock_query, mock_items):
        """Test cursor pagination with ascending order"""
        cursor = "2025-12-15T10:00:20:item-020"

        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_items[21:41]

        result = paginate_cursor(
            mock_query,
            cursor=cursor,
            page_size=20,
            order_by_field="created_at",
            order_direction="asc"
        )

        # Verify filter was called (ASC filtering logic)
        mock_query.filter.assert_called_once()

    def test_cursor_pagination_metadata_values(self, mock_query, mock_items):
        """Test that cursor pagination metadata uses sentinel values"""
        mock_query.limit.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_items[:20]

        result = paginate_cursor(mock_query, cursor=None, page_size=20)

        # Cursor pagination doesn't calculate total/page
        assert result["metadata"].total == -1
        assert result["metadata"].page == -1
        assert result["metadata"].total_pages == -1


class TestHybridPagination:
    """Test hybrid pagination strategy"""

    def test_hybrid_uses_offset_for_small_page(self, mock_query, mock_items):
        """Test hybrid uses offset for page 1-5"""
        mock_query.count.return_value = 200
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_items[:20]

        result = paginate_hybrid(mock_query, page=3, page_size=20)

        # Page 3, page_size 20 = offset 40 (< OFFSET_THRESHOLD)
        assert result["metadata"].strategy == "offset"
        assert result["metadata"].page == 3
        mock_query.offset.assert_called_once_with(40)

    def test_hybrid_uses_cursor_for_large_page(self, mock_query, mock_items):
        """Test hybrid switches to cursor for page 6+"""
        mock_query.limit.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_items[:21]

        # Page 10, page_size 20 = offset 180 (>= OFFSET_THRESHOLD)
        result = paginate_hybrid(
            mock_query,
            page=10,
            page_size=20,
            order_by_field="created_at",
            order_direction="desc"
        )

        assert result["metadata"].strategy == "cursor"
        # Should not have called offset/count
        mock_query.offset.assert_not_called()
        mock_query.count.assert_not_called()

    def test_hybrid_uses_cursor_when_cursor_provided(self, mock_query, mock_items):
        """Test hybrid uses cursor when cursor is provided"""
        cursor = "2025-12-15T10:00:20:item-020"

        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_items[21:41]

        result = paginate_hybrid(
            mock_query,
            cursor=cursor,
            page_size=20
        )

        assert result["metadata"].strategy == "cursor"
        mock_query.filter.assert_called_once()

    def test_hybrid_defaults_to_offset_page_1(self, mock_query, mock_items):
        """Test hybrid defaults to offset page 1 when no params"""
        mock_query.count.return_value = 50
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_items[:20]

        result = paginate_hybrid(mock_query, page_size=20)

        assert result["metadata"].strategy == "offset"
        assert result["metadata"].page == 1
        mock_query.offset.assert_called_once_with(0)

    def test_hybrid_respects_max_page_size(self, mock_query, mock_items):
        """Test hybrid pagination enforces MAX_PAGE_SIZE"""
        mock_query.count.return_value = 500
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        result = paginate_hybrid(mock_query, page=1, page_size=500)

        assert result["metadata"].page_size == MAX_PAGE_SIZE


class TestPaginationParams:
    """Test pagination parameter validation"""

    def test_get_pagination_params_defaults(self):
        """Test default pagination parameters"""
        params = get_pagination_params()

        assert params["page"] is None
        assert params["cursor"] is None
        assert params["page_size"] == DEFAULT_PAGE_SIZE

    def test_get_pagination_params_validates_page_size(self):
        """Test page_size is capped at MAX_PAGE_SIZE"""
        params = get_pagination_params(page_size=500)

        assert params["page_size"] == MAX_PAGE_SIZE

    def test_get_pagination_params_validates_page_size_minimum(self):
        """Test page_size has minimum of 1"""
        params = get_pagination_params(page_size=0)

        assert params["page_size"] == 1

        params = get_pagination_params(page_size=-5)
        assert params["page_size"] == 1

    def test_get_pagination_params_validates_page_minimum(self):
        """Test page has minimum of 1"""
        params = get_pagination_params(page=0)

        assert params["page"] == 1

        params = get_pagination_params(page=-5)
        assert params["page"] == 1

    def test_get_pagination_params_preserves_cursor(self):
        """Test cursor is passed through unchanged"""
        cursor = "2025-12-15T10:00:00:item-123"
        params = get_pagination_params(cursor=cursor)

        assert params["cursor"] == cursor

    def test_get_pagination_params_with_all_values(self):
        """Test with all parameters provided"""
        params = get_pagination_params(
            page=5,
            cursor="test-cursor",
            page_size=50
        )

        assert params["page"] == 5
        assert params["cursor"] == "test-cursor"
        assert params["page_size"] == 50


class TestPaginationMetadataModel:
    """Test PaginationMetadata Pydantic model"""

    def test_pagination_metadata_creation(self):
        """Test creating PaginationMetadata instance"""
        metadata = PaginationMetadata(
            total=100,
            page=1,
            page_size=20,
            total_pages=5,
            has_next=True,
            has_prev=False,
            strategy="offset"
        )

        assert metadata.total == 100
        assert metadata.page == 1
        assert metadata.strategy == "offset"
        assert metadata.next_cursor is None
        assert metadata.prev_cursor is None

    def test_pagination_metadata_with_cursors(self):
        """Test metadata with cursor fields"""
        metadata = PaginationMetadata(
            total=-1,
            page=-1,
            page_size=20,
            total_pages=-1,
            has_next=True,
            has_prev=True,
            next_cursor="cursor-123",
            prev_cursor="cursor-abc",
            strategy="cursor"
        )

        assert metadata.next_cursor == "cursor-123"
        assert metadata.prev_cursor == "cursor-abc"


class TestPaginatedResponseModel:
    """Test PaginatedResponse generic model"""

    def test_paginated_response_creation(self):
        """Test creating PaginatedResponse instance"""
        items = [{"id": 1}, {"id": 2}]
        metadata = PaginationMetadata(
            total=2,
            page=1,
            page_size=20,
            total_pages=1,
            has_next=False,
            has_prev=False,
            strategy="offset"
        )

        response = PaginatedResponse(items=items, metadata=metadata)

        assert len(response.items) == 2
        assert response.metadata.total == 2
        assert response.metadata.strategy == "offset"

    def test_paginated_response_with_typed_items(self):
        """Test PaginatedResponse with specific type"""
        items = [MockModel("id1", datetime.now()), MockModel("id2", datetime.now())]
        metadata = PaginationMetadata(
            total=2,
            page=1,
            page_size=20,
            total_pages=1,
            has_next=False,
            has_prev=False,
            strategy="offset"
        )

        response = PaginatedResponse[MockModel](items=items, metadata=metadata)

        assert len(response.items) == 2
        assert isinstance(response.items[0], MockModel)
