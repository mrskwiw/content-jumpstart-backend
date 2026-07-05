"""
Comprehensive unit tests for CoordinatorAgent

Tests cover:
- Brief processing from multiple formats
- Voice sample analysis
- Client classification
- Complete workflow orchestration
- Interactive brief building
- Error handling
- Deliverable generation integration
"""

import pytest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from src.agents.coordinator import CoordinatorAgent, run_workflow
from src.agents.brief_parser import BriefParserAgent
from src.agents.client_classifier import ClientClassifier
from src.agents.content_generator import ContentGeneratorAgent
from src.agents.qa_agent import QAAgent
from src.agents.voice_analyzer import VoiceAnalyzer
from src.agents.post_regenerator import PostRegenerator
from src.models.client_brief import ClientBrief, Platform, TonePreference
from src.models.post import Post
from src.models.qa_report import QAReport
from src.agents.client_classifier import ClientType
from src.utils.output_formatter import OutputFormatter


# ==================== Fixtures ====================


@pytest.fixture
def sample_client_brief():
    """Sample client brief for testing"""
    return ClientBrief(
        company_name="Test Company",
        business_description="We provide cloud-based project management software",
        ideal_customer="Small business owners with 5-20 employees",
        main_problem_solved="Inefficient workflows and scattered communication",
        customer_pain_points=[
            "Wasting time on manual data entry",
            "Poor team collaboration",
        ],
        brand_personality=[TonePreference.AUTHORITATIVE],
        target_platforms=[Platform.LINKEDIN],
    )


@pytest.fixture
def sample_posts(sample_client_brief):
    """Sample posts for testing"""
    posts = []
    for i in range(5):
        post = Post(
            content=f"Test post {i+1} with enough content to meet requirements. This discusses productivity and workflow optimization for small business teams. Manual tasks waste time and reduce efficiency. Here's how to improve your processes and boost team productivity today.",
            template_id=1,
            template_name="Problem Recognition",
            variant=1,
            client_name=sample_client_brief.company_name,
            target_platform=Platform.LINKEDIN,
        )
        posts.append(post)
    return posts


@pytest.fixture
def sample_qa_report():
    """Sample QA report for testing"""
    return QAReport(
        client_name="Test Company",
        total_posts=30,
        passed_posts=28,
        flagged_posts=2,
        quality_score=0.93,
        overall_passed=True,
        hook_validation={"uniqueness_score": 0.92, "metric": "Good"},
        cta_validation={"variety_score": 0.85, "metric": "Good"},
        length_validation={"average_length": 210, "optimal_ratio": 0.95},
        headline_validation={"engagement_score": 0.88, "metric": "Good"},
        all_issues=["Post 5: Hook too similar", "Post 12: CTA missing"],
    )


@pytest.fixture
def mock_agents():
    """Mock all sub-agents"""
    mocks = {
        "brief_parser": Mock(spec=BriefParserAgent),
        "client_classifier": Mock(spec=ClientClassifier),
        "content_generator": Mock(spec=ContentGeneratorAgent),
        "qa_agent": Mock(spec=QAAgent),
        "voice_analyzer": Mock(spec=VoiceAnalyzer),
        "post_regenerator": Mock(spec=PostRegenerator),
        "output_formatter": Mock(spec=OutputFormatter),
    }
    return mocks


@pytest.fixture
def coordinator_with_mocks(mock_agents, sample_client_brief, sample_posts, sample_qa_report):
    """Coordinator with all agents mocked"""
    coordinator = CoordinatorAgent()

    # Replace agents with mocks
    coordinator.brief_parser = mock_agents["brief_parser"]
    coordinator.client_classifier = mock_agents["client_classifier"]
    coordinator.content_generator = mock_agents["content_generator"]
    coordinator.qa_agent = mock_agents["qa_agent"]
    coordinator.voice_analyzer = mock_agents["voice_analyzer"]
    coordinator.post_regenerator = mock_agents["post_regenerator"]
    coordinator.output_formatter = mock_agents["output_formatter"]

    # Configure mock returns
    coordinator.brief_parser.parse_brief.return_value = sample_client_brief
    coordinator.client_classifier.classify_client.return_value = (ClientType.B2B_SAAS, 0.85)
    coordinator.content_generator.generate_posts = Mock(return_value=sample_posts)
    coordinator.content_generator.generate_posts_async = AsyncMock(return_value=sample_posts)
    coordinator.qa_agent.validate_posts.return_value = sample_qa_report
    coordinator.output_formatter.save_complete_package.return_value = {
        "deliverable": Path("/tmp/deliverable.md"),
        "brand_voice": Path("/tmp/voice.md"),
    }

    return coordinator


