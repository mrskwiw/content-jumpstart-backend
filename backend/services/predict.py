"""Pre-publish performance prediction (PREDICT-01).

A cheap, deterministic pre-publish score (0-100) estimating a post's relative
engagement *before* spending on real distribution — so operators regenerate weak
posts, not publish-then-learn. This is a transparent heuristic (not a trained
model; the Phase-11 engagement-dataset model is the later upgrade) combining the
signals that correlate with reach: LOW genericity (BRAND-CORE-02 — the LinkedIn
penalty trigger), a specific/number-led hook, a question, a clear CTA, and the
right length for the platform.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.services.genericity import analyze_genericity

# Rough platform sweet-spots (words) for the prose body.
_LENGTH_TARGETS: dict[str, tuple[int, int]] = {
    "linkedin": (150, 300),
    "twitter": (12, 50),
    "facebook": (40, 120),
    "blog": (800, 2000),
    "email": (120, 250),
    "generic": (40, 300),
}

_BASELINE = 50.0
_GENERICITY_PENALTY = 40.0  # full genericity wipes out most of the score
_HOOK_BONUS = 15.0
_QUESTION_BONUS = 10.0
_CTA_BONUS = 10.0
_LENGTH_BONUS = 15.0
_LENGTH_PENALTY = 15.0

_NUMBER_RE = re.compile(r"\d")
_CTA_RE = re.compile(
    r"\b(comment|share|dm|follow|sign up|try|download|book|reply|tell me|what'?s your)\b",
    re.IGNORECASE,
)


@dataclass
class PredictionReport:
    score: float
    breakdown: dict[str, float] = field(default_factory=dict)


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _last_lines(text: str, n: int = 2) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return " ".join(lines[-n:])


def predict_engagement(text: str, *, platform: str = "linkedin") -> PredictionReport:
    """Return a 0-100 predicted-engagement score with a transparent breakdown."""
    breakdown: dict[str, float] = {"baseline": _BASELINE}

    # Genericity penalty (the dominant negative signal).
    generic = analyze_genericity(text)
    breakdown["genericity"] = -round(generic.score * _GENERICITY_PENALTY, 1)

    # Hook: short first line that leads with a number / specific.
    first = _first_line(text)
    if first and len(first.split()) <= 15 and _NUMBER_RE.search(first):
        breakdown["hook"] = _HOOK_BONUS

    # A question anywhere invites replies.
    if "?" in text:
        breakdown["question"] = _QUESTION_BONUS

    # A clear CTA near the end.
    if _CTA_RE.search(_last_lines(text)):
        breakdown["cta"] = _CTA_BONUS

    # Length fit for the platform.
    lo, hi = _LENGTH_TARGETS.get(platform, _LENGTH_TARGETS["generic"])
    words = len(text.split())
    if lo <= words <= hi:
        breakdown["length"] = _LENGTH_BONUS
    elif words < lo // 2 or words > hi * 2:
        breakdown["length"] = -_LENGTH_PENALTY

    score = max(0.0, min(100.0, sum(breakdown.values())))
    return PredictionReport(score=round(score, 1), breakdown=breakdown)
