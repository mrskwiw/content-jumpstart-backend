"""Tests for Keyword Refinement Agent"""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.keyword_refiner import KeywordRefinementAgent
from src.models.seo_keyword import (
    KeywordDifficulty,
    KeywordIntent,
    KeywordStrategy,
    SEOKeyword,
)


@pytest.fixture
def sample_strategy():
    """Create sample keyword strategy"""
    return KeywordStrategy(
        primary_keywords=[
            SEOKeyword(
                keyword="content marketing",
                intent=KeywordIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.HARD,
                priority=1,
                related_keywords=["content strategy", "content creation"],
                notes="Main topic",
            ),
            SEOKeyword(
                keyword="social media content",
                intent=KeywordIntent.COMMERCIAL,
                difficulty=KeywordDifficulty.MEDIUM,
                priority=2,
                related_keywords=["social posts", "social strategy"],
                notes="Secondary focus",
            ),
        ],
        secondary_keywords=[
            SEOKeyword(
                keyword="content calendar",
                intent=KeywordIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.MEDIUM,
                priority=1,
                related_keywords=[],
                notes="Supporting keyword",
            ),
            SEOKeyword(
                keyword="editorial workflow",
                intent=KeywordIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.MEDIUM,
                priority=2,
                related_keywords=[],
            ),
        ],
        longtail_keywords=[
            SEOKeyword(
                keyword="how to create a content calendar",
                intent=KeywordIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.EASY,
                priority=1,
                related_keywords=[],
            ),
        ],
    )


class TestInitialization:
    """Test agent initialization"""

    @patch("src.agents.keyword_refiner.AnthropicClient")
    def test_init_creates_client(self, mock_anthropic):
        """Test initialization creates Anthropic client"""
        agent = KeywordRefinementAgent()

        mock_anthropic.assert_called_once()
        assert agent.client is not None
        assert agent.model is not None


class TestAddCustomKeywords:
    """Test add_custom_keywords method"""

    def test_add_custom_secondary_keywords(self, sample_strategy):
        """Test adding custom secondary keywords"""
        agent = KeywordRefinementAgent()

        # Store original count before mutation
        original_count = len(sample_strategy.secondary_keywords)
        custom_keywords = ["custom keyword 1", "custom keyword 2"]

        result = agent.add_custom_keywords(
            sample_strategy, custom_keywords, keyword_type="secondary"
        )

        # Should add 2 keywords (method mutates the object)
        assert len(result.secondary_keywords) == original_count + 2

        # Check last keywords are the custom ones
        assert result.secondary_keywords[-2].keyword == "custom keyword 1"
        assert result.secondary_keywords[-1].keyword == "custom keyword 2"

        # Check defaults
        assert result.secondary_keywords[-1].intent == KeywordIntent.INFORMATIONAL
        assert result.secondary_keywords[-1].difficulty == KeywordDifficulty.MEDIUM
        assert result.secondary_keywords[-1].notes == "User-provided custom keyword"

    def test_add_custom_primary_keywords(self, sample_strategy):
        """Test adding custom primary keywords"""
        agent = KeywordRefinementAgent()

        original_count = len(sample_strategy.primary_keywords)
        custom_keywords = ["custom primary keyword"]

        result = agent.add_custom_keywords(sample_strategy, custom_keywords, keyword_type="primary")

        assert len(result.primary_keywords) == original_count + 1
        assert result.primary_keywords[-1].keyword == "custom primary keyword"

    def test_add_custom_longtail_keywords(self, sample_strategy):
        """Test adding custom longtail keywords"""
        agent = KeywordRefinementAgent()

        original_count = len(sample_strategy.longtail_keywords)
        custom_keywords = ["how to do something specific step by step"]

        result = agent.add_custom_keywords(
            sample_strategy, custom_keywords, keyword_type="longtail"
        )

        assert len(result.longtail_keywords) == original_count + 1
        assert result.longtail_keywords[-1].keyword == "how to do something specific step by step"

    def test_add_multiple_custom_keywords(self, sample_strategy):
        """Test adding multiple custom keywords at once"""
        agent = KeywordRefinementAgent()

        original_count = len(sample_strategy.secondary_keywords)
        custom_keywords = ["keyword 1", "keyword 2", "keyword 3", "keyword 4", "keyword 5"]

        result = agent.add_custom_keywords(
            sample_strategy, custom_keywords, keyword_type="secondary"
        )

        assert len(result.secondary_keywords) == original_count + 5

    def test_add_empty_list(self, sample_strategy):
        """Test adding empty list of keywords"""
        agent = KeywordRefinementAgent()

        original_count = len(sample_strategy.secondary_keywords)

        result = agent.add_custom_keywords(sample_strategy, [], keyword_type="secondary")

        # Should not change anything
        assert len(result.secondary_keywords) == original_count


