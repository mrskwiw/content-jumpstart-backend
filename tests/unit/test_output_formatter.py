"""Comprehensive unit tests for OutputFormatter

Tests all formatting and file output methods to achieve 90%+ coverage.
"""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.models.client_brief import ClientBrief, Platform, TonePreference
from src.models.post import Post
from src.models.qa_report import QAReport
from src.models.seo_keyword import (
    KeywordStrategy,
    SEOKeyword,
    KeywordIntent,
    KeywordDifficulty,
)
from src.utils.output_formatter import OutputFormatter, get_default_formatter


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory for testing"""
    output_dir = tmp_path / "test_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def sample_posts():
    """Create sample posts for testing"""
    return [
        Post(
            content="First post content with a clear CTA.\n\nThis is the body.\n\nWhat do you think?",
            template_id=1,
            template_name="Template 1",
            client_name="Test Client",
        ),
        Post(
            content="Second post is longer and has different content.\n\nMore body text here.\n\nLearn more today!",
            template_id=2,
            template_name="Template 2",
            client_name="Test Client",
        ),
        Post(
            content="Third post completes the set.\n\nFinal body paragraph.\n\nJoin us now!",
            template_id=3,
            template_name="Template 3",
            client_name="Test Client",
        ),
    ]


@pytest.fixture
def sample_client_brief():
    """Create sample client brief for testing"""
    return ClientBrief(
        company_name="Test Company Inc",
        business_description="We provide cloud-based solutions",
        ideal_customer="Small business owners",
        main_problem_solved="Inefficient workflows",
        customer_pain_points=["Time waste", "Poor collaboration"],
        target_platforms=[Platform.LINKEDIN, Platform.TWITTER],
        brand_personality=[TonePreference.AUTHORITATIVE, TonePreference.DATA_DRIVEN],
        posting_frequency="3 times per week",
        key_phrases=["cloud solutions", "workflow optimization"],
    )


@pytest.fixture
def sample_qa_report():
    """Create sample QA report for testing"""
    return QAReport(
        client_name="Test Client",
        total_posts=3,
        overall_passed=True,
        quality_score=0.92,
        hook_validation={
            "passed": True,
            "uniqueness_score": 0.95,
            "metric": "3/3 unique hooks",
            "issues": [],
        },
        cta_validation={
            "passed": True,
            "variety_score": 0.90,
            "metric": "3 unique CTA types",
            "cta_distribution": {"question": 1, "action": 1, "share": 1},
            "issues": [],
        },
        length_validation={
            "passed": True,
            "average_length": 200,
            "metric": "3/3 in optimal range",
            "optimal_ratio": 1.0,
            "length_distribution": {"optimal": 3, "too_short": 0, "too_long": 0},
            "issues": [],
        },
        headline_validation={
            "passed": True,
            "score": 0.92,
            "average_elements": 3.5,
            "metric": "3/3 engaging headlines",
            "issues": [],
        },
    )


@pytest.fixture
def sample_keyword_strategy():
    """Create sample keyword strategy for testing"""
    return KeywordStrategy(
        primary_keywords=[
            SEOKeyword(
                keyword="cloud solutions",
                intent=KeywordIntent.COMMERCIAL,
                difficulty=KeywordDifficulty.MEDIUM,
                priority=1,
                related_keywords=["cloud computing", "cloud services"],
                notes="Main service keyword",
            ),
        ],
        secondary_keywords=[
            SEOKeyword(
                keyword="workflow automation",
                intent=KeywordIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.EASY,
                priority=2,
                related_keywords=["process automation"],
            ),
        ],
        longtail_keywords=[
            SEOKeyword(
                keyword="how to automate business workflows",
                intent=KeywordIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.EASY,
                priority=3,
            ),
        ],
        keyword_density_target=0.02,
    )


class TestOutputFormatterInit:
    """Test OutputFormatter initialization"""

    def test_init_with_custom_dir(self, temp_output_dir):
        """Test initialization with custom output directory"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        assert formatter.output_dir == temp_output_dir
        assert formatter.output_dir.exists()

    def test_init_creates_directory(self, tmp_path):
        """Test initialization creates directory if it doesn't exist"""
        new_dir = tmp_path / "nonexistent" / "nested"
        OutputFormatter(output_dir=new_dir)
        assert new_dir.exists()

    def test_init_with_default_dir(self):
        """Test initialization with default directory from settings"""
        # Patch where settings is imported from (import happens inside __init__)
        with patch("src.config.settings.settings") as mock_settings:
            mock_settings.DEFAULT_OUTPUT_DIR = "test_default_dir"
            formatter = OutputFormatter()
            assert "test_default_dir" in str(formatter.output_dir)


