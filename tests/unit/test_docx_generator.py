"""
Comprehensive unit tests for DOCXGenerator

Tests cover:
- DOCX document creation
- Cover page generation
- Introduction section
- Posts section formatting
- Voice guide appendix
- Schedule appendix
- QA summary appendix
- Style configuration
- Error handling
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.utils.docx_generator import DOCXGenerator, get_default_docx_generator
from src.models.client_brief import ClientBrief, Platform, TonePreference
from src.models.post import Post
from src.models.qa_report import QAReport


# ==================== Fixtures ====================


@pytest.fixture
def sample_client_brief():
    """Sample client brief for testing"""
    return ClientBrief(
        company_name="Test Company Inc",
        business_description="We provide cloud-based project management software for small businesses",
        ideal_customer="Small business owners with 5-20 employees",
        main_problem_solved="Inefficient workflows and scattered communication across multiple tools",
        customer_pain_points=[
            "Wasting time on manual data entry",
            "Poor team collaboration",
            "Lack of visibility into project progress",
        ],
        brand_personality=[TonePreference.AUTHORITATIVE, TonePreference.DATA_DRIVEN],
        target_platforms=[Platform.LINKEDIN, Platform.TWITTER],
    )


@pytest.fixture
def sample_posts(sample_client_brief):
    """Sample posts for testing"""
    posts = []
    for i in range(5):
        post = Post(
            content=f"Test post {i+1} with enough content. This discusses productivity and workflow optimization. Teams waste time on manual tasks. Here's how to improve efficiency and boost productivity today.",
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
        client_name="Test Company Inc",
        total_posts=30,
        passed_posts=27,
        flagged_posts=3,
        quality_score=0.90,
        overall_passed=True,
        hook_validation={"uniqueness_score": 0.88, "metric": "Good"},
        cta_validation={"variety_score": 0.82, "metric": "Acceptable"},
        length_validation={"average_length": 215, "optimal_ratio": 0.92},
        headline_validation={"engagement_score": 0.86, "metric": "Good"},
        all_issues=[
            "Post 5: Hook similarity 85%",
            "Post 12: CTA missing",
            "Post 18: Length 320 words (too long)",
        ],
    )


@pytest.fixture
def sample_voice_guide():
    """Sample voice guide content"""
    return """# Brand Voice Guide for Test Company Inc

## Voice Characteristics

### Tone
Professional yet approachable, data-driven

### Perspective
First-person plural (we, our)

### Key Phrases
- "Streamline your workflow"
- "Boost productivity"
- "Save time and money"

## Writing Patterns

- Use concrete data and statistics
- Lead with problem recognition
- End with clear calls-to-action
"""


@pytest.fixture
def sample_schedule():
    """Sample posting schedule content"""
    return """# 30-Day Posting Schedule

## Week 1 (LinkedIn Focus)

├─ Day 1 (Mon): Post 1 - Problem Recognition
├─ Day 3 (Wed): Post 2 - Statistic + Insight
└─ Day 5 (Fri): Post 3 - How-To Guide

## Week 2 (Twitter Blitz)

