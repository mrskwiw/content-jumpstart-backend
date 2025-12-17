"""Pytest fixtures for Portal API tests."""

from typing import Generator

import pytest
from app.core.security import create_access_token, get_password_hash
from app.db.database import Base, get_db
from app.main import app
from app.models.brief import Brief
from app.models.deliverable import Deliverable
from app.models.file_upload import FileUpload
from app.models.project import Project
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Test database URL (in-memory SQLite)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine."""
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session) -> Generator:
    """Create a test client with database override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db_session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_user2(db_session) -> User:
    """Create a second test user for permission testing."""
    user = User(
        email="test2@example.com",
        password_hash=get_password_hash("testpassword123"),
        full_name="Test User 2",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_token(test_user) -> str:
    """Create an access token for test user."""
    return create_access_token(data={"sub": test_user.user_id})


@pytest.fixture(scope="function")
def auth_token2(test_user2) -> str:
    """Create an access token for second test user."""
    return create_access_token(data={"sub": test_user2.user_id})


@pytest.fixture(scope="function")
def auth_headers(auth_token) -> dict:
    """Create authorization headers with test token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="function")
def auth_headers2(auth_token2) -> dict:
    """Create authorization headers for second test user."""
    return {"Authorization": f"Bearer {auth_token2}"}


@pytest.fixture(scope="function")
def test_project(db_session, test_user) -> Project:
    """Create a test project."""
    project = Project(
        user_id=test_user.user_id,
        client_name="Test Client",
        package_tier="Professional",
        package_price=1800.00,
        posts_count=30,
        revision_limit=2,
        status="brief_submitted",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture(scope="function")
def test_brief(db_session, test_project) -> Brief:
    """Create a test brief."""
    brief = Brief(
        project_id=test_project.project_id,
        tone_descriptors='["professional", "friendly"]',
        voice_notes="Clear and concise",
        audience_type="B2B SaaS Founders",
        audience_title="CEO",
        audience_industry="Technology",
        pain_points='["time management", "content consistency"]',
        key_topics='["content strategy", "SEO", "social media"]',
        content_examples="https://example.com/blog",
        target_platforms='["LinkedIn", "Twitter"]',
        posting_frequency="3-4 times per week",
        conversion_goal="Lead generation",
        cta_preference="Soft ask",
        customer_stories='["Success story 1"]',
        personal_stories='["Personal story 1"]',
    )
    db_session.add(brief)
    db_session.commit()
    db_session.refresh(brief)
    return brief


@pytest.fixture(scope="function")
def test_file_upload(db_session, test_project) -> FileUpload:
    """Create a test file upload."""
    file_upload = FileUpload(
        project_id=test_project.project_id,
        file_type="voice_sample",
        original_filename="test_audio.mp3",
        stored_filename="abc123.mp3",
        file_path="voice_samples/abc123.mp3",
        file_size=1024000,
        mime_type="audio/mpeg",
    )
    db_session.add(file_upload)
    db_session.commit()
    db_session.refresh(file_upload)
    return file_upload


@pytest.fixture(scope="function")
def test_deliverable(db_session, test_project, tmp_path) -> Deliverable:
    """Create a test deliverable with actual file."""
    # Create a temporary test file
    test_file = tmp_path / "test_deliverable.txt"
    test_file.write_text("Test deliverable content")

    deliverable = Deliverable(
        project_id=test_project.project_id,
        deliverable_type="social_posts",
        file_path=str(test_file),
        file_format="txt",
        download_count=0,
    )
    db_session.add(deliverable)
    db_session.commit()
    db_session.refresh(deliverable)
    return deliverable


@pytest.fixture(scope="function")
def tmp_upload_dir(tmp_path):
    """Create a temporary upload directory."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    (upload_dir / "voice_samples").mkdir()
    (upload_dir / "brand_assets").mkdir()
    (upload_dir / "briefs").mkdir()
    return upload_dir
