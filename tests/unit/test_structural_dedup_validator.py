"""Unit tests for src.validators.structural_dedup_validator."""

import pytest
from unittest.mock import MagicMock

from src.validators.structural_dedup_validator import (
    _shingle,
    _jaccard,
    _extract_matching_sentences,
    StructuralDedupValidator,
)


def _post(content: str):
    p = MagicMock()
    p.content = content
    return p


class TestShingle:
    def test_returns_trigrams(self):
        result = _shingle("hello world foo bar", k=3)
        assert "hello world foo" in result

    def test_short_text_returns_words(self):
        result = _shingle("hello world", k=3)
        assert "hello" in result or "world" in result

    def test_case_insensitive(self):
        result = _shingle("Hello World", k=3)
        assert all(s == s.lower() for s in result)

    def test_empty_text(self):
        result = _shingle("", k=3)
        assert result == []


class TestJaccard:
    def test_identical_sets_is_one(self):
        a = ["foo", "bar"]
        assert _jaccard(a, a) == pytest.approx(1.0)

    def test_disjoint_sets_is_zero(self):
        assert _jaccard(["a", "b"], ["c", "d"]) == pytest.approx(0.0)

    def test_partial_overlap(self):
        sim = _jaccard(["a", "b", "c"], ["b", "c", "d"])
        assert 0 < sim < 1

    def test_both_empty_is_one(self):
        assert _jaccard([], []) == pytest.approx(1.0)

    def test_one_empty_is_zero(self):
        assert _jaccard(["a"], []) == pytest.approx(0.0)
        assert _jaccard([], ["b"]) == pytest.approx(0.0)


class TestExtractMatchingSentences:
    def test_client_told_us_matches(self):
        result = _extract_matching_sentences(
            "One of our clients told us they struggled with pricing."
        )
        assert len(result) == 1
        assert "scaffold" in result[0][1]

    def test_client_mentioned_matches(self):
        result = _extract_matching_sentences("One of my patients mentioned their anxiety improved.")
        assert len(result) == 1

    def test_no_match_returns_empty(self):
        result = _extract_matching_sentences("Here are five tips for better sleep.")
        assert result == []

    def test_multiple_sentences_first_match_wins(self):
        content = (
            "One of our clients told us they had issues. "
            "One of my customers asked about pricing. "
            "No match here."
        )
        result = _extract_matching_sentences(content)
        # Each matching sentence contributes one hit
        assert len(result) >= 2

    def test_future_prediction_matches(self):
        result = _extract_matching_sentences("Years from now, AI will replace most manual tasks.")
        assert len(result) == 1


class TestStructuralDedupValidator:
    def test_no_issues_when_no_scaffolds(self):
        posts = [
            _post("Here are five quick tips to improve your workflow."),
            _post("The most important thing in marketing is consistency."),
        ]
        result = StructuralDedupValidator().validate(posts)
        assert result["passed"] is True
        assert result["issues"] == []

    def test_flags_similar_scaffold_across_posts(self):
        posts = [
            _post("One of our clients told us they had trouble with onboarding."),
            _post("One of our clients told us they had trouble with scaling."),
        ]
        result = StructuralDedupValidator().validate(posts)
        assert result["passed"] is False
        assert len(result["issues"]) >= 1
        assert "1" in result["issues"][0]  # references post 1

    def test_different_scaffold_types_not_flagged(self):
        # One uses "told us", another uses "future prediction" — different labels
        posts = [
            _post("One of our clients told us about their challenges."),
            _post("Years from now, automation will replace these tasks."),
        ]
        result = StructuralDedupValidator().validate(posts)
        assert result["passed"] is True

    def test_same_scaffold_in_same_post_not_flagged(self):
        # Internal repetition within one post — not cross-post
        content = (
            "One of our clients told us they had issues. "
            "One of our clients told us they saw results."
        )
        posts = [_post(content)]
        result = StructuralDedupValidator().validate(posts)
        # Single post can't have cross-post duplicate
        assert result["passed"] is True

    def test_empty_posts_returns_passed(self):
        result = StructuralDedupValidator().validate([])
        assert result["passed"] is True
        assert result["issues"] == []

    def test_returns_scaffold_hits(self):
        posts = [_post("One of our clients told us about pricing.")]
        result = StructuralDedupValidator().validate(posts)
        assert len(result["scaffold_hits"]) == 1

    def test_returns_posts_flagged_count(self):
        posts = [
            _post("One of our clients told us they needed help."),
            _post("One of our clients told us they were struggling."),
        ]
        result = StructuralDedupValidator().validate(posts)
        assert "posts_flagged" in result
        assert isinstance(result["posts_flagged"], int)
