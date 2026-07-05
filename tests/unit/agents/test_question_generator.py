"""Tests for Question Generator Agent"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.agents.question_generator import QuestionGeneratorAgent
from src.models.brief_quality import BriefQualityReport, FieldQuality
from src.models.client_brief import ClientBrief
from src.models.question import QuestionType


@pytest.fixture
def mock_anthropic_client():
    """Create mock Anthropic client"""
    return MagicMock()


@pytest.fixture
def sample_brief():
    """Create a sample client brief"""
    return ClientBrief(
        company_name="Test Company",
        business_description="We sell software solutions",
        ideal_customer="Small businesses",
        main_problem_solved="Inefficiency",
    )


@pytest.fixture
def minimal_brief():
    """Create a minimal brief with only required fields"""
    return ClientBrief(
        company_name="Minimal Co",
        business_description="Software",
        ideal_customer="Businesses",
        main_problem_solved="Problems",
    )


@pytest.fixture
def quality_report_missing_critical():
    """Quality report with missing critical fields (weight >= 0.8)"""
    return BriefQualityReport(
        overall_score=0.50,
        completeness_score=0.60,
        specificity_score=0.40,
        usability_score=0.50,
        field_quality={
            "company_name": FieldQuality.STRONG,
            "business_description": FieldQuality.MISSING,  # weight 1.0
            "ideal_customer": FieldQuality.MISSING,  # weight 1.0
            "customer_pain_points": FieldQuality.MISSING,  # weight 0.8
        },
        missing_fields=["business_description", "ideal_customer", "customer_pain_points"],
        weak_fields=[],
        strong_fields=["company_name"],
        priority_improvements=["Add business description", "Define ideal customer"],
        can_generate_content=False,
        minimum_questions_needed=3,
        total_fields=10,
        filled_fields=4,
        required_fields_filled=1,
    )


@pytest.fixture
def quality_report_weak_important():
    """Quality report with weak important fields (weight >= 0.6)"""
    return BriefQualityReport(
        overall_score=0.60,
        completeness_score=0.70,
        specificity_score=0.50,
        usability_score=0.60,
        field_quality={
            "company_name": FieldQuality.STRONG,
            "business_description": FieldQuality.WEAK,  # weight 1.0
            "ideal_customer": FieldQuality.WEAK,  # weight 1.0
            "customer_pain_points": FieldQuality.WEAK,  # weight 0.8
            "key_phrases": FieldQuality.WEAK,  # weight 0.7
            "main_cta": FieldQuality.WEAK,  # weight 0.6
        },
        missing_fields=[],
        weak_fields=[
            "business_description",
            "ideal_customer",
            "customer_pain_points",
            "key_phrases",
            "main_cta",
        ],
        strong_fields=["company_name"],
        priority_improvements=[
            "Improve business description",
            "Be more specific about ideal customer",
        ],
        can_generate_content=False,
        minimum_questions_needed=4,
        total_fields=10,
        filled_fields=8,
        required_fields_filled=4,
    )


@pytest.fixture
def quality_report_optional_only():
    """Quality report with only optional fields missing"""
    return BriefQualityReport(
        overall_score=0.75,
        completeness_score=0.80,
        specificity_score=0.70,
        usability_score=0.75,
        field_quality={
            "company_name": FieldQuality.STRONG,
            "business_description": FieldQuality.STRONG,
            "ideal_customer": FieldQuality.STRONG,
            "stories": FieldQuality.MISSING,  # weight 0.7, optional
            "misconceptions": FieldQuality.MISSING,  # weight 0.5, optional
            "case_studies": FieldQuality.MISSING,  # weight 0.4, optional
        },
        missing_fields=["stories", "misconceptions", "case_studies"],
        weak_fields=[],
        strong_fields=["company_name", "business_description", "ideal_customer"],
        priority_improvements=[],
        can_generate_content=True,
        minimum_questions_needed=0,
        total_fields=10,
        filled_fields=7,
        required_fields_filled=4,
    )


class TestInitialization:
    """Test agent initialization"""

    def test_init_with_client(self, mock_anthropic_client):
        """Test initialization with provided client"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)
        assert agent.client == mock_anthropic_client

    def test_init_without_client(self):
        """Test initialization creates default client"""
        with patch("src.agents.question_generator.AnthropicClient") as mock_client_class:
            agent = QuestionGeneratorAgent()
            mock_client_class.assert_called_once()
            assert agent.client == mock_client_class.return_value


