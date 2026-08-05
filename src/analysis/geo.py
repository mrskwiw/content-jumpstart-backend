"""GEO / AEO output helpers (GEO-01): make content citable by AI answer engines.

Generative Engine Optimization — getting a brand cited *inside* ChatGPT /
Perplexity / Google AI Overviews — is the defining 2026 differentiator. AI
answer engines preferentially extract from (a) schema.org-marked FAQ/Article
content and (b) short, self-contained "answer blocks". These are the pure,
deterministic building blocks: JSON-LD generators + an answer-block length gate.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

_SCHEMA_CONTEXT = "https://schema.org"

# A markdown heading line (used to skip titles / find paragraph boundaries in answer-block extraction).
_HEADING_RE = re.compile(r"^\s*#{1,6}\s+")
# A non-prose opener: a bullet/numbered list item or a blockquote. An answer block must be a
# self-contained PROSE paragraph — AI answer engines extract paragraphs, not list/quote structure —
# so a lead that starts with one of these is not a valid answer block.
_NON_PROSE_RE = re.compile(r"^\s*([-*+]\s|\d+[.)]\s|>)")

# AI Overviews favour a self-contained ~40-60 word answer near the top.
_ANSWER_MIN_WORDS = 40
_ANSWER_MAX_WORDS = 60


def faq_jsonld(qa_pairs: Sequence[tuple[str, str]]) -> dict[str, Any]:
    """schema.org FAQPage JSON-LD from (question, answer) pairs."""
    if not qa_pairs:
        raise ValueError("faq_jsonld requires at least one Q/A pair")
    return {
        "@context": _SCHEMA_CONTEXT,
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q.strip(),
                "acceptedAnswer": {"@type": "Answer", "text": a.strip()},
            }
            for q, a in qa_pairs
        ],
    }


def article_jsonld(
    *,
    headline: str,
    description: str,
    author: str,
    date_published: str,
    url: str | None = None,
    publisher: str | None = None,
) -> dict[str, Any]:
    """schema.org Article JSON-LD. ``date_published`` should be ISO-8601."""
    data: dict[str, Any] = {
        "@context": _SCHEMA_CONTEXT,
        "@type": "Article",
        "headline": headline.strip(),
        "description": description.strip(),
        "author": {"@type": "Person", "name": author.strip()},
        "datePublished": date_published,
    }
    if url:
        data["url"] = url
        data["mainEntityOfPage"] = {"@type": "WebPage", "@id": url}
    if publisher:
        data["publisher"] = {"@type": "Organization", "name": publisher}
    return data


def howto_jsonld(
    *,
    name: str,
    steps: Sequence[str],
    description: str | None = None,
    total_time: str | None = None,
) -> dict[str, Any]:
    """schema.org HowTo JSON-LD from an ordered list of step texts (GEO-01).

    HowTo markup makes step-by-step content eligible for AI Overviews' procedural answers —
    the third schema type (with FAQPage + Article) GEO-01 targets. Blank/whitespace-only steps
    are dropped; ``total_time`` is an ISO-8601 duration (e.g. ``"PT15M"``).
    """
    clean_name = name.strip()
    if not clean_name:
        # A HowTo requires a name (schema.org) — reject blank/whitespace rather than emit
        # `"name": ""`, which is malformed markup answer engines silently ignore.
        raise ValueError("howto_jsonld requires a non-empty name")
    cleaned = [s.strip() for s in steps if s and s.strip()]
    if not cleaned:
        raise ValueError("howto_jsonld requires at least one non-empty step")
    data: dict[str, Any] = {
        "@context": _SCHEMA_CONTEXT,
        "@type": "HowTo",
        "name": clean_name,
        "step": [
            {"@type": "HowToStep", "position": i, "text": text}
            for i, text in enumerate(cleaned, start=1)
        ],
    }
    # Optional fields are OMITTED when blank/whitespace-only (never emitted as empty strings).
    clean_description = (description or "").strip()
    if clean_description:
        data["description"] = clean_description
    clean_total_time = (total_time or "").strip()
    if clean_total_time:
        data["totalTime"] = clean_total_time
    return data


@dataclass(frozen=True)
class AnswerBlockCheck:
    word_count: int
    ok: bool
    reason: str


def check_answer_block(
    text: str, *, min_words: int = _ANSWER_MIN_WORDS, max_words: int = _ANSWER_MAX_WORDS
) -> AnswerBlockCheck:
    """Validate a candidate answer block is the AI-extractable ~40-60 word length."""
    n = len(text.split())
    if n < min_words:
        return AnswerBlockCheck(n, False, f"too short ({n} < {min_words} words)")
    if n > max_words:
        return AnswerBlockCheck(n, False, f"too long ({n} > {max_words} words)")
    return AnswerBlockCheck(n, True, "ok")


def _looks_like_headline(line: str) -> bool:
    """Whether ``line`` reads as a title (skippable) rather than the lead answer paragraph.

    A markdown heading, or a short line with no sentence-ending punctuation. This keeps
    ``opening_answer_block`` from blindly skipping a genuine lead paragraph on content that opens
    with prose instead of a dedicated headline (otherwise the answer-block check would evaluate
    the wrong paragraph, or nothing). See BUGS.md Decision #234.
    """
    stripped = line.strip()
    if _HEADING_RE.match(line):
        return True
    return len(stripped.split()) <= 12 and not stripped.endswith((".", "!", "?", ":", ";"))


def opening_answer_block(content: str) -> str:
    """The lead prose paragraph of ``content`` — the AEO "answer block" candidate.

    AI answer engines preferentially extract a short, self-contained PROSE answer positioned near
    the top. The candidate is the first prose paragraph; a leading title line is skipped ONLY when
    it reads like a headline (``_looks_like_headline``), so content that opens directly with prose
    is still evaluated correctly. Returns "" when no prose paragraph is found — including when the
    lead is a list or blockquote (``_NON_PROSE_RE``), which is not an extractable answer block.
    """
    lines = content.splitlines()
    n = len(lines)
    i = 0
    while i < n and not lines[i].strip():  # skip leading blanks
        i += 1
    if i < n and _looks_like_headline(lines[i]):  # skip the headline line only if it looks like one
        i += 1
        while i < n and not lines[i].strip():  # skip blanks after the headline
            i += 1
    if i >= n or _NON_PROSE_RE.match(
        lines[i]
    ):  # a list/blockquote lead is not a prose answer block
        return ""
    para: list[str] = []
    while i < n:
        line = lines[i]
        if not line.strip() or _HEADING_RE.match(line):  # paragraph ends at a blank / new heading
            break
        para.append(line.strip())
        i += 1
    return " ".join(para).strip()
