"""
Configuration for integration tests.

Sets up Python path to allow backend imports to work correctly.
Provides database fixtures and mocks for integration testing.
"""

import os
import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set environment variables BEFORE importing backend modules
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-integration-tests")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-integration-tests-min-32-chars")
os.environ["ENV_FILE"] = ".env.test.nonexistent"

# Add backend directory to Python path so relative imports work
backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Add project root to path for src imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import database and models FIRST before app
from backend.database import Base, get_db  # noqa: E402
import backend.models  # noqa: E402, F401 - Import models before app to register them

from backend.main import app  # noqa: E402

# Import shared fixtures for integration tests
from tests.fixtures.anthropic_responses import (  # noqa: E402, F401
    mock_anthropic_client,
    mock_anthropic_client_with_custom_response,
    mock_anthropic_client_with_error,
)


@pytest.fixture(autouse=True)
def mock_background_tasks(monkeypatch):
    """
    Mock background tasks to not actually run during tests.

    Background tasks in routers create their own database sessions which
    bypass test database mocking. For integration tests, we test the
    endpoint behavior (returns 202 Accepted) without actually running
    the background generation.
    """
    from unittest.mock import Mock

    # Mock BackgroundTasks.add_task to do nothing
    mock_add_task = Mock(return_value=None)

    monkeypatch.setattr("fastapi.BackgroundTasks.add_task", mock_add_task)
    yield mock_add_task


@pytest.fixture(scope="function", autouse=True)
def reset_rate_limiting():
    """
    Reset rate limiter storage before each test.

    Rate limiters use in-memory storage (or Redis) that accumulates across tests,
    causing tests to fail when run together due to rate limit exhaustion.
    This fixture resets the storage before each test.
    """
    from backend.utils.http_rate_limiter import (
        limiter,
        strict_limiter,
        standard_limiter,
        lenient_limiter,
    )

    # Also reset the research rate limiter counters
    try:
        from backend.utils.research_rate_limiter import research_rate_limiter

        if research_rate_limiter.use_redis:
            # Flush all per-user research rate limit keys from Redis
            keys = research_rate_limiter.redis_client.keys("research_limit:user:*")
            if keys:
                research_rate_limiter.redis_client.delete(*keys)
        else:
            research_rate_limiter.memory_store.clear()
    except Exception:
        pass

    # Reset all rate limiters by clearing their internal storage
    # slowapi uses limits library which stores data in the storage backend
    for rate_limiter in [limiter, strict_limiter, standard_limiter, lenient_limiter]:
        try:
            # Access the storage backend and reset it
            if hasattr(rate_limiter, "_storage") and rate_limiter._storage:
                storage = rate_limiter._storage

                # Redis storage: flush database
                if hasattr(storage, "storage") and hasattr(storage.storage, "flushdb"):
                    try:
                        storage.storage.flushdb()
                    except Exception:
                        pass  # Redis not available, ignore

                # Memory storage: clear cache
                if hasattr(storage, "reset"):
                    storage.reset()
                elif hasattr(storage, "storage") and isinstance(storage.storage, dict):
                    storage.storage.clear()
                elif hasattr(storage, "_cache"):
                    storage._cache.clear()
        except Exception:
            pass  # Ignore errors if storage doesn't support reset

    yield


@pytest.fixture(scope="function", autouse=True)
def reset_research_cache():
    """
    Reset research cache before each test.

    Research cache persists across tests while database is reset,
    causing cache hits when tests expect fresh execution.
    This fixture ensures each test starts with a clean cache.
    """
    from backend.routers.research import research_cache

    # Clear cache before test
    if research_cache:
        research_cache.clear()

    yield

    # Clear cache after test
    if research_cache:
        research_cache.clear()
    # No cleanup needed - fixture runs before each test


@pytest.fixture(scope="function", autouse=True)
def reset_query_cache():
    """
    Clear the query_cache between tests.

    query_cache stores SQLAlchemy ORM instances in a global TTLCache.
    When a test session closes, cached instances become detached from their
    session.  The next test that hits the same cache key gets back a detached
    object and raises DetachedInstanceError.  Clearing the cache before each
    test ensures every request loads a fresh instance bound to the current
    test session.
    """
    from backend.utils.query_cache import _caches

    for cache in _caches.values():
        cache.clear()

    yield

    for cache in _caches.values():
        cache.clear()


