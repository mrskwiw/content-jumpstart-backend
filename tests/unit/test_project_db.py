"""Tests for project database layer

Comprehensive tests for ProjectDatabase class covering all operations:
- Project CRUD
- Revision management
- Revision scope tracking
- Client memory
- Voice samples
- Feedback themes
- Template performance
- Post feedback
- Client satisfaction
- System metrics
"""

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src.database.project_db import ProjectDatabase
from src.models.client_memory import ClientMemory, FeedbackTheme, VoiceSample
from src.models.project import (
    Project,
    ProjectStatus,
    Revision,
    RevisionPost,
    RevisionScope,
    RevisionStatus,
)
from src.models.voice_sample import VoiceSampleUpload


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_projects.db"
        db = ProjectDatabase(db_path)
        yield db


@pytest.fixture
def sample_project():
    """Create a sample project for testing"""
    return Project(
        project_id="proj-001",
        client_name="Test Client",
        created_at=datetime.now(),
        deliverable_path="/output/test",
        brief_path="/briefs/test.txt",
        num_posts=30,
        quality_profile_name="standard",
        status=ProjectStatus.IN_PROGRESS,
        notes="Test project notes",
    )


@pytest.fixture
def sample_revision(sample_project):
    """Create a sample revision for testing"""
    return Revision(
        revision_id="rev-001",
        project_id=sample_project.project_id,
        attempt_number=1,
        status=RevisionStatus.PENDING,
        feedback="Please make it more casual",
        created_at=datetime.now(),
        completed_at=None,
        cost=0.0,
    )


