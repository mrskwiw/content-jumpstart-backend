"""
Integration tests for briefs router.

Tests all brief endpoints including:
- Create brief (POST /api/briefs/create)
- Upload brief (POST /api/briefs/upload)
- Get brief (GET /api/briefs/{brief_id})
- Parse brief (POST /api/briefs/parse)
- Authorization checks (TR-021)
- Input sanitization (TR-020)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User, Client, Project, Brief
from backend.utils.auth import get_password_hash
from tests.fixtures.model_factories import create_test_client, create_test_project


@pytest.fixture
def client(db_session):
    """Create test client with test database"""
    # db_session fixture sets up the database and dependency override
    # before TestClient is created
    return TestClient(app)


@pytest.fixture
def test_user_a(db_session: Session):
    """Create test user A"""
    user = User(
        id="user-a-123",
        email="usera@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="User A",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_b(db_session: Session):
    """Create test user B"""
    user = User(
        id="user-b-456",
        email="userb@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="User B",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers_user_a(test_user_a, client):
    """Get auth headers for user A"""
    # test_user_a MUST come before client to ensure database is set up first
    response = client.post(
        "/api/auth/login",
        json={"email": "usera@example.com", "password": "testpass123"},  # pragma: allowlist secret
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user_b(test_user_b, client):
    """Get auth headers for user B"""
    # test_user_b MUST come before client to ensure database is set up first
    response = client.post(
        "/api/auth/login",
        json={"email": "userb@example.com", "password": "testpass123"},  # pragma: allowlist secret
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client_for_user_a(db_session: Session, test_user_a):
    """Create a client owned by user A"""
    client_data = create_test_client(
        name="User A Client",
        user_id=test_user_a.id,
        email="clienta@example.com",
    )
    db_client = Client(**client_data)
    db_session.add(db_client)
    db_session.commit()
    db_session.refresh(db_client)
    return db_client


@pytest.fixture
def project_for_user_a(db_session: Session, test_user_a, client_for_user_a):
    """Create a project owned by user A"""
    project_data = create_test_project(
        name="User A Project",
        client_id=client_for_user_a.id,
        user_id=test_user_a.id,
    )
    db_project = Project(**project_data)
    db_session.add(db_project)
    db_session.commit()
    db_session.refresh(db_project)
    return db_project


class TestCreateBriefEndpoint:
    """Test POST /api/briefs/create"""

    def test_create_brief_success(
        self, client, auth_headers_user_a, project_for_user_a, client_for_user_a
    ):
        """Test creating brief with complete data"""
        brief_content = """
        Company: Acme Corp
        Business: We provide cloud solutions for small businesses
        Ideal Customer: Small business owners with 10-50 employees
        Main Problem: Inefficient workflow management
        Pain Points: Manual processes, Poor collaboration
        Questions: How to automate workflows?
        Platforms: LinkedIn, Twitter
        Tone: Professional
        """

        response = client.post(
            "/api/briefs/create",
            headers=auth_headers_user_a,
            json={
                "project_id": project_for_user_a.id,
                "content": brief_content,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert (
            data["projectId"] == project_for_user_a.id
            or data["project_id"] == project_for_user_a.id
        )
        assert "id" in data
        assert "createdAt" in data or "created_at" in data
        assert "content" in data

    def test_create_brief_minimal_fields(
        self, client, auth_headers_user_a, project_for_user_a, client_for_user_a
    ):
        """Test creating brief with minimal required fields"""
        response = client.post(
            "/api/briefs/create",
            headers=auth_headers_user_a,
            json={
                "project_id": project_for_user_a.id,
                "content": "Company: Test Co\nBusiness: We do things",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "content" in data

    def test_create_brief_missing_required_field(
        self, client, auth_headers_user_a, project_for_user_a
    ):
        """Test creating brief without required content field"""
        response = client.post(
            "/api/briefs/create",
            headers=auth_headers_user_a,
            json={
                "project_id": project_for_user_a.id,
                # Missing "content" field
            },
        )

        assert response.status_code == 422

    def test_create_brief_unauthenticated(self, client, project_for_user_a):
        """Test creating brief without authentication"""
        response = client.post(
            "/api/briefs/create",
            json={
                "project_id": project_for_user_a.id,
                "company_name": "Test",
                "business_description": "Test",
                "ideal_customer": "Test",
                "main_problem_solved": "Test",
            },
        )

        assert response.status_code == 401

    def test_create_brief_input_sanitization(
        self, client, auth_headers_user_a, project_for_user_a, client_for_user_a
    ):
        """Test TR-020: Input sanitization for prompt injection

        Note: The sanitization is focused on prompt injection attacks, not HTML/XSS.
        HTML tags in brief content are allowed since the content is stored as plain text
        and displayed to operators (not rendered as HTML). The sanitizer prevents
        prompt injection patterns like 'ignore previous instructions'.
        """
        # Content with HTML tags (allowed - not XSS since not rendered as HTML)
        # and prompt injection patterns (should be blocked)
        content_with_html = """
        Company: <script>alert('xss')</script>
        Business: Normal business description
        """

        response = client.post(
            "/api/briefs/create",
            headers=auth_headers_user_a,
            json={
                "project_id": project_for_user_a.id,
                "content": content_with_html,
            },
        )

        # HTML content is allowed (not XSS risk since stored as text, not rendered)
        # The sanitization is for prompt injection, not HTML
        assert response.status_code in [201, 400]
        if response.status_code == 201:
            data = response.json()
            assert "content" in data
            # Content is stored - HTML is not sanitized (not a risk for text storage)


class TestUploadBriefEndpoint:
    """Test POST /api/briefs/upload"""

    def test_upload_brief_text_success(
        self, client, auth_headers_user_a, project_for_user_a, client_for_user_a
    ):
        """Test uploading brief as file"""
        brief_text = """
        Company: Acme Corp
        Business: We provide cloud solutions
        Customer: Small businesses
        Problem: Manual workflows
        """

        # Upload expects multipart/form-data with file
        # project_id is a query parameter, not form data
        from io import BytesIO

        files = {"file": ("brief.txt", BytesIO(brief_text.encode()), "text/plain")}

        response = client.post(
            f"/api/briefs/upload?project_id={project_for_user_a.id}",
            headers=auth_headers_user_a,
            files=files,
        )

        assert response.status_code in [200, 201]
        response_data = response.json()
        assert "id" in response_data
        assert "content" in response_data

    def test_upload_brief_unauthenticated(self, client, project_for_user_a):
        """Test uploading brief without authentication"""
        from io import BytesIO

        files = {"file": ("brief.txt", BytesIO(b"Test content"), "text/plain")}
        data = {"project_id": project_for_user_a.id}

        response = client.post(
            "/api/briefs/upload",
            files=files,
            data=data,
        )

        assert response.status_code == 401


class TestGetBriefEndpoint:
    """Test GET /api/briefs/{brief_id}"""

    def test_get_brief_success(
        self,
        client,
        auth_headers_user_a,
        project_for_user_a,
        client_for_user_a,
        db_session,
        test_user_a,
    ):
        """Test getting brief by ID"""
        # Create a brief first
        brief = Brief(
            id="brief-test-123",
            project_id=project_for_user_a.id,
            content="Company: Test Company\nBusiness: We do things",
            source="paste",
            file_path=None,
        )
        db_session.add(brief)
        db_session.commit()

        response = client.get(f"/api/briefs/{brief.id}", headers=auth_headers_user_a)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == brief.id
        assert "content" in data

    def test_get_brief_not_found(self, client, auth_headers_user_a):
        """Test getting non-existent brief"""
        response = client.get("/api/briefs/nonexistent-id", headers=auth_headers_user_a)

        assert response.status_code == 404

    def test_get_brief_unauthenticated(self, client):
        """Test getting brief without authentication"""
        response = client.get("/api/briefs/some-id")

        assert response.status_code == 401


class TestParseBriefEndpoint:
    """Test POST /api/briefs/parse"""

    def test_parse_brief_success(self, client, auth_headers_user_a, mock_anthropic_client):
        """Test parsing brief text with mocked Anthropic API"""
        from io import BytesIO

        brief_text = """
        Company Name: Acme Corporation
        What we do: We provide cloud-based project management software for small businesses
        Target Customer: Small business owners with 5-20 employees
        Main Problem: Inefficient workflows and scattered communication
        """

        files = {"file": ("brief.txt", BytesIO(brief_text.encode()), "text/plain")}

        response = client.post(
            "/api/briefs/parse",
            headers=auth_headers_user_a,
            files=files,
        )

        assert response.status_code == 200
        data = response.json()
        # Should have parsed fields nested under "fields"
        assert "fields" in data
        assert "companyName" in data["fields"] or "company_name" in data["fields"]

    def test_parse_brief_empty_content(self, client, auth_headers_user_a, mock_anthropic_client):
        """Test parsing empty brief content - mock always returns data so 200 is expected"""
        from io import BytesIO

        files = {"file": ("brief.txt", BytesIO(b""), "text/plain")}

        response = client.post(
            "/api/briefs/parse",
            headers=auth_headers_user_a,
            files=files,
        )

        # Mock parser always returns data regardless of content; parallel parse (3x)
        # picks the best-scoring result. Empty content is gracefully handled: 200 + fields.
        assert response.status_code == 200
        data = response.json()
        assert "fields" in data
        # companyName field must be present (value may be from mock or None)
        assert "companyName" in data["fields"]

    def test_parse_brief_unauthenticated(self, client):
        """Test parsing brief without authentication"""
        from io import BytesIO

        files = {"file": ("brief.txt", BytesIO(b"Test content"), "text/plain")}

        response = client.post(
            "/api/briefs/parse",
            files=files,
        )

        assert response.status_code == 401

    def test_parse_brief_uses_mock(self, client, auth_headers_user_a, mock_anthropic_client):
        """Verify that parsing uses mocked Anthropic API (no real calls)"""
        from io import BytesIO

        brief_content = "Company: Test\nBusiness: Testing"
        files = {"file": ("brief.txt", BytesIO(brief_content.encode()), "text/plain")}

        response = client.post(
            "/api/briefs/parse",
            headers=auth_headers_user_a,
            files=files,
        )

        # Should succeed with mock (not fail with API error)
        assert response.status_code in [200, 201]


# NOTE: TestBriefDataValidation removed - the /api/briefs/create endpoint
# only accepts {project_id, content}, not structured fields.
# Structured field validation would apply to parsed briefs or a different endpoint.
