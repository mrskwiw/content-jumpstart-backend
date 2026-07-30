"""Generic-AI signal detection (BRAND-CORE-02).

Flags the exact signals LinkedIn's 2026 algorithm penalizes on *generic* AI
content — generic openers, cliché / AI-tell phrases, and bullet-heavy templated
structure — so generation can regenerate toward a point of view (the "publish
without editing" moat). The trigger for reach suppression is generic output, not
AI use, so a high score is the actionable signal.

Pure and deterministic (no LLM): a cheap pre-check the QA pass runs on every post.
Higher ``score`` (0..1) = more generic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Formulaic openers — the strongest tell of templated AI content.
_GENERIC_OPENERS: tuple[str, ...] = (
    # allow stacked adjectives: "today's fast-paced digital world"
    r"in today'?s (?:(?:fast-?paced|digital|competitive|ever-?changing|modern)[\s,]+){1,3}world",
    r"in the (?:(?:ever-?evolving|fast-?paced|digital|modern)[\s,]+){1,3}(?:landscape|world|age|era)",
    r"in this (?:blog )?post,? (?:we|i)('?ll| will| are going to)",
    r"are you (?:tired|struggling|looking|ready)\b",
    r"let'?s (?:dive|dive deep|explore|unpack|take a look)\b",
    r"when it comes to\b",
    r"picture this[:.]",
)

# Overused clichés / buzzwords.
_CLICHES: tuple[str, ...] = (
    "game-changer",
    "game changer",
    "leverage",
    "unlock",
    "dive deep",
    "in the realm of",
    "elevate",
    "seamless",
    "robust",
    "synergy",
    "take it to the next level",
    "low-hanging fruit",
    "move the needle",
    "supercharge",
    "unleash",
    "revolutionize",
    "cutting-edge",
    "best-in-class",
)

# Classic LLM tells.
_AI_TELLS: tuple[str, ...] = (
    "as an ai",
    "in conclusion",
    "furthermore",
    "moreover",
    "it is important to note",
    "it's important to note",
    "delve into",
    "tapestry",
    "in summary",
    "navigating the",
)

_OPENER_WEIGHT = 0.35
_CLICHE_WEIGHT = 0.10
_AI_TELL_WEIGHT = 0.15
_BULLET_WEIGHT = 0.20
_BULLET_RATIO_TRIGGER = 0.5  # >half the non-empty lines are bullets → templated
_MATCH_CAP = 3  # diminishing returns past a few of the same signal type

_BULLET_RE = re.compile(r"^\s*(?:[-*•·]|\d+[.)])\s+")


@dataclass
class GenericityReport:
    score: float
    is_generic: bool
    generic_opener: bool = False
    cliches: list[str] = field(default_factory=list)
    ai_tells: list[str] = field(default_factory=list)
    bullet_ratio: float = 0.0


def _bullet_ratio(text: str) -> float:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 0.0
    bullets = sum(1 for ln in lines if _BULLET_RE.match(ln))
    return bullets / len(lines)


def analyze_genericity(text: str, *, threshold: float = 0.4) -> GenericityReport:
    """Score how generic/templated a piece of content reads (0..1)."""
    lower = text.lower()

    opener = any(re.search(pat, lower) for pat in _GENERIC_OPENERS)
    cliches = [c for c in _CLICHES if c in lower]
    ai_tells = [t for t in _AI_TELLS if t in lower]
    ratio = _bullet_ratio(text)

    score = 0.0
    if opener:
        score += _OPENER_WEIGHT
    score += min(len(cliches), _MATCH_CAP) * _CLICHE_WEIGHT
    score += min(len(ai_tells), _MATCH_CAP) * _AI_TELL_WEIGHT
    if ratio > _BULLET_RATIO_TRIGGER:
        score += _BULLET_WEIGHT
    score = min(score, 1.0)

    return GenericityReport(
        score=round(score, 3),
        is_generic=score >= threshold,
        generic_opener=opener,
        cliches=cliches,
        ai_tells=ai_tells,
        bullet_ratio=round(ratio, 3),
    )
