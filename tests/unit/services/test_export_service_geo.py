"""GEO wiring: schema.org Article JSON-LD in blog Markdown deliverables (GEO-01)."""

import asyncio
import json
from datetime import datetime
from unittest.mock import MagicMock

from backend.services.export_service import (
    _blog_geo_jsonld_block,
    _blog_howto_jsonld_block,
    generate_export_file,
)


def _run(coro):
    return asyncio.run(coro)


def _make_client(name="Acme Co"):
    c = MagicMock()
    c.name = name
    c.id = "client-1"
    return c


def _make_project(name="Spring Campaign"):
    p = MagicMock()
    p.name = name
    p.id = "proj-1"
    return p


def _make_post(content, platform="blog", template="Blog Post"):
    p = MagicMock()
    p.content = content
    p.target_platform = platform
    p.template_name = template
    p.word_count = 800
    p.has_cta = True
    p.readability_score = None
    p.twitter_share_copy = None
    p.created_at = None
    return p


_BLOG = "How to Rank in AI Overviews\n\nAnswer-engine visibility is the new SEO. Here is how."

_OPEN = '<script type="application/ld+json">'
_CLOSE = "</script>"


def _jsonld_from(text: str) -> dict:
    """Extract and parse the JSON-LD payload from inside the <script> tag."""
    inner = text.split(_OPEN, 1)[1].split(_CLOSE, 1)[0]
    return json.loads(inner)


def test_non_blog_post_yields_no_block():
    assert _blog_geo_jsonld_block(_make_post(_BLOG, platform="linkedin"), _make_client()) == []


def test_empty_content_yields_no_block():
    assert _blog_geo_jsonld_block(_make_post("", platform="blog"), _make_client()) == []


def test_blog_block_emits_publishable_script_tag():
    block = _blog_geo_jsonld_block(_make_post(_BLOG), _make_client(name="Acme Co"))
    assert block  # non-empty
    joined = "\n".join(block)
    # Must be a real, ready-to-paste JSON-LD script tag, not a bare code block.
    assert _OPEN in joined and _CLOSE in joined
    data = _jsonld_from(joined)
    assert data["@type"] == "Article"
    assert data["@context"] == "https://schema.org"
    assert data["headline"] == "How to Rank in AI Overviews"  # first line, markdown stripped
    assert data["author"]["name"] == "Acme Co"
    assert data["publisher"]["name"] == "Acme Co"
    assert "description" in data


def test_script_breakout_is_escaped():
    # Client-controlled content containing </script> must NOT close the tag early.
    malicious = "Beat the </script><script>alert(1)</script> algorithm\n\nBody text here."
    block = _blog_geo_jsonld_block(_make_post(malicious), _make_client())
    joined = "\n".join(block)

    # Exactly one opening and one closing script tag — the payload didn't break out.
    assert joined.count(_OPEN) == 1
    assert joined.count(_CLOSE) == 1
    # The literal </script> from content is escaped inside the payload.
    assert "\\u003c/script\\u003e" in joined
    # ...and it still parses as valid JSON-LD, decoding back to the real text.
    data = _jsonld_from(joined)
    assert data["@type"] == "Article"
    assert "</script>" in data["headline"]  # < decoded back to <


def test_blog_block_uses_post_created_date():
    post = _make_post(_BLOG)
    post.created_at = datetime(2026, 3, 14, 9, 30)
    block = _blog_geo_jsonld_block(post, _make_client())
    assert _jsonld_from("\n".join(block))["datePublished"] == "2026-03-14"


def test_markdown_export_embeds_jsonld_for_blog_post():
    out_path, size = _run(
        generate_export_file(
            posts=[_make_post(_BLOG)],
            client=_make_client(),
            project=_make_project(),
            format="md",
            relative_path="Acme Co/blog.md",
        )
    )
    try:
        text = out_path.read_text(encoding="utf-8")
        assert "GEO Metadata (schema.org Article JSON-LD)" in text
        # End-to-end: the exported artifact contains publishable structured data
        # (a real script tag), not just a fenced code block.
        assert _OPEN in text
        assert _jsonld_from(text)["@type"] == "Article"
        assert size > 0
    finally:
        out_path.unlink(missing_ok=True)


