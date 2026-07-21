"""SSRF guard unit tests (Phase 10 distribution).

Covers backend.services.distribution.net_guard: URL scheme/IP validation and
per-redirect-hop re-validation in safe_stream_get.
"""

import ipaddress
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest
import requests

from backend.services.distribution.net_guard import (
    UnsafeURLError,
    _pin,
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


def _session_returning(response):
    """A fake requests.Session whose .get returns `response`; records the mount."""
    session = MagicMock()
    session.get.return_value = response
    return session


def test_safe_stream_get_revalidates_redirect_to_internal():
    """A 302 pointing at an internal address must be caught on the next hop."""
    redirect = MagicMock()
    redirect.is_redirect = True
    redirect.headers = {"location": "http://169.254.169.254/latest/meta-data/"}
    session = _session_returning(redirect)

    with patch(
        "backend.services.distribution.net_guard.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("93.184.216.34", 0))],
    ):
        with patch(
            "backend.services.distribution.net_guard.requests.Session", return_value=session
        ):
            with pytest.raises(UnsafeURLError):
                safe_stream_get("https://cdn.example.com/video.mp4", timeout=5)
    # The redirect hop's response/session are cleaned up before the next hop.
    session.close.assert_called()


def test_safe_stream_get_pins_to_validated_ip_and_returns_response():
    ok = MagicMock()
    ok.is_redirect = False
    ok.headers = {}
    session = _session_returning(ok)

    with patch(
        "backend.services.distribution.net_guard.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("93.184.216.34", 0))],
    ):
        with patch(
            "backend.services.distribution.net_guard.requests.Session", return_value=session
        ):
            resp = safe_stream_get("https://cdn.example.com/video.mp4", timeout=5)

    assert resp is ok
    call = session.get.call_args
    # Pinned: connect to the validated literal IP, not the hostname (no 2nd DNS).
    assert call.args[0] == "https://93.184.216.34/video.mp4"
    # But route/serve the original vhost, and don't auto-follow redirects.
    assert call.kwargs["headers"]["Host"] == "cdn.example.com"
    assert call.kwargs["allow_redirects"] is False
    assert call.kwargs["stream"] is True


def test_safe_stream_get_falls_back_to_next_validated_ip():
    """First (e.g. unreachable IPv6) validated IP fails → try the next one."""
    ok = MagicMock()
    ok.is_redirect = False
    ok.headers = {}

    sessions = []

    def make_session():
        s = MagicMock()
        sessions.append(s)
        # First session's .get raises a connection error; second returns ok.
        s.get.side_effect = (
            [requests.exceptions.ConnectionError("no route")] if len(sessions) == 1 else [ok]
        )
        return s

    with patch(
        "backend.services.distribution.net_guard.socket.getaddrinfo",
        return_value=[
            (10, 1, 6, "", ("2606:2800:220:1:248:1893:25c8:1946", 0, 0, 0)),  # public IPv6
            (2, 1, 6, "", ("93.184.216.34", 0)),  # public IPv4
        ],
    ):
        with patch(
            "backend.services.distribution.net_guard.requests.Session", side_effect=make_session
        ):
            resp = safe_stream_get("https://cdn.example.com/video.mp4", timeout=5)

    assert resp is ok
    # Second (IPv4) address was tried after the first failed.
    assert sessions[1].get.call_args.args[0] == "https://93.184.216.34/video.mp4"
    # The failed first attempt must not leak its session.
    sessions[0].close.assert_called_once()


def test_safe_stream_get_closes_session_when_response_closed():
    """Closing the returned response also closes its underlying session."""
    ok = MagicMock()
    ok.is_redirect = False
    ok.headers = {}
    session = _session_returning(ok)

    with patch(
        "backend.services.distribution.net_guard.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("93.184.216.34", 0))],
    ):
        with patch(
            "backend.services.distribution.net_guard.requests.Session", return_value=session
        ):
            resp = safe_stream_get("https://cdn.example.com/video.mp4", timeout=5)
        resp.close()  # caller (e.g. `with ... as src`) closes the stream

    session.close.assert_called_once()


def test_safe_stream_get_tries_beyond_four_addresses(monkeypatch):
    """Regression: a host with >4 public IPs whose only reachable one is the 5th
    must still succeed — fallback is time-bounded, not count-capped (BUGS #192)."""
    ok = MagicMock()
    ok.is_redirect = False
    ok.headers = {}

    sessions = []

    def make_session():
        s = MagicMock()
        sessions.append(s)
        # First four addresses fail fast; the fifth succeeds.
        s.get.side_effect = (
            [ok] if len(sessions) == 5 else [requests.exceptions.ConnectionError("down")]
        )
        return s

    addrs = [(2, 1, 6, "", (f"93.184.216.{n}", 0)) for n in (34, 35, 36, 37, 38)]  # 5 public IPv4s
    # Freeze the clock so the connect-time budget never trips (failures are instant).
    monkeypatch.setattr("backend.services.distribution.net_guard.time.monotonic", lambda: 0.0)
    with patch("backend.services.distribution.net_guard.socket.getaddrinfo", return_value=addrs):
        with patch(
            "backend.services.distribution.net_guard.requests.Session", side_effect=make_session
        ):
            resp = safe_stream_get("https://cdn.example.com/video.mp4", timeout=5)

    assert resp is ok
    assert len(sessions) == 5  # tried all five, not capped at four
    assert sessions[4].get.call_args.args[0] == "https://93.184.216.38/video.mp4"


def test_safe_stream_get_caps_pathological_address_set(monkeypatch):
    """A huge fast-failing public-IP answer is capped at _MAX_UNIQUE_ADDRS so it
    can't drive unbounded connect attempts even when the time budget never trips."""
    from backend.services.distribution.net_guard import _MAX_UNIQUE_ADDRS

    sessions = []

    def make_session():
        s = MagicMock()
        sessions.append(s)
        s.get.side_effect = [requests.exceptions.ConnectionError("down")]  # all fail fast
        return s

    # 40 distinct public IPs, all unreachable-but-instant.
    addrs = [(2, 1, 6, "", (f"93.184.{n // 256}.{n % 256}", 0)) for n in range(40)]
    monkeypatch.setattr("backend.services.distribution.net_guard.time.monotonic", lambda: 0.0)
    with patch("backend.services.distribution.net_guard.socket.getaddrinfo", return_value=addrs):
        with patch(
            "backend.services.distribution.net_guard.requests.Session", side_effect=make_session
        ):
            with pytest.raises(requests.exceptions.ConnectionError):
                safe_stream_get("https://cdn.example.com/video.mp4", timeout=5)

    assert len(sessions) == _MAX_UNIQUE_ADDRS  # capped, not 40


def test_pin_ipv6_literal_host_header_is_bracketed():
    parsed = urlparse("https://[2606:2800:220:1:248:1893:25c8:1946]:8443/v.mp4")
    connect_url, host_header = _pin(parsed, ipaddress.ip_address("93.184.216.34"))
    assert connect_url == "https://93.184.216.34:8443/v.mp4"
    assert host_header == "[2606:2800:220:1:248:1893:25c8:1946]:8443"
