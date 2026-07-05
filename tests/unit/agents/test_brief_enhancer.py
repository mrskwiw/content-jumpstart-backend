"""Tests for Brief Enhancer Agent"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.agents.brief_enhancer import BriefEnhancerAgent
from src.models.brief_quality import BriefQualityReport
from src.models.client_brief import ClientBrief


@pytest.fixture
def mock_anthropic_client():
    """Create mock Anthropic client"""
    return MagicMock()


@pytest.fixture
def sample_brief():
    """Create a sample client brief"""
    return ClientBrief(
        company_name="Test Company",
        business_description="We sell software",
        ideal_customer="Small businesses",
        main_problem_solved="Inefficiency",
    )


@pytest.fixture
def weak_brief():
    """Create a brief with weak fields"""
    return ClientBrief(
        company_name="Test Company",
        business_description="Software",  # Too short
        ideal_customer="Businesses",  # Too generic
        main_problem_solved="Problems",  # Too vague
    )


@pytest.fixture
def high_quality_report():
    """Create a high-quality report (≥85%)"""
    from src.models.brief_quality import FieldQuality

    return BriefQualityReport(
        overall_score=0.90,
        completeness_score=0.95,
        specificity_score=0.85,
        usability_score=0.90,
        field_quality={
            "company_name": FieldQuality.STRONG,
            "business_description": FieldQuality.STRONG,
            "ideal_customer": FieldQuality.STRONG,
            "main_problem_solved": FieldQuality.STRONG,
        },
        missing_fields=[],
        weak_fields=[],
        strong_fields=["company_name", "business_description", "ideal_customer"],
        priority_improvements=[],
        can_generate_content=True,
        minimum_questions_needed=0,
        total_fields=10,
        filled_fields=9,
        required_fields_filled=4,
    )


@pytest.fixture
def low_quality_report():
    """Create a low-quality report (<85%)"""
    from src.models.brief_quality import FieldQuality

    return BriefQualityReport(
        overall_score=0.60,
        completeness_score=0.70,
        specificity_score=0.50,
        usability_score=0.60,
        field_quality={
            "company_name": FieldQuality.STRONG,
            "business_description": FieldQuality.WEAK,
            "ideal_customer": FieldQuality.WEAK,
            "main_problem_solved": FieldQuality.ADEQUATE,
            "target_platforms": FieldQuality.MISSING,
            "posting_frequency": FieldQuality.MISSING,
        },
        missing_fields=["target_platforms", "posting_frequency"],
        weak_fields=["business_description", "ideal_customer"],
        strong_fields=["company_name"],
        priority_improvements=["Add more detail to business description", "Specify ideal customer"],
        can_generate_content=False,
        minimum_questions_needed=3,
        total_fields=10,
        filled_fields=6,
        required_fields_filled=4,
    )


class TestInitialization:
    """Test agent initialization"""

    def test_init_with_client(self, mock_anthropic_client):
        """Test initialization with provided client"""
        agent = BriefEnhancerAgent(client=mock_anthropic_client)
        assert agent.client == mock_anthropic_client

    def test_init_without_client(self):
        """Test initialization creates default client"""
        with patch("src.agents.brief_enhancer.AnthropicClient") as mock_client_class:
            agent = BriefEnhancerAgent()
            mock_client_class.assert_called_once()
            assert agent.client == mock_client_class.return_value


class TestEnhanceBrief:
    """Test main enhance_brief method"""

    def test_skip_enhancement_for_high_quality(
        self, sample_brief, high_quality_report, mock_anthropic_client
    ):
        """Test enhancement is skipped when quality ≥85%"""
        agent = BriefEnhancerAgent(client=mock_anthropic_client)
        result = agent.enhance_brief(sample_brief, high_quality_report)

        # Should return original brief unchanged
        assert result == sample_brief
        # Should not call API
        mock_anthropic_client.create_message.assert_not_called()

    def test_enhance_low_quality_brief_auto_apply(
        self, weak_brief, low_quality_report, mock_anthropic_client
    ):
        """Test enhancement is applied for low-quality brief"""
        # Mock API response
        enhancement_json = {
            "business_description": "We provide enterprise software solutions for workflow automation",
            "ideal_customer": "Small to medium businesses in healthcare and finance sectors",
        }
        mock_anthropic_client.create_message.return_value = json.dumps(enhancement_json)

        agent = BriefEnhancerAgent(client=mock_anthropic_client)
        result = agent.enhance_brief(weak_brief, low_quality_report, auto_apply=True)

        # Should call API
        mock_anthropic_client.create_message.assert_called_once()

        # Should apply enhancements
        assert result.business_description == enhancement_json["business_description"]
        assert result.ideal_customer == enhancement_json["ideal_customer"]

    def test_enhance_suggest_only_mode(self, weak_brief, low_quality_report, mock_anthropic_client):
        """Test suggest-only mode doesn't apply enhancements"""
        # Mock API response
        enhancement_json = {
            "business_description": "We provide enterprise software solutions",
        }
        mock_anthropic_client.create_message.return_value = json.dumps(enhancement_json)

        agent = BriefEnhancerAgent(client=mock_anthropic_client)
        result = agent.enhance_brief(weak_brief, low_quality_report, auto_apply=False)

        # Should call API
        mock_anthropic_client.create_message.assert_called_once()

        # Should NOT apply enhancements
        assert result == weak_brief

    def test_enhance_handles_api_error(self, weak_brief, low_quality_report, mock_anthropic_client):
        """Test enhancement handles API errors gracefully"""
        # Mock API error
        mock_anthropic_client.create_message.side_effect = Exception("API Error")

        agent = BriefEnhancerAgent(client=mock_anthropic_client)
        result = agent.enhance_brief(weak_brief, low_quality_report)

        # Should return original brief on error
        assert result == weak_brief


