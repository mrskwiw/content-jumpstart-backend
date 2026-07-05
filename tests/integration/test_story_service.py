"""
Unit tests for story_service.py.

Tests story CRUD operations, usage tracking, and analytics.
"""

import pytest
from datetime import datetime, UTC
from sqlalchemy.orm import Session

from backend.models import MinedStory, StoryUsage, User, Client, Project
from backend.schemas import StoryCreate, StoryUpdate, StoryUsageCreate
from backend.services.story_service import story_service


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    from backend.utils.auth import get_password_hash

    user = User(
        id="user-test-stories",
        email="test-stories@example.com",
        full_name="Test User Stories",
        hashed_password=get_password_hash("testpass123"),
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_client(db_session: Session, test_user: User) -> Client:
    """Create a test client."""
    client = Client(
        id="client-test-stories",
        user_id=test_user.id,
        name="Test Client",
        email="client@example.com",
        business_description="A test client for story service testing",
        ideal_customer="Tech professionals",
        main_problem_solved="Testing challenges",
    )
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


@pytest.fixture
def test_project(db_session: Session, test_client: Client, test_user: User) -> Project:
    """Create a test project."""
    project = Project(
        id="proj-test-stories",
        client_id=test_client.id,
        user_id=test_user.id,
        name="Test Project",
        templates=["1", "2", "3"],
        template_quantities={"1": 10, "2": 10, "3": 10},
        num_posts=30,
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


class TestStoryService:
    """Test cases for story_service."""

    def test_create_story_minimal(self, db_session: Session, test_client: Client, test_user: User):
        """Test creating a story with minimal required fields."""
        story_create = StoryCreate(client_id=test_client.id)

        story = story_service.create_story(db_session, story_create, test_user.id)

        assert story.id is not None
        assert story.client_id == test_client.id
        assert story.user_id == test_user.id
        assert story.project_id is None
        assert story.story_type is None
        assert story.title is None
        assert story.summary is None
        assert story.source is None

    def test_create_story_full(
        self,
        db_session: Session,
        test_client: Client,
        test_project: Project,
        test_user: User,
    ):
        """Test creating a story with all fields."""
        full_story = {
            "customer_background": {"industry": "SaaS", "size": "50 employees"},
            "challenge": {"problem": "Manual processes"},
            "decision_process": {"evaluation_criteria": ["Cost", "Features"]},
            "implementation": {"timeline": "3 months"},
            "results": {"quantitative_results": ["50% faster", "30% cost reduction"]},
            "testimonials": {"headline_quote": "Game changer!"},
            "future_plans": {"expansion": "Q2 2026"},
        }

        key_metrics = {
            "revenue_increase": "300%",
            "time_saved": "20 hours/week",
            "customer_satisfaction": "95%",
        }

        story_create = StoryCreate(
            client_id=test_client.id,
            project_id=test_project.id,
            story_type="customer_win",
            title="How Acme Corp Tripled Revenue",
            summary="Acme Corp achieved 300% revenue growth using our platform.",
            full_story=full_story,
            key_metrics=key_metrics,
            emotional_hook="This solution completely transformed our business",
            source="story_mining_tool",
        )

        story = story_service.create_story(db_session, story_create, test_user.id)

        assert story.id is not None
        assert story.client_id == test_client.id
        assert story.project_id == test_project.id
        assert story.user_id == test_user.id
        assert story.story_type == "customer_win"
        assert story.title == "How Acme Corp Tripled Revenue"
        assert story.summary == "Acme Corp achieved 300% revenue growth using our platform."
        assert story.full_story == full_story
        assert story.key_metrics == key_metrics
        assert story.emotional_hook == "This solution completely transformed our business"
        assert story.source == "story_mining_tool"
        assert story.created_at is not None
        assert story.updated_at is not None

    def test_get_story(self, db_session: Session, test_client: Client, test_user: User):
        """Test retrieving a story by ID."""
        story_create = StoryCreate(
            client_id=test_client.id, title="Test Story", summary="Test summary"
        )
        created = story_service.create_story(db_session, story_create, test_user.id)

        retrieved = story_service.get_story(db_session, created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == "Test Story"
        assert retrieved.summary == "Test summary"

    def test_get_story_not_found(self, db_session: Session):
        """Test retrieving a non-existent story returns None."""
        story = story_service.get_story(db_session, "non-existent-id")
        assert story is None

    def test_get_client_stories(self, db_session: Session, test_client: Client, test_user: User):
        """Test retrieving all stories for a client."""
        # Create multiple stories
        for i in range(3):
            story_create = StoryCreate(
                client_id=test_client.id,
                title=f"Story {i + 1}",
                story_type="customer_win" if i % 2 == 0 else "case_study",
            )
            story_service.create_story(db_session, story_create, test_user.id)

        # Get all stories
        all_stories = story_service.get_client_stories(db_session, test_client.id)
        assert len(all_stories) == 3

        # Filter by story type
        filtered_stories = story_service.get_client_stories(
            db_session, test_client.id, story_type="customer_win"
        )
        assert len(filtered_stories) == 2

        # Test limit
        limited_stories = story_service.get_client_stories(db_session, test_client.id, limit=2)
        assert len(limited_stories) == 2

    def test_update_story(self, db_session: Session, test_client: Client, test_user: User):
        """Test updating a story."""
        # Create story
        story_create = StoryCreate(
            client_id=test_client.id,
            title="Original Title",
            summary="Original summary",
            story_type="customer_win",
        )
        story = story_service.create_story(db_session, story_create, test_user.id)
        original_updated_at = story.updated_at

        # Update story
        story_update = StoryUpdate(
            title="Updated Title",
            summary="Updated summary",
            emotional_hook="New hook",
        )
        updated = story_service.update_story(db_session, story.id, story_update)

        assert updated.title == "Updated Title"
        assert updated.summary == "Updated summary"
        assert updated.emotional_hook == "New hook"
        assert updated.story_type == "customer_win"  # Unchanged
        assert updated.updated_at >= original_updated_at  # >= instead of > to handle fast execution

    def test_update_story_not_found(self, db_session: Session):
        """Test updating a non-existent story returns None."""
        story_update = StoryUpdate(title="New Title")
        result = story_service.update_story(db_session, "non-existent-id", story_update)
        assert result is None

    def test_delete_story(self, db_session: Session, test_client: Client, test_user: User):
        """Test deleting a story."""
        # Create story
        story_create = StoryCreate(client_id=test_client.id, title="To Delete")
        story = story_service.create_story(db_session, story_create, test_user.id)
        story_id = story.id

        # Delete story
        result = story_service.delete_story(db_session, story_id)
        assert result is True

        # Verify deleted
        deleted = story_service.get_story(db_session, story_id)
        assert deleted is None

    def test_delete_story_not_found(self, db_session: Session):
        """Test deleting a non-existent story returns False."""
        result = story_service.delete_story(db_session, "non-existent-id")
        assert result is False

    def test_track_story_usage(self, db_session: Session, test_client: Client, test_user: User):
        """Test tracking story usage."""
        # Create story
        story_create = StoryCreate(client_id=test_client.id, title="Test Story")
        story = story_service.create_story(db_session, story_create, test_user.id)

        # Track usage
        usage_create = StoryUsageCreate(
            story_id=story.id,
            post_id="post-123",
            platform="linkedin",
            usage_type="full_story",
            template_id=5,
        )
        usage = story_service.track_story_usage(db_session, usage_create)

        assert usage.id is not None
        assert usage.story_id == story.id
        assert usage.post_id == "post-123"
        assert usage.platform == "linkedin"
        assert usage.usage_type == "full_story"
        assert usage.template_id == 5
        assert usage.used_at is not None

    def test_get_story_usage(self, db_session: Session, test_client: Client, test_user: User):
        """Test retrieving story usage records."""
        # Create story
        story_create = StoryCreate(client_id=test_client.id, title="Test Story")
        story = story_service.create_story(db_session, story_create, test_user.id)

        # Track multiple usages
        for i, platform in enumerate(["linkedin", "twitter", "linkedin"], 1):
            usage_create = StoryUsageCreate(
                story_id=story.id, post_id=f"post-{i}", platform=platform
            )
            story_service.track_story_usage(db_session, usage_create)

        # Get all usage
        usages = story_service.get_story_usage(db_session, story.id)
        assert len(usages) == 3

        # Verify platforms
        platforms = [u.platform for u in usages]
        assert platforms.count("linkedin") == 2
        assert platforms.count("twitter") == 1

    def test_get_available_stories(self, db_session: Session, test_client: Client, test_user: User):
        """Test getting stories available for a platform."""
        # Create stories
        story1_create = StoryCreate(
            client_id=test_client.id, title="Story 1", story_type="customer_win"
        )
        story1 = story_service.create_story(db_session, story1_create, test_user.id)

        story2_create = StoryCreate(
            client_id=test_client.id, title="Story 2", story_type="customer_win"
        )
        story2 = story_service.create_story(db_session, story2_create, test_user.id)

        story3_create = StoryCreate(
            client_id=test_client.id, title="Story 3", story_type="case_study"
        )
        story3 = story_service.create_story(db_session, story3_create, test_user.id)

        # Use story1 on linkedin
        usage_create = StoryUsageCreate(story_id=story1.id, post_id="post-1", platform="linkedin")
        story_service.track_story_usage(db_session, usage_create)

        # Get available stories for linkedin
        available = story_service.get_available_stories(
            db_session, test_client.id, platform="linkedin"
        )

        # Should exclude story1 (already used on linkedin)
        available_ids = [s.id for s in available]
        assert story1.id not in available_ids
        assert story2.id in available_ids
        assert story3.id in available_ids

        # Filter by story type
        available_wins = story_service.get_available_stories(
            db_session, test_client.id, platform="linkedin", story_type="customer_win"
        )
        available_win_ids = [s.id for s in available_wins]
        assert story1.id not in available_win_ids
        assert story2.id in available_win_ids
        assert story3.id not in available_win_ids  # Different type

    def test_get_story_analytics(self, db_session: Session, test_client: Client, test_user: User):
        """Test getting analytics for a story."""
        # Create story
        story_create = StoryCreate(client_id=test_client.id, title="Analytics Story")
        story = story_service.create_story(db_session, story_create, test_user.id)

        # Track usage on different platforms
        platforms = ["linkedin", "twitter", "facebook", "linkedin"]
        templates = [1, 2, 3, 1]
        for i, (platform, template) in enumerate(zip(platforms, templates), 1):
            usage_create = StoryUsageCreate(
                story_id=story.id,
                post_id=f"post-{i}",
                platform=platform,
                template_id=template,
            )
            story_service.track_story_usage(db_session, usage_create)

        # Get analytics
        analytics = story_service.get_story_analytics(db_session, story.id)

        assert analytics is not None
        assert analytics.story_id == story.id
        assert analytics.title == "Analytics Story"
        assert analytics.total_uses == 4
        assert set(analytics.platforms_used) == {"linkedin", "twitter", "facebook"}
        assert set(analytics.templates_used) == {1, 2, 3}
        assert analytics.first_used is not None
        assert analytics.last_used is not None
        assert analytics.last_used >= analytics.first_used

    def test_get_story_analytics_no_usage(
        self, db_session: Session, test_client: Client, test_user: User
    ):
        """Test analytics for a story with no usage."""
        story_create = StoryCreate(client_id=test_client.id, title="Unused Story")
        story = story_service.create_story(db_session, story_create, test_user.id)

        analytics = story_service.get_story_analytics(db_session, story.id)

        assert analytics is not None
        assert analytics.total_uses == 0
        assert analytics.platforms_used == []
        assert analytics.templates_used == []
        assert analytics.first_used is None
        assert analytics.last_used is None

    def test_get_client_story_analytics(
        self, db_session: Session, test_client: Client, test_user: User
    ):
        """Test getting analytics for all client stories."""
        # Create stories with different usage
        story1_create = StoryCreate(client_id=test_client.id, title="Story 1")
        story1 = story_service.create_story(db_session, story1_create, test_user.id)

        story2_create = StoryCreate(client_id=test_client.id, title="Story 2")
        story2 = story_service.create_story(db_session, story2_create, test_user.id)

        # Track usage for story1
        for i in range(3):
            usage_create = StoryUsageCreate(
                story_id=story1.id, post_id=f"post-{i}", platform="linkedin"
            )
            story_service.track_story_usage(db_session, usage_create)

        # Track usage for story2
        usage_create = StoryUsageCreate(story_id=story2.id, post_id="post-4", platform="twitter")
        story_service.track_story_usage(db_session, usage_create)

        # Get client analytics
        analytics_list = story_service.get_client_story_analytics(db_session, test_client.id)

        assert len(analytics_list) == 2

        # Verify analytics
        analytics_dict = {a.story_id: a for a in analytics_list}
        assert analytics_dict[story1.id].total_uses == 3
        assert analytics_dict[story2.id].total_uses == 1

    def test_cascade_delete_with_usage(
        self, db_session: Session, test_client: Client, test_user: User
    ):
        """Test that deleting a story also deletes its usage records."""
        # Create story with usage
        story_create = StoryCreate(client_id=test_client.id, title="Story to Delete")
        story = story_service.create_story(db_session, story_create, test_user.id)

        # Track usage
        usage_create = StoryUsageCreate(story_id=story.id, post_id="post-1")
        story_service.track_story_usage(db_session, usage_create)

        # Verify usage exists
        usages = story_service.get_story_usage(db_session, story.id)
        assert len(usages) == 1

        # Delete story
        story_service.delete_story(db_session, story.id)

        # Verify usage is also deleted (cascade)
        usages_after = story_service.get_story_usage(db_session, story.id)
        assert len(usages_after) == 0
