"""Unit tests for template module.

Tests cover:
- TemplateDifficulty enum
- TemplateType enum
- Template model creation
- get_required_context_fields() method
- can_be_filled() method
"""

from src.models.template import (
    TemplateDifficulty,
    TemplateType,
    Template,
)


class TestTemplateDifficulty:
    """Tests for TemplateDifficulty enum."""

    def test_fast_value(self):
        """Test FAST difficulty value."""
        assert TemplateDifficulty.FAST.value == "fast"

    def test_medium_value(self):
        """Test MEDIUM difficulty value."""
        assert TemplateDifficulty.MEDIUM.value == "medium"

    def test_slow_value(self):
        """Test SLOW difficulty value."""
        assert TemplateDifficulty.SLOW.value == "slow"

    def test_all_difficulties(self):
        """Test all difficulty values exist."""
        difficulties = [d for d in TemplateDifficulty]
        assert len(difficulties) == 3


class TestTemplateType:
    """Tests for TemplateType enum."""

    def test_expected_types_exist(self):
        """Test that expected template types exist."""
        expected = [
            "problem_recognition",
            "statistic",
            "contrarian",
            "evolution",
            "question",
            "story",
            "myth_busting",
            "vulnerability",
            "how_to",
            "comparison",
            "learning",
            "behind_scenes",
            "future",
            "q_and_a",
            "milestone",
        ]
        for type_name in expected:
            assert TemplateType(type_name) is not None

    def test_template_type_count(self):
        """Test total number of template types."""
        types = [t for t in TemplateType]
        assert len(types) == 15


class TestTemplateModel:
    """Tests for Template model."""

    def test_create_basic_template(self):
        """Test creating a basic template."""
        template = Template(
            template_id=1,
            name="Problem Recognition",
            template_type=TemplateType.PROBLEM_RECOGNITION,
            structure="[PROBLEM] is something [AUDIENCE] struggles with...",
            best_for="Creating awareness",
            difficulty=TemplateDifficulty.FAST,
        )

        assert template.template_id == 1
        assert template.name == "Problem Recognition"
        assert template.template_type == TemplateType.PROBLEM_RECOGNITION
        assert template.difficulty == TemplateDifficulty.FAST
        assert template.requires_story is False
        assert template.requires_data is False
        assert template.requires_question is False

    def test_create_template_with_requirements(self):
        """Test creating template with special requirements."""
        template = Template(
            template_id=6,
            name="Personal Story",
            template_type=TemplateType.STORY,
            structure="Let me share a story about [CLIENT_EXPERIENCE]...",
            best_for="Building connection",
            difficulty=TemplateDifficulty.SLOW,
            requires_story=True,
        )

        assert template.requires_story is True
        assert template.requires_data is False

    def test_create_template_with_data_requirement(self):
        """Test creating template requiring data."""
        template = Template(
            template_id=2,
            name="Statistic + Insight",
            template_type=TemplateType.STATISTIC,
            structure="[STATISTIC]% of [AUDIENCE] experience [PROBLEM]...",
            best_for="Credibility and authority",
            difficulty=TemplateDifficulty.FAST,
            requires_data=True,
        )

        assert template.requires_data is True

    def test_create_template_with_question_requirement(self):
        """Test creating template requiring customer question."""
        template = Template(
            template_id=14,
            name="Reader Q Response",
            template_type=TemplateType.Q_AND_A,
            structure="A reader asked: [CUSTOMER_QUESTION]. Here's my answer...",
            best_for="Community building",
            difficulty=TemplateDifficulty.MEDIUM,
            requires_question=True,
        )

        assert template.requires_question is True

    def test_create_template_with_all_requirements(self):
        """Test creating template with all requirements."""
        template = Template(
            template_id=99,
            name="Complex Template",
            template_type=TemplateType.STORY,
            structure="...",
            best_for="Testing",
            difficulty=TemplateDifficulty.SLOW,
            requires_story=True,
            requires_data=True,
            requires_question=True,
        )

        assert template.requires_story is True
        assert template.requires_data is True
        assert template.requires_question is True

    def test_template_with_example(self):
        """Test template with example content."""
        template = Template(
            template_id=1,
            name="Test Template",
            template_type=TemplateType.PROBLEM_RECOGNITION,
            structure="[HOOK] [PROBLEM]",
            example="Ever wondered why marketing feels so hard?",
            best_for="Testing",
            difficulty=TemplateDifficulty.FAST,
        )

        assert template.example == "Ever wondered why marketing feels so hard?"

    def test_template_with_placeholder_fields(self):
        """Test template with placeholder fields list."""
        template = Template(
            template_id=1,
            name="Test Template",
            template_type=TemplateType.HOW_TO,
            structure="[HOOK] [PROBLEM] [SOLUTION]",
            best_for="Testing",
            difficulty=TemplateDifficulty.MEDIUM,
            placeholder_fields=["HOOK", "PROBLEM", "SOLUTION"],
        )

        assert template.placeholder_fields == ["HOOK", "PROBLEM", "SOLUTION"]


