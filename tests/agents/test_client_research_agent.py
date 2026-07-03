"""Unit tests for ClientResearchAgent."""

import asyncio
from dataclasses import dataclass
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from project.src.agents.client_research_agent import (
    ClientResearchAgent,
    ClientResearchResult,
    CREDIT_COST,
)
from project.src.models.client_brief import ClientBrief
from project.src.utils.web_search import SearchResponse, SearchResult


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_search_result(title: str, url: str, snippet: str) -> SearchResult:
    return SearchResult(title=title, url=url, snippet=snippet)


def _make_search_response(query: str, results: List[SearchResult]) -> SearchResponse:
    from datetime import datetime

    return SearchResponse(
        query=query,
        results=results,
        total_results=len(results),
        search_time_ms=100.0,
        timestamp=datetime.now(),
    )


def _make_brief() -> ClientBrief:
    return ClientBrief(
        company_name="Acme Co",
        business_description="A test business",
        ideal_customer="Small business owners",
        main_problem_solved="Time management",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestClientResearchAgent:
    def test_credit_cost_is_200(self):
        assert CREDIT_COST == 200
        assert ClientResearchAgent.CREDIT_COST == 200

    def test_parallel_search_builds_correct_query_count(self):
        agent = ClientResearchAgent.__new__(ClientResearchAgent)
        # Without website: 6 queries
        queries_no_website = [
            f'"Acme" Austin, TX',
            f'"Acme" about founder CEO owner',
            f'"Acme" services products customers',
            f'"Acme" reviews testimonials results',
            f'"Acme" competitors alternatives Austin, TX',
            f'"Acme" site:linkedin.com OR site:instagram.com OR site:facebook.com',
        ]
        assert len(queries_no_website) == 6

    @pytest.mark.asyncio
    async def test_parallel_search_runs_six_queries(self):
        mock_client = MagicMock()
        agent = ClientResearchAgent(client=mock_client)

        results = [_make_search_result("Title", "https://example.com", "snippet")]
        mock_response = _make_search_response("query", results)

        with patch("project.src.agents.client_research_agent.get_search_client") as mock_get:
            mock_search_client = MagicMock()
            mock_search_client.provider = "brave"
            mock_search_client.search.return_value = mock_response
            mock_get.return_value = mock_search_client

            snippets, sources, stub_mode = await agent._parallel_search("Acme", "Austin, TX", None)

            assert mock_search_client.search.call_count == 6
            assert stub_mode is False
            assert len(sources) == 6  # one URL per query (5 results each, but only 1 mock result)

    @pytest.mark.asyncio
    async def test_parallel_search_adds_seventh_query_for_website(self):
        mock_client = MagicMock()
        agent = ClientResearchAgent(client=mock_client)

        mock_response = _make_search_response("query", [])

        with patch("project.src.agents.client_research_agent.get_search_client") as mock_get:
            mock_search_client = MagicMock()
            mock_search_client.provider = "brave"
            mock_search_client.search.return_value = mock_response
            mock_get.return_value = mock_search_client

            await agent._parallel_search("Acme", "Austin", "acme.com")

            assert mock_search_client.search.call_count == 7

    @pytest.mark.asyncio
    async def test_stub_mode_sets_warning(self):
        mock_client = MagicMock()
        agent = ClientResearchAgent(client=mock_client)

        mock_response = _make_search_response("query", [])

        with (
            patch("project.src.agents.client_research_agent.get_search_client") as mock_get,
            patch.object(agent, "_synthesize", return_value=(_make_brief(), {})),
        ):
            mock_search_client = MagicMock()
            mock_search_client.provider = "stub"
            mock_search_client.search.return_value = mock_response
            mock_get.return_value = mock_search_client

            result = await agent.run("Acme", "Austin, TX")

            assert result.stub_mode is True
            assert result.warning is not None
            assert "stub mode" in result.warning.lower()

    @pytest.mark.asyncio
    async def test_real_provider_has_no_warning(self):
        mock_client = MagicMock()
        agent = ClientResearchAgent(client=mock_client)

        mock_response = _make_search_response("query", [])

        with (
            patch("project.src.agents.client_research_agent.get_search_client") as mock_get,
            patch.object(agent, "_synthesize", return_value=(_make_brief(), {})),
        ):
            mock_search_client = MagicMock()
            mock_search_client.provider = "brave"
            mock_search_client.search.return_value = mock_response
            mock_get.return_value = mock_search_client

            result = await agent.run("Acme", "Austin, TX")

            assert result.stub_mode is False
            assert result.warning is None

    @pytest.mark.asyncio
    async def test_run_returns_client_research_result(self):
        mock_client = MagicMock()
        agent = ClientResearchAgent(client=mock_client)

        mock_response = _make_search_response("query", [])

        with (
            patch("project.src.agents.client_research_agent.get_search_client") as mock_get,
            patch.object(
                agent, "_synthesize", return_value=(_make_brief(), {"business_description": 0.9})
            ),
        ):
            mock_search_client = MagicMock()
            mock_search_client.provider = "brave"
            mock_search_client.search.return_value = mock_response
            mock_get.return_value = mock_search_client

            result = await agent.run("Acme", "Austin, TX")

            assert isinstance(result, ClientResearchResult)
            assert isinstance(result.brief, ClientBrief)
            assert isinstance(result.confidence, dict)
            assert isinstance(result.sources, list)
            assert result.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_sources_are_deduplicated(self):
        mock_client = MagicMock()
        agent = ClientResearchAgent(client=mock_client)

        # Same URL in two results
        dup_result = _make_search_result("Title", "https://example.com", "snippet")
        mock_response = _make_search_response("query", [dup_result, dup_result])

        with (
            patch("project.src.agents.client_research_agent.get_search_client") as mock_get,
            patch.object(agent, "_synthesize", return_value=(_make_brief(), {})),
        ):
            mock_search_client = MagicMock()
            mock_search_client.provider = "brave"
            mock_search_client.search.return_value = mock_response
            mock_get.return_value = mock_search_client

            result = await agent.run("Acme", "Austin, TX")

            assert result.sources.count("https://example.com") == 1

    @pytest.mark.asyncio
    async def test_failed_search_query_is_skipped(self):
        mock_client = MagicMock()
        agent = ClientResearchAgent(client=mock_client)

        call_count = 0

        def sometimes_fail(query, max_results):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise Exception("Search provider error")
            from datetime import datetime

            return SearchResponse(
                query=query, results=[], total_results=0, search_time_ms=0, timestamp=datetime.now()
            )

        with (
            patch("project.src.agents.client_research_agent.get_search_client") as mock_get,
            patch.object(agent, "_synthesize", return_value=(_make_brief(), {})),
        ):
            mock_search_client = MagicMock()
            mock_search_client.provider = "brave"
            mock_search_client.search.side_effect = sometimes_fail
            mock_get.return_value = mock_search_client

            # Should not raise — failed queries are skipped
            result = await agent.run("Acme", "Austin, TX")
            assert isinstance(result, ClientResearchResult)

    def test_synthesize_returns_brief_and_confidence(self):
        mock_client = MagicMock()
        agent = ClientResearchAgent(client=mock_client)

        synthesized_json = {
            "brief": {
                "company_name": "Acme",
                "business_description": "We help small businesses.",
                "ideal_customer": "SMB owners",
                "main_problem_solved": "Time",
                "target_platforms": [],
                "keywords": [],
                "competitors": [],
                "customer_pain_points": [],
                "customer_questions": [],
                "brand_personality": [],
                "key_phrases": [],
                "stories": [],
                "misconceptions": [],
                "data_usage": "moderate",
            },
            "confidence": {
                "business_description": 0.9,
                "ideal_customer": 0.7,
            },
        }

        with patch(
            "project.src.agents.client_research_agent.call_claude_api",
            return_value=synthesized_json,
        ):
            brief, confidence = agent._synthesize("Acme", "Austin", [])

        assert isinstance(brief, ClientBrief)
        assert brief.company_name == "Acme"
        assert confidence["business_description"] == 0.9

    def test_synthesize_handles_empty_api_response(self):
        mock_client = MagicMock()
        agent = ClientResearchAgent(client=mock_client)

        with patch("project.src.agents.client_research_agent.call_claude_api", return_value={}):
            brief, confidence = agent._synthesize("Acme", "Austin", [])

        assert isinstance(brief, ClientBrief)
        assert isinstance(confidence, dict)
