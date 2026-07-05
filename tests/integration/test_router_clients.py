"""
Integration tests for clients router.

Tests all client endpoints including:
- List clients (GET /api/clients/)
- Get client (GET /api/clients/{client_id})
- Create client (POST /api/clients/)
- Update client (PATCH /api/clients/{client_id})
- Export client profile (GET /api/clients/{client_id}/export-profile)
- Authorization checks (TR-021)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User, Client
from backend.utils.auth import get_password_hash
from tests.fixtures.model_factories import create_test_client


@pytest.fixture
def client(db_session):
    """Create test client with test database"""
    # db_session fixture sets up the database and dependency override
    # before TestClient is created
    """Create test client"""
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
def auth_headers_user_a(test_user_a, client, db_session):
    """Get auth headers for user A"""
    # Ensure user is committed
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": "usera@example.com", "password": "testpass123"},  # pragma: allowlist secret
    )

    # Debug: print response if login fails
    if response.status_code != 200:
        print(f"[DEBUG] Login failed: status={response.status_code}, body={response.json()}")

    data = response.json()
    if "access_token" not in data:
        raise ValueError(f"Login failed: {data}")

    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.fixture
def auth_headers_user_b(test_user_b, client, db_session):
    """Get auth headers for user B"""
    # Ensure user is committed
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": "userb@example.com", "password": "testpass123"},  # pragma: allowlist secret
    )

    # Debug: print response if login fails
    if response.status_code != 200:
        print(f"[DEBUG] Login failed: status={response.status_code}, body={response.json()}")

    data = response.json()
    if "access_token" not in data:
        raise ValueError(f"Login failed: {data}")

    return {"Authorization": f"Bearer {data['access_token']}"}


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
def client_for_user_b(db_session: Session, test_user_b):
    """Create a client owned by user B"""
    client_data = create_test_client(
        name="User B Client",
        user_id=test_user_b.id,
        email="clientb@example.com",
    )
    db_client = Client(**client_data)
    db_session.add(db_client)
    db_session.commit()
    db_session.refresh(db_client)
    return db_client


class TestListClients:
    """Test GET /api/clients/"""

    def test_list_clients_authenticated(self, client, auth_headers_user_a, client_for_user_a):
        """Test listing clients with authentication"""
        response = client.get("/api/clients/", headers=auth_headers_user_a)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "items" in data
        # Should see own client
        if isinstance(data, list):
            assert len(data) >= 1
            assert any(c["id"] == client_for_user_a.id for c in data)
        else:
            assert len(data["items"]) >= 1
            assert any(c["id"] == client_for_user_a.id for c in data["items"])

    def test_list_clients_unauthenticated(self, client):
        """Test listing clients without authentication"""
        response = client.get("/api/clients/")
        assert response.status_code == 401

    def test_list_clients_filters_by_user(
        self,
        client,
        auth_headers_user_a,
        auth_headers_user_b,
        client_for_user_a,
        client_for_user_b,
        enforce_ownership,
    ):
        """Test TR-021: Users only see their own clients"""
        # User A should see only their client
        response = client.get("/api/clients/", headers=auth_headers_user_a)
        data = response.json()
        items = data if isinstance(data, list) else data["items"]

        assert len(items) >= 1
        assert all(c["id"] != client_for_user_b.id for c in items)
        assert any(c["id"] == client_for_user_a.id for c in items)

        # User B should see only their client
        response = client.get("/api/clients/", headers=auth_headers_user_b)
        data = response.json()
        items = data if isinstance(data, list) else data["items"]

        assert len(items) >= 1
        assert all(c["id"] != client_for_user_a.id for c in items)
        assert any(c["id"] == client_for_user_b.id for c in items)

    def test_list_clients_pagination(self, client, auth_headers_user_a):
        """Test pagination parameters"""
        response = client.get("/api/clients/?page=1&per_page=10", headers=auth_headers_user_a)
        assert response.status_code == 200


class TestGetClient:
    """Test GET /api/clients/{client_id}"""

    def test_get_client_success(self, client, auth_headers_user_a, client_for_user_a):
        """Test getting client by ID"""
        response = client.get(f"/api/clients/{client_for_user_a.id}", headers=auth_headers_user_a)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == client_for_user_a.id
        assert data["companyName"] == client_for_user_a.name
        # API returns camelCase for frontend
        assert "businessDescription" in data or "business_description" in data
        assert "idealCustomer" in data or "ideal_customer" in data

    def test_get_client_unauthorized_user(
        self, client, auth_headers_user_b, client_for_user_a, enforce_ownership
    ):
        """Test TR-021: User B cannot access User A's client"""
        response = client.get(f"/api/clients/{client_for_user_a.id}", headers=auth_headers_user_b)
        assert response.status_code == 403

    def test_get_client_not_found(self, client, auth_headers_user_a):
        """Test getting non-existent client"""
        response = client.get("/api/clients/nonexistent-id", headers=auth_headers_user_a)
        assert response.status_code == 404

    def test_get_client_unauthenticated(self, client, client_for_user_a):
        """Test getting client without authentication"""
        response = client.get(f"/api/clients/{client_for_user_a.id}")
        assert response.status_code == 401


