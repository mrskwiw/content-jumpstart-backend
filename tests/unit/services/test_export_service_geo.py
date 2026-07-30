"""GEO wiring: schema.org Article JSON-LD in blog Markdown deliverables (GEO-01)."""

import asyncio
import json
from datetime import datetime
from unittest.mock import MagicMock

from backend.services.export_service import _blog_geo_jsonld_block, generate_export_file


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
