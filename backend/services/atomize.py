"""Content atomization / repurposing (table-stakes 2026).

Turn one long-form piece into platform atoms without an LLM: a numbered thread
(paragraph/sentence-packed to a per-post character limit) and pull-quote
candidates (punchy standalone sentences for quote graphics / teasers).
Deterministic building blocks; an LLM rewrite pass is a later enhancement.
"""

from __future__ import annotations

import re

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_NUMBERING_RESERVE = 8  # room for a trailing " (10/10)"


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.split(text.strip()) if s.strip()]


def _pack_words(sentence: str, budget: int) -> list[str]:
    """Hard-split an over-long sentence into word chunks that fit ``budget``."""
    chunks: list[str] = []
    piece = ""
    for word in sentence.split():
        if piece and len(piece) + 1 + len(word) > budget:
            chunks.append(piece)
            piece = word
        else:
            piece = f"{piece} {word}".strip()
    if piece:
        chunks.append(piece)
    return chunks


def to_thread(text: str, *, max_chars: int = 270) -> list[str]:
    """Split ``text`` into a numbered thread of posts each <= ``max_chars``."""
    budget = max_chars - _NUMBERING_RESERVE
    chunks: list[str] = []
    current = ""
    for sentence in _sentences(text):
        if len(sentence) > budget:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_pack_words(sentence, budget))
            continue
        if current and len(current) + 1 + len(sentence) > budget:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)

    total = len(chunks)
    if total <= 1:
        return chunks
    return [f"{chunk} ({i}/{total})" for i, chunk in enumerate(chunks, 1)]


def pull_quotes(text: str, *, min_words: int = 6, max_words: int = 20, limit: int = 3) -> list[str]:
    """Standalone punchy sentences suitable for quote graphics / teasers."""
    quotes = [
        s
        for s in _sentences(text)
        if min_words <= len(s.split()) <= max_words and not s.endswith(":")
    ]
    return quotes[:limit]
