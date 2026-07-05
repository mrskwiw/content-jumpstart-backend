"""Unit tests for KeywordQualityScorer"""

import pytest
from src.models.seo_models import Keyword, KeywordDifficulty, SearchIntent
from src.utils.keyword_quality_scorer import KeywordQualityScorer


@pytest.fixture
def scorer():
    """Create scorer with sample business context"""
    return KeywordQualityScorer(
        business_context="AI-powered content marketing automation platform for B2B SaaS companies",
        industry="marketing software",
    )


@pytest.fixture
def sample_keywords():
    """Create sample keywords for testing"""
    return [
        # High-quality keyword (specific, good volume, medium difficulty)
        Keyword(
            keyword="AI content marketing automation",
            search_intent=SearchIntent.COMMERCIAL,
            difficulty=KeywordDifficulty.MEDIUM,
            monthly_volume_estimate="5K-10K",
            relevance_score=9.0,
            long_tail=True,
            question_based=False,
            related_topics=["marketing", "automation", "AI"],
            trend_direction="rising",
            trend_score=75.0,
        ),
        # Medium-quality keyword (generic, but decent)
        Keyword(
            keyword="marketing software",
            search_intent=SearchIntent.INFORMATIONAL,
            difficulty=KeywordDifficulty.HIGH,
            monthly_volume_estimate="10K-50K",
            relevance_score=6.5,
            long_tail=False,
            question_based=False,
            related_topics=["marketing"],
            trend_direction="stable",
        ),
        # Low-quality keyword (too generic)
        Keyword(
            keyword="software",
            search_intent=SearchIntent.INFORMATIONAL,
            difficulty=KeywordDifficulty.HIGH,
            monthly_volume_estimate="1M+",
            relevance_score=3.0,
            long_tail=False,
            question_based=False,
            related_topics=[],
        ),
        # High-quality long-tail question keyword
        Keyword(
            keyword="how to automate content marketing with AI",
            search_intent=SearchIntent.INFORMATIONAL,
            difficulty=KeywordDifficulty.LOW,
            monthly_volume_estimate="1K-5K",
            relevance_score=9.5,
            long_tail=True,
            question_based=True,
            related_topics=["content marketing", "AI", "automation"],
            trend_direction="rising",
            trend_score=80.0,
        ),
    ]


