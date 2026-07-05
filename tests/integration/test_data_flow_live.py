"""
Live Data Flow Test - Verify Prerequisites Data Actually Flows

Tests that when research tools run, they receive data from prerequisite tools.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from backend.services.research_service import ResearchService


@pytest.fixture
def research_service():
    return ResearchService()


@pytest.fixture
def mock_db_with_seo_result():
    """Mock database that has completed SEO research"""
    db = Mock()

    # Mock SEO result
    seo_result = Mock()
    seo_result.tool_name = "seo_keyword_research"
    seo_result.status = "completed"
    seo_result.data = {
        "primary_keywords": [
            "AI content marketing",
            "B2B SaaS marketing",
            "content automation",
            "marketing workflows",
        ],
        "keywords": ["content strategy", "lead generation"],
    }
    seo_result.created_at = datetime.now()

    # Configure mock to return SEO result for seo_keyword_research queries
    def mock_query_side_effect(*args):
        mock_query = Mock()

        def mock_filter_side_effect(*filter_args, **filter_kwargs):
            mock_filtered = Mock()
            mock_ordered = Mock()

            # Return SEO result for seo_keyword_research queries
            mock_ordered.first = Mock(return_value=seo_result)
            mock_filtered.order_by = Mock(return_value=mock_ordered)

            return mock_filtered

        mock_query.filter = Mock(side_effect=mock_filter_side_effect)
        return mock_query

    db.query = Mock(side_effect=mock_query_side_effect)
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()

    # Mock completed tools query
    completed_tools_mock = Mock()
    completed_tools_mock.distinct = Mock()
    completed_tools_mock.distinct().all = Mock(return_value=[("seo_keyword_research",)])

    return db


class TestDataFlowActuallyWorks:
    """Verify data actually flows between tools"""

    def test_market_trends_receives_seo_keywords(self, research_service, mock_db_with_seo_result):
        """Test that Market Trends receives SEO keywords from database"""

        # Call _fetch_prerequisite_data for Market Trends
        prerequisite_data = research_service._fetch_prerequisite_data(
            mock_db_with_seo_result, "project-test", "market_trends_research"
        )

        # Verify SEO keywords were fetched
        assert "seo_keywords" in prerequisite_data
        assert len(prerequisite_data["seo_keywords"]) == 4
        assert "AI content marketing" in prerequisite_data["seo_keywords"]
        assert "B2B SaaS marketing" in prerequisite_data["seo_keywords"]

    def test_content_calendar_receives_multiple_prerequisites(self, research_service):
        """Test Content Calendar can receive multiple prerequisite data"""

        # Mock database with both SEO and Platform results
        db = Mock()

        # SEO result
        seo_result = Mock()
        seo_result.tool_name = "seo_keyword_research"
        seo_result.status = "completed"
        seo_result.data = {"primary_keywords": ["AI", "automation"]}
        seo_result.created_at = datetime.now()

        # Platform result
        platform_result = Mock()
        platform_result.tool_name = "platform_strategy"
        platform_result.status = "completed"
        platform_result.data = {
            "platforms": ["LinkedIn", "Twitter"],
            "frequency": {"LinkedIn": "3x/week"},
        }
        platform_result.created_at = datetime.now()

        # Market Trends result
        trends_result = Mock()
        trends_result.tool_name = "market_trends_research"
        trends_result.status = "completed"
        trends_result.data = {
            "trends": ["AI automation", "Remote work"],
            "trending_topics": ["ChatGPT", "AI tools"],
        }
        trends_result.created_at = datetime.now()

        # Mock query to return appropriate result based on tool
        results_map = {
            "seo_keyword_research": seo_result,
            "platform_strategy": platform_result,
            "market_trends_research": trends_result,
        }

        call_counter = [0]

        def mock_query_side_effect(*args):
            mock_query = Mock()

            def mock_filter_side_effect(*filter_args, **filter_kwargs):
                mock_filtered = Mock()
                mock_ordered = Mock()

                # Rotate through results
                tool_order = ["seo_keyword_research", "platform_strategy", "market_trends_research"]
                result = results_map[tool_order[call_counter[0] % 3]]
                call_counter[0] += 1

                mock_ordered.first = Mock(return_value=result)
                mock_filtered.order_by = Mock(return_value=mock_ordered)

                return mock_filtered

            mock_query.filter = Mock(side_effect=mock_filter_side_effect)
            return mock_query

        db.query = Mock(side_effect=mock_query_side_effect)

        # Fetch prerequisite data for Content Calendar
        prerequisite_data = research_service._fetch_prerequisite_data(
            db, "project-test", "content_calendar"
        )

        # Content Calendar should receive data from multiple sources
        # At least one of these should be present
        possible_keys = [
            "seo_keywords",
            "platform_recommendations",
            "posting_frequency",
            "market_trends",
            "trending_topics",
        ]

        assert any(
            key in prerequisite_data for key in possible_keys
        ), f"Expected at least one prerequisite data key, got: {list(prerequisite_data.keys())}"

    def test_no_data_when_prerequisite_not_found(self, research_service):
        """Test graceful handling when prerequisite not in database"""

        # Mock database with no results
        db = Mock()

        def mock_query_side_effect(*args):
            mock_query = Mock()

            def mock_filter_side_effect(*filter_args, **filter_kwargs):
                mock_filtered = Mock()
                mock_ordered = Mock()
                mock_ordered.first = Mock(return_value=None)  # No result
                mock_filtered.order_by = Mock(return_value=mock_ordered)
                return mock_filtered

            mock_query.filter = Mock(side_effect=mock_filter_side_effect)
            return mock_query

        db.query = Mock(side_effect=mock_query_side_effect)

        # Fetch prerequisite data
        prerequisite_data = research_service._fetch_prerequisite_data(
            db, "project-test", "market_trends_research"
        )

        # Should return empty dict when no prerequisites found
        assert prerequisite_data == {}


class TestPrerequisiteDataExtraction:
    """Test that data extraction works for each tool type"""

    def test_seo_keywords_extraction(self, research_service):
        """Test SEO keywords are extracted correctly"""
        db = Mock()

        result = Mock()
        result.tool_name = "seo_keyword_research"
        result.status = "completed"
        result.data = {
            "primary_keywords": ["keyword1", "keyword2"],
            "keywords": ["keyword3", "keyword4"],
        }
        result.created_at = datetime.now()

        def mock_query(*args):
            m = Mock()
            m.filter = Mock(return_value=m)
            m.order_by = Mock(return_value=m)
            m.first = Mock(return_value=result)
            return m

        db.query = mock_query

        data = research_service._fetch_prerequisite_data(db, "proj", "market_trends_research")

        assert data["seo_keywords"] == ["keyword1", "keyword2"]

    def test_audience_research_extraction(self, research_service):
        """Test audience data is extracted correctly"""
        db = Mock()

        result = Mock()
        result.tool_name = "audience_research"
        result.status = "completed"
        result.data = {
            "personas": [{"name": "Marketing Mary"}],
            "demographics": {"age": "25-34"},
            "pain_points": ["Time management"],
        }
        result.created_at = datetime.now()

        def mock_query(*args):
            m = Mock()
            m.filter = Mock(return_value=m)
            m.order_by = Mock(return_value=m)
            m.first = Mock(return_value=result)
            return m

        db.query = mock_query

        data = research_service._fetch_prerequisite_data(db, "proj", "platform_strategy")

        assert "audience_personas" in data
        assert "audience_demographics" in data
        assert "audience_pain_points" in data
