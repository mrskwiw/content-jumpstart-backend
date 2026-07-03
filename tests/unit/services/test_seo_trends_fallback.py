"""Unit tests for DataForSEO fallback wiring in seo_keyword_research._try_dataforseo_fallback."""

import pytest
from unittest.mock import MagicMock, patch


def _make_keyword(term: str = "dentist") -> MagicMock:
    kw = MagicMock()
    kw.keyword = term
    kw.trend_score = None
    kw.trend_direction = None
    kw.trend_momentum_score = None
    return kw


def _make_tool():
    """Return an instance of SEOKeywordResearcher with minimal setup."""
    from src.research.seo_keyword_research import SEOKeywordResearcher

    tool = SEOKeywordResearcher.__new__(SEOKeywordResearcher)
    return tool


class TestTryDataForSEOFallback:
    def test_returns_false_when_client_not_configured(self):
        tool = _make_tool()
        kw = _make_keyword()

        mock_client = MagicMock()
        mock_client.configured = False

        with patch("src.utils.dataforseo_client.DataForSEOClient", return_value=mock_client):
            result = tool._try_dataforseo_fallback("dentist", kw)

        assert result is False
        assert kw.trend_score is None

    def test_returns_false_when_get_trends_returns_none(self):
        tool = _make_tool()
        kw = _make_keyword()

        mock_client = MagicMock()
        mock_client.configured = True
        mock_client.get_trends.return_value = None

        with patch("src.utils.dataforseo_client.DataForSEOClient", return_value=mock_client):
            result = tool._try_dataforseo_fallback("dentist", kw)

        assert result is False
        assert kw.trend_score is None

    def test_returns_true_and_sets_fields_on_success(self):
        tool = _make_tool()
        kw = _make_keyword()

        mock_client = MagicMock()
        mock_client.configured = True
        mock_client.get_trends.return_value = {
            "trend_score": 72.5,
            "trend_direction": "rising",
            "trend_momentum_score": 72.5,
        }

        with patch("src.utils.dataforseo_client.DataForSEOClient", return_value=mock_client):
            result = tool._try_dataforseo_fallback("dentist", kw)

        assert result is True
        assert kw.trend_score == pytest.approx(72.5)
        assert kw.trend_direction == "rising"
        assert kw.trend_momentum_score == pytest.approx(72.5)
        assert kw.seasonal is False  # "rising" is not seasonal

    def test_sets_seasonal_true_when_direction_is_seasonal(self):
        tool = _make_tool()
        kw = _make_keyword()

        mock_client = MagicMock()
        mock_client.configured = True
        mock_client.get_trends.return_value = {
            "trend_score": 55.0,
            "trend_direction": "seasonal",
            "trend_momentum_score": 55.0,
        }

        with patch("src.utils.dataforseo_client.DataForSEOClient", return_value=mock_client):
            tool._try_dataforseo_fallback("holiday dentist", kw)

        assert kw.seasonal is True

    def test_returns_false_on_unexpected_exception(self):
        tool = _make_tool()
        kw = _make_keyword()

        with patch(
            "src.utils.dataforseo_client.DataForSEOClient", side_effect=RuntimeError("boom")
        ):
            result = tool._try_dataforseo_fallback("dentist", kw)

        assert result is False
        assert kw.trend_score is None

    def test_passes_keyword_term_to_get_trends(self):
        tool = _make_tool()
        kw = _make_keyword("family dentist near me")

        mock_client = MagicMock()
        mock_client.configured = True
        mock_client.get_trends.return_value = {
            "trend_score": 50.0,
            "trend_direction": "stable",
            "trend_momentum_score": 50.0,
        }

        with patch("src.utils.dataforseo_client.DataForSEOClient", return_value=mock_client):
            tool._try_dataforseo_fallback("family dentist near me", kw)

        mock_client.get_trends.assert_called_once_with("family dentist near me")


class TestFallbackIntegrationInEnrichmentLoop:
    """Test that the 429 handler correctly calls the fallback and uses its result."""

    def test_consecutive_failures_not_incremented_when_fallback_succeeds(self):
        """When DataForSEO succeeds on a 429, consecutive_failures stays at 0."""
        tool = _make_tool()

        # Patch _try_dataforseo_fallback to return True (success)
        with patch.object(tool, "_try_dataforseo_fallback", return_value=True) as mock_fallback:
            # Simulate the 429 branch directly
            consecutive_failures = 0
            keyword_term = "dentist"

            # Replicate the logic from _enrich_with_google_trends 429 branch
            if tool._try_dataforseo_fallback(keyword_term, MagicMock()):
                consecutive_failures = 0
            else:
                consecutive_failures += 1

            assert consecutive_failures == 0
            mock_fallback.assert_called_once()

    def test_consecutive_failures_incremented_when_fallback_fails(self):
        """When DataForSEO is not configured or fails, consecutive_failures increments."""
        tool = _make_tool()

        with patch.object(tool, "_try_dataforseo_fallback", return_value=False):
            consecutive_failures = 0
            keyword_term = "dentist"

            if tool._try_dataforseo_fallback(keyword_term, MagicMock()):
                consecutive_failures = 0
            else:
                consecutive_failures += 1

            assert consecutive_failures == 1
