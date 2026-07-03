"""
Unit tests for Google Maps search utility (SerpAPI).

Covers GoogleMapsPlace, GoogleMapsReview, PlaceWithReviews dataclasses,
GoogleMapsClient (search_local_businesses, get_place_reviews),
and the get_google_maps_client singleton helper.

All external HTTP calls are mocked — no real network traffic.
"""

import pytest
from unittest.mock import Mock, patch
import requests

from src.utils.google_maps_search import (
    GoogleMapsPlace,
    GoogleMapsReview,
    PlaceWithReviews,
    GoogleMapsClient,
    get_google_maps_client,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_default_client():
    """Reset the module-level singleton before each test."""
    import src.utils.google_maps_search as gm_module

    gm_module._default_client = None
    yield
    gm_module._default_client = None


@pytest.fixture
def serpapi_local_results():
    """Realistic SerpAPI google_maps response payload."""
    return {
        "local_results": [
            {
                "place_id": "place_abc123",
                "title": "Acme Coffee Co.",
                "address": "123 Main St, San Francisco, CA",
                "rating": 4.5,
                "reviews": 312,
                "phone": "+1-415-555-0100",
                "website": "https://acmecoffee.example.com",
                "type": "Coffee Shop",
                "hours": "Open · Closes 8 PM",
                "gps_coordinates": {"latitude": 37.7749, "longitude": -122.4194},
            },
            {
                "place_id": "place_def456",
                "title": "Blue Bottle",
                "address": "456 Market St, San Francisco, CA",
                "rating": 4.2,
                "reviews": 198,
                "phone": "+1-415-555-0200",
                "website": "https://bluebottle.example.com",
                "type": "Coffee Shop",
                "hours": "Open · Closes 7 PM",
                "gps_coordinates": {"latitude": 37.7905, "longitude": -122.4035},
            },
        ]
    }


@pytest.fixture
def serpapi_reviews_response():
    """Realistic SerpAPI google_maps_reviews response payload."""
    return {
        "place_info": {
            "title": "Acme Coffee Co.",
            "address": "123 Main St, San Francisco, CA",
            "rating": 4.5,
            "reviews": 312,
        },
        "reviews": [
            {
                "user": {"name": "Alice"},
                "rating": 5,
                "snippet": "Best coffee in the city!",
                "date": "2 weeks ago",
                "likes": 12,
            },
            {
                "user": {"name": "Bob"},
                "rating": 4,
                "snippet": "Good espresso, a bit pricey.",
                "date": "1 month ago",
                "likes": 3,
            },
        ],
    }


def _make_mock_response(json_data, status_code=200):
    """Build a mock requests.Response object."""
    mock_resp = Mock()
    mock_resp.json.return_value = json_data
    mock_resp.status_code = status_code
    mock_resp.raise_for_status.return_value = None
    return mock_resp


# ---------------------------------------------------------------------------
# Dataclass smoke tests
# ---------------------------------------------------------------------------


class TestGoogleMapsPlace:
    """Tests for the GoogleMapsPlace dataclass."""

    def test_required_fields(self):
        place = GoogleMapsPlace(place_id="id1", name="Shop", address="1 Main St")
        assert place.place_id == "id1"
        assert place.name == "Shop"
        assert place.address == "1 Main St"

    def test_optional_fields_default_none(self):
        place = GoogleMapsPlace(place_id="id1", name="Shop", address="1 Main St")
        assert place.rating is None
        assert place.reviews_count is None
        assert place.phone is None
        assert place.website is None
        assert place.category is None
        assert place.hours is None
        assert place.latitude is None
        assert place.longitude is None

    def test_all_fields(self):
        place = GoogleMapsPlace(
            place_id="id2",
            name="Cafe",
            address="2 Elm St",
            rating=4.7,
            reviews_count=500,
            phone="+1-555-0100",
            website="https://cafe.example.com",
            category="Cafe",
            hours="Open",
            latitude=37.77,
            longitude=-122.42,
        )
        assert place.rating == 4.7
        assert place.reviews_count == 500
        assert place.latitude == 37.77
        assert place.longitude == -122.42


class TestGoogleMapsReview:
    """Tests for the GoogleMapsReview dataclass."""

    def test_required_fields(self):
        review = GoogleMapsReview(author="Alice", rating=5, text="Great!")
        assert review.author == "Alice"
        assert review.rating == 5
        assert review.text == "Great!"

    def test_optional_fields_default_none(self):
        review = GoogleMapsReview(author="Alice", rating=5, text="Great!")
        assert review.date is None
        assert review.likes is None

    def test_all_fields(self):
        review = GoogleMapsReview(
            author="Bob", rating=3, text="Average.", date="1 week ago", likes=7
        )
        assert review.date == "1 week ago"
        assert review.likes == 7


class TestPlaceWithReviews:
    """Tests for the PlaceWithReviews dataclass."""

    def test_basic_construction(self):
        place = GoogleMapsPlace(place_id="p1", name="Spot", address="3 Oak Ave")
        reviews = [GoogleMapsReview(author="Carol", rating=4, text="Nice.")]
        pwr = PlaceWithReviews(place=place, reviews=reviews, total_reviews=100)
        assert pwr.place is place
        assert len(pwr.reviews) == 1
        assert pwr.total_reviews == 100


# ---------------------------------------------------------------------------
# GoogleMapsClient — initialization
# ---------------------------------------------------------------------------


class TestGoogleMapsClientInit:
    """Tests for GoogleMapsClient.__init__."""

    def test_explicit_api_key(self):
        client = GoogleMapsClient(api_key="mykey")
        assert client.api_key == "mykey"

    @patch.dict("os.environ", {"SERPAPI_API_KEY": "env_key"})
    def test_api_key_from_env(self):
        client = GoogleMapsClient()
        assert client.api_key == "env_key"

    @patch.dict("os.environ", {}, clear=True)
    def test_no_api_key_logs_warning(self):
        with patch("src.utils.google_maps_search.logger") as mock_logger:
            client = GoogleMapsClient()
            assert client.api_key is None
            mock_logger.warning.assert_called_once()

    def test_explicit_key_overrides_env(self):
        with patch.dict("os.environ", {"SERPAPI_API_KEY": "env_key"}):
            client = GoogleMapsClient(api_key="explicit_key")
            assert client.api_key == "explicit_key"


# ---------------------------------------------------------------------------
# GoogleMapsClient.search_local_businesses — lines 89–131
# ---------------------------------------------------------------------------


class TestSearchLocalBusinesses:
    """Tests for GoogleMapsClient.search_local_businesses (lines 89–131)."""

    # --- guard: no API key ---

    def test_returns_empty_list_when_no_api_key(self):
        """Line 85-87: early return when api_key is falsy."""
        with patch.dict("os.environ", {}, clear=True):
            client = GoogleMapsClient()
        result = client.search_local_businesses("coffee", "San Francisco, CA")
        assert result == []

    def test_no_api_key_logs_warning(self):
        with patch.dict("os.environ", {}, clear=True):
            client = GoogleMapsClient()
        with patch("src.utils.google_maps_search.logger") as mock_logger:
            client.search_local_businesses("coffee", "San Francisco, CA")
            mock_logger.warning.assert_called()

    # --- successful path (lines 89–128) ---

    @patch("requests.get")
    def test_successful_search_returns_places(self, mock_get, serpapi_local_results):
        """Lines 104–127: happy-path parses local_results correctly."""
        mock_get.return_value = _make_mock_response(serpapi_local_results)
        client = GoogleMapsClient(api_key="key123")

        places = client.search_local_businesses("coffee shops", "San Francisco, CA")

        assert len(places) == 2
        p = places[0]
        assert isinstance(p, GoogleMapsPlace)
        assert p.place_id == "place_abc123"
        assert p.name == "Acme Coffee Co."
        assert p.address == "123 Main St, San Francisco, CA"
        assert p.rating == 4.5
        assert p.reviews_count == 312
        assert p.phone == "+1-415-555-0100"
        assert p.website == "https://acmecoffee.example.com"
        assert p.category == "Coffee Shop"
        assert p.hours == "Open · Closes 8 PM"
        assert p.latitude == 37.7749
        assert p.longitude == -122.4194

    @patch("requests.get")
    def test_correct_api_params_sent(self, mock_get, serpapi_local_results):
        """Lines 92–104: correct parameters are passed to requests.get."""
        mock_get.return_value = _make_mock_response(serpapi_local_results)
        client = GoogleMapsClient(api_key="key123")

        client.search_local_businesses("marketing agencies", "New York", max_results=5)

        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        params = kwargs["params"]
        assert params["engine"] == "google_maps"
        assert params["q"] == "marketing agencies near New York"
        assert params["type"] == "search"
        assert params["api_key"] == "key123"
        assert params["num"] == 5

    @patch("requests.get")
    def test_serpapi_url_correct(self, mock_get, serpapi_local_results):
        mock_get.return_value = _make_mock_response(serpapi_local_results)
        client = GoogleMapsClient(api_key="key")
        client.search_local_businesses("gyms", "Austin, TX")

        args, _ = mock_get.call_args
        assert args[0] == "https://serpapi.com/search"

    @patch("requests.get")
    def test_request_timeout_is_set(self, mock_get, serpapi_local_results):
        """Line 104: timeout=15 must be passed."""
        mock_get.return_value = _make_mock_response(serpapi_local_results)
        client = GoogleMapsClient(api_key="key")
        client.search_local_businesses("yoga", "Denver, CO")

        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 15

    @patch("requests.get")
    def test_max_results_limit_respected(self, mock_get):
        """Lines 110: slice [:max_results] trims oversized responses."""
        many_results = {
            "local_results": [
                {
                    "place_id": f"pid{i}",
                    "title": f"Place {i}",
                    "address": f"{i} St",
                }
                for i in range(20)
            ]
        }
        mock_get.return_value = _make_mock_response(many_results)
        client = GoogleMapsClient(api_key="key")

        places = client.search_local_businesses("restaurants", "Seattle", max_results=3)

        assert len(places) == 3

    @patch("requests.get")
    def test_empty_local_results_key(self, mock_get):
        """Lines 110: missing local_results key → empty list (no crash)."""
        mock_get.return_value = _make_mock_response({})
        client = GoogleMapsClient(api_key="key")

        places = client.search_local_businesses("shops", "Portland")

        assert places == []

    @patch("requests.get")
    def test_empty_local_results_list(self, mock_get):
        """Lines 110: local_results exists but is empty."""
        mock_get.return_value = _make_mock_response({"local_results": []})
        client = GoogleMapsClient(api_key="key")

        places = client.search_local_businesses("shops", "Portland")

        assert places == []

    @patch("requests.get")
    def test_place_missing_optional_fields(self, mock_get):
        """Lines 111–124: item with only mandatory fields doesn't crash."""
        minimal = {
            "local_results": [{"place_id": "p1", "title": "Minimal Place", "address": "1 A St"}]
        }
        mock_get.return_value = _make_mock_response(minimal)
        client = GoogleMapsClient(api_key="key")

        places = client.search_local_businesses("x", "y")

        assert len(places) == 1
        p = places[0]
        assert p.rating is None
        assert p.reviews_count is None
        assert p.phone is None
        assert p.website is None
        assert p.category is None
        assert p.hours is None
        assert p.latitude is None
        assert p.longitude is None

    @patch("requests.get")
    def test_place_with_empty_gps_coordinates(self, mock_get):
        """Lines 121–122: gps_coordinates present but empty dict → None."""
        data = {
            "local_results": [
                {
                    "place_id": "p1",
                    "title": "No GPS",
                    "address": "1 B St",
                    "gps_coordinates": {},
                }
            ]
        }
        mock_get.return_value = _make_mock_response(data)
        client = GoogleMapsClient(api_key="key")

        places = client.search_local_businesses("x", "y")

        assert places[0].latitude is None
        assert places[0].longitude is None

    @patch("requests.get")
    def test_logs_result_count(self, mock_get, serpapi_local_results):
        """Line 126: info log emitted with correct count."""
        mock_get.return_value = _make_mock_response(serpapi_local_results)
        client = GoogleMapsClient(api_key="key")

        with patch("src.utils.google_maps_search.logger") as mock_logger:
            client.search_local_businesses("coffee", "SF")
            info_calls = [str(c) for c in mock_logger.info.call_args_list]
            assert any("2" in msg for msg in info_calls)

    # --- exception path (lines 129–131) ---

    @patch("requests.get")
    def test_http_error_returns_empty_list(self, mock_get):
        """Lines 129–131: HTTPError → returns [] without propagating."""
        mock_get.side_effect = requests.HTTPError("503 Service Unavailable")
        client = GoogleMapsClient(api_key="key")

        result = client.search_local_businesses("food", "Chicago")

        assert result == []

    @patch("requests.get")
    def test_connection_error_returns_empty_list(self, mock_get):
        """Lines 129–131: ConnectionError → returns []."""
        mock_get.side_effect = requests.ConnectionError("No route to host")
        client = GoogleMapsClient(api_key="key")

        result = client.search_local_businesses("bars", "Miami")

        assert result == []

    @patch("requests.get")
    def test_timeout_error_returns_empty_list(self, mock_get):
        """Lines 129–131: Timeout → returns []."""
        mock_get.side_effect = requests.Timeout("timed out")
        client = GoogleMapsClient(api_key="key")

        result = client.search_local_businesses("spas", "Vegas")

        assert result == []

    @patch("requests.get")
    def test_json_decode_error_returns_empty_list(self, mock_get):
        """Lines 129–131: bad JSON response → returns []."""
        mock_resp = Mock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("No JSON object could be decoded")
        mock_get.return_value = mock_resp
        client = GoogleMapsClient(api_key="key")

        result = client.search_local_businesses("parks", "Boston")

        assert result == []

    @patch("requests.get")
    def test_raise_for_status_error_returns_empty_list(self, mock_get):
        """Lines 129–131: non-2xx status raises HTTPError → returns []."""
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("429 Rate Limited")
        mock_get.return_value = mock_resp
        client = GoogleMapsClient(api_key="key")

        result = client.search_local_businesses("hotels", "LA")

        assert result == []

    @patch("requests.get")
    def test_exception_logged(self, mock_get):
        """Lines 129–131: errors are logged, not silently swallowed."""
        mock_get.side_effect = RuntimeError("unexpected failure")
        client = GoogleMapsClient(api_key="key")

        with patch("src.utils.google_maps_search.logger") as mock_logger:
            client.search_local_businesses("gyms", "Phoenix")
            mock_logger.error.assert_called_once()


# ---------------------------------------------------------------------------
# GoogleMapsClient.get_place_reviews — lines 147–204
# ---------------------------------------------------------------------------


class TestGetPlaceReviews:
    """Tests for GoogleMapsClient.get_place_reviews (lines 147–204)."""

    # --- guard: no API key (lines 147–153) ---

    def test_no_api_key_returns_empty_place_with_reviews(self):
        """Lines 147–153: no key → PlaceWithReviews with empty reviews."""
        with patch.dict("os.environ", {}, clear=True):
            client = GoogleMapsClient()

        result = client.get_place_reviews("place_abc123")

        assert isinstance(result, PlaceWithReviews)
        assert result.place.place_id == "place_abc123"
        assert result.place.name == "Unknown"
        assert result.place.address == ""
        assert result.reviews == []
        assert result.total_reviews == 0

    def test_no_api_key_logs_warning(self):
        with patch.dict("os.environ", {}, clear=True):
            client = GoogleMapsClient()

        with patch("src.utils.google_maps_search.logger") as mock_logger:
            client.get_place_reviews("p1")
            mock_logger.warning.assert_called()

    # --- successful path (lines 155–200) ---

    @patch("requests.get")
    def test_successful_reviews_returns_place_with_reviews(
        self, mock_get, serpapi_reviews_response
    ):
        """Lines 172–200: happy-path parses place_info and reviews."""
        mock_get.return_value = _make_mock_response(serpapi_reviews_response)
        client = GoogleMapsClient(api_key="key")

        result = client.get_place_reviews("place_abc123")

        assert isinstance(result, PlaceWithReviews)
        assert result.place.place_id == "place_abc123"
        assert result.place.name == "Acme Coffee Co."
        assert result.place.address == "123 Main St, San Francisco, CA"
        assert result.place.rating == 4.5
        assert result.place.reviews_count == 312
        assert result.total_reviews == 312
        assert len(result.reviews) == 2

    @patch("requests.get")
    def test_reviews_parsed_correctly(self, mock_get, serpapi_reviews_response):
        """Lines 183–192: individual review fields are correctly mapped."""
        mock_get.return_value = _make_mock_response(serpapi_reviews_response)
        client = GoogleMapsClient(api_key="key")

        result = client.get_place_reviews("place_abc123")

        r0 = result.reviews[0]
        assert isinstance(r0, GoogleMapsReview)
        assert r0.author == "Alice"
        assert r0.rating == 5
        assert r0.text == "Best coffee in the city!"
        assert r0.date == "2 weeks ago"
        assert r0.likes == 12

    @patch("requests.get")
    def test_correct_api_params_sent(self, mock_get, serpapi_reviews_response):
        """Lines 158–165: correct parameters are passed to requests.get."""
        mock_get.return_value = _make_mock_response(serpapi_reviews_response)
        client = GoogleMapsClient(api_key="key456")

        client.get_place_reviews("pid789", max_reviews=10)

        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        params = kwargs["params"]
        assert params["engine"] == "google_maps_reviews"
        assert params["place_id"] == "pid789"
        assert params["api_key"] == "key456"
        assert params["num"] == 10

    @patch("requests.get")
    def test_serpapi_url_correct(self, mock_get, serpapi_reviews_response):
        mock_get.return_value = _make_mock_response(serpapi_reviews_response)
        client = GoogleMapsClient(api_key="key")
        client.get_place_reviews("pid1")

        args, _ = mock_get.call_args
        assert args[0] == "https://serpapi.com/search"

    @patch("requests.get")
    def test_request_timeout_is_set(self, mock_get, serpapi_reviews_response):
        """Line 168: timeout=15 must be passed."""
        mock_get.return_value = _make_mock_response(serpapi_reviews_response)
        client = GoogleMapsClient(api_key="key")
        client.get_place_reviews("pid1")

        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 15

    @patch("requests.get")
    def test_max_reviews_limit_respected(self, mock_get):
        """Line 184: slice [:max_reviews] trims oversized review lists."""
        many_reviews = {
            "place_info": {"title": "Big Place", "address": "1 St"},
            "reviews": [
                {
                    "user": {"name": f"User{i}"},
                    "rating": 4,
                    "snippet": "Good.",
                }
                for i in range(25)
            ],
        }
        mock_get.return_value = _make_mock_response(many_reviews)
        client = GoogleMapsClient(api_key="key")

        result = client.get_place_reviews("pid", max_reviews=5)

        assert len(result.reviews) == 5

    @patch("requests.get")
    def test_empty_reviews_list(self, mock_get):
        """Lines 183–200: no reviews key → empty list but place populated."""
        data = {
            "place_info": {
                "title": "Quiet Spot",
                "address": "2 Elm St",
                "rating": 4.0,
                "reviews": 0,
            }
        }
        mock_get.return_value = _make_mock_response(data)
        client = GoogleMapsClient(api_key="key")

        result = client.get_place_reviews("pid2")

        assert result.reviews == []
        assert result.total_reviews == 0
        assert result.place.name == "Quiet Spot"

    @patch("requests.get")
    def test_missing_place_info_uses_defaults(self, mock_get):
        """Lines 173–180: missing place_info → fallback defaults."""
        data = {"reviews": []}
        mock_get.return_value = _make_mock_response(data)
        client = GoogleMapsClient(api_key="key")

        result = client.get_place_reviews("pid3")

        assert result.place.name == "Unknown"
        assert result.place.address == ""
        assert result.place.rating is None

    @patch("requests.get")
    def test_review_missing_user_name_falls_back_to_anonymous(self, mock_get):
        """Line 186: missing user.name → 'Anonymous'."""
        data = {
            "place_info": {"title": "Cafe", "address": "1 St"},
            "reviews": [{"user": {}, "rating": 3, "snippet": "OK"}],
        }
        mock_get.return_value = _make_mock_response(data)
        client = GoogleMapsClient(api_key="key")

        result = client.get_place_reviews("pid4")

        assert result.reviews[0].author == "Anonymous"

    @patch("requests.get")
    def test_review_missing_user_key_falls_back_to_anonymous(self, mock_get):
        """Line 186: entirely missing user key → 'Anonymous'."""
        data = {
            "place_info": {"title": "Bar", "address": "1 St"},
            "reviews": [{"rating": 3, "snippet": "OK"}],
        }
        mock_get.return_value = _make_mock_response(data)
        client = GoogleMapsClient(api_key="key")

        result = client.get_place_reviews("pid5")

        assert result.reviews[0].author == "Anonymous"

    @patch("requests.get")
    def test_total_reviews_falls_back_to_len_reviews(self, mock_get):
        """Line 199: if place_info.reviews absent, fallback is len(reviews)."""
        data = {
            "place_info": {"title": "Shop", "address": "1 St"},
            "reviews": [
                {"user": {"name": "X"}, "rating": 4, "snippet": "Good"},
                {"user": {"name": "Y"}, "rating": 5, "snippet": "Great"},
            ],
        }
        mock_get.return_value = _make_mock_response(data)
        client = GoogleMapsClient(api_key="key")

        result = client.get_place_reviews("pid6")

        assert result.total_reviews == 2

    @patch("requests.get")
    def test_logs_review_count(self, mock_get, serpapi_reviews_response):
        """Line 194: info log contains review count and place name."""
        mock_get.return_value = _make_mock_response(serpapi_reviews_response)
        client = GoogleMapsClient(api_key="key")

        with patch("src.utils.google_maps_search.logger") as mock_logger:
            client.get_place_reviews("place_abc123")
            info_calls = [str(c) for c in mock_logger.info.call_args_list]
            assert any("2" in msg for msg in info_calls)

    # --- exception path (lines 202–208) ---

    @patch("requests.get")
    def test_http_error_returns_empty_place_with_reviews(self, mock_get):
        """Lines 202–208: HTTPError → fallback PlaceWithReviews."""
        mock_get.side_effect = requests.HTTPError("500 Internal Server Error")
        client = GoogleMapsClient(api_key="key")

        result = client.get_place_reviews("pid_err")

        assert isinstance(result, PlaceWithReviews)
        assert result.place.place_id == "pid_err"
        assert result.place.name == "Unknown"
        assert result.reviews == []
        assert result.total_reviews == 0

    @patch("requests.get")
    def test_connection_error_returns_fallback(self, mock_get):
        """Lines 202–208: ConnectionError → fallback."""
        mock_get.side_effect = requests.ConnectionError("unreachable")
        client = GoogleMapsClient(api_key="key")

        result = client.get_place_reviews("pid_conn")

        assert result.reviews == []
        assert result.place.place_id == "pid_conn"

    @patch("requests.get")
    def test_timeout_returns_fallback(self, mock_get):
        """Lines 202–208: Timeout → fallback."""
        mock_get.side_effect = requests.Timeout("timed out")
        client = GoogleMapsClient(api_key="key")

        result = client.get_place_reviews("pid_timeout")

        assert result.reviews == []

    @patch("requests.get")
    def test_json_decode_error_returns_fallback(self, mock_get):
        """Lines 202–208: bad JSON → fallback."""
        mock_resp = Mock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("bad JSON")
        mock_get.return_value = mock_resp
        client = GoogleMapsClient(api_key="key")

        result = client.get_place_reviews("pid_json")

        assert result.reviews == []
        assert result.place.name == "Unknown"

    @patch("requests.get")
    def test_rate_limit_error_returns_fallback(self, mock_get):
        """Lines 202–208: 429 rate-limit error → fallback."""
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("429 Too Many Requests")
        mock_get.return_value = mock_resp
        client = GoogleMapsClient(api_key="key")

        result = client.get_place_reviews("pid_rate")

        assert result.reviews == []

    @patch("requests.get")
    def test_exception_is_logged(self, mock_get):
        """Lines 202–208: errors are logged, not silently swallowed."""
        mock_get.side_effect = RuntimeError("unexpected")
        client = GoogleMapsClient(api_key="key")

        with patch("src.utils.google_maps_search.logger") as mock_logger:
            client.get_place_reviews("pid_log")
            mock_logger.error.assert_called_once()


# ---------------------------------------------------------------------------
# get_google_maps_client singleton helper
# ---------------------------------------------------------------------------


class TestGetGoogleMapsClient:
    """Tests for the get_google_maps_client module-level singleton."""

    def test_returns_google_maps_client_instance(self):
        client = get_google_maps_client(api_key="key")
        assert isinstance(client, GoogleMapsClient)

    def test_singleton_reused_when_no_key_provided(self):
        c1 = get_google_maps_client(api_key="key_first")
        c2 = get_google_maps_client()  # no key → reuse existing
        assert c1 is c2

    def test_new_instance_when_different_key_provided(self):
        c1 = get_google_maps_client(api_key="key_a")
        c2 = get_google_maps_client(api_key="key_b")
        assert c1 is not c2
        assert c2.api_key == "key_b"

    def test_same_key_reuses_singleton(self):
        get_google_maps_client(api_key="key_same")
        c2 = get_google_maps_client(api_key="key_same")
        # Same key → should NOT create a new instance (key_same == key_same)
        assert c2.api_key == "key_same"

    def test_creates_fresh_instance_when_none_exists(self):
        """Singleton starts as None; first call creates it."""
        client = get_google_maps_client(api_key="fresh_key")
        assert client is not None
        assert client.api_key == "fresh_key"

    @patch.dict("os.environ", {"SERPAPI_API_KEY": "env_key_singleton"})
    def test_works_with_env_key(self):
        client = get_google_maps_client()
        assert client.api_key == "env_key_singleton"