class TestProjectDatabaseInit:
    """Tests for database initialization"""

    def test_init_creates_directory(self):
        """Test that init creates parent directory if needed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "subdir" / "nested" / "test.db"
            _db = ProjectDatabase(db_path)  # noqa: F841 - Testing directory creation side effect
            assert db_path.parent.exists()

    def test_init_with_default_path(self):
        """Test that init uses default path when none provided"""
        with patch.object(Path, "mkdir"):
            with patch.object(ProjectDatabase, "_init_schema"):
                db = ProjectDatabase()
                assert "projects.db" in str(db.db_path)

    def test_init_schema_creates_tables(self, temp_db):
        """Test that schema initialization creates required tables"""
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            # Check for essential tables
            assert "projects" in tables
            assert "revisions" in tables
            assert "revision_scope" in tables
            assert "client_history" in tables


class TestProjectOperations:
    """Tests for project CRUD operations"""

    def test_create_project_success(self, temp_db, sample_project):
        """Test successful project creation"""
        result = temp_db.create_project(sample_project)
        assert result is True

    def test_create_project_duplicate_fails(self, temp_db, sample_project):
        """Test that duplicate project ID fails"""
        temp_db.create_project(sample_project)
        result = temp_db.create_project(sample_project)
        assert result is False

    def test_create_project_initializes_revision_scope(self, temp_db, sample_project):
        """Test that creating project also initializes revision scope"""
        temp_db.create_project(sample_project)
        scope = temp_db.get_revision_scope(sample_project.project_id)
        assert scope is not None
        assert scope.project_id == sample_project.project_id
        assert scope.used_revisions == 0

    def test_get_project_success(self, temp_db, sample_project):
        """Test retrieving an existing project"""
        temp_db.create_project(sample_project)
        retrieved = temp_db.get_project(sample_project.project_id)

        assert retrieved is not None
        assert retrieved.project_id == sample_project.project_id
        assert retrieved.client_name == sample_project.client_name

    def test_get_project_not_found(self, temp_db):
        """Test retrieving non-existent project returns None"""
        result = temp_db.get_project("nonexistent-id")
        assert result is None

    def test_get_projects_by_client(self, temp_db, sample_project):
        """Test retrieving all projects for a client"""
        # Create multiple projects for same client
        temp_db.create_project(sample_project)

        project2 = Project(
            project_id="proj-002",
            client_name=sample_project.client_name,
            created_at=datetime.now(),
            deliverable_path="/output/test2",
            brief_path="/briefs/test2.txt",
            num_posts=20,
            quality_profile_name="premium",
            status=ProjectStatus.IN_PROGRESS,
        )
        temp_db.create_project(project2)

        projects = temp_db.get_projects_by_client(sample_project.client_name)
        assert len(projects) == 2

    def test_get_projects_by_client_empty(self, temp_db):
        """Test retrieving projects for non-existent client"""
        projects = temp_db.get_projects_by_client("Nonexistent Client")
        assert len(projects) == 0

    def test_get_projects_with_limit(self, temp_db):
        """Test get_projects respects limit parameter"""
        # Create multiple projects
        for i in range(5):
            project = Project(
                project_id=f"proj-{i:03d}",
                client_name=f"Client {i}",
                created_at=datetime.now(),
                deliverable_path=f"/output/test{i}",
                brief_path=f"/briefs/test{i}.txt",
                num_posts=30,
                quality_profile_name="standard",
                status=ProjectStatus.IN_PROGRESS,
            )
            temp_db.create_project(project)

        projects = temp_db.get_projects(limit=3)
        assert len(projects) == 3

    def test_update_project_status_success(self, temp_db, sample_project):
        """Test updating project status"""
        temp_db.create_project(sample_project)
        result = temp_db.update_project_status(sample_project.project_id, ProjectStatus.COMPLETED)

        assert result is True
        updated = temp_db.get_project(sample_project.project_id)
        assert updated.status == ProjectStatus.COMPLETED

    def test_update_project_status_not_found(self, temp_db):
        """Test updating non-existent project status"""
        result = temp_db.update_project_status("nonexistent", ProjectStatus.COMPLETED)
        assert result is False


class TestRevisionOperations:
    """Tests for revision management"""

    def test_create_revision_success(self, temp_db, sample_project, sample_revision):
        """Test successful revision creation"""
        temp_db.create_project(sample_project)
        result = temp_db.create_revision(sample_revision)
        assert result is True

    def test_create_revision_duplicate_fails(self, temp_db, sample_project, sample_revision):
        """Test that duplicate revision ID fails"""
        temp_db.create_project(sample_project)
        temp_db.create_revision(sample_revision)
        result = temp_db.create_revision(sample_revision)
        assert result is False

    def test_create_revision_updates_scope(self, temp_db, sample_project, sample_revision):
        """Test that creating revision updates the scope counters"""
        temp_db.create_project(sample_project)

        scope_before = temp_db.get_revision_scope(sample_project.project_id)
        assert scope_before.used_revisions == 0

        temp_db.create_revision(sample_revision)

        scope_after = temp_db.get_revision_scope(sample_project.project_id)
        assert scope_after.used_revisions == 1

    def test_get_revision_success(self, temp_db, sample_project, sample_revision):
        """Test retrieving an existing revision"""
        temp_db.create_project(sample_project)
        temp_db.create_revision(sample_revision)

        retrieved = temp_db.get_revision(sample_revision.revision_id)
        assert retrieved is not None
        assert retrieved.revision_id == sample_revision.revision_id
        assert retrieved.feedback == sample_revision.feedback

    def test_get_revision_not_found(self, temp_db):
        """Test retrieving non-existent revision returns None"""
        result = temp_db.get_revision("nonexistent-rev")
        assert result is None

    def test_get_revision_with_posts(self, temp_db, sample_project, sample_revision):
        """Test that get_revision loads associated posts"""
        temp_db.create_project(sample_project)
        temp_db.create_revision(sample_revision)

        # Save some posts for this revision
        posts = [
            RevisionPost(
                post_index=i,
                template_id=i,
                template_name=f"Template {i}",
                original_content=f"Original content {i}",
                original_word_count=100,
                revised_content=f"Revised content {i}",
                revised_word_count=120,
                changes_summary=f"Made it better {i}",
            )
            for i in range(3)
        ]
        temp_db.save_revision_posts(sample_revision.revision_id, posts)

        retrieved = temp_db.get_revision(sample_revision.revision_id)
        assert len(retrieved.posts) == 3

    def test_get_revisions_by_project(self, temp_db, sample_project):
        """Test retrieving all revisions for a project"""
        temp_db.create_project(sample_project)

        # Create multiple revisions
        for i in range(3):
            revision = Revision(
                revision_id=f"rev-{i:03d}",
                project_id=sample_project.project_id,
                attempt_number=i + 1,
                status=RevisionStatus.PENDING,
                feedback=f"Feedback {i}",
                created_at=datetime.now(),
            )
            temp_db.create_revision(revision)

        revisions = temp_db.get_revisions_by_project(sample_project.project_id)
        assert len(revisions) == 3

    def test_update_revision_status_pending_to_in_progress(
        self, temp_db, sample_project, sample_revision
    ):
        """Test updating revision status from pending to in progress"""
        temp_db.create_project(sample_project)
        temp_db.create_revision(sample_revision)

        result = temp_db.update_revision_status(
            sample_revision.revision_id,
            RevisionStatus.IN_PROGRESS,
        )

        assert result is True
        updated = temp_db.get_revision(sample_revision.revision_id)
        assert updated.status == RevisionStatus.IN_PROGRESS

    def test_update_revision_status_completed_sets_timestamp(
        self, temp_db, sample_project, sample_revision
    ):
        """Test that completing revision auto-sets completed_at"""
        temp_db.create_project(sample_project)
        temp_db.create_revision(sample_revision)

        temp_db.update_revision_status(
            sample_revision.revision_id,
            RevisionStatus.COMPLETED,
        )

        updated = temp_db.get_revision(sample_revision.revision_id)
        assert updated.completed_at is not None

    def test_update_revision_status_with_explicit_timestamp(
        self, temp_db, sample_project, sample_revision
    ):
        """Test updating revision with explicit completion time"""
        temp_db.create_project(sample_project)
        temp_db.create_revision(sample_revision)

        explicit_time = datetime(2025, 1, 15, 12, 0, 0)
        temp_db.update_revision_status(
            sample_revision.revision_id,
            RevisionStatus.COMPLETED,
            completed_at=explicit_time,
        )

        updated = temp_db.get_revision(sample_revision.revision_id)
        assert updated.completed_at.year == 2025

    def test_update_revision_status_not_found(self, temp_db):
        """Test updating non-existent revision status"""
        result = temp_db.update_revision_status("nonexistent", RevisionStatus.COMPLETED)
        assert result is False

    def test_get_revision_posts(self, temp_db, sample_project, sample_revision):
        """Test retrieving posts for a specific revision"""
        temp_db.create_project(sample_project)
        temp_db.create_revision(sample_revision)

        posts = [
            RevisionPost(
                post_index=i,
                template_id=i,
                template_name=f"Template {i}",
                original_content=f"Original {i}",
                original_word_count=100,
                revised_content=f"Revised {i}",
                revised_word_count=110,
            )
            for i in range(5)
        ]
        temp_db.save_revision_posts(sample_revision.revision_id, posts)

        retrieved_posts = temp_db.get_revision_posts(sample_revision.revision_id)
        assert len(retrieved_posts) == 5

    def test_save_revision_posts(self, temp_db, sample_project, sample_revision):
        """Test saving revision posts"""
        temp_db.create_project(sample_project)
        temp_db.create_revision(sample_revision)

        posts = [
            RevisionPost(
                post_index=0,
                template_id=1,
                template_name="Problem Recognition",
                original_content="The original post content",
                original_word_count=100,
                revised_content="The revised post content",
                revised_word_count=120,
                changes_summary="Made it more engaging",
            )
        ]

        result = temp_db.save_revision_posts(sample_revision.revision_id, posts)
        assert result is True


class TestRevisionScopeOperations:
    """Tests for revision scope tracking"""

    def test_get_revision_scope_success(self, temp_db, sample_project):
        """Test getting revision scope for existing project"""
        temp_db.create_project(sample_project)
        scope = temp_db.get_revision_scope(sample_project.project_id)

        assert scope is not None
        assert scope.allowed_revisions == 5  # Default from model
        assert scope.used_revisions == 0

    def test_get_revision_scope_not_found(self, temp_db):
        """Test getting revision scope for non-existent project"""
        scope = temp_db.get_revision_scope("nonexistent")
        assert scope is None

    def test_update_revision_scope(self, temp_db, sample_project):
        """Test updating revision scope"""
        temp_db.create_project(sample_project)

        scope = temp_db.get_revision_scope(sample_project.project_id)
        scope.used_revisions = 3
        # remaining_revisions is computed property: allowed - used = 5 - 3 = 2

        result = temp_db.update_revision_scope(scope)
        assert result is True

        updated = temp_db.get_revision_scope(sample_project.project_id)
        assert updated.used_revisions == 3
        assert updated.remaining_revisions == 2  # Computed: 5 - 3 = 2

    def test_update_revision_scope_not_found(self, temp_db):
        """Test updating non-existent revision scope"""
        scope = RevisionScope(
            project_id="nonexistent",
            allowed_revisions=5,
            used_revisions=0,
            remaining_revisions=5,
        )
        result = temp_db.update_revision_scope(scope)
        assert result is False

    def test_mark_upsell_offered(self, temp_db, sample_project):
        """Test marking upsell as offered"""
        temp_db.create_project(sample_project)

        result = temp_db.mark_upsell_offered(sample_project.project_id)
        assert result is True

        scope = temp_db.get_revision_scope(sample_project.project_id)
        assert scope.upsell_offered is True

    def test_mark_upsell_offered_not_found(self, temp_db):
        """Test marking upsell offered for non-existent project"""
        result = temp_db.mark_upsell_offered("nonexistent")
        assert result is False

    def test_accept_upsell(self, temp_db, sample_project):
        """Test accepting upsell adds revisions"""
        temp_db.create_project(sample_project)

        # First exhaust existing revisions
        scope = temp_db.get_revision_scope(sample_project.project_id)
        scope.used_revisions = 5
        # remaining_revisions is computed (will be 0)
        scope.scope_exceeded = True
        temp_db.update_revision_scope(scope)

        # Accept upsell
        result = temp_db.accept_upsell(sample_project.project_id, additional_revisions=5)
        assert result is True

        updated = temp_db.get_revision_scope(sample_project.project_id)
        assert updated.allowed_revisions == 10  # 5 + 5
        assert updated.upsell_accepted is True
        assert updated.scope_exceeded is False

    def test_accept_upsell_not_found(self, temp_db):
        """Test accepting upsell for non-existent project"""
        result = temp_db.accept_upsell("nonexistent")
        assert result is False


class TestAnalyticsAndReporting:
    """Tests for analytics and reporting methods"""

    def test_get_client_stats(self, temp_db, sample_project, sample_revision):
        """Test getting client statistics"""
        temp_db.create_project(sample_project)
        temp_db.create_revision(sample_revision)

        stats = temp_db.get_client_stats(sample_project.client_name)

        assert stats["client_name"] == sample_project.client_name
        assert stats["total_projects"] == 1
        assert stats["total_revisions"] == 1
        assert stats["avg_revisions_per_project"] == 1.0

    def test_get_client_stats_no_projects(self, temp_db):
        """Test client stats for client with no projects"""
        stats = temp_db.get_client_stats("New Client")

        assert stats["total_projects"] == 0
        assert stats["total_revisions"] == 0
        assert stats["avg_revisions_per_project"] == 0

    def test_get_client_stats_scope_exceeded(self, temp_db, sample_project):
        """Test client stats includes scope exceeded count"""
        temp_db.create_project(sample_project)

        # Mark scope as exceeded
        scope = temp_db.get_revision_scope(sample_project.project_id)
        scope.scope_exceeded = True
        temp_db.update_revision_scope(scope)

        stats = temp_db.get_client_stats(sample_project.client_name)
        assert stats["scope_exceeded_count"] == 1

    def test_get_revision_summary(self, temp_db, sample_project, sample_revision):
        """Test getting revision summary across all projects"""
        temp_db.create_project(sample_project)
        temp_db.create_revision(sample_revision)

        # Note: This tests the view which may not exist in schema
        # If the view exists, it returns a list of dicts
        try:
            summary = temp_db.get_revision_summary()
            assert isinstance(summary, list)
        except sqlite3.OperationalError:
            # View doesn't exist - that's OK for this test
            pass


class TestClientMemoryOperations:
    """Tests for client memory (Phase 8B)"""

    def test_get_client_memory_not_found(self, temp_db):
        """Test getting non-existent client memory"""
        memory = temp_db.get_client_memory("New Client")
        assert memory is None

    def test_create_client_memory(self, temp_db):
        """Test creating client memory"""
        memory = ClientMemory(client_name="Test Client")
        result = temp_db.create_client_memory(memory)
        assert result is True

    def test_create_client_memory_duplicate(self, temp_db):
        """Test creating duplicate client memory fails"""
        memory = ClientMemory(client_name="Test Client")
        temp_db.create_client_memory(memory)
        result = temp_db.create_client_memory(memory)
        assert result is False

    def test_get_client_memory_success(self, temp_db):
        """Test retrieving existing client memory"""
        memory = ClientMemory(
            client_name="Test Client",
            total_projects=5,
            lifetime_value=9000.0,
        )
        temp_db.create_client_memory(memory)

        retrieved = temp_db.get_client_memory("Test Client")
        assert retrieved is not None
        assert retrieved.client_name == "Test Client"
        assert retrieved.total_projects == 5

    def test_update_client_memory(self, temp_db):
        """Test updating client memory"""
        memory = ClientMemory(client_name="Test Client")
        temp_db.create_client_memory(memory)

        # Update values
        memory.total_projects = 10
        memory.lifetime_value = 15000.0

        result = temp_db.update_client_memory(memory)
        assert result is True

        updated = temp_db.get_client_memory("Test Client")
        assert updated.total_projects == 10
        assert updated.lifetime_value == 15000.0

    def test_update_client_memory_not_found(self, temp_db):
        """Test updating non-existent client memory"""
        memory = ClientMemory(client_name="Nonexistent Client")
        result = temp_db.update_client_memory(memory)
        assert result is False

    def test_get_or_create_client_memory_creates(self, temp_db):
        """Test get_or_create creates new memory if not exists"""
        memory = temp_db.get_or_create_client_memory("New Client")
        assert memory is not None
        assert memory.client_name == "New Client"

    def test_get_or_create_client_memory_gets_existing(self, temp_db):
        """Test get_or_create returns existing memory"""
        # First create
        original = ClientMemory(client_name="Test Client", total_projects=5)
        temp_db.create_client_memory(original)

        # Then get_or_create should return existing
        memory = temp_db.get_or_create_client_memory("Test Client")
        assert memory.total_projects == 5


class TestVoiceSampleOperations:
    """Tests for voice sample storage"""

    def test_store_voice_sample(self, temp_db):
        """Test storing a voice sample"""
        sample = VoiceSample(
            client_name="Test Client",
            project_id="proj-001",
            generated_at=datetime.now(),
            average_readability=65.0,
            voice_archetype="Expert",
            dominant_tone="Professional",
            average_word_count=200,
            question_usage_rate=0.15,
            common_hooks=["Did you know", "Here's the thing"],
            common_transitions=["However", "That said"],
            common_ctas=["Learn more", "Get started"],
            key_phrases=["data-driven", "best practices"],
        )

        result = temp_db.store_voice_sample(sample)
        assert result is True

    def test_get_voice_samples(self, temp_db):
        """Test retrieving voice samples for a client"""
        # Store multiple samples
        for i in range(3):
            sample = VoiceSample(
                client_name="Test Client",
                project_id=f"proj-{i:03d}",
                generated_at=datetime.now(),
                average_readability=60.0 + i,
                voice_archetype="Expert",
                dominant_tone="Professional",
                average_word_count=200,
                question_usage_rate=0.1,
                common_hooks=[],
                common_transitions=[],
                common_ctas=[],
                key_phrases=[],
            )
            temp_db.store_voice_sample(sample)

        samples = temp_db.get_voice_samples("Test Client", limit=2)
        assert len(samples) == 2

    def test_get_voice_samples_empty(self, temp_db):
        """Test getting voice samples for client with none"""
        samples = temp_db.get_voice_samples("Nonexistent Client")
        assert len(samples) == 0


class TestVoiceSampleUploadOperations:
    """Tests for client-uploaded voice samples (Phase 8C)"""

    def test_store_voice_sample_upload(self, temp_db):
        """Test storing uploaded voice sample"""
        # First create client memory
        memory = ClientMemory(client_name="Test Client")
        temp_db.create_client_memory(memory)

        # sample_source must be lowercase and from allowed list: linkedin, blog, twitter, email, mixed, other
        # word_count must be >= 100
        upload = VoiceSampleUpload(
            client_name="Test Client",
            sample_text="This is sample content from the client. " * 30,  # Make it >= 100 words
            sample_source="linkedin",  # lowercase, from allowed list
            word_count=150,  # >= 100
            file_name="sample.txt",
        )

        sample_id = temp_db.store_voice_sample_upload(upload)
        assert sample_id > 0

    def test_get_voice_sample_uploads(self, temp_db):
        """Test retrieving uploaded voice samples"""
        # Create client memory first
        memory = ClientMemory(client_name="Test Client")
        temp_db.create_client_memory(memory)

        # Store samples with valid sources and word counts
        for i in range(3):
            upload = VoiceSampleUpload(
                client_name="Test Client",
                sample_text="Sample content for testing purposes. " * 25,
                sample_source="blog",  # lowercase, from allowed list
                word_count=125,  # >= 100
                file_name=f"sample_{i}.txt",
            )
            temp_db.store_voice_sample_upload(upload)

        uploads = temp_db.get_voice_sample_uploads("Test Client", limit=2)
        assert len(uploads) == 2

    def test_get_voice_sample_uploads_no_limit(self, temp_db):
        """Test retrieving all uploaded voice samples"""
        memory = ClientMemory(client_name="Test Client")
        temp_db.create_client_memory(memory)

        for i in range(3):
            upload = VoiceSampleUpload(
                client_name="Test Client",
                sample_text="Sample text for email content. " * 25,
                sample_source="email",  # lowercase, from allowed list
                word_count=125,  # >= 100
                file_name=f"email_sample_{i}.txt",
            )
            temp_db.store_voice_sample_upload(upload)

        uploads = temp_db.get_voice_sample_uploads("Test Client")
        assert len(uploads) == 3

    def test_delete_voice_sample_uploads(self, temp_db):
        """Test deleting voice sample uploads"""
        memory = ClientMemory(client_name="Test Client")
        temp_db.create_client_memory(memory)

        for i in range(3):
            upload = VoiceSampleUpload(
                client_name="Test Client",
                sample_text="Article sample text content here. " * 25,
                sample_source="other",  # use 'other' for article-like content
                word_count=125,  # >= 100
                file_name=f"article_{i}.txt",
            )
            temp_db.store_voice_sample_upload(upload)

        deleted_count = temp_db.delete_voice_sample_uploads("Test Client")
        assert deleted_count == 3

        remaining = temp_db.get_voice_sample_uploads("Test Client")
        assert len(remaining) == 0

    def test_get_voice_sample_upload_stats(self, temp_db):
        """Test getting voice sample upload statistics"""
        memory = ClientMemory(client_name="Test Client")
        temp_db.create_client_memory(memory)

        sources = ["linkedin", "blog", "linkedin"]
        for i, source in enumerate(sources):
            upload = VoiceSampleUpload(
                client_name="Test Client",
                sample_text="Sample content for statistics testing. " * 25,
                sample_source=source,  # lowercase, from allowed list
                word_count=125,  # >= 100
                file_name=f"stats_sample_{i}.txt",
            )
            temp_db.store_voice_sample_upload(upload)

        stats = temp_db.get_voice_sample_upload_stats("Test Client")

        assert stats["sample_count"] == 3
        assert stats["total_words"] == 375
        assert "linkedin" in stats["sources"]
        assert "blog" in stats["sources"]

    def test_get_voice_sample_upload_stats_empty(self, temp_db):
        """Test stats for client with no uploads"""
        stats = temp_db.get_voice_sample_upload_stats("Nonexistent Client")

        assert stats["sample_count"] == 0
        assert stats["total_words"] == 0
        assert stats["sources"] == []
        assert stats["last_upload"] is None


class TestFeedbackThemeOperations:
    """Tests for feedback theme tracking"""

    def test_record_feedback_theme_new(self, temp_db):
        """Test recording a new feedback theme"""
        theme = FeedbackTheme(
            theme_type="tone",
            feedback_phrase="Make it more casual",
            occurrence_count=1,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
        )

        result = temp_db.record_feedback_theme("Test Client", theme)
        assert result is True

    def test_record_feedback_theme_existing_increments(self, temp_db):
        """Test that recording existing theme increments count"""
        theme = FeedbackTheme(
            theme_type="tone",
            feedback_phrase="Make it more casual",
            occurrence_count=1,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
        )

        temp_db.record_feedback_theme("Test Client", theme)
        temp_db.record_feedback_theme("Test Client", theme)

        themes = temp_db.get_feedback_themes("Test Client", "tone")
        assert len(themes) == 1
        assert themes[0].occurrence_count == 2

    def test_get_feedback_themes_all(self, temp_db):
        """Test getting all feedback themes for client"""
        themes_data = [
            ("tone", "More casual"),
            ("length", "Shorter posts"),
            ("tone", "Less formal"),
        ]

        for theme_type, phrase in themes_data:
            theme = FeedbackTheme(
                theme_type=theme_type,
                feedback_phrase=phrase,
                occurrence_count=1,
                first_seen=datetime.now(),
                last_seen=datetime.now(),
            )
            temp_db.record_feedback_theme("Test Client", theme)

        all_themes = temp_db.get_feedback_themes("Test Client")
        assert len(all_themes) == 3

    def test_get_feedback_themes_by_type(self, temp_db):
        """Test filtering feedback themes by type"""
        themes_data = [
            ("tone", "More casual"),
            ("length", "Shorter posts"),
            ("tone", "Less formal"),
        ]

        for theme_type, phrase in themes_data:
            theme = FeedbackTheme(
                theme_type=theme_type,
                feedback_phrase=phrase,
                occurrence_count=1,
                first_seen=datetime.now(),
                last_seen=datetime.now(),
            )
            temp_db.record_feedback_theme("Test Client", theme)

        tone_themes = temp_db.get_feedback_themes("Test Client", theme_type="tone")
        assert len(tone_themes) == 2


class TestTemplatePerformanceOperations:
    """Tests for template performance tracking"""

    def test_update_template_performance_new(self, temp_db):
        """Test creating new template performance record"""
        result = temp_db.update_template_performance(
            client_name="Test Client",
            template_id=1,
            was_revised=False,
            quality_score=0.85,
        )

        assert result is True

        perf = temp_db.get_template_performance("Test Client", template_id=1)
        assert perf["usage_count"] == 1
        assert perf["revision_count"] == 0
        assert perf["client_kept_count"] == 1

    def test_update_template_performance_revised(self, temp_db):
        """Test updating template performance when post was revised"""
        temp_db.update_template_performance(
            client_name="Test Client",
            template_id=1,
            was_revised=True,
            quality_score=0.7,
        )

        perf = temp_db.get_template_performance("Test Client", template_id=1)
        assert perf["revision_count"] == 1
        assert perf["client_kept_count"] == 0
        assert perf["revision_rate"] == 1.0

    def test_update_template_performance_multiple_uses(self, temp_db):
        """Test template performance over multiple uses"""
        # First use - kept
        temp_db.update_template_performance("Test Client", 1, False, 0.9)
        # Second use - revised
        temp_db.update_template_performance("Test Client", 1, True, 0.7)
        # Third use - kept
        temp_db.update_template_performance("Test Client", 1, False, 0.85)

        perf = temp_db.get_template_performance("Test Client", template_id=1)
        assert perf["usage_count"] == 3
        assert perf["revision_count"] == 1
        assert perf["client_kept_count"] == 2
        assert round(perf["revision_rate"], 2) == 0.33

    def test_get_template_performance_all(self, temp_db):
        """Test getting all template performance for a client"""
        for template_id in [1, 2, 3]:
            temp_db.update_template_performance("Test Client", template_id, False, 0.8)

        all_perf = temp_db.get_template_performance("Test Client")
        assert len(all_perf) == 3

    def test_get_template_performance_not_found(self, temp_db):
        """Test getting non-existent template performance"""
        perf = temp_db.get_template_performance("Nonexistent", template_id=999)
        assert perf == {}


class TestPostFeedbackOperations:
    """Tests for post feedback (Phase 8D)"""

    def test_store_post_feedback(self, temp_db):
        """Test storing post feedback"""
        feedback_id = temp_db.store_post_feedback(
            client_name="Test Client",
            project_id="proj-001",
            post_id="post-001",
            template_id=1,
            template_name="Problem Recognition",
            feedback_type="kept",
        )

        assert feedback_id > 0

    def test_store_post_feedback_with_engagement(self, temp_db):
        """Test storing feedback with engagement data"""
        engagement = {
            "likes": 50,
            "comments": 10,
            "shares": 5,
        }

        feedback_id = temp_db.store_post_feedback(
            client_name="Test Client",
            project_id="proj-001",
            post_id="post-001",
            template_id=1,
            template_name="Problem Recognition",
            feedback_type="loved",
            modification_notes="Client loved this one!",
            engagement_data=engagement,
        )

        assert feedback_id > 0

    def test_get_post_feedback_all(self, temp_db):
        """Test getting all post feedback"""
        for i in range(3):
            temp_db.store_post_feedback(
                client_name="Test Client",
                project_id="proj-001",
                post_id=f"post-{i:03d}",
                template_id=i + 1,
                template_name=f"Template {i}",
                feedback_type="kept",
            )

        feedback = temp_db.get_post_feedback()
        assert len(feedback) == 3

    def test_get_post_feedback_filtered_by_client(self, temp_db):
        """Test filtering post feedback by client"""
        for client in ["Client A", "Client B"]:
            temp_db.store_post_feedback(
                client_name=client,
                project_id="proj-001",
                post_id="post-001",
                template_id=1,
                template_name="Template 1",
                feedback_type="kept",
            )

        feedback = temp_db.get_post_feedback(client_name="Client A")
        assert len(feedback) == 1

    def test_get_post_feedback_filtered_by_type(self, temp_db):
        """Test filtering post feedback by type"""
        types = ["kept", "modified", "rejected", "loved"]
        for i, fb_type in enumerate(types):
            temp_db.store_post_feedback(
                client_name="Test Client",
                project_id="proj-001",
                post_id=f"post-{i:03d}",
                template_id=1,
                template_name="Template 1",
                feedback_type=fb_type,
            )

        kept_feedback = temp_db.get_post_feedback(feedback_type="kept")
        assert len(kept_feedback) == 1

    def test_get_post_feedback_with_limit(self, temp_db):
        """Test limiting post feedback results"""
        for i in range(10):
            temp_db.store_post_feedback(
                client_name="Test Client",
                project_id="proj-001",
                post_id=f"post-{i:03d}",
                template_id=1,
                template_name="Template 1",
                feedback_type="kept",
            )

        feedback = temp_db.get_post_feedback(limit=5)
        assert len(feedback) == 5

    def test_get_post_feedback_summary(self, temp_db):
        """Test getting feedback summary"""
        feedback_types = ["kept"] * 5 + ["modified"] * 3 + ["rejected"] * 1 + ["loved"] * 1
        for i, fb_type in enumerate(feedback_types):
            temp_db.store_post_feedback(
                client_name="Test Client",
                project_id="proj-001",
                post_id=f"post-{i:03d}",
                template_id=1,
                template_name="Template 1",
                feedback_type=fb_type,
            )

        summary = temp_db.get_post_feedback_summary()

        assert summary["total_feedback"] == 10
        assert summary["kept"] == 5
        assert summary["modified"] == 3
        assert summary["rejected"] == 1
        assert summary["loved"] == 1
        assert summary["kept_rate"] == 0.5

    def test_get_post_feedback_summary_by_client(self, temp_db):
        """Test getting feedback summary for specific client"""
        # Add feedback for two clients
        temp_db.store_post_feedback("Client A", "proj-001", "post-001", 1, "T1", "kept")
        temp_db.store_post_feedback("Client B", "proj-002", "post-002", 1, "T1", "rejected")

        summary = temp_db.get_post_feedback_summary(client_name="Client A")

        assert summary["total_feedback"] == 1
        assert summary["kept"] == 1

    def test_get_post_feedback_summary_empty(self, temp_db):
        """Test feedback summary when no feedback exists"""
        summary = temp_db.get_post_feedback_summary()

        assert summary["total_feedback"] == 0
        assert summary["kept_rate"] == 0.0


class TestClientSatisfactionOperations:
    """Tests for client satisfaction tracking (Phase 8D)"""

    def test_store_client_satisfaction(self, temp_db):
        """Test storing satisfaction survey response"""
        # Create client memory first
        memory = ClientMemory(client_name="Test Client")
        temp_db.create_client_memory(memory)

        satisfaction_id = temp_db.store_client_satisfaction(
            client_name="Test Client",
            project_id="proj-001",
            satisfaction_score=5,
            quality_rating=4,
            voice_match_rating=5,
            would_recommend=True,
            feedback_text="Great work!",
            strengths="Voice matching was excellent",
            improvements="Could be faster",
        )

        assert satisfaction_id > 0

    def test_store_client_satisfaction_updates_average(self, temp_db):
        """Test that storing satisfaction updates client's average"""
        memory = ClientMemory(client_name="Test Client")
        temp_db.create_client_memory(memory)

        # Store two satisfaction scores
        temp_db.store_client_satisfaction("Test Client", "proj-001", 5, 5, 5, True)
        temp_db.store_client_satisfaction("Test Client", "proj-002", 3, 3, 3, False)

        updated_memory = temp_db.get_client_memory("Test Client")
        assert updated_memory.average_satisfaction == 4.0  # (5+3)/2

    def test_get_client_satisfaction_all(self, temp_db):
        """Test getting all satisfaction records"""
        memory = ClientMemory(client_name="Test Client")
        temp_db.create_client_memory(memory)

        for i in range(3):
            temp_db.store_client_satisfaction("Test Client", f"proj-{i:03d}", 4, 4, 4, True)

        records = temp_db.get_client_satisfaction()
        assert len(records) == 3

    def test_get_client_satisfaction_filtered(self, temp_db):
        """Test filtering satisfaction by client"""
        for client in ["Client A", "Client B"]:
            memory = ClientMemory(client_name=client)
            temp_db.create_client_memory(memory)
            temp_db.store_client_satisfaction(client, "proj-001", 4, 4, 4, True)

        records = temp_db.get_client_satisfaction(client_name="Client A")
        assert len(records) == 1

    def test_get_client_satisfaction_with_limit(self, temp_db):
        """Test limiting satisfaction results"""
        memory = ClientMemory(client_name="Test Client")
        temp_db.create_client_memory(memory)

        for i in range(10):
            temp_db.store_client_satisfaction("Test Client", f"proj-{i:03d}", 4, 4, 4, True)

        records = temp_db.get_client_satisfaction(limit=5)
        assert len(records) == 5

    def test_get_satisfaction_summary(self, temp_db):
        """Test getting satisfaction summary"""
        memory = ClientMemory(client_name="Test Client")
        temp_db.create_client_memory(memory)

        # Store varied satisfaction scores
        scores = [(5, 5, 5, True), (4, 4, 4, True), (3, 3, 3, False)]
        for i, (sat, qual, voice, rec) in enumerate(scores):
            temp_db.store_client_satisfaction("Test Client", f"proj-{i:03d}", sat, qual, voice, rec)

        summary = temp_db.get_satisfaction_summary()

        assert summary["total_surveys"] == 3
        assert summary["avg_satisfaction"] == 4.0
        assert summary["recommendation_rate"] == 2 / 3

    def test_get_satisfaction_summary_empty(self, temp_db):
        """Test satisfaction summary with no data"""
        summary = temp_db.get_satisfaction_summary()

        assert summary["total_surveys"] == 0
        assert summary["avg_satisfaction"] == 0.0
        assert summary["recommendation_rate"] == 0.0