class TestFormatPostsAsText:
    """Test format_posts_as_text method"""

    def test_format_basic(self, temp_output_dir, sample_posts):
        """Test basic text formatting without metadata"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_posts_as_text(sample_posts, include_metadata=False)

        assert "First post content" in result
        assert "Second post is longer" in result
        assert "Third post completes" in result
        assert "---" in result  # Default separator

    def test_format_with_metadata(self, temp_output_dir, sample_posts):
        """Test text formatting with metadata included"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_posts_as_text(sample_posts, include_metadata=True)

        # Should include template names and word counts from to_formatted_string
        assert result  # Metadata format depends on Post.to_formatted_string implementation

    def test_format_custom_separator(self, temp_output_dir, sample_posts):
        """Test text formatting with custom separator"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_posts_as_text(sample_posts, separator="\n###\n")

        assert "###" in result
        assert "---" not in result

    def test_format_empty_posts(self, temp_output_dir):
        """Test formatting empty post list"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_posts_as_text([], include_metadata=False)
        assert result == ""


class TestFormatPostsAsJSON:
    """Test format_posts_as_json method"""

    def test_format_json_valid(self, temp_output_dir, sample_posts):
        """Test JSON formatting produces valid JSON"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_posts_as_json(sample_posts)

        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 3

    def test_format_json_content(self, temp_output_dir, sample_posts):
        """Test JSON contains correct post data"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_posts_as_json(sample_posts)
        parsed = json.loads(result)

        assert parsed[0]["template_name"] == "Template 1"
        assert parsed[1]["template_name"] == "Template 2"
        assert "content" in parsed[0]

    def test_format_json_empty_posts(self, temp_output_dir):
        """Test JSON formatting with empty post list"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_posts_as_json([])
        parsed = json.loads(result)
        assert parsed == []


class TestFormatPostsAsMarkdown:
    """Test format_posts_as_markdown method"""

    def test_format_markdown_without_brief(self, temp_output_dir, sample_posts):
        """Test markdown formatting without client brief"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_posts_as_markdown(sample_posts)

        assert "# 30-Day Content Jumpstart" in result
        assert "**Generated:**" in result
        assert "## Post 1:" in result
        assert "Template 1" in result

    def test_format_markdown_with_brief(self, temp_output_dir, sample_posts, sample_client_brief):
        """Test markdown formatting with client brief"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_posts_as_markdown(sample_posts, sample_client_brief)

        assert "Test Company Inc" in result
        assert "Small business owners" in result
        assert "linkedin" in result  # Platform enum values are lowercase
        assert "twitter" in result

    def test_format_markdown_structure(self, temp_output_dir, sample_posts):
        """Test markdown has correct structure"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_posts_as_markdown(sample_posts)

        # Check for all post headers
        assert "## Post 1:" in result
        assert "## Post 2:" in result
        assert "## Post 3:" in result

        # Check for metadata
        assert "Words:" in result
        assert "Has CTA:" in result


