"""
Shared fixtures for unit tests that require database access.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models.user import User
from backend.models.client import Client
from backend.models.project import Project


@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory SQLite session for unit tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(
        id="unit-test-user-1",
        email="unit@example.com",
        hashed_password="hashed_pw",
        full_name="Unit Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def sample_client(db_session, sample_user):
    """Create a sample client for testing."""
    client = Client(
        id="unit-test-client-1",
        user_id=sample_user.id,
        name="Unit Test Client",
        email="client@example.com",
    )
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


@pytest.fixture(scope="function")
def sample_project(db_session, sample_user, sample_client):
    """Create a sample project for testing."""
    project = Project(
        id="unit-test-project-1",
        user_id=sample_user.id,
        client_id=sample_client.id,
        name="Unit Test Project",
        status="draft",
        num_posts=30,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project