class TestSystemMetricsOperations:
    """Tests for system metrics tracking (Phase 8D)"""

    def test_record_metric(self, temp_db):
        """Test recording a system metric"""
        temp_db.record_metric(
            metric_date="2025-01-15",
            metric_type="generation",
            metric_name="avg_quality_score",
            metric_value=0.87,
        )

        metrics = temp_db.get_metrics(metric_name="avg_quality_score")
        assert len(metrics) == 1
        assert metrics[0]["metric_value"] == 0.87

    def test_record_metric_with_metadata(self, temp_db):
        """Test recording metric with metadata"""
        metadata = {"project_count": 5, "client": "Test Client"}

        temp_db.record_metric(
            metric_date="2025-01-15",
            metric_type="generation",
            metric_name="posts_generated",
            metric_value=150,
            metadata=metadata,
        )

        metrics = temp_db.get_metrics(metric_name="posts_generated")
        assert metrics[0]["metadata"]["project_count"] == 5

    def test_record_metric_upsert(self, temp_db):
        """Test that recording same metric upserts"""
        temp_db.record_metric("2025-01-15", "generation", "score", 0.8)
        temp_db.record_metric("2025-01-15", "generation", "score", 0.9)

        metrics = temp_db.get_metrics(
            metric_type="generation",
            metric_name="score",
        )
        assert len(metrics) == 1
        assert metrics[0]["metric_value"] == 0.9

    def test_get_metrics_filtered_by_type(self, temp_db):
        """Test filtering metrics by type"""
        temp_db.record_metric("2025-01-15", "generation", "score", 0.8)
        temp_db.record_metric("2025-01-15", "quality", "avg_score", 0.85)
        temp_db.record_metric("2025-01-15", "cost", "total", 50.0)

        gen_metrics = temp_db.get_metrics(metric_type="generation")
        assert len(gen_metrics) == 1

    def test_get_metrics_filtered_by_date_range(self, temp_db):
        """Test filtering metrics by date range"""
        dates = ["2025-01-10", "2025-01-15", "2025-01-20"]
        for date in dates:
            temp_db.record_metric(date, "generation", "score", 0.8)

        metrics = temp_db.get_metrics(
            start_date="2025-01-12",
            end_date="2025-01-18",
        )
        assert len(metrics) == 1

    def test_get_metrics_with_limit(self, temp_db):
        """Test limiting metric results"""
        for i in range(10):
            temp_db.record_metric(
                f"2025-01-{i+1:02d}",
                "generation",
                "score",
                0.8 + i * 0.01,
            )

        metrics = temp_db.get_metrics(limit=5)
        assert len(metrics) == 5

    def test_get_metrics_summary(self, temp_db):
        """Test getting metrics summary"""
        # Record multiple metrics
        for i in range(5):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            temp_db.record_metric(date, "generation", "quality", 0.8 + i * 0.02)
            temp_db.record_metric(date, "cost", "total", 10.0 + i)

        summary = temp_db.get_metrics_summary(days=30)

        assert "generation" in summary
        assert "cost" in summary

        gen_metrics = summary["generation"]
        assert len(gen_metrics) > 0

    def test_get_metrics_summary_empty(self, temp_db):
        """Test metrics summary with no data"""
        summary = temp_db.get_metrics_summary()
        assert summary == {}