class TestGetRequiredContextFields:
    """Tests for get_required_context_fields() method."""

    def test_basic_template_required_fields(self):
        """Test basic template returns base required fields."""
        template = Template(
            template_id=1,
            name="Basic",
            template_type=TemplateType.PROBLEM_RECOGNITION,
            structure="...",
            best_for="Testing",
            difficulty=TemplateDifficulty.FAST,
        )

        required = template.get_required_context_fields()

        assert "company_name" in required
        assert "ideal_customer" in required
        assert "problem_solved" in required
        assert "brand_voice" in required
        assert "stories" not in required
        assert "statistics" not in required

    def test_story_template_requires_stories(self):
        """Test story template includes stories field."""
        template = Template(
            template_id=6,
            name="Story",
            template_type=TemplateType.STORY,
            structure="...",
            best_for="Testing",
            difficulty=TemplateDifficulty.SLOW,
            requires_story=True,
        )

        required = template.get_required_context_fields()

        assert "stories" in required

    def test_data_template_requires_statistics(self):
        """Test data template includes statistics field."""
        template = Template(
            template_id=2,
            name="Statistic",
            template_type=TemplateType.STATISTIC,
            structure="...",
            best_for="Testing",
            difficulty=TemplateDifficulty.FAST,
            requires_data=True,
        )

        required = template.get_required_context_fields()

        assert "statistics" in required

    def test_question_template_requires_questions(self):
        """Test Q&A template includes customer_questions field."""
        template = Template(
            template_id=14,
            name="Q&A",
            template_type=TemplateType.Q_AND_A,
            structure="...",
            best_for="Testing",
            difficulty=TemplateDifficulty.MEDIUM,
            requires_question=True,
        )

        required = template.get_required_context_fields()

        assert "customer_questions" in required

    def test_template_with_all_requirements(self):
        """Test template with all requirements includes all fields."""
        template = Template(
            template_id=99,
            name="Complex",
            template_type=TemplateType.STORY,
            structure="...",
            best_for="Testing",
            difficulty=TemplateDifficulty.SLOW,
            requires_story=True,
            requires_data=True,
            requires_question=True,
        )

        required = template.get_required_context_fields()

        assert "stories" in required
        assert "statistics" in required
        assert "customer_questions" in required


