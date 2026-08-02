"""GEO-01 — schema.org JSON-LD generators + answer-block gate."""

import pytest

from backend.services.geo import article_jsonld, check_answer_block, faq_jsonld, howto_jsonld


def test_faq_jsonld_shape():
    data = faq_jsonld([("What is X?", "X is a thing."), ("Why X?", "Because.")])
    assert data["@context"] == "https://schema.org"
    assert data["@type"] == "FAQPage"
    assert len(data["mainEntity"]) == 2
    q0 = data["mainEntity"][0]
    assert q0["@type"] == "Question"
    assert q0["name"] == "What is X?"
    assert q0["acceptedAnswer"] == {"@type": "Answer", "text": "X is a thing."}


def test_faq_jsonld_strips_whitespace():
    data = faq_jsonld([("  Q ?  ", "  A.  ")])
    assert data["mainEntity"][0]["name"] == "Q ?"
    assert data["mainEntity"][0]["acceptedAnswer"]["text"] == "A."


def test_faq_jsonld_requires_pairs():
    with pytest.raises(ValueError):
        faq_jsonld([])


def test_article_jsonld_minimal():
    data = article_jsonld(
        headline="How we fixed billing",
        description="A short post.",
        author="Jane Doe",
        date_published="2026-07-30",
    )
    assert data["@type"] == "Article"
    assert data["headline"] == "How we fixed billing"
    assert data["author"] == {"@type": "Person", "name": "Jane Doe"}
    assert data["datePublished"] == "2026-07-30"
    assert "url" not in data and "publisher" not in data


def test_article_jsonld_with_url_and_publisher():
    data = article_jsonld(
        headline="H",
        description="D",
        author="A",
        date_published="2026-07-30",
        url="https://acme.com/post",
        publisher="Acme",
    )
    assert data["url"] == "https://acme.com/post"
    assert data["mainEntityOfPage"] == {"@type": "WebPage", "@id": "https://acme.com/post"}
    assert data["publisher"] == {"@type": "Organization", "name": "Acme"}


def test_howto_jsonld_shape():
    data = howto_jsonld(name="How to deploy", steps=["Build the image", "Push it", "Roll out"])
    assert data["@context"] == "https://schema.org"
    assert data["@type"] == "HowTo"
    assert data["name"] == "How to deploy"
    assert [s["position"] for s in data["step"]] == [1, 2, 3]
    assert data["step"][0] == {"@type": "HowToStep", "position": 1, "text": "Build the image"}
    assert "description" not in data and "totalTime" not in data


def test_howto_jsonld_strips_and_drops_blank_steps():
    data = howto_jsonld(name="  Make tea  ", steps=["  Boil water  ", "   ", "", "Steep"])
    assert data["name"] == "Make tea"
    # Blank/whitespace-only steps are dropped and positions re-number contiguously.
    assert [s["text"] for s in data["step"]] == ["Boil water", "Steep"]
    assert [s["position"] for s in data["step"]] == [1, 2]


def test_howto_jsonld_optional_description_and_time():
    data = howto_jsonld(
        name="H", steps=["one step"], description="  A guide.  ", total_time="PT15M"
    )
    assert data["description"] == "A guide."
    assert data["totalTime"] == "PT15M"


def test_howto_jsonld_requires_a_non_empty_step():
    with pytest.raises(ValueError):
        howto_jsonld(name="H", steps=["   ", ""])


def test_answer_block_ok_in_range():
    text = " ".join(["word"] * 50)
    r = check_answer_block(text)
    assert r.ok is True and r.word_count == 50


def test_answer_block_too_short():
    r = check_answer_block("only three words")
    assert r.ok is False and "too short" in r.reason


def test_answer_block_too_long():
    r = check_answer_block(" ".join(["word"] * 80))
    assert r.ok is False and "too long" in r.reason


def test_answer_block_custom_range():
    r = check_answer_block("five words go right here", min_words=3, max_words=6)
    assert r.ok is True