class TestGenerateQuestions:
    """Test generate_questions method"""

    def test_generate_questions_missing_critical_fields(
        self, sample_brief, quality_report_missing_critical, mock_anthropic_client
    ):
        """Test generates questions for missing critical fields (weight >= 0.8)"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        questions = agent.generate_questions(
            sample_brief, quality_report_missing_critical, max_questions=5
        )

        # Should have 3 questions for 3 missing critical fields
        assert len(questions) == 3

        # Check all are priority 1 (critical)
        assert all(q.priority == 1 for q in questions)

        # Check all are open-ended (not clarifying)
        assert all(q.question_type == QuestionType.OPEN_ENDED for q in questions)

        # Check field names
        field_names = {q.field_name for q in questions}
        assert field_names == {"business_description", "ideal_customer", "customer_pain_points"}

    def test_generate_questions_weak_important_fields(self, mock_anthropic_client):
        """Test generates clarifying questions for weak important fields (weight >= 0.6)"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        # Create brief with values for all weak fields so they generate clarifying questions
        brief_with_values = ClientBrief(
            company_name="Test Company",
            business_description="We sell software solutions",
            ideal_customer="Small businesses",
            main_problem_solved="Inefficiency",
            customer_pain_points=["Generic pain point"],  # Has value
            key_phrases=["Some phrase"],  # Has value
            main_cta="Contact us",  # Has value
        )

        # Quality report with these fields marked as weak
        quality_report = BriefQualityReport(
            overall_score=0.60,
            completeness_score=0.70,
            specificity_score=0.50,
            usability_score=0.60,
            field_quality={
                "company_name": FieldQuality.STRONG,
                "business_description": FieldQuality.WEAK,  # weight 1.0
                "ideal_customer": FieldQuality.WEAK,  # weight 1.0
                "customer_pain_points": FieldQuality.WEAK,  # weight 0.8
                "key_phrases": FieldQuality.WEAK,  # weight 0.7
                "main_cta": FieldQuality.WEAK,  # weight 0.6
            },
            missing_fields=[],
            weak_fields=[
                "business_description",
                "ideal_customer",
                "customer_pain_points",
                "key_phrases",
                "main_cta",
            ],
            strong_fields=["company_name"],
            priority_improvements=[
                "Improve business description",
                "Be more specific about ideal customer",
            ],
            can_generate_content=False,
            minimum_questions_needed=4,
            total_fields=10,
            filled_fields=8,
            required_fields_filled=4,
        )

        questions = agent.generate_questions(brief_with_values, quality_report, max_questions=5)

        # Should have 5 weak fields, limited to max_questions
        assert len(questions) == 5

        # Check all are priority 2 (important)
        assert all(q.priority == 2 for q in questions)

        # Check all are clarifying (since fields have values and are weak)
        assert all(q.question_type == QuestionType.CLARIFYING for q in questions)

    def test_generate_questions_optional_enrichment(
        self, sample_brief, quality_report_optional_only, mock_anthropic_client
    ):
        """Test generates optional enrichment questions"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        questions = agent.generate_questions(
            sample_brief, quality_report_optional_only, max_questions=5
        )

        # Should have optional questions from stories, misconceptions, case_studies
        assert len(questions) >= 1
        assert len(questions) <= 3  # Only 3 optional fields missing

        # Check all are priority 3 (optional)
        assert all(q.priority == 3 for q in questions)

        # Check field names are from optional list
        field_names = {q.field_name for q in questions}
        assert field_names.issubset(
            {"stories", "misconceptions", "case_studies", "measurable_results"}
        )

    def test_generate_questions_respects_max_limit(
        self, sample_brief, quality_report_missing_critical, mock_anthropic_client
    ):
        """Test max_questions limits output"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        questions = agent.generate_questions(
            sample_brief, quality_report_missing_critical, max_questions=2
        )

        # Should limit to 2 even though 3 critical fields missing
        assert len(questions) == 2

    def test_generate_questions_priority_sorting(self, sample_brief, mock_anthropic_client):
        """Test questions are sorted by priority"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        # Create report with mixed priorities
        mixed_report = BriefQualityReport(
            overall_score=0.60,
            completeness_score=0.70,
            specificity_score=0.50,
            usability_score=0.60,
            field_quality={
                "company_name": FieldQuality.STRONG,
                "business_description": FieldQuality.MISSING,  # priority 1
                "key_phrases": FieldQuality.WEAK,  # priority 2
                "stories": FieldQuality.MISSING,  # priority 3 (optional)
            },
            missing_fields=["business_description", "stories"],
            weak_fields=["key_phrases"],
            strong_fields=["company_name"],
            priority_improvements=["Add business description"],
            can_generate_content=False,
            minimum_questions_needed=2,
            total_fields=10,
            filled_fields=6,
            required_fields_filled=3,
        )

        questions = agent.generate_questions(sample_brief, mixed_report, max_questions=10)

        # Should be sorted priority 1 → 2 → 3
        priorities = [q.priority for q in questions]
        assert priorities == sorted(priorities)

        # First question should be priority 1
        assert questions[0].priority == 1

    def test_generate_questions_empty_quality_report(self, sample_brief, mock_anthropic_client):
        """Test handles empty quality report (no missing or weak fields)"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        empty_report = BriefQualityReport(
            overall_score=0.95,
            completeness_score=0.95,
            specificity_score=0.95,
            usability_score=0.95,
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

        questions = agent.generate_questions(sample_brief, empty_report)

        # Should return empty list
        assert questions == []


