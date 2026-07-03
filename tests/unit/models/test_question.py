"""Tests for Question Model"""

import pytest
from pydantic import ValidationError

from src.models.question import Question, QuestionType


class TestQuestionType:
    """Test QuestionType enum"""

    def test_enum_values(self):
        """Test all enum values are accessible"""
        assert QuestionType.OPEN_ENDED == "open_ended"
        assert QuestionType.SPECIFIC == "specific"
        assert QuestionType.CLARIFYING == "clarifying"
        assert QuestionType.CHOICE == "choice"

    def test_enum_members(self):
        """Test enum members list"""
        values = {member.value for member in QuestionType}
        assert values == {"open_ended", "specific", "clarifying", "choice"}


class TestQuestion:
    """Test Question model"""

    def test_create_minimal_question(self):
        """Test creating question with minimal required fields"""
        question = Question(
            text="What is your company name?",
            field_name="company_name",
            question_type=QuestionType.SPECIFIC,
            priority=1,
        )

        assert question.text == "What is your company name?"
        assert question.field_name == "company_name"
        assert question.question_type == QuestionType.SPECIFIC
        assert question.priority == 1
        assert question.context is None
        assert question.example_answer is None

    def test_create_full_question(self):
        """Test creating question with all fields"""
        question = Question(
            text="Tell me about your ideal customer",
            field_name="ideal_customer",
            question_type=QuestionType.OPEN_ENDED,
            context="Need more detail about target audience",
            example_answer="VP of Sales at B2B SaaS companies with $2-10M ARR",
            priority=1,
        )

        assert question.text == "Tell me about your ideal customer"
        assert question.field_name == "ideal_customer"
        assert question.question_type == QuestionType.OPEN_ENDED
        assert question.context == "Need more detail about target audience"
        assert question.example_answer == "VP of Sales at B2B SaaS companies with $2-10M ARR"
        assert question.priority == 1

    def test_all_question_types(self):
        """Test creating questions with all enum types"""
        types_to_test = [
            QuestionType.OPEN_ENDED,
            QuestionType.SPECIFIC,
            QuestionType.CLARIFYING,
            QuestionType.CHOICE,
        ]

        for qtype in types_to_test:
            question = Question(
                text="Test question",
                field_name="test_field",
                question_type=qtype,
                priority=2,
            )
            assert question.question_type == qtype

    def test_priority_levels(self):
        """Test all priority levels (1=critical, 2=important, 3=nice-to-have)"""
        for priority in [1, 2, 3]:
            question = Question(
                text="Test question",
                field_name="test_field",
                question_type=QuestionType.SPECIFIC,
                priority=priority,
            )
            assert question.priority == priority


