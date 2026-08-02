"""Unit tests for the Bluesky publisher (DIST-EXPAND) — AT Protocol app-password flow."""

import pytest
import requests

from backend.services.distribution.publishers import (
    BlueskyPublisher,
    NotImplementedPublisher,
    get_publisher,
)


class _Resp:
    def __init__(self, status, payload=None, text=""):
        self.status_code = status
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def _seq_post(monkeypatch, responses):
    """Return each queued response for successive requests.post calls."""
    it = iter(responses)
    calls = []

    def fake_post(url, **kw):
        calls.append((url, kw))
        return next(it)

    monkeypatch.setattr(requests, "post", fake_post)
    return calls


def test_bluesky_registered_as_real_publisher(monkeypatch):
    monkeypatch.delenv("DISTRIBUTION_DRY_RUN", raising=False)
    pub = get_publisher("bluesky", access_token="app-pw", account_ref="me.bsky.social")
    assert isinstance(pub, BlueskyPublisher)
    assert not isinstance(pub, NotImplementedPublisher)


def test_bluesky_publish_success(monkeypatch):
    calls = _seq_post(
        monkeypatch,
        [
            _Resp(200, {"accessJwt": "jwt-1", "did": "did:plc:abc"}),  # createSession
            _Resp(200, {"uri": "at://did:plc:abc/app.bsky.feed.post/rkey9"}),  # createRecord
        ],
    )
    r = BlueskyPublisher(access_token="app-pw", account_ref="me.bsky.social").publish("hello sky")
    assert r.success, r.error
    assert r.platform_post_id.endswith("rkey9")
    assert r.platform_url == "https://bsky.app/profile/me.bsky.social/post/rkey9"
    # Session first, then the post record, with the text in the record.
    assert calls[0][0].endswith("com.atproto.server.createSession")
    assert calls[1][0].endswith("com.atproto.repo.createRecord")
    assert calls[1][1]["json"]["record"]["text"] == "hello sky"
    assert calls[1][1]["json"]["repo"] == "did:plc:abc"


def test_bluesky_requires_handle():
    r = BlueskyPublisher(access_token="app-pw", account_ref=None).publish("hi")
    assert not r.success and "handle" in r.error.lower()


def test_bluesky_auth_failure(monkeypatch):
    _seq_post(monkeypatch, [_Resp(401, text="bad app password")])
    r = BlueskyPublisher(access_token="wrong", account_ref="me.bsky.social").publish("hi")
    assert not r.success and "401" in r.error


def test_bluesky_post_failure(monkeypatch):
    _seq_post(
        monkeypatch,
        [
            _Resp(200, {"accessJwt": "jwt-1", "did": "did:plc:abc"}),
            _Resp(400, text="record rejected"),
        ],
    )
    r = BlueskyPublisher(access_token="app-pw", account_ref="me.bsky.social").publish("hi")
    assert not r.success and "400" in r.error


def test_bluesky_session_missing_fields(monkeypatch):
    _seq_post(monkeypatch, [_Resp(200, {})])  # no accessJwt/did
    r = BlueskyPublisher(access_token="app-pw", account_ref="me.bsky.social").publish("hi")
    assert not r.success and "accessJwt" in r.error


def test_bluesky_fails_closed_on_media(monkeypatch):
    """A post with media must fail closed (embeds unimplemented), not silently drop it."""
    posted = []
    monkeypatch.setattr(requests, "post", lambda *a, **k: posted.append(a) or _Resp(200, {}))
    r = BlueskyPublisher(access_token="app-pw", account_ref="me.bsky.social").publish(
        "with pic", media_url="https://cdn/x.png"
    )
    assert not r.success and "media" in r.error.lower()
    assert posted == []  # no network call attempted


def test_bluesky_uses_configured_pds_host(monkeypatch):
    monkeypatch.setenv("BLUESKY_PDS_URL", "https://pds.example.com")
    calls = _seq_post(
        monkeypatch,
        [
            _Resp(200, {"accessJwt": "j", "did": "did:plc:x"}),
            _Resp(200, {"uri": "at://did:plc:x/app.bsky.feed.post/rk"}),
        ],
    )
    r = BlueskyPublisher(access_token="pw", account_ref="me.example.com").publish("hi")
    assert r.success, r.error
    # Both AT Protocol calls hit the configured PDS host, not the bsky.social default.
    assert calls[0][0].startswith("https://pds.example.com/xrpc/")
    assert calls[1][0].startswith("https://pds.example.com/xrpc/")


def test_bluesky_unset_pds_uses_default(monkeypatch):
    """TRULY UNSET BLUESKY_PDS_URL → the public bsky.social default (the common case)."""
    monkeypatch.delenv("BLUESKY_PDS_URL", raising=False)
    calls = _seq_post(
        monkeypatch,
        [
            _Resp(200, {"accessJwt": "j", "did": "did:plc:x"}),
            _Resp(200, {"uri": "at://did:plc:x/app.bsky.feed.post/rk"}),
        ],
    )
    r = BlueskyPublisher(access_token="pw", account_ref="me.bsky.social").publish("hi")
    assert r.success, r.error
    assert calls[0][0].startswith("https://bsky.social/xrpc/")