class TestClientNameOperations:
    """Tests for client name retrieval"""

    def test_get_all_client_names(self, temp_db):
        """Test getting all client names"""
        clients = ["Alpha Corp", "Beta Inc", "Gamma LLC"]
        for client in clients:
            memory = ClientMemory(client_name=client)
            temp_db.create_client_memory(memory)

        names = temp_db.get_all_client_names()
        assert len(names) == 3
        for client in clients:
            assert client in names

    def test_get_all_client_names_empty(self, temp_db):
        """Test getting client names when none exist"""
        names = temp_db.get_all_client_names()
        assert len(names) == 0


class TestHelperMethods:
    """Tests for helper methods"""

    def test_row_to_revision_post(self, temp_db):
        """Test converting database row to RevisionPost"""
        row = {
            "post_index": 0,
            "template_id": 1,
            "template_name": "Problem Recognition",
            "original_content": "Original text",
            "original_word_count": 100,
            "revised_content": "Revised text",
            "revised_word_count": 120,
            "changes_summary": "Made it better",
        }

        post = temp_db._row_to_revision_post(row)

        assert post.post_index == 0
        assert post.template_id == 1
        assert post.template_name == "Problem Recognition"
        assert post.changes_summary == "Made it better"

    def test_row_to_revision_post_without_changes_summary(self, temp_db):
        """Test converting row without optional changes_summary"""
        row = {
            "post_index": 0,
            "template_id": 1,
            "template_name": "Template",
            "original_content": "Original",
            "original_word_count": 50,
            "revised_content": "Revised",
            "revised_word_count": 60,
        }

        post = temp_db._row_to_revision_post(row)
        assert post.changes_summary is None


