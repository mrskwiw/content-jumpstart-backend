"""COMPLIANCE-01: TikTok and YouTube carry AI disclosure in their own API fields
(verified against current docs 2026-10-28), never as text in the caption."""

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.services.distribution import publishers as pub


def _ok(json_body, headers=None):
    resp = MagicMock(status_code=200, ok=True, headers=headers or {})
    resp.json.return_value = json_body
    resp.raise_for_status.return_value = None
    return resp


@pytest.mark.parametrize("flag", [True, False])
def test_tiktok_sets_is_aigc(flag):
    # publishers import requests inside publish(), so patch the module attribute itself.
    with patch("requests.post", return_value=_ok({"data": {"publish_id": "x"}})) as post:
        pub.TikTokPublisher("tok").publish("caption", "https://cdn/x.mp4", ai_generated=flag)
    body = post.call_args.kwargs["json"]
    assert body["post_info"]["is_aigc"] is flag
    assert "Drafted with AI" not in body["post_info"]["title"]


@pytest.mark.parametrize("flag", [True, False])
def test_youtube_sets_contains_synthetic_media(flag):
    # No "location" header ⇒ YouTube returns before streaming, so no network is touched.
    with patch("requests.post", return_value=_ok({}, {})) as post:
        pub.YouTubePublisher("tok").publish("desc", "https://cdn/x.mp4", ai_generated=flag)
    body = json.loads(post.call_args_list[0].kwargs["data"])
    assert body["status"]["containsSyntheticMedia"] is flag


def test_every_publisher_accepts_the_ai_generated_keyword():
    import inspect

    classes = [
        c for c in vars(pub).values() if inspect.isclass(c) and issubclass(c, pub.BasePublisher)
    ]
    assert len(classes) >= 10
    for cls in classes:
        params = inspect.signature(cls.publish).parameters
        assert "ai_generated" in params, f"{cls.__name__}.publish lacks ai_generated"
        assert params["ai_generated"].kind is inspect.Parameter.KEYWORD_ONLY
