"""
Integration tests for Privacy API endpoints - GDPR/CCPA compliance
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User, Client, Project
from backend.utils.auth import get_password_hash, create_access_token


@pytest.fixture
def auth_headers(db_session: Session):
    """Create test user and return auth headers."""
    user = User(
        id="user-privacy-test",
        email="privacy@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Privacy Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(data={"sub": user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def _privacy_test_user(db_session: Session):
    """Get or create test user for privacy tests."""
    user = db_session.query(User).filter(User.id == "user-privacy-test").first()
    if not user:
        user = User(
            id="user-privacy-test",
            email="privacy@example.com",
            hashed_password=get_password_hash("testpass123"),
            full_name="Privacy Test User",
            is_active=True,
            is_superuser=False,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


@pytest.fixture
def sample_client(db_session: Session, auth_headers):
    """Create a sample client for testing."""
    user = db_session.query(User).filter(User.id == "user-privacy-test").first()
    client_obj = Client(
        id="client-privacy-test",
        user_id=user.id,
        name="Privacy Test Client",
        email="client@privacytest.com",
        business_description="Test business for privacy testing",
        ideal_customer="Test customers",
    )
    db_session.add(client_obj)
    db_session.commit()
    db_session.refresh(client_obj)
    return client_obj


@pytest.fixture
def sample_project(db_session: Session, sample_client):
    """Create a sample project for testing."""
    user = db_session.query(User).filter(User.id == "user-privacy-test").first()
    project = Project(
        id="proj-privacy-test",
        user_id=user.id,
        client_id=sample_client.id,
        name="Privacy Test Project",
        templates=["1"],
        template_quantities={"1": 10},
        num_posts=10,
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


class TestPrivacyEndpoints:
    def test_delete_client_endpoint(self, client: TestClient, auth_headers, sample_client):
        """Test DELETE /api/privacy/clients/{id} soft deletes client"""
        response = client.delete(f"/api/privacy/clients/{sample_client.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["client_id"] == sample_client.id
        assert "deleted_at" in data

    def test_delete_client_with_cascade(
        self, client: TestClient, auth_headers, sample_client, sample_project
    ):
        """Test deletion cascades to related projects"""
        response = client.delete(
            f"/api/privacy/clients/{sample_client.id}?cascade=true", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_counts"]["projects"] >= 1

    def test_delete_nonexistent_client_returns_404(self, client: TestClient, auth_headers):
        """Test deleting nonexistent client returns 404"""
        response = client.delete("/api/privacy/clients/nonexistent-id", headers=auth_headers)

        assert response.status_code == 404

    def test_anonymize_client_endpoint(self, client: TestClient, auth_headers, sample_client):
        """Test POST /api/privacy/clients/{id}/anonymize replaces PII"""
        response = client.post(
            f"/api/privacy/clients/{sample_client.id}/anonymize", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "anonymized_at" in data

    def test_export_client_data_endpoint(self, client: TestClient, auth_headers, sample_client):
        """Test GET /api/privacy/clients/{id}/export returns all data"""
        response = client.get(
            f"/api/privacy/clients/{sample_client.id}/export", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "client" in data
        assert data["client"]["id"] == sample_client.id
        assert "export_metadata" in data

    def test_restore_client_endpoint(
        self, client: TestClient, auth_headers, sample_client, db_session
    ):
        """Test POST /api/privacy/clients/{id}/restore restores deleted client"""
        # First soft delete
        sample_client.soft_delete()
        db_session.commit()

        # Then restore
        response = client.post(
            f"/api/privacy/clients/{sample_client.id}/restore", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_endpoints_require_authentication(self, client: TestClient, sample_client):
        """Test privacy endpoints require authentication"""
        endpoints = [
            ("delete", f"/api/privacy/clients/{sample_client.id}"),
            ("post", f"/api/privacy/clients/{sample_client.id}/anonymize"),
            ("get", f"/api/privacy/clients/{sample_client.id}/export"),
            ("post", f"/api/privacy/clients/{sample_client.id}/restore"),
        ]

        for method, url in endpoints:
            response = getattr(client, method)(url)
            assert response.status_code == 401  # Unauthorized


class TestGDPRCompliance:
    def test_full_gdpr_workflow(self, client: TestClient, auth_headers, sample_client, db_session):
        """Test complete GDPR Article 17 workflow"""
        # 1. Export data (Article 15 - Right of Access)
        export_response = client.get(
            f"/api/privacy/clients/{sample_client.id}/export", headers=auth_headers
        )
        assert export_response.status_code == 200
        export_data = export_response.json()
        assert "client" in export_data

        # 2. Delete data (Article 17 - Right to Erasure)
        delete_response = client.delete(
            f"/api/privacy/clients/{sample_client.id}", headers=auth_headers
        )
        assert delete_response.status_code == 200

        # 3. Verify data is no longer accessible
        db_session.refresh(sample_client)
        assert sample_client.is_deleted == True

    def test_ccpa_right_to_deletion(self, client: TestClient, auth_headers, sample_client):
        """Test CCPA Section 1798.105 compliance"""
        response = client.delete(
            f"/api/privacy/clients/{sample_client.id}?cascade=true", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "recovery_period_days" in data