# ==================== Initialization Tests ====================


def test_coordinator_init():
    """Test CoordinatorAgent initialization"""
    coordinator = CoordinatorAgent()

    assert isinstance(coordinator.brief_parser, BriefParserAgent)
    assert isinstance(coordinator.client_classifier, ClientClassifier)
    assert isinstance(coordinator.content_generator, ContentGeneratorAgent)
    assert isinstance(coordinator.qa_agent, QAAgent)
    assert isinstance(coordinator.voice_analyzer, VoiceAnalyzer)
    assert isinstance(coordinator.post_regenerator, PostRegenerator)
    assert isinstance(coordinator.output_formatter, OutputFormatter)


# ==================== Brief Processing Tests ====================


@pytest.mark.asyncio
async def test_process_brief_input_from_clientbrief(coordinator_with_mocks, sample_client_brief):
    """Test processing brief from ClientBrief object"""
    result = await coordinator_with_mocks._process_brief_input(
        brief_input=sample_client_brief,
        interactive=False,
    )

    assert isinstance(result, ClientBrief)
    assert result.company_name == "Test Company"


@pytest.mark.asyncio
async def test_process_brief_input_from_dict(coordinator_with_mocks):
    """Test processing brief from dictionary"""
    brief_dict = {
        "company_name": "Dict Company",
        "business_description": "Test business",
        "ideal_customer": "Test customer",
        "main_problem_solved": "Test problem",
    }

    result = await coordinator_with_mocks._process_brief_input(
        brief_input=brief_dict,
        interactive=False,
    )

    assert isinstance(result, ClientBrief)
    assert result.company_name == "Dict Company"


@pytest.mark.asyncio
async def test_process_brief_input_from_file(coordinator_with_mocks, tmp_path, sample_client_brief):
    """Test processing brief from file"""
    # Create temp brief file
    brief_file = tmp_path / "test_brief.txt"
    brief_file.write_text(
        """
    Company: File Company
    Business: Test business
    Customer: Test customer
    Problem: Test problem
    """
    )

    result = await coordinator_with_mocks._process_brief_input(
        brief_input=brief_file,
        interactive=False,
    )

    assert isinstance(result, ClientBrief)
    # Should have called parse_brief
    coordinator_with_mocks.brief_parser.parse_brief.assert_called_once()


@pytest.mark.asyncio
async def test_process_brief_input_file_not_found(coordinator_with_mocks):
    """Test error handling for missing brief file"""
    with pytest.raises(FileNotFoundError):
        await coordinator_with_mocks._process_brief_input(
            brief_input=Path("/nonexistent/file.txt"),
            interactive=False,
        )


@pytest.mark.asyncio
async def test_process_brief_input_invalid_type(coordinator_with_mocks):
    """Test error handling for invalid input type"""
    with pytest.raises(TypeError):
        await coordinator_with_mocks._process_brief_input(
            brief_input=12345,  # Invalid type
            interactive=False,
        )


# ==================== Interactive Mode Tests ====================


@pytest.mark.asyncio
async def test_fill_missing_fields_all_present(coordinator_with_mocks, sample_client_brief):
    """Test fill missing fields when all required fields are present"""
    result = await coordinator_with_mocks._fill_missing_fields(sample_client_brief)

    assert result == sample_client_brief


@pytest.mark.asyncio
async def test_fill_missing_fields_missing_required(coordinator_with_mocks):
    """Test fill missing fields when required fields are missing"""
    incomplete_brief = ClientBrief(
        company_name="Test",
        business_description="",  # Missing
        ideal_customer="Customer",
        main_problem_solved="",  # Missing
    )

    with pytest.raises(ValueError, match="Missing required fields"):
        await coordinator_with_mocks._fill_missing_fields(incomplete_brief)


# ==================== Voice Analysis Tests ====================


