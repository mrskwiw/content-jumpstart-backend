"""Tests for Interactive Mode"""

from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.cli.interactive_mode import InteractiveMode
from src.models.brief_quality import BriefQualityReport, FieldQuality
from src.models.client_brief import ClientBrief, Platform, TonePreference
from src.models.question import Question, QuestionType


@pytest.fixture
def sample_quality_report():
    """Create sample quality report for testing"""
    return BriefQualityReport(
        overall_score=0.85,
        completeness_score=0.9,
        specificity_score=0.8,
        usability_score=0.85,
        can_generate_content=True,
        total_fields=20,
        filled_fields=18,
        required_fields_filled=15,
        minimum_questions_needed=0,
        field_quality={
            "company_name": FieldQuality.STRONG,
            "business_description": FieldQuality.ADEQUATE,
        },
        missing_fields=[],
        weak_fields=[],
    )


class TestInteractiveModeInit:
    """Test InteractiveMode initialization"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    def test_init_creates_all_agents(
        self, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test initialization creates all required agents"""
        mode = InteractiveMode()

        assert mode.parser is not None
        assert mode.quality_checker is not None
        assert mode.question_generator is not None
        assert mode.enhancer is not None
        assert mode.client_brief is None
        assert mode.iteration_count == 0

        # Verify agents were created
        mock_parser.assert_called_once()
        mock_quality_checker.assert_called_once()
        mock_question_gen.assert_called_once()
        mock_enhancer.assert_called_once()


