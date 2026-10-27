"""GAP-BE-02: errors that spa_routing_middleware turns into a 500 must still reach Sentry.

The middleware catches every exception from the app and returns a JSON 500 itself, so
the exception never propagates to Sentry's ASGI integration. The production login
outage (BUGS #258) took exactly this path. These tests pin that the middleware reports
what it swallows — and does not report the expected SPA fallback or ordinary HTTP errors.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.main import app

_PATH = "/api/__sentry_capture_probe"


@pytest.fixture
def probe_route():
    """Mount a temporary route that raises whatever the test parametrises."""
    state = {"exc": None}

    async def _probe():
        raise state["exc"]

    app.add_api_route(_PATH, _probe, methods=["GET"])
    try:
        yield state
    finally:
        app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", None) != _PATH]


@pytest.mark.parametrize("exc", [ValueError("db down"), RuntimeError("pool exhausted")])
def test_swallowed_server_error_is_reported(probe_route, exc):
    probe_route["exc"] = exc
    with patch("sentry_sdk.capture_exception") as capture:
        response = TestClient(app, raise_server_exceptions=False).get(_PATH)
    assert response.status_code == 500
    capture.assert_called_once_with(exc)


def test_http_exception_is_not_reported(probe_route):
    probe_route["exc"] = HTTPException(status_code=404, detail="nope")
    with patch("sentry_sdk.capture_exception") as capture:
        response = TestClient(app, raise_server_exceptions=False).get(_PATH)
    assert response.status_code == 404
    capture.assert_not_called()


def test_spa_fallback_is_not_reported():
    # A deep link the API doesn't know is served index.html (or 404s without a build) —
    # normal routing, not an error.
    with patch("sentry_sdk.capture_exception") as capture:
        TestClient(app, raise_server_exceptions=False).get("/dashboard/projects/proj-x")
    capture.assert_not_called()
