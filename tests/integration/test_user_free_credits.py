"""
Test Task #50: New users should receive 1000 free welcome credits
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User
from backend.services import crud


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestFreeWelcomeCredits:
    """Test that new users receive 1000 free credits"""

    def test_new_user_receives_1000_credits_via_model_default(self, db_session: Session):
        """Test that User model defaults credit_balance to 1000"""
        # Create user directly via CRUD (bypasses API)
        user = crud.create_user(
            db=db_session,
            email="newuser@example.com",
            hashed_password="hashed_password",
            full_name="New User",
            is_active=True,
        )

        # Verify user received 1000 free credits
        assert (
            user.credit_balance == 1000
        ), f"New user should have 1000 free credits, got {user.credit_balance}"

    def test_new_user_registration_includes_free_credits(
        self, client, db_session: Session, monkeypatch
    ):
        """Test that user registration via API creates user with 1000 credits (production mode)"""
        from backend.config import settings

        # Force production-like behavior (no debug credits override)
        monkeypatch.setattr(settings, "DEBUG_MODE", False)

        # Register new user via API
        response = client.post(
            "/api/auth/register",
            json={
                "email": "apiuser@example.com",
                "password": "Tr0ub4dor&3!QwZ",  # pragma: allowlist secret
                "full_name": "API Test User",
            },
        )

        # Registration might return 201 or 200
        assert response.status_code in [200, 201], f"Registration failed: {response.json()}"

        # Verify user was created with 1000 credits (model default, no debug override)
        user = crud.get_user_by_email(db_session, "apiuser@example.com")
        assert user is not None, "User should exist in database"
        assert (
            user.credit_balance == 1000
        ), f"Registered user should have 1000 free credits, got {user.credit_balance}"

    def test_multiple_new_users_all_receive_credits(self, db_session: Session):
        """Test that multiple new users all receive 1000 credits"""
        users = []
        for i in range(5):
            user = crud.create_user(
                db=db_session,
                email=f"user{i}@example.com",
                hashed_password="hashed",
                full_name=f"User {i}",
            )
            users.append(user)

        # All users should have 1000 credits
        for user in users:
            assert (
                user.credit_balance == 1000
            ), f"User {user.email} should have 1000 credits, got {user.credit_balance}"

    def test_credit_balance_tracking_fields_initialized(self, db_session: Session):
        """Test that all credit tracking fields are properly initialized"""
        user = crud.create_user(
            db=db_session,
            email="tracking@example.com",
            hashed_password="hashed",
            full_name="Tracking User",
        )

        # Verify all credit fields are initialized correctly
        assert user.credit_balance == 1000, "Should start with 1000 free credits"
        assert user.total_credits_purchased == 0, "Should have purchased 0 credits initially"
        assert user.total_credits_used == 0, "Should have used 0 credits initially"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