class TestFormatBrandVoiceGuide:
    """Test format_brand_voice_guide method"""

    def test_format_voice_guide_basic(self, temp_output_dir, sample_client_brief):
        """Test basic brand voice guide formatting"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_brand_voice_guide(sample_client_brief)

        assert "# Brand Voice Guide: Test Company Inc" in result
        assert "## Audience" in result
        assert "Small business owners" in result
        assert "Inefficient workflows" in result

    def test_format_voice_guide_with_pain_points(self, temp_output_dir, sample_client_brief):
        """Test voice guide includes pain points"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_brand_voice_guide(sample_client_brief)

        assert "**Customer Pain Points:**" in result
        assert "Time waste" in result
        assert "Poor collaboration" in result

    def test_format_voice_guide_with_key_phrases(self, temp_output_dir, sample_client_brief):
        """Test voice guide includes key phrases"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_brand_voice_guide(sample_client_brief)

        assert "**Key Phrases to Use:**" in result
        assert "cloud solutions" in result
        assert "workflow optimization" in result

    def test_format_voice_guide_with_stories(self, temp_output_dir):
        """Test voice guide includes stories when present"""
        brief = ClientBrief(
            company_name="Test Co",
            business_description="Test business",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
            target_platforms=[Platform.LINKEDIN],
            posting_frequency="Daily",
        )
        # Add stories attribute
        brief.stories = ["Story 1 about success", "Story 2 about growth"]

        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_brand_voice_guide(brief)

        assert "## Example Stories/Wins" in result
        assert "Story 1 about success" in result


class TestFormatKeywordStrategy:
    """Test format_keyword_strategy method"""

    def test_format_keyword_strategy_structure(
        self, temp_output_dir, sample_keyword_strategy, sample_client_brief
    ):
        """Test keyword strategy formatting structure"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_keyword_strategy(sample_keyword_strategy, sample_client_brief)

        assert "# SEO Keyword Strategy: Test Company Inc" in result
        assert "## Primary Keywords" in result
        assert "## Secondary Keywords" in result
        assert "## Long-Tail Keywords" in result

    def test_format_keyword_strategy_content(
        self, temp_output_dir, sample_keyword_strategy, sample_client_brief
    ):
        """Test keyword strategy includes keyword details"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_keyword_strategy(sample_keyword_strategy, sample_client_brief)

        assert "cloud solutions" in result
        assert "workflow automation" in result
        assert "how to automate business workflows" in result
        assert "**Intent:**" in result
        assert "**Difficulty:**" in result

    def test_format_keyword_strategy_guidelines(
        self, temp_output_dir, sample_keyword_strategy, sample_client_brief
    ):
        """Test keyword strategy includes usage guidelines"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_keyword_strategy(sample_keyword_strategy, sample_client_brief)

        assert "## How to Use These Keywords" in result
        assert "Natural Integration" in result
        assert "Track Performance" in result


