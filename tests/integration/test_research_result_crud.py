"""
Unit tests for research result CRUD operations.

Tests get, create, update, delete operations for research results.
"""

import pytest
from backend.services import crud
from backend.models import ResearchResult


class TestResearchResultCRUD:
    """Test CRUD operations for research results."""

    def test_get_research_result(self, db_session, test_user, test_client, test_project):
        """Test getting a research result by ID."""
        # Create research result
        result = ResearchResult(
            id="res-get123",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            params={},
            outputs={},
            status="completed",
        )
        db_session.add(result)
        db_session.commit()

        # Get result
        fetched = crud.get_research_result(db_session, "res-get123")

        assert fetched is not None
        assert fetched.id == "res-get123"
        assert fetched.tool_name == "voice_analysis"
        assert fetched.status == "completed"

    def test_get_research_result_not_found(self, db_session):
        """Test getting non-existent research result returns None."""
        result = crud.get_research_result(db_session, "res-nonexistent")
        assert result is None

    def test_get_research_results_by_project(
        self, db_session, test_user, test_client, test_project
    ):
        """Test getting all research results for a project."""
        # Create multiple results for same project
        result1 = ResearchResult(
            id="res-proj1",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            params={},
            outputs={},
            status="completed",
        )

        result2 = ResearchResult(
            id="res-proj2",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="seo_keyword_research",
            tool_label="SEO Keyword Research",
            tool_price=500.0,
            params={},
            outputs={},
            status="completed",
        )

        db_session.add_all([result1, result2])
        db_session.commit()

        # Get all results for project
        results = crud.get_research_results_by_project(db_session, test_project.id)

        assert len(results) == 2
        result_ids = [r.id for r in results]
        assert "res-proj1" in result_ids
        assert "res-proj2" in result_ids

    def test_get_research_results_by_project_with_tool_filter(
        self, db_session, test_user, test_client, test_project
    ):
        """Test getting research results filtered by tool name."""
        # Create results with different tools
        result1 = ResearchResult(
            id="res-filter1",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            params={},
            outputs={},
            status="completed",
        )

        result2 = ResearchResult(
            id="res-filter2",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="seo_keyword_research",
            tool_label="SEO Keyword Research",
            tool_price=500.0,
            params={},
            outputs={},
            status="completed",
        )

        db_session.add_all([result1, result2])
        db_session.commit()

        # Filter by tool name
        voice_results = crud.get_research_results_by_project(
            db_session, test_project.id, tool_name="voice_analysis"
        )

        assert len(voice_results) == 1
        assert voice_results[0].tool_name == "voice_analysis"

    def test_get_research_results_by_project_with_status_filter(
        self, db_session, test_user, test_client, test_project
    ):
        """Test getting research results filtered by status."""
        # Create completed and failed results
        result1 = ResearchResult(
            id="res-status1",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            params={},
            outputs={},
            status="completed",
        )

        result2 = ResearchResult(
            id="res-status2",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="seo_keyword_research",
            tool_label="SEO Keyword Research",
            tool_price=500.0,
            params={},
            outputs={},
            status="failed",
            error_message="Timeout",
        )

        db_session.add_all([result1, result2])
        db_session.commit()

        # Filter by status
        completed_results = crud.get_research_results_by_project(
            db_session, test_project.id, status="completed"
        )

        failed_results = crud.get_research_results_by_project(
            db_session, test_project.id, status="failed"
        )

        assert len(completed_results) == 1
        assert len(failed_results) == 1
        assert failed_results[0].error_message == "Timeout"

    def test_get_research_results_by_project_empty(self, db_session, test_project):
        """Test getting results for project with no research."""
        results = crud.get_research_results_by_project(db_session, test_project.id)
        assert len(results) == 0

    def test_get_research_results_by_client(self, db_session, test_user, test_client, test_project):
        """Test getting all research results for a client."""
        # Create results for client
        result1 = ResearchResult(
            id="res-client1",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            params={},
            outputs={},
            status="completed",
        )

        result2 = ResearchResult(
            id="res-client2",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=None,  # Client-level research (no project)
            tool_name="brand_archetype",
            tool_label="Brand Archetype",
            tool_price=300.0,
            params={},
            outputs={},
            status="completed",
        )

        db_session.add_all([result1, result2])
        db_session.commit()

        # Get all results for client
        results = crud.get_research_results_by_client(db_session, test_client.id)

        assert len(results) == 2
        result_ids = [r.id for r in results]
        assert "res-client1" in result_ids
        assert "res-client2" in result_ids

    def test_get_research_results_by_client_with_tool_filter(
        self, db_session, test_user, test_client, test_project
    ):
        """Test getting client results filtered by tool name."""
        # Create results with different tools
        result1 = ResearchResult(
            id="res-clientfilt1",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            params={},
            outputs={},
            status="completed",
        )

        result2 = ResearchResult(
            id="res-clientfilt2",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="seo_keyword_research",
            tool_label="SEO Keyword Research",
            tool_price=500.0,
            params={},
            outputs={},
            status="completed",
        )

        db_session.add_all([result1, result2])
        db_session.commit()

        # Filter by tool name
        seo_results = crud.get_research_results_by_client(
            db_session, test_client.id, tool_name="seo_keyword_research"
        )

        assert len(seo_results) == 1
        assert seo_results[0].tool_name == "seo_keyword_research"

    def test_get_research_results_by_client_empty(self, db_session, test_client):
        """Test getting results for client with no research."""
        results = crud.get_research_results_by_client(db_session, test_client.id)
        assert len(results) == 0

    def test_delete_research_result(self, db_session, test_user, test_client, test_project):
        """Test deleting a research result."""
        # Create research result
        result = ResearchResult(
            id="res-delete123",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            params={},
            outputs={},
            status="completed",
        )
        db_session.add(result)
        db_session.commit()

        # Verify it exists
        assert crud.get_research_result(db_session, "res-delete123") is not None

        # Delete it
        deleted = crud.delete_research_result(db_session, "res-delete123")
        assert deleted is True

        # Verify it's gone
        assert crud.get_research_result(db_session, "res-delete123") is None

    def test_delete_research_result_not_found(self, db_session):
        """Test deleting non-existent research result returns False."""
        deleted = crud.delete_research_result(db_session, "res-nonexistent")
        assert deleted is False

    def test_get_research_results_ordered_by_created_at(
        self, db_session, test_user, test_client, test_project
    ):
        """Test that results are ordered by created_at descending (newest first)."""
        import time

        # Create results with different created_at times
        from datetime import datetime, timedelta

        now = datetime.utcnow()

        result1 = ResearchResult(
            id="res-order1",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            params={},
            outputs={},
            status="completed",
            created_at=now - timedelta(seconds=2),  # 2 seconds ago
        )
        db_session.add(result1)
        db_session.commit()

        result2 = ResearchResult(
            id="res-order2",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="seo_keyword_research",
            tool_label="SEO Keyword Research",
            tool_price=500.0,
            params={},
            outputs={},
            status="completed",
            created_at=now,  # Now (newer)
        )
        db_session.add(result2)
        db_session.commit()

        # Get results (should be newest first)
        results = crud.get_research_results_by_project(db_session, test_project.id)

        assert len(results) == 2
        assert results[0].id == "res-order2"  # Newest first
        assert results[1].id == "res-order1"  # Oldest last
