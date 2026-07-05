"""
Unit tests for research service demo data functionality.

Tests the demo response generation when research tools are unavailable.
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.services.research_service import ResearchService


class TestResearchDemoData:
    """Test demo data generation for research tools"""

    @pytest.fixture
    def research_service(self):
        """Create research service instance"""
        return ResearchService()

    @pytest.fixture
    def mock_client(self):
        """Create mock client"""
        client = MagicMock()
        client.name = "Test Company"
        client.business_description = "A test company for demos"
        client.ideal_customer = "Demo customers"
        return client

    def test_get_demo_response_voice_analysis(self, research_service, mock_client):
        """Test voice analysis demo response"""
        response = research_service._get_demo_response(
            tool_name="voice_analysis",
            project_id="test-project-123",
            client=mock_client,
        )

        assert response["success"] is True
        assert response["error"] is None
        assert "data" in response
        assert "metadata" in response

        # Check voice analysis specific data
        data = response["data"]
        assert "summary" in data
        assert "tone" in data
        assert "readability_score" in data
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

    def test_get_demo_response_brand_archetype(self, research_service, mock_client):
        """Test brand archetype demo response"""
        response = research_service._get_demo_response(
            tool_name="brand_archetype",
            project_id="test-project-123",
            client=mock_client,
        )

        assert response["success"] is True
        data = response["data"]
        assert "primary_archetype" in data
        assert "secondary_archetype" in data
        assert "archetype_traits" in data

    def test_get_demo_response_competitive_analysis(self, research_service, mock_client):
        """Test competitive analysis demo response"""
        response = research_service._get_demo_response(
            tool_name="competitive_analysis",
            project_id="test-project-123",
            client=mock_client,
        )

        assert response["success"] is True
        data = response["data"]
        assert "competitors_analyzed" in data
        assert "market_position" in data
        assert "content_gaps" in data

    def test_get_demo_response_market_trends(self, research_service, mock_client):
        """Test market trends demo response"""
        response = research_service._get_demo_response(
            tool_name="market_trends_research",
            project_id="test-project-123",
            client=mock_client,
        )

        assert response["success"] is True
        data = response["data"]
        assert "trending_topics" in data
        assert "content_opportunities" in data

    def test_get_demo_response_seo_keywords(self, research_service, mock_client):
        """Test SEO keyword research demo response"""
        response = research_service._get_demo_response(
            tool_name="seo_keyword_research",
            project_id="test-project-123",
            client=mock_client,
        )

        assert response["success"] is True
        data = response["data"]
        assert "primary_keywords" in data
        assert "long_tail_opportunities" in data

    def test_get_demo_response_unknown_tool(self, research_service, mock_client):
        """Test demo response for unknown tool returns generic data"""
        response = research_service._get_demo_response(
            tool_name="unknown_tool",
            project_id="test-project-123",
            client=mock_client,
        )

        assert response["success"] is True
        data = response["data"]
        assert "summary" in data
        assert "status" in data

    def test_get_demo_response_metadata(self, research_service, mock_client):
        """Test that demo response includes proper metadata"""
        response = research_service._get_demo_response(
            tool_name="voice_analysis",
            project_id="test-project-123",
            client=mock_client,
        )

        metadata = response["metadata"]
        assert metadata["status"] == "completed"
        assert metadata["tool_name"] == "voice_analysis"
        assert metadata["project_id"] == "test-project-123"
        assert "executed_at" in metadata
        assert "note" in metadata
        assert "Demo data" in metadata["note"]

    def test_get_demo_response_no_outputs(self, research_service, mock_client):
        """Test that demo response has empty outputs (no file generation)"""
        response = research_service._get_demo_response(
            tool_name="voice_analysis",
            project_id="test-project-123",
            client=mock_client,
        )

        assert response["outputs"] == {}

    def test_get_demo_response_client_name_in_summary(self, research_service, mock_client):
        """Test that client name appears in demo summaries"""
        response = research_service._get_demo_response(
            tool_name="voice_analysis",
            project_id="test-project-123",
            client=mock_client,
        )

        assert "Test Company" in response["data"]["summary"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
