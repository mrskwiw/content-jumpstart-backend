"""SSRF guard unit tests (Phase 10 distribution).

Covers backend.services.distribution.net_guard: URL scheme/IP validation and
per-redirect-hop re-validation in safe_stream_get.
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.services.distribution.net_guard import (
    UnsafeURLError,
    assert_safe_url,
    safe_stream_get,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/x",  # loopback
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata / link-local
        "http://10.0.0.5/x",  # RFC1918
        "http://192.168.1.1/x",  # RFC1918
        "http://172.16.0.1/x",  # RFC1918
        "http://100.64.0.1/x",  # CGNAT
        "http://0.0.0.0/x",  # unspecified
        "http://[::1]/x",  # IPv6 loopback
        "ftp://example.com/x",  # disallowed scheme
        "file:///etc/passwd",  # disallowed scheme
        "http:///nohost",  # no host
    ],
)
def test_assert_safe_url_rejects_internal_and_bad_scheme(url):
    with pytest.raises(UnsafeURLError):
        assert_safe_url(url)


def test_assert_safe_url_allows_public_ip_literal():
    # Public IP literal — no DNS needed, must pass.
    assert_safe_url("https://93.184.216.34/video.mp4")


def test_assert_safe_url_rejects_hostname_resolving_to_private():
    # A hostname that resolves to a private address must be rejected.
    with patch(
        "backend.services.distribution.net_guard.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("10.1.2.3", 0))],
    ):
        with pytest.raises(UnsafeURLError):
            assert_safe_url("https://sneaky.example.com/video.mp4")


def test_assert_safe_url_allows_hostname_resolving_to_public():
    with patch(
        "backend.services.distribution.net_guard.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("93.184.216.34", 0))],
    ):
        assert_safe_url("https://cdn.example.com/video.mp4")


def test_safe_stream_get_revalidates_redirect_to_internal():
    """A 302 pointing at an internal address must be caught on the next hop."""
    redirect = MagicMock()
    redirect.is_redirect = True
    redirect.headers = {"location": "http://169.254.169.254/latest/meta-data/"}

    with patch(
        "backend.services.distribution.net_guard.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("93.184.216.34", 0))],
    ):
        with patch("backend.services.distribution.net_guard.requests.get", return_value=redirect):
            with pytest.raises(UnsafeURLError):
                safe_stream_get("https://cdn.example.com/video.mp4", timeout=5)
    redirect.close.assert_called_once()


def test_safe_stream_get_returns_final_response():
    ok = MagicMock()
    ok.is_redirect = False
    ok.headers = {}

    with patch(
        "backend.services.distribution.net_guard.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("93.184.216.34", 0))],
    ):
        with patch(
            "backend.services.distribution.net_guard.requests.get", return_value=ok
        ) as mock_get:
            resp = safe_stream_get("https://cdn.example.com/video.mp4", timeout=5)
    assert resp is ok
    # Guarded fetch must disable auto-redirect following.
    assert mock_get.call_args.kwargs["allow_redirects"] is False
    assert mock_get.call_args.kwargs["stream"] is True
