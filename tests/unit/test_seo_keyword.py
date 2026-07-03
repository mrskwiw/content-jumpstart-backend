"""Unit tests for seo_keyword module.

Tests cover:
- KeywordStrategy methods (lines 71-81)
"""

import pytest

from src.models.seo_keyword import (
    SEOKeyword,
    KeywordIntent,
    KeywordDifficulty,
    KeywordStrategy,
)


@pytest.fixture
def sample_keywords():
    """Create sample keywords for testing."""
    return {
        "primary": [
            SEOKeyword(
                keyword="content marketing",
                search_volume=1000,
                difficulty=KeywordDifficulty.MEDIUM,
                intent=KeywordIntent.INFORMATIONAL,
                priority=1,
            ),
            SEOKeyword(
                keyword="social media strategy",
                search_volume=800,
                difficulty=KeywordDifficulty.MEDIUM,
                intent=KeywordIntent.COMMERCIAL,
                priority=2,
            ),
        ],
        "secondary": [
            SEOKeyword(
                keyword="linkedin tips",
                search_volume=500,
                difficulty=KeywordDifficulty.EASY,
                intent=KeywordIntent.INFORMATIONAL,
                priority=3,
            ),
            SEOKeyword(
                keyword="buy marketing tools",
                search_volume=200,
                difficulty=KeywordDifficulty.HARD,
                intent=KeywordIntent.TRANSACTIONAL,
                priority=4,
            ),
        ],
        "longtail": [
            SEOKeyword(
                keyword="how to create content calendar",
                search_volume=100,
                difficulty=KeywordDifficulty.EASY,
                intent=KeywordIntent.INFORMATIONAL,
                priority=5,
            ),
            SEOKeyword(
                keyword="best content marketing software",
                search_volume=150,
                difficulty=KeywordDifficulty.HARD,
                intent=KeywordIntent.NAVIGATIONAL,
                priority=3,
            ),
        ],
    }


@pytest.fixture
def keyword_strategy(sample_keywords):
    """Create keyword strategy with all keyword types."""
    return KeywordStrategy(
        primary_keywords=sample_keywords["primary"],
        secondary_keywords=sample_keywords["secondary"],
        longtail_keywords=sample_keywords["longtail"],
    )


class TestKeywordStrategyMethods:
    """Tests for KeywordStrategy methods (lines 71-81)."""

    def test_get_all_keywords(self, keyword_strategy):
        """Test get_all_keywords returns all keywords (line 73)."""
        all_keywords = keyword_strategy.get_all_keywords()

        assert len(all_keywords) == 6
        # Check all types are included
        keywords = [kw.keyword for kw in all_keywords]
        assert "content marketing" in keywords
        assert "linkedin tips" in keywords
        assert "how to create content calendar" in keywords

    def test_get_keywords_by_intent_informational(self, keyword_strategy):
        """Test get_keywords_by_intent filters correctly (line 77)."""
        informational = keyword_strategy.get_keywords_by_intent(KeywordIntent.INFORMATIONAL)

        assert len(informational) == 3
        for kw in informational:
            assert kw.intent == KeywordIntent.INFORMATIONAL

    def test_get_keywords_by_intent_commercial(self, keyword_strategy):
        """Test get_keywords_by_intent for commercial intent."""
        commercial = keyword_strategy.get_keywords_by_intent(KeywordIntent.COMMERCIAL)

        assert len(commercial) == 1
        assert commercial[0].keyword == "social media strategy"

    def test_get_keywords_by_intent_transactional(self, keyword_strategy):
        """Test get_keywords_by_intent for transactional intent."""
        transactional = keyword_strategy.get_keywords_by_intent(KeywordIntent.TRANSACTIONAL)

        assert len(transactional) == 1
        assert transactional[0].keyword == "buy marketing tools"

    def test_get_keywords_by_intent_empty(self, keyword_strategy):
        """Test get_keywords_by_intent returns empty for no matches."""
        # Create strategy with no commercial keywords
        strategy = KeywordStrategy(
            primary_keywords=[
                SEOKeyword(
                    keyword="test",
                    search_volume=100,
                    difficulty=KeywordDifficulty.EASY,
                    intent=KeywordIntent.INFORMATIONAL,
                )
            ],
            secondary_keywords=[],
            longtail_keywords=[],
        )

        commercial = strategy.get_keywords_by_intent(KeywordIntent.COMMERCIAL)
        assert len(commercial) == 0

    def test_get_keywords_by_priority_default(self, keyword_strategy):
        """Test get_keywords_by_priority with default max (line 81)."""
        high_priority = keyword_strategy.get_keywords_by_priority()

        # Priority <= 3 should include 4 keywords
        assert len(high_priority) == 4
        for kw in high_priority:
            assert kw.priority <= 3

    def test_get_keywords_by_priority_custom(self, keyword_strategy):
        """Test get_keywords_by_priority with custom max."""
        top_priority = keyword_strategy.get_keywords_by_priority(max_priority=2)

        assert len(top_priority) == 2
        for kw in top_priority:
            assert kw.priority <= 2

    def test_get_keywords_by_priority_strict(self, keyword_strategy):
        """Test get_keywords_by_priority with strict max."""
        top_only = keyword_strategy.get_keywords_by_priority(max_priority=1)

        assert len(top_only) == 1
        assert top_only[0].priority == 1


class TestSEOKeywordModel:
    """Tests for SEOKeyword model."""

    def test_seo_keyword_defaults(self):
        """Test SEOKeyword default values."""
        keyword = SEOKeyword(
            keyword="test keyword",
            search_volume=100,
            intent=KeywordIntent.INFORMATIONAL,
        )

        assert keyword.difficulty == KeywordDifficulty.MEDIUM  # Default
        assert keyword.priority == 1  # Default
        assert keyword.notes is None
        assert keyword.related_keywords == []

    def test_seo_keyword_with_all_fields(self):
        """Test SEOKeyword with all fields populated."""
        keyword = SEOKeyword(
            keyword="comprehensive test",
            search_volume=500,
            difficulty=KeywordDifficulty.HARD,
            intent=KeywordIntent.COMMERCIAL,
            priority=1,
            notes="Important keyword",
            related_keywords=["related1", "related2"],
        )

        assert keyword.keyword == "comprehensive test"
        assert keyword.intent == KeywordIntent.COMMERCIAL
        assert keyword.difficulty == KeywordDifficulty.HARD
        assert keyword.priority == 1
        assert keyword.notes == "Important keyword"
        assert len(keyword.related_keywords) == 2


class TestKeywordIntent:
    """Tests for KeywordIntent enum."""

    def test_intent_values(self):
        """Test all intent values."""
        assert KeywordIntent.INFORMATIONAL.value == "informational"
        assert KeywordIntent.NAVIGATIONAL.value == "navigational"
        assert KeywordIntent.COMMERCIAL.value == "commercial"
        assert KeywordIntent.TRANSACTIONAL.value == "transactional"