class TestGenerateQuestionForField:
    """Test _generate_question_for_field method"""

    def test_generate_question_with_template(self, sample_brief, mock_anthropic_client):
        """Test generates question when template exists"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        question = agent._generate_question_for_field(
            "business_description", sample_brief, priority=1, is_clarifying=False
        )

        assert question is not None
        assert question.field_name == "business_description"
        assert question.priority == 1
        assert question.question_type == QuestionType.OPEN_ENDED
        assert question.example_answer is not None
        assert "business" in question.text.lower()

    def test_generate_question_no_template(self, sample_brief, mock_anthropic_client):
        """Test returns None when template not found"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        question = agent._generate_question_for_field(
            "nonexistent_field", sample_brief, priority=1, is_clarifying=False
        )

        assert question is None

    def test_generate_clarifying_question(self, sample_brief, mock_anthropic_client):
        """Test generates clarifying question for existing value"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        question = agent._generate_question_for_field(
            "business_description", sample_brief, priority=2, is_clarifying=True
        )

        assert question is not None
        assert question.question_type == QuestionType.CLARIFYING
        # Should include current value in question text
        assert sample_brief.business_description in question.text
        assert "You mentioned" in question.text or "more specific" in question.text.lower()

    def test_generate_open_ended_question(self, sample_brief, mock_anthropic_client):
        """Test generates open-ended question for missing field"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        question = agent._generate_question_for_field(
            "ideal_customer", sample_brief, priority=1, is_clarifying=False
        )

        assert question is not None
        assert question.question_type == QuestionType.OPEN_ENDED
        assert question.context == "Missing: ideal_customer"

    def test_generate_question_includes_example(self, sample_brief, mock_anthropic_client):
        """Test generated question includes example answer"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        question = agent._generate_question_for_field(
            "ideal_customer", sample_brief, priority=1, is_clarifying=False
        )

        assert question is not None
        assert question.example_answer is not None
        # Example should be from template
        assert len(question.example_answer) > 0


class TestGenerateFollowUpQuestion:
    """Test generate_follow_up_question method"""

    def test_generate_follow_up_needs_clarification(self, sample_brief, mock_anthropic_client):
        """Test generates follow-up when answer is vague"""
        # Mock API response indicating need for follow-up
        follow_up_json = {
            "needs_followup": True,
            "reason": "Answer is too generic",
            "suggested_question": "Can you be more specific about your target industry?",
        }
        mock_anthropic_client.create_message.return_value = json.dumps(follow_up_json)

        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        question = agent.generate_follow_up_question(
            "ideal_customer", "Small businesses", sample_brief
        )

        assert question is not None
        assert question.field_name == "ideal_customer"
        assert question.question_type == QuestionType.CLARIFYING
        assert question.priority == 2
        assert question.text == follow_up_json["suggested_question"]
        assert question.context == follow_up_json["reason"]

        # Should call API
        mock_anthropic_client.create_message.assert_called_once()

    def test_generate_follow_up_answer_sufficient(self, sample_brief, mock_anthropic_client):
        """Test returns None when answer is sufficient"""
        # Mock API response indicating no follow-up needed
        no_followup_json = {"needs_followup": False, "reason": "Answer is detailed and specific"}
        mock_anthropic_client.create_message.return_value = json.dumps(no_followup_json)

        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        question = agent.generate_follow_up_question(
            "ideal_customer",
            "VP of Sales at B2B SaaS companies with $2-10M ARR struggling to hit quota",
            sample_brief,
        )

        assert question is None
        mock_anthropic_client.create_message.assert_called_once()

    def test_generate_follow_up_handles_api_error(self, sample_brief, mock_anthropic_client):
        """Test handles API errors gracefully"""
        # Mock API error
        mock_anthropic_client.create_message.side_effect = Exception("API Error")

        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        question = agent.generate_follow_up_question("ideal_customer", "Some answer", sample_brief)

        # Should return None on error
        assert question is None

    def test_generate_follow_up_includes_context(self, sample_brief, mock_anthropic_client):
        """Test follow-up includes field name and answer in prompt"""
        mock_anthropic_client.create_message.return_value = json.dumps(
            {"needs_followup": False, "reason": "Good"}
        )

        agent = QuestionGeneratorAgent(client=mock_anthropic_client)
        agent.generate_follow_up_question("ideal_customer", "Test answer", sample_brief)

        # Check prompt included field and answer
        call_args = mock_anthropic_client.create_message.call_args
        messages = call_args.kwargs["messages"]
        prompt = messages[0]["content"]

        assert "ideal_customer" in prompt
        assert "Test answer" in prompt


class TestExtractJson:
    """Test _extract_json method"""

    def test_extract_json_plain_text(self, mock_anthropic_client):
        """Test extracts JSON from plain text"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        response = '{"field1": "value1", "field2": 123}'
        result = agent._extract_json(response)

        assert result == {"field1": "value1", "field2": 123}

    def test_extract_json_code_block(self, mock_anthropic_client):
        """Test extracts JSON from markdown code block"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        response = """Here's the result:

