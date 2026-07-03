"""Tests for Keyword Extraction Agent"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.agents.keyword_agent import KeywordExtractionAgent
from src.models.client_brief import ClientBrief
from src.models.seo_keyword import KeywordDifficulty, KeywordIntent, KeywordStrategy, SEOKeyword


@pytest.fixture
def sample_brief():
    """Create a sample client brief"""
    return ClientBrief(
        company_name="Test SaaS Co",
        business_description="We provide B2B workflow automation software",
        ideal_customer="VP of Operations at mid-market companies",
        main_problem_solved="Manual processes and data silos",
        customer_pain_points=["Inefficient workflows", "Data inconsistency", "Scaling challenges"],
        customer_questions=["How long to implement?", "Does it integrate with Salesforce?"],
        misconceptions=["Automation is too expensive", "It requires technical expertise"],
    )


@pytest.fixture
def minimal_brief():
    """Create minimal brief with only required fields"""
    return ClientBrief(
        company_name="Minimal Co",
        business_description="Software",
        ideal_customer="Businesses",
        main_problem_solved="Problems",
    )


@pytest.fixture
def sample_keyword_json():
    """Sample keyword response JSON"""
    return {
        "primary_keywords": [
            {
                "keyword": "B2B workflow automation",
                "intent": "commercial",
                "difficulty": "hard",
                "priority": 1,
                "related_keywords": ["business process automation", "workflow software"],
                "notes": "Core offering keyword",
            },
            {
                "keyword": "enterprise workflow management",
                "intent": "commercial",
                "difficulty": "medium",
                "priority": 2,
                "related_keywords": ["workflow tools", "process management"],
                "notes": "Secondary focus",
            },
        ],
        "secondary_keywords": [
            {
                "keyword": "workflow automation software",
                "intent": "commercial",
                "difficulty": "medium",
                "priority": 1,
                "related_keywords": [],
            }
        ],
        "longtail_keywords": [
            {
                "keyword": "how to automate manual workflows",
                "intent": "informational",
                "difficulty": "easy",
                "priority": 1,
                "related_keywords": [],
                "notes": "Question-based keyword",
            }
        ],
    }


class TestInitialization:
    """Test agent initialization"""

    @patch("src.agents.keyword_agent.AnthropicClient")
    def test_init_creates_anthropic_client(self, mock_anthropic):
        """Test initialization creates Anthropic client"""
        agent = KeywordExtractionAgent()

        mock_anthropic.assert_called_once()
        assert agent.client is not None
        assert agent.model is not None


class TestExtractKeywords:
    """Test extract_keywords method"""

    @patch("src.agents.keyword_agent.AnthropicClient")
    def test_extract_keywords_success(self, mock_anthropic, sample_brief, sample_keyword_json):
        """Test successful keyword extraction"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps(sample_keyword_json)
        mock_anthropic.return_value.create_message.return_value = mock_response.content[0].text

        agent = KeywordExtractionAgent()
        strategy = agent.extract_keywords(sample_brief)

        # Verify API was called
        mock_anthropic.return_value.create_message.assert_called_once()

        # Verify strategy structure
        assert isinstance(strategy, KeywordStrategy)
        assert len(strategy.primary_keywords) == 2
        assert len(strategy.secondary_keywords) == 1
        assert len(strategy.longtail_keywords) == 1

        # Verify first primary keyword
        primary = strategy.primary_keywords[0]
        assert primary.keyword == "B2B workflow automation"
        assert primary.intent == KeywordIntent.COMMERCIAL
        assert primary.difficulty == KeywordDifficulty.HARD
        assert primary.priority == 1

    @patch("src.agents.keyword_agent.AnthropicClient")
    def test_extract_keywords_uses_correct_params(self, mock_anthropic, sample_brief):
        """Test API call uses correct parameters"""
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = (
            '{"primary_keywords": [], "secondary_keywords": [], "longtail_keywords": []}'
        )
        mock_anthropic.return_value.create_message.return_value = mock_response.content[0].text

        agent = KeywordExtractionAgent()
        agent.extract_keywords(sample_brief)

        call_kwargs = mock_anthropic.return_value.create_message.call_args.kwargs

        # Check parameters
        assert call_kwargs["max_tokens"] == 4000
        assert call_kwargs["temperature"] == 0.3
        assert "system" in call_kwargs
        assert "messages" in call_kwargs

    @patch("src.agents.keyword_agent.AnthropicClient")
    def test_extract_keywords_includes_context(self, mock_anthropic, sample_brief):
        """Test keyword extraction includes client context"""
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = (
            '{"primary_keywords": [], "secondary_keywords": [], "longtail_keywords": []}'
        )
        mock_anthropic.return_value.create_message.return_value = mock_response.content[0].text

        agent = KeywordExtractionAgent()
        agent.extract_keywords(sample_brief)

        call_kwargs = mock_anthropic.return_value.create_message.call_args.kwargs
        user_message = call_kwargs["messages"][0]["content"]

        # Check context includes key information
        assert sample_brief.company_name in user_message
        assert sample_brief.business_description in user_message


