"""Unit tests for DataForSEOClient."""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(values: list[int], status_code: int = 200) -> MagicMock:
    """Build a mock requests.Response with the actual DataForSEO shape.

    Per docs: data[n].values is a plain integer array [N], not [{"value": N}].
    """
    data_points = [
        {
            "date_from": f"2025-{i:02d}-01",
            "date_to": f"2025-{i:02d}-07",
            "timestamp": 1700000000 + i,
            "missing_data": False,
            "values": [v],
        }
        for i, v in enumerate(values, 1)
    ]
    body = {
        "tasks": [
            {
                "result": [
                    {
                        "items": [
                            {
                                "data": data_points,
                            }
                        ]
                    }
                ]
            }
        ]
    }
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        from requests.exceptions import HTTPError

        resp.raise_for_status.side_effect = HTTPError(f"{status_code} error")
    return resp


# ---------------------------------------------------------------------------
# configured property
# ---------------------------------------------------------------------------


class TestConfigured:
    def test_false_when_both_absent(self, monkeypatch):
        monkeypatch.setenv("DATAFORSEO_LOGIN", "")
        monkeypatch.setenv("DATAFORSEO_PASSWORD", "")
        with patch("backend.config.settings") as mock_settings:
            mock_settings.DATAFORSEO_LOGIN = ""
            mock_settings.DATAFORSEO_PASSWORD = ""
            from src.utils.dataforseo_client import DataForSEOClient

            client = DataForSEOClient.__new__(DataForSEOClient)
            client._login = ""
            client._password = ""
            assert client.configured is False

    def test_false_when_password_absent(self):
        from src.utils.dataforseo_client import DataForSEOClient

        client = DataForSEOClient.__new__(DataForSEOClient)
        client._login = "user@example.com"
        client._password = ""
        assert client.configured is False

    def test_true_when_both_present(self):
        from src.utils.dataforseo_client import DataForSEOClient

        client = DataForSEOClient.__new__(DataForSEOClient)
        client._login = "user@example.com"
        client._password = "secret"
        assert client.configured is True


# ---------------------------------------------------------------------------
# get_trends — not configured
# ---------------------------------------------------------------------------


class TestGetTrendsNotConfigured:
    def test_returns_none_without_http_call(self):
        from src.utils.dataforseo_client import DataForSEOClient

        client = DataForSEOClient.__new__(DataForSEOClient)
        client._login = ""
        client._password = ""

        with patch("requests.post") as mock_post:
            result = client.get_trends("dentistry")
        assert result is None
        mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# get_trends — success path
# ---------------------------------------------------------------------------


class TestGetTrendsSuccess:
    def _client(self):
        from src.utils.dataforseo_client import DataForSEOClient

        client = DataForSEOClient.__new__(DataForSEOClient)
        client._login = "user@example.com"
        client._password = "secret"
        return client

    def test_returns_trend_score_as_mean_of_last_4(self):
        # 8 values: older=[10,20,30,40], recent=[60,70,80,90]
        values = [10, 20, 30, 40, 60, 70, 80, 90]
        with patch("requests.post", return_value=_make_response(values)):
            result = self._client().get_trends("family dentist")
        assert result is not None
        assert result["trend_score"] == pytest.approx(75.0)  # mean(60,70,80,90)

    def test_direction_rising_when_recent_20pct_above_older(self):
        # older mean=50, recent mean=65 → 65/50=1.3 > 1.2 → rising
        values = [40, 50, 60, 50, 60, 65, 70, 65]
        with patch("requests.post", return_value=_make_response(values)):
            result = self._client().get_trends("keyword")
        assert result["trend_direction"] == "rising"

    def test_direction_declining_when_recent_20pct_below_older(self):
        # older mean=80, recent mean=60 → 60/80=0.75 < 0.8 → declining
        values = [80, 80, 80, 80, 60, 60, 60, 60]
        with patch("requests.post", return_value=_make_response(values)):
            result = self._client().get_trends("keyword")
        assert result["trend_direction"] == "declining"

    def test_direction_stable_when_within_20pct(self):
        values = [50, 50, 50, 50, 55, 55, 55, 55]
        with patch("requests.post", return_value=_make_response(values)):
            result = self._client().get_trends("keyword")
        assert result["trend_direction"] == "stable"

    def test_direction_seasonal_when_high_variance(self):
        # stdev > 25 triggers seasonal
        values = [10, 90, 10, 90, 10, 90, 10, 90]
        with patch("requests.post", return_value=_make_response(values)):
            result = self._client().get_trends("keyword")
        assert result["trend_direction"] == "seasonal"

    def test_trend_momentum_score_equals_trend_score(self):
        values = [50] * 8
        with patch("requests.post", return_value=_make_response(values)):
            result = self._client().get_trends("keyword")
        assert result["trend_momentum_score"] == result["trend_score"]

    def test_direction_stable_when_fewer_than_8_points(self):
        # Only 4 values — can't compare older vs recent, defaults to stable
        values = [60, 70, 80, 90]
        with patch("requests.post", return_value=_make_response(values)):
            result = self._client().get_trends("keyword")
        assert result is not None
        assert result["trend_direction"] == "stable"

    def test_posts_to_correct_url_with_auth(self):
        values = [50] * 8
        with patch("requests.post", return_value=_make_response(values)) as mock_post:
            self._client().get_trends("dentist")
        call_kwargs = mock_post.call_args
        assert call_kwargs[0][0] == DataForSEOClient._BASE_URL
        assert call_kwargs[1]["auth"] == ("user@example.com", "secret")

    def test_payload_contains_keyword_and_location(self):
        values = [50] * 8
        with patch("requests.post", return_value=_make_response(values)) as mock_post:
            self._client().get_trends("dentist near me")
        payload = mock_post.call_args[1]["json"]
        assert payload[0]["keywords"] == ["dentist near me"]
        assert payload[0]["location_code"] == 2840
        assert payload[0]["language_code"] == "en"