```json
{
  "needs_followup": true,
  "reason": "Too vague"
}
```

That's the analysis."""

        result = agent._extract_json(response)

        assert result == {"needs_followup": True, "reason": "Too vague"}

    def test_extract_json_plain_code_block(self, mock_anthropic_client):
        """Test extracts JSON from plain code block (no json tag)"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        response = """```
{"field": "value"}
```"""

        result = agent._extract_json(response)

        assert result == {"field": "value"}

    def test_extract_json_with_whitespace(self, mock_anthropic_client):
        """Test extracts JSON with extra whitespace"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        response = """

        {"field": "value"}

        """

        result = agent._extract_json(response)

        assert result == {"field": "value"}

    def test_extract_json_raises_on_invalid(self, mock_anthropic_client):
        """Test raises ValueError on invalid JSON"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        response = "This is not JSON at all"

        with pytest.raises(ValueError, match="Invalid JSON"):
            agent._extract_json(response)

    def test_extract_json_raises_on_malformed(self, mock_anthropic_client):
        """Test raises ValueError on malformed JSON"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        response = '{"field": "value"'  # Missing closing brace

        with pytest.raises(ValueError, match="Invalid JSON"):
            agent._extract_json(response)


class TestQuestionTemplates:
    """Test QUESTION_TEMPLATES constant"""

    def test_all_templates_have_text_and_example(self):
        """Test all templates have required fields"""
        agent = QuestionGeneratorAgent()

        for field_name, template in agent.QUESTION_TEMPLATES.items():
            assert "text" in template, f"{field_name} missing 'text'"
            assert "example" in template, f"{field_name} missing 'example'"
            assert isinstance(template["text"], str)
            assert isinstance(template["example"], str)
            assert len(template["text"]) > 0
            assert len(template["example"]) > 0

    def test_field_weights_match_templates(self):
        """Test FIELD_WEIGHTS covers all template fields"""
        agent = QuestionGeneratorAgent()

        # Not all templates need weights, but check major ones
        important_fields = ["business_description", "ideal_customer", "customer_pain_points"]

        for field in important_fields:
            assert field in agent.FIELD_WEIGHTS, f"{field} not in FIELD_WEIGHTS"
            assert agent.FIELD_WEIGHTS[field] > 0


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_generate_questions_with_zero_max(
        self, sample_brief, quality_report_missing_critical, mock_anthropic_client
    ):
        """Test max_questions=0 returns empty list"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        questions = agent.generate_questions(
            sample_brief, quality_report_missing_critical, max_questions=0
        )

        assert questions == []

    def test_generate_questions_with_large_max(
        self, sample_brief, quality_report_optional_only, mock_anthropic_client
    ):
        """Test large max_questions doesn't exceed available questions"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        questions = agent.generate_questions(
            sample_brief, quality_report_optional_only, max_questions=100
        )

        # Should only have questions for available optional fields
        assert len(questions) <= 4  # stories, misconceptions, case_studies, measurable_results

    def test_generate_follow_up_with_invalid_json_response(
        self, sample_brief, mock_anthropic_client
    ):
        """Test handles invalid JSON response from API"""
        # Return invalid JSON
        mock_anthropic_client.create_message.return_value = "Not JSON at all"

        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        question = agent.generate_follow_up_question("ideal_customer", "Some answer", sample_brief)

        # Should return None when JSON parsing fails
        assert question is None

    def test_clarifying_question_without_current_value(self, minimal_brief, mock_anthropic_client):
        """Test clarifying question when field exists but is empty/minimal"""
        agent = QuestionGeneratorAgent(client=mock_anthropic_client)

        # minimal_brief.business_description is "Software" (very short)
        question = agent._generate_question_for_field(
            "business_description", minimal_brief, priority=2, is_clarifying=True
        )

        assert question is not None
        assert question.question_type == QuestionType.CLARIFYING
        # Should include the short value in clarifying question
        assert "Software" in question.text