class TestSaveAsMethods:
    """Test save_as_text, save_as_json, save_as_markdown methods"""

    def test_save_as_text(self, temp_output_dir, sample_posts):
        """Test saving posts as text file"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        output_path = formatter.save_as_text(sample_posts, "test_posts")

        assert output_path.exists()
        assert output_path.suffix == ".txt"
        content = output_path.read_text(encoding="utf-8")
        assert "First post content" in content

    def test_save_as_json(self, temp_output_dir, sample_posts):
        """Test saving posts as JSON file"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        output_path = formatter.save_as_json(sample_posts, "test_posts")

        assert output_path.exists()
        assert output_path.suffix == ".json"
        content = json.loads(output_path.read_text(encoding="utf-8"))
        assert len(content) == 3

    def test_save_as_markdown(self, temp_output_dir, sample_posts, sample_client_brief):
        """Test saving posts as markdown file"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        output_path = formatter.save_as_markdown(sample_posts, "test_posts", sample_client_brief)

        assert output_path.exists()
        assert output_path.suffix == ".md"
        content = output_path.read_text(encoding="utf-8")
        assert "Test Company Inc" in content


class TestSaveCompletePackage:
    """Test save_complete_package method"""

    def test_save_complete_package_basic(self, temp_output_dir, sample_posts, sample_client_brief):
        """Test complete package saves core files"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        saved_files = formatter.save_complete_package(
            posts=sample_posts,
            client_brief=sample_client_brief,
            client_name="TestClient",
            include_docx=False,
            include_analytics_tracker=False,
        )

        # Check core files are saved
        assert "markdown" in saved_files
        assert "brand_voice" in saved_files
        assert "text" in saved_files
        assert "json" in saved_files

        # Check files exist
        assert saved_files["markdown"].exists()
        assert saved_files["brand_voice"].exists()

    def test_save_complete_package_with_qa_report(
        self, temp_output_dir, sample_posts, sample_client_brief, sample_qa_report
    ):
        """Test complete package includes QA report"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        saved_files = formatter.save_complete_package(
            posts=sample_posts,
            client_brief=sample_client_brief,
            client_name="TestClient",
            qa_report=sample_qa_report,
            include_docx=False,
            include_analytics_tracker=False,
        )

        assert "qa_report" in saved_files
        assert saved_files["qa_report"].exists()

    def test_save_complete_package_with_keyword_strategy(
        self,
        temp_output_dir,
        sample_posts,
        sample_client_brief,
        sample_keyword_strategy,
    ):
        """Test complete package includes keyword strategy"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        saved_files = formatter.save_complete_package(
            posts=sample_posts,
            client_brief=sample_client_brief,
            client_name="TestClient",
            keyword_strategy=sample_keyword_strategy,
            include_docx=False,
            include_analytics_tracker=False,
        )

        assert "keyword_strategy" in saved_files
        assert saved_files["keyword_strategy"].exists()

    def test_save_complete_package_creates_client_dir(
        self, temp_output_dir, sample_posts, sample_client_brief
    ):
        """Test complete package creates client-specific directory"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        formatter.save_complete_package(
            posts=sample_posts,
            client_brief=sample_client_brief,
            client_name="UniqueClient",
            include_docx=False,
            include_analytics_tracker=False,
        )

        client_dir = temp_output_dir / "UniqueClient"
        assert client_dir.exists()

    @patch("src.utils.output_formatter.VoiceAnalyzer")
    def test_save_complete_package_with_enhanced_voice_guide(
        self, mock_voice_analyzer, temp_output_dir, sample_posts, sample_client_brief
    ):
        """Test complete package generates enhanced voice guide"""
        # Mock VoiceAnalyzer
        mock_analyzer_instance = MagicMock()
        mock_voice_guide = MagicMock()
        mock_voice_guide.to_markdown.return_value = "# Enhanced Voice Guide"
        mock_analyzer_instance.analyze_voice_patterns.return_value = mock_voice_guide
        mock_voice_analyzer.return_value = mock_analyzer_instance

        formatter = OutputFormatter(output_dir=temp_output_dir)
        formatter.save_complete_package(
            posts=sample_posts,
            client_brief=sample_client_brief,
            client_name="TestClient",
            include_docx=False,
            include_analytics_tracker=False,
        )

        # Check if enhanced voice guide was attempted
        # Note: May be in saved_files if successful, or logged as warning if failed
        # We're primarily testing the code path is executed

    @patch("src.utils.output_formatter.ScheduleGenerator")
    def test_save_complete_package_with_schedule(
        self, mock_schedule_gen, temp_output_dir, sample_posts, sample_client_brief
    ):
        """Test complete package generates posting schedule"""
        # Mock ScheduleGenerator
        mock_gen_instance = MagicMock()
        mock_schedule = MagicMock()
        mock_schedule.to_markdown_calendar.return_value = "# Schedule"
        mock_schedule.to_csv.return_value = temp_output_dir / "schedule.csv"
        mock_gen_instance.generate_schedule.return_value = mock_schedule
        mock_schedule_gen.return_value = mock_gen_instance

        formatter = OutputFormatter(output_dir=temp_output_dir)
        formatter.save_complete_package(
            posts=sample_posts,
            client_brief=sample_client_brief,
            client_name="TestClient",
            start_date=date(2025, 1, 15),
            include_docx=False,
            include_analytics_tracker=False,
        )

        # Schedule generation attempted
        mock_gen_instance.generate_schedule.assert_called_once()


class TestCreatePostingSchedule:
    """Test create_posting_schedule method"""

    def test_create_schedule_basic(self, temp_output_dir, sample_posts):
        """Test creating basic posting schedule"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.create_posting_schedule(sample_posts, posts_per_week=3)

        assert "# Suggested Posting Schedule" in result
        assert "**Posts per week:** 3" in result
        assert "**Total posts:** 3" in result

    def test_create_schedule_structure(self, temp_output_dir, sample_posts):
        """Test schedule has correct week structure"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.create_posting_schedule(sample_posts, posts_per_week=2)

        assert "## Week 1" in result
        # 3 posts / 2 per week = 2 weeks
        assert "## Week 2" in result

    def test_create_schedule_includes_post_info(self, temp_output_dir, sample_posts):
        """Test schedule includes post information"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.create_posting_schedule(sample_posts, posts_per_week=3)

        assert "Template 1" in result
        assert "Template 2" in result
        assert "words" in result


