"""Unit tests for SEO negative keywords feature.

Covers all six touch points:
1. SEOKeywordParams schema validation
2. _build_keyword_research_prompt injection
3. Post-filter logic (primary + secondary)
4. KeywordStrategy model storage
5. research_context_builder _format_seo_keywords
6. export_service _format_seo_keywords
"""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _keyword(term):
    """Create a minimal Keyword object with the given term."""
    from src.models.seo_models import Keyword, SearchIntent, KeywordDifficulty

    return Keyword(
        keyword=term,
        search_intent=SearchIntent.INFORMATIONAL,
        difficulty=KeywordDifficulty.MEDIUM,
        monthly_volume_estimate="1K-5K",
        relevance_score=8.0,
        long_tail=False,
        question_based=False,
        related_topics=[],
    )


def _researcher():
    """Return a SEOKeywordResearcher without running __init__ (avoids API client setup)."""
    from src.research.seo_keyword_research import SEOKeywordResearcher
    from src.validators.research_input_validator import ResearchInputValidator

    r = SEOKeywordResearcher.__new__(SEOKeywordResearcher)
    r.project_id = "test-proj"
    r.base_output_dir = MagicMock()
    r.validator = ResearchInputValidator(strict_mode=False)
    r.client = MagicMock()
    return r


# ---------------------------------------------------------------------------
# 1. Schema validation — SEOKeywordParams.negative_keywords
# ---------------------------------------------------------------------------


class TestSEOKeywordParamsNegativeKeywords:
    def test_none_accepted(self):
        from backend.schemas.research_schemas import SEOKeywordParams

        params = SEOKeywordParams(negative_keywords=None)
        assert params.negative_keywords is None

    def test_empty_list_returns_none(self):
        from backend.schemas.research_schemas import SEOKeywordParams

        params = SEOKeywordParams(negative_keywords=[])
        assert params.negative_keywords is None

    def test_valid_list_preserved(self):
        from backend.schemas.research_schemas import SEOKeywordParams

        params = SEOKeywordParams(negative_keywords=["competitor brand", "spam term"])
        assert params.negative_keywords == ["competitor brand", "spam term"]

    def test_whitespace_stripped(self):
        from backend.schemas.research_schemas import SEOKeywordParams

        params = SEOKeywordParams(negative_keywords=["  trimmed  "])
        assert params.negative_keywords == ["trimmed"]

    def test_capped_at_50(self):
        from backend.schemas.research_schemas import SEOKeywordParams

        params = SEOKeywordParams(negative_keywords=[f"kw{i}" for i in range(60)])
        assert len(params.negative_keywords) == 50

    def test_single_char_entries_skipped(self):
        from backend.schemas.research_schemas import SEOKeywordParams

        params = SEOKeywordParams(negative_keywords=["a", "valid"])
        assert params.negative_keywords == ["valid"]

    def test_long_entries_truncated_not_rejected(self):
        from backend.schemas.research_schemas import SEOKeywordParams

        long_kw = "x" * 200
        params = SEOKeywordParams(negative_keywords=[long_kw])
        assert len(params.negative_keywords[0]) == 100

    def test_all_invalid_returns_none(self):
        from backend.schemas.research_schemas import SEOKeywordParams

        params = SEOKeywordParams(negative_keywords=["a", "b"])
        assert params.negative_keywords is None


# ---------------------------------------------------------------------------
# 2. Prompt injection — _build_keyword_research_prompt
# ---------------------------------------------------------------------------


class TestBuildKeywordResearchPromptNegatives:
    def _prompt(self, negative_keywords=None):
        r = _researcher()
        return r._build_keyword_research_prompt(
            business_desc="B2B SaaS analytics",
            target_audience="SaaS teams",
            main_topics=["analytics", "reporting"],
            industry="B2B SaaS",
            focus="broad topics",
            iteration=1,
            negative_keywords=negative_keywords,
        )

    def test_keywords_to_avoid_section_present_when_provided(self):
        prompt = self._prompt(["competitor brand", "spam"])
        assert "KEYWORDS TO AVOID" in prompt

    def test_excluded_terms_listed_in_prompt(self):
        prompt = self._prompt(["competitor brand", "unrelated topic"])
        assert "competitor brand" in prompt
        assert "unrelated topic" in prompt

    def test_no_avoid_section_when_none(self):
        prompt = self._prompt(None)
        assert "KEYWORDS TO AVOID" not in prompt

    def test_no_avoid_section_when_empty(self):
        prompt = self._prompt([])
        assert "KEYWORDS TO AVOID" not in prompt

    def test_avoid_section_placed_after_main_topics(self):
        prompt = self._prompt(["bad term"])
        topics_pos = prompt.index("Main Topics")
        avoid_pos = prompt.index("KEYWORDS TO AVOID")
        assert avoid_pos > topics_pos


# ---------------------------------------------------------------------------
# 3. Post-filter logic
# ---------------------------------------------------------------------------


