"""Unit tests for backend.utils.cache_invalidation."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.utils.cache_invalidation import (
    invalidate_project_cache,
    invalidate_client_cache,
    invalidate_research_cache,
    invalidate_cost_cache,
    invalidate_all_caches,
)


@pytest.fixture(autouse=True)
def mock_cache():
    """Provide a mock cache so tests don't touch the global singleton."""
    cache = MagicMock()
    cache.invalidate_pattern = AsyncMock()
    cache.clear = AsyncMock()
    with patch("backend.utils.cache_invalidation.get_cache", return_value=cache):
        yield cache


class TestInvalidateProjectCache:
    @pytest.mark.asyncio
    async def test_calls_invalidate_for_project(self, mock_cache):
        await invalidate_project_cache("proj-123")
        calls = [str(c) for c in mock_cache.invalidate_pattern.call_args_list]
        assert any("proj-123" in c for c in calls)

    @pytest.mark.asyncio
    async def test_multiple_patterns_invalidated(self, mock_cache):
        await invalidate_project_cache("proj-abc")
        # Should call invalidate_pattern multiple times for different patterns
        assert mock_cache.invalidate_pattern.call_count >= 2


class TestInvalidateClientCache:
    @pytest.mark.asyncio
    async def test_calls_invalidate_for_client(self, mock_cache):
        await invalidate_client_cache("client-456")
        calls = [str(c) for c in mock_cache.invalidate_pattern.call_args_list]
        assert any("client-456" in c for c in calls)

    @pytest.mark.asyncio
    async def test_multiple_patterns(self, mock_cache):
        await invalidate_client_cache("client-xyz")
        assert mock_cache.invalidate_pattern.call_count >= 2


class TestInvalidateResearchCache:
    @pytest.mark.asyncio
    async def test_with_client_id(self, mock_cache):
        await invalidate_research_cache(client_id="client-111")
        calls = [str(c) for c in mock_cache.invalidate_pattern.call_args_list]
        assert any("client-111" in c for c in calls)

    @pytest.mark.asyncio
    async def test_with_project_id(self, mock_cache):
        await invalidate_research_cache(project_id="proj-222")
        calls = [str(c) for c in mock_cache.invalidate_pattern.call_args_list]
        assert any("proj-222" in c for c in calls)

    @pytest.mark.asyncio
    async def test_with_both_ids(self, mock_cache):
        await invalidate_research_cache(client_id="c1", project_id="p1")
        calls = [str(c) for c in mock_cache.invalidate_pattern.call_args_list]
        assert any("c1" in c for c in calls)
        assert any("p1" in c for c in calls)

    @pytest.mark.asyncio
    async def test_no_calls_when_neither_provided(self, mock_cache):
        await invalidate_research_cache()
        mock_cache.invalidate_pattern.assert_not_called()


class TestInvalidateCostCache:
    @pytest.mark.asyncio
    async def test_calls_invalidate_for_user(self, mock_cache):
        await invalidate_cost_cache("user-789")
        calls = [str(c) for c in mock_cache.invalidate_pattern.call_args_list]
        assert any("user-789" in c for c in calls)


class TestInvalidateAllCaches:
    @pytest.mark.asyncio
    async def test_calls_cache_clear(self, mock_cache):
        await invalidate_all_caches()
        mock_cache.clear.assert_called_once()