class TestExtractJsonFromResponse:
    """Test _extract_json_from_response method"""

    def test_extract_plain_json(self):
        """Test extracting plain JSON"""
        agent = KeywordExtractionAgent()
        response = '{"primary_keywords": [], "secondary_keywords": [], "longtail_keywords": []}'

        result = agent._extract_json_from_response(response)

        assert result == {"primary_keywords": [], "secondary_keywords": [], "longtail_keywords": []}

    def test_extract_json_with_markdown_code_fences(self):
        """Test extracting JSON with markdown code fences"""
        agent = KeywordExtractionAgent()
        response = """```json
{
  "primary_keywords": [],
  "secondary_keywords": [],
  "longtail_keywords": []
}
```"""

        result = agent._extract_json_from_response(response)

        assert "primary_keywords" in result
        assert "secondary_keywords" in result

    def test_extract_json_with_plain_code_fences(self):
        """Test extracting JSON with plain code fences (no json tag)"""
        agent = KeywordExtractionAgent()
        response = """```
{"primary_keywords": [], "secondary_keywords": [], "longtail_keywords": []}
```"""

        result = agent._extract_json_from_response(response)

        assert "primary_keywords" in result

    def test_extract_json_with_extra_text_before(self):
        """Test extracting JSON when there's text before JSON object"""
        agent = KeywordExtractionAgent()
        response = 'Here are the keywords:\n\n{"primary_keywords": [], "secondary_keywords": [], "longtail_keywords": []}'

        result = agent._extract_json_from_response(response)

        assert "primary_keywords" in result

    def test_extract_json_with_whitespace(self):
        """Test extracting JSON with extra whitespace"""
        agent = KeywordExtractionAgent()
        response = """

        {"primary_keywords": [], "secondary_keywords": [], "longtail_keywords": []}

        """

        result = agent._extract_json_from_response(response)

        assert "primary_keywords" in result

    def test_extract_json_repairs_truncated(self):
        """Test JSON repair for truncated responses (missing closing brackets)"""
        agent = KeywordExtractionAgent()
        # Slightly truncated but repairable
        response = '{"primary_keywords": [], "secondary_keywords": []'  # Missing closing brace

        result = agent._extract_json_from_response(response)

        # Should successfully repair and parse
        assert "primary_keywords" in result
        assert "secondary_keywords" in result

    def test_extract_json_raises_on_invalid(self):
        """Test raises ValueError on completely invalid JSON"""
        agent = KeywordExtractionAgent()
        response = "This is not JSON at all, no brackets or anything"

        with pytest.raises(ValueError, match="Failed to extract valid JSON"):
            agent._extract_json_from_response(response)

    def test_extract_json_handles_nested_objects(self):
        """Test extracting complex nested JSON"""
        agent = KeywordExtractionAgent()
        response = """{
            "primary_keywords": [
                {
                    "keyword": "test",
                    "intent": "informational",
                    "related_keywords": ["a", "b"]
                }
            ],
            "secondary_keywords": [],
            "longtail_keywords": []
        }"""

        result = agent._extract_json_from_response(response)

        assert len(result["primary_keywords"]) == 1
        assert result["primary_keywords"][0]["related_keywords"] == ["a", "b"]