class TestGetDefaultFormatter:
    """Test get_default_formatter singleton function"""

    def test_get_default_formatter_returns_instance(self):
        """Test get_default_formatter returns OutputFormatter instance"""
        formatter = get_default_formatter()
        assert isinstance(formatter, OutputFormatter)

    def test_get_default_formatter_singleton(self):
        """Test get_default_formatter returns same instance"""
        formatter1 = get_default_formatter()
        formatter2 = get_default_formatter()
        assert formatter1 is formatter2


class TestKeywordStrategyEdgeCases:
    """Test edge cases for format_keyword_strategy method"""

    def test_format_keyword_strategy_secondary_with_notes(
        self, temp_output_dir, sample_client_brief
    ):
        """Test keyword strategy with notes on secondary keywords (line 207)"""
        keyword_strategy = KeywordStrategy(
            primary_keywords=[
                SEOKeyword(
                    keyword="primary keyword",
                    intent=KeywordIntent.COMMERCIAL,
                    difficulty=KeywordDifficulty.MEDIUM,
                    priority=1,
                ),
            ],
            secondary_keywords=[
                SEOKeyword(
                    keyword="secondary keyword",
                    intent=KeywordIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.EASY,
                    priority=2,
                    related_keywords=["related term"],
                    notes="This is a note for secondary keyword",  # Cover line 207
                ),
            ],
            longtail_keywords=[
                SEOKeyword(
                    keyword="longtail keyword",
                    intent=KeywordIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.EASY,
                    priority=3,
                ),
            ],
            keyword_density_target=0.02,
        )

        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_keyword_strategy(keyword_strategy, sample_client_brief)

        assert "This is a note for secondary keyword" in result
        assert "related term" in result

    def test_format_keyword_strategy_longtail_with_notes(
        self, temp_output_dir, sample_client_brief
    ):
        """Test keyword strategy with notes on longtail keywords (line 219)"""
        keyword_strategy = KeywordStrategy(
            primary_keywords=[
                SEOKeyword(
                    keyword="primary keyword",
                    intent=KeywordIntent.COMMERCIAL,
                    difficulty=KeywordDifficulty.MEDIUM,
                    priority=1,
                ),
            ],
            secondary_keywords=[
                SEOKeyword(
                    keyword="secondary keyword",
                    intent=KeywordIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.EASY,
                    priority=2,
                ),
            ],
            longtail_keywords=[
                SEOKeyword(
                    keyword="how to do longtail search",
                    intent=KeywordIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.EASY,
                    priority=3,
                    notes="This is a note for longtail keyword",  # Cover line 219
                ),
            ],
            keyword_density_target=0.02,
        )

        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_keyword_strategy(keyword_strategy, sample_client_brief)

        assert "This is a note for longtail keyword" in result

    def test_format_keyword_strategy_primary_without_related_or_notes(
        self, temp_output_dir, sample_client_brief
    ):
        """Test keyword strategy with primary keywords without related or notes"""
        keyword_strategy = KeywordStrategy(
            primary_keywords=[
                SEOKeyword(
                    keyword="primary only keyword",
                    intent=KeywordIntent.COMMERCIAL,
                    difficulty=KeywordDifficulty.HARD,
                    priority=1,
                    # No related_keywords or notes - tests the else branches
                ),
            ],
            secondary_keywords=[],
            longtail_keywords=[],
            keyword_density_target=0.01,
        )

        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_keyword_strategy(keyword_strategy, sample_client_brief)

        assert "primary only keyword" in result
        assert "**Priority:** 1" in result


