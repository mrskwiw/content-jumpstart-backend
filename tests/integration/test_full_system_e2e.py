"""
Comprehensive End-to-End System Integration Test
Tests all systems from user perspective with edge cases

These tests use FastAPI's TestClient for in-process testing with
isolated database fixtures. No running server required.
"""

import pytest
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestAuthenticationFlow:
    """Test authentication endpoints with edge cases"""

    def test_login_valid_credentials(self, client, test_user):
        """Test successful login"""
        response = client.post(
            "/api/auth/login", json={"email": test_user.email, "password": "testpass123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post(
            "/api/auth/login", json={"email": test_user.email, "password": "WrongPassword123!"}
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client, db_session):
        """Test login with non-existent user"""
        # db_session fixture ensures database is set up properly
        response = client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "SomePassword123!"},
        )
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        """Test login with missing fields"""
        response = client.post("/api/auth/login", json={"email": "test@example.com"})
        assert response.status_code == 422  # Validation error

    def test_protected_endpoint_no_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/clients/")
        assert response.status_code == 401

    def test_protected_endpoint_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token"""
        response = client.get(
            "/api/clients/", headers={"Authorization": "Bearer invalid_token_12345"}
        )
        assert response.status_code == 401


class TestClientManagement:
    """Test client CRUD operations"""

    def test_create_client_complete_data(self, client, test_user_headers):
        """Test creating client with all fields"""
        client_data = {
            "name": "E2E Test Client Complete",
            "email": "e2e.complete@testclient.com",
            "business_description": "Test Company Inc in the Technology industry",
            "ideal_customer": "Technology companies looking for solutions",
            "main_problem_solved": "Full integration testing",
            "tone_preference": "professional",
        }
        response = client.post("/api/clients/", json=client_data, headers=test_user_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["companyName"] == client_data["name"]
        assert data["email"] == client_data["email"]
        assert "id" in data

    def test_create_client_minimal_data(self, client, test_user_headers):
        """Test creating client with only required fields"""
        client_data = {"name": "E2E Test Client Minimal", "email": "e2e.minimal@testclient.com"}
        response = client.post("/api/clients/", json=client_data, headers=test_user_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["companyName"] == client_data["name"]

    def test_create_client_duplicate_email(self, client, test_user_headers):
        """Test creating client with duplicate email"""
        client_data = {"name": "Duplicate Test", "email": "duplicate@testclient.com"}
        # First creation
        response1 = client.post("/api/clients/", json=client_data, headers=test_user_headers)
        assert response1.status_code == 201

        # Second creation with same email - system allows duplicates currently
        response2 = client.post("/api/clients/", json=client_data, headers=test_user_headers)
        assert response2.status_code in [201, 409]  # Either creates or conflicts

    def test_list_clients(self, client, test_user_headers, test_client):
        """Test listing all clients"""
        response = client.get("/api/clients/", headers=test_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Verify our test_client is in the list
        client_ids = [c["id"] for c in data]
        assert test_client.id in client_ids

    def test_get_client_by_id(self, client, test_user_headers, test_client):
        """Test retrieving specific client"""
        response = client.get(f"/api/clients/{test_client.id}", headers=test_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_client.id
        assert data["companyName"] == test_client.name

    def test_get_nonexistent_client(self, client, test_user_headers):
        """Test retrieving non-existent client"""
        response = client.get("/api/clients/client-nonexistent123", headers=test_user_headers)
        assert response.status_code == 404

    def test_update_client(self, client, test_user_headers, test_client):
        """Test updating client information"""
        update_data = {"name": "Updated Client Name", "tone_preference": "casual"}
        response = client.patch(
            f"/api/clients/{test_client.id}", json=update_data, headers=test_user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["companyName"] == update_data["name"]
        assert (
            data.get("tonePreference") == update_data["tone_preference"]
            or data.get("tone_preference") == update_data["tone_preference"]
        )


class TestProjectManagement:
    """Test project CRUD operations"""

    def test_create_project_complete(self, client, db_session, test_user_headers, test_client):
        """Test creating project with all fields"""
        project_data = {
            "name": "E2E Complete Project",
            "client_id": test_client.id,
            "target_platform": "linkedin",
            "num_posts": 30,
            "template_quantities": {"1": 10, "2": 10, "3": 10},
        }
        response = client.post("/api/projects/", json=project_data, headers=test_user_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == project_data["name"]
        assert data["clientId"] == test_client.id  # Backend returns camelCase
        assert data["targetPlatform"] == "linkedin"

    def test_create_project_minimal(self, client, db_session, test_user_headers, test_client):
        """Test creating project with minimal required fields"""
        project_data = {
            "name": "E2E Minimal Project",
            "client_id": test_client.id,
        }
        response = client.post("/api/projects/", json=project_data, headers=test_user_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == project_data["name"]
        assert "id" in data

    def test_list_projects(self, client, db_session, test_user_headers, test_project):
        """Test listing all projects"""
        response = client.get("/api/projects/", headers=test_user_headers)
        assert response.status_code == 200
        data = response.json()
        # Projects endpoint returns paginated response with items and metadata
        assert "items" in data
        assert "metadata" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) > 0
        # Verify our test_project is in the list
        project_ids = [p["id"] for p in data["items"]]
        assert test_project.id in project_ids

    def test_get_project_by_id(self, client, db_session, test_user_headers, test_project):
        """Test retrieving specific project"""
        response = client.get(f"/api/projects/{test_project.id}", headers=test_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_project.id
        assert data["name"] == test_project.name

    def test_get_nonexistent_project(self, client, db_session, test_user_headers):
        """Test retrieving non-existent project"""
        response = client.get("/api/projects/proj-nonexistent123", headers=test_user_headers)
        assert response.status_code == 404

    def test_update_project(self, client, db_session, test_user_headers, test_project):
        """Test updating project information"""
        update_data = {
            "name": "Updated Project Name",
            "status": "in_progress",
            "target_platform": "twitter",
        }
        response = client.patch(
            f"/api/projects/{test_project.id}", json=update_data, headers=test_user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["status"] == update_data["status"]
        assert data["targetPlatform"] == "twitter"


class TestAuthorizationAndSecurity:
    """Test authorization and security controls"""

    def test_user_cannot_access_other_user_client(self, client, db_session, enforce_ownership):
        """Test that users cannot access clients they don't own (TR-021)"""
        from backend.models import User, Client
        from backend.utils.auth import get_password_hash, create_access_token

        # Create two users
        user1 = User(
            id="user-auth-test1",
            email="user1@test.com",
            hashed_password=get_password_hash("password123"),
            full_name="User One",
            is_active=True,
        )
        user2 = User(
            id="user-auth-test2",
            email="user2@test.com",
            hashed_password=get_password_hash("password123"),
            full_name="User Two",
            is_active=True,
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        # Create client owned by user1
        test_client_obj = Client(
            id="client-auth-test1",
            user_id=user1.id,
            name="User 1 Client",
            business_description="Test client for user 1",
        )
        db_session.add(test_client_obj)
        db_session.commit()

        # Try to access user1's client as user2
        user2_token = create_access_token(data={"sub": user2.id})
        user2_headers = {"Authorization": f"Bearer {user2_token}"}

        response = client.get(f"/api/clients/{test_client_obj.id}", headers=user2_headers)
        # TR-021: Returns 403 Forbidden when accessing resource owned by another user
        assert response.status_code == 403

    def test_user_cannot_update_other_user_client(self, client, db_session, enforce_ownership):
        """Test that users cannot update clients they don't own (TR-021)"""
        from backend.models import User, Client
        from backend.utils.auth import get_password_hash, create_access_token

        # Create two users
        user1 = User(
            id="user-auth-test3",
            email="user3@test.com",
            hashed_password=get_password_hash("password123"),
            full_name="User Three",
            is_active=True,
        )
        user2 = User(
            id="user-auth-test4",
            email="user4@test.com",
            hashed_password=get_password_hash("password123"),
            full_name="User Four",
            is_active=True,
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        # Create client owned by user1
        test_client_obj = Client(
            id="client-auth-test2",
            user_id=user1.id,
            name="User 3 Client",
            business_description="Test client for user 3",
        )
        db_session.add(test_client_obj)
        db_session.commit()

        # Try to update user1's client as user2
        user2_token = create_access_token(data={"sub": user2.id})
        user2_headers = {"Authorization": f"Bearer {user2_token}"}

        update_data = {"name": "Hacked Name"}
        response = client.patch(
            f"/api/clients/{test_client_obj.id}", json=update_data, headers=user2_headers
        )
        # TR-021: Returns 403 Forbidden when trying to update resource owned by another user
        assert response.status_code == 403

    def test_mass_assignment_protection(self, client, test_user_headers):
        """Test that protected fields cannot be set via API (TR-022)"""
        client_data = {
            "name": "Test Client",
            "email": "test@example.com",
            "user_id": "user-hacker123",  # Trying to set protected field
            "id": "client-hacker456",  # Trying to set protected field
        }
        response = client.post("/api/clients/", json=client_data, headers=test_user_headers)
        # Should reject with 422 due to extra="forbid" in schema
        assert response.status_code == 422

    def test_sql_injection_prevention(self, client, test_user_headers):
        """Test that SQL injection attempts are handled safely"""
        # Try SQL injection in client name
        client_data = {
            "name": "Test'; DROP TABLE clients; --",
            "email": "test@example.com",
        }
        response = client.post("/api/clients/", json=client_data, headers=test_user_headers)
        assert response.status_code == 201  # Should create normally, treating it as text

        # Verify the client was created with the literal string (not executed as SQL)
        data = response.json()
        assert data["companyName"] == client_data["name"]