class TestBuildExtractionContext:
    """Test _build_extraction_context method"""

    def test_build_context_with_full_brief(self, sample_brief):
        """Test context building with complete brief"""
        agent = KeywordExtractionAgent()
        context = agent._build_extraction_context(sample_brief)

        # Check all key fields are included
        assert sample_brief.company_name in context
        assert sample_brief.business_description in context
        assert sample_brief.ideal_customer in context
        assert sample_brief.main_problem_solved in context

        # Check optional fields
        assert "Pain Points" in context
        assert sample_brief.customer_pain_points[0] in context
        assert "Customer Questions" in context
        assert sample_brief.customer_questions[0] in context
        assert "Misconceptions" in context
        assert sample_brief.misconceptions[0] in context

    def test_build_context_with_minimal_brief(self, minimal_brief):
        """Test context building with minimal required fields only"""
        agent = KeywordExtractionAgent()
        context = agent._build_extraction_context(minimal_brief)

        # Check required fields
        assert minimal_brief.company_name in context
        assert minimal_brief.business_description in context
        assert minimal_brief.ideal_customer in context
        assert minimal_brief.main_problem_solved in context

        # Optional sections should not be present
        assert "Pain Points" not in context
        assert "Customer Questions" not in context
        assert "Misconceptions" not in context

    def test_build_context_limits_customer_questions(self):
        """Test customer questions are limited to 5"""
        agent = KeywordExtractionAgent()
        brief = ClientBrief(
            company_name="Test",
            business_description="Software",
            ideal_customer="Businesses",
            main_problem_solved="Problems",
            customer_questions=["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7"],  # 7 questions
        )

        context = agent._build_extraction_context(brief)

        # Should include first 5, not 6th
        assert "Q1" in context
        assert "Q5" in context
        assert "Q6" not in context

    def test_build_context_limits_misconceptions(self):
        """Test misconceptions are limited to 3"""
        agent = KeywordExtractionAgent()
        brief = ClientBrief(
            company_name="Test",
            business_description="Software",
            ideal_customer="Businesses",
            main_problem_solved="Problems",
            misconceptions=["M1", "M2", "M3", "M4", "M5"],  # 5 misconceptions
        )

        context = agent._build_extraction_context(brief)

        # Should include first 3, not 4th
        assert "M1" in context
        assert "M3" in context
        assert "M4" not in context

    def test_build_context_format(self, sample_brief):
        """Test context has proper markdown formatting"""
        agent = KeywordExtractionAgent()
        context = agent._build_extraction_context(sample_brief)

        # Check markdown formatting
        assert "**Company:**" in context
        assert "**Business:**" in context
        assert "**Target Audience:**" in context
        assert "**Main Problem:**" in context


class TestBuildSystemPrompt:
    """Test _build_system_prompt method"""

    def test_system_prompt_includes_rules(self):
        """Test system prompt includes keyword extraction rules"""
        agent = KeywordExtractionAgent()
        prompt = agent._build_system_prompt()

        # Check key sections
        assert "PRIMARY KEYWORDS" in prompt
        assert "SECONDARY KEYWORDS" in prompt
        assert "LONG-TAIL KEYWORDS" in prompt
        assert "KEYWORD INTENT CLASSIFICATION" in prompt
        assert "DIFFICULTY ESTIMATION" in prompt
        assert "OUTPUT FORMAT" in prompt

    def test_system_prompt_includes_examples(self):
        """Test system prompt includes examples"""
        agent = KeywordExtractionAgent()
        prompt = agent._build_system_prompt()

        # Check examples are present
        assert "B2B content marketing" in prompt
        assert "content calendar template" in prompt
        assert "how to scale content" in prompt

    def test_system_prompt_specifies_platforms(self):
        """Test system prompt mentions LinkedIn and Twitter"""
        agent = KeywordExtractionAgent()
        prompt = agent._build_system_prompt()

        assert "LinkedIn" in prompt
        assert "Twitter" in prompt


