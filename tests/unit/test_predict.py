"""PREDICT-01 — pre-publish engagement prediction."""

from backend.services.predict import predict_engagement

# Strong LinkedIn post: number-led hook, LinkedIn-length (150-300w), question, CTA,
# low genericity.
_STRONG = (
    "3 words killed our onboarding conversion.\n\n"
    "We A/B tested the signup button copy for six weeks across 12,000 visitors, "
    "splitting traffic evenly and letting each variant run until the confidence "
    "interval closed. The version everyone on the team expected to win was the "
    "clever, playful one — the copy we were proud of in the design review. It lost. "
    "Badly. The version that actually won was the boring, literal one that told "
    "people exactly what would happen the moment they clicked: no metaphor, no wink, "
    "just the next step spelled out in plain words. Clarity beat cleverness by 34% on "
    "completed signups, and the gap held for the entire second month once we shipped "
    "it to everyone. The lesson stuck with me: when someone is deciding whether to "
    "trust you with their email, they are not looking to be entertained. They are "
    "looking to be reassured that they understand what happens next.\n\n"
    "What's the most boring change that ever moved your numbers? Tell me in the comments."
)

_WEAK = (
    "In today's fast-paced digital world, businesses must leverage cutting-edge "
    "solutions to unlock synergy and supercharge growth. In conclusion, it is "
    "important to note that we should elevate our robust strategies."
)


def test_strong_post_scores_high():
    r = predict_engagement(_STRONG, platform="linkedin")
    assert r.score >= 75
    assert r.breakdown.get("hook") == 15.0
    assert r.breakdown.get("question") == 10.0
    assert r.breakdown.get("cta") == 10.0
    assert r.breakdown["genericity"] == 0  # not generic


def test_weak_generic_post_scores_low():
    r = predict_engagement(_WEAK, platform="linkedin")
    assert r.score < 40
    assert r.breakdown["genericity"] < 0  # penalized


def test_score_is_clamped_0_100():
    r = predict_engagement(_STRONG)
    assert 0.0 <= r.score <= 100.0


def test_breakdown_always_has_baseline_and_genericity():
    r = predict_engagement("short")
    assert "baseline" in r.breakdown and "genericity" in r.breakdown


def test_platform_length_fit_affects_score():
    body = " ".join(["word"] * 200)  # good for linkedin, too long for twitter
    li = predict_engagement(body, platform="linkedin")
    tw = predict_engagement(body, platform="twitter")
    assert li.breakdown.get("length") == 15.0
    assert tw.breakdown.get("length") == -15.0
    assert li.score > tw.score
