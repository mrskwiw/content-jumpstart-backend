"""
Test Bug #31: Integration status endpoint correctly detects web search providers.

Verifies that the /api/settings/integrations/status endpoint correctly
identifies configured web search providers by checking the actual API key values
rather than non-existent "_configured" keys.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch

from backend.main import app
from backend.models import User
from backend.utils.auth import get_password_hash


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def test_user(db_session: Session):
    """Create test user"""
    user = User(
        id="user-integration-test",
        email="integration@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Integration Test User",
        is_active=True,
        is_superuser=False,
        credit_balance=1000,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user, client):
    """Get auth headers"""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "integration@example.com",
            "password": "testpass123",
        },  # pragma: allowlist secret
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestBug31IntegrationStatus:
    """Test that Bug #31 is fixed - integration status correctly detects providers"""

    @patch("backend.services.settings_service.get_web_search_config")
    def test_brave_api_key_detected_correctly(self, mock_get_config, client, auth_headers):
        """Test that Brave API key is detected when present"""
        # Mock config with Brave key present
        mock_get_config.return_value = {
            "provider": "brave",
            "brave_api_key": "BSA-test-key-123",  # Actual key name, not "_configured"
            "tavily_api_key": "",
            "serpapi_api_key": "",
        }

        response = client.get(
            "/api/settings/integrations/status",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should detect Brave as configured
        assert data["brave"] is True, "Brave should be detected when API key is present"
        assert data["web_search"] is True, "web_search should be True when Brave is configured"

        # Others should be False
        assert data["tavily"] is False
        assert data["serpapi"] is False

    @patch("backend.services.settings_service.get_web_search_config")
    def test_tavily_api_key_detected_correctly(self, mock_get_config, client, auth_headers):
        """Test that Tavily API key is detected when present"""
        # Mock config with Tavily key present
        mock_get_config.return_value = {
            "provider": "tavily",
            "brave_api_key": "",
            "tavily_api_key": "tvly-test-key-456",  # Actual key name
            "serpapi_api_key": "",
        }

        response = client.get(
            "/api/settings/integrations/status",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should detect Tavily as configured
        assert data["tavily"] is True, "Tavily should be detected when API key is present"
        assert data["web_search"] is True, "web_search should be True when Tavily is configured"

        # Others should be False
        assert data["brave"] is False
        assert data["serpapi"] is False

    @patch("backend.services.settings_service.get_web_search_config")
    def test_serpapi_key_detected_correctly(self, mock_get_config, client, auth_headers):
        """Test that SerpAPI key is detected when present"""
        # Mock config with SerpAPI key present
        mock_get_config.return_value = {
            "provider": "serpapi",
            "brave_api_key": "",
            "tavily_api_key": "",
            "serpapi_api_key": "serp-test-key-789",  # Actual key name
        }

        response = client.get(
            "/api/settings/integrations/status",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should detect SerpAPI as configured
        assert data["serpapi"] is True, "SerpAPI should be detected when API key is present"
        assert data["web_search"] is True, "web_search should be True when SerpAPI is configured"

        # Others should be False
        assert data["brave"] is False
        assert data["tavily"] is False

    @patch("backend.services.settings_service.get_web_search_config")
    def test_no_providers_configured(self, mock_get_config, client, auth_headers):
        """Test that all providers are False when no keys present"""
        # Mock config with no keys
        mock_get_config.return_value = {
            "provider": None,
            "brave_api_key": "",
            "tavily_api_key": "",
            "serpapi_api_key": "",
        }

        response = client.get(
            "/api/settings/integrations/status",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # All should be False
        assert data["brave"] is False
        assert data["tavily"] is False
        assert data["serpapi"] is False
        assert (
            data["web_search"] is False
        ), "web_search should be False when no providers configured"

    @patch("backend.services.settings_service.get_web_search_config")
    def test_multiple_providers_configured(self, mock_get_config, client, auth_headers):
        """Test that multiple providers can be detected simultaneously"""
        # Mock config with multiple keys
        mock_get_config.return_value = {
            "provider": "brave",
            "brave_api_key": "BSA-test-key-123",
            "tavily_api_key": "tvly-test-key-456",
            "serpapi_api_key": "serp-test-key-789",
        }

        response = client.get(
            "/api/settings/integrations/status",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # All should be True
        assert data["brave"] is True
        assert data["tavily"] is True
        assert data["serpapi"] is True
        assert (
            data["web_search"] is True
        ), "web_search should be True when any provider is configured"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
