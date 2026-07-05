"""
Unit tests for research_context_builder.py

Target: 90%+ coverage
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.services.research_context_builder import (
    build_research_context,
    invalidate_cache,
    _format_all_results,
    _format_tool_result,
    _format_voice_analysis,
    _format_seo_keywords,
    _format_brand_archetype,
    CACHE_PREFIX,
    CACHE_TTL,
    MAX_TOTAL_TOKENS,
)


class TestBuildResearchContext:
    """Test the main build_research_context function."""

    def test_returns_cached_result_when_available(self):
        """Test that cached results are returned without DB query."""
        mock_db = Mock(spec=Session)
        client_id = "test-client-123"
        cached_data = {
            "formatted_text": "Cached insights",
            "tools_included": ["voice_analysis"],
            "total_tokens": 100,
        }

        with patch("backend.services.research_context_builder.cache") as mock_cache:
            mock_cache.get_by_key.return_value = cached_data

            result = build_research_context(mock_db, client_id)

            assert result == cached_data
            mock_cache.get_by_key.assert_called_once_with(f"{CACHE_PREFIX}_{client_id}")

    def test_fetches_from_db_on_cache_miss(self):
        """Test that DB is queried when cache misses."""
        mock_db = Mock(spec=Session)
        client_id = "test-client-123"

        mock_result = Mock()
        mock_result.tool_name = "voice_analysis"
        mock_result.result_data = {"readability_score": 8.5}
        mock_result.created_at = datetime.now()
        mock_result.status = "completed"

        with (
            patch("backend.services.research_context_builder.cache") as mock_cache,
            patch("backend.services.research_context_builder.crud") as mock_crud,
        ):
            mock_cache.get_by_key.return_value = None
            mock_crud.get_research_results_by_client.return_value = [mock_result]

            result = build_research_context(mock_db, client_id)

            mock_cache.get_by_key.assert_called_once()
            mock_crud.get_research_results_by_client.assert_called_once_with(mock_db, client_id)
            assert isinstance(result, dict)
            assert "formatted_text" in result

    def test_caches_result_after_db_fetch(self):
        """Test that results are cached after DB fetch."""
        mock_db = Mock(spec=Session)
        client_id = "test-client-123"

        mock_result = Mock()
        mock_result.tool_name = "voice_analysis"
        mock_result.result_data = {"readability_score": 8.5}
        mock_result.created_at = datetime.now()
        mock_result.status = "completed"

        with (
            patch("backend.services.research_context_builder.cache") as mock_cache,
            patch("backend.services.research_context_builder.crud") as mock_crud,
        ):
            mock_cache.get_by_key.return_value = None
            mock_crud.get_research_results_by_client.return_value = [mock_result]

            result = build_research_context(mock_db, client_id)

            assert mock_cache.put_by_key.called
            call_args = mock_cache.put_by_key.call_args
            assert call_args[0][0] == f"{CACHE_PREFIX}_{client_id}"

    def test_returns_empty_when_no_results(self):
        """Test behavior when no research results exist."""
        mock_db = Mock(spec=Session)
        client_id = "test-client-123"

        with (
            patch("backend.services.research_context_builder.cache") as mock_cache,
            patch("backend.services.research_context_builder.crud") as mock_crud,
        ):
            mock_cache.get_by_key.return_value = None
            mock_crud.get_research_results_by_client.return_value = []

            result = build_research_context(mock_db, client_id)

            assert result["formatted_text"] == ""
            assert result["tools_included"] == []
            assert result["total_tokens"] == 0

    def test_handles_db_error_gracefully(self):
        """Test that DB errors propagate (no top-level error handling)."""
        mock_db = Mock(spec=Session)
        client_id = "test-client-123"

        with (
            patch("backend.services.research_context_builder.cache") as mock_cache,
            patch("backend.services.research_context_builder.crud") as mock_crud,
        ):
            mock_cache.get_by_key.return_value = None
            mock_crud.get_research_results_by_client.side_effect = Exception("DB Error")

            # Exception should propagate (no error handling in build_research_context)
            with pytest.raises(Exception, match="DB Error"):
                build_research_context(mock_db, client_id)


class TestInvalidateCache:
    """Test cache invalidation function."""

    def test_invalidates_correct_key(self):
        """Test that correct cache key is invalidated."""
        client_id = "test-client-123"

        with patch("backend.services.research_context_builder.cache") as mock_cache:
            invalidate_cache(client_id)

            mock_cache.delete.assert_called_once_with(f"{CACHE_PREFIX}_{client_id}")

    def test_handles_cache_error(self):
        """Test that cache errors propagate (no error handling in invalidate_cache)."""
        client_id = "test-client-123"

        with patch("backend.services.research_context_builder.cache") as mock_cache:
            mock_cache.delete.side_effect = Exception("Cache Error")

            # Exception should propagate (no error handling in invalidate_cache)
            with pytest.raises(Exception, match="Cache Error"):
                invalidate_cache(client_id)


class TestTokenBudgetEnforcement:
    """Test token budget enforcement."""

    def test_enforces_total_budget_across_tools(self):
        """Test that total across all tools doesn't exceed 500."""
        tool_results = {}  # Dictionary mapping tool_name to result

        tool_names = [
            "voice_analysis",
            "seo_keyword_research",
            "brand_archetype",
            "competitive_analysis",
            "content_gap_analysis",
            "market_trends_research",
            "platform_strategy",
            "content_calendar",
            "audience_research",
            "icp_workshop",
            "story_mining",
            "content_audit",
        ]

        for tool_name in tool_names:
            mock_result = Mock()
            mock_result.tool_name = tool_name
            mock_result.result_data = {
                "key1": "x" * 500,
                "key2": "y" * 500,
            }
            mock_result.created_at = datetime.now()
            mock_result.status = "completed"
            tool_results[tool_name] = mock_result  # Add to dict

        formatted = _format_all_results(tool_results)

        assert formatted["total_tokens"] <= MAX_TOTAL_TOKENS
