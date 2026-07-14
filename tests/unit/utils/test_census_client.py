"""
Unit tests for src/utils/census_client.py
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


from src.utils.census_client import (
    _extract_zip,
    _format_response,
    fetch_zip_demographics,
)

# ---------------------------------------------------------------------------
# Sample Census API response (headers + values row)
# ---------------------------------------------------------------------------
_SAMPLE_RAW = [
    [
        "NAME",
        "B01003_001E",  # total population (all ages)
        "B19013_001E",  # median household income
        "B01002_001E",  # median age
        "B15003_001E",  # population 25+ (education universe)
        "B15003_022E",  # bachelor's
        "B15003_023E",  # master's
        "B15003_024E",  # professional-school
        "B15003_025E",  # doctorate
        "B11001_001E",  # households
        "zip code tabulation area",
    ],
    [
        "ZCTA5 63376",
        "42531",
        "75400",
        "38.5",
        "28000",
        "8100",
        "3200",
        "400",
        "850",
        "16200",
        "63376",
    ],
]


# ---------------------------------------------------------------------------
# _extract_zip
# ---------------------------------------------------------------------------
class TestExtractZip:
    def test_extracts_5_digit_zip(self):
        assert _extract_zip("Wentzville, MO 63376") == "63376"

    def test_extracts_zip_at_start(self):
        assert _extract_zip("63376 Wentzville MO") == "63376"

    def test_returns_none_when_no_zip(self):
        assert _extract_zip("Chicago, Illinois") is None

    def test_does_not_match_4_digit_number(self):
        assert _extract_zip("Suite 1234 Main St") is None

    def test_does_not_match_6_digit_number(self):
        assert _extract_zip("123456 is too long") is None

    def test_handles_empty_string(self):
        assert _extract_zip("") is None


# ---------------------------------------------------------------------------
# _format_response
# ---------------------------------------------------------------------------
class TestFormatResponse:
    def test_returns_none_for_empty_response(self):
        assert _format_response([], "12345") is None

    def test_returns_none_for_single_row(self):
        assert _format_response([["NAME"]], "12345") is None

    def test_includes_zip_in_output(self):
        out = _format_response(_SAMPLE_RAW, "63376")
        assert "63376" in out

    def test_includes_population(self):
        out = _format_response(_SAMPLE_RAW, "63376")
        assert "42,531" in out  # 42531 formatted

    def test_includes_median_income(self):
        out = _format_response(_SAMPLE_RAW, "63376")
        assert "$75,400" in out

    def test_includes_median_age(self):
        out = _format_response(_SAMPLE_RAW, "63376")
        assert "38.5" in out

    def test_includes_college_percentage(self):
        out = _format_response(_SAMPLE_RAW, "63376")
        assert "College-educated" in out
        assert "%" in out

    def test_college_percentage_uses_25plus_universe(self):
        """Bug #62: the college-educated share must divide degree-holders by the
        25+ population (B15003_001E), not the all-ages total, and must include
        professional-school (024E) as well as bachelor's/master's/doctorate."""
        # (8100 + 3200 + 400 + 850) / 28000 = 44.8%  (NOT / 42531 = 29.5%)
        out = _format_response(_SAMPLE_RAW, "63376")
        assert "44.8% of adults 25+" in out

    def test_college_line_skipped_when_25plus_universe_missing(self):
        """If the 25+ universe column is absent, skip the line rather than
        dividing by the wrong denominator."""
        headers = [h for h in _SAMPLE_RAW[0] if h != "B15003_001E"]
        idx = _SAMPLE_RAW[0].index("B15003_001E")
        values = [v for i, v in enumerate(_SAMPLE_RAW[1]) if i != idx]
        out = _format_response([headers, values], "63376")
        assert out is not None
        assert "College-educated" not in out

    def test_handles_negative_income_gracefully(self):
        """Negative values (Census sentinel for N/A) should not crash."""
        raw = [_SAMPLE_RAW[0], list(_SAMPLE_RAW[1])]
        raw[1][2] = "-666666666"  # Census N/A sentinel
        out = _format_response(raw, "63376")
        assert "N/A" in out

    def test_handles_null_values_gracefully(self):
        raw = [_SAMPLE_RAW[0], list(_SAMPLE_RAW[1])]
        raw[1][1] = None
        out = _format_response(raw, "63376")
        assert out is not None  # Should not crash


# ---------------------------------------------------------------------------
# fetch_zip_demographics
# ---------------------------------------------------------------------------
class TestFetchZipDemographics:
    def test_returns_none_when_no_api_key(self):
        result = fetch_zip_demographics("Wentzville, MO 63376", api_key="")
        assert result is None

    def test_returns_none_when_location_has_no_zip(self):
        result = fetch_zip_demographics("Chicago, Illinois", api_key="test-key")
        assert result is None

    def test_returns_formatted_string_on_success(self):
        """Mock urllib to return the sample Census response."""

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(_SAMPLE_RAW).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = fetch_zip_demographics("63376", api_key="abc123")

        assert result is not None
        assert "63376" in result
        assert "42,531" in result

    def test_returns_none_on_network_error(self):
        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            result = fetch_zip_demographics("63376", api_key="abc123")

        assert result is None

    def test_uses_zip_from_complex_location(self):
        """Verify zip extraction works on realistic location strings."""

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(_SAMPLE_RAW).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        captured_url = []

        def fake_urlopen(req, timeout=None):
            captured_url.append(req.full_url)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            fetch_zip_demographics("Wentzville, MO 63376", api_key="abc123")

        assert any("63376" in url for url in captured_url)
