"""Unit tests for the Bluesky publisher (DIST-EXPAND) — AT Protocol app-password flow."""

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


def test_bluesky_supported_but_not_oauth():
    """Bluesky is a supported publish target (credentials + publishing) but is NOT an
    OAuth platform — so it must not appear in the OAuth connect grid."""
    from backend.models.distribution import SUPPORTED_PLATFORMS
    from backend.services.distribution.oauth import PROVIDERS

    assert "bluesky" in SUPPORTED_PLATFORMS
    assert "bluesky" not in PROVIDERS
