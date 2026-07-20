"""
SSRF guard for server-side fetches of user-supplied URLs (Phase 10 distribution).

Only the YouTube publisher streams bytes from a caller-provided ``media_url``
through our own process; the other platforms hand the URL to the remote platform
API, which fetches it on *their* side. This helper hardens that single
server-side fetch (and any future one) against SSRF: it requires an ``http(s)``
scheme, resolves the host, and refuses any address that maps to loopback,
private, link-local, or otherwise-internal space — re-validating on **every
redirect hop** so a ``302`` to ``169.254.169.254`` can't slip past the first
check.

Residual risk: a TOCTOU/DNS-rebinding window remains between our resolve-time
check and ``requests``' own resolution at connect time. Closing it fully would
require pinning the socket to the validated IP; for this scaffolded path
(YouTube is not yet a live publisher) the resolve-then-request + per-hop
re-validation is the standard, proportionate mitigation.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests

_MAX_REDIRECTS = 5

# Ranges not consistently covered by ``ipaddress.is_private`` across Python
# versions — blocked explicitly for defense in depth.
_EXTRA_BLOCKED = [
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT / RFC 6598 shared space
    ipaddress.ip_network("198.18.0.0/15"),  # RFC 2544 benchmarking
    ipaddress.ip_network("192.0.0.0/24"),  # IETF protocol assignments
    ipaddress.ip_network("::ffff:0:0/96"),  # IPv4-mapped IPv6
]


class UnsafeURLError(ValueError):
    """Raised when a user-supplied URL resolves to a disallowed address."""


def _ip_is_blocked(ip: ipaddress._BaseAddress) -> bool:
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        return True
    return any(ip in net for net in _EXTRA_BLOCKED)


def _resolve_ips(host: str) -> list:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Could not resolve host: {host}") from exc
    ips = []
    for info in infos:
        addr = info[4][0].split("%", 1)[0]  # strip IPv6 zone id
        ips.append(ipaddress.ip_address(addr))
    return ips


def assert_safe_url(url: str) -> None:
    """Raise ``UnsafeURLError`` unless ``url`` is a public http(s) URL.

    Validates the scheme, then every IP the host resolves to (or a literal IP),
    rejecting loopback/private/link-local/reserved/internal addresses.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeURLError(f"Only http(s) URLs are allowed, got scheme: {parsed.scheme!r}")
    host = parsed.hostname
    if not host:
        raise UnsafeURLError("URL has no host")
    try:
        ips = [ipaddress.ip_address(host)]  # literal IP in the URL
    except ValueError:
        ips = _resolve_ips(host)
    if not ips:
        raise UnsafeURLError(f"Host did not resolve: {host}")
    for ip in ips:
        if _ip_is_blocked(ip):
            raise UnsafeURLError(f"URL resolves to a disallowed address: {ip}")


def safe_stream_get(url: str, *, timeout, **kwargs) -> requests.Response:
    """SSRF-guarded ``requests.get(stream=True)``.

    Follows redirects manually, re-validating the target of each hop, and
    returns the final streamed :class:`requests.Response`.
    """
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        assert_safe_url(current)
        resp = requests.get(current, stream=True, timeout=timeout, allow_redirects=False, **kwargs)
        location = resp.headers.get("location")
        if resp.is_redirect and location:
            nxt = urljoin(current, location)
            resp.close()
            current = nxt
            continue
        return resp
    raise UnsafeURLError("Too many redirects while fetching URL")