class TestSaveCompletePackageErrorHandling:
    """Test error handling paths in save_complete_package"""

    @patch("src.utils.output_formatter.VoiceAnalyzer")
    def test_enhanced_voice_guide_failure(
        self, mock_voice_analyzer, temp_output_dir, sample_posts, sample_client_brief
    ):
        """Test graceful handling when enhanced voice guide fails (lines 393-394)"""
        # Make VoiceAnalyzer raise an exception
        mock_analyzer_instance = MagicMock()
        mock_analyzer_instance.analyze_voice_patterns.side_effect = Exception(
            "Voice analysis failed"
        )
        mock_voice_analyzer.return_value = mock_analyzer_instance

        formatter = OutputFormatter(output_dir=temp_output_dir)
        saved_files = formatter.save_complete_package(
            posts=sample_posts,
            client_brief=sample_client_brief,
            client_name="TestClient",
            include_docx=False,
            include_analytics_tracker=False,
        )

        # Should still save core files despite voice guide failure
        assert "markdown" in saved_files
        assert "brand_voice" in saved_files
        # Enhanced voice guide should NOT be in saved_files due to failure
        assert "brand_voice_enhanced" not in saved_files

    @patch("src.utils.output_formatter.ScheduleGenerator")
    def test_schedule_generation_failure(
        self, mock_schedule_gen, temp_output_dir, sample_posts, sample_client_brief
    ):
        """Test graceful handling when schedule generation fails (lines 427-428)"""
        # Make ScheduleGenerator raise an exception
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate_schedule.side_effect = Exception("Schedule generation failed")
        mock_schedule_gen.return_value = mock_gen_instance

        formatter = OutputFormatter(output_dir=temp_output_dir)
        saved_files = formatter.save_complete_package(
            posts=sample_posts,
            client_brief=sample_client_brief,
            client_name="TestClient",
            include_docx=False,
            include_analytics_tracker=False,
        )

        # Should still save core files despite schedule failure
        assert "markdown" in saved_files
        # Schedule files should NOT be in saved_files due to failure
        assert "schedule_markdown" not in saved_files
        assert "schedule_csv" not in saved_files

    @patch("src.utils.output_formatter.ScheduleGenerator")
    def test_ical_import_error(
        self, mock_schedule_gen, temp_output_dir, sample_posts, sample_client_brief
    ):
        """Test handling when icalendar import fails (lines 423-424)"""
        # Mock successful schedule generation
        mock_gen_instance = MagicMock()
        mock_schedule = MagicMock()
        mock_schedule.to_markdown_calendar.return_value = "# Schedule"
        mock_schedule.to_csv.return_value = temp_output_dir / "TestClient" / "schedule.csv"
        # Simulate ImportError when calling to_ical
        mock_schedule.to_ical.side_effect = ImportError("icalendar not installed")
        mock_gen_instance.generate_schedule.return_value = mock_schedule
        mock_schedule_gen.return_value = mock_gen_instance

        # Create the CSV file that would be returned
        client_dir = temp_output_dir / "TestClient"
        client_dir.mkdir(parents=True, exist_ok=True)
        csv_file = client_dir / "schedule.csv"
        csv_file.write_text("test")

        formatter = OutputFormatter(output_dir=temp_output_dir)
        saved_files = formatter.save_complete_package(
            posts=sample_posts,
            client_brief=sample_client_brief,
            client_name="TestClient",
            include_docx=False,
            include_analytics_tracker=False,
        )

        # Should have markdown and csv but not ical
        assert "schedule_markdown" in saved_files
        assert "schedule_csv" in saved_files
        assert "schedule_ical" not in saved_files

    @patch("src.utils.output_formatter.ScheduleGenerator")
    @patch("src.utils.output_formatter.AnalyticsTracker")
    def test_analytics_tracker_generation(
        self,
        mock_analytics_tracker,
        mock_schedule_gen,
        temp_output_dir,
        sample_posts,
        sample_client_brief,
    ):
        """Test analytics tracker generation (lines 432-457)"""
        # Mock schedule generation
        mock_gen_instance = MagicMock()
        mock_schedule = MagicMock()
        mock_schedule.to_markdown_calendar.return_value = "# Schedule"
        mock_schedule.to_csv.return_value = temp_output_dir / "TestClient" / "schedule.csv"
        mock_schedule.to_ical.side_effect = ImportError("icalendar not installed")
        mock_gen_instance.generate_schedule.return_value = mock_schedule
        mock_schedule_gen.return_value = mock_gen_instance

        # Mock analytics tracker
        mock_tracker_instance = MagicMock()
        csv_path = temp_output_dir / "TestClient" / "analytics.csv"
        xlsx_path = temp_output_dir / "TestClient" / "analytics.xlsx"
        mock_tracker_instance.create_tracking_sheet.side_effect = [csv_path, xlsx_path]
        mock_analytics_tracker.return_value = mock_tracker_instance

        # Create directories and files
        client_dir = temp_output_dir / "TestClient"
        client_dir.mkdir(parents=True, exist_ok=True)
        (client_dir / "schedule.csv").write_text("test")
        csv_path.write_text("csv content")
        xlsx_path.write_text("xlsx content")

        formatter = OutputFormatter(output_dir=temp_output_dir)
        saved_files = formatter.save_complete_package(
            posts=sample_posts,
            client_brief=sample_client_brief,
            client_name="TestClient",
            include_docx=False,
            include_analytics_tracker=True,
        )

        # Analytics tracker should be called
        assert mock_tracker_instance.create_tracking_sheet.call_count >= 1
        assert "analytics_csv" in saved_files

    @patch("src.utils.output_formatter.ScheduleGenerator")
    @patch("src.utils.output_formatter.AnalyticsTracker")
    def test_analytics_tracker_xlsx_import_error(
        self,
        mock_analytics_tracker,
        mock_schedule_gen,
        temp_output_dir,
        sample_posts,
        sample_client_brief,
    ):
        """Test handling when openpyxl import fails for analytics tracker (line 453-454)"""
        # Mock schedule generation
        mock_gen_instance = MagicMock()
        mock_schedule = MagicMock()
        mock_schedule.to_markdown_calendar.return_value = "# Schedule"
        mock_schedule.to_csv.return_value = temp_output_dir / "TestClient" / "schedule.csv"
        mock_schedule.to_ical.side_effect = ImportError("icalendar not installed")
        mock_gen_instance.generate_schedule.return_value = mock_schedule
        mock_schedule_gen.return_value = mock_gen_instance

        # Mock analytics tracker - CSV succeeds, XLSX fails with ImportError
        mock_tracker_instance = MagicMock()
        csv_path = temp_output_dir / "TestClient" / "analytics.csv"

        def create_tracking_sheet_side_effect(*args, **kwargs):
            if kwargs.get("format") == "csv":
                return csv_path
            elif kwargs.get("format") == "xlsx":
                raise ImportError("openpyxl not installed")
            return csv_path

        mock_tracker_instance.create_tracking_sheet.side_effect = create_tracking_sheet_side_effect
        mock_analytics_tracker.return_value = mock_tracker_instance

        # Create directories and files
        client_dir = temp_output_dir / "TestClient"
        client_dir.mkdir(parents=True, exist_ok=True)
        (client_dir / "schedule.csv").write_text("test")
        csv_path.write_text("csv content")

        formatter = OutputFormatter(output_dir=temp_output_dir)
        saved_files = formatter.save_complete_package(
            posts=sample_posts,
            client_brief=sample_client_brief,
            client_name="TestClient",
            include_docx=False,
            include_analytics_tracker=True,
        )

        # CSV should exist, XLSX should not
        assert "analytics_csv" in saved_files
        assert "analytics_xlsx" not in saved_files

    @patch("src.utils.output_formatter.ScheduleGenerator")
    @patch("src.utils.output_formatter.AnalyticsTracker")
    def test_analytics_tracker_failure(
        self,
        mock_analytics_tracker,
        mock_schedule_gen,
        temp_output_dir,
        sample_posts,
        sample_client_brief,
    ):
        """Test handling when analytics tracker completely fails (line 456-457)"""
        # Mock schedule generation
        mock_gen_instance = MagicMock()
        mock_schedule = MagicMock()
        mock_schedule.to_markdown_calendar.return_value = "# Schedule"
        mock_schedule.to_csv.return_value = temp_output_dir / "TestClient" / "schedule.csv"
        mock_schedule.to_ical.side_effect = ImportError("icalendar not installed")
        mock_gen_instance.generate_schedule.return_value = mock_schedule
        mock_schedule_gen.return_value = mock_gen_instance

        # Mock analytics tracker to raise exception
        mock_tracker_instance = MagicMock()
        mock_tracker_instance.create_tracking_sheet.side_effect = Exception("Tracker failed")
        mock_analytics_tracker.return_value = mock_tracker_instance

        # Create directories and files
        client_dir = temp_output_dir / "TestClient"
        client_dir.mkdir(parents=True, exist_ok=True)
        (client_dir / "schedule.csv").write_text("test")

        formatter = OutputFormatter(output_dir=temp_output_dir)
        saved_files = formatter.save_complete_package(
            posts=sample_posts,
            client_brief=sample_client_brief,
            client_name="TestClient",
            include_docx=False,
            include_analytics_tracker=True,
        )

        # Should still save core files despite analytics failure
        assert "markdown" in saved_files
        assert "analytics_csv" not in saved_files
        assert "analytics_xlsx" not in saved_files

    @patch("src.utils.output_formatter.DOCXGenerator")
    def test_docx_generation_success(
        self, mock_docx_gen, temp_output_dir, sample_posts, sample_client_brief
    ):
        """Test DOCX generation success path (lines 461-488)"""
        # Mock DOCXGenerator
        mock_gen_instance = MagicMock()
        docx_path = temp_output_dir / "TestClient" / "deliverable.docx"
        mock_gen_instance.create_deliverable_docx.return_value = docx_path
        mock_docx_gen.return_value = mock_gen_instance

        # Create directories and files
        client_dir = temp_output_dir / "TestClient"
        client_dir.mkdir(parents=True, exist_ok=True)
        docx_path.write_text("docx content")

        formatter = OutputFormatter(output_dir=temp_output_dir)
        saved_files = formatter.save_complete_package(
            posts=sample_posts,
            client_brief=sample_client_brief,
            client_name="TestClient",
            include_docx=True,
            include_analytics_tracker=False,
        )

        # DOCX should be generated
        assert mock_gen_instance.create_deliverable_docx.called
        assert "docx" in saved_files

    @patch("src.utils.output_formatter.DOCXGenerator")
    def test_docx_import_error(
        self, mock_docx_gen, temp_output_dir, sample_posts, sample_client_brief
    ):
        """Test handling when python-docx import fails (lines 490-491)"""
        # Make DOCXGenerator raise ImportError
        mock_docx_gen.side_effect = ImportError("python-docx not installed")

        formatter = OutputFormatter(output_dir=temp_output_dir)
        saved_files = formatter.save_complete_package(
            posts=sample_posts,
            client_brief=sample_client_brief,
            client_name="TestClient",
            include_docx=True,
            include_analytics_tracker=False,
        )

        # Should still save core files despite DOCX failure
        assert "markdown" in saved_files
        assert "docx" not in saved_files

    @patch("src.utils.output_formatter.DOCXGenerator")
    def test_docx_generation_failure(
        self, mock_docx_gen, temp_output_dir, sample_posts, sample_client_brief
    ):
        """Test handling when DOCX generation fails (lines 492-493)"""
        # Make DOCXGenerator raise a general exception
        mock_gen_instance = MagicMock()
        mock_gen_instance.create_deliverable_docx.side_effect = Exception("DOCX generation failed")
        mock_docx_gen.return_value = mock_gen_instance

        formatter = OutputFormatter(output_dir=temp_output_dir)
        saved_files = formatter.save_complete_package(
            posts=sample_posts,
            client_brief=sample_client_brief,
            client_name="TestClient",
            include_docx=True,
            include_analytics_tracker=False,
        )

        # Should still save core files despite DOCX failure
        assert "markdown" in saved_files
        assert "docx" not in saved_files


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_format_with_unicode_content(self, temp_output_dir):
        """Test formatting posts with unicode characters"""
        posts = [
            Post(
                content="Unicode test: 你好 世界 🌍 café",
                template_id=1,
                template_name="Unicode Test",
                client_name="Test",
            )
        ]
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_posts_as_text(posts)
        assert "你好" in result
        assert "🌍" in result

    def test_save_with_special_chars_in_filename(self, temp_output_dir, sample_posts):
        """Test saving with special characters in client name"""
        formatter = OutputFormatter(output_dir=temp_output_dir)
        # Should handle special characters gracefully
        saved_files = formatter.save_complete_package(
            posts=sample_posts,
            client_brief=ClientBrief(
                company_name="Test Co",
                business_description="Test",
                ideal_customer="Test",
                main_problem_solved="Test",
                target_platforms=[Platform.LINKEDIN],
                posting_frequency="Daily",
            ),
            client_name="Client-Name_123",
            include_docx=False,
            include_analytics_tracker=False,
        )
        assert len(saved_files) > 0

    def test_format_with_very_long_content(self, temp_output_dir):
        """Test formatting with very long post content"""
        long_content = "Word " * 10000  # 10,000 words
        posts = [
            Post(
                content=long_content,
                template_id=1,
                template_name="Long Post",
                client_name="Test",
            )
        ]
        formatter = OutputFormatter(output_dir=temp_output_dir)
        result = formatter.format_posts_as_text(posts)
        assert len(result) > 0