class TestLoadInitialBrief:
    """Test _load_initial_brief method"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Progress")
    @patch("src.cli.interactive_mode.console")
    def test_load_initial_brief_success(
        self,
        mock_console,
        mock_progress,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test loading initial brief successfully"""
        # Create mock brief
        sample_brief = ClientBrief(
            company_name="Test Company",
            business_description="Test business",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        # Mock parser
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_brief.return_value = sample_brief
        mock_parser.return_value = mock_parser_instance

        # Mock file reading
        with patch("pathlib.Path.read_text", return_value="Brief content"):
            mode = InteractiveMode()
            result = mode._load_initial_brief("tests/fixtures/sample_brief.txt")

        assert result.company_name == "Test Company"
        mock_parser_instance.parse_brief.assert_called_once_with("Brief content")
        mock_console.print.assert_called()

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Prompt")
    @patch("src.cli.interactive_mode.console")
    def test_load_initial_brief_failure_fallback(
        self,
        mock_console,
        mock_prompt,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test loading brief failure falls back to creating minimal brief"""
        # Mock parser to raise exception
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_brief.side_effect = Exception("Parse error")
        mock_parser.return_value = mock_parser_instance

        # Mock user prompts
        mock_prompt.ask.side_effect = ["Test Co", "Test biz", "Test customer", "Test problem"]

        with patch("pathlib.Path.read_text", return_value="Bad content"):
            mode = InteractiveMode()
            result = mode._load_initial_brief("bad_file.txt")

        assert result.company_name == "Test Co"
        assert "Failed to load brief" in str(mock_console.print.call_args_list)


class TestCreateMinimalBrief:
    """Test _create_minimal_brief method"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Prompt")
    @patch("src.cli.interactive_mode.console")
    def test_create_minimal_brief_with_all_answers(
        self,
        mock_console,
        mock_prompt,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test creating minimal brief with all answers provided"""
        mock_prompt.ask.side_effect = [
            "Test Company",
            "We do testing",
            "Test customers",
            "We solve test problems",
        ]

        mode = InteractiveMode()
        result = mode._create_minimal_brief()

        assert result.company_name == "Test Company"
        assert result.business_description == "We do testing"
        assert result.ideal_customer == "Test customers"
        assert result.main_problem_solved == "We solve test problems"

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Prompt")
    @patch("src.cli.interactive_mode.console")
    def test_create_minimal_brief_with_defaults(
        self,
        mock_console,
        mock_prompt,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test creating minimal brief with default empty values"""
        mock_prompt.ask.side_effect = ["Test Company", "", "", ""]

        mode = InteractiveMode()
        result = mode._create_minimal_brief()

        assert result.company_name == "Test Company"
        assert result.business_description == "No description provided"
        assert result.ideal_customer == "Not specified"
        assert result.main_problem_solved == "Not specified"


class TestParseListInput:
    """Test _parse_list_input method"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    def test_parse_comma_separated(
        self, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test parsing comma-separated list"""
        mode = InteractiveMode()
        result = mode._parse_list_input("item1, item2, item3")

        assert result == ["item1", "item2", "item3"]

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    def test_parse_newline_separated(
        self, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test parsing newline-separated list"""
        mode = InteractiveMode()
        result = mode._parse_list_input("- item1\n- item2\n- item3")

        assert result == ["item1", "item2", "item3"]

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    def test_parse_numbered_list(
        self, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test parsing numbered list"""
        mode = InteractiveMode()
        result = mode._parse_list_input("1. item1 2. item2 3. item3")

        assert "item1" in result
        assert "item2" in result
        assert "item3" in result

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    def test_parse_single_item(
        self, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test parsing single item"""
        mode = InteractiveMode()
        result = mode._parse_list_input("single item")

        assert result == ["single item"]


class TestUpdateBriefField:
    """Test _update_brief_field method"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_update_string_field(
        self, mock_console, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test updating a string field"""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Old desc",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        mode._update_brief_field("business_description", "New description")

        assert mode.client_brief.business_description == "New description"

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_update_string_field_append(
        self, mock_console, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test appending to string field"""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Old desc",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        mode._update_brief_field("business_description", "Additional info", append=True)

        assert mode.client_brief.business_description == "Old desc Additional info"

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_update_list_field(
        self, mock_console, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test updating a list field"""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        mode._update_brief_field("customer_pain_points", "pain1, pain2, pain3")

        assert len(mode.client_brief.customer_pain_points) == 3
        assert "pain1" in mode.client_brief.customer_pain_points

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_update_list_field_append(
        self, mock_console, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test appending to list field"""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
            customer_pain_points=["existing_pain"],
        )

        mode._update_brief_field("customer_pain_points", "new_pain", append=True)

        assert len(mode.client_brief.customer_pain_points) == 2
        assert "existing_pain" in mode.client_brief.customer_pain_points
        assert "new_pain" in mode.client_brief.customer_pain_points

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_update_brand_personality_field(
        self, mock_console, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test updating brand_personality enum field"""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        mode._update_brief_field("brand_personality", "conversational, direct")

        assert len(mode.client_brief.brand_personality) == 2
        assert TonePreference.CONVERSATIONAL in mode.client_brief.brand_personality
        assert TonePreference.DIRECT in mode.client_brief.brand_personality

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_update_target_platforms_field(
        self, mock_console, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test updating target_platforms enum field"""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        mode._update_brief_field("target_platforms", "linkedin, twitter")

        assert len(mode.client_brief.target_platforms) == 2
        assert Platform.LINKEDIN in mode.client_brief.target_platforms
        assert Platform.TWITTER in mode.client_brief.target_platforms


class TestAskSingleQuestion:
    """Test _ask_single_question method"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Prompt")
    @patch("src.cli.interactive_mode.console")
    def test_ask_question_with_answer(
        self,
        mock_console,
        mock_prompt,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test asking question and receiving answer (priority 3 - no follow-up)"""
        mock_prompt.ask.return_value = "Test answer"

        # Mock question generator to not generate follow-ups
        mock_question_gen_instance = MagicMock()
        mock_question_gen_instance.generate_follow_up_question.return_value = None
        mock_question_gen.return_value = mock_question_gen_instance

        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        question = Question(
            text="What's your business description?",
            field_name="business_description",
            question_type=QuestionType.OPEN_ENDED,
            priority=3,  # Priority 3 - no follow-up
        )

        mode._ask_single_question(question, 1, 1)

        assert mode.client_brief.business_description == "Test answer"
        mock_prompt.ask.assert_called()

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Prompt")
    @patch("src.cli.interactive_mode.console")
    def test_ask_question_skip(
        self,
        mock_console,
        mock_prompt,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test skipping a question"""
        mock_prompt.ask.return_value = "[skip]"

        # Mock question generator (not used but required)
        mock_question_gen_instance = MagicMock()
        mock_question_gen.return_value = mock_question_gen_instance

        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Original",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        question = Question(
            text="What's your business description?",
            field_name="business_description",
            question_type=QuestionType.OPEN_ENDED,
            priority=3,  # Priority 3 so no follow-up attempt
        )

        mode._ask_single_question(question, 1, 1)

        # Should not have changed
        assert mode.client_brief.business_description == "Original"

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Prompt")
    @patch("src.cli.interactive_mode.console")
    def test_ask_question_with_follow_up(
        self,
        mock_console,
        mock_prompt,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test asking question with follow-up"""
        mock_prompt.ask.side_effect = ["Test answer", "Follow-up answer"]

        # Mock follow-up question generation
        mock_question_gen_instance = MagicMock()
        follow_up = Question(
            text="Follow-up question?",
            field_name="business_description",
            question_type=QuestionType.CLARIFYING,
            priority=1,
        )
        mock_question_gen_instance.generate_follow_up_question.return_value = follow_up
        mock_question_gen.return_value = mock_question_gen_instance

        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        question = Question(
            text="What's your business description?",
            field_name="business_description",
            question_type=QuestionType.OPEN_ENDED,
            priority=1,
        )

        mode._ask_single_question(question, 1, 1)

        # Should have both answers combined
        assert "Test answer" in mode.client_brief.business_description
        assert "Follow-up answer" in mode.client_brief.business_description


class TestConfirmReady:
    """Test _confirm_ready method"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Confirm")
    @patch("src.cli.interactive_mode.console")
    def test_confirm_ready_proceed(
        self,
        mock_console,
        mock_confirm,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
        sample_quality_report,
    ):
        """Test user confirms ready to proceed"""
        mock_confirm.ask.return_value = True

        mode = InteractiveMode()

        result = mode._confirm_ready(sample_quality_report)

        assert result is True
        mock_confirm.ask.assert_called_once()

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Confirm")
    @patch("src.cli.interactive_mode.console")
    def test_confirm_ready_continue_improving(
        self,
        mock_console,
        mock_confirm,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
        sample_quality_report,
    ):
        """Test user wants to continue improving"""
        mock_confirm.ask.return_value = False

        mode = InteractiveMode()

        result = mode._confirm_ready(sample_quality_report)

        assert result is False


class TestSaveProgress:
    """Test _save_progress method"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_progress_success(
        self,
        mock_file,
        mock_mkdir,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test saving progress successfully"""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Company",
            business_description="Test",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        mode._save_progress()

        mock_mkdir.assert_called_once()
        mock_file.assert_called()
        # Check that filename contains company name
        call_args = mock_file.call_args[0][0]
        assert "Test_Company_wip.json" in str(call_args)


class TestSaveFinalBrief:
    """Test _save_final_brief method"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_final_brief_success(
        self,
        mock_file,
        mock_mkdir,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test saving final brief successfully"""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Company",
            business_description="Test business",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        result = mode._save_final_brief()

        mock_mkdir.assert_called_once()
        mock_file.assert_called()
        assert "Test_Company" in result
        assert "_complete.txt" in result


class TestFormatBriefAsText:
    """Test _format_brief_as_text method"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    def test_format_brief_minimal(
        self, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test formatting minimal brief"""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Company",
            business_description="We do testing",
            ideal_customer="Test customers",
            main_problem_solved="Test problems",
        )

        result = mode._format_brief_as_text()

        assert "# Client Brief - Test Company" in result
        assert "Company: Test Company" in result
        assert "Business: We do testing" in result
        assert "Ideal Customer: Test customers" in result
        assert "Problem Solved: Test problems" in result

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    def test_format_brief_with_optional_fields(
        self, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test formatting brief with optional fields"""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Company",
            business_description="We do testing",
            ideal_customer="Test customers",
            main_problem_solved="Test problems",
            founder_name="John Doe",
            website="https://example.com",
            brand_personality=[TonePreference.CONVERSATIONAL, TonePreference.DIRECT],
            key_phrases=["phrase1", "phrase2"],
            customer_pain_points=["pain1", "pain2"],
            customer_questions=["question1"],
            misconceptions=["myth1"],
            stories=["story1"],
            main_cta="Contact us",
        )

        result = mode._format_brief_as_text()

        assert "Founder: John Doe" in result
        assert "Website: https://example.com" in result
        assert "Personality:" in result
        assert "Key Phrases:" in result
        assert "Pain Points:" in result
        assert "- pain1" in result
        assert "Customer Questions:" in result
        assert "Misconceptions to Correct:" in result
        assert "Stories:" in result
        assert "Main CTA: Contact us" in result


class TestDisplayCompletion:
    """Test _display_completion method"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_display_completion(
        self,
        mock_console,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
        sample_quality_report,
    ):
        """Test displaying completion message"""
        # Mock quality checker
        mock_quality_checker_instance = MagicMock()
        mock_quality_checker_instance.assess_brief.return_value = sample_quality_report
        mock_quality_checker.return_value = mock_quality_checker_instance

        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Company",
            business_description="Test",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        mode._display_completion("data/briefs/Test_Company_complete.txt")

        # Check that completion message was printed
        assert mock_console.print.called


class TestConversationLoop:
    """Test _conversation_loop method"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Confirm")
    @patch("src.cli.interactive_mode.console")
    def test_conversation_loop_brief_ready(
        self,
        mock_console,
        mock_confirm,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
        sample_quality_report,
    ):
        """Test conversation loop when brief is ready"""
        # Mock quality checker to return ready status
        mock_quality_checker_instance = MagicMock()
        mock_quality_checker_instance.assess_brief.return_value = sample_quality_report
        mock_quality_checker.return_value = mock_quality_checker_instance

        # Mock user confirms ready
        mock_confirm.ask.return_value = True

        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        with patch.object(mode, "_save_progress"):
            mode._conversation_loop()

        assert mode.iteration_count == 1

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_conversation_loop_no_questions(
        self,
        mock_console,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
        sample_quality_report,
    ):
        """Test conversation loop when no questions generated"""
        # Create modified report with can_generate_content=False
        not_ready_report = BriefQualityReport(
            **{
                **sample_quality_report.model_dump(),
                "can_generate_content": False,
                "minimum_questions_needed": 2,
            }
        )

        # Mock quality checker
        mock_quality_checker_instance = MagicMock()
        mock_quality_checker_instance.assess_brief.return_value = not_ready_report
        mock_quality_checker.return_value = mock_quality_checker_instance

        # Mock question generator to return empty list
        mock_question_gen_instance = MagicMock()
        mock_question_gen_instance.generate_questions.return_value = []
        mock_question_gen.return_value = mock_question_gen_instance

        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        with patch.object(mode, "_save_progress"):
            mode._conversation_loop()

        # Should complete after 1 iteration
        assert mode.iteration_count == 1


class TestApplyFinalEnhancements:
    """Test _apply_final_enhancements method"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Progress")
    @patch("src.cli.interactive_mode.console")
    def test_apply_final_enhancements_success(
        self,
        mock_console,
        mock_progress,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
        sample_quality_report,
    ):
        """Test applying final enhancements successfully"""
        # Mock quality checker
        mock_quality_checker_instance = MagicMock()
        mock_quality_checker_instance.assess_brief.return_value = sample_quality_report
        mock_quality_checker.return_value = mock_quality_checker_instance

        # Mock enhancer
        enhanced_brief = ClientBrief(
            company_name="Test Co Enhanced",
            business_description="Enhanced description",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )
        mock_enhancer_instance = MagicMock()
        mock_enhancer_instance.enhance_brief.return_value = enhanced_brief
        mock_enhancer.return_value = mock_enhancer_instance

        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        mode._apply_final_enhancements()

        assert mode.client_brief.company_name == "Test Co Enhanced"
        mock_enhancer_instance.enhance_brief.assert_called_once()

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Progress")
    @patch("src.cli.interactive_mode.console")
    def test_apply_final_enhancements_failure(
        self,
        mock_console,
        mock_progress,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
        sample_quality_report,
    ):
        """Test handling enhancement failure"""
        # Mock quality checker
        mock_quality_checker_instance = MagicMock()
        mock_quality_checker_instance.assess_brief.return_value = sample_quality_report
        mock_quality_checker.return_value = mock_quality_checker_instance

        # Mock enhancer to raise exception
        mock_enhancer_instance = MagicMock()
        mock_enhancer_instance.enhance_brief.side_effect = Exception("Enhancement failed")
        mock_enhancer.return_value = mock_enhancer_instance

        mode = InteractiveMode()
        original_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )
        mode.client_brief = original_brief

        mode._apply_final_enhancements()

        # Brief should remain unchanged
        assert mode.client_brief == original_brief


class TestBriefProperty:
    """Test brief property accessor"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    def test_brief_property_raises_when_not_initialized(
        self, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test brief property raises RuntimeError when client_brief is None"""
        mode = InteractiveMode()
        mode.client_brief = None

        with pytest.raises(RuntimeError, match="Client brief not initialized"):
            _ = mode.brief


class TestAskQuestions:
    """Test _ask_questions method"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Prompt")
    @patch("src.cli.interactive_mode.console")
    def test_ask_questions_multiple(
        self,
        mock_console,
        mock_prompt,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test asking multiple questions"""
        mock_prompt.ask.side_effect = ["Answer 1", "Answer 2"]

        mock_question_gen_instance = MagicMock()
        mock_question_gen_instance.generate_follow_up_question.return_value = None
        mock_question_gen.return_value = mock_question_gen_instance

        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        questions = [
            Question(
                text="Question 1?",
                field_name="business_description",
                question_type=QuestionType.OPEN_ENDED,
                priority=3,
            ),
            Question(
                text="Question 2?",
                field_name="ideal_customer",
                question_type=QuestionType.OPEN_ENDED,
                priority=3,
            ),
        ]

        mode._ask_questions(questions)

        # Should have asked both questions
        assert mock_prompt.ask.call_count == 2


class TestQuestionWithContext:
    """Test question display with context and example"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Prompt")
    @patch("src.cli.interactive_mode.console")
    def test_question_with_context_and_example(
        self,
        mock_console,
        mock_prompt,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test question displays context and example"""
        mock_prompt.ask.return_value = "Test answer"

        mock_question_gen_instance = MagicMock()
        mock_question_gen_instance.generate_follow_up_question.return_value = None
        mock_question_gen.return_value = mock_question_gen_instance

        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
        )

        question = Question(
            text="What's your target?",
            field_name="ideal_customer",
            question_type=QuestionType.OPEN_ENDED,
            priority=3,
            context="This helps us understand your audience",
            example_answer="Small business owners aged 25-45",
        )

        mode._ask_single_question(question, 1, 1)

        # Verify context and example were printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("This helps us understand" in call for call in print_calls)
        assert any("Small business owners" in call for call in print_calls)


class TestFollowUpSkip:
    """Test follow-up question skip handling"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Prompt")
    @patch("src.cli.interactive_mode.console")
    def test_follow_up_skip(
        self,
        mock_console,
        mock_prompt,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test skipping follow-up question"""
        mock_prompt.ask.side_effect = ["Main answer", "[skip]"]

        follow_up = Question(
            text="Follow-up?",
            field_name="business_description",
            question_type=QuestionType.CLARIFYING,
            priority=1,
        )
        mock_question_gen_instance = MagicMock()
        mock_question_gen_instance.generate_follow_up_question.return_value = follow_up
        mock_question_gen.return_value = mock_question_gen_instance

        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Original",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        question = Question(
            text="Main question?",
            field_name="business_description",
            question_type=QuestionType.OPEN_ENDED,
            priority=1,  # Priority 1 triggers follow-up
        )

        mode._ask_single_question(question, 1, 1)

        # Should only have main answer, not appended
        assert mode.client_brief.business_description == "Main answer"


class TestEnumHandlingWithUnknownValues:
    """Test enum handling with unknown values"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_valid_tone_preferences(
        self, mock_console, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test valid tone preferences are parsed correctly"""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        # Only valid tones
        mode._update_brief_field("brand_personality", "conversational, direct")

        assert TonePreference.CONVERSATIONAL in mode.client_brief.brand_personality
        assert TonePreference.DIRECT in mode.client_brief.brand_personality
        assert len(mode.client_brief.brand_personality) == 2

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_valid_platforms(
        self, mock_console, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test valid platforms are parsed correctly"""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        # Only valid platforms
        mode._update_brief_field("target_platforms", "linkedin, twitter")

        assert Platform.LINKEDIN in mode.client_brief.target_platforms
        assert Platform.TWITTER in mode.client_brief.target_platforms
        assert len(mode.client_brief.target_platforms) == 2


class TestUpdateFieldError:
    """Test error handling in _update_brief_field"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_update_field_error_handling(
        self, mock_console, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test error handling when field update fails with invalid enum"""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        # Try to set an invalid enum value which will fail model reconstruction
        mode._update_brief_field("brand_personality", "invalid_tone_that_doesnt_exist")

        # Should print error message due to Pydantic validation error
        assert any(
            "Error updating field" in str(call) for call in mock_console.print.call_args_list
        )


class TestSaveProgressError:
    """Test error handling in _save_progress"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("pathlib.Path.mkdir", side_effect=Exception("mkdir failed"))
    def test_save_progress_error_handling(
        self, mock_mkdir, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test error handling when save progress fails"""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        # Should not raise, just log error
        mode._save_progress()


class TestFormatBriefWithToneToAvoid:
    """Test formatting brief with tone_to_avoid field"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    def test_format_brief_with_tone_to_avoid(
        self, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test formatting brief with tone_to_avoid field"""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
            tone_to_avoid="aggressive, pushy",
        )

        result = mode._format_brief_as_text()

        assert "Tone to Avoid: aggressive, pushy" in result


class TestDisplayCompletionLowQuality:
    """Test display completion with low quality score"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_display_completion_low_quality_shows_tip(
        self,
        mock_console,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test low quality score shows improvement tip"""
        low_quality_report = BriefQualityReport(
            overall_score=0.60,  # Below 0.75 threshold
            completeness_score=0.6,
            specificity_score=0.6,
            usability_score=0.6,
            can_generate_content=True,
            total_fields=20,
            filled_fields=12,
            required_fields_filled=10,
            minimum_questions_needed=0,
            field_quality={},
            missing_fields=[],
            weak_fields=[],
        )

        mock_quality_checker_instance = MagicMock()
        mock_quality_checker_instance.assess_brief.return_value = low_quality_report
        mock_quality_checker.return_value = mock_quality_checker_instance

        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        mode._display_completion("test_path.txt")

        # Should show tip about improving brief
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Tip:" in call or "higher quality" in call for call in print_calls)


class TestConversationLoopMaxIterations:
    """Test conversation loop max iterations"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Prompt")
    @patch("src.cli.interactive_mode.console")
    def test_conversation_loop_max_iterations(
        self,
        mock_console,
        mock_prompt,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test conversation loop reaches max iterations"""
        not_ready_report = BriefQualityReport(
            overall_score=0.5,
            completeness_score=0.5,
            specificity_score=0.5,
            usability_score=0.5,
            can_generate_content=False,
            total_fields=20,
            filled_fields=10,
            required_fields_filled=8,
            minimum_questions_needed=5,
            field_quality={},
            missing_fields=["field1"],
            weak_fields=[],
        )

        mock_quality_checker_instance = MagicMock()
        mock_quality_checker_instance.assess_brief.return_value = not_ready_report
        mock_quality_checker.return_value = mock_quality_checker_instance

        # Generate questions each time
        question = Question(
            text="Q?",
            field_name="business_description",
            question_type=QuestionType.OPEN_ENDED,
            priority=3,
        )
        mock_question_gen_instance = MagicMock()
        mock_question_gen_instance.generate_questions.return_value = [question]
        mock_question_gen_instance.generate_follow_up_question.return_value = None
        mock_question_gen.return_value = mock_question_gen_instance

        mock_prompt.ask.return_value = "answer"

        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        with patch.object(mode, "_save_progress"):
            mode._conversation_loop()

        assert mode.iteration_count == 10  # Max iterations
        # Should print max iterations message
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("maximum iterations" in call.lower() for call in print_calls)


class TestRun:
    """Test run method - main entry point"""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Confirm")
    @patch("src.cli.interactive_mode.Progress")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.cli.interactive_mode.console")
    def test_run_with_keyboard_interrupt(
        self,
        mock_console,
        mock_file,
        mock_mkdir,
        mock_progress,
        mock_confirm,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
        sample_quality_report,
    ):
        """Test run method handles KeyboardInterrupt"""
        # Create modified report with can_generate_content=False
        not_ready_report = BriefQualityReport(
            **{
                **sample_quality_report.model_dump(),
                "can_generate_content": False,
                "minimum_questions_needed": 2,
            }
        )

        # Mock quality checker
        mock_quality_checker_instance = MagicMock()
        mock_quality_checker_instance.assess_brief.return_value = not_ready_report
        mock_quality_checker.return_value = mock_quality_checker_instance

        # Mock question generator to raise KeyboardInterrupt
        mock_question_gen_instance = MagicMock()
        mock_question_gen_instance.generate_questions.side_effect = KeyboardInterrupt()
        mock_question_gen.return_value = mock_question_gen_instance

        mode = InteractiveMode()

        with patch("src.cli.interactive_mode.Prompt.ask", side_effect=["Test Co", "", "", ""]):
            mode.run()

        # Should print interrupted message
        assert any("interrupted" in str(call).lower() for call in mock_console.print.call_args_list)

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Confirm")
    @patch("src.cli.interactive_mode.Progress")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.cli.interactive_mode.console")
    def test_run_with_exception(
        self,
        mock_console,
        mock_file,
        mock_mkdir,
        mock_progress,
        mock_confirm,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
        sample_quality_report,
    ):
        """Test run method handles general exceptions"""
        not_ready_report = BriefQualityReport(
            **{
                **sample_quality_report.model_dump(),
                "can_generate_content": False,
                "minimum_questions_needed": 2,
            }
        )

        mock_quality_checker_instance = MagicMock()
        mock_quality_checker_instance.assess_brief.return_value = not_ready_report
        mock_quality_checker.return_value = mock_quality_checker_instance

        mock_question_gen_instance = MagicMock()
        mock_question_gen_instance.generate_questions.side_effect = Exception("Test error")
        mock_question_gen.return_value = mock_question_gen_instance

        mode = InteractiveMode()

        with patch("src.cli.interactive_mode.Prompt.ask", side_effect=["Test Co", "", "", ""]):
            mode.run()

        # Should print error message
        assert any("error" in str(call).lower() for call in mock_console.print.call_args_list)

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Confirm")
    @patch("src.cli.interactive_mode.Progress")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.cli.interactive_mode.console")
    def test_run_with_initial_brief_file(
        self,
        mock_console,
        mock_file,
        mock_mkdir,
        mock_progress,
        mock_confirm,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
        sample_quality_report,
    ):
        """Test run method with initial brief file"""
        sample_brief = ClientBrief(
            company_name="Loaded Company",
            business_description="Loaded description",
            ideal_customer="Loaded customer",
            main_problem_solved="Loaded problem",
        )

        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_brief.return_value = sample_brief
        mock_parser.return_value = mock_parser_instance

        mock_quality_checker_instance = MagicMock()
        mock_quality_checker_instance.assess_brief.return_value = sample_quality_report
        mock_quality_checker.return_value = mock_quality_checker_instance

        mock_enhancer_instance = MagicMock()
        mock_enhancer_instance.enhance_brief.return_value = sample_brief
        mock_enhancer.return_value = mock_enhancer_instance

        mock_confirm.ask.return_value = True

        mode = InteractiveMode()

        with patch("pathlib.Path.read_text", return_value="Brief content"):
            mode.run(initial_brief_file="test_brief.txt")

        assert mode.client_brief.company_name == "Loaded Company"

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.Confirm")
    @patch("src.cli.interactive_mode.Prompt")
    @patch("src.cli.interactive_mode.console")
    def test_conversation_loop_ready_but_continue_improving(
        self,
        mock_console,
        mock_prompt,
        mock_confirm,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
        sample_quality_report,
    ):
        """Test conversation loop when brief is ready but user wants to continue"""
        mock_quality_checker_instance = MagicMock()
        mock_quality_checker_instance.assess_brief.side_effect = [
            sample_quality_report,  # First: ready
            sample_quality_report,  # Second: still ready
        ]
        mock_quality_checker.return_value = mock_quality_checker_instance

        # User declines first, accepts second
        mock_confirm.ask.side_effect = [False, True]

        # Generate questions on second iteration
        question = Question(
            text="Q?",
            field_name="business_description",
            question_type=QuestionType.OPEN_ENDED,
            priority=3,
        )
        mock_question_gen_instance = MagicMock()
        mock_question_gen_instance.generate_questions.return_value = [question]
        mock_question_gen_instance.generate_follow_up_question.return_value = None
        mock_question_gen.return_value = mock_question_gen_instance

        mock_prompt.ask.return_value = "answer"

        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        with patch.object(mode, "_save_progress"):
            mode._conversation_loop()

        # Should have run 2 iterations
        assert mode.iteration_count == 2


class TestRunNoInitialBrief:
    """Test run() method edge cases not covered by existing tests."""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_run_keyboard_interrupt_with_no_brief(
        self,
        mock_console,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test run() KeyboardInterrupt when client_brief is None (no save attempted)."""
        # Prompt raises KeyboardInterrupt before brief is created
        with patch("src.cli.interactive_mode.Prompt.ask", side_effect=KeyboardInterrupt()):
            mode = InteractiveMode()
            mode.run()

        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("interrupted" in call.lower() for call in print_calls)

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_run_general_exception_with_no_brief(
        self,
        mock_console,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test run() general exception when client_brief is None (no save attempted)."""
        with patch("src.cli.interactive_mode.Prompt.ask", side_effect=RuntimeError("bang")):
            mode = InteractiveMode()
            mode.run()

        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("error" in call.lower() or "bang" in call for call in print_calls)


class TestParseListInputEdgeCases:
    """Additional edge-case coverage for _parse_list_input."""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    def test_parse_parenthesis_numbered_list(
        self, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test parsing a parenthesis-style numbered list (e.g. '1) item1 2) item2')."""
        mode = InteractiveMode()
        result = mode._parse_list_input("1) item1 2) item2 3) item3")

        assert "item1" in result
        assert "item2" in result
        assert "item3" in result

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    def test_parse_bullet_newline_list(
        self, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test parsing newline list with bullet markers."""
        mode = InteractiveMode()
        result = mode._parse_list_input("• item1\n• item2")

        assert result == ["item1", "item2"]

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    def test_parse_asterisk_newline_list(
        self, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Test parsing newline list with asterisk markers."""
        mode = InteractiveMode()
        result = mode._parse_list_input("* item1\n* item2")

        assert result == ["item1", "item2"]


class TestUpdateBriefFieldEdgeCases:
    """Coverage for uncovered branches in _update_brief_field."""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_update_target_platforms_with_invalid_platform_prints_error(
        self, mock_console, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Invalid platform values cause a Pydantic error caught by the outer handler.

        The source code calls logger.warning for each unknown platform but still
        passes the collected (partial) list to ClientBrief(**current_data).  When
        the list contains invalid enum strings Pydantic raises a ValidationError,
        which is caught by the except-block and printed as an error message.
        """
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        # "notaplatform" causes the model rebuild to fail; error is printed
        mode._update_brief_field("target_platforms", "notaplatform")

        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Error" in call for call in print_calls)

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_update_string_field_append_empty_current(
        self, mock_console, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Appending to a string field that has no current value replaces instead."""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
            tone_to_avoid=None,  # None value — append should just replace
        )

        mode._update_brief_field("tone_to_avoid", "aggressive", append=True)

        assert mode.client_brief.tone_to_avoid == "aggressive"

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_update_list_field_append_empty_current(
        self, mock_console, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Appending to an empty list field replaces rather than concatenates."""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
            # customer_pain_points defaults to []
        )

        mode._update_brief_field("customer_pain_points", "pain1, pain2", append=True)

        assert mode.client_brief.customer_pain_points == ["pain1", "pain2"]

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_update_brand_personality_with_mixed_valid_invalid(
        self, mock_console, mock_question_gen, mock_quality_checker, mock_parser, mock_enhancer
    ):
        """Invalid tone preference logs warning and prints error; valid ones are stored."""
        mode = InteractiveMode()
        mode.client_brief = ClientBrief(
            company_name="Test Co",
            business_description="Test",
            ideal_customer="Test",
            main_problem_solved="Test",
        )

        mode._update_brief_field("brand_personality", "direct, notexist")

        # The error path prints a message about invalid tones
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Error" in call or "notexist" in call for call in print_calls)
        # Valid tone was still stored
        assert TonePreference.DIRECT in mode.client_brief.brand_personality


class TestDisplayProgress:
    """Tests for _display_progress method branches."""

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_display_progress_not_ready(
        self,
        mock_console,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test progress display when brief is not ready shows questions-needed message."""
        from src.models.brief_quality import BriefQualityReport, FieldQuality

        not_ready_report = BriefQualityReport(
            overall_score=0.5,
            completeness_score=0.5,
            specificity_score=0.5,
            usability_score=0.5,
            can_generate_content=False,
            total_fields=20,
            filled_fields=10,
            required_fields_filled=8,
            minimum_questions_needed=3,
            field_quality={},
            missing_fields=["field1"],
            weak_fields=[],
        )

        mode = InteractiveMode()
        mode._display_progress(not_ready_report, iteration=1)

        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("3" in call for call in print_calls)

    @patch("src.cli.interactive_mode.BriefEnhancerAgent")
    @patch("src.cli.interactive_mode.BriefParserAgent")
    @patch("src.cli.interactive_mode.BriefQualityChecker")
    @patch("src.cli.interactive_mode.QuestionGeneratorAgent")
    @patch("src.cli.interactive_mode.console")
    def test_display_progress_ready(
        self,
        mock_console,
        mock_question_gen,
        mock_quality_checker,
        mock_parser,
        mock_enhancer,
    ):
        """Test progress display when brief is ready shows ready message."""
        from src.models.brief_quality import BriefQualityReport, FieldQuality

        ready_report = BriefQualityReport(
            overall_score=0.9,
            completeness_score=0.9,
            specificity_score=0.9,
            usability_score=0.9,
            can_generate_content=True,
            total_fields=20,
            filled_fields=18,
            required_fields_filled=15,
            minimum_questions_needed=0,
            field_quality={},
            missing_fields=[],
            weak_fields=[],
        )

        mode = InteractiveMode()
        mode._display_progress(ready_report, iteration=2)

        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("ready" in call.lower() for call in print_calls)
