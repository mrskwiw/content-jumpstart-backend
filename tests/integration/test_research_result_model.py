"""
Unit tests for ResearchResult model.

Tests model creation, relationships, and data storage.
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from backend.models import ResearchResult, User, Client, Project


class TestResearchResultModel:
    """Test ResearchResult model."""

    def test_create_research_result(self, db_session, test_user, test_client, test_project):
        """Test creating a research result."""
        result = ResearchResult(
            id="res-test123",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=400.0,
            params={"content_samples": ["sample1", "sample2"]},
            outputs={"report": "path/to/report.md"},
            data={"tone": "Professional", "readability_score": 65.2},
            status="completed",
            duration_seconds=12.5,
            cache_key="abc123",
            is_cached_result=False,
        )

        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)

        assert result.id == "res-test123"
        assert result.user_id == test_user.id
        assert result.client_id == test_client.id
        assert result.project_id == test_project.id
        assert result.tool_name == "voice_analysis"
        assert result.tool_label == "Voice Analysis"
        assert result.tool_price == 400.0
        assert result.params == {"content_samples": ["sample1", "sample2"]}
        assert result.outputs == {"report": "path/to/report.md"}
        assert result.data == {"tone": "Professional", "readability_score": 65.2}
        assert result.status == "completed"
        assert result.duration_seconds == 12.5
        assert result.cache_key == "abc123"
        assert result.is_cached_result is False
        assert result.created_at is not None

    def test_research_result_relationships(self, db_session, test_user, test_client, test_project):
        """Test ResearchResult relationships."""
        result = ResearchResult(
            id="res-rel123",
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

        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)

        # Test relationships
        assert result.user.id == test_user.id
        assert result.client.id == test_client.id
        assert result.project.id == test_project.id

    def test_research_result_without_project(self, db_session, test_user, test_client):
        """Test creating research result without project_id (optional)."""
        result = ResearchResult(
            id="res-noproj123",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=None,  # Optional
            tool_name="brand_archetype",
            tool_label="Brand Archetype",
            tool_price=300.0,
            params={},
            outputs={},
            status="completed",
        )

        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)

        assert result.project_id is None
        assert result.project is None

    def test_research_result_failed_status(self, db_session, test_user, test_client, test_project):
        """Test creating research result with failed status."""
        result = ResearchResult(
            id="res-failed123",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="competitive_analysis",
            tool_label="Competitive Analysis",
            tool_price=600.0,
            params={},
            outputs={},
            status="failed",
            error_message="API rate limit exceeded",
            duration_seconds=2.3,
        )

        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)

        assert result.status == "failed"
        assert result.error_message == "API rate limit exceeded"
        assert result.duration_seconds == 2.3

    def test_research_result_json_columns(self, db_session, test_user, test_client, test_project):
        """Test JSON column storage."""
        complex_data = {
            "primary_keywords": [
                {"keyword": "content marketing", "volume": 50000, "difficulty": "Medium"},
                {"keyword": "social media", "volume": 25000, "difficulty": "High"},
            ],
            "secondary_keywords": ["seo", "analytics", "strategy"],
            "metadata": {"tool_version": "2.0", "analysis_date": "2026-02-25"},
        }

        result = ResearchResult(
            id="res-json123",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="seo_keyword_research",
            tool_label="SEO Keyword Research",
            tool_price=500.0,
            params={"target_keywords": ["marketing", "content"]},
            outputs={"csv": "keywords.csv", "json": "keywords.json"},
            data=complex_data,
            status="completed",
        )

        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)

        # Verify JSON data is preserved
        assert result.data["primary_keywords"][0]["keyword"] == "content marketing"
        assert result.data["primary_keywords"][0]["volume"] == 50000
        assert result.data["secondary_keywords"] == ["seo", "analytics", "strategy"]
        assert result.data["metadata"]["tool_version"] == "2.0"
        assert result.params["target_keywords"] == ["marketing", "content"]
        assert result.outputs["csv"] == "keywords.csv"

    def test_research_result_repr(self, db_session, test_user, test_client, test_project):
        """Test ResearchResult __repr__."""
        result = ResearchResult(
            id="res-repr123",
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

        repr_str = repr(result)
        assert "res-repr123" in repr_str
        assert "voice_analysis" in repr_str
        assert "completed" in repr_str

    def test_research_result_missing_required_fields(self, db_session, test_user, test_client):
        """Test that missing required fields raise IntegrityError."""
        # Missing user_id
        result = ResearchResult(
            id="res-missing123",
            client_id=test_client.id,
            tool_name="voice_analysis",
            params={},
            outputs={},
            status="completed",
        )

        db_session.add(result)

        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

    def test_research_result_cache_tracking(self, db_session, test_user, test_client, test_project):
        """Test cache key tracking."""
        result = ResearchResult(
            id="res-cache123",
            user_id=test_user.id,
            client_id=test_client.id,
            project_id=test_project.id,
            tool_name="seo_keyword_research",
            tool_label="SEO Keyword Research",
            tool_price=500.0,
            params={"keywords": ["seo"]},
            outputs={},
            status="completed",
            cache_key="sha256hash123",
            is_cached_result=True,
        )

        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)

        assert result.cache_key == "sha256hash123"
        assert result.is_cached_result is True

    def test_research_result_query_by_tool_name(
        self, db_session, test_user, test_client, test_project
    ):
        """Test querying research results by tool name."""
        # Create multiple results
        result1 = ResearchResult(
            id="res-query1",
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
            id="res-query2",
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

        # Query by tool name
        voice_results = (
            db_session.query(ResearchResult)
            .filter(ResearchResult.tool_name == "voice_analysis")
            .all()
        )

        assert len(voice_results) == 1
        assert voice_results[0].id == "res-query1"

    def test_research_result_query_by_status(
        self, db_session, test_user, test_client, test_project
    ):
        """Test querying research results by status."""
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

        # Query by status
        completed_results = (
            db_session.query(ResearchResult).filter(ResearchResult.status == "completed").all()
        )

        failed_results = (
            db_session.query(ResearchResult).filter(ResearchResult.status == "failed").all()
        )

        assert len(completed_results) == 1
        assert len(failed_results) == 1
        assert failed_results[0].error_message == "Timeout"