class TestGenerateEnhancements:
    """Test _generate_enhancements method"""

    def test_generate_enhancements_for_weak_fields(
        self, weak_brief, low_quality_report, mock_anthropic_client
    ):
        """Test enhancement generation for weak fields"""
        enhancement_json = {
            "business_description": "Enhanced description",
            "ideal_customer": "Enhanced customer profile",
        }
        mock_anthropic_client.create_message.return_value = json.dumps(enhancement_json)

        agent = BriefEnhancerAgent(client=mock_anthropic_client)
        enhancements = agent._generate_enhancements(weak_brief, low_quality_report)

        assert enhancements == enhancement_json
        mock_anthropic_client.create_message.assert_called_once()

    def test_generate_enhancements_for_missing_fields(
        self, sample_brief, low_quality_report, mock_anthropic_client
    ):
        """Test enhancement generation for missing fields"""
        enhancement_json = {
            "target_platforms": ["LinkedIn", "Twitter"],
            "posting_frequency": "3 times per week",
        }
        mock_anthropic_client.create_message.return_value = json.dumps(enhancement_json)

        agent = BriefEnhancerAgent(client=mock_anthropic_client)
        enhancements = agent._generate_enhancements(sample_brief, low_quality_report)

        assert "target_platforms" in enhancements or "posting_frequency" in enhancements

    def test_generate_enhancements_no_targets(self, sample_brief, mock_anthropic_client):
        """Test enhancement generation when no fields need enhancement"""
        from src.models.brief_quality import FieldQuality

        agent = BriefEnhancerAgent(client=mock_anthropic_client)

        # Create report with no weak or missing fields
        empty_report = BriefQualityReport(
            overall_score=0.90,
            completeness_score=0.95,
            specificity_score=0.85,
            usability_score=0.90,
            field_quality={"company_name": FieldQuality.STRONG},
            missing_fields=[],
            weak_fields=[],
            strong_fields=["company_name"],
            priority_improvements=[],
            can_generate_content=True,
            minimum_questions_needed=0,
            total_fields=10,
            filled_fields=10,
            required_fields_filled=4,
        )

        enhancements = agent._generate_enhancements(sample_brief, empty_report)

        assert enhancements == {}
        mock_anthropic_client.create_message.assert_not_called()

    def test_generate_enhancements_handles_json_error(
        self, weak_brief, low_quality_report, mock_anthropic_client
    ):
        """Test enhancement generation handles invalid JSON"""
        # Return invalid JSON
        mock_anthropic_client.create_message.return_value = "This is not JSON"

        agent = BriefEnhancerAgent(client=mock_anthropic_client)
        enhancements = agent._generate_enhancements(weak_brief, low_quality_report)

        # Should return empty dict on error
        assert enhancements == {}


class TestBuildEnhancementPrompt:
    """Test _build_enhancement_prompt method"""

    def test_build_prompt_includes_brief_context(self, sample_brief, mock_anthropic_client):
        """Test prompt includes brief context"""
        agent = BriefEnhancerAgent(client=mock_anthropic_client)

        enhancement_targets = [
            {"field": "business_description", "current_value": "Software", "issue": "too brief"}
        ]

        prompt = agent._build_enhancement_prompt(sample_brief, enhancement_targets)

        assert sample_brief.company_name in prompt
        assert sample_brief.business_description in prompt
        assert "business_description" in prompt
        assert "too brief" in prompt

    def test_build_prompt_includes_enhancement_rules(self, sample_brief, mock_anthropic_client):
        """Test prompt includes enhancement rules"""
        agent = BriefEnhancerAgent(client=mock_anthropic_client)

        enhancement_targets = [
            {"field": "ideal_customer", "current_value": None, "issue": "missing"}
        ]

        prompt = agent._build_enhancement_prompt(sample_brief, enhancement_targets)

        assert "Maintain client voice" in prompt
        assert "Don't invent facts" in prompt
        assert "NEED_CLIENT_INPUT" in prompt
        assert "Return ONLY valid JSON" in prompt


