"""Unit tests for project module.

Tests cover:
- Project, Revision, RevisionScope, RevisionPost, RevisionDiff models
- to_dict and from_dict serialization
- RevisionScope properties and methods
- RevisionDiff.to_markdown
"""

from datetime import datetime

import pytest

from src.models.project import (
    Project,
    ProjectStatus,
    Revision,
    RevisionDiff,
    RevisionPost,
    RevisionScope,
    RevisionStatus,
)


class TestProjectStatus:
    """Tests for ProjectStatus enum."""

    def test_status_values(self):
        """Test project status values."""
        assert ProjectStatus.IN_PROGRESS.value == "in_progress"
        assert ProjectStatus.COMPLETED.value == "completed"
        assert ProjectStatus.ARCHIVED.value == "archived"


class TestRevisionStatus:
    """Tests for RevisionStatus enum."""

    def test_revision_status_values(self):
        """Test revision status values."""
        assert RevisionStatus.PENDING.value == "pending"
        assert RevisionStatus.IN_PROGRESS.value == "in_progress"
        assert RevisionStatus.COMPLETED.value == "completed"
        assert RevisionStatus.FAILED.value == "failed"


class TestProject:
    """Tests for Project model."""

    @pytest.fixture
    def sample_project(self):
        """Create a sample project."""
        return Project(
            project_id="TestClient_20250115_120000",
            client_name="TestClient",
            deliverable_path="/path/to/deliverables",
            brief_path="/path/to/brief.txt",
            num_posts=30,
            quality_profile_name="default",
            notes="Test project notes",
        )

    def test_project_creation(self, sample_project):
        """Test basic project creation."""
        assert sample_project.project_id == "TestClient_20250115_120000"
        assert sample_project.client_name == "TestClient"
        assert sample_project.num_posts == 30
        assert sample_project.status == ProjectStatus.COMPLETED  # Default

    def test_project_to_dict(self, sample_project):
        """Test Project.to_dict serialization."""
        result = sample_project.to_dict()

        assert result["project_id"] == "TestClient_20250115_120000"
        assert result["client_name"] == "TestClient"
        assert result["deliverable_path"] == "/path/to/deliverables"
        assert result["brief_path"] == "/path/to/brief.txt"
        assert result["num_posts"] == 30
        assert result["quality_profile_name"] == "default"
        assert result["status"] == "completed"
        assert result["notes"] == "Test project notes"
        assert "created_at" in result

    def test_project_from_dict(self):
        """Test Project.from_dict deserialization."""
        data = {
            "project_id": "Client_20250110_080000",
            "client_name": "Client",
            "created_at": "2025-01-10T08:00:00",
            "deliverable_path": "/path/to/files",
            "brief_path": None,
            "num_posts": 20,
            "quality_profile_name": None,
            "status": "in_progress",
            "notes": None,
        }

        project = Project.from_dict(data)

        assert project.project_id == "Client_20250110_080000"
        assert project.status == ProjectStatus.IN_PROGRESS
        assert isinstance(project.created_at, datetime)


class TestRevisionPost:
    """Tests for RevisionPost model."""

    @pytest.fixture
    def sample_revision_post(self):
        """Create a sample revision post."""
        return RevisionPost(
            post_index=5,
            template_id=3,
            template_name="Contrarian Take",
            original_content="Original post content here.",
            original_word_count=100,
            revised_content="Revised and improved post content here.",
            revised_word_count=120,
            changes_summary="Added more detail and stronger hook.",
        )

    def test_revision_post_creation(self, sample_revision_post):
        """Test basic revision post creation."""
        assert sample_revision_post.post_index == 5
        assert sample_revision_post.template_name == "Contrarian Take"
        assert sample_revision_post.original_word_count == 100
        assert sample_revision_post.revised_word_count == 120

    def test_revision_post_to_dict(self, sample_revision_post):
        """Test RevisionPost.to_dict serialization."""
        result = sample_revision_post.to_dict("rev_123")

        assert result["revision_id"] == "rev_123"
        assert result["post_index"] == 5
        assert result["template_id"] == 3
        assert result["template_name"] == "Contrarian Take"
        assert result["original_content"] == "Original post content here."
        assert result["original_word_count"] == 100
        assert result["revised_content"] == "Revised and improved post content here."
        assert result["revised_word_count"] == 120
        assert result["changes_summary"] == "Added more detail and stronger hook."


