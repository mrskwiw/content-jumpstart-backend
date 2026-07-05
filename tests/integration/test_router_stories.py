"""
Integration tests for stories router (Task #34).

Tests all /api/stories/* endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from backend.main import app
from backend.models import Client, Project
from backend.services.story_service import story_service

client = TestClient(app)


def create_test_post(db_session, project_id, **kwargs):
    """Helper to create a test post with run."""
    from backend.models import Post, Run
    import uuid

    run = Run(
        id=f"run-{uuid.uuid4().hex[:12]}",
        project_id=project_id,
        status="completed",
        is_batch=True,
    )
    db_session.add(run)
    db_session.commit()

    post = Post(
        id=f"post-{uuid.uuid4().hex[:12]}",
        project_id=project_id,
        run_id=run.id,
        content=kwargs.get("content", "Test content"),
        template_id=str(kwargs.get("template_id", 1)),
        target_platform=kwargs.get("platform", "linkedin"),
    )
    db_session.add(post)
    db_session.commit()
    return post


@pytest.fixture
def test_client_for_stories(db_session, test_user):
    """Create a test client for story tests."""
    test_client_obj = Client(
        id="client-stories-test",
        user_id=test_user.id,
        name="Stories Test Client",
        email="stories@example.com",
        business_description="A business for testing story functionality",
        ideal_customer="Test customers",
        main_problem_solved="Test problems",
    )
    db_session.add(test_client_obj)
    db_session.commit()
    db_session.refresh(test_client_obj)
    return test_client_obj


@pytest.fixture
def test_project_for_stories(db_session, test_user, test_client_for_stories):
    """Create a test project for story tests."""
    project = Project(
        id="proj-stories-test",
        user_id=test_user.id,
        client_id=test_client_for_stories.id,
        name="Stories Test Project",
        status="draft",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def sample_story_data(test_client_for_stories, test_project_for_stories):
    """Sample story data for tests."""
    return {
        "client_id": test_client_for_stories.id,
        "project_id": test_project_for_stories.id,
        "story_type": "customer_win",
        "title": "How Client X Increased Revenue by 150%",
        "summary": "Client X transformed their business using our solution, achieving remarkable results.",
        "full_story": {
            "context": "Starting point and background",
            "challenge": "Problems they faced",
            "resolution": "How we solved it",
        },
        "key_metrics": {
            "revenue": "+150%",
            "time_saved": "20 hours/week",
        },
        "emotional_hook": "We went from struggling to thriving in just 3 months",
        "source": "manual_entry",
    }


# ==================== Story CRUD Tests ====================


def test_create_story(test_user_headers, sample_story_data):
    """Test creating a new story."""
    response = client.post(
        "/api/stories/",
        json=sample_story_data,
        headers=test_user_headers,
    )

    assert response.status_code == 201
    data = response.json()

    assert data["title"] == sample_story_data["title"]
    assert data["story_type"] == sample_story_data["story_type"]
    assert data["summary"] == sample_story_data["summary"]
    assert data["key_metrics"] == sample_story_data["key_metrics"]
    assert data["emotional_hook"] == sample_story_data["emotional_hook"]
    assert data["source"] == sample_story_data["source"]
    assert data["usage_count"] == 0
    assert data["platforms_used"] == []
    assert "id" in data
    assert "created_at" in data


def test_create_story_minimal(test_user_headers, test_client_for_stories):
    """Test creating a story with minimal required fields."""
    minimal_data = {
        "client_id": test_client_for_stories.id,
    }

    response = client.post(
        "/api/stories/",
        json=minimal_data,
        headers=test_user_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["client_id"] == test_client_for_stories.id
    assert data["usage_count"] == 0


def test_create_story_unauthorized(sample_story_data):
    """Test creating story without authentication fails."""
    response = client.post("/api/stories/", json=sample_story_data)
    assert response.status_code == 401


def test_create_story_wrong_client(test_user_headers, sample_story_data):
    """Test creating story for non-existent client fails."""
    sample_story_data["client_id"] = "nonexistent-client"

    response = client.post(
        "/api/stories/",
        json=sample_story_data,
        headers=test_user_headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_story(db_session, test_user, test_user_headers, test_client_for_stories):
    """Test getting a story by ID."""
    # Create story directly in DB
    from backend.schemas import StoryCreate

    story_create = StoryCreate(
        client_id=test_client_for_stories.id,
        story_type="success",
        title="Test Story",
        summary="A test story",
    )
    db_story = story_service.create_story(db_session, story_create, test_user.id)

    # Get story via API
    response = client.get(
        f"/api/stories/{db_story.id}",
        headers=test_user_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == db_story.id
    assert data["title"] == "Test Story"
    assert data["usage_count"] == 0
    assert data["platforms_used"] == []


def test_get_story_not_found(test_user_headers):
    """Test getting non-existent story returns 404."""
    response = client.get(
        "/api/stories/nonexistent-story",
        headers=test_user_headers,
    )

    assert response.status_code == 404


def test_get_client_stories(db_session, test_user, test_user_headers, test_client_for_stories):
    """Test getting all stories for a client."""
    from backend.schemas import StoryCreate

    # Create multiple stories
    for i in range(3):
        story_create = StoryCreate(
            client_id=test_client_for_stories.id,
            story_type="customer_win" if i % 2 == 0 else "success",
            title=f"Story {i+1}",
            summary=f"Summary {i+1}",
        )
        story_service.create_story(db_session, story_create, test_user.id)

    # Get all stories
    response = client.get(
        f"/api/stories/client/{test_client_for_stories.id}",
        headers=test_user_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["stories"]) == 3


def test_get_client_stories_filtered_by_type(
    db_session, test_user, test_user_headers, test_client_for_stories
):
    """Test filtering stories by type."""
    from backend.schemas import StoryCreate

    # Create stories of different types
    for story_type in ["customer_win", "success", "customer_win"]:
        story_create = StoryCreate(
            client_id=test_client_for_stories.id,
            story_type=story_type,
            title=f"Story {story_type}",
        )
        story_service.create_story(db_session, story_create, test_user.id)

    # Get only customer_win stories
    response = client.get(
        f"/api/stories/client/{test_client_for_stories.id}?story_type=customer_win",
        headers=test_user_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(s["story_type"] == "customer_win" for s in data["stories"])


def test_update_story(db_session, test_user, test_user_headers, test_client_for_stories):
    """Test updating a story."""
    from backend.schemas import StoryCreate

    # Create story
    story_create = StoryCreate(
        client_id=test_client_for_stories.id,
        title="Original Title",
        summary="Original Summary",
    )
    db_story = story_service.create_story(db_session, story_create, test_user.id)

    # Update story
    update_data = {
        "title": "Updated Title",
        "summary": "Updated Summary",
        "emotional_hook": "New compelling hook",
    }

    response = client.put(
        f"/api/stories/{db_story.id}",
        json=update_data,
        headers=test_user_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["summary"] == "Updated Summary"
    assert data["emotional_hook"] == "New compelling hook"


def test_update_story_not_found(test_user_headers):
    """Test updating non-existent story returns 404."""
    response = client.put(
        "/api/stories/nonexistent",
        json={"title": "New Title"},
        headers=test_user_headers,
    )

    assert response.status_code == 404


def test_delete_story(db_session, test_user, test_user_headers, test_client_for_stories):
    """Test deleting a story."""
    from backend.schemas import StoryCreate

    # Create story
    story_create = StoryCreate(
        client_id=test_client_for_stories.id,
        title="Story to Delete",
    )
    db_story = story_service.create_story(db_session, story_create, test_user.id)

    # Delete story
    response = client.delete(
        f"/api/stories/{db_story.id}",
        headers=test_user_headers,
    )

    assert response.status_code == 204

    # Verify deleted
    verify_response = client.get(
        f"/api/stories/{db_story.id}",
        headers=test_user_headers,
    )
    assert verify_response.status_code == 404


def test_delete_story_not_found(test_user_headers):
    """Test deleting non-existent story returns 404."""
    response = client.delete(
        "/api/stories/nonexistent",
        headers=test_user_headers,
    )

    assert response.status_code == 404


# ==================== Story Usage Tests ====================


def test_track_story_usage(
    db_session, test_user, test_user_headers, test_client_for_stories, test_project_for_stories
):
    """Test tracking story usage."""
    from backend.schemas import StoryCreate
    from backend.models import Post, Run
    import uuid

    # Create story
    story_create = StoryCreate(
        client_id=test_client_for_stories.id,
        title="Story for Usage Tracking",
    )
    db_story = story_service.create_story(db_session, story_create, test_user.id)

    # Create run
    run = Run(
        id=f"run-{uuid.uuid4().hex[:12]}",
        project_id=test_project_for_stories.id,
        status="completed",
        is_batch=True,
    )
    db_session.add(run)
    db_session.commit()

    # Create post
    post = Post(
        id=f"post-{uuid.uuid4().hex[:12]}",
        project_id=test_project_for_stories.id,
        run_id=run.id,
        content="Test post content",
        template_id="1",
        target_platform="linkedin",
    )
    db_session.add(post)
    db_session.commit()

    # Track usage
    usage_data = {
        "story_id": db_story.id,
        "post_id": post.id,
        "platform": "linkedin",
        "usage_type": "primary",
        "template_id": 1,
    }

    response = client.post(
        "/api/stories/usage",
        json=usage_data,
        headers=test_user_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["story_id"] == db_story.id
    assert data["post_id"] == post.id
    assert data["platform"] == "linkedin"
    assert data["usage_type"] == "primary"


def test_get_available_stories(
    db_session, test_user, test_user_headers, test_client_for_stories, test_project_for_stories
):
    """Test getting available stories (excluding used on platform)."""
    from backend.schemas import StoryCreate, StoryUsageCreate
    from backend.models import Post, Run
    import uuid

    # Create stories
    story1 = story_service.create_story(
        db_session,
        StoryCreate(client_id=test_client_for_stories.id, title="Story 1"),
        test_user.id,
    )
    story2 = story_service.create_story(
        db_session,
        StoryCreate(client_id=test_client_for_stories.id, title="Story 2"),
        test_user.id,
    )
    story3 = story_service.create_story(
        db_session,
        StoryCreate(client_id=test_client_for_stories.id, title="Story 3"),
        test_user.id,
    )

    # Create run and post
    run = Run(
        id=f"run-{uuid.uuid4().hex[:12]}",
        project_id=test_project_for_stories.id,
        status="completed",
        is_batch=True,
    )
    db_session.add(run)
    db_session.commit()

    post = Post(
        id=f"post-{uuid.uuid4().hex[:12]}",
        project_id=test_project_for_stories.id,
        run_id=run.id,
        content="Test",
        template_id="1",
        target_platform="linkedin",
    )
    db_session.add(post)
    db_session.commit()

    # Mark story1 as used on LinkedIn
    story_service.track_story_usage(
        db_session,
        StoryUsageCreate(
            story_id=story1.id, post_id=post.id, platform="linkedin", usage_type="primary"
        ),
    )

    # Get available stories for LinkedIn (should exclude story1)
    request_data = {
        "client_id": test_client_for_stories.id,
        "platform": "linkedin",
        "limit": 10,
    }

    response = client.post(
        "/api/stories/available",
        json=request_data,
        headers=test_user_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2  # story2 and story3, not story1
    story_ids = [s["id"] for s in data["stories"]]
    assert story2.id in story_ids
    assert story3.id in story_ids
    assert story1.id not in story_ids


def test_get_available_stories_all_platforms(
    db_session, test_user, test_user_headers, test_client_for_stories, test_project_for_stories
):
    """Test getting all stories when no platform filter."""
    from backend.schemas import StoryCreate, StoryUsageCreate
    from backend.services import crud

    # Create stories
    story1 = story_service.create_story(
        db_session,
        StoryCreate(client_id=test_client_for_stories.id, title="Story 1"),
        test_user.id,
    )
    story2 = story_service.create_story(
        db_session,
        StoryCreate(client_id=test_client_for_stories.id, title="Story 2"),
        test_user.id,
    )

    # Mark story1 as used on LinkedIn
    post = create_test_post(
        db_session, test_project_for_stories.id, platform="linkedin", template_id=1, content="Test"
    )
    story_service.track_story_usage(
        db_session,
        StoryUsageCreate(
            story_id=story1.id, post_id=post.id, platform="linkedin", usage_type="primary"
        ),
    )

    # Get all stories (no platform filter)
    request_data = {
        "client_id": test_client_for_stories.id,
        "limit": 10,
    }

    response = client.post(
        "/api/stories/available",
        json=request_data,
        headers=test_user_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2  # Both stories returned


# ==================== Analytics Tests ====================


def test_get_story_analytics(
    db_session, test_user, test_user_headers, test_client_for_stories, test_project_for_stories
):
    """Test getting story analytics."""
    from backend.schemas import StoryCreate, StoryUsageCreate
    from backend.services import crud

    # Create story
    story = story_service.create_story(
        db_session,
        StoryCreate(client_id=test_client_for_stories.id, title="Analytics Test Story"),
        test_user.id,
    )

    # Create posts and track usage
    for platform in ["linkedin", "twitter", "facebook"]:
        post = create_test_post(
            db_session,
            test_project_for_stories.id,
            platform=platform,
            template_id=1,
            content="Test",
        )
        story_service.track_story_usage(
            db_session,
            StoryUsageCreate(
                story_id=story.id,
                post_id=post.id,
                platform=platform,
                usage_type="primary",
                template_id=1,
            ),
        )

    # Get analytics
    response = client.get(
        f"/api/stories/{story.id}/analytics",
        headers=test_user_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["story_id"] == story.id
    assert data["title"] == "Analytics Test Story"
    assert data["total_uses"] == 3
    assert set(data["platforms_used"]) == {"linkedin", "twitter", "facebook"}
    assert data["templates_used"] == [1]
    assert "first_used" in data
    assert "last_used" in data


def test_get_story_analytics_not_found(test_user_headers):
    """Test getting analytics for non-existent story."""
    response = client.get(
        "/api/stories/nonexistent/analytics",
        headers=test_user_headers,
    )

    assert response.status_code == 404


def test_get_client_story_analytics(
    db_session, test_user, test_user_headers, test_client_for_stories, test_project_for_stories
):
    """Test getting analytics for all client stories."""
    from backend.schemas import StoryCreate, StoryUsageCreate
    from backend.services import crud

    # Create stories
    story1 = story_service.create_story(
        db_session,
        StoryCreate(client_id=test_client_for_stories.id, title="Story 1"),
        test_user.id,
    )
    story2 = story_service.create_story(
        db_session,
        StoryCreate(client_id=test_client_for_stories.id, title="Story 2"),
        test_user.id,
    )

    # Track usage for story1
    post = create_test_post(
        db_session, test_project_for_stories.id, platform="linkedin", template_id=1, content="Test"
    )
    story_service.track_story_usage(
        db_session,
        StoryUsageCreate(
            story_id=story1.id, post_id=post.id, platform="linkedin", usage_type="primary"
        ),
    )

    # Get client analytics
    response = client.get(
        f"/api/stories/client/{test_client_for_stories.id}/analytics",
        headers=test_user_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Find story1 analytics
    story1_analytics = next(a for a in data if a["story_id"] == story1.id)
    assert story1_analytics["total_uses"] == 1

    # Find story2 analytics
    story2_analytics = next(a for a in data if a["story_id"] == story2.id)
    assert story2_analytics["total_uses"] == 0


# ==================== Authorization Tests ====================


def test_cannot_access_other_user_story(
    db_session, test_user, test_user_headers, test_client_for_stories
):
    """Test that users cannot access stories they don't own."""
    from backend.schemas import StoryCreate
    from backend.models import User
    from backend.utils.auth import create_access_token, get_password_hash

    # Create second user
    second_user = User(
        id="user-second-test",
        email="second@example.com",
        full_name="Second User",
        hashed_password=get_password_hash("testpass123"),
        is_active=True,
        is_superuser=False,
    )
    db_session.add(second_user)
    db_session.commit()

    # Create story owned by test_user
    story = story_service.create_story(
        db_session,
        StoryCreate(client_id=test_client_for_stories.id, title="Protected Story"),
        test_user.id,
    )

    # Try to access with second_user credentials
    second_user_token = create_access_token({"sub": second_user.email})
    second_user_headers = {"Authorization": f"Bearer {second_user_token}"}

    response = client.get(
        f"/api/stories/{story.id}",
        headers=second_user_headers,
    )

    # Should get 401 (token invalid) or 403 (not authorized)
    assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
