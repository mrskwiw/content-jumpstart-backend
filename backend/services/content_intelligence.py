"""Content-intelligence facade (BRAND-CORE-02 + PREDICT-01).

One call over the pure content-quality signals for a generated post, producing
the single decision the QA pass and the operator UI act on: *should this post be
regenerated toward a point of view?* Ties the genericity detector and the
pre-publish predictor together with actionable flags.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.services.genericity import analyze_genericity
from backend.services.predict import predict_engagement

_REGENERATE_BELOW = 45.0  # predicted-score floor
_GENERIC_THRESHOLD = 0.4


@dataclass
class PostAssessment:
    predicted_score: float
    genericity_score: float
    is_generic: bool
    should_regenerate: bool
    reasons: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


def assess_post(
    text: str,
    *,
    platform: str = "linkedin",
    regenerate_below: float = _REGENERATE_BELOW,
    generic_threshold: float = _GENERIC_THRESHOLD,
) -> PostAssessment:
    """Assess a post; ``should_regenerate`` is the actionable QA output."""
    generic = analyze_genericity(text, threshold=generic_threshold)
    pred = predict_engagement(text, platform=platform)

    flags: list[str] = []
    if generic.generic_opener:
        flags.append("generic_opener")
    if generic.cliches:
        flags.append(f"cliches:{len(generic.cliches)}")
    if generic.ai_tells:
        flags.append(f"ai_tells:{len(generic.ai_tells)}")
    if generic.bullet_ratio > 0.5:
        flags.append("bullet_heavy")

    reasons: list[str] = []
    if generic.is_generic:
        reasons.append("reads as generic AI — likely reach-penalized on LinkedIn")
    if pred.score < regenerate_below:
        reasons.append(f"predicted engagement {pred.score} below {regenerate_below}")

    return PostAssessment(
        predicted_score=pred.score,
        genericity_score=generic.score,
        is_generic=generic.is_generic,
        should_regenerate=bool(reasons),
        reasons=reasons,
        flags=flags,
    )