class TestCreateClient:
    """Test POST /api/clients/"""

    def test_create_client_success(self, client, auth_headers_user_a):
        """Test creating new client"""
        response = client.post(
            "/api/clients/",
            headers=auth_headers_user_a,
            json={
                "name": "New Client Corp",
                "email": "contact@newclient.com",
                "business_description": "We provide innovative solutions",
                "ideal_customer": "Small businesses",
                "main_problem_solved": "Inefficient workflows",
                "tone_preference": "professional",
                "platforms": ["linkedin", "twitter"],
                "customer_pain_points": ["Manual processes", "Poor collaboration"],
                "customer_questions": ["How to automate?", "What metrics to track?"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["companyName"] == "New Client Corp"
        assert data["email"] == "contact@newclient.com"
        assert "id" in data
        # API returns camelCase for frontend compatibility
        assert "createdAt" in data or "created_at" in data

    def test_create_client_minimal_fields(self, client, auth_headers_user_a):
        """Test creating client with minimal required fields"""
        response = client.post(
            "/api/clients/",
            headers=auth_headers_user_a,
            json={"name": "Minimal Client"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["companyName"] == "Minimal Client"

    def test_create_client_missing_required_field(self, client, auth_headers_user_a):
        """Test creating client without required name field"""
        response = client.post(
            "/api/clients/",
            headers=auth_headers_user_a,
            json={"email": "test@example.com"},
        )

        assert response.status_code == 422

    def test_create_client_invalid_email(self, client, auth_headers_user_a):
        """Test creating client with invalid email format"""
        response = client.post(
            "/api/clients/",
            headers=auth_headers_user_a,
            json={"name": "Test Client", "email": "not-an-email"},
        )

        assert response.status_code == 422

    def test_create_client_unauthenticated(self, client):
        """Test creating client without authentication"""
        response = client.post(
            "/api/clients/",
            json={"name": "Test Client"},
        )

        assert response.status_code == 401

    def test_create_client_assigns_to_current_user(
        self, client, auth_headers_user_a, test_user_a, db_session
    ):
        """Test TR-021: Created client is assigned to current user"""
        response = client.post(
            "/api/clients/",
            headers=auth_headers_user_a,
            json={"name": "Ownership Test Client"},
        )

        assert response.status_code == 201
        client_id = response.json()["id"]

        # Verify in database that client belongs to user A
        db_client = db_session.query(Client).filter(Client.id == client_id).first()
        assert db_client is not None
        assert db_client.user_id == test_user_a.id


class TestUpdateClient:
    """Test PATCH /api/clients/{client_id}"""

    def test_update_client_success(self, client, auth_headers_user_a, client_for_user_a):
        """Test updating client"""
        response = client.patch(
            f"/api/clients/{client_for_user_a.id}",
            headers=auth_headers_user_a,
            json={
                "name": "Updated Client Name",
                "tone_preference": "casual",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["companyName"] == "Updated Client Name"
        # API returns camelCase for frontend compatibility
        assert data.get("tonePreference") == "casual" or data.get("tone_preference") == "casual"

    def test_update_client_partial_update(self, client, auth_headers_user_a, client_for_user_a):
        """Test partial update (only some fields)"""
        original_name = client_for_user_a.name

        response = client.patch(
            f"/api/clients/{client_for_user_a.id}",
            headers=auth_headers_user_a,
            json={"tone_preference": "friendly"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["companyName"] == original_name  # Name unchanged
        # API returns camelCase for frontend compatibility
        assert data.get("tonePreference") == "friendly" or data.get("tone_preference") == "friendly"

    def test_update_client_unauthorized(
        self, client, auth_headers_user_b, client_for_user_a, enforce_ownership
    ):
        """Test TR-021: User B cannot update User A's client"""
        response = client.patch(
            f"/api/clients/{client_for_user_a.id}",
            headers=auth_headers_user_b,
            json={"name": "Hacked Name"},
        )

        assert response.status_code == 403

    def test_update_client_not_found(self, client, auth_headers_user_a):
        """Test updating non-existent client"""
        response = client.patch(
            "/api/clients/nonexistent-id",
            headers=auth_headers_user_a,
            json={"name": "New Name"},
        )

        assert response.status_code == 404

    def test_update_client_invalid_data(self, client, auth_headers_user_a, client_for_user_a):
        """Test updating with invalid data"""
        response = client.patch(
            f"/api/clients/{client_for_user_a.id}",
            headers=auth_headers_user_a,
            json={"email": "invalid-email"},
        )

        assert response.status_code == 422

    def test_key_phrases_round_trip(self, client, auth_headers_user_a, client_for_user_a):
        """Bug #107: key_phrases must persist through create → read cycle."""
        phrases = ["AI-powered reporting", "zero manual effort", "ops efficiency"]
        response = client.patch(
            f"/api/clients/{client_for_user_a.id}",
            headers=auth_headers_user_a,
            json={"key_phrases": phrases},
        )

        assert response.status_code == 200
        data = response.json()
        returned = data.get("keyPhrases") or data.get("key_phrases")
        assert returned == phrases, f"key_phrases not persisted: got {returned}"

    def test_key_phrases_present_in_get_response(
        self, client, auth_headers_user_a, client_for_user_a
    ):
        """Bug #107: key_phrases must appear in the GET /api/clients/{id} response."""
        phrases = ["instant dashboards", "no-code automation"]
        client.patch(
            f"/api/clients/{client_for_user_a.id}",
            headers=auth_headers_user_a,
            json={"key_phrases": phrases},
        )

        get_response = client.get(
            f"/api/clients/{client_for_user_a.id}",
            headers=auth_headers_user_a,
        )
        assert get_response.status_code == 200
        data = get_response.json()
        returned = data.get("keyPhrases") or data.get("key_phrases")
        assert returned == phrases, f"key_phrases missing from GET response: got {returned}"


class TestExportClientProfile:
    """Test GET /api/clients/{client_id}/export-profile"""

    def test_export_profile_success(self, client, auth_headers_user_a, client_for_user_a):
        """Test exporting client profile as markdown"""
        response = client.get(
            f"/api/clients/{client_for_user_a.id}/export-profile",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/markdown; charset=utf-8"
        assert "attachment" in response.headers.get("content-disposition", "")

        # Check content includes client info
        content = response.text
        assert client_for_user_a.name in content
        assert "Client Profile" in content

    def test_export_profile_unauthorized(
        self, client, auth_headers_user_b, client_for_user_a, enforce_ownership
    ):
        """Test TR-021: User B cannot export User A's client profile"""
        response = client.get(
            f"/api/clients/{client_for_user_a.id}/export-profile",
            headers=auth_headers_user_b,
        )

        assert response.status_code == 403

    def test_export_profile_not_found(self, client, auth_headers_user_a):
        """Test exporting non-existent client"""
        response = client.get(
            "/api/clients/nonexistent-id/export-profile",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 404


class TestClientDataValidation:
    """Test data validation for client fields"""

    def test_platforms_array_validation(self, client, auth_headers_user_a):
        """Test platforms field accepts array"""
        response = client.post(
            "/api/clients/",
            headers=auth_headers_user_a,
            json={"name": "Test Client", "platforms": ["linkedin", "twitter", "facebook"]},
        )

        assert response.status_code == 201
        assert response.json()["platforms"] == ["linkedin", "twitter", "facebook"]

    def test_customer_pain_points_array(self, client, auth_headers_user_a):
        """Test customer_pain_points accepts array of strings"""
        pain_points = ["Issue 1", "Issue 2", "Issue 3"]
        response = client.post(
            "/api/clients/",
            headers=auth_headers_user_a,
            json={"name": "Test Client", "customer_pain_points": pain_points},
        )

        assert response.status_code == 201
        # API returns camelCase for frontend compatibility
        data = response.json()
        assert (
            data.get("customerPainPoints") == pain_points
            or data.get("customer_pain_points") == pain_points
        )

    def test_customer_questions_array(self, client, auth_headers_user_a):
        """Test customer_questions accepts array of strings"""
        questions = ["Question 1?", "Question 2?"]
        response = client.post(
            "/api/clients/",
            headers=auth_headers_user_a,
            json={"name": "Test Client", "customer_questions": questions},
        )

        assert response.status_code == 201
        # API returns camelCase for frontend compatibility
        data = response.json()
        assert (
            data.get("customerQuestions") == questions
            or data.get("customer_questions") == questions
        )