class TestRemoveKeywords:
    """Test remove_keywords method"""

    def test_remove_single_keyword(self, sample_strategy):
        """Test removing a single keyword"""
        agent = KeywordRefinementAgent()

        original_count = len(sample_strategy.secondary_keywords)
        keywords_to_remove = ["content calendar"]

        result = agent.remove_keywords(sample_strategy, keywords_to_remove)

        # Should remove 1 keyword from secondary
        assert len(result.secondary_keywords) == original_count - 1

        # Keyword should not be in result
        assert not any(kw.keyword == "content calendar" for kw in result.secondary_keywords)

    def test_remove_multiple_keywords(self, sample_strategy):
        """Test removing multiple keywords"""
        agent = KeywordRefinementAgent()

        original_count = len(sample_strategy.secondary_keywords)
        keywords_to_remove = ["content calendar", "editorial workflow"]

        result = agent.remove_keywords(sample_strategy, keywords_to_remove)

        # Should remove 2 keywords from secondary
        assert len(result.secondary_keywords) == original_count - 2

    def test_remove_case_insensitive(self, sample_strategy):
        """Test removal is case-insensitive"""
        agent = KeywordRefinementAgent()

        keywords_to_remove = ["CONTENT CALENDAR"]  # Uppercase

        result = agent.remove_keywords(sample_strategy, keywords_to_remove)

        # Should still remove the keyword
        assert not any(kw.keyword.lower() == "content calendar" for kw in result.secondary_keywords)

    def test_remove_from_primary_keywords(self, sample_strategy):
        """Test removing from primary keywords"""
        agent = KeywordRefinementAgent()

        original_count = len(sample_strategy.primary_keywords)
        keywords_to_remove = ["content marketing"]

        result = agent.remove_keywords(sample_strategy, keywords_to_remove)

        assert len(result.primary_keywords) == original_count - 1
        assert not any(kw.keyword == "content marketing" for kw in result.primary_keywords)

    def test_remove_from_longtail_keywords(self, sample_strategy):
        """Test removing from longtail keywords"""
        agent = KeywordRefinementAgent()

        original_count = len(sample_strategy.longtail_keywords)
        keywords_to_remove = ["how to create a content calendar"]

        result = agent.remove_keywords(sample_strategy, keywords_to_remove)

        assert len(result.longtail_keywords) == original_count - 1

    def test_remove_nonexistent_keyword(self, sample_strategy):
        """Test removing keyword that doesn't exist"""
        agent = KeywordRefinementAgent()

        original_primary = len(sample_strategy.primary_keywords)
        original_secondary = len(sample_strategy.secondary_keywords)
        original_longtail = len(sample_strategy.longtail_keywords)

        keywords_to_remove = ["nonexistent keyword"]

        result = agent.remove_keywords(sample_strategy, keywords_to_remove)

        # Counts should not change
        assert len(result.primary_keywords) == original_primary
        assert len(result.secondary_keywords) == original_secondary
        assert len(result.longtail_keywords) == original_longtail

    def test_remove_empty_list(self, sample_strategy):
        """Test removing empty list of keywords"""
        agent = KeywordRefinementAgent()

        original_primary = len(sample_strategy.primary_keywords)
        original_secondary = len(sample_strategy.secondary_keywords)
        original_longtail = len(sample_strategy.longtail_keywords)

        result = agent.remove_keywords(sample_strategy, [])

        # Should not change anything
        assert len(result.primary_keywords) == original_primary
        assert len(result.secondary_keywords) == original_secondary
        assert len(result.longtail_keywords) == original_longtail


class TestDisplayKeywords:
    """Test _display_keywords method"""

    @patch("src.agents.keyword_refiner.console")
    def test_display_shows_all_keyword_types(self, mock_console, sample_strategy):
        """Test display shows primary, secondary, and longtail keywords"""
        agent = KeywordRefinementAgent()

        agent._display_keywords(sample_strategy)

        # Check console.print was called
        assert mock_console.print.call_count > 0

        # Check it printed headers for all types
        calls = [str(call) for call in mock_console.print.call_args_list]
        all_calls = " ".join(calls)

        assert "Primary" in all_calls or "primary" in all_calls
        assert "Secondary" in all_calls or "secondary" in all_calls
        assert "Long-tail" in all_calls or "longtail" in all_calls

    @patch("src.agents.keyword_refiner.console")
    def test_display_shows_keyword_details(self, mock_console, sample_strategy):
        """Test display shows keyword intent and difficulty"""
        agent = KeywordRefinementAgent()

        agent._display_keywords(sample_strategy)

        # Check it showed keyword details
        calls = [str(call) for call in mock_console.print.call_args_list]
        all_calls = " ".join(calls)

        # Should show at least one keyword name
        assert "content marketing" in all_calls or "content" in all_calls

    @patch("src.agents.keyword_refiner.console")
    def test_display_limits_secondary_keywords(self, mock_console):
        """Test display shows only first 5 secondary keywords"""
        agent = KeywordRefinementAgent()

        # Create strategy with many secondary keywords
        strategy = KeywordStrategy(
            primary_keywords=[],
            secondary_keywords=[
                SEOKeyword(
                    keyword=f"keyword {i}",
                    intent=KeywordIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.MEDIUM,
                    priority=i,
                )
                for i in range(10)
            ],
            longtail_keywords=[],
        )

        agent._display_keywords(strategy)

        # Should mention "more" for truncated list
        calls = [str(call) for call in mock_console.print.call_args_list]
        all_calls = " ".join(calls)

        assert "more" in all_calls or "..." in all_calls


