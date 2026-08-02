"""GEO / AEO output helpers (GEO-01): make content citable by AI answer engines.

Generative Engine Optimization — getting a brand cited *inside* ChatGPT /
Perplexity / Google AI Overviews — is the defining 2026 differentiator. AI
answer engines preferentially extract from (a) schema.org-marked FAQ/Article
content and (b) short, self-contained "answer blocks". These are the pure,
deterministic building blocks: JSON-LD generators + an answer-block length gate.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

_SCHEMA_CONTEXT = "https://schema.org"

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
    cleaned = [s.strip() for s in steps if s and s.strip()]
    if not cleaned:
        raise ValueError("howto_jsonld requires at least one non-empty step")
    data: dict[str, Any] = {
        "@context": _SCHEMA_CONTEXT,
        "@type": "HowTo",
        "name": name.strip(),
        "step": [
            {"@type": "HowToStep", "position": i, "text": text}
            for i, text in enumerate(cleaned, start=1)
        ],
    }
    if description:
        data["description"] = description.strip()
    if total_time:
        data["totalTime"] = total_time.strip()
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