class TestRevision:
    """Tests for Revision model."""

    @pytest.fixture
    def sample_revision(self):
        """Create a sample revision."""
        return Revision(
            revision_id="rev_20250115_120000",
            project_id="TestClient_20250110_080000",
            attempt_number=1,
            feedback="Please make the hook stronger.",
            cost=0.15,
        )

    def test_revision_creation(self, sample_revision):
        """Test basic revision creation."""
        assert sample_revision.revision_id == "rev_20250115_120000"
        assert sample_revision.project_id == "TestClient_20250110_080000"
        assert sample_revision.attempt_number == 1
        assert sample_revision.status == RevisionStatus.PENDING  # Default
        assert sample_revision.completed_at is None

    def test_revision_to_dict(self, sample_revision):
        """Test Revision.to_dict serialization."""
        result = sample_revision.to_dict()

        assert result["revision_id"] == "rev_20250115_120000"
        assert result["project_id"] == "TestClient_20250110_080000"
        assert result["attempt_number"] == 1
        assert result["status"] == "pending"
        assert result["feedback"] == "Please make the hook stronger."
        assert result["cost"] == 0.15
        assert result["completed_at"] is None

    def test_revision_to_dict_with_completed_at(self):
        """Test Revision.to_dict with completed_at set."""
        revision = Revision(
            revision_id="rev_123",
            project_id="proj_456",
            attempt_number=2,
            feedback="Fix typos",
            status=RevisionStatus.COMPLETED,
            completed_at=datetime(2025, 1, 15, 14, 30, 0),
        )

        result = revision.to_dict()

        assert result["completed_at"] == "2025-01-15T14:30:00"

    def test_revision_from_dict(self):
        """Test Revision.from_dict deserialization."""
        data = {
            "revision_id": "rev_abc",
            "project_id": "proj_xyz",
            "attempt_number": 3,
            "status": "completed",
            "feedback": "Original feedback",
            "created_at": "2025-01-10T10:00:00",
            "completed_at": "2025-01-10T12:00:00",
            "cost": 0.25,
        }

        revision = Revision.from_dict(data)

        assert revision.revision_id == "rev_abc"
        assert revision.status == RevisionStatus.COMPLETED
        assert isinstance(revision.created_at, datetime)
        assert isinstance(revision.completed_at, datetime)
        assert revision.posts == []  # Posts loaded separately

    def test_revision_from_dict_without_completed_at(self):
        """Test Revision.from_dict without completed_at."""
        data = {
            "revision_id": "rev_pending",
            "project_id": "proj_test",
            "attempt_number": 1,
            "status": "pending",
            "feedback": "Pending feedback",
            "created_at": "2025-01-15T09:00:00",
            "completed_at": None,
            "cost": 0.0,
        }

        revision = Revision.from_dict(data)

        assert revision.completed_at is None

    def test_mark_completed(self, sample_revision):
        """Test Revision.mark_completed method."""
        assert sample_revision.status == RevisionStatus.PENDING
        assert sample_revision.completed_at is None

        sample_revision.mark_completed()

        assert sample_revision.status == RevisionStatus.COMPLETED
        assert sample_revision.completed_at is not None
        assert isinstance(sample_revision.completed_at, datetime)

    def test_mark_failed(self, sample_revision):
        """Test Revision.mark_failed method."""
        assert sample_revision.status == RevisionStatus.PENDING
        assert sample_revision.completed_at is None

        sample_revision.mark_failed()

        assert sample_revision.status == RevisionStatus.FAILED
        assert sample_revision.completed_at is not None


