"""
Configuration for integration tests.

Sets up Python path to allow backend imports to work correctly.
"""

import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to Python path so relative imports work
backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from backend.database import Base  # noqa: E402


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    # Use in-memory SQLite for fast tests
    # check_same_thread=False allows sharing across threads (needed for TestClient)
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=None,  # Disable pooling for in-memory database
    )
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(engine)
