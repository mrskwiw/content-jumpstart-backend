"""
Unit tests for Bug #48: alias_generator in research response schemas

Tests that ResearchResultResponse and ResearchResultListResponse
properly convert snake_case field names to camelCase for frontend.
"""

import pytest
from datetime import datetime
from backend.schemas.research_schemas import ResearchResultResponse, ResearchResultListResponse


class TestResearchResultResponseAliasGenerator:
    """Test suite for ResearchResultResponse alias_generator (Bug #48)"""

    def test_response_converts_snake_case_to_camel_case(self):
        """Test that response schema converts snake_case to camelCase"""
        # Create response with snake_case field names
        response = ResearchResultResponse(
            id="result-123",
            user_id="user-456",
            client_id="client-789",
            project_id="proj-abc",
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=300.0,
            params={"industry": "tech"},
            outputs={"summary": "test"},
            data={"test": "data"},
            status="completed",
            error_message=None,
            duration_seconds=45.5,
            created_at=datetime(2026, 3, 18, 10, 30, 0),
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=100,
            cache_read_tokens=200,
            actual_cost_usd=0.05,
        )

        # Convert to dict with aliases
        response_dict = response.model_dump(by_alias=True)

        # Verify camelCase keys exist
        assert "userId" in response_dict
        assert "clientId" in response_dict
        assert "projectId" in response_dict
        assert "toolName" in response_dict
        assert "toolLabel" in response_dict
        assert "toolPrice" in response_dict
        assert "errorMessage" in response_dict
        assert "durationSeconds" in response_dict
        assert "createdAt" in response_dict
        assert "inputTokens" in response_dict
        assert "outputTokens" in response_dict
        assert "cacheCreationTokens" in response_dict
        assert "cacheReadTokens" in response_dict
        assert "actualCostUsd" in response_dict

        # Verify snake_case keys DO NOT exist
        assert "user_id" not in response_dict
        assert "client_id" not in response_dict
        assert "project_id" not in response_dict
        assert "tool_name" not in response_dict

    def test_response_preserves_values(self):
        """Test that alias_generator preserves field values"""
        response = ResearchResultResponse(
            id="result-test",
            user_id="user-test",
            client_id="client-test",
            project_id="proj-test",
            tool_name="seo_keyword_research",
            tool_label="SEO Keywords",
            tool_price=400.0,
            params={},
            outputs={"keywords": "test, keywords"},  # Fixed: outputs is Dict[str, str]
            data={"keyword_list": ["test", "keywords"]},
            status="completed",
            error_message=None,
            duration_seconds=55.2,
            created_at=datetime(2026, 3, 18),
        )

        response_dict = response.model_dump(by_alias=True)

        # Verify values are preserved
        assert response_dict["userId"] == "user-test"
        assert response_dict["clientId"] == "client-test"
        assert response_dict["projectId"] == "proj-test"
        assert response_dict["toolName"] == "seo_keyword_research"
        assert response_dict["toolPrice"] == 400.0

    def test_response_accepts_snake_case_input(self):
        """Test that schema accepts snake_case input (serialization_alias is output-only)"""
        # Should accept snake_case input
        response = ResearchResultResponse.model_validate(
            {
                "id": "result-2",
                "user_id": "user-2",  # snake_case
                "client_id": "client-2",
                "project_id": "proj-2",
                "tool_name": "test_tool",
                "tool_label": "Test Tool",
                "tool_price": 300.0,
                "params": {},
                "outputs": {"result": "test"},
                "data": {"test": "data"},
                "status": "completed",
                "error_message": None,
                "duration_seconds": 30.0,
                "created_at": "2026-03-18T10:00:00",
            }
        )
        assert response.user_id == "user-2"
        # Verify camelCase output via serialization_alias
        response_dict = response.model_dump(by_alias=True)
        assert response_dict["userId"] == "user-2"


class TestResearchResultListResponseAliasGenerator:
    """Test suite for ResearchResultListResponse alias_generator (Bug #48)"""

    def test_list_response_converts_snake_case(self):
        """Test that list response converts snake_case to camelCase"""
        response = ResearchResultListResponse(
            results=[], total=5, project_id="proj-123", client_id="client-456"
        )

        response_dict = response.model_dump(by_alias=True)

        # Verify camelCase keys
        assert "projectId" in response_dict
        assert "clientId" in response_dict

        # Verify snake_case keys don't exist
        assert "project_id" not in response_dict
        assert "client_id" not in response_dict

    def test_list_response_with_results(self):
        """Test list response with nested result objects"""
        result = ResearchResultResponse(
            id="result-1",
            user_id="user-1",
            client_id="client-1",
            project_id="proj-1",
            tool_name="test",
            tool_label="Test Tool",
            tool_price=300.0,
            params={},
            outputs={"result": "test"},
            data={"test": "data"},
            status="completed",
            error_message=None,
            duration_seconds=25.0,
            created_at=datetime(2026, 3, 18),
        )

        list_response = ResearchResultListResponse(
            results=[result], total=1, project_id="proj-1", client_id="client-1"
        )

        response_dict = list_response.model_dump(by_alias=True)

        # Verify list-level fields are camelCase
        assert "projectId" in response_dict
        assert "clientId" in response_dict

        # Verify nested result also has camelCase
        assert len(response_dict["results"]) == 1
        assert "userId" in response_dict["results"][0]
        assert "toolName" in response_dict["results"][0]