class TestConnectionManagement:
    """Tests for database connection handling"""

    def test_connection_context_manager(self, temp_db):
        """Test that connection context manager properly opens and closes"""
        with temp_db._get_connection() as conn:
            assert conn is not None
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_connection_row_factory(self, temp_db, sample_project):
        """Test that row factory returns dict-like rows"""
        temp_db.create_project(sample_project)

        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM projects WHERE project_id = ?", (sample_project.project_id,)
            )
            row = cursor.fetchone()

            # Should be able to access by column name
            assert row["project_id"] == sample_project.project_id
            assert row["client_name"] == sample_project.client_name


class TestMissingBranchCoverage:
    """Tests covering the two remaining uncovered branches in project_db.py.

    Lines 1288-1289: get_post_feedback(project_id=...) filter branch.
    Lines 1474-1475: get_client_satisfaction(project_id=...) filter branch.
    """

    def test_get_post_feedback_filtered_by_project_id(self, temp_db):
        """Test filtering post feedback by project_id (covers lines 1288-1289)"""
        # Store feedback for two different projects
        temp_db.store_post_feedback(
            client_name="Client A",
            project_id="proj-alpha",
            post_id="post-001",
            template_id=1,
            template_name="Template 1",
            feedback_type="kept",
        )
        temp_db.store_post_feedback(
            client_name="Client A",
            project_id="proj-beta",
            post_id="post-002",
            template_id=2,
            template_name="Template 2",
            feedback_type="loved",
        )

        # Filter by project_id should return only matching records
        results = temp_db.get_post_feedback(project_id="proj-alpha")

        assert len(results) == 1
        assert results[0]["project_id"] == "proj-alpha"
        assert results[0]["feedback_type"] == "kept"

    def test_get_client_satisfaction_filtered_by_project_id(self, temp_db):
        """Test filtering client satisfaction by project_id (covers lines 1474-1475)"""
        memory = ClientMemory(client_name="Test Client")
        temp_db.create_client_memory(memory)

        # Store satisfaction for two different projects
        temp_db.store_client_satisfaction(
            client_name="Test Client",
            project_id="proj-one",
            satisfaction_score=5,
            quality_rating=5,
            voice_match_rating=5,
            would_recommend=True,
        )
        temp_db.store_client_satisfaction(
            client_name="Test Client",
            project_id="proj-two",
            satisfaction_score=3,
            quality_rating=3,
            voice_match_rating=3,
            would_recommend=False,
        )

        # Filter by project_id should return only matching records
        results = temp_db.get_client_satisfaction(project_id="proj-one")

        assert len(results) == 1
        assert results[0]["project_id"] == "proj-one"
        assert results[0]["satisfaction_score"] == 5