class TestRevisionScope:
    """Tests for RevisionScope model."""

    @pytest.fixture
    def sample_scope(self):
        """Create a sample revision scope."""
        return RevisionScope(
            project_id="proj_test",
            allowed_revisions=5,
            used_revisions=2,
        )

    def test_revision_scope_creation(self, sample_scope):
        """Test basic revision scope creation."""
        assert sample_scope.project_id == "proj_test"
        assert sample_scope.allowed_revisions == 5
        assert sample_scope.used_revisions == 2
        assert sample_scope.scope_exceeded is False
        assert sample_scope.upsell_offered is False
        assert sample_scope.upsell_accepted is False

    def test_remaining_revisions_property(self, sample_scope):
        """Test remaining_revisions property."""
        assert sample_scope.remaining_revisions == 3  # 5 - 2 = 3

    def test_remaining_revisions_at_zero(self):
        """Test remaining_revisions when at limit."""
        scope = RevisionScope(
            project_id="test",
            allowed_revisions=5,
            used_revisions=5,
        )
        assert scope.remaining_revisions == 0

    def test_remaining_revisions_exceeds_limit(self):
        """Test remaining_revisions when over limit."""
        scope = RevisionScope(
            project_id="test",
            allowed_revisions=5,
            used_revisions=7,  # Over limit
        )
        assert scope.remaining_revisions == 0  # max(0, -2) = 0

    def test_is_at_limit_property_false(self, sample_scope):
        """Test is_at_limit when not at limit."""
        assert sample_scope.is_at_limit is False

    def test_is_at_limit_property_true(self):
        """Test is_at_limit when at limit."""
        scope = RevisionScope(
            project_id="test",
            allowed_revisions=5,
            used_revisions=5,
        )
        assert scope.is_at_limit is True

    def test_is_at_limit_property_over(self):
        """Test is_at_limit when over limit."""
        scope = RevisionScope(
            project_id="test",
            allowed_revisions=5,
            used_revisions=6,
        )
        assert scope.is_at_limit is True

    def test_is_near_limit_property_true(self):
        """Test is_near_limit when 1 revision remaining."""
        scope = RevisionScope(
            project_id="test",
            allowed_revisions=5,
            used_revisions=4,
        )
        assert scope.is_near_limit is True

    def test_is_near_limit_property_false(self, sample_scope):
        """Test is_near_limit when more than 1 remaining."""
        assert sample_scope.is_near_limit is False  # 3 remaining

    def test_increment_usage(self, sample_scope):
        """Test increment_usage method."""
        assert sample_scope.used_revisions == 2

        sample_scope.increment_usage()

        assert sample_scope.used_revisions == 3
        assert sample_scope.scope_exceeded is False

    def test_increment_usage_exceeds_limit(self):
        """Test increment_usage when it exceeds limit."""
        scope = RevisionScope(
            project_id="test",
            allowed_revisions=5,
            used_revisions=5,
        )

        scope.increment_usage()

        assert scope.used_revisions == 6
        assert scope.scope_exceeded is True

    def test_add_revisions(self):
        """Test add_revisions method (after upsell)."""
        scope = RevisionScope(
            project_id="test",
            allowed_revisions=5,
            used_revisions=5,
            scope_exceeded=True,
        )

        scope.add_revisions(3)

        assert scope.allowed_revisions == 8
        assert scope.scope_exceeded is False
        assert scope.upsell_accepted is True

    def test_to_dict(self, sample_scope):
        """Test RevisionScope.to_dict serialization."""
        result = sample_scope.to_dict()

        assert result["project_id"] == "proj_test"
        assert result["allowed_revisions"] == 5
        assert result["used_revisions"] == 2
        assert result["remaining_revisions"] == 3  # Computed property
        assert result["scope_exceeded"] is False
        assert result["upsell_offered"] is False
        assert result["upsell_accepted"] is False

    def test_from_dict(self):
        """Test RevisionScope.from_dict deserialization."""
        data = {
            "project_id": "proj_from_db",
            "allowed_revisions": 10,
            "used_revisions": 7,
            "remaining_revisions": 3,  # This should be removed
            "scope_exceeded": False,
            "upsell_offered": True,
            "upsell_accepted": False,
        }

        scope = RevisionScope.from_dict(data)

        assert scope.project_id == "proj_from_db"
        assert scope.allowed_revisions == 10
        assert scope.used_revisions == 7
        # remaining_revisions is computed, not stored
        assert scope.remaining_revisions == 3


class TestRevisionDiff:
    """Tests for RevisionDiff model."""

    @pytest.fixture
    def sample_diff(self):
        """Create a sample revision diff."""
        return RevisionDiff(
            post_index=3,
            template_name="Problem Recognition",
            original_length=150,
            revised_length=180,
            word_count_change=30,
            changes=["Added stronger hook", "Expanded CTA", "Fixed typos"],
            improvement_score=0.85,
        )

    def test_revision_diff_creation(self, sample_diff):
        """Test basic revision diff creation."""
        assert sample_diff.post_index == 3
        assert sample_diff.template_name == "Problem Recognition"
        assert sample_diff.word_count_change == 30
        assert len(sample_diff.changes) == 3
        assert sample_diff.improvement_score == 0.85

    def test_to_markdown_full(self, sample_diff):
        """Test to_markdown with all fields."""
        md = sample_diff.to_markdown()

        assert "### Post #3: Problem Recognition" in md
        assert "**Length:** 150 → 180 words" in md
        assert "(+30 words)" in md
        assert "**Changes Made:**" in md
        assert "- Added stronger hook" in md
        assert "- Expanded CTA" in md
        assert "- Fixed typos" in md
        assert "**Quality Improvement:** 85%" in md

    def test_to_markdown_negative_change(self):
        """Test to_markdown with negative word count change."""
        diff = RevisionDiff(
            post_index=5,
            template_name="How-To",
            original_length=300,
            revised_length=250,
            word_count_change=-50,
            changes=["Condensed for clarity"],
        )

        md = diff.to_markdown()

        assert "(-50 words)" in md

    def test_to_markdown_no_changes(self):
        """Test to_markdown with empty changes list."""
        diff = RevisionDiff(
            post_index=1,
            template_name="Test",
            original_length=100,
            revised_length=100,
            word_count_change=0,
            changes=[],
        )

        md = diff.to_markdown()

        assert "**Changes Made:**" not in md

    def test_to_markdown_no_improvement_score(self):
        """Test to_markdown without improvement score."""
        diff = RevisionDiff(
            post_index=2,
            template_name="Statistic",
            original_length=120,
            revised_length=140,
            word_count_change=20,
            changes=["Updated statistics"],
            improvement_score=None,  # No score
        )

        md = diff.to_markdown()

        assert "**Quality Improvement:**" not in md

    def test_to_markdown_zero_improvement_score(self):
        """Test to_markdown with zero improvement score (falsy but valid)."""
        diff = RevisionDiff(
            post_index=4,
            template_name="Question",
            original_length=100,
            revised_length=100,
            word_count_change=0,
            changes=["Minor edits"],
            improvement_score=0.0,  # Zero is falsy but could be intentional
        )

        md = diff.to_markdown()

        # 0.0 is falsy so won't show
        assert "**Quality Improvement:**" not in md
