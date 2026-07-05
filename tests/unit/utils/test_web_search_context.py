"""
Unit tests for src/utils/web_search_context.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from src.utils.web_search import SearchResponse, SearchResult, WebSearchClient
from src.utils.web_search_context import (
    MAX_SEARCHES_PER_RUN,
    TEMPLATE_WEB_SEARCH_CONFIG,
    _format_results,
    build_web_search_context,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_response(results: list[dict]) -> SearchResponse:
    return SearchResponse(
        query="test query",
        results=[
            SearchResult(
                title=r["title"],
                url=r.get("url", "https://example.com"),
                snippet=r["snippet"],
                published_date=r.get("published_date"),
                source=r.get("source"),
            )
            for r in results
        ],
        total_results=len(results),
        search_time_ms=100.0,
        timestamp=datetime.utcnow(),
    )


def _stub_client() -> WebSearchClient:
    client = MagicMock(spec=WebSearchClient)
    client.provider = "stub"
    return client


def _real_client(results: list[dict]) -> WebSearchClient:
    client = MagicMock(spec=WebSearchClient)
    client.provider = "brave"
    client.search.return_value = _make_response(results)
    return client


# ---------------------------------------------------------------------------
# TEMPLATE_WEB_SEARCH_CONFIG
# ---------------------------------------------------------------------------


class TestConfig:
    def test_enabled_template_ids_present(self):
        assert 2 in TEMPLATE_WEB_SEARCH_CONFIG  # Statistic + Insight
        assert 3 in TEMPLATE_WEB_SEARCH_CONFIG  # Contrarian Take
        assert 13 in TEMPLATE_WEB_SEARCH_CONFIG  # Future Thinking

    def test_non_web_search_templates_absent(self):
        assert 6 not in TEMPLATE_WEB_SEARCH_CONFIG  # Personal Story — no web search
        assert 8 not in TEMPLATE_WEB_SEARCH_CONFIG  # Things I Got Wrong
        assert 15 not in TEMPLATE_WEB_SEARCH_CONFIG  # Milestone

    def test_each_config_has_required_keys(self):
        required = {"query_template", "fallback_query", "focus", "max_results"}
        for tid, cfg in TEMPLATE_WEB_SEARCH_CONFIG.items():
            missing = required - set(cfg.keys())
            assert not missing, f"Template {tid} config missing keys: {missing}"

    def test_max_results_reasonable(self):
        for cfg in TEMPLATE_WEB_SEARCH_CONFIG.values():
            assert 1 <= cfg["max_results"] <= 10


# ---------------------------------------------------------------------------
# build_web_search_context
# ---------------------------------------------------------------------------


class TestBuildWebSearchContext:
    def test_returns_none_for_unknown_template(self):
        result = build_web_search_context(99, "technology")
        assert result is None

    def test_returns_none_when_stub_client(self):
        result = build_web_search_context(2, "dental", web_search_client=_stub_client())
        assert result is None

    def test_returns_formatted_string_with_real_client(self):
        client = _real_client(
            [
                {
                    "title": "Dental Stats 2025",
                    "snippet": "87% of people use AI.",
                    "source": "Forbes",
                },
            ]
        )
        result = build_web_search_context(2, "dental", web_search_client=client)
        assert result is not None
        assert "Dental Stats 2025" in result
        assert "Forbes" in result

    def test_uses_industry_in_query(self):
        client = _real_client([{"title": "X", "snippet": "Y"}])
        build_web_search_context(2, "real estate", web_search_client=client)
        call_args = client.search.call_args
        assert "real estate" in call_args[0][0]

    def test_uses_fallback_query_when_no_industry(self):
        client = _real_client([{"title": "X", "snippet": "Y"}])
        build_web_search_context(2, None, web_search_client=client)
        call_args = client.search.call_args
        # fallback_query should NOT contain a placeholder
        assert "{industry}" not in call_args[0][0]

    def test_returns_none_on_empty_results(self):
        client = _real_client([])
        result = build_web_search_context(2, "tech", web_search_client=client)
        assert result is None

    def test_returns_none_on_search_exception(self):
        client = MagicMock(spec=WebSearchClient)
        client.provider = "tavily"
        client.search.side_effect = RuntimeError("network error")
        result = build_web_search_context(2, "tech", web_search_client=client)
        assert result is None

    def test_max_results_respected(self):
        """Should not request more results than config says."""
        client = _real_client([{"title": f"T{i}", "snippet": "S"} for i in range(10)])
        build_web_search_context(2, "tech", web_search_client=client)
        _, kwargs = client.search.call_args
        assert kwargs.get("max_results", 10) <= TEMPLATE_WEB_SEARCH_CONFIG[2]["max_results"]


# ---------------------------------------------------------------------------
# _format_results
# ---------------------------------------------------------------------------


class TestFormatResults:
    def test_returns_none_for_empty_results(self):
        resp = _make_response([])
        assert _format_results(resp, "statistics") is None

    def test_includes_title_and_snippet(self):
        resp = _make_response([{"title": "Big Data 2025", "snippet": "AI usage hit 72%."}])
        out = _format_results(resp, "data")
        assert "Big Data 2025" in out
        assert "AI usage hit 72%." in out

    def test_includes_source_when_present(self):
        resp = _make_response([{"title": "T", "snippet": "S", "source": "Harvard Business Review"}])
        out = _format_results(resp, "data")
        assert "Harvard Business Review" in out

    def test_includes_date_when_present(self):
        resp = _make_response([{"title": "T", "snippet": "S", "published_date": "2025-03-15"}])
        out = _format_results(resp, "data")
        assert "2025-03-15" in out

    def test_caps_at_five_results(self):
        resp = _make_response([{"title": f"T{i}", "snippet": "S"} for i in range(10)])
        out = _format_results(resp, "data")
        # Only entries 1–5 should appear
        assert "5." in out
        assert "6." not in out

    def test_truncates_long_snippets(self):
        long_snippet = "X" * 300
        resp = _make_response([{"title": "T", "snippet": long_snippet}])
        out = _format_results(resp, "data")
        # Snippet in output should be ≤ 203 chars (200 + "...")
        lines = out.splitlines()
        content_line = next(l for l in lines if "T:" in l)
        snippet_part = content_line.split("T:", 1)[1].strip()
        assert len(snippet_part) <= 203


# ---------------------------------------------------------------------------
# MAX_SEARCHES_PER_RUN
# ---------------------------------------------------------------------------


def test_max_searches_per_run_is_positive():
    assert MAX_SEARCHES_PER_RUN > 0


def test_max_searches_per_run_not_excessive():
    assert MAX_SEARCHES_PER_RUN <= 15