class TestApplyEnhancements:
    """Test _apply_enhancements method"""

    def test_apply_enhancement_to_missing_field(self, sample_brief, mock_anthropic_client):
        """Test applying enhancement to missing field"""
        from src.models.client_brief import Platform

        agent = BriefEnhancerAgent(client=mock_anthropic_client)

        # Sample brief has no target_platforms
        enhancements = {"target_platforms": ["linkedin", "twitter"]}

        result = agent._apply_enhancements(sample_brief, enhancements)

        # Pydantic converts strings to Platform enum
        assert result.target_platforms == [Platform.LINKEDIN, Platform.TWITTER]

    def test_apply_enhancement_to_weak_field(self, weak_brief, mock_anthropic_client):
        """Test applying enhancement to weak field"""
        agent = BriefEnhancerAgent(client=mock_anthropic_client)

        enhancements = {
            "business_description": "We provide enterprise software solutions for automation"
        }

        result = agent._apply_enhancements(weak_brief, enhancements)

        assert result.business_description == enhancements["business_description"]

    def test_skip_need_client_input_enhancements(self, sample_brief, mock_anthropic_client):
        """Test skipping NEED_CLIENT_INPUT enhancements"""
        agent = BriefEnhancerAgent(client=mock_anthropic_client)

        enhancements = {"target_platforms": "NEED_CLIENT_INPUT"}

        result = agent._apply_enhancements(sample_brief, enhancements)

        # Should not apply NEED_CLIENT_INPUT
        assert result.target_platforms == sample_brief.target_platforms

    def test_apply_multiple_enhancements(self, weak_brief, mock_anthropic_client):
        """Test applying multiple enhancements"""
        agent = BriefEnhancerAgent(client=mock_anthropic_client)

        enhancements = {
            "business_description": "Enhanced description with more detail and specificity",
            "ideal_customer": "Small to medium businesses in healthcare sector",
        }

        result = agent._apply_enhancements(weak_brief, enhancements)

        assert result.business_description == enhancements["business_description"]
        assert result.ideal_customer == enhancements["ideal_customer"]

    def test_apply_handles_validation_error(self, sample_brief, mock_anthropic_client):
        """Test apply handles validation errors"""
        agent = BriefEnhancerAgent(client=mock_anthropic_client)

        # Invalid enhancement (company_name is required)
        enhancements = {"company_name": None}

        result = agent._apply_enhancements(sample_brief, enhancements)

        # Should return original brief on validation error
        assert result == sample_brief

    def test_apply_enhancement_to_empty_string(self, mock_anthropic_client):
        """Test applying enhancement to empty string field"""
        agent = BriefEnhancerAgent(client=mock_anthropic_client)

        brief = ClientBrief(
            company_name="Test",
            business_description="",  # Empty
            ideal_customer="Businesses",
            main_problem_solved="Problems",
        )

        enhancements = {"business_description": "Enhanced description"}

        result = agent._apply_enhancements(brief, enhancements)

        assert result.business_description == "Enhanced description"

    def test_apply_enhancement_to_empty_list(self, sample_brief, mock_anthropic_client):
        """Test applying enhancement to empty list field"""
        agent = BriefEnhancerAgent(client=mock_anthropic_client)

        # sample_brief has empty customer_pain_points
        enhancements = {"customer_pain_points": ["Pain 1", "Pain 2"]}

        result = agent._apply_enhancements(sample_brief, enhancements)

        assert result.customer_pain_points == ["Pain 1", "Pain 2"]


class TestSuggestEnhancementsOnly:
    """Test suggest_enhancements_only method"""

    def test_suggest_enhancements_only(self, weak_brief, low_quality_report, mock_anthropic_client):
        """Test generating suggestions without applying"""
        enhancement_json = {
            "business_description": "Enhanced description",
            "ideal_customer": "Enhanced customer",
        }
        mock_anthropic_client.create_message.return_value = json.dumps(enhancement_json)

        agent = BriefEnhancerAgent(client=mock_anthropic_client)
        suggestions = agent.suggest_enhancements_only(weak_brief, low_quality_report)

        assert suggestions == enhancement_json

    def test_suggest_filters_need_client_input(
        self, weak_brief, low_quality_report, mock_anthropic_client
    ):
        """Test suggest filters out NEED_CLIENT_INPUT values"""
        enhancement_json = {
            "business_description": "Enhanced description",
            "target_platforms": "NEED_CLIENT_INPUT",
        }
        mock_anthropic_client.create_message.return_value = json.dumps(enhancement_json)

        agent = BriefEnhancerAgent(client=mock_anthropic_client)
        suggestions = agent.suggest_enhancements_only(weak_brief, low_quality_report)

        # Should only include real suggestions
        assert "business_description" in suggestions
        assert "target_platforms" not in suggestions

    def test_suggest_returns_empty_on_error(
        self, weak_brief, low_quality_report, mock_anthropic_client
    ):
        """Test suggest returns empty dict on error"""
        mock_anthropic_client.create_message.side_effect = Exception("API Error")

        agent = BriefEnhancerAgent(client=mock_anthropic_client)
        suggestions = agent.suggest_enhancements_only(weak_brief, low_quality_report)

        assert suggestions == {}
