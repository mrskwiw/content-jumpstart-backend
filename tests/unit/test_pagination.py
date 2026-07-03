"""Unit tests for backend.utils.pagination."""

import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from datetime import datetime

from backend.utils.pagination import (
    PaginationMetadata,
    paginate_offset,
    paginate_cursor,
    paginate_hybrid,
    get_pagination_params,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    OFFSET_THRESHOLD,
)


# Minimal SQLAlchemy model for testing pagination
_Base = declarative_base()


class Item(_Base):
    __tablename__ = "test_items"
    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)


@pytest.fixture(scope="module")
def db_with_items():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Insert 25 items with distinct timestamps
    for i in range(25):
        item = Item(
            id=f"item-{i:03d}",
            created_at=datetime(2025, 1, i + 1),
        )
        session.add(item)
    session.commit()
    yield session
    session.close()


class TestPaginationMetadata:
    def test_basic_construction(self):
        meta = PaginationMetadata(
            total=100,
            page=1,
            page_size=20,
            total_pages=5,
            has_next=True,
            has_prev=False,
            strategy="offset",
        )
        assert meta.total == 100
        assert meta.has_next is True
        assert meta.strategy == "offset"


class TestPaginateOffset:
    def test_first_page(self, db_with_items):
        query = db_with_items.query(Item)
        result = paginate_offset(query, page=1, page_size=10)
        assert len(result["items"]) == 10
        assert result["metadata"].page == 1
        assert result["metadata"].has_next is True
        assert result["metadata"].has_prev is False
        assert result["metadata"].strategy == "offset"

    def test_last_page(self, db_with_items):
        query = db_with_items.query(Item)
        result = paginate_offset(query, page=3, page_size=10)
        assert len(result["items"]) == 5  # 25 items, 3rd page of 10 = 5 items
        assert result["metadata"].has_next is False
        assert result["metadata"].has_prev is True

    def test_total_count(self, db_with_items):
        query = db_with_items.query(Item)
        result = paginate_offset(query, page=1, page_size=20)
        assert result["metadata"].total == 25

    def test_total_pages(self, db_with_items):
        query = db_with_items.query(Item)
        result = paginate_offset(query, page=1, page_size=10)
        assert result["metadata"].total_pages == 3

    def test_page_size_clamped_to_max(self, db_with_items):
        query = db_with_items.query(Item)
        result = paginate_offset(query, page=1, page_size=99999)
        assert result["metadata"].page_size == MAX_PAGE_SIZE

    def test_page_clamped_to_min_1(self, db_with_items):
        query = db_with_items.query(Item)
        result = paginate_offset(query, page=-5, page_size=10)
        assert result["metadata"].page == 1


class TestPaginateCursor:
    def test_first_page_no_cursor(self, db_with_items):
        query = db_with_items.query(Item)
        result = paginate_cursor(query, cursor=None, page_size=10)
        assert len(result["items"]) == 10
        assert result["metadata"].strategy == "cursor"
        assert result["metadata"].has_next is True
        assert result["metadata"].has_prev is False

    def test_has_next_cursor(self, db_with_items):
        query = db_with_items.query(Item)
        result = paginate_cursor(query, cursor=None, page_size=10)
        assert result["metadata"].next_cursor is not None

    def test_last_page_no_next_cursor(self, db_with_items):
        query = db_with_items.query(Item)
        result = paginate_cursor(query, cursor=None, page_size=100)
        assert result["metadata"].has_next is False
        assert result["metadata"].next_cursor is None

    def test_invalid_cursor_falls_back_to_start(self, db_with_items):
        query = db_with_items.query(Item)
        result = paginate_cursor(query, cursor="invalid-cursor", page_size=10)
        assert len(result["items"]) == 10  # Gets items from start

    def test_page_size_clamped(self, db_with_items):
        query = db_with_items.query(Item)
        result = paginate_cursor(query, page_size=99999)
        assert result["metadata"].page_size == MAX_PAGE_SIZE


class TestPaginateHybrid:
    def test_small_page_uses_offset(self, db_with_items):
        query = db_with_items.query(Item)
        result = paginate_hybrid(query, page=1, page_size=10)
        assert result["metadata"].strategy == "offset"

    def test_large_page_uses_cursor(self, db_with_items):
        query = db_with_items.query(Item)
        # offset >= OFFSET_THRESHOLD (100): page 11 * 10 = 110
        result = paginate_hybrid(query, page=11, page_size=10)
        assert result["metadata"].strategy == "cursor"

    def test_cursor_provided_uses_cursor(self, db_with_items):
        query = db_with_items.query(Item)
        first = paginate_cursor(query, page_size=5)
        cursor = first["metadata"].next_cursor
        result = paginate_hybrid(query, cursor=cursor, page_size=5)
        assert result["metadata"].strategy == "cursor"

    def test_default_first_page(self, db_with_items):
        query = db_with_items.query(Item)
        result = paginate_hybrid(query)
        assert result["metadata"].strategy == "offset"
        assert result["metadata"].page == 1


class TestGetPaginationParams:
    def test_default_values(self):
        params = get_pagination_params()
        assert params["page_size"] == DEFAULT_PAGE_SIZE
        assert params["page"] is None
        assert params["cursor"] is None

    def test_page_clamped_to_1(self):
        params = get_pagination_params(page=0)
        assert params["page"] == 1

    def test_page_size_clamped_to_max(self):
        params = get_pagination_params(page_size=99999)
        assert params["page_size"] == MAX_PAGE_SIZE

    def test_page_size_clamped_to_1(self):
        params = get_pagination_params(page_size=0)
        assert params["page_size"] == 1

    def test_cursor_passed_through(self):
        params = get_pagination_params(cursor="some-cursor")
        assert params["cursor"] == "some-cursor"