_HOWTO_BLOG = (
    "How to Deploy with Zero Downtime\n\n"
    "Follow these steps:\n\n"
    "1. Build the container image\n"
    "2. Push it to the registry\n"
    "3) Roll out with a health check\n"
    "Step 4: Verify metrics\n"
)


def test_howto_block_emitted_for_numbered_steps():
    block = _blog_howto_jsonld_block(_make_post(_HOWTO_BLOG), _make_client())
    assert block
    data = _jsonld_from("\n".join(block))
    assert data["@type"] == "HowTo"
    assert data["name"] == "How to Deploy with Zero Downtime"
    # All four marker styles (1. / 2. / 3) / Step 4:) parsed, in order, marker stripped.
    assert [s["text"] for s in data["step"]] == [
        "Build the container image",
        "Push it to the registry",
        "Roll out with a health check",
        "Verify metrics",
    ]
    assert [s["position"] for s in data["step"]] == [1, 2, 3, 4]


def test_howto_block_emitted_for_step_by_step_headline():
    content = "Step-by-Step: Migrate to Postgres\n\n1. Back up\n2. Dump the schema\n3. Restore\n"
    block = _blog_howto_jsonld_block(_make_post(content), _make_client())
    assert block and _jsonld_from("\n".join(block))["@type"] == "HowTo"


def test_howto_block_skipped_for_listicle_headline():
    # A numbered list under a listicle headline is NOT a procedure — must not emit HowTo.
    listicle = (
        "10 Ways to Grow Your Audience\n\n"
        "Top tactics:\n\n"
        "1. Post consistently\n"
        "2. Engage with comments\n"
        "3) Use hashtags\n"
    )
    assert _blog_howto_jsonld_block(_make_post(listicle), _make_client()) == []


def test_howto_block_skipped_for_reference_list_headline():
    reference = "A Brief History of SEO\n\nKey milestones:\n\n1. Keyword stuffing\n2. PageRank\n"
    assert _blog_howto_jsonld_block(_make_post(reference), _make_client()) == []


def test_howto_block_skipped_without_steps():
    # Prose with no numbered list → no HowTo (Article still applies separately).
    assert _blog_howto_jsonld_block(_make_post(_BLOG), _make_client()) == []


def test_howto_block_skipped_with_single_step():
    one = "My Guide\n\n1. Just do this one thing\n"
    assert _blog_howto_jsonld_block(_make_post(one), _make_client()) == []


def test_howto_block_skipped_for_non_blog():
    assert (
        _blog_howto_jsonld_block(_make_post(_HOWTO_BLOG, platform="linkedin"), _make_client()) == []
    )


def test_markdown_export_embeds_howto_for_stepwise_blog():
    out_path, _ = _run(
        generate_export_file(
            posts=[_make_post(_HOWTO_BLOG)],
            client=_make_client(),
            project=_make_project(),
            format="md",
            relative_path="Acme Co/howto.md",
        )
    )
    try:
        text = out_path.read_text(encoding="utf-8")
        # A stepwise blog carries BOTH Article and HowTo markup — two script tags.
        assert "GEO Metadata (schema.org HowTo JSON-LD)" in text
        assert "GEO Metadata (schema.org Article JSON-LD)" in text
        assert text.count(_OPEN) == 2
    finally:
        out_path.unlink(missing_ok=True)


def test_markdown_export_no_jsonld_for_non_blog_post():
    out_path, _ = _run(
        generate_export_file(
            posts=[_make_post(_BLOG, platform="linkedin")],
            client=_make_client(),
            project=_make_project(),
            format="md",
            relative_path="Acme Co/li.md",
        )
    )
    try:
        text = out_path.read_text(encoding="utf-8")
        assert "GEO Metadata" not in text
    finally:
        out_path.unlink(missing_ok=True)