class TestReviewKeywordsInteractive:
    """Test review_keywords_interactive method"""

    @patch("src.agents.keyword_refiner.input")
    @patch("src.agents.keyword_refiner.console")
    def test_review_no_feedback_returns_original(self, mock_console, mock_input, sample_strategy):
        """Test review with no feedback returns original strategy"""
        agent = KeywordRefinementAgent()

        # Simulate user pressing Enter (empty feedback)
        mock_input.return_value = ""

        result = agent.review_keywords_interactive(sample_strategy)

        # Should return original strategy unchanged
        assert result == sample_strategy
        assert len(result.primary_keywords) == len(sample_strategy.primary_keywords)

    @patch("src.agents.keyword_refiner.input")
    @patch("src.agents.keyword_refiner.console")
    @patch("src.agents.keyword_refiner.AnthropicClient")
    def test_review_with_feedback_calls_ai(
        self, mock_anthropic, mock_console, mock_input, sample_strategy
    ):
        """Test review with feedback triggers AI refinement"""
        # Mock AI response
        mock_anthropic.return_value.create_message.return_value = """{
            "primary_keywords": [{"keyword": "new keyword", "intent": "informational", "difficulty": "medium", "priority": 1, "related_keywords": [], "notes": "test"}],
            "secondary_keywords": [],
            "longtail_keywords": []
        }"""

        agent = KeywordRefinementAgent()

        # Simulate user providing feedback
        mock_input.return_value = "Make keywords more specific"

        result = agent.review_keywords_interactive(sample_strategy)

        # Should call Anthropic API
        mock_anthropic.return_value.create_message.assert_called_once()

        # Result should be different from original
        assert result != sample_strategy


class TestRefineWithAI:
    """Test _refine_with_ai method"""

    @patch("src.agents.keyword_refiner.AnthropicClient")
    def test_refine_with_ai_calls_api(self, mock_anthropic, sample_strategy):
        """Test AI refinement calls Anthropic API"""
        # Mock API response
        mock_anthropic.return_value.create_message.return_value = """{
            "primary_keywords": [{"keyword": "refined keyword", "intent": "informational", "difficulty": "medium", "priority": 1, "related_keywords": [], "notes": "test"}],
            "secondary_keywords": [],
            "longtail_keywords": []
        }"""

        agent = KeywordRefinementAgent()

        feedback = "Make keywords more industry-specific"
        result = agent._refine_with_ai(sample_strategy, feedback)

        # Should call API
        mock_anthropic.return_value.create_message.assert_called_once()

        # Should return KeywordStrategy
        assert isinstance(result, KeywordStrategy)

    @patch("src.agents.keyword_refiner.AnthropicClient")
    def test_refine_includes_feedback_in_prompt(self, mock_anthropic, sample_strategy):
        """Test refinement includes user feedback in prompt"""
        # Mock API response
        mock_anthropic.return_value.create_message.return_value = """{
            "primary_keywords": [],
            "secondary_keywords": [],
            "longtail_keywords": []
        }"""

        agent = KeywordRefinementAgent()

        feedback = "Focus on B2B SaaS keywords"
        agent._refine_with_ai(sample_strategy, feedback)

        # Check that feedback was included in the API call
        call_args = mock_anthropic.return_value.create_message.call_args
        messages = call_args.kwargs["messages"]

        assert any(feedback in str(msg) for msg in messages)

    @patch("src.agents.keyword_refiner.AnthropicClient")
    def test_refine_includes_current_keywords(self, mock_anthropic, sample_strategy):
        """Test refinement includes current keywords in prompt"""
        # Mock API response
        mock_anthropic.return_value.create_message.return_value = """{
            "primary_keywords": [],
            "secondary_keywords": [],
            "longtail_keywords": []
        }"""

        agent = KeywordRefinementAgent()

        agent._refine_with_ai(sample_strategy, "test feedback")

        # Check that current keywords were included
        call_args = mock_anthropic.return_value.create_message.call_args
        messages = call_args.kwargs["messages"]
        message_text = str(messages)

        # Should include at least one current keyword
        assert "content marketing" in message_text or "content" in message_text
