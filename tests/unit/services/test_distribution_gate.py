"""Distribution pre-publish compliance gate (_gate_compliance).

The gate rejects content the platform API would hard-reject (api_only mode: char
ceiling + hashtag over-cap; word counts are advisory) at schedule time, so it fails
fast with a ValueError (-> 400) instead of a silent worker failure at publish time.
"""

import pytest

from backend.services.distribution.orchestrator import _gate_compliance


def test_oversized_tweet_is_rejected():
    with pytest.raises(ValueError, match="over the|API limit|limits"):
        _gate_compliance("twitter", "x " * 200)  # 400 chars > 280


def test_short_tweet_is_allowed():
    # Deliberately short — must NOT be blocked (word floor is advisory in api_only).
    _gate_compliance("twitter", "Ship boring copy. It converts.")


def test_long_linkedin_post_is_allowed():
    # ~1900 chars: over LinkedIn's quality ceiling but under the real API limit, so
    # the gate must not block it (only Twitter has a listed API char limit).
    _gate_compliance("linkedin", "word " * 380)


def test_excess_hashtags_rejected():
    with pytest.raises(ValueError):
        _gate_compliance("linkedin", "word " * 240 + " #a #b #c #d #e")


def test_unknown_platform_is_skipped():
    # instagram/tiktok/youtube/stub have no compliance spec -> nothing to gate.
    _gate_compliance("instagram", "x " * 5000)
    _gate_compliance("stub", "x " * 5000)


def test_valid_tweet_is_allowed():
    _gate_compliance("twitter", "A specific, punchy take on shipping boring copy that converts.")


def test_empty_content_is_rejected():
    for text in ("", "   ", "\n\t"):
        with pytest.raises(ValueError, match="empty"):
            _gate_compliance("twitter", text)


def test_media_only_post_with_empty_caption_is_allowed():
    # An image/video post can have no caption — the media is the content.
    _gate_compliance("facebook", "", has_media=True)
    _gate_compliance("twitter", "   ", has_media=True)


def test_media_post_with_oversized_caption_still_gated():
    # A caption that IS present must still respect the platform's char limit.
    with pytest.raises(ValueError, match="280|limit"):
        _gate_compliance("twitter", "x " * 200, has_media=True)


def test_empty_caption_without_media_still_rejected():
    with pytest.raises(ValueError, match="empty"):
        _gate_compliance("twitter", "", has_media=False)
