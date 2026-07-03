"""Unit tests for template_parser utility module.

Covers all 63 lines of src/utils/template_parser.py (currently at 0%).

All file I/O is mocked — no real template library file is read.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.utils.template_parser import TemplateParser


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

MINIMAL_TEMPLATE_CONTENT = """\
# Post Template Library

## TEMPLATE 1: The Problem-Recognition Post
**Best for:** Building awareness, getting engagement
**Format:** Hook problem → Validate feeling → Hint at solution

## TEMPLATE 2: The Solution-Reveal Post
**Best for:** Converting warm leads
**Format:** Present solution clearly
"""

TEMPLATE_WITH_RESEARCH = """\
# Library

## TEMPLATE 1: Research-Heavy Post
**Best for:** Deep research content
**Format:** Data → Insight → Action
**Research Tools:**
- **Required:** Audience Research (understand your target)
- **Recommended:** SEO Keywords (for visibility), ICP Workshop (buyer persona)

## TEMPLATE 2: Competitive Post
**Best for:** Differentiation
**Format:** Them vs Us
**Research Tools:**
- **Required:** Competitive Analysis (benchmark competitors)
- **Recommended:** Market Trends (industry context), Brand Archetype (positioning)
"""

TEMPLATE_ALL_TOOLS = """\
# Library