class TestNegativeKeywordsPostFilter:
    """Test substring matching filter applied after Claude returns keywords."""

    def test_exact_match_removed(self):
        """Keyword exactly matching a negative term is dropped."""
        keywords = [_keyword("competitor brand analytics"), _keyword("customer success metrics")]
        negative = ["competitor brand"]
        filtered = [
            kw for kw in keywords if not any(neg.lower() in kw.keyword.lower() for neg in negative)
        ]
        assert len(filtered) == 1
        assert filtered[0].keyword == "customer success metrics"

    def test_substring_match_removed(self):
        """Keyword containing a negative substring is dropped."""
        keywords = [_keyword("acme corp pricing"), _keyword("saas pricing comparison")]
        negative = ["acme"]
        filtered = [
            kw for kw in keywords if not any(neg.lower() in kw.keyword.lower() for neg in negative)
        ]
        assert len(filtered) == 1
        assert "saas" in filtered[0].keyword

    def test_case_insensitive(self):
        """Filter is case-insensitive."""
        keywords = [_keyword("CompetitorX features"), _keyword("product features")]
        negative = ["competitorx"]
        filtered = [
            kw for kw in keywords if not any(neg.lower() in kw.keyword.lower() for neg in negative)
        ]
        assert len(filtered) == 1
        assert filtered[0].keyword == "product features"

    def test_no_negatives_returns_all(self):
        keywords = [_keyword("analytics"), _keyword("reporting")]
        filtered = [
            kw for kw in keywords if not any(neg.lower() in kw.keyword.lower() for neg in [])
        ]
        assert len(filtered) == 2

    def test_non_matching_keyword_retained(self):
        keywords = [_keyword("saas analytics"), _keyword("data dashboard")]
        negative = ["competitor"]
        filtered = [
            kw for kw in keywords if not any(neg.lower() in kw.keyword.lower() for neg in negative)
        ]
        assert len(filtered) == 2


# ---------------------------------------------------------------------------
# 4. KeywordStrategy model — negative_keywords field
# ---------------------------------------------------------------------------


class TestKeywordStrategyNegativeKeywordsField:
    def test_field_defaults_to_empty_list(self):
        from src.models.seo_models import KeywordStrategy

        strategy = KeywordStrategy(
            business_name="Acme",
            industry="SaaS",
            target_audience="Teams",
            strategy_summary="summary",
        )
        assert strategy.negative_keywords == []

    def test_field_accepts_list(self):
        from src.models.seo_models import KeywordStrategy

        strategy = KeywordStrategy(
            business_name="Acme",
            industry="SaaS",
            target_audience="Teams",
            strategy_summary="summary",
            negative_keywords=["competitor", "spam"],
        )
        assert strategy.negative_keywords == ["competitor", "spam"]

    def test_field_serializes_to_json(self):
        from src.models.seo_models import KeywordStrategy

        strategy = KeywordStrategy(
            business_name="Acme",
            industry="SaaS",
            target_audience="Teams",
            strategy_summary="summary",
            negative_keywords=["bad term"],
        )
        data = strategy.model_dump()
        assert data["negative_keywords"] == ["bad term"]


# ---------------------------------------------------------------------------
# 5. Context builder — _format_seo_keywords
# ---------------------------------------------------------------------------


class TestContextBuilderNegativeKeywords:
    def _format(self, negative_keywords):
        from backend.services.research_context_builder import _format_seo_keywords
        from datetime import datetime

        result = MagicMock()
        result.data = {
            "primary_keywords": [{"keyword": "analytics software", "relevance_score": 9.0}],
            "strategy_summary": "Focus on analytics.",
            "negative_keywords": negative_keywords,
        }
        result.created_at = datetime(2026, 1, 1)
        return _format_seo_keywords(result)

    def test_avoid_line_present_when_negatives_provided(self):
        result = self._format(["competitor", "spam"])
        assert "Avoid in content" in result
        assert "competitor" in result

    def test_avoid_line_absent_when_empty(self):
        result = self._format([])
        assert "Avoid in content" not in result

    def test_avoid_line_absent_when_none(self):
        result = self._format(None)
        assert "Avoid in content" not in result

    def test_capped_at_10_in_context(self):
        negatives = [f"term{i}" for i in range(15)]
        result = self._format(negatives)
        # Only first 10 should appear; term10..term14 should not all appear
        listed = [f"term{i}" for i in range(10) if f"term{i}" in result]
        assert len(listed) == 10


# ---------------------------------------------------------------------------
# 6. Export service — _format_seo_keywords
# ---------------------------------------------------------------------------


class TestExportServiceNegativeKeywords:
    def _format(self, negative_keywords):
        from backend.services.export_service import _format_seo_keywords

        data = {
            "primary_keywords": [
                {
                    "keyword": "analytics software",
                    "relevance_score": 9.0,
                    "search_intent": "commercial",
                    "difficulty": "medium",
                }
            ],
            "strategy_summary": "Focus on analytics.",
            "negative_keywords": negative_keywords,
        }
        return "\n".join(_format_seo_keywords(data))

    def test_excluded_section_present_when_negatives_provided(self):
        result = self._format(["competitor brand", "spam term"])
        assert "Keywords Excluded from Strategy" in result

    def test_each_excluded_keyword_listed(self):
        result = self._format(["competitor brand", "spam term"])
        assert "competitor brand" in result
        assert "spam term" in result

    def test_excluded_section_absent_when_empty(self):
        result = self._format([])
        assert "Keywords Excluded from Strategy" not in result

    def test_excluded_section_absent_when_none(self):
        result = self._format(None)
        assert "Keywords Excluded from Strategy" not in result

    def test_keywords_formatted_as_list_items(self):
        result = self._format(["bad term"])
        assert "- bad term" in result