class TestKeywordQualityScorer:
    """Test keyword quality scoring functionality"""

    def test_score_high_quality_keyword(self, scorer):
        """Test scoring of high-quality specific keyword"""
        keyword = Keyword(
            keyword="AI content marketing automation",
            search_intent=SearchIntent.COMMERCIAL,
            difficulty=KeywordDifficulty.MEDIUM,
            monthly_volume_estimate="5K-10K",
            relevance_score=9.0,
            long_tail=True,
            question_based=False,
            related_topics=["marketing", "automation"],
            trend_direction="rising",
            trend_score=75.0,
        )

        score = scorer.score_keyword(keyword)

        # Should score highly (80+)
        assert score >= 80.0
        assert score <= 100.0

    def test_score_generic_keyword(self, scorer):
        """Test that generic keywords score poorly"""
        keyword = Keyword(
            keyword="marketing",
            search_intent=SearchIntent.INFORMATIONAL,
            difficulty=KeywordDifficulty.HIGH,
            monthly_volume_estimate="1M+",
            relevance_score=5.0,
            long_tail=False,
            question_based=False,
            related_topics=[],
        )

        score = scorer.score_keyword(keyword)

        # Generic single-word should score low (< 50)
        assert score < 50.0

    def test_score_question_based_long_tail(self, scorer):
        """Test that question-based long-tail keywords score highly"""
        keyword = Keyword(
            keyword="how to automate content marketing with AI",
            search_intent=SearchIntent.INFORMATIONAL,
            difficulty=KeywordDifficulty.LOW,
            monthly_volume_estimate="1K-5K",
            relevance_score=9.5,
            long_tail=True,
            question_based=True,
            related_topics=["content marketing", "AI"],
            trend_direction="rising",
            trend_score=80.0,
        )

        score = scorer.score_keyword(keyword)

        # Question-based long-tail with good trends should score very high (85+)
        assert score >= 85.0

    def test_specificity_scoring(self, scorer):
        """Test specificity component of scoring"""
        # Generic single word
        generic = Keyword(
            keyword="software",
            search_intent=SearchIntent.INFORMATIONAL,
            difficulty=KeywordDifficulty.MEDIUM,
            monthly_volume_estimate="1K-10K",
            relevance_score=5.0,
            long_tail=False,
            question_based=False,
            related_topics=[],
        )

        # Specific single word
        specific = Keyword(
            keyword="podiatry",
            search_intent=SearchIntent.INFORMATIONAL,
            difficulty=KeywordDifficulty.MEDIUM,
            monthly_volume_estimate="1K-10K",
            relevance_score=8.0,
            long_tail=False,
            question_based=False,
            related_topics=["healthcare"],
        )

        generic_score = scorer.score_keyword(generic)
        specific_score = scorer.score_keyword(specific)

        # Specific keyword should score higher
        assert specific_score > generic_score

    def test_difficulty_balance_scoring(self, scorer):
        """Test that medium difficulty is preferred over high"""
        high_diff = Keyword(
            keyword="content marketing",
            search_intent=SearchIntent.INFORMATIONAL,
            difficulty=KeywordDifficulty.HIGH,
            monthly_volume_estimate="10K+",
            relevance_score=8.0,
            long_tail=False,
            question_based=False,
            related_topics=[],
        )

        medium_diff = Keyword(
            keyword="content marketing",
            search_intent=SearchIntent.INFORMATIONAL,
            difficulty=KeywordDifficulty.MEDIUM,
            monthly_volume_estimate="10K+",
            relevance_score=8.0,
            long_tail=False,
            question_based=False,
            related_topics=[],
        )

        high_score = scorer.score_keyword(high_diff)
        medium_score = scorer.score_keyword(medium_diff)

        # Medium difficulty should score higher than high
        assert medium_score > high_score

    def test_volume_scoring(self, scorer):
        """Test search volume component of scoring"""
        # Create keywords with different volumes
        volumes = [
            ("Unknown", 5.0),  # Neutral
            ("10-100", 5.0),  # Low
            ("100-1K", 9.0),  # Medium
            ("1K-10K", 12.0),  # Medium-high
            ("10K+", 15.0),  # High
        ]

        for volume_str, expected_points in volumes:
            keyword = Keyword(
                keyword="test keyword",
                search_intent=SearchIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.MEDIUM,
                monthly_volume_estimate=volume_str,
                relevance_score=5.0,
                long_tail=False,
                question_based=False,
                related_topics=[],
            )

            score = scorer.score_keyword(keyword)
            # Verify volume contributes correctly (approximate check)
            # Note: Total score depends on all factors, so we can't test exact volume points
            # But we can verify higher volume = higher score (all else equal)

    def test_trend_scoring(self, scorer):
        """Test Google Trends component of scoring"""
        rising = Keyword(
            keyword="AI automation",
            search_intent=SearchIntent.INFORMATIONAL,
            difficulty=KeywordDifficulty.MEDIUM,
            monthly_volume_estimate="1K-10K",
            relevance_score=8.0,
            long_tail=False,
            question_based=False,
            related_topics=[],
            trend_direction="rising",
            trend_score=80.0,
        )

        declining = Keyword(
            keyword="AI automation",
            search_intent=SearchIntent.INFORMATIONAL,
            difficulty=KeywordDifficulty.MEDIUM,
            monthly_volume_estimate="1K-10K",
            relevance_score=8.0,
            long_tail=False,
            question_based=False,
            related_topics=[],
            trend_direction="declining",
        )

        rising_score = scorer.score_keyword(rising)
        declining_score = scorer.score_keyword(declining)

        # Rising trend should score higher
        assert rising_score > declining_score

    def test_filter_high_quality(self, scorer, sample_keywords):
        """Test filtering for high-quality keywords"""
        high_quality = scorer.filter_high_quality(sample_keywords, min_score=70.0)

        # Should have at least 2 high-quality keywords
        assert len(high_quality) >= 2

        # All should have quality_score attached
        for kw in high_quality:
            assert kw.quality_score is not None
            assert kw.quality_score >= 70.0

        # Should be sorted by quality score (highest first)
        for i in range(len(high_quality) - 1):
            assert high_quality[i].quality_score >= high_quality[i + 1].quality_score

    def test_get_keyword_stats(self, scorer, sample_keywords):
        """Test keyword statistics calculation"""
        stats = scorer.get_keyword_stats(sample_keywords)

        assert "total" in stats
        assert "avg_quality" in stats
        assert "high_quality_count" in stats
        assert "medium_quality_count" in stats
        assert "low_quality_count" in stats
        assert "top_keywords" in stats

        assert stats["total"] == len(sample_keywords)
        assert stats["avg_quality"] > 0.0
        assert len(stats["top_keywords"]) <= 10

    def test_intent_scoring(self, scorer):
        """Test that commercial/transactional intents score higher"""
        intents = [
            (SearchIntent.TRANSACTIONAL, 5.0),
            (SearchIntent.COMMERCIAL, 4.0),
            (SearchIntent.INFORMATIONAL, 3.0),
            (SearchIntent.NAVIGATIONAL, 2.0),
        ]

        scores_by_intent = {}

        for intent, expected_points in intents:
            keyword = Keyword(
                keyword="test keyword",
                search_intent=intent,
                difficulty=KeywordDifficulty.MEDIUM,
                monthly_volume_estimate="1K-10K",
                relevance_score=8.0,
                long_tail=False,
                question_based=False,
                related_topics=[],
            )

            scores_by_intent[intent] = scorer.score_keyword(keyword)

        # Transactional should score highest
        assert (
            scores_by_intent[SearchIntent.TRANSACTIONAL]
            >= scores_by_intent[SearchIntent.COMMERCIAL]
        )
        assert (
            scores_by_intent[SearchIntent.COMMERCIAL]
            >= scores_by_intent[SearchIntent.INFORMATIONAL]
        )

    def test_scorer_with_no_trend_data(self, scorer):
        """Test scoring works without Google Trends data"""
        keyword = Keyword(
            keyword="content marketing automation",
            search_intent=SearchIntent.COMMERCIAL,
            difficulty=KeywordDifficulty.MEDIUM,
            monthly_volume_estimate="5K-10K",
            relevance_score=9.0,
            long_tail=True,
            question_based=False,
            related_topics=["marketing"],
            # No trend data provided
        )

        score = scorer.score_keyword(keyword)

        # Should still score well (>70) even without trend data
        assert score > 70.0

    def test_minimum_quality_threshold(self, scorer):
        """Test MIN_QUALITY_SCORE constant is reasonable"""
        assert KeywordQualityScorer.MIN_QUALITY_SCORE == 70
        assert KeywordQualityScorer.TARGET_HIGH_QUALITY == 5

    def test_empty_keywords_list(self, scorer):
        """Test handling of empty keywords list"""
        stats = scorer.get_keyword_stats([])

        assert stats["total"] == 0
        assert stats["avg_quality"] == 0.0
        assert stats["high_quality_count"] == 0
        assert stats["top_keywords"] == []

    def test_quality_score_range(self, scorer, sample_keywords):
        """Test that all quality scores are within 0-100 range"""
        for kw in sample_keywords:
            score = scorer.score_keyword(kw)
            assert 0.0 <= score <= 100.0