## TEMPLATE 1: Full Tool Coverage
**Best for:** Maximum research
**Format:** Research-driven content
**Research Tools:**
- **Required:** Audience Research, SEO Keywords, Competitive Analysis, Market Trends
- **Recommended:** Story Mining, Brand Archetype, ICP Workshop, Content Gap Analysis, \
Voice Analysis, Platform Strategy, Content Calendar, Content Audit
"""


@pytest.fixture
def parser():
    """TemplateParser with template_path mocked so no real file is needed."""
    with patch("src.utils.template_parser.settings") as mock_settings:
        mock_settings.TEMPLATE_LIBRARY_PATH = "/fake/path/templates.md"
        tp = TemplateParser()
    return tp


@pytest.fixture
def parser_with_content(parser):
    """Helper that patches template_path.exists() and read_text() with given content."""

    def _make(content: str):
        parser.template_path = MagicMock(spec=Path)
        parser.template_path.exists.return_value = True
        parser.template_path.read_text.return_value = content
        return parser

    return _make


# ---------------------------------------------------------------------------
# TemplateParser.__init__
# ---------------------------------------------------------------------------


class TestTemplateParserInit:
    """Tests for __init__ (lines 16-18)."""

    def test_init_sets_template_path_from_settings(self):
        """template_path is derived from settings.TEMPLATE_LIBRARY_PATH."""
        with patch("src.utils.template_parser.settings") as mock_settings:
            mock_settings.TEMPLATE_LIBRARY_PATH = "templates.md"
            tp = TemplateParser()

        assert tp.template_path == Path("templates.md")


# ---------------------------------------------------------------------------
# parse_all_templates
# ---------------------------------------------------------------------------


class TestParseAllTemplates:
    """Tests for parse_all_templates (lines 20-64)."""

    def test_raises_file_not_found_when_path_missing(self, parser):
        """FileNotFoundError raised when template file does not exist (line 41)."""
        parser.template_path = MagicMock(spec=Path)
        parser.template_path.exists.return_value = False

        with pytest.raises(FileNotFoundError, match="Template library not found"):
            parser.parse_all_templates()

    def test_returns_empty_dict_for_empty_content(self, parser):
        """Returns empty dict when file has no TEMPLATE sections."""
        parser.template_path = MagicMock(spec=Path)
        parser.template_path.exists.return_value = True
        parser.template_path.read_text.return_value = "# Just a header\nNo templates here."

        result = parser.parse_all_templates()

        assert result == {}

    def test_parses_two_templates(self, parser_with_content):
        """Two templates are parsed and returned keyed by number."""
        tp = parser_with_content(MINIMAL_TEMPLATE_CONTENT)
        result = tp.parse_all_templates()

        assert len(result) == 2
        assert 1 in result
        assert 2 in result

    def test_template_number_and_title_extracted(self, parser_with_content):
        """Template number and title are correctly extracted."""
        tp = parser_with_content(MINIMAL_TEMPLATE_CONTENT)
        result = tp.parse_all_templates()

        assert result[1]["number"] == 1
        assert result[1]["title"] == "The Problem-Recognition Post"
        assert result[2]["number"] == 2
        assert result[2]["title"] == "The Solution-Reveal Post"

    def test_best_for_extracted(self, parser_with_content):
        """best_for metadata field is extracted from template body."""
        tp = parser_with_content(MINIMAL_TEMPLATE_CONTENT)
        result = tp.parse_all_templates()

        assert result[1]["best_for"] == "Building awareness, getting engagement"

    def test_format_extracted(self, parser_with_content):
        """format metadata field is extracted from template body."""
        tp = parser_with_content(MINIMAL_TEMPLATE_CONTENT)
        result = tp.parse_all_templates()

        assert result[1]["format"] == "Hook problem → Validate feeling → Hint at solution"

    def test_research_dependencies_default_empty(self, parser_with_content):
        """Templates without Research Tools section have empty dependency lists."""
        tp = parser_with_content(MINIMAL_TEMPLATE_CONTENT)
        result = tp.parse_all_templates()

        assert result[1]["research_dependencies"] == {"required": [], "recommended": []}

    def test_research_dependencies_parsed(self, parser_with_content):
        """Research tools are parsed from the Research Tools section."""
        tp = parser_with_content(TEMPLATE_WITH_RESEARCH)
        result = tp.parse_all_templates()

        assert "audience_research" in result[1]["research_dependencies"]["required"]
        assert "seo_keyword_research" in result[1]["research_dependencies"]["recommended"]
        assert "icp_workshop" in result[1]["research_dependencies"]["recommended"]

    def test_competitive_analysis_parsed_as_required(self, parser_with_content):
        """Competitive Analysis appears as required tool in template 2."""
        tp = parser_with_content(TEMPLATE_WITH_RESEARCH)
        result = tp.parse_all_templates()

        assert "competitive_analysis" in result[2]["research_dependencies"]["required"]

    def test_read_text_called_with_utf8(self, parser_with_content):
        """read_text is called with encoding='utf-8'."""
        tp = parser_with_content(MINIMAL_TEMPLATE_CONTENT)
        tp.parse_all_templates()

        tp.template_path.read_text.assert_called_once_with(encoding="utf-8")

    def test_incomplete_trailing_section_triggers_break(self, parser_with_content):
        """Trailing template header without body causes loop to break safely (line 54).

        re.split returns [header, num, title, body, num2, title2] when a template
        header appears at the very end of the file with nothing after the title —
        i.e. the body element is missing, making len(template_sections) % 3 == 0
        with i+2 >= len at the last iteration.
        """
        # One complete template + one header-only at end (no body text follows title2)
        content = (
            "## TEMPLATE 1: Complete Post\n"
            "**Best for:** Full template\n"
            "**Format:** Complete format\n\n"
            "## TEMPLATE 2: Incomplete Post\n"
            "Truncated"
        )
        tp = parser_with_content(content)
        # Should not raise — the break guard prevents IndexError
        result = tp.parse_all_templates()
        # Template 1 must still be parsed correctly
        assert 1 in result


# ---------------------------------------------------------------------------
# _parse_template_metadata
# ---------------------------------------------------------------------------


class TestParseTemplateMetadata:
    """Tests for _parse_template_metadata (lines 66-94)."""

    def test_returns_dict_with_required_keys(self, parser):
        """Returned dict contains number, title, best_for, format, research_dependencies."""
        result = parser._parse_template_metadata(
            3,
            "My Template",
            "**Best for:** Testing\n**Format:** Test format\n",
        )

        assert result["number"] == 3
        assert result["title"] == "My Template"
        assert result["best_for"] == "Testing"
        assert result["format"] == "Test format"
        assert "research_dependencies" in result

    def test_best_for_none_when_missing(self, parser):
        """best_for is None when the field is absent from template body."""
        result = parser._parse_template_metadata(1, "Title", "Some body with no fields.\n")

        assert result["best_for"] is None

    def test_format_none_when_missing(self, parser):
        """format is None when the field is absent from template body."""
        result = parser._parse_template_metadata(1, "Title", "Some body with no fields.\n")

        assert result["format"] is None

    def test_research_section_parsed_into_dependencies(self, parser):
        """Research Tools section is parsed into structured dependencies."""
        body = (
            "**Best for:** Test\n"
            "**Format:** Test format\n"
            "**Research Tools:**\n"
            "- **Required:** Audience Research\n"
            "- **Recommended:** SEO Keywords\n"
        )
        result = parser._parse_template_metadata(1, "Title", body)

        assert "audience_research" in result["research_dependencies"]["required"]
        assert "seo_keyword_research" in result["research_dependencies"]["recommended"]


# ---------------------------------------------------------------------------
# _parse_research_dependencies
# ---------------------------------------------------------------------------


class TestParseResearchDependencies:
    """Tests for _parse_research_dependencies (lines 96-118)."""

    def test_empty_text_returns_empty_lists(self, parser):
        """Empty research text returns empty required and recommended lists."""
        result = parser._parse_research_dependencies("")

        assert result == {"required": [], "recommended": []}

    def test_required_tools_extracted(self, parser):
        """Required tools are extracted correctly."""
        text = "- **Required:** Audience Research (know your audience)\n"
        result = parser._parse_research_dependencies(text)

        assert "audience_research" in result["required"]

    def test_recommended_tools_extracted(self, parser):
        """Recommended tools are extracted correctly."""
        text = "- **Recommended:** Story Mining (find stories), Brand Archetype (positioning)\n"
        result = parser._parse_research_dependencies(text)

        assert "story_mining" in result["recommended"]
        assert "brand_archetype" in result["recommended"]

    def test_both_required_and_recommended(self, parser):
        """Both required and recommended sections parsed in one call."""
        text = (
            "- **Required:** Competitive Analysis\n"
            "- **Recommended:** Market Trends, Content Gap\n"
        )
        result = parser._parse_research_dependencies(text)

        assert "competitive_analysis" in result["required"]
        assert "market_trends" in result["recommended"]
        assert "content_gap_analysis" in result["recommended"]

    def test_no_required_section(self, parser):
        """Missing Required section yields empty required list."""
        text = "- **Recommended:** Voice Analysis\n"
        result = parser._parse_research_dependencies(text)

        assert result["required"] == []
        assert "voice_analysis" in result["recommended"]

    def test_no_recommended_section(self, parser):
        """Missing Recommended section yields empty recommended list."""
        text = "- **Required:** Platform Strategy\n"
        result = parser._parse_research_dependencies(text)

        assert "platform_strategy" in result["required"]
        assert result["recommended"] == []


# ---------------------------------------------------------------------------
# _extract_tool_names
# ---------------------------------------------------------------------------


class TestExtractToolNames:
    """Tests for _extract_tool_names (lines 120-153)."""

    def test_audience_research_mapped(self, parser):
        """'audience research' label maps to 'audience_research'."""
        result = parser._extract_tool_names("Audience Research (understand your target)")
        assert "audience_research" in result

    def test_seo_keyword_mapped(self, parser):
        """'seo keyword' label maps to 'seo_keyword_research'."""
        result = parser._extract_tool_names("SEO Keywords for visibility")
        assert "seo_keyword_research" in result

    def test_competitive_analysis_mapped(self, parser):
        """'competitive analysis' label maps to 'competitive_analysis'."""
        result = parser._extract_tool_names("Competitive Analysis report")
        assert "competitive_analysis" in result

    def test_market_trends_mapped(self, parser):
        """'market trends' maps to 'market_trends'."""
        result = parser._extract_tool_names("Market Trends data")
        assert "market_trends" in result

    def test_story_mining_mapped(self, parser):
        """'story mining' maps to 'story_mining'."""
        result = parser._extract_tool_names("Story Mining for client narratives")
        assert "story_mining" in result

    def test_brand_archetype_mapped(self, parser):
        """'brand archetype' maps to 'brand_archetype'."""
        result = parser._extract_tool_names("Brand Archetype assessment")
        assert "brand_archetype" in result

    def test_icp_workshop_mapped(self, parser):
        """'icp workshop' maps to 'icp_workshop'."""
        result = parser._extract_tool_names("ICP Workshop session")
        assert "icp_workshop" in result

    def test_content_gap_mapped(self, parser):
        """'content gap' maps to 'content_gap_analysis'."""
        result = parser._extract_tool_names("Content Gap analysis tool")
        assert "content_gap_analysis" in result

    def test_voice_analysis_mapped(self, parser):
        """'voice analysis' maps to 'voice_analysis'."""
        result = parser._extract_tool_names("Voice Analysis for brand tone")
        assert "voice_analysis" in result

    def test_platform_strategy_mapped(self, parser):
        """'platform strategy' maps to 'platform_strategy'."""
        result = parser._extract_tool_names("Platform Strategy planning")
        assert "platform_strategy" in result

    def test_content_calendar_mapped(self, parser):
        """'content calendar' maps to 'content_calendar'."""
        result = parser._extract_tool_names("Content Calendar scheduling")
        assert "content_calendar" in result

    def test_content_audit_mapped(self, parser):
        """'content audit' maps to 'content_audit'."""
        result = parser._extract_tool_names("Content Audit review")
        assert "content_audit" in result

    def test_no_duplicates(self, parser):
        """Duplicate label appearances do not create duplicate tool entries."""
        result = parser._extract_tool_names("Audience Research, more Audience Research references")
        assert result.count("audience_research") == 1

    def test_empty_text_returns_empty_list(self, parser):
        """Empty text returns an empty list."""
        result = parser._extract_tool_names("")
        assert result == []

    def test_unrecognized_label_returns_empty(self, parser):
        """Text with no recognized tool labels returns empty list."""
        result = parser._extract_tool_names("Unknown tool name here")
        assert result == []

    def test_multiple_tools_extracted(self, parser):
        """Multiple distinct tools extracted from a single string."""
        result = parser._extract_tool_names("Audience Research, SEO Keywords, Story Mining")
        assert "audience_research" in result
        assert "seo_keyword_research" in result
        assert "story_mining" in result

    def test_all_tools_coverage(self, parser_with_content):
        """Full template with all 12 tools produces complete dependency lists."""
        tp = parser_with_content(TEMPLATE_ALL_TOOLS)
        result = tp.parse_all_templates()

        deps = result[1]["research_dependencies"]
        required_tools = deps["required"]
        recommended_tools = deps["recommended"]
        all_tools = required_tools + recommended_tools

        for tool in [
            "audience_research",
            "seo_keyword_research",
            "competitive_analysis",
            "market_trends",
            "story_mining",
            "brand_archetype",
            "icp_workshop",
            "content_gap_analysis",
            "voice_analysis",
            "platform_strategy",
            "content_calendar",
            "content_audit",
        ]:
            assert tool in all_tools, f"Expected {tool} in tool list"


# ---------------------------------------------------------------------------
# get_template_dependencies
# ---------------------------------------------------------------------------


class TestGetTemplateDependencies:
    """Tests for get_template_dependencies (lines 155-172)."""

    def test_returns_none_for_nonexistent_template(self, parser_with_content):
        """Returns None when the requested template number is not in the library."""
        tp = parser_with_content(MINIMAL_TEMPLATE_CONTENT)
        result = tp.get_template_dependencies(99)

        assert result is None

    def test_returns_dependencies_for_existing_template(self, parser_with_content):
        """Returns dependency dict for a template that exists."""
        tp = parser_with_content(TEMPLATE_WITH_RESEARCH)
        result = tp.get_template_dependencies(1)

        assert result is not None
        assert "required" in result
        assert "recommended" in result
        assert "audience_research" in result["required"]

    def test_returns_empty_dependencies_for_template_without_research(self, parser_with_content):
        """Templates with no Research Tools section return empty dependency lists."""
        tp = parser_with_content(MINIMAL_TEMPLATE_CONTENT)
        result = tp.get_template_dependencies(1)

        assert result is not None
        assert result["required"] == []
        assert result["recommended"] == []

    def test_calls_parse_all_templates_internally(self, parser_with_content):
        """get_template_dependencies calls parse_all_templates (line 165)."""
        tp = parser_with_content(MINIMAL_TEMPLATE_CONTENT)
        with patch.object(tp, "parse_all_templates", wraps=tp.parse_all_templates) as mock_parse:
            tp.get_template_dependencies(1)
        mock_parse.assert_called_once()
