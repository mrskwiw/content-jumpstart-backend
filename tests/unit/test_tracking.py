"""Attribution — build_tracked_url (UTM params)."""

from urllib.parse import parse_qs, urlparse

import pytest

from backend.services.tracking import build_tracked_url, tag_urls_in_text


def _qs(url):
    return parse_qs(urlparse(url).query)


def test_basic_utms_added():
    url = build_tracked_url("https://acme.com/post", source="linkedin", campaign="jan-launch")
    q = _qs(url)
    assert q["utm_source"] == ["linkedin"]
    assert q["utm_medium"] == ["social"]
    assert q["utm_campaign"] == ["jan-launch"]


def test_preserves_existing_query_params():
    url = build_tracked_url("https://acme.com/p?ref=abc&id=7", source="x", campaign="c")
    q = _qs(url)
    assert q["ref"] == ["abc"] and q["id"] == ["7"]
    assert q["utm_source"] == ["x"]


def test_overrides_preexisting_utm():
    url = build_tracked_url("https://acme.com/p?utm_source=old", source="new", campaign="c")
    q = _qs(url)
    assert q["utm_source"] == ["new"]  # ours wins, no duplicate
    assert len(q["utm_source"]) == 1


def test_optional_content_and_term():
    url = build_tracked_url(
        "https://acme.com/p", source="s", campaign="c", content="variant-a", term="ai tools"
    )
    q = _qs(url)
    assert q["utm_content"] == ["variant-a"]
    assert q["utm_term"] == ["ai tools"]  # space properly encoded/decoded


def test_llm_referral_as_channel():
    url = build_tracked_url("https://acme.com/p", source="chatgpt", medium="llm", campaign="geo")
    q = _qs(url)
    assert q["utm_source"] == ["chatgpt"] and q["utm_medium"] == ["llm"]


def test_requires_source_and_campaign():
    with pytest.raises(ValueError):
        build_tracked_url("https://acme.com", source="", campaign="c")
    with pytest.raises(ValueError):
        build_tracked_url("https://acme.com", source="s", campaign="")


def test_signed_query_param_preserved_byte_exact():
    # A signature param must survive untouched (no re-encoding of + / % / case).
    signed = "https://acme.com/p?sig=aB%2Fc9%2Bd&exp=1712000000"
    url = build_tracked_url(signed, source="linkedin", campaign="c")
    assert "sig=aB%2Fc9%2Bd" in url  # exact bytes, not re-encoded
    assert "exp=1712000000" in url
    assert "utm_source=linkedin" in url


def test_path_and_scheme_preserved():
    url = build_tracked_url("https://acme.com/a/b/c", source="s", campaign="c")
    parsed = urlparse(url)
    assert parsed.scheme == "https" and parsed.netloc == "acme.com" and parsed.path == "/a/b/c"


# --- tag_urls_in_text -------------------------------------------------------


def test_tag_single_url_in_text():
    out = tag_urls_in_text("Read more at https://acme.com/post", source="linkedin", campaign="c")
    assert "https://acme.com/post?utm_source=linkedin" in out
    assert out.startswith("Read more at ")


def test_tag_text_without_urls_unchanged():
    text = "No links here, just prose."
    assert tag_urls_in_text(text, source="x", campaign="c") == text


def test_tag_preserves_trailing_period():
    out = tag_urls_in_text("Visit https://acme.com now.", source="x", campaign="c")
    # The period stays in the prose, not swallowed into the URL.
    assert out.endswith(" now.")
    assert "acme.com now" not in out  # 'now' not part of the URL
    q = parse_qs(urlparse(out.split()[1].rstrip(".")).query)
    assert q["utm_source"] == ["x"]


def test_tag_is_idempotent():
    once = tag_urls_in_text("go https://acme.com/p", source="li", campaign="jan")
    twice = tag_urls_in_text(once, source="li", campaign="jan")
    assert once == twice  # already-tagged URL not re-tagged
    assert once.count("utm_source=") == 1


def test_tag_multiple_urls():
    out = tag_urls_in_text("A https://a.com and B https://b.com end", source="fb", campaign="c")
    assert out.count("utm_source=fb") == 2
    assert out.startswith("A ") and out.endswith(" end")


def test_tag_passes_medium_through():
    out = tag_urls_in_text("x https://acme.com", source="chatgpt", campaign="geo", medium="llm")
    q = parse_qs(urlparse(out.split()[1]).query)
    assert q["utm_medium"] == ["llm"]
