"""Unit tests for the Threads + Pinterest publishers (DIST-EXPAND) and their OAuth wiring."""

import requests

from backend.services.distribution.publishers import (
    NotImplementedPublisher,
    PinterestPublisher,
    ThreadsPublisher,
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


# ── Threads ──────────────────────────────────────────────────────────────────


def test_threads_registered_as_real_publisher(monkeypatch):
    monkeypatch.delenv("DISTRIBUTION_DRY_RUN", raising=False)
    pub = get_publisher("threads", access_token="tok", account_ref="17841400000")
    assert isinstance(pub, ThreadsPublisher)
    assert not isinstance(pub, NotImplementedPublisher)


def test_threads_text_post_success(monkeypatch):
    calls = _seq_post(
        monkeypatch,
        [
            _Resp(200, {"id": "container-1"}),  # create container
            _Resp(200, {"id": "post-99"}),  # publish
        ],
    )
    r = ThreadsPublisher(access_token="tok", account_ref="tid").publish("hello threads")
    assert r.success, r.error
    assert r.platform_post_id == "post-99"
    # Text-only → media_type=TEXT container, then publish with the creation_id.
    assert calls[0][0].endswith("/tid/threads")
    assert calls[0][1]["data"]["media_type"] == "TEXT"
    assert calls[0][1]["data"]["text"] == "hello threads"
    assert calls[1][0].endswith("/tid/threads_publish")
    assert calls[1][1]["data"]["creation_id"] == "container-1"


def test_threads_image_post_uses_image_media_type(monkeypatch):
    calls = _seq_post(
        monkeypatch,
        [_Resp(200, {"id": "c2"}), _Resp(200, {"id": "p2"})],
    )
    r = ThreadsPublisher(access_token="tok", account_ref="tid").publish(
        "with pic", media_url="https://cdn/x.png"
    )
    assert r.success, r.error
    assert calls[0][1]["data"]["media_type"] == "IMAGE"
    assert calls[0][1]["data"]["image_url"] == "https://cdn/x.png"


def test_threads_requires_account_ref():
    r = ThreadsPublisher(access_token="tok", account_ref=None).publish("hi")
    assert not r.success and "account_ref" in r.error


def test_threads_container_error_is_surfaced(monkeypatch):
    _seq_post(monkeypatch, [_Resp(400, text="bad container")])
    r = ThreadsPublisher(access_token="tok", account_ref="tid").publish("hi")
    assert not r.success and "400" in r.error


def test_threads_publish_error_is_surfaced(monkeypatch):
    _seq_post(monkeypatch, [_Resp(200, {"id": "c"}), _Resp(500, text="down")])
    r = ThreadsPublisher(access_token="tok", account_ref="tid").publish("hi")
    assert not r.success and "500" in r.error


# ── Pinterest ────────────────────────────────────────────────────────────────


def test_pinterest_registered_as_real_publisher(monkeypatch):
    monkeypatch.delenv("DISTRIBUTION_DRY_RUN", raising=False)
    pub = get_publisher("pinterest", access_token="tok", account_ref="board-1")
    assert isinstance(pub, PinterestPublisher)
    assert not isinstance(pub, NotImplementedPublisher)


def test_pinterest_pin_success(monkeypatch):
    calls = _seq_post(monkeypatch, [_Resp(201, {"id": "pin-7"})])
    r = PinterestPublisher(access_token="tok", account_ref="board-1").publish(
        "a pin", media_url="https://cdn/img.jpg"
    )
    assert r.success, r.error
    assert r.platform_post_id == "pin-7"
    assert r.platform_url == "https://www.pinterest.com/pin/pin-7/"
    body = calls[0][1]["json"]
    assert body["board_id"] == "board-1"
    assert body["media_source"] == {"source_type": "image_url", "url": "https://cdn/img.jpg"}


def test_pinterest_requires_account_ref():
    r = PinterestPublisher(access_token="tok", account_ref=None).publish(
        "x", media_url="https://cdn/i.jpg"
    )
    assert not r.success and "account_ref" in r.error


def test_pinterest_requires_media(monkeypatch):
    """Pinterest is image-first — a text-only post must fail closed, no network call."""
    posted = []
    monkeypatch.setattr(requests, "post", lambda *a, **k: posted.append(a) or _Resp(201, {}))
    r = PinterestPublisher(access_token="tok", account_ref="board-1").publish("no image")
    assert not r.success and "image" in r.error.lower()
    assert posted == []


def test_pinterest_api_error_is_surfaced(monkeypatch):
    _seq_post(monkeypatch, [_Resp(403, text="forbidden")])
    r = PinterestPublisher(access_token="tok", account_ref="board-1").publish(
        "x", media_url="https://cdn/i.jpg"
    )
    assert not r.success and "403" in r.error


# ── OAuth wiring ─────────────────────────────────────────────────────────────


def test_threads_and_pinterest_are_oauth_platforms():
    """Both are OAuth-based, so they must be registered as OAuth providers and shown in the
    OAuth connect grid (unlike Bluesky's app-password flow)."""
    from backend.models.distribution import SUPPORTED_PLATFORMS
    from backend.services.distribution.oauth import PROVIDERS

    for platform in ("threads", "pinterest"):
        assert platform in SUPPORTED_PLATFORMS
        assert platform in PROVIDERS
        # oauth_status.all logic: supported, not stub, and an OAuth provider.
        assert platform != "stub" and platform in PROVIDERS
