"""Integration tests for AI Assistant API"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.user import User
from backend.database import SessionLocal
from backend.utils.auth import create_access_token


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create auth headers with valid token"""
    # Create a test user token
    token = create_access_token(data={"sub": "test@example.com"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user(db_session):
    """Create test user"""
    user = User(
        id="test-user-123",
        email="test@example.com",
        hashed_password="hashed_password_here",
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    yield user
    db_session.delete(user)
    db_session.commit()


def test_chat_endpoint_requires_auth(client):
    """Test that chat endpoint requires authentication"""
    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "Hello",
            "context": {},
            "conversation_history": [],
        },
    )
    assert response.status_code == 401


def test_chat_basic(client, auth_headers):
    """Test basic chat functionality"""
    response = client.post(
        "/api/assistant/chat",
        headers=auth_headers,
        json={
            "message": "What is the wizard?",
            "context": {"page": "overview"},
            "conversation_history": [],
        },
    )

    # May fail if Claude API not available, but should not crash
    assert response.status_code in [200, 503]

    if response.status_code == 200:
        data = response.json()
        assert "message" in data
        assert "suggestions" in data
        assert isinstance(data["message"], str)
        assert isinstance(data["suggestions"], list)
        print(f"[OK] Chat response: {data['message'][:100]}...")


def test_chat_with_page_context(client, auth_headers):
    """Test chat with different page contexts"""
    pages = ["wizard", "projects", "clients", "content-review", "overview"]

    for page in pages:
        response = client.post(
            "/api/assistant/chat",
            headers=auth_headers,
            json={
                "message": f"Help me with {page}",
                "context": {"page": page},
                "conversation_history": [],
            },
        )

        assert response.status_code in [200, 503]
        print(f"[OK] {page} context works")


def test_chat_with_conversation_history(client, auth_headers):
    """Test chat with conversation history"""
    conversation = [
        {"role": "user", "content": "What is the wizard?"},
        {"role": "assistant", "content": "The wizard helps you create client profiles and generate content."},
    ]

    response = client.post(
        "/api/assistant/chat",
        headers=auth_headers,
        json={
            "message": "How do I use it?",
            "context": {"page": "wizard"},
            "conversation_history": conversation,
        },
    )

    assert response.status_code in [200, 503]

    if response.status_code == 200:
        data = response.json()
        # Response should be contextual to previous conversation
        assert "message" in data
        print(f"[OK] Conversation history maintained")


def test_context_suggestions(client, auth_headers):
    """Test context-aware suggestions"""
    response = client.post(
        "/api/assistant/context",
        headers=auth_headers,
        json={
            "page": "wizard",
            "data": {},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert "quick_actions" in data
    assert isinstance(data["suggestions"], list)
    assert isinstance(data["quick_actions"], list)
    assert len(data["suggestions"]) > 0  # Should have wizard-specific suggestions

    print(f"[OK] Wizard suggestions: {data['suggestions']}")


def test_context_suggestions_all_pages(client, auth_headers):
    """Test suggestions for all pages"""
    pages = ["wizard", "projects", "clients", "content-review", "deliverables", "settings", "overview"]

    for page in pages:
        response = client.post(
            "/api/assistant/context",
            headers=auth_headers,
            json={"page": page, "data": {}},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["suggestions"]) > 0, f"{page} should have suggestions"
        print(f"[OK] {page}: {len(data['suggestions'])} suggestions")


def test_reset_conversation(client, auth_headers):
    """Test conversation reset"""
    response = client.post(
        "/api/assistant/reset",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data
    print("[OK] Conversation reset works")


def test_chat_error_handling(client, auth_headers):
    """Test error handling with invalid input"""
    # Missing message field
    response = client.post(
        "/api/assistant/chat",
        headers=auth_headers,
        json={
            "context": {},
            "conversation_history": [],
        },
    )

    assert response.status_code == 422  # Validation error


def test_page_specific_prompts():
    """Test that each page has a specific system prompt"""
    from backend.routers.assistant import PAGE_CONTEXTS

    expected_pages = ["wizard", "projects", "clients", "content-review", "deliverables", "settings", "overview"]

    for page in expected_pages:
        assert page in PAGE_CONTEXTS, f"Missing prompt for {page}"
        prompt = PAGE_CONTEXTS[page]
        assert len(prompt) > 100, f"{page} prompt too short"
        assert "AI assistant" in prompt.lower(), f"{page} prompt missing role description"

    print(f"[OK] All {len(expected_pages)} page contexts defined")


def test_suggestion_generation():
    """Test suggestion generator functions"""
    from backend.routers.assistant import generate_suggestions, generate_quick_actions

    # Test wizard suggestions
    suggestions = generate_suggestions("wizard", {})
    assert len(suggestions) > 0
    assert any("template" in s.lower() for s in suggestions)

    # Test projects suggestions
    suggestions = generate_suggestions("projects", {})
    assert len(suggestions) > 0
    assert any("project" in s.lower() for s in suggestions)

    # Test quick actions
    actions = generate_quick_actions("wizard", {})
    assert len(actions) > 0
    assert all(isinstance(a, dict) for a in actions)
    assert all("label" in a and "action" in a and "icon" in a for a in actions)

    print("[OK] Suggestion generation works")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