def test_bluesky_uppercase_scheme_accepted(monkeypatch):
    """URL schemes are case-insensitive (RFC 3986) — an uppercase scheme is valid and the
    host is normalized to lowercase, not rejected."""
    monkeypatch.setenv("BLUESKY_PDS_URL", "HTTPS://pds.example.com")
    calls = _seq_post(
        monkeypatch,
        [
            _Resp(200, {"accessJwt": "j", "did": "did:plc:x"}),
            _Resp(200, {"uri": "at://did:plc:x/app.bsky.feed.post/rk"}),
        ],
    )
    r = BlueskyPublisher(access_token="pw", account_ref="me.example.com").publish("hi")
    assert r.success, r.error
    assert calls[0][0].startswith("https://pds.example.com/xrpc/")


def test_bluesky_invalid_or_blank_pds_fails_closed(monkeypatch):
    """PRESENT-BUT-BLANK or non-http(s) BLUESKY_PDS_URL → fail closed. A blank value is a
    misconfiguration (templated-but-empty), not an opt-out, so it must not silently publish
    to the default host with the wrong credentials."""
    posted = []
    monkeypatch.setattr(requests, "post", lambda *a, **k: posted.append(a) or _Resp(200, {}))
    for bad in ("", "   ", "not-a-url", "ftp://x", "bsky.social"):
        monkeypatch.setenv("BLUESKY_PDS_URL", bad)
        r = BlueskyPublisher(access_token="pw", account_ref="me.bsky.social").publish("hi")
        assert not r.success and "BLUESKY_PDS_URL" in r.error
    assert posted == []  # never attempted a network call with a bad/blank host


def test_bluesky_verify_success_without_posting(monkeypatch):
    """verify() authenticates (createSession) but must NOT create a record."""
    calls = _seq_post(monkeypatch, [_Resp(200, {"accessJwt": "j", "did": "did:plc:x"})])
    r = BlueskyPublisher(access_token="pw", account_ref="me.bsky.social").verify()
    assert r.success, r.error
    # Exactly one call — the session — and never createRecord.
    assert len(calls) == 1
    assert calls[0][0].endswith("com.atproto.server.createSession")


def test_bluesky_verify_rejects_bad_app_password(monkeypatch):
    """A bad app password fails verify() (so connect can reject it) — no record attempted."""
    calls = _seq_post(monkeypatch, [_Resp(401, text="bad app password")])
    r = BlueskyPublisher(access_token="wrong", account_ref="me.bsky.social").verify()
    assert not r.success and "401" in r.error
    assert len(calls) == 1  # session attempt only, no createRecord


def test_bluesky_verify_requires_handle():
    r = BlueskyPublisher(access_token="pw", account_ref=None).verify()
    assert not r.success and "handle" in r.error.lower()
    assert r.retryable is False  # a missing handle is definitively bad input, not transient


def test_bluesky_verify_401_is_definitive_not_retryable(monkeypatch):
    _seq_post(monkeypatch, [_Resp(401, text="bad app password")])
    r = BlueskyPublisher(access_token="wrong", account_ref="me.bsky.social").verify()
    assert not r.success and "401" in r.error
    assert r.retryable is False  # rejected credential → definitive


def test_bluesky_verify_5xx_is_retryable(monkeypatch):
    """A PDS 5xx means the provider is unhealthy, not that the credential is wrong."""
    _seq_post(monkeypatch, [_Resp(503, text="upstream down")])
    r = BlueskyPublisher(access_token="pw", account_ref="me.bsky.social").verify()
    assert not r.success and "503" in r.error
    assert r.retryable is True


def test_bluesky_verify_network_error_is_retryable(monkeypatch):
    """Known transport failures (timeout/DNS/connection) are the provider, not the input →
    retryable, not a hard rejection."""
    for exc in (
        requests.exceptions.Timeout("connect timeout"),
        requests.exceptions.ConnectionError("dns failure"),
    ):

        def boom(*a, _exc=exc, **k):
            raise _exc

        monkeypatch.setattr(requests, "post", boom)
        r = BlueskyPublisher(access_token="pw", account_ref="me.bsky.social").verify()
        assert not r.success and r.retryable is True


def test_bluesky_verify_2xx_without_token_raises_contract_error(monkeypatch):
    """A 2xx createSession with no accessJwt/did is a broken contract, not a transient blip —
    it must surface (raise → 500), not be swallowed into a retryable 502."""
    _seq_post(monkeypatch, [_Resp(200, {})])
    with pytest.raises(ValueError, match="accessJwt"):
        BlueskyPublisher(access_token="pw", account_ref="me.bsky.social").verify()


def test_bluesky_verify_unexpected_exception_propagates(monkeypatch):
    """An unexpected (non-transport) exception must NOT be masked as a retryable 502 — it
    propagates so a broken verifier surfaces as a real error."""

    def boom(*a, **k):
        raise RuntimeError("unexpected bug")

    monkeypatch.setattr(requests, "post", boom)
    with pytest.raises(RuntimeError, match="unexpected bug"):
        BlueskyPublisher(access_token="pw", account_ref="me.bsky.social").verify()


def test_base_publisher_verify_is_noop():
    """OAuth platforms have nothing to round-trip at manual-connect time → verify passes."""
    from backend.services.distribution.publishers import BasePublisher, NotImplementedPublisher

    assert BasePublisher(access_token="t").verify().success
    # Unimplemented platforms fail closed so a credential can't be stored for them.
    assert not NotImplementedPublisher("threads", access_token="t").verify().success


def test_bluesky_supported_but_not_oauth():
    """Bluesky is a supported publish target (credentials + publishing) but is NOT an
    OAuth platform — so it must not appear in the OAuth connect grid."""
    from backend.models.distribution import SUPPORTED_PLATFORMS
    from backend.services.distribution.oauth import PROVIDERS

    assert "bluesky" in SUPPORTED_PLATFORMS
    assert "bluesky" not in PROVIDERS