class TestQuestionValidation:
    """Test Pydantic validation constraints"""

    def test_priority_must_be_1_to_3(self):
        """Test priority must be between 1 and 3"""
        # Priority 0 - too low
        with pytest.raises(ValidationError) as exc_info:
            Question(
                text="Test",
                field_name="test",
                question_type=QuestionType.SPECIFIC,
                priority=0,  # Invalid
            )
        assert "priority" in str(exc_info.value)

        # Priority 4 - too high
        with pytest.raises(ValidationError) as exc_info:
            Question(
                text="Test",
                field_name="test",
                question_type=QuestionType.SPECIFIC,
                priority=4,  # Invalid
            )
        assert "priority" in str(exc_info.value)

    def test_negative_priority_invalid(self):
        """Test negative priority is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            Question(
                text="Test",
                field_name="test",
                question_type=QuestionType.SPECIFIC,
                priority=-1,  # Invalid
            )
        assert "priority" in str(exc_info.value)

    def test_boundary_priorities_valid(self):
        """Test boundary priority values (1 and 3) are valid"""
        # Priority 1 (minimum valid)
        q1 = Question(
            text="Test",
            field_name="test",
            question_type=QuestionType.SPECIFIC,
            priority=1,
        )
        assert q1.priority == 1

        # Priority 3 (maximum valid)
        q3 = Question(
            text="Test",
            field_name="test",
            question_type=QuestionType.SPECIFIC,
            priority=3,
        )
        assert q3.priority == 3


class TestToDisplayText:
    """Test to_display_text method"""

    def test_display_with_context_and_example(self):
        """Test display with both context and example"""
        question = Question(
            text="What is your main CTA?",
            field_name="main_cta",
            question_type=QuestionType.SPECIFIC,
            context="Need to know primary conversion goal",
            example_answer="Book a 15-minute demo call",
            priority=1,
        )

        display = question.to_display_text(show_context=True, show_example=True)

        assert "[Context: Need to know primary conversion goal]" in display
        assert "What is your main CTA?" in display
        assert "Example: Book a 15-minute demo call" in display

        # Check order
        lines = display.split("\n")
        assert len(lines) == 3
        assert lines[0].startswith("[Context:")
        assert lines[1] == "What is your main CTA?"
        assert lines[2].startswith("Example:")

    def test_display_without_context(self):
        """Test display without context (show_context=False)"""
        question = Question(
            text="What is your main CTA?",
            field_name="main_cta",
            question_type=QuestionType.SPECIFIC,
            context="Need to know primary conversion goal",
            example_answer="Book a 15-minute demo call",
            priority=1,
        )

        display = question.to_display_text(show_context=False, show_example=True)

        assert "[Context:" not in display
        assert "What is your main CTA?" in display
        assert "Example: Book a 15-minute demo call" in display

        lines = display.split("\n")
        assert len(lines) == 2

    def test_display_without_example(self):
        """Test display without example (show_example=False)"""
        question = Question(
            text="What is your main CTA?",
            field_name="main_cta",
            question_type=QuestionType.SPECIFIC,
            context="Need to know primary conversion goal",
            example_answer="Book a 15-minute demo call",
            priority=1,
        )

        display = question.to_display_text(show_context=True, show_example=False)

        assert "[Context: Need to know primary conversion goal]" in display
        assert "What is your main CTA?" in display
        assert "Example:" not in display

        lines = display.split("\n")
        assert len(lines) == 2

    def test_display_without_context_or_example(self):
        """Test display with both flags False"""
        question = Question(
            text="What is your main CTA?",
            field_name="main_cta",
            question_type=QuestionType.SPECIFIC,
            context="Need to know primary conversion goal",
            example_answer="Book a 15-minute demo call",
            priority=1,
        )

        display = question.to_display_text(show_context=False, show_example=False)

        assert "[Context:" not in display
        assert "Example:" not in display
        assert display == "What is your main CTA?"

    def test_display_minimal_question_no_context_no_example(self):
        """Test display when question has no context or example"""
        question = Question(
            text="What is your company name?",
            field_name="company_name",
            question_type=QuestionType.SPECIFIC,
            priority=1,
            # No context or example_answer
        )

        display = question.to_display_text(show_context=True, show_example=True)

        # Should only show text, no context or example lines
        assert display == "What is your company name?"
        assert "[Context:" not in display
        assert "Example:" not in display

    def test_display_with_context_no_example_field(self):
        """Test display when question has context but no example_answer field"""
        question = Question(
            text="Tell me about your business",
            field_name="business_description",
            question_type=QuestionType.OPEN_ENDED,
            context="Need more detail",
            priority=2,
            # No example_answer
        )

        display = question.to_display_text(show_context=True, show_example=True)

        assert "[Context: Need more detail]" in display
        assert "Tell me about your business" in display
        assert "Example:" not in display

        lines = display.split("\n")
        assert len(lines) == 2

    def test_display_with_example_no_context_field(self):
        """Test display when question has example but no context field"""
        question = Question(
            text="What is your target platform?",
            field_name="target_platforms",
            question_type=QuestionType.CHOICE,
            example_answer="LinkedIn and Blog",
            priority=2,
            # No context
        )

        display = question.to_display_text(show_context=True, show_example=True)

        assert "[Context:" not in display
        assert "What is your target platform?" in display
        assert "Example: LinkedIn and Blog" in display

        lines = display.split("\n")
        assert len(lines) == 2

    def test_display_default_parameters(self):
        """Test display with default parameters (both True)"""
        question = Question(
            text="What problem do you solve?",
            field_name="main_problem_solved",
            question_type=QuestionType.SPECIFIC,
            context="Need clarity on value proposition",
            example_answer="Reduce customer churn by 40%",
            priority=1,
        )

        # Call with defaults
        display = question.to_display_text()

        assert "[Context: Need clarity on value proposition]" in display
        assert "What problem do you solve?" in display
        assert "Example: Reduce customer churn by 40%" in display


class TestQuestionTypeInQuestion:
    """Test QuestionType usage in Question model"""

    def test_question_type_is_enum(self):
        """Test question_type field stores enum value"""
        question = Question(
            text="Test",
            field_name="test",
            question_type=QuestionType.CLARIFYING,
            priority=2,
        )

        assert isinstance(question.question_type, QuestionType)
        assert question.question_type == QuestionType.CLARIFYING
        assert question.question_type.value == "clarifying"

    def test_question_type_string_comparison(self):
        """Test question_type can be compared with strings"""
        question = Question(
            text="Test",
            field_name="test",
            question_type=QuestionType.OPEN_ENDED,
            priority=1,
        )

        assert question.question_type == "open_ended"
        assert question.question_type != "specific"