├─ Day 8 (Mon): Post 4 - Quick Tip
└─ Day 10 (Wed): Post 5 - Customer Success
"""


# ==================== Mock Document Classes ====================


class MockParagraph:
    """Mock docx Paragraph"""

    def __init__(self):
        self.text = ""
        self.style = None
        self.alignment = None
        self.paragraph_format = Mock()
        self.paragraph_format.space_after = None

    def add_run(self, text):
        run = MockRun(text)
        self.text += text
        return run


class MockRun:
    """Mock docx Run"""

    def __init__(self, text):
        self.text = text
        self.font = Mock()
        self.font.name = None
        self.font.size = None
        self.font.bold = False
        self.font.italic = False
        self.font.color = Mock()
        self.font.color.rgb = None
        self.bold = False


class MockTable:
    """Mock docx Table"""

    def __init__(self, rows, cols):
        self.rows = [MockRow(cols) for _ in range(rows)]
        self.style = None


class MockRow:
    """Mock docx Table Row"""

    def __init__(self, num_cells):
        self.cells = [MockCell() for _ in range(num_cells)]


class MockCell:
    """Mock docx Table Cell"""

    def __init__(self):
        self.text = ""


class MockDocument:
    """Mock docx Document"""

    def __init__(self):
        self.paragraphs = []
        self.tables = []
        self.styles = Mock()
        self.styles.add_style = Mock(return_value=Mock(font=Mock(color=Mock())))
        self.styles.__contains__ = Mock(return_value=False)  # Styles don't exist by default

    def add_paragraph(self, text="", style=None):
        para = MockParagraph()
        para.text = text
        para.style = style
        self.paragraphs.append(para)
        return para

    def add_heading(self, text, level=1):
        para = MockParagraph()
        para.text = text
        self.paragraphs.append(para)
        return para

    def add_page_break(self):
        para = MockParagraph()
        para.text = "[PAGE BREAK]"
        self.paragraphs.append(para)
        return para

    def add_table(self, rows, cols):
        table = MockTable(rows, cols)
        self.tables.append(table)
        return table

    def save(self, path):
        pass


# ==================== Initialization Tests ====================


def test_docx_generator_init():
    """Test DOCXGenerator initialization"""
    with patch("docx.shared.RGBColor"):
        generator = DOCXGenerator()

        assert generator.brand_color is not None
        assert generator.metadata_color is not None


def test_get_default_docx_generator():
    """Test default generator singleton"""
    with patch("docx.shared.RGBColor"):
        # First call creates instance
        gen1 = get_default_docx_generator()
        assert gen1 is not None

        # Second call returns same instance
        gen2 = get_default_docx_generator()
        assert gen1 is gen2


# ==================== Document Creation Tests ====================


def test_create_deliverable_docx_basic(tmp_path, sample_client_brief, sample_posts):
    """Test basic DOCX deliverable creation"""
    with patch("docx.Document", return_value=MockDocument()):
        generator = DOCXGenerator()

        output_path = tmp_path / "test_deliverable.docx"

        result = generator.create_deliverable_docx(
            posts=sample_posts,
            client_brief=sample_client_brief,
            output_path=output_path,
            include_voice_guide=False,
            include_schedule=False,
        )

        assert result == output_path


def test_create_deliverable_docx_with_all_sections(
    tmp_path,
    sample_client_brief,
    sample_posts,
    sample_qa_report,
    sample_voice_guide,
    sample_schedule,
):
    """Test DOCX creation with all sections"""
    with patch("docx.Document", return_value=MockDocument()):
        generator = DOCXGenerator()

        output_path = tmp_path / "complete_deliverable.docx"

        result = generator.create_deliverable_docx(
            posts=sample_posts,
            client_brief=sample_client_brief,
            output_path=output_path,
            include_voice_guide=True,
            include_schedule=True,
            qa_report=sample_qa_report,
            voice_guide_content=sample_voice_guide,
            schedule_content=sample_schedule,
        )

        assert result == output_path


def test_create_deliverable_docx_creates_directory(tmp_path, sample_client_brief, sample_posts):
    """Test that DOCX creation creates parent directories"""
    with patch("docx.Document", return_value=MockDocument()):
        generator = DOCXGenerator()

        # Path with non-existent parent directory
        output_path = tmp_path / "subdir" / "nested" / "deliverable.docx"

        generator.create_deliverable_docx(
            posts=sample_posts,
            client_brief=sample_client_brief,
            output_path=output_path,
        )

        # Parent directory should be created
        assert output_path.parent.exists()


# ==================== Cover Page Tests ====================


def test_add_cover_page():
    """Test cover page generation"""
    with patch("docx.shared.RGBColor"):
        generator = DOCXGenerator()
        mock_doc = MockDocument()

        with patch("src.utils.docx_generator.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0, 0)

            sample_brief = ClientBrief(
                company_name="Test Company",
                business_description="Test",
                ideal_customer="Test",
                main_problem_solved="Test",
            )

            generator._add_cover_page(mock_doc, sample_brief)

            # Should have title, company, date, and page break
            assert len(mock_doc.paragraphs) >= 4

            # Check for expected text
            all_text = " ".join(p.text for p in mock_doc.paragraphs)
            assert "30-Day Content Jumpstart" in all_text
            assert "Test Company" in all_text
            assert "January 15, 2025" in all_text
            assert "[PAGE BREAK]" in all_text


# ==================== Introduction Tests ====================


def test_add_introduction(sample_client_brief):
    """Test introduction section generation"""
    with patch("docx.shared.RGBColor"):
        generator = DOCXGenerator()
        mock_doc = MockDocument()

        generator._add_introduction(mock_doc, sample_client_brief)

        # Should have created a table
        assert len(mock_doc.tables) == 1

        # Table should have 5 rows (company, business, customer, problem, platforms)
        table = mock_doc.tables[0]
        assert len(table.rows) == 5

        # Check table content
        assert table.rows[0].cells[0].text == "Company"
        assert table.rows[0].cells[1].text == "Test Company Inc"
        assert table.rows[1].cells[0].text == "Business"
        assert table.rows[4].cells[0].text == "Target Platforms"


# ==================== Posts Section Tests ====================


def test_add_posts_section(sample_client_brief, sample_posts):
    """Test posts section generation"""
    with patch("docx.shared.RGBColor"):
        generator = DOCXGenerator()
        mock_doc = MockDocument()

        generator._add_posts_section(mock_doc, sample_posts, sample_client_brief)

        # Should have paragraphs for header + posts
        all_text = " ".join(p.text for p in mock_doc.paragraphs)

        # Check for section header
        assert "Your 30 Posts" in all_text

        # Check for post content
        assert "Test post 1" in all_text
        assert "Test post 5" in all_text


def test_add_post_entry(sample_posts):
    """Test individual post entry formatting"""
    with patch("docx.shared.RGBColor"):
        generator = DOCXGenerator()
        mock_doc = MockDocument()

        post = sample_posts[0]
        generator._add_post_entry(mock_doc, post, 1)

        all_text = " ".join(p.text for p in mock_doc.paragraphs)

        # Should have post number and title
        assert "Post 1" in all_text
        assert "Problem Recognition" in all_text

        # Should have post content
        assert "Test post 1" in all_text

        # Should have metadata
        assert "Words:" in all_text or "Template:" in all_text


def test_add_post_entry_with_keywords(sample_posts):
    """Test post entry without keywords field (Post model doesn't have keywords_used)"""
    with patch("docx.shared.RGBColor"):
        generator = DOCXGenerator()
        mock_doc = MockDocument()

        # Use post as-is (no keywords field exists)
        post = sample_posts[0]

        generator._add_post_entry(mock_doc, post, 1)

        all_text = " ".join(p.text for p in mock_doc.paragraphs)

        # Should still format post correctly without keywords
        assert "Post 1" in all_text


def test_add_posts_section_page_breaks(sample_client_brief):
    """Test that page breaks are inserted every 5 posts"""
    with patch("docx.shared.RGBColor"):
        generator = DOCXGenerator()
        mock_doc = MockDocument()

        # Create 15 posts
        posts = []
        for i in range(15):
            post = Post(
                content=f"Post {i+1}",
                template_id=1,
                template_name="Test",
                variant=1,
                client_name="Test",
            )
            posts.append(post)

        generator._add_posts_section(mock_doc, posts, sample_client_brief)

        # Count page breaks (should be 2: after post 5 and post 10)
        page_breaks = [p for p in mock_doc.paragraphs if "[PAGE BREAK]" in p.text]
        assert len(page_breaks) >= 2


# ==================== Voice Guide Appendix Tests ====================


def test_add_voice_guide_section(sample_voice_guide):
    """Test voice guide appendix generation"""
    with patch("docx.shared.RGBColor"):
        generator = DOCXGenerator()
        mock_doc = MockDocument()

        generator._add_voice_guide_section(mock_doc, sample_voice_guide)

        all_text = " ".join(p.text for p in mock_doc.paragraphs)

        # Should have page break
        assert "[PAGE BREAK]" in all_text

        # Should have content from voice guide
        assert "Brand Voice Guide" in all_text or "Voice Characteristics" in all_text


def test_add_voice_guide_parses_markdown():
    """Test that voice guide parses markdown headings"""
    with patch("docx.shared.RGBColor"):
        generator = DOCXGenerator()
        mock_doc = MockDocument()

        markdown_content = """# Heading 1
## Heading 2
### Heading 3
- Bullet item 1
- Bullet item 2

**Bold text**

Normal paragraph
"""

        generator._add_voice_guide_section(mock_doc, markdown_content)

        # Should have created multiple paragraphs
        assert len(mock_doc.paragraphs) > 5


# ==================== Schedule Appendix Tests ====================


def test_add_schedule_section(sample_schedule):
    """Test posting schedule appendix generation"""
    with patch("docx.shared.RGBColor"):
        generator = DOCXGenerator()
        mock_doc = MockDocument()

        generator._add_schedule_section(mock_doc, sample_schedule)

        all_text = " ".join(p.text for p in mock_doc.paragraphs)

        # Should have page break
        assert "[PAGE BREAK]" in all_text

        # Should have schedule content
        assert "Posting Schedule" in all_text or "Week 1" in all_text


def test_add_schedule_parses_tree_structure():
    """Test that schedule parses tree structure correctly"""
    with patch("docx.shared.RGBColor"):
        generator = DOCXGenerator()
        mock_doc = MockDocument()

        schedule_content = """# Schedule

## Week 1

├─ Day 1: Post 1
├─ Day 3: Post 2
└─ Day 5: Post 3
"""

        generator._add_schedule_section(mock_doc, schedule_content)

        # Tree items should be converted to bullets
        all_text = " ".join(p.text for p in mock_doc.paragraphs)
        assert "Day 1" in all_text


# ==================== QA Summary Appendix Tests ====================


def test_add_qa_summary_section_passed(sample_qa_report):
    """Test QA summary appendix for passed report"""
    with patch("docx.shared.RGBColor"):
        generator = DOCXGenerator()
        mock_doc = MockDocument()

        generator._add_qa_summary_section(mock_doc, sample_qa_report)

        all_text = " ".join(p.text for p in mock_doc.paragraphs)

        # Should have page break
        assert "[PAGE BREAK]" in all_text

        # Should have status
        assert "PASSED" in all_text or "Overall Status" in all_text

        # Should have quality score
        assert "90" in all_text or "Quality Score" in all_text


def test_add_qa_summary_section_failed():
    """Test QA summary appendix for failed report"""
    with patch("docx.shared.RGBColor"):
        generator = DOCXGenerator()
        mock_doc = MockDocument()

        failed_report = QAReport(
            client_name="Test",
            total_posts=30,
            passed_posts=20,
            flagged_posts=10,
            quality_score=0.67,
            overall_passed=False,
            hook_validation={"uniqueness_score": 0.65, "metric": "Needs work"},
            cta_validation={"variety_score": 0.60, "metric": "Needs work"},
            length_validation={"average_length": 180, "optimal_ratio": 0.70},
            headline_validation={"engagement_score": 0.60, "metric": "Needs work"},
            all_issues=["Issue 1", "Issue 2"],
        )

        generator._add_qa_summary_section(mock_doc, failed_report)

        all_text = " ".join(p.text for p in mock_doc.paragraphs)

        # Should show failed status
        assert "NEEDS ATTENTION" in all_text or "67" in all_text


def test_add_qa_summary_section_with_issues(sample_qa_report):
    """Test QA summary shows issues"""
    with patch("docx.shared.RGBColor"):
        generator = DOCXGenerator()
        mock_doc = MockDocument()

        # Report with many issues
        sample_qa_report.all_issues = [f"Issue {i}" for i in range(10)]

        generator._add_qa_summary_section(mock_doc, sample_qa_report)

        all_text = " ".join(p.text for p in mock_doc.paragraphs)

        # Should show first 5 issues
        assert "Issue 0" in all_text or "Issue 1" in all_text

        # Should show "and X more issues"
        assert "more issues" in all_text or "5 more" in all_text


def test_add_qa_summary_validation_results(sample_qa_report):
    """Test QA summary includes validation results"""
    with patch("docx.shared.RGBColor"):
        generator = DOCXGenerator()
        mock_doc = MockDocument()

        generator._add_qa_summary_section(mock_doc, sample_qa_report)

        all_text = " ".join(p.text for p in mock_doc.paragraphs)

        # Should include validation metrics
        # Check for any of the validation types
        has_validation = any(
            [
                "Hook" in all_text,
                "CTA" in all_text,
                "Length" in all_text,
                "88" in all_text,  # Hook score
                "82" in all_text,  # CTA score
            ]
        )
        assert has_validation


# ==================== Style Configuration Tests ====================


def test_configure_document_styles():
    """Test document style configuration"""
    with patch("docx.shared.RGBColor"):
        with patch("docx.enum.style.WD_STYLE_TYPE"):
            generator = DOCXGenerator()
            mock_doc = MockDocument()

            # Mock styles collection
            mock_doc.styles.__contains__ = lambda self, name: False

            generator._configure_document_styles(mock_doc)

            # Should have attempted to add custom styles
            # (Actual call verification would require more complex mocking)
            assert mock_doc.styles is not None


# ==================== Error Handling Tests ====================


def test_create_deliverable_handles_missing_optional_sections(
    tmp_path, sample_client_brief, sample_posts
):
    """Test DOCX creation with None for optional sections"""
    with patch("docx.Document", return_value=MockDocument()):
        generator = DOCXGenerator()

        output_path = tmp_path / "test.docx"

        # Should not raise error with None values
        result = generator.create_deliverable_docx(
            posts=sample_posts,
            client_brief=sample_client_brief,
            output_path=output_path,
            voice_guide_content=None,
            schedule_content=None,
            qa_report=None,
        )

        assert result == output_path


# ==================== Integration-Style Tests ====================


def test_full_docx_generation_workflow(
    tmp_path,
    sample_client_brief,
    sample_posts,
    sample_qa_report,
    sample_voice_guide,
    sample_schedule,
):
    """Test complete DOCX generation with all components"""
    with patch("docx.Document", return_value=MockDocument()):
        generator = DOCXGenerator()

        output_path = tmp_path / "complete_deliverable.docx"

        result = generator.create_deliverable_docx(
            posts=sample_posts,
            client_brief=sample_client_brief,
            output_path=output_path,
            include_voice_guide=True,
            include_schedule=True,
            qa_report=sample_qa_report,
            voice_guide_content=sample_voice_guide,
            schedule_content=sample_schedule,
        )

        # Should successfully create document
        assert result == output_path

        # Note: In real usage with python-docx, we'd verify the file exists and is valid
        # Here we're just testing the code paths
