"""
SSRF guard for server-side fetches of user-supplied URLs (Phase 10 distribution).

Only the YouTube publisher streams bytes from a caller-supplied ``media_url``
through our own process; the other platforms hand the URL to the remote platform
API, which fetches it on *their* side. This helper hardens that single
server-side fetch (and any future one) against SSRF.

Defense:

* Require an ``http(s)`` scheme.
* Resolve the host and refuse any address that maps to loopback, private,
  link-local, reserved, or otherwise-internal space.
* **Pin the connection to the exact validated IP.** We connect to that IP
  literally (and, for TLS, keep the original hostname for SNI + certificate
  verification), so ``requests``/``urllib3`` never performs a second DNS lookup.
  This closes the TOCTOU/DNS-rebinding window where a hostname could pass the
  check with a public IP and then rebind to ``169.254.169.254`` before the fetch.
* Re-validate on **every redirect hop** so a ``302`` can't jump to an internal
  target.
"""

from __future__ import annotations

import ipaddress
import socket
import time
from typing import List, Tuple
from urllib.parse import ParseResult, urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter

_MAX_REDIRECTS = 5
# Fallback across a host's resolved addresses is bounded by wall-clock, not a
# fixed count: we try *every unique* validated address (so a host publishing
# many A/AAAA records is never rejected just for having >N of them) but stop
# once total connect time exceeds this multiple of the caller's connect timeout
# (so blackholed addresses can't stack into an unbounded hang). This is a
# deliberate latency-vs-exhaustiveness trade-off — see BUGS #192.
_FALLBACK_CONNECT_BUDGET = 4

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


class _PinnedHostHTTPSAdapter(HTTPAdapter):
    """Verify TLS against the real hostname while connected to a pinned IP.

    We connect the socket to a literal validated IP, but SNI and certificate
    hostname verification must still use the original hostname — otherwise the
    cert wouldn't match. urllib3 forwards these connection kwargs down to each
    HTTPS connection in the pool.
    """

    def __init__(self, server_hostname: str, **kw):
        self._server_hostname = server_hostname
        super().__init__(**kw)

    def init_poolmanager(self, *args, **kwargs):  # type: ignore[override]
        kwargs["server_hostname"] = self._server_hostname
        kwargs["assert_hostname"] = self._server_hostname
        super().init_poolmanager(*args, **kwargs)


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


def _unique(ips: List[ipaddress._BaseAddress]) -> List[ipaddress._BaseAddress]:
    """De-duplicate resolved addresses, preserving resolver order."""
    seen, out = set(), []
    for ip in ips:
        if ip not in seen:
            seen.add(ip)
            out.append(ip)
    return out


def _resolve_ips(host: str) -> List[ipaddress._BaseAddress]:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Could not resolve host: {host}") from exc
    ips = []
    for info in infos:
        addr = info[4][0].split("%", 1)[0]  # strip IPv6 zone id
        ips.append(ipaddress.ip_address(addr))
    return ips


def _validate_and_resolve(url: str) -> Tuple[ParseResult, List[ipaddress._BaseAddress]]:
    """Return ``(parsed_url, validated_ips)`` or raise ``UnsafeURLError``.

    Validates the scheme, then every IP the host resolves to (or a literal IP),
    rejecting loopback/private/link-local/reserved/internal addresses. All
    returned IPs are guaranteed public — so pinning to any of them is safe.
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
    return parsed, ips


def assert_safe_url(url: str) -> None:
    """Raise ``UnsafeURLError`` unless ``url`` is a public http(s) URL."""
    _validate_and_resolve(url)


def _host_header(parsed: ParseResult) -> str:
    """Original ``hostname[:port]`` for the Host header (IPv6 literal bracketed)."""
    raw = parsed.hostname
    try:
        if isinstance(ipaddress.ip_address(raw), ipaddress.IPv6Address):
            raw = f"[{raw}]"
    except ValueError:
        pass  # a normal hostname
    return f"{raw}:{parsed.port}" if parsed.port else raw


def _pin(parsed: ParseResult, ip: ipaddress._BaseAddress) -> Tuple[str, str]:
    """Build ``(connect_url, host_header)`` that targets the literal ``ip``.

    The connect URL swaps the hostname for the validated IP (bracketed for
    IPv6, original port preserved); the Host header carries the original
    hostname[:port] so the far end still routes/serves the right vhost.
    """
    ip_host = f"[{ip}]" if ip.version == 6 else str(ip)
    netloc = f"{ip_host}:{parsed.port}" if parsed.port else ip_host
    connect_url = parsed._replace(netloc=netloc).geturl()
    return connect_url, _host_header(parsed)


def _pinned_get(parsed: ParseResult, ip, headers: dict, timeout, kwargs) -> requests.Response:
    """One streamed GET pinned to ``ip`` (TLS verified against the real host).

    The per-``Session`` lifetime is tied to the streamed response: a failed
    attempt closes its session immediately, and a successful one closes it when
    the caller closes the response (so no connection pool / socket is leaked).
    """
    connect_url, host_header = _pin(parsed, ip)
    session = requests.Session()
    try:
        if parsed.scheme == "https":
            # Pin the socket to the IP but verify the cert against the real host.
            session.mount(connect_url, _PinnedHostHTTPSAdapter(parsed.hostname))
        resp = session.get(
            connect_url,
            stream=True,
            timeout=timeout,
            allow_redirects=False,
            headers={**headers, "Host": host_header},
            **kwargs,
        )
    except BaseException:
        session.close()
        raise
    # Close the session alongside the response it produced.
    _orig_close = resp.close

    def _close_both() -> None:
        try:
            _orig_close()
        finally:
            session.close()

    resp.close = _close_both  # type: ignore[method-assign]
    return resp


def safe_stream_get(url: str, *, timeout, **kwargs) -> requests.Response:
    """SSRF-guarded ``requests.get(stream=True)`` pinned to a validated IP.

    Follows redirects manually, re-validating and re-pinning each hop. Because
    every resolved address is already vetted as public, we try each *unique*
    address in resolver order and fall back to the next on a connection failure —
    so a dual-stack / CDN host doesn't hard-fail when its first (e.g. IPv6)
    address is unreachable. Fallback stops when addresses are exhausted or the
    total connect wall-clock exceeds ``_FALLBACK_CONNECT_BUDGET`` × the caller's
    connect timeout, whichever comes first (see BUGS #192). Returns the final
    streamed :class:`requests.Response`.
    """
    current = url
    headers = dict(kwargs.pop("headers", {}) or {})
    connect_timeout = timeout[0] if isinstance(timeout, (tuple, list)) else timeout
    for _ in range(_MAX_REDIRECTS + 1):
        parsed, ips = _validate_and_resolve(current)

        resp = None
        last_err: Exception | None = None
        deadline = (
            time.monotonic() + connect_timeout * _FALLBACK_CONNECT_BUDGET
            if connect_timeout
            else None
        )
        for ip in _unique(ips):
            if deadline is not None and time.monotonic() >= deadline:
                break  # latency budget spent — stop before an unbounded hang
            try:
                resp = _pinned_get(parsed, ip, headers, timeout, kwargs)
                break
            except requests.exceptions.RequestException as exc:
                last_err = exc  # unreachable address — try the next validated IP
        if resp is None:
            raise last_err if last_err else UnsafeURLError(f"No usable address for {url}")

        location = resp.headers.get("location")
        if resp.is_redirect and location:
            nxt = urljoin(current, location)  # resolve relative Location vs real host
            resp.close()
            current = nxt
            continue
        return resp
    raise UnsafeURLError("Too many redirects while fetching URL")
