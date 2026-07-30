"""BRAND-CORE-02 — generic-AI signal detection."""

from src.analysis.genericity import analyze_genericity

_GENERIC = (
    "In today's fast-paced digital world, businesses must leverage cutting-edge tools.\n"
    "- Unlock synergy\n"
    "- Move the needle\n"
    "- Supercharge growth\n"
    "In conclusion, it's important to note that we should delve into this."
)

_SPECIFIC = (
    "We shipped the wrong invoice to 40 customers last Tuesday. Here's the exact "
    "database query that caused it, and the one-line fix that stopped it. If you run "
    "a billing system, check whether your currency column is nullable — ours was, and "
    "that's all it took."
)


def test_generic_text_scores_high_and_flags():
    r = analyze_genericity(_GENERIC)
    assert r.is_generic is True
    assert r.score >= 0.4
    assert r.generic_opener is True
    assert "leverage" in r.cliches and "supercharge" in r.cliches
    assert "in conclusion" in r.ai_tells
    assert r.bullet_ratio > 0.5


def test_specific_text_scores_low():
    r = analyze_genericity(_SPECIFIC)
    assert r.is_generic is False
    assert r.score < 0.4
    assert r.generic_opener is False
    assert r.cliches == []


def test_generic_opener_alone_below_threshold():
    r = analyze_genericity("When it comes to marketing, consistency wins.")
    assert r.generic_opener is True
    assert r.score == 0.35  # opener weight only
    assert r.is_generic is False  # one signal isn't enough at the default threshold


def test_cliches_accumulate_but_capped():
    text = "leverage unlock synergy elevate robust seamless"  # 6 clichés
    r = analyze_genericity(text)
    # capped at 3 * 0.10 = 0.30 (diminishing returns)
    assert r.score == 0.3
    assert len(r.cliches) == 6  # all reported, but score-capped


def test_bullet_heavy_structure_flagged():
    text = "- point one\n- point two\n- point three\none prose line"
    r = analyze_genericity(text)
    assert r.bullet_ratio == 0.75


def test_empty_text_is_not_generic():
    r = analyze_genericity("")
    assert r.score == 0.0 and r.is_generic is False


def test_threshold_is_tunable():
    text = "When it comes to marketing, consistency wins."  # score 0.35
    assert analyze_genericity(text, threshold=0.3).is_generic is True
    assert analyze_genericity(text, threshold=0.5).is_generic is False