@pytest.mark.asyncio
async def test_analyze_voice_samples(coordinator_with_mocks, sample_client_brief):
    """Test voice sample analysis"""
    from src.models.voice_guide import EnhancedVoiceGuide

    mock_voice_guide = EnhancedVoiceGuide(
        company_name="Test Company",
        generated_from_posts=3,
        dominant_tones=["professional", "data-driven"],
        tone_consistency_score=0.92,
        average_word_count=150,
        average_paragraph_count=3.5,
        question_usage_rate=0.33,
    )

    coordinator_with_mocks.voice_analyzer.analyze_voice_patterns.return_value = mock_voice_guide

    voice_samples = [
        "Sample post 1 about productivity",
        "Sample post 2 about efficiency",
        "Sample post 3 about workflows",
    ]

    result = await coordinator_with_mocks._analyze_voice_samples(
        voice_samples=voice_samples,
        client_brief=sample_client_brief,
    )

    assert result == mock_voice_guide
    coordinator_with_mocks.voice_analyzer.analyze_voice_patterns.assert_called_once()


# ==================== Complete Workflow Tests ====================


@pytest.mark.asyncio
async def test_run_complete_workflow_basic(coordinator_with_mocks, sample_client_brief):
    """Test complete workflow execution with basic options"""
    with patch("src.config.settings.settings") as mock_settings:
        mock_settings.PARALLEL_GENERATION = True

        result = await coordinator_with_mocks.run_complete_workflow(
            brief_input=sample_client_brief,
            num_posts=5,
            interactive=False,
        )

        # Verify workflow steps were executed
        coordinator_with_mocks.client_classifier.classify_client.assert_called_once()
        coordinator_with_mocks.content_generator.generate_posts_async.assert_called_once()
        coordinator_with_mocks.qa_agent.validate_posts.assert_called_once()
        coordinator_with_mocks.output_formatter.save_complete_package.assert_called_once()

        # Verify return value
        assert isinstance(result, dict)
        assert "deliverable" in result


@pytest.mark.asyncio
async def test_run_complete_workflow_with_voice_samples(
    coordinator_with_mocks, sample_client_brief
):
    """Test workflow with voice sample analysis"""
    from src.models.voice_guide import EnhancedVoiceGuide

    mock_voice_guide = EnhancedVoiceGuide(
        company_name="Test Company",
        generated_from_posts=2,
        dominant_tones=["professional"],
        tone_consistency_score=0.90,
        average_word_count=150,
        average_paragraph_count=3.5,
        question_usage_rate=0.33,
    )

    coordinator_with_mocks.voice_analyzer.analyze_voice_patterns.return_value = mock_voice_guide

    voice_samples = ["Sample 1", "Sample 2"]

    with patch("src.config.settings.settings") as mock_settings:
        mock_settings.PARALLEL_GENERATION = True

        await coordinator_with_mocks.run_complete_workflow(
            brief_input=sample_client_brief,
            voice_samples=voice_samples,
            num_posts=5,
        )

        # Voice analyzer should have been called
        coordinator_with_mocks.voice_analyzer.analyze_voice_patterns.assert_called_once()


@pytest.mark.asyncio
async def test_run_complete_workflow_with_template_quantities(
    coordinator_with_mocks, sample_client_brief
):
    """Test workflow with template quantities"""
    template_quantities = {"1": 10, "2": 10, "9": 10}

    with patch("src.config.settings.settings") as mock_settings:
        mock_settings.PARALLEL_GENERATION = True

        await coordinator_with_mocks.run_complete_workflow(
            brief_input=sample_client_brief,
            template_quantities=template_quantities,
            num_posts=30,
        )

        # Verify template quantities were passed (converted to int keys)
        call_kwargs = coordinator_with_mocks.content_generator.generate_posts_async.call_args[1]
        assert call_kwargs["template_quantities"] == {1: 10, 2: 10, 9: 10}


@pytest.mark.asyncio
async def test_run_complete_workflow_sync_mode(coordinator_with_mocks, sample_client_brief):
    """Test workflow in synchronous mode"""
    # Patch where settings is imported and used (in coordinator module)
    with patch("src.agents.coordinator.settings") as mock_settings:
        mock_settings.PARALLEL_GENERATION = False

        await coordinator_with_mocks.run_complete_workflow(
            brief_input=sample_client_brief,
            num_posts=5,
        )

        # Should use sync generation
        coordinator_with_mocks.content_generator.generate_posts.assert_called_once()
        coordinator_with_mocks.content_generator.generate_posts_async.assert_not_called()