class TestCanBeFilled:
    """Tests for can_be_filled() method."""

    class MockBrief:
        """Mock client brief for testing."""

        def __init__(self, stories=None, customer_questions=None):
            self.stories = stories or []
            self.customer_questions = customer_questions or []

    def test_basic_template_can_be_filled(self):
        """Test basic template can always be filled."""
        template = Template(
            template_id=1,
            name="Basic",
            template_type=TemplateType.PROBLEM_RECOGNITION,
            structure="...",
            best_for="Testing",
            difficulty=TemplateDifficulty.FAST,
        )

        brief = self.MockBrief()
        can_fill, missing = template.can_be_filled(brief)

        assert can_fill is True
        assert missing == []

    def test_story_template_without_stories(self):
        """Test story template cannot be filled without stories."""
        template = Template(
            template_id=6,
            name="Story",
            template_type=TemplateType.STORY,
            structure="...",
            best_for="Testing",
            difficulty=TemplateDifficulty.SLOW,
            requires_story=True,
        )

        brief = self.MockBrief(stories=[])
        can_fill, missing = template.can_be_filled(brief)

        assert can_fill is False
        assert "client stories" in missing

    def test_story_template_with_stories(self):
        """Test story template can be filled with stories."""
        template = Template(
            template_id=6,
            name="Story",
            template_type=TemplateType.STORY,
            structure="...",
            best_for="Testing",
            difficulty=TemplateDifficulty.SLOW,
            requires_story=True,
        )

        brief = self.MockBrief(stories=["A story about success"])
        can_fill, missing = template.can_be_filled(brief)

        assert can_fill is True
        assert missing == []

    def test_question_template_without_questions(self):
        """Test Q&A template cannot be filled without questions."""
        template = Template(
            template_id=14,
            name="Q&A",
            template_type=TemplateType.Q_AND_A,
            structure="...",
            best_for="Testing",
            difficulty=TemplateDifficulty.MEDIUM,
            requires_question=True,
        )

        brief = self.MockBrief(customer_questions=[])
        can_fill, missing = template.can_be_filled(brief)

        assert can_fill is False
        assert "customer questions" in missing

    def test_question_template_with_questions(self):
        """Test Q&A template can be filled with questions."""
        template = Template(
            template_id=14,
            name="Q&A",
            template_type=TemplateType.Q_AND_A,
            structure="...",
            best_for="Testing",
            difficulty=TemplateDifficulty.MEDIUM,
            requires_question=True,
        )

        brief = self.MockBrief(customer_questions=["How do I start?"])
        can_fill, missing = template.can_be_filled(brief)

        assert can_fill is True
        assert missing == []

    def test_template_with_multiple_requirements_all_missing(self):
        """Test template with multiple requirements, all missing."""
        template = Template(
            template_id=99,
            name="Complex",
            template_type=TemplateType.STORY,
            structure="...",
            best_for="Testing",
            difficulty=TemplateDifficulty.SLOW,
            requires_story=True,
            requires_question=True,
        )

        brief = self.MockBrief(stories=[], customer_questions=[])
        can_fill, missing = template.can_be_filled(brief)

        assert can_fill is False
        assert "client stories" in missing
        assert "customer questions" in missing

    def test_template_with_multiple_requirements_partial_available(self):
        """Test template with multiple requirements, some available."""
        template = Template(
            template_id=99,
            name="Complex",
            template_type=TemplateType.STORY,
            structure="...",
            best_for="Testing",
            difficulty=TemplateDifficulty.SLOW,
            requires_story=True,
            requires_question=True,
        )

        brief = self.MockBrief(stories=["A story"], customer_questions=[])
        can_fill, missing = template.can_be_filled(brief)

        assert can_fill is False
        assert "client stories" not in missing
        assert "customer questions" in missing

    def test_template_with_multiple_requirements_all_available(self):
        """Test template with multiple requirements, all available."""
        template = Template(
            template_id=99,
            name="Complex",
            template_type=TemplateType.STORY,
            structure="...",
            best_for="Testing",
            difficulty=TemplateDifficulty.SLOW,
            requires_story=True,
            requires_question=True,
        )

        brief = self.MockBrief(stories=["A story"], customer_questions=["A question"])
        can_fill, missing = template.can_be_filled(brief)

        assert can_fill is True
        assert missing == []
