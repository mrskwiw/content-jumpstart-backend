"""Unit tests for src/models/project.py.

Covers:
- ProjectStatus and RevisionStatus enum membership and values
- Project model: creation, optional fields, to_dict / from_dict, serialization round trip
- RevisionPost model: creation, to_dict
- Revision model: creation, mark_completed / mark_failed, to_dict / from_dict
- RevisionScope model: all properties and methods, to_dict / from_dict
- RevisionDiff model: creation, to_markdown variations
- Validation: invalid enum values, field constraints
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models.project import (
    Project,
    ProjectStatus,
    Revision,
    RevisionDiff,
    RevisionPost,
    RevisionScope,
    RevisionStatus,
)


# ---------------------------------------------------------------------------
# ProjectStatus enum
# ---------------------------------------------------------------------------


class TestProjectStatus:
    """Tests for ProjectStatus enum."""

    def test_status_values(self):
        """All ProjectStatus members must have the documented string values."""
        assert ProjectStatus.IN_PROGRESS.value == "in_progress"
        assert ProjectStatus.COMPLETED.value == "completed"
        assert ProjectStatus.ARCHIVED.value == "archived"

    def test_status_is_str_enum(self):
        """ProjectStatus must be usable as a plain string."""
        assert ProjectStatus.COMPLETED == "completed"

    def test_all_status_members_present(self):
        """ProjectStatus must expose exactly the expected set of members."""
        expected = {"IN_PROGRESS", "COMPLETED", "ARCHIVED"}
        actual = {m.name for m in ProjectStatus}
        assert actual == expected

    def test_invalid_status_raises(self):
        """Constructing ProjectStatus from an unknown string must raise ValueError."""
        with pytest.raises(ValueError):
            ProjectStatus("nonexistent_status")


# ---------------------------------------------------------------------------
# RevisionStatus enum
# ---------------------------------------------------------------------------


class TestRevisionStatus:
    """Tests for RevisionStatus enum."""

    def test_revision_status_values(self):
        """All RevisionStatus members must have the documented string values."""
        assert RevisionStatus.PENDING.value == "pending"
        assert RevisionStatus.IN_PROGRESS.value == "in_progress"
        assert RevisionStatus.COMPLETED.value == "completed"
        assert RevisionStatus.FAILED.value == "failed"

    def test_all_revision_status_members_present(self):
        """RevisionStatus must expose exactly the expected set of members."""
        expected = {"PENDING", "IN_PROGRESS", "COMPLETED", "FAILED"}
        actual = {m.name for m in RevisionStatus}
        assert actual == expected

    def test_invalid_revision_status_raises(self):
        """Constructing RevisionStatus from an unknown string must raise ValueError."""
        with pytest.raises(ValueError):
            RevisionStatus("unknown")


# ---------------------------------------------------------------------------
# Project model
# ---------------------------------------------------------------------------


class TestProject:
    """Tests for the Project Pydantic model."""

    @pytest.fixture
    def sample_project(self) -> Project:
        """Return a fully populated Project for reuse across test methods."""
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
        """A Project created with all fields must store them correctly."""
        assert sample_project.project_id == "TestClient_20250115_120000"
        assert sample_project.client_name == "TestClient"
        assert sample_project.num_posts == 30
        assert sample_project.status == ProjectStatus.COMPLETED  # Default

    def test_project_default_status_is_completed(self):
        """Status must default to COMPLETED when not supplied."""
        project = Project(
            project_id="p1",
            client_name="C",
            deliverable_path="/d",
            num_posts=10,
        )
        assert project.status == ProjectStatus.COMPLETED

    def test_project_optional_fields_default_to_none(self):
        """brief_path, quality_profile_name, and notes must default to None."""
        project = Project(
            project_id="p2",
            client_name="C",
            deliverable_path="/d",
            num_posts=10,
        )
        assert project.brief_path is None
        assert project.quality_profile_name is None
        assert project.notes is None

    def test_project_created_at_is_datetime(self, sample_project):
        """created_at must be a datetime instance."""
        assert isinstance(sample_project.created_at, datetime)

    def test_project_to_dict(self, sample_project):
        """to_dict must return all fields with the correct types and values."""
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
        # created_at must be an ISO format string
        datetime.fromisoformat(result["created_at"])

    def test_project_to_dict_optional_none_fields(self):
        """to_dict must serialize None optional fields as None (not omit them)."""
        project = Project(
            project_id="p3",
            client_name="C",
            deliverable_path="/d",
            num_posts=5,
        )
        d = project.to_dict()
        assert "brief_path" in d
        assert d["brief_path"] is None
        assert "quality_profile_name" in d
        assert d["quality_profile_name"] is None
        assert "notes" in d
        assert d["notes"] is None

    def test_project_from_dict(self):
        """from_dict must deserialise a DB-style dict back to a Project."""
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

    def test_project_from_dict_archived_status(self):
        """from_dict must correctly handle the 'archived' status string."""
        data = {
            "project_id": "p4",
            "client_name": "C",
            "created_at": "2025-06-01T00:00:00",
            "deliverable_path": "/d",
            "brief_path": None,
            "num_posts": 30,
            "quality_profile_name": None,
            "status": "archived",
            "notes": None,
        }
        project = Project.from_dict(data)
        assert project.status == ProjectStatus.ARCHIVED

    def test_project_serialization_round_trip(self, sample_project):
        """to_dict -> from_dict must preserve every field."""
        data = sample_project.to_dict()
        restored = Project.from_dict(data)

        assert restored.project_id == sample_project.project_id
        assert restored.client_name == sample_project.client_name
        assert restored.deliverable_path == sample_project.deliverable_path
        assert restored.brief_path == sample_project.brief_path
        assert restored.num_posts == sample_project.num_posts
        assert restored.quality_profile_name == sample_project.quality_profile_name
        assert restored.status == sample_project.status
        assert restored.notes == sample_project.notes

    def test_project_in_progress_status_persists(self):
        """A Project with IN_PROGRESS status must round-trip correctly."""
        project = Project(
            project_id="p5",
            client_name="C",
            deliverable_path="/d",
            num_posts=30,
            status=ProjectStatus.IN_PROGRESS,
        )
        data = project.to_dict()
        assert data["status"] == "in_progress"
        restored = Project.from_dict(data)
        assert restored.status == ProjectStatus.IN_PROGRESS


# ---------------------------------------------------------------------------
# RevisionPost model
# ---------------------------------------------------------------------------


class TestRevisionPost:
    """Tests for the RevisionPost model."""

    @pytest.fixture
    def sample_revision_post(self) -> RevisionPost:
        """Return a fully populated RevisionPost."""
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
        """All fields must be stored with the correct values."""
        assert sample_revision_post.post_index == 5
        assert sample_revision_post.template_name == "Contrarian Take"
        assert sample_revision_post.original_word_count == 100
        assert sample_revision_post.revised_word_count == 120

    def test_revision_post_optional_changes_summary_defaults_none(self):
        """changes_summary must default to None when not supplied."""
        rp = RevisionPost(
            post_index=1,
            template_id=1,
            template_name="T",
            original_content="orig",
            original_word_count=50,
            revised_content="rev",
            revised_word_count=60,
        )
        assert rp.changes_summary is None

    def test_revision_post_to_dict(self, sample_revision_post):
        """to_dict must include revision_id and all model fields."""
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

    def test_revision_post_to_dict_none_changes_summary(self):
        """to_dict must include changes_summary as None when not set."""
        rp = RevisionPost(
            post_index=2,
            template_id=2,
            template_name="T2",
            original_content="x",
            original_word_count=10,
            revised_content="y",
            revised_word_count=12,
        )
        result = rp.to_dict("rev_456")
        assert result["changes_summary"] is None


# ---------------------------------------------------------------------------
# Revision model
# ---------------------------------------------------------------------------


class TestRevision:
    """Tests for the Revision model."""

    @pytest.fixture
    def sample_revision(self) -> Revision:
        """Return a pending Revision for reuse."""
        return Revision(
            revision_id="rev_20250115_120000",
            project_id="TestClient_20250110_080000",
            attempt_number=1,
            feedback="Please make the hook stronger.",
            cost=0.15,
        )

    def test_revision_creation(self, sample_revision):
        """Default status must be PENDING and completed_at must be None."""
        assert sample_revision.revision_id == "rev_20250115_120000"
        assert sample_revision.status == RevisionStatus.PENDING
        assert sample_revision.completed_at is None

    def test_revision_default_posts_list_empty(self, sample_revision):
        """The posts list must default to an empty list."""
        assert sample_revision.posts == []

    def test_revision_attempt_number_lower_bound(self):
        """attempt_number = 1 is the minimum valid value."""
        rev = Revision(
            revision_id="r1",
            project_id="p1",
            attempt_number=1,
            feedback="f",
        )
        assert rev.attempt_number == 1

    def test_revision_attempt_number_upper_bound(self):
        """attempt_number = 10 is the maximum valid value."""
        rev = Revision(
            revision_id="r10",
            project_id="p1",
            attempt_number=10,
            feedback="f",
        )
        assert rev.attempt_number == 10

    def test_revision_attempt_number_out_of_range_raises(self):
        """attempt_number outside [1, 10] must raise ValidationError."""
        with pytest.raises(ValidationError):
            Revision(
                revision_id="r0",
                project_id="p1",
                attempt_number=0,
                feedback="f",
            )
        with pytest.raises(ValidationError):
            Revision(
                revision_id="r11",
                project_id="p1",
                attempt_number=11,
                feedback="f",
            )

    def test_revision_to_dict(self, sample_revision):
        """to_dict must contain all stored fields with correct types."""
        result = sample_revision.to_dict()

        assert result["revision_id"] == "rev_20250115_120000"
        assert result["attempt_number"] == 1
        assert result["status"] == "pending"
        assert result["cost"] == 0.15
        assert result["completed_at"] is None
        datetime.fromisoformat(result["created_at"])

    def test_revision_to_dict_with_completed_at(self):
        """to_dict must serialise completed_at as an ISO string when set."""
        revision = Revision(
            revision_id="rev_c",
            project_id="p1",
            attempt_number=2,
            feedback="Fix typos",
            status=RevisionStatus.COMPLETED,
            completed_at=datetime(2025, 1, 15, 14, 30, 0),
        )
        result = revision.to_dict()
        assert result["completed_at"] == "2025-01-15T14:30:00"

    def test_revision_from_dict(self):
        """from_dict must reconstruct a Revision from a DB-style dict."""
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
        assert revision.posts == []

    def test_revision_from_dict_without_completed_at(self):
        """from_dict must accept None for completed_at."""
        data = {
            "revision_id": "rev_p",
            "project_id": "proj_p",
            "attempt_number": 1,
            "status": "pending",
            "feedback": "Pending",
            "created_at": "2025-01-15T09:00:00",
            "completed_at": None,
            "cost": 0.0,
        }
        revision = Revision.from_dict(data)
        assert revision.completed_at is None

    def test_mark_completed(self, sample_revision):
        """mark_completed must set status to COMPLETED and populate completed_at."""
        sample_revision.mark_completed()
        assert sample_revision.status == RevisionStatus.COMPLETED
        assert isinstance(sample_revision.completed_at, datetime)

    def test_mark_failed(self, sample_revision):
        """mark_failed must set status to FAILED and populate completed_at."""
        sample_revision.mark_failed()
        assert sample_revision.status == RevisionStatus.FAILED
        assert isinstance(sample_revision.completed_at, datetime)

    def test_mark_completed_sets_timestamp(self, sample_revision):
        """completed_at set by mark_completed must be close to now."""
        before = datetime.now()
        sample_revision.mark_completed()
        after = datetime.now()
        assert before <= sample_revision.completed_at <= after

    def test_revision_serialization_round_trip(self):
        """to_dict -> from_dict must preserve all fields for a completed revision."""
        rev = Revision(
            revision_id="rev_rt",
            project_id="proj_rt",
            attempt_number=5,
            feedback="Full round trip feedback",
            cost=0.42,
            status=RevisionStatus.FAILED,
            completed_at=datetime(2025, 5, 20, 11, 0, 0),
        )
        data = rev.to_dict()
        restored = Revision.from_dict(data)

        assert restored.revision_id == rev.revision_id
        assert restored.project_id == rev.project_id
        assert restored.attempt_number == rev.attempt_number
        assert restored.feedback == rev.feedback
        assert restored.cost == rev.cost
        assert restored.status == rev.status
        # completed_at is reconstructed from ISO string
        assert restored.completed_at == rev.completed_at


# ---------------------------------------------------------------------------
# RevisionScope model
# ---------------------------------------------------------------------------


class TestRevisionScope:
    """Tests for the RevisionScope model."""

    @pytest.fixture
    def sample_scope(self) -> RevisionScope:
        """Return a RevisionScope with 2 of 5 used."""
        return RevisionScope(
            project_id="proj_test",
            allowed_revisions=5,
            used_revisions=2,
        )

    def test_revision_scope_creation(self, sample_scope):
        """Default boolean flags must all be False."""
        assert sample_scope.scope_exceeded is False
        assert sample_scope.upsell_offered is False
        assert sample_scope.upsell_accepted is False

    def test_remaining_revisions(self, sample_scope):
        """remaining_revisions must return allowed - used."""
        assert sample_scope.remaining_revisions == 3

    def test_remaining_revisions_zero_at_limit(self):
        """remaining_revisions must return 0 when used equals allowed."""
        scope = RevisionScope(project_id="p", allowed_revisions=5, used_revisions=5)
        assert scope.remaining_revisions == 0

    def test_remaining_revisions_clamped_at_zero_when_exceeded(self):
        """remaining_revisions must return 0 (not negative) when over limit."""
        scope = RevisionScope(project_id="p", allowed_revisions=5, used_revisions=7)
        assert scope.remaining_revisions == 0

    def test_is_at_limit_false(self, sample_scope):
        """is_at_limit must be False when under limit."""
        assert sample_scope.is_at_limit is False

    def test_is_at_limit_true(self):
        """is_at_limit must be True when used equals allowed."""
        scope = RevisionScope(project_id="p", allowed_revisions=5, used_revisions=5)
        assert scope.is_at_limit is True

    def test_is_at_limit_true_when_exceeded(self):
        """is_at_limit must be True when used exceeds allowed."""
        scope = RevisionScope(project_id="p", allowed_revisions=5, used_revisions=6)
        assert scope.is_at_limit is True

    def test_is_near_limit_true(self):
        """is_near_limit must be True when exactly 1 revision remains."""
        scope = RevisionScope(project_id="p", allowed_revisions=5, used_revisions=4)
        assert scope.is_near_limit is True

    def test_is_near_limit_false_when_more_remain(self, sample_scope):
        """is_near_limit must be False when more than 1 revision remains."""
        assert sample_scope.is_near_limit is False

    def test_is_near_limit_false_at_exact_limit(self):
        """is_near_limit must be False when already at the limit (0 remaining)."""
        scope = RevisionScope(project_id="p", allowed_revisions=5, used_revisions=5)
        assert scope.is_near_limit is False

    def test_increment_usage(self, sample_scope):
        """increment_usage must increase used_revisions by 1."""
        sample_scope.increment_usage()
        assert sample_scope.used_revisions == 3
        assert sample_scope.scope_exceeded is False

    def test_increment_usage_sets_scope_exceeded(self):
        """increment_usage must set scope_exceeded when usage surpasses allowed."""
        scope = RevisionScope(project_id="p", allowed_revisions=5, used_revisions=5)
        scope.increment_usage()
        assert scope.scope_exceeded is True

    def test_add_revisions_after_upsell(self):
        """add_revisions must extend allowed_revisions and clear scope_exceeded."""
        scope = RevisionScope(
            project_id="p",
            allowed_revisions=5,
            used_revisions=5,
            scope_exceeded=True,
        )
        scope.add_revisions(3)
        assert scope.allowed_revisions == 8
        assert scope.scope_exceeded is False
        assert scope.upsell_accepted is True

    def test_add_revisions_increases_allowed(self):
        """add_revisions must increase allowed_revisions by the exact count supplied."""
        scope = RevisionScope(project_id="p", allowed_revisions=5, used_revisions=2)
        scope.add_revisions(5)
        assert scope.allowed_revisions == 10

    def test_to_dict(self, sample_scope):
        """to_dict must include the computed remaining_revisions field."""
        result = sample_scope.to_dict()
        assert result["project_id"] == "proj_test"
        assert result["allowed_revisions"] == 5
        assert result["used_revisions"] == 2
        assert result["remaining_revisions"] == 3
        assert result["scope_exceeded"] is False
        assert result["upsell_offered"] is False
        assert result["upsell_accepted"] is False

    def test_from_dict_strips_remaining_revisions(self):
        """from_dict must silently discard the computed remaining_revisions key."""
        data = {
            "project_id": "proj_from_db",
            "allowed_revisions": 10,
            "used_revisions": 7,
            "remaining_revisions": 3,
            "scope_exceeded": False,
            "upsell_offered": True,
            "upsell_accepted": False,
        }
        scope = RevisionScope.from_dict(data)
        assert scope.project_id == "proj_from_db"
        assert scope.remaining_revisions == 3  # re-computed from 10 - 7

    def test_revision_scope_serialization_round_trip(self, sample_scope):
        """to_dict -> from_dict must preserve all stored fields."""
        data = sample_scope.to_dict()
        restored = RevisionScope.from_dict(data)
        assert restored.project_id == sample_scope.project_id
        assert restored.allowed_revisions == sample_scope.allowed_revisions
        assert restored.used_revisions == sample_scope.used_revisions
        assert restored.scope_exceeded == sample_scope.scope_exceeded
        assert restored.upsell_offered == sample_scope.upsell_offered
        assert restored.upsell_accepted == sample_scope.upsell_accepted


# ---------------------------------------------------------------------------
# RevisionDiff model
# ---------------------------------------------------------------------------


class TestRevisionDiff:
    """Tests for the RevisionDiff model."""

    @pytest.fixture
    def sample_diff(self) -> RevisionDiff:
        """Return a fully populated RevisionDiff."""
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
        """All fields must be stored correctly."""
        assert sample_diff.post_index == 3
        assert sample_diff.template_name == "Problem Recognition"
        assert sample_diff.word_count_change == 30
        assert len(sample_diff.changes) == 3
        assert sample_diff.improvement_score == 0.85

    def test_revision_diff_optional_improvement_score_defaults_none(self):
        """improvement_score must default to None when not supplied."""
        diff = RevisionDiff(
            post_index=1,
            template_name="T",
            original_length=100,
            revised_length=100,
            word_count_change=0,
            changes=[],
        )
        assert diff.improvement_score is None

    def test_to_markdown_full(self, sample_diff):
        """to_markdown must include header, length change, changes list, and score."""
        md = sample_diff.to_markdown()

        assert "### Post #3: Problem Recognition" in md
        assert "**Length:** 150 → 180 words" in md
        assert "(+30 words)" in md
        assert "**Changes Made:**" in md
        assert "- Added stronger hook" in md
        assert "- Expanded CTA" in md
        assert "- Fixed typos" in md
        assert "**Quality Improvement:** 85%" in md

    def test_to_markdown_negative_word_count_change(self):
        """to_markdown must render a negative word_count_change with a minus sign."""
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

    def test_to_markdown_no_changes_list_omits_changes_section(self):
        """to_markdown must omit the '**Changes Made:**' section when changes is empty."""
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

    def test_to_markdown_none_improvement_score_omits_score_section(self):
        """to_markdown must not include the quality improvement line when score is None."""
        diff = RevisionDiff(
            post_index=2,
            template_name="Statistic",
            original_length=120,
            revised_length=140,
            word_count_change=20,
            changes=["Updated statistics"],
            improvement_score=None,
        )
        md = diff.to_markdown()
        assert "**Quality Improvement:**" not in md

    def test_to_markdown_zero_improvement_score_omits_score_section(self):
        """to_markdown omits the quality section when improvement_score is 0.0 (falsy)."""
        diff = RevisionDiff(
            post_index=4,
            template_name="Question",
            original_length=100,
            revised_length=100,
            word_count_change=0,
            changes=["Minor edits"],
            improvement_score=0.0,
        )
        md = diff.to_markdown()
        assert "**Quality Improvement:**" not in md

    def test_to_markdown_returns_string(self, sample_diff):
        """to_markdown must return a non-empty string."""
        md = sample_diff.to_markdown()
        assert isinstance(md, str)
        assert len(md) > 0

    def test_to_markdown_post_header_format(self, sample_diff):
        """The markdown header must follow the '### Post #N: Name' format."""
        md = sample_diff.to_markdown()
        assert md.startswith("### Post #3: Problem Recognition")

    def test_to_markdown_single_change(self):
        """to_markdown must render a single change item correctly."""
        diff = RevisionDiff(
            post_index=7,
            template_name="Single Change",
            original_length=80,
            revised_length=90,
            word_count_change=10,
            changes=["Only one edit"],
        )
        md = diff.to_markdown()
        assert "- Only one edit" in md

    def test_to_markdown_improvement_score_percentage_format(self):
        """Improvement score must be rendered as a rounded integer percentage."""
        diff = RevisionDiff(
            post_index=1,
            template_name="T",
            original_length=100,
            revised_length=110,
            word_count_change=10,
            changes=["edit"],
            improvement_score=0.735,  # Should display as 74%
        )
        md = diff.to_markdown()
        # 0.735 * 100 = 73.5 → rounds to 74
        assert "74%" in md