@pytest.mark.asyncio
async def test_run_complete_workflow_with_auto_fix(
    coordinator_with_mocks, sample_client_brief, sample_posts
):
    """Test workflow with auto-fix enabled"""
    # Mock regeneration
    regen_stats = {
        "total_posts": 5,
        "posts_regenerated": 2,
        "posts_improved": 2,
        "reasons": {"too_short": 1, "no_cta": 1},
    }

    coordinator_with_mocks.post_regenerator.regenerate_failed_posts.return_value = (
        sample_posts,
        regen_stats,
    )

    # Patch where settings is imported and used (in coordinator module)
    with patch("src.agents.coordinator.settings") as mock_settings:
        mock_settings.PARALLEL_GENERATION = True

        await coordinator_with_mocks.run_complete_workflow(
            brief_input=sample_client_brief,
            num_posts=5,
            auto_fix=True,
        )

        # Should have called regenerator
        coordinator_with_mocks.post_regenerator.regenerate_failed_posts.assert_called_once()


@pytest.mark.asyncio
async def test_run_complete_workflow_custom_start_date(coordinator_with_mocks, sample_client_brief):
    """Test workflow with custom start date"""
    custom_date = date(2025, 1, 15)

    with patch("src.config.settings.settings") as mock_settings:
        mock_settings.PARALLEL_GENERATION = True

        await coordinator_with_mocks.run_complete_workflow(
            brief_input=sample_client_brief,
            num_posts=5,
            start_date=custom_date,
        )

        # Verify start date was passed to output formatter
        call_kwargs = coordinator_with_mocks.output_formatter.save_complete_package.call_args[1]
        assert call_kwargs["start_date"] == custom_date


@pytest.mark.asyncio
async def test_run_complete_workflow_without_analytics(coordinator_with_mocks, sample_client_brief):
    """Test workflow without analytics generation"""
    with patch("src.config.settings.settings") as mock_settings:
        mock_settings.PARALLEL_GENERATION = True

        await coordinator_with_mocks.run_complete_workflow(
            brief_input=sample_client_brief,
            num_posts=5,
            include_analytics=False,
        )

        # Verify analytics flag was passed
        call_kwargs = coordinator_with_mocks.output_formatter.save_complete_package.call_args[1]
        assert not call_kwargs["include_analytics_tracker"]


@pytest.mark.asyncio
async def test_run_complete_workflow_without_docx(coordinator_with_mocks, sample_client_brief):
    """Test workflow without DOCX generation"""
    with patch("src.config.settings.settings") as mock_settings:
        mock_settings.PARALLEL_GENERATION = True

        await coordinator_with_mocks.run_complete_workflow(
            brief_input=sample_client_brief,
            num_posts=5,
            include_docx=False,
        )

        # Verify docx flag was passed
        call_kwargs = coordinator_with_mocks.output_formatter.save_complete_package.call_args[1]
        assert not call_kwargs["include_docx"]


# ==================== Interactive Builder Tests ====================


def test_run_interactive_builder_basic(monkeypatch):
    """Test interactive brief builder with user inputs"""
    # Mock user inputs
    inputs = [
        "Test Interactive Company",  # company_name
        "We build software",  # business_description
        "Small businesses",  # ideal_customer
        "Manual workflows",  # main_problem_solved
        "Poor productivity",  # pain_point 1
        "",  # End pain points
        "professional, data_driven",  # tones
        "",  # End key phrases
        "",  # End questions
        "linkedin, twitter",  # platforms
        "3x weekly",  # posting_frequency
        "moderate",  # data_usage
        "Book a demo",  # main_cta
    ]

    input_iter = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda _: next(input_iter))

    coordinator = CoordinatorAgent()
    result = coordinator.run_interactive_builder()

    assert isinstance(result, ClientBrief)
    assert result.company_name == "Test Interactive Company"
    assert result.business_description == "We build software"
    assert len(result.target_platforms) == 2
    assert Platform.LINKEDIN in result.target_platforms
    assert Platform.TWITTER in result.target_platforms


def test_run_interactive_builder_with_defaults(monkeypatch):
    """Test interactive builder uses defaults for optional fields"""
    # Minimal inputs (empty strings for optional fields)
    inputs = [
        "Minimal Company",
        "Business",
        "Customer",
        "Problem",
        "",  # No pain points
        "",  # No tones
        "",  # No key phrases
        "",  # No questions
        "",  # No platforms (will use default)
        "",  # No frequency (will use default)
        "",  # No data usage (will use default)
        "",  # No CTA (will use default)
    ]

    input_iter = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda _: next(input_iter))

    coordinator = CoordinatorAgent()
    result = coordinator.run_interactive_builder()

    # Check defaults were applied
    assert result.customer_pain_points == ["(No pain points provided)"]
    assert len(result.brand_personality) >= 1
    assert len(result.target_platforms) >= 1
    assert result.posting_frequency == "3-4x weekly"
    assert result.main_cta == "Get in touch"