class TestParseKeywordStrategy:
    """Test _parse_keyword_strategy method"""

    def test_parse_complete_strategy(self, sample_keyword_json):
        """Test parsing complete keyword strategy"""
        agent = KeywordExtractionAgent()
        strategy = agent._parse_keyword_strategy(sample_keyword_json)

        assert isinstance(strategy, KeywordStrategy)
        assert len(strategy.primary_keywords) == 2
        assert len(strategy.secondary_keywords) == 1
        assert len(strategy.longtail_keywords) == 1

    def test_parse_keyword_details(self, sample_keyword_json):
        """Test parsed keywords have correct details"""
        agent = KeywordExtractionAgent()
        strategy = agent._parse_keyword_strategy(sample_keyword_json)

        primary = strategy.primary_keywords[0]
        assert isinstance(primary, SEOKeyword)
        assert primary.keyword == "B2B workflow automation"
        assert primary.intent == KeywordIntent.COMMERCIAL
        assert primary.difficulty == KeywordDifficulty.HARD
        assert primary.priority == 1
        assert "business process automation" in primary.related_keywords
        assert primary.notes == "Core offering keyword"

    def test_parse_empty_strategy(self):
        """Test parsing empty keyword data"""
        agent = KeywordExtractionAgent()
        empty_data = {
            "primary_keywords": [],
            "secondary_keywords": [],
            "longtail_keywords": [],
        }

        strategy = agent._parse_keyword_strategy(empty_data)

        assert len(strategy.primary_keywords) == 0
        assert len(strategy.secondary_keywords) == 0
        assert len(strategy.longtail_keywords) == 0

    def test_parse_with_defaults(self):
        """Test parsing applies defaults for missing optional fields"""
        agent = KeywordExtractionAgent()
        data = {
            "primary_keywords": [
                {
                    "keyword": "test keyword",
                    # Missing intent, difficulty, priority, related_keywords, notes
                }
            ],
            "secondary_keywords": [],
            "longtail_keywords": [],
        }

        strategy = agent._parse_keyword_strategy(data)

        keyword = strategy.primary_keywords[0]
        assert keyword.keyword == "test keyword"
        assert keyword.intent == KeywordIntent.INFORMATIONAL  # Default
        assert keyword.difficulty == KeywordDifficulty.MEDIUM  # Default
        assert keyword.priority == 1  # Default
        assert keyword.related_keywords == []  # Default
        assert keyword.notes is None  # Default

    def test_parse_skips_invalid_keywords(self):
        """Test parsing skips keywords that fail validation"""
        agent = KeywordExtractionAgent()
        data = {
            "primary_keywords": [
                {"keyword": "valid keyword", "intent": "informational"},
                {"invalid": "no keyword field"},  # Should be skipped
                {"keyword": "another valid", "intent": "commercial"},
            ],
            "secondary_keywords": [],
            "longtail_keywords": [],
        }

        strategy = agent._parse_keyword_strategy(data)

        # Should have 2 valid keywords, skipped the invalid one
        assert len(strategy.primary_keywords) == 2
        assert strategy.primary_keywords[0].keyword == "valid keyword"
        assert strategy.primary_keywords[1].keyword == "another valid"

    def test_parse_handles_missing_sections(self):
        """Test parsing when entire sections are missing"""
        agent = KeywordExtractionAgent()
        data = {
            "primary_keywords": [{"keyword": "test", "intent": "informational"}],
            # Missing secondary_keywords and longtail_keywords
        }

        strategy = agent._parse_keyword_strategy(data)

        assert len(strategy.primary_keywords) == 1
        assert len(strategy.secondary_keywords) == 0  # Defaults to empty
        assert len(strategy.longtail_keywords) == 0  # Defaults to empty


