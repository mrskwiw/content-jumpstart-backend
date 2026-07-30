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


def test_non_blog_post_yields_no_block():
    assert _blog_geo_jsonld_block(_make_post(_BLOG, platform="linkedin"), _make_client()) == []


def test_empty_content_yields_no_block():
    assert _blog_geo_jsonld_block(_make_post("", platform="blog"), _make_client()) == []


def test_blog_block_is_valid_article_jsonld():
    block = _blog_geo_jsonld_block(_make_post(_BLOG), _make_client(name="Acme Co"))
    assert block  # non-empty
    # Extract the fenced JSON payload and parse it.
    joined = "\n".join(block)
    payload = joined.split("```json\n", 1)[1].split("\n```", 1)[0]
    data = json.loads(payload)
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
    payload = "\n".join(block).split("```json\n", 1)[1].split("\n```", 1)[0]
    assert json.loads(payload)["datePublished"] == "2026-03-14"


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
        assert '"@type": "Article"' in text
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