# ==================== Convenience Function Tests ====================


@pytest.mark.asyncio
async def test_run_workflow_convenience_function(sample_client_brief, tmp_path):
    """Test convenience function for running workflow"""
    with patch("src.agents.coordinator.CoordinatorAgent") as MockCoordinator:
        mock_coordinator = Mock()
        mock_coordinator.run_complete_workflow = AsyncMock(
            return_value={"deliverable": tmp_path / "test.md"}
        )
        MockCoordinator.return_value = mock_coordinator

        result = await run_workflow(
            brief_input=sample_client_brief,
            num_posts=10,
        )

        mock_coordinator.run_complete_workflow.assert_called_once()
        assert "deliverable" in result


# ==================== Error Handling Tests ====================


@pytest.mark.asyncio
async def test_workflow_handles_generation_error(coordinator_with_mocks, sample_client_brief):
    """Test workflow handles content generation errors gracefully"""
    coordinator_with_mocks.content_generator.generate_posts_async.side_effect = Exception(
        "Generation failed"
    )

    with patch("src.config.settings.settings") as mock_settings:
        mock_settings.PARALLEL_GENERATION = True

        with pytest.raises(Exception, match="Generation failed"):
            await coordinator_with_mocks.run_complete_workflow(
                brief_input=sample_client_brief,
                num_posts=5,
            )


@pytest.mark.asyncio
async def test_workflow_handles_qa_error(coordinator_with_mocks, sample_client_brief):
    """Test workflow handles QA validation errors"""
    coordinator_with_mocks.qa_agent.validate_posts.side_effect = Exception("QA failed")

    with patch("src.config.settings.settings") as mock_settings:
        mock_settings.PARALLEL_GENERATION = True

        with pytest.raises(Exception, match="QA failed"):
            await coordinator_with_mocks.run_complete_workflow(
                brief_input=sample_client_brief,
                num_posts=5,
            )


# ==================== Platform-Specific Tests ====================


@pytest.mark.asyncio
async def test_workflow_with_twitter_platform(coordinator_with_mocks, sample_client_brief):
    """Test workflow targeting Twitter platform"""
    with patch("src.config.settings.settings") as mock_settings:
        mock_settings.PARALLEL_GENERATION = True

        await coordinator_with_mocks.run_complete_workflow(
            brief_input=sample_client_brief,
            num_posts=5,
            platform=Platform.TWITTER,
        )

        # Verify Twitter platform was passed to generator
        call_kwargs = coordinator_with_mocks.content_generator.generate_posts_async.call_args[1]
        assert call_kwargs["platform"] == Platform.TWITTER


@pytest.mark.asyncio
async def test_workflow_uses_brief_default_platform(coordinator_with_mocks, sample_client_brief):
    """Test workflow uses brief's default platform when none specified"""
    sample_client_brief.target_platforms = [Platform.FACEBOOK, Platform.TWITTER]

    with patch("src.config.settings.settings") as mock_settings:
        mock_settings.PARALLEL_GENERATION = True

        await coordinator_with_mocks.run_complete_workflow(
            brief_input=sample_client_brief,
            num_posts=5,
            platform=None,  # Use default from brief
        )

        # Should use first platform from brief
        call_kwargs = coordinator_with_mocks.content_generator.generate_posts_async.call_args[1]
        assert call_kwargs["platform"] == Platform.FACEBOOK


# ==================== Logging and Output Tests ====================


@pytest.mark.asyncio
async def test_workflow_logs_progress(coordinator_with_mocks, sample_client_brief, caplog):
    """Test that workflow logs progress messages"""
    with patch("src.config.settings.settings") as mock_settings:
        mock_settings.PARALLEL_GENERATION = True

        result = await coordinator_with_mocks.run_complete_workflow(
            brief_input=sample_client_brief,
            num_posts=5,
        )

        # Check that key log messages were generated
        # (This would require checking actual log output, simplified here)
        assert result is not None
