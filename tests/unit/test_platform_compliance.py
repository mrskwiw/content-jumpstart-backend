"""Pre-publish platform compliance gate."""

from backend.services.platform_compliance import check_compliance, count_hashtags
from src.models.client_brief import Platform


def test_count_hashtags_word_boundary():
    assert count_hashtags("hello #ai and #growth-hacking") == 2
    assert count_hashtags("no tags here") == 0
    assert count_hashtags("email a#b is not a tag") == 0


def test_twitter_over_280_is_hard_fail():
    text = "x " * 200  # 400 chars
    r = check_compliance(text, Platform.TWITTER)
    assert r.publishable is False
    assert any("hard limit of 280" in v for v in r.hard)


def test_twitter_short_is_publishable_with_warning():
    r = check_compliance("Ship boring copy. It converts.", Platform.TWITTER)
    assert r.publishable is True  # under 280
    # word count below optimal band -> a warning, not a block
    assert r.warnings


def test_too_many_hashtags_hard_fail_on_linkedin():
    # LinkedIn policy max is 3
    body = "word " * 240 + "#a #b #c #d #e"
    r = check_compliance(body, Platform.LINKEDIN)
    assert r.hashtag_count == 5
    assert r.publishable is False
    assert any("exceeds linkedin max of 3" in v for v in r.hard)


def test_hashtags_on_disabled_platform_warns_not_blocks():
    body = "word " * 60 + "#promo"
    r = check_compliance(body, Platform.FACEBOOK)
    assert r.publishable is True
    assert any("should not use hashtags" in w for w in r.warnings)


def test_clean_linkedin_post_publishable_no_hard():
    body = "word " * 240 + "#industry #niche #brand"
    r = check_compliance(body, Platform.LINKEDIN)
    assert r.publishable is True
    assert r.hard == []
    assert r.hashtag_count == 3


def test_report_reports_counts():
    r = check_compliance("hello world #x", Platform.TWITTER)
    assert r.char_count == len("hello world #x")
    assert r.word_count == 3
    assert r.hashtag_count == 1
    assert r.platform == "twitter"