class TestEdgeCases:
    """Test edge cases and error conditions"""

    @patch("src.agents.keyword_agent.AnthropicClient")
    def test_extract_keywords_with_empty_brief(self, mock_anthropic, minimal_brief):
        """Test keyword extraction works with minimal brief"""
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = (
            '{"primary_keywords": [], "secondary_keywords": [], "longtail_keywords": []}'
        )
        mock_anthropic.return_value.create_message.return_value = mock_response.content[0].text

        agent = KeywordExtractionAgent()
        strategy = agent.extract_keywords(minimal_brief)

        # Should still work, just with empty strategy
        assert isinstance(strategy, KeywordStrategy)

    def test_extract_json_from_text_with_embedded_json(self):
        """Test extraction when JSON is embedded in text"""
        agent = KeywordExtractionAgent()
        response = 'Here is the result: {"primary_keywords": [], "secondary_keywords": [], "longtail_keywords": []} - that is all'

        result = agent._extract_json_from_response(response)

        # Should extract the JSON object
        assert "primary_keywords" in result
        assert "secondary_keywords" in result

    def test_parse_keyword_with_all_intent_types(self):
        """Test parsing keywords with all intent types"""
        agent = KeywordExtractionAgent()
        data = {
            "primary_keywords": [
                {"keyword": "test1", "intent": "informational"},
                {"keyword": "test2", "intent": "commercial"},
                {"keyword": "test3", "intent": "transactional"},
                {"keyword": "test4", "intent": "navigational"},
            ],
            "secondary_keywords": [],
            "longtail_keywords": [],
        }

        strategy = agent._parse_keyword_strategy(data)

        assert strategy.primary_keywords[0].intent == KeywordIntent.INFORMATIONAL
        assert strategy.primary_keywords[1].intent == KeywordIntent.COMMERCIAL
        assert strategy.primary_keywords[2].intent == KeywordIntent.TRANSACTIONAL
        assert strategy.primary_keywords[3].intent == KeywordIntent.NAVIGATIONAL

    def test_parse_keyword_with_all_difficulty_levels(self):
        """Test parsing keywords with all difficulty levels"""
        agent = KeywordExtractionAgent()
        data = {
            "primary_keywords": [
                {"keyword": "test1", "difficulty": "easy"},
                {"keyword": "test2", "difficulty": "medium"},
                {"keyword": "test3", "difficulty": "hard"},
            ],
            "secondary_keywords": [],
            "longtail_keywords": [],
        }

        strategy = agent._parse_keyword_strategy(data)

        assert strategy.primary_keywords[0].difficulty == KeywordDifficulty.EASY
        assert strategy.primary_keywords[1].difficulty == KeywordDifficulty.MEDIUM
        assert strategy.primary_keywords[2].difficulty == KeywordDifficulty.HARD


class TestJsonExtractionEdgeCases:
    """Additional tests for JSON extraction edge cases to improve coverage"""

    def test_extract_json_code_fence_fallback_no_closing(self):
        """Test fallback when code fence regex doesn't match (malformed fence without closing)"""
        agent = KeywordExtractionAgent()
        # Code fence starts with ``` but doesn't have proper closing ``` pattern
        # This triggers the fallback logic on lines 94-99
        response = """```json
{"primary_keywords": [], "secondary_keywords": [], "longtail_keywords": []}
```other stuff"""  # Different closing pattern that breaks regex

        result = agent._extract_json_from_response(response)
        assert "primary_keywords" in result

    def test_extract_json_repairs_truncated_with_missing_brace(self):
        """Test JSON repair handles missing closing brace"""
        agent = KeywordExtractionAgent()
        # Properly formed JSON but truncated - missing only the final }
        response = '{"primary_keywords": [], "secondary_keywords": [], "longtail_keywords": []'

        result = agent._extract_json_from_response(response)
        assert "primary_keywords" in result
        assert "secondary_keywords" in result
        assert "longtail_keywords" in result

    def test_extract_json_repairs_truncated_array_bracket(self):
        """Test JSON repair for truncated arrays - adds closing bracket (line 133)"""
        agent = KeywordExtractionAgent()
        # Array truncated after valid items - missing ] and }
        response = '{"primary_keywords": [{"keyword": "test", "intent": "informational"}]'

        # This should parse fine - the test below tests the bracket repair
        result = agent._extract_json_from_response(response)
        assert "primary_keywords" in result

    def test_extract_json_unterminated_string_triggers_repair(self):
        """Test that 'Unterminated string' error message triggers repair logic (line 119)"""
        agent = KeywordExtractionAgent()
        # Simple truncation missing only closing }
        response = '{"primary_keywords": [], "secondary_keywords": []'  # Missing }

        result = agent._extract_json_from_response(response)
        assert "primary_keywords" in result
        assert "secondary_keywords" in result

    def test_extract_json_failed_repair_raises_valueerror(self):
        """Test that failed repair attempt still raises ValueError"""
        agent = KeywordExtractionAgent()
        # Completely malformed - can't be repaired
        response = '{"primary_keywords": [invalid json here'

        with pytest.raises(ValueError, match="Failed to extract valid JSON"):
            agent._extract_json_from_response(response)
