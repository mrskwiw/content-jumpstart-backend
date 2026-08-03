"""GEO wiring: schema.org Article JSON-LD in blog Markdown deliverables (GEO-01)."""

import asyncio
import json
from datetime import datetime
from unittest.mock import MagicMock

from backend.services.export_service import (
    _blog_answer_block_advisory,
    _blog_faq_jsonld_block,
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


def test_howto_block_emitted_for_varied_procedural_headlines():
    # Common procedural forms beyond the "How to …" prefix should still qualify.
    steps = "\n\n1. First\n2. Second\n"
    for title in (
        "Tutorial: Setting up CI",
        "Postgres Migration in 3 Steps",
        "7 Steps to a Faster Site",
        "Deploy Postgres: A Step-by-Step Walkthrough",
    ):
        block = _blog_howto_jsonld_block(_make_post(title + steps), _make_client())
        assert block, f"expected HowTo for procedural title: {title!r}"
        assert _jsonld_from("\n".join(block))["@type"] == "HowTo"


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


def test_howto_block_skipped_for_bare_guide_overview():
    # Precision boundary: a bare "Guide to …" overview is NOT procedural (no steps/how-to/
    # tutorial signal), so numbered items must NOT trigger HowTo. Erring toward precision:
    # a missed how-to is harmless, a mislabeled overview is spammy structured data.
    overview = "A Guide to Marketing Strategy\n\nThemes:\n\n1. Positioning\n2. Channels\n"
    assert _blog_howto_jsonld_block(_make_post(overview), _make_client()) == []


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


# --- FAQPage JSON-LD (GEO-01, completes the Article/HowTo/FAQ triad) --------------------

# Heading-question FAQ: honored because an explicit "Frequently Asked Questions" section is present.
_FAQ_BLOG = (
    "GEO Explained\n\n"
    "Intro paragraph about answer engines.\n\n"
    "## Frequently Asked Questions\n\n"
    "## What is GEO?\n\n"
    "GEO is Generative Engine Optimization: structuring content so AI answer engines cite it.\n\n"
    "## How is it different from SEO?\n\n"
    "SEO targets ranked links; GEO targets being quoted inside AI answers like ChatGPT.\n"
)

# "Q:"/"A:" pairs are an unambiguous FAQ marker — honored WITHOUT any FAQ section heading.
_FAQ_QA_BLOG = (
    "Pricing Questions\n\n"
    "Q: Do you offer refunds?\n"
    "A: Yes, within 30 days of purchase, no questions asked.\n\n"
    "Q: Can I change plans?\n"
    "A: Absolutely — upgrade or downgrade anytime from your dashboard.\n"
)

_FAQ_BOLD_BLOG = (
    "Security Overview\n\n"
    "## FAQ\n\n"
    "**Is my data secure?**\n\n"
    "Yes, everything is encrypted at rest and in transit using industry standards.\n\n"
    "**Where is it stored?**\n\n"
    "In SOC 2 compliant data centers within your selected region.\n"
)


def test_faq_block_emitted_for_heading_questions():
    block = _blog_faq_jsonld_block(_make_post(_FAQ_BLOG), _make_client())
    assert block
    data = _jsonld_from("\n".join(block))
    assert data["@type"] == "FAQPage"
    names = [q["name"] for q in data["mainEntity"]]
    assert names == ["What is GEO?", "How is it different from SEO?"]
    first = data["mainEntity"][0]["acceptedAnswer"]["text"]
    assert first.startswith("GEO is Generative Engine Optimization")


def test_faq_block_emitted_for_q_and_a_prefixes():
    # "Q:"/"A:" prefixed pairs are an unambiguous FAQ structure; the A: marker is stripped.
    data = _jsonld_from("\n".join(_blog_faq_jsonld_block(_make_post(_FAQ_QA_BLOG), _make_client())))
    assert data["@type"] == "FAQPage"
    assert [q["name"] for q in data["mainEntity"]] == [
        "Do you offer refunds?",
        "Can I change plans?",
    ]
    assert data["mainEntity"][0]["acceptedAnswer"]["text"] == (
        "Yes, within 30 days of purchase, no questions asked."
    )


def test_faq_block_emitted_for_bold_questions():
    data = _jsonld_from(
        "\n".join(_blog_faq_jsonld_block(_make_post(_FAQ_BOLD_BLOG), _make_client()))
    )
    assert data["@type"] == "FAQPage"
    assert [q["name"] for q in data["mainEntity"]] == [
        "Is my data secure?",
        "Where is it stored?",
    ]


def test_faq_block_skipped_for_single_pair():
    one = "My Post\n\n## FAQ\n\n## What is X?\n\nX is a thing you use.\n"
    assert _blog_faq_jsonld_block(_make_post(one), _make_client()) == []


def test_faq_block_skipped_for_narrative_question_headings_without_faq_section():
    # THE precision boundary (Decision #233): an ordinary article whose sections are phrased as
    # questions — but with NO explicit FAQ section and no Q:/A: markers — must NOT emit FAQPage.
    narrative = (
        "The Future of Marketing\n\n"
        "## Why does this matter?\n\n"
        "Because attention is scarce and trust compounds over time.\n\n"
        "## What comes next?\n\n"
        "Brands that adapt their voice to AI answer engines will win the decade.\n"
    )
    assert _blog_faq_jsonld_block(_make_post(narrative), _make_client()) == []


def test_faq_only_marks_questions_inside_the_faq_section():
    # Section-scoped (Decision #233): a post with narrative question headings BEFORE a real FAQ
    # section must mark up ONLY the in-section questions, never the earlier narrative headers.
    content = (
        "The Future of Marketing\n\n"
        "## Why does this matter?\n\n"
        "Because attention is scarce and trust compounds over time.\n\n"
        "## What comes next?\n\n"
        "Brands adapt or fade.\n\n"
        "## Frequently Asked Questions\n\n"
        "## Is it expensive?\n\n"
        "No — it reuses your existing content pipeline.\n\n"
        "## How long does setup take?\n\n"
        "About an afternoon for a first campaign.\n"
    )
    data = _jsonld_from("\n".join(_blog_faq_jsonld_block(_make_post(content), _make_client())))
    names = [q["name"] for q in data["mainEntity"]]
    # Only the two in-section questions — the narrative headers are excluded.
    assert names == ["Is it expensive?", "How long does setup take?"]


def test_faq_section_closes_at_same_level_non_question_heading():
    # A non-question heading at the FAQ section's level closes it: later question headings in a
    # DIFFERENT section are not part of the FAQ and must not be marked up.
    content = (
        "## FAQ\n\n"
        "## What is included?\n\n"
        "Everything in your plan.\n\n"
        "## Testimonials\n\n"  # same level, non-question → closes the FAQ section
        "## Why do customers love us?\n\n"  # now OUTSIDE the FAQ section → ignored
        "Because it works.\n"
    )
    # Only one in-section pair remains → below the ≥2 threshold → no block at all.
    assert _blog_faq_jsonld_block(_make_post(content), _make_client()) == []


def test_faq_block_skipped_for_rhetorical_prose_questions():
    # Questions buried in a paragraph are NOT structural FAQ markers — must not emit FAQPage.
    prose = (
        "Why Content Matters\n\n"
        "Ever wonder why content matters? It builds trust. Does it really work? Yes, it does.\n"
    )
    assert _blog_faq_jsonld_block(_make_post(prose), _make_client()) == []


def test_faq_block_drops_answerless_cta_question():
    # Under an explicit FAQ section, a lone answer-less "Ready to buy?" heading contributes no
    # pair, so with only one real Q/A the block is skipped (≥2 required) — a CTA question never
    # becomes spammy markup.
    content = (
        "## FAQ\n\n"
        "## What is included?\n\n"
        "Everything in your plan, billed monthly.\n\n"
        "## Ready to buy?\n\n"
        "## Footer\n\n"
        "Copyright notice.\n"
    )
    assert _blog_faq_jsonld_block(_make_post(content), _make_client()) == []


def test_faq_block_skipped_for_non_blog():
    assert _blog_faq_jsonld_block(_make_post(_FAQ_BLOG, platform="linkedin"), _make_client()) == []


def test_faq_answer_stops_at_heading_but_deeper_subheading_keeps_section_open():
    # The answer must not bleed past a heading; a DEEPER (level-3) non-question sub-heading ends
    # the answer but does NOT close the FAQ section, so the following level-2 question still counts.
    content = (
        "## FAQ\n\n"
        "## What is GEO?\n\n"
        "A short definition.\n\n"
        "### Aside\n\n"
        "Body that is not part of any answer.\n\n"
        "## Does it help?\n\n"
        "Yes it does, measurably.\n"
    )
    data = _jsonld_from("\n".join(_blog_faq_jsonld_block(_make_post(content), _make_client())))
    assert [q["name"] for q in data["mainEntity"]] == ["What is GEO?", "Does it help?"]
    assert data["mainEntity"][0]["acceptedAnswer"]["text"] == "A short definition."


# --- Answer-block advisory (GEO-01 check_answer_block wired into blog exports) --------


def _blog_with_opening(word_count: int) -> str:
    """A blog post whose opening paragraph (after the title) has exactly ``word_count`` words."""
    body = " ".join(f"word{i}" for i in range(word_count))
    return f"My Blog Title\n\n{body}\n"


def test_answer_block_advisory_ok_for_in_range_opening():
    block = _blog_answer_block_advisory(_make_post(_blog_with_opening(50)), _make_client())
    joined = "\n".join(block)
    assert "GEO Answer Block (advisory)" in joined
    assert "50 words" in joined
    assert "✅" in joined


def test_answer_block_advisory_flags_too_short():
    joined = "\n".join(
        _blog_answer_block_advisory(_make_post(_blog_with_opening(20)), _make_client())
    )
    assert "20 words" in joined
    assert "under 40" in joined
    assert "⚠" in joined


def test_answer_block_advisory_flags_too_long():
    joined = "\n".join(
        _blog_answer_block_advisory(_make_post(_blog_with_opening(80)), _make_client())
    )
    assert "80 words" in joined
    assert "over 60" in joined
    assert "⚠" in joined


def test_answer_block_advisory_evaluates_lead_prose_when_no_title():
    # A post that opens directly with a long prose paragraph (no separate headline) must be
    # evaluated as the answer block itself, not blindly skipped as if line 1 were a title.
    body = " ".join(f"word{i}" for i in range(50)) + "."  # 50-word sentence (ends with a period)
    joined = "\n".join(_blog_answer_block_advisory(_make_post(body + "\n"), _make_client()))
    assert "50 words" in joined
    assert "✅" in joined


def test_answer_block_advisory_skips_non_blog():
    post = _make_post(_blog_with_opening(50), platform="linkedin")
    assert _blog_answer_block_advisory(post, _make_client()) == []


def test_answer_block_advisory_skips_when_no_opening_paragraph():
    # Title only, or a heading straight after the title → no prose answer block → no advisory.
    assert _blog_answer_block_advisory(_make_post("Just A Title\n"), _make_client()) == []
    assert (
        _blog_answer_block_advisory(_make_post("Title\n\n## Section\n\nBody.\n"), _make_client())
        == []
    )


def test_answer_block_advisory_is_advisory_not_gating():
    # It's a hint block, never a <script>/structured-data or a pass/fail gate.
    joined = "\n".join(
        _blog_answer_block_advisory(_make_post(_blog_with_opening(20)), _make_client())
    )
    assert _OPEN not in joined  # not JSON-LD


def test_markdown_export_includes_answer_block_advisory_for_blog():
    out_path, _ = _run(
        generate_export_file(
            posts=[_make_post(_blog_with_opening(50))],
            client=_make_client(),
            project=_make_project(),
            format="md",
            relative_path="Acme Co/answerblock.md",
        )
    )
    try:
        text = out_path.read_text(encoding="utf-8")
        assert "GEO Answer Block (advisory)" in text
        assert "50 words" in text
    finally:
        out_path.unlink(missing_ok=True)


def test_markdown_export_embeds_faq_and_article_for_qa_blog():
    out_path, _ = _run(
        generate_export_file(
            posts=[_make_post(_FAQ_BLOG)],
            client=_make_client(),
            project=_make_project(),
            format="md",
            relative_path="Acme Co/faq.md",
        )
    )
    try:
        text = out_path.read_text(encoding="utf-8")
        # A Q/A blog carries BOTH Article and FAQPage markup — two script tags.
        assert "GEO Metadata (schema.org FAQPage JSON-LD)" in text
        assert "GEO Metadata (schema.org Article JSON-LD)" in text
        assert text.count(_OPEN) == 2
    finally:
        out_path.unlink(missing_ok=True)