@pytest.fixture(scope="function", autouse=False)
def db_session(monkeypatch):
    """
    Create a fresh database session for each test.

    This fixture creates an in-memory SQLite database, sets up all tables,
    and overrides the FastAPI dependency to use this test database.

    Each test gets a completely isolated database that is torn down after
    the test completes.
    """
    # Create a new engine for each test
    # CRITICAL: Use StaticPool for in-memory SQLite to ensure all connections
    # share the same database. Without this, each connection gets a separate
    # empty database and tests fail with "no such table" errors.
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Debug: Print registered tables
    print(f"\n[DEBUG] Registered tables in Base.metadata: {list(Base.metadata.tables.keys())}")
    print(f"[DEBUG] Test engine ID: {id(engine)}, URL: {engine.url}")

    # Create all tables
    Base.metadata.create_all(engine)

    # Debug: Verify tables were created
    from sqlalchemy import inspect

    inspector = inspect(engine)
    created_tables = inspector.get_table_names()
    print(f"[DEBUG] Created tables in database: {created_tables}")

    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create the session
    session = SessionLocal()

    # Override the get_db dependency
    def override_get_db():
        print(
            f"[DEBUG] override_get_db called, yielding session {id(session)}, engine {id(session.bind)}"
        )
        # Verify this session can access tables
        from sqlalchemy import inspect

        inspector = inspect(session.bind)
        tables_in_session = inspector.get_table_names()
        print(f"[DEBUG] Tables visible in override session: {tables_in_session}")
        try:
            yield session
        finally:
            pass  # Session will be closed in fixture cleanup

    # Apply the override
    app.dependency_overrides[get_db] = override_get_db
    print("[DEBUG] Dependency override set for get_db")
    print(f"[DEBUG] App dependency overrides: {list(app.dependency_overrides.keys())}")

    # CRITICAL: Also monkeypatch SessionLocal for background tasks
    # Background tasks in generator.py and other routers create their own
    # database sessions using SessionLocal() directly, bypassing dependency injection.
    # We need to patch it to return our test session instead.
    from backend import database

    def mock_sessionlocal():
        """Return the test session for background tasks"""
        print(f"[DEBUG] SessionLocal() called, returning test session {id(session)}")
        return session

    # Patch the SessionLocal callable
    monkeypatch.setattr(database, "SessionLocal", mock_sessionlocal)
    print("[DEBUG] Monkeypatched SessionLocal for background tasks")

    # Provide the session to the test
    yield session

    # Cleanup after test
    try:
        session.rollback()  # Rollback any uncommitted transactions
    except Exception:
        pass

    try:
        session.close()
    except Exception:
        pass

    # Clear the override
    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]

    # Drop all tables
    try:
        Base.metadata.drop_all(engine)
    except Exception:
        pass

    # Dispose of the engine
    try:
        engine.dispose()
    except Exception:
        pass


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    from backend.models import User
    from backend.utils.auth import get_password_hash

    user = User(
        id="user-test123",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_client(db_session, test_user):
    """Create a test client."""
    from backend.models import Client

    client = Client(
        id="client-test123",  # FIXED: Must start with 'client-' per schema validation
        user_id=test_user.id,
        name="Test Client",
        business_description="A test client for integration testing with comprehensive business description that meets the 70 character minimum requirement for research tools",
        ideal_customer="Tech-savvy professionals",
        main_problem_solved="Testing challenges",
    )
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


@pytest.fixture
def test_project(db_session, test_user, test_client):
    """Create a test project."""
    from backend.models import Project

    project = Project(
        id="proj-test123",
        user_id=test_user.id,
        client_id=test_client.id,
        name="Test Project",
        templates=["1", "2", "3"],
        template_quantities={"1": 10, "2": 10, "3": 10},
        num_posts=30,
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def enforce_ownership(monkeypatch):
    """Enable per-user resource ownership enforcement for tests that verify IDOR protection.

    The global default (ENFORCE_RESOURCE_OWNERSHIP=False) uses org-wide access.
    Add this fixture to any test that checks cross-user access is denied.

    Patches the enforcement-check function directly (more reliable than settings attribute)
    since Pydantic v2 attribute restoration can interfere when run alongside autouse fixtures.
    """
    monkeypatch.setattr(
        "backend.middleware.authorization._ownership_enforcement_enabled",
        lambda: True,
    )


@pytest.fixture
def test_user_headers(test_user, client):
    """Get JWT auth headers for test user."""
    from backend.utils.auth import create_access_token

    access_token = create_access_token(data={"sub": test_user.id})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def client():
    """Create a TestClient for API tests."""
    from fastapi.testclient import TestClient

    return TestClient(app)