# Needed for the URL assertion above
from src.utils.dataforseo_client import DataForSEOClient  # noqa: E402


# ---------------------------------------------------------------------------
# get_trends — error paths
# ---------------------------------------------------------------------------


class TestGetTrendsErrors:
    def _client(self):
        from src.utils.dataforseo_client import DataForSEOClient

        client = DataForSEOClient.__new__(DataForSEOClient)
        client._login = "user@example.com"
        client._password = "secret"
        return client

    def test_returns_none_on_http_error(self):
        with patch("requests.post", return_value=_make_response([], status_code=401)):
            result = self._client().get_trends("keyword")
        assert result is None

    def test_returns_none_on_network_exception(self):
        import requests as req_lib

        with patch("requests.post", side_effect=req_lib.exceptions.ConnectionError("timeout")):
            result = self._client().get_trends("keyword")
        assert result is None

    def test_returns_none_when_items_empty(self):
        body = {"tasks": [{"result": [{"items": []}]}]}
        resp = MagicMock()
        resp.json.return_value = body
        resp.raise_for_status = MagicMock()
        with patch("requests.post", return_value=resp):
            result = self._client().get_trends("keyword")
        assert result is None

    def test_returns_none_when_fewer_than_4_data_points(self):
        values = [50, 60, 70]  # only 3
        with patch("requests.post", return_value=_make_response(values)):
            result = self._client().get_trends("keyword")
        assert result is None

    def test_returns_none_on_malformed_response(self):
        resp = MagicMock()
        resp.json.return_value = {"unexpected": "shape"}
        resp.raise_for_status = MagicMock()
        with patch("requests.post", return_value=resp):
            result = self._client().get_trends("keyword")
        assert result is None

    def test_does_not_raise_on_any_error(self):
        with patch("requests.post", side_effect=Exception("boom")):
            # must not propagate — enrichment is optional
            result = self._client().get_trends("keyword")
        assert result is None


# ---------------------------------------------------------------------------
# Regression tests for specific response-shape bugs
# ---------------------------------------------------------------------------


class TestParseResponseShape:
    """Regression tests that pin the exact response shape the API actually returns.

    These tests call _parse_response directly so a shape change immediately
    breaks them — even if the higher-level helper is updated to match.
    """

    def _client(self):
        from src.utils.dataforseo_client import DataForSEOClient

        c = DataForSEOClient.__new__(DataForSEOClient)
        c._login = "u"
        c._password = "p"
        return c

    def _body(self, data_points):
        return {"tasks": [{"result": [{"items": [{"data": data_points}]}]}]}

    def test_values_is_plain_integer_array_not_object_array(self):
        """Regression: values:[N] not values:[{"value":N}].

        The original bug — pt["values"][0]["value"] — always raised TypeError
        because pt["values"][0] is an int, not a dict. This test fails if that
        bug is reintroduced.
        """
        # Correct shape: values is [integer]
        data_points = [
            {
                "date_from": "2025-01-01",
                "date_to": "2025-01-07",
                "missing_data": False,
                "values": [v],
            }
            for v in [50, 55, 60, 65, 70, 75, 80, 85]
        ]
        result = self._client()._parse_response("dentist", self._body(data_points))
        assert result is not None, (
            "Parser returned None — likely regressed to values[0]['value'] "
            "subscript on an integer"
        )
        assert result["trend_score"] == pytest.approx(77.5)  # mean(70,75,80,85)

    def test_old_object_array_shape_returns_none(self):
        """Confirm the old wrong shape [{"value":N}] is correctly rejected."""
        data_points = [
            {
                "date_from": "2025-01-01",
                "date_to": "2025-01-07",
                "missing_data": False,
                "values": [{"value": v}],
            }
            for v in [50, 55, 60, 65, 70, 75, 80, 85]
        ]
        result = self._client()._parse_response("dentist", self._body(data_points))
        # int({"value": 50}) raises TypeError → caught → returns None
        assert result is None

    def test_missing_data_points_excluded(self):
        """Points with missing_data:true must be skipped."""
        data_points = [
            {"date_from": "2025-01-01", "missing_data": True, "values": [99]},
            {"date_from": "2025-01-08", "missing_data": False, "values": [50]},
            {"date_from": "2025-01-15", "missing_data": False, "values": [60]},
            {"date_from": "2025-01-22", "missing_data": False, "values": [70]},
            {"date_from": "2025-01-29", "missing_data": False, "values": [80]},
        ]
        result = self._client()._parse_response("dentist", self._body(data_points))
        # 99 must not influence the score — only the 4 non-missing values count
        assert result is not None
        assert result["trend_score"] == pytest.approx(65.0)  # mean(50,60,70,80)
