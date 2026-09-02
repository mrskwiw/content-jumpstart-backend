"""Direct unit tests for generator_service's pure helpers (AUDIT-01 T1: the orchestration
core previously had zero direct tests — only router-level HTTP coverage).

Covers the two batch-quality checks that guard a deliverable before it ships:
- _check_batch_consistency: Bug #139 (same source reused) + Bug #143 (contradictory stats).
- _calculate_readability: the Flesch score attached to each post.
"""

from types import SimpleNamespace

from backend.services.generator_service import (
    _calculate_readability,
    _check_batch_consistency,
)


def _post(content: str):
    """A minimal stand-in for a Post — the helper only reads `.content`."""
    return SimpleNamespace(content=content)


# ── _check_batch_consistency ──────────────────────────────────────────────────


def test_no_warnings_for_a_clean_batch():
    posts = [
        _post("Productivity is a habit worth building."),
        _post("Ship small, ship often — momentum compounds."),
    ]
    assert _check_batch_consistency(posts) == []


def test_flags_the_same_source_cited_across_posts_bug_139():
    # "In <Title> by <Author>" — the trigger word is immediately followed by the title, so
    # both posts capture the same book key.
    posts = [
        _post("In Atomic Habits by James Clear, identity beats outcomes."),
        _post("From Atomic Habits by James Clear: small habits compound."),
    ]
    warnings = _check_batch_consistency(posts)
    assert len(warnings) == 1
    assert "atomic habits" in warnings[0].lower()
    assert "[1, 2]" in warnings[0]  # both offending post indices named


def test_does_not_flag_a_source_cited_once():
    posts = [
        _post("In Deep Work by Cal Newport, focus is the new IQ."),
        _post("A totally different post with no citation at all."),
    ]
    assert _check_batch_consistency(posts) == []


def test_flags_contradictory_stats_for_the_same_topic_bug_143():
    posts = [
        _post("Our data shows engagement rate increased by 73% last quarter."),
        _post("Our data shows engagement rate increased by 45% last quarter."),
    ]
    warnings = _check_batch_consistency(posts)
    assert any("contradictory statistics" in w.lower() for w in warnings)
    conflict = next(w for w in warnings if "contradictory" in w.lower())
    assert "73" in conflict and "45" in conflict


def test_same_stat_for_the_same_topic_is_not_a_conflict():
    posts = [
        _post("Our data shows engagement rate increased by 73% last quarter."),
        _post("Reminder: engagement rate increased by 73% last quarter."),
    ]
    # Identical figure for the same topic is consistent, not contradictory.
    assert not any("contradictory" in w.lower() for w in _check_batch_consistency(posts))


def test_empty_batch_is_safe():
    assert _check_batch_consistency([]) == []


# ── _calculate_readability ────────────────────────────────────────────────────


def test_readability_empty_content_is_zero():
    assert _calculate_readability("") == 0.0
    assert _calculate_readability("   ") == 0.0


def test_readability_is_clamped_to_0_100():
    for text in ("The cat sat on the mat.", "Word " * 200, "a", "supercalifragilistic " * 40):
        score = _calculate_readability(text)
        assert 0.0 <= score <= 100.0


def test_readability_short_simple_text_clamps_high():
    # A very short, simple sentence yields a >100 raw Flesch score → clamped to the 100 ceiling.
    assert _calculate_readability("The cat sat on the mat.") == 100.0


def test_readability_returns_a_rounded_float():
    score = _calculate_readability(
        "Generative engine optimization rewards concise, well-structured answers "
        "that machines can extract and cite without ambiguity."
    )
    assert isinstance(score, float)
    assert round(score, 1) == score  # rounded to one decimal
