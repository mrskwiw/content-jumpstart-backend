"""COMPLIANCE-01 disclosure rules (backend/services/distribution/disclosure.py).

User decisions 2026-10-28 (docs/explore-compliance-01.md v1.1):
 D1  a text post published identical to its AI draft is disclosed; edited text is not
 D2  identical = equal after normalising whitespace/line breaks and letter case
 D3  platform-generated media (media-asset://) is always disclosed
 D4  native API flag where one exists (tiktok, youtube), else a visible label
 D5  free-text scheduled posts: checkbox, NULL/None treated as AI-generated
"""

from types import SimpleNamespace

import pytest

from backend.services.distribution import disclosure as d


def _sp(
    content="Hello world", *, post_id=None, media_url=None, ai_generated=None, platform="linkedin"
):
    return SimpleNamespace(
        content=content,
        post_id=post_id,
        media_url=media_url,
        ai_generated=ai_generated,
        platform=platform,
    )


def _post(draft):
    return SimpleNamespace(ai_draft_content=draft)


# ---- D2: normalisation ----------------------------------------------------------


@pytest.mark.parametrize(
    "a,b",
    [
        ("Hello  world", "Hello world"),
        ("Hello\n\nworld", "Hello world"),
        ("  Hello world\t", "Hello world"),
        ("HELLO World", "hello world"),
    ],
)
def test_whitespace_and_case_changes_are_not_edits(a, b):
    assert d.normalise(a) == d.normalise(b)


def test_changing_a_word_is_an_edit():
    assert d.normalise("Hello world") != d.normalise("Hello there world")


# ---- D1: linked posts -----------------------------------------------------------


def test_unedited_draft_is_disclosed():
    assert (
        d.needs_disclosure(
            _sp("Our new feature ships today.", post_id="p"), _post("Our new  feature ships today.")
        )
        is True
    )


def test_edited_post_is_not_disclosed():
    assert (
        d.needs_disclosure(
            _sp("We shipped the feature you asked for.", post_id="p"),
            _post("Our new feature ships today."),
        )
        is False
    )


def test_legacy_post_without_a_snapshot_is_disclosed():
    # Pre-v10 posts have no draft to compare against: conservative.
    assert d.needs_disclosure(_sp("anything", post_id="p"), _post(None)) is True


def test_linked_post_ignores_the_free_text_checkbox():
    # An unedited draft can't be un-disclosed by unticking a box.
    assert d.needs_disclosure(_sp("draft", post_id="p", ai_generated=False), _post("draft")) is True


def test_linked_post_that_is_gone_is_always_disclosed():
    # Codex review of 21ad00e: the free-text checkbox applies to free text only. A post
    # scheduled against a draft that later vanished (deleted / access revoked) must not
    # fall back to an "unticked" box and go out undisclosed.
    assert d.needs_disclosure(_sp("x", post_id="deleted", ai_generated=False), None) is True
    assert d.needs_disclosure(_sp("x", post_id="deleted", ai_generated=None), None) is True


# ---- D5: free text --------------------------------------------------------------


@pytest.mark.parametrize("flag,expected", [(None, True), (True, True), (False, False)])
def test_free_text_follows_the_checkbox_none_means_ai(flag, expected):
    assert d.needs_disclosure(_sp("my own words", ai_generated=flag), None) is expected


# ---- D3: generated media --------------------------------------------------------


def test_generated_media_is_always_disclosed_even_if_text_was_edited():
    sp = _sp("I rewrote this caption myself.", post_id="p", media_url="media-asset://abc")
    assert d.needs_disclosure(sp, _post("Original AI caption.")) is True


def test_users_own_media_url_does_not_force_disclosure():
    sp = _sp("my words", media_url="https://example.com/my-video.mp4", ai_generated=False)
    assert d.needs_disclosure(sp, None) is False


# ---- D4: mechanism --------------------------------------------------------------


def test_native_flag_platforms():
    assert d.NATIVE_FLAG_PLATFORMS == frozenset({"tiktok", "youtube"})


def test_label_appended_on_platforms_without_a_native_flag():
    out = d.with_text_label("Post body", "linkedin")
    assert out == "Post body\n\nDrafted with AI"


@pytest.mark.parametrize("platform", ["tiktok", "youtube"])
def test_no_text_label_where_a_native_flag_is_used(platform):
    assert d.with_text_label("Post body", platform) == "Post body"


def test_label_is_configurable(monkeypatch):
    monkeypatch.setenv("AI_DISCLOSURE_LABEL", "#AIGenerated")
    assert d.with_text_label("Body", "twitter") == "Body\n\n#AIGenerated"


def test_blank_label_setting_falls_back_to_the_default(monkeypatch):
    # The label can be reworded, not switched off by an empty value (fail closed).
    monkeypatch.setenv("AI_DISCLOSURE_LABEL", "   ")
    assert d.disclosure_label() == "Drafted with AI"


def test_label_is_not_appended_twice():
    once = d.with_text_label("Body", "linkedin")
    assert d.with_text_label(once, "linkedin") == once
