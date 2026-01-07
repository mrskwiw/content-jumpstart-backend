"""Unit tests for ResearchTool base class utility methods

Tests the new Claude API utility methods added in Phase 3 Task 4:
- _call_claude_api()
- _extract_json_from_response()

These methods eliminate ~340 lines of duplicate code across 12 research tools.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.research.base import ResearchTool


class MockResearchTool(ResearchTool):
    """Mock research tool for testing base class methods"""

    @property
    def tool_name(self) -> str:
        return "mock_tool"

    @property
    def price(self) -> int:
        return 100

    def validate_inputs(self, inputs):
        return True

    def run_analysis(self, inputs):
        return {"result": "test"}

    def generate_reports(self, analysis):
        return {}


class TestExtractJsonFromResponse:
    """Test JSON extraction from various response formats"""

    def test_extract_raw_json(self):
        """Test extraction of raw JSON"""
        tool = MockResearchTool(project_id="test")
        response = '{"market": "B2B SaaS", "competitors": ["A", "B"]}'

        result = tool._extract_json_from_response(response)

        assert result == {"market": "B2B SaaS", "competitors": ["A", "B"]}

    def test_extract_from_markdown_code_block(self):
        """Test extraction from markdown ```json``` blocks"""
        tool = MockResearchTool(project_id="test")
        response = """Here is the analysis:

```json
{
  "market": "B2B SaaS",
  "trends": ["AI", "Automation"]
}
```

Let me know if you need more details."""

        result = tool._extract_json_from_response(response)

        assert result == {"market": "B2B SaaS", "trends": ["AI", "Automation"]}

    def test_extract_from_markdown_without_language(self):
        """Test extraction from markdown code blocks without json language tag"""
        tool = MockResearchTool(project_id="test")
        response = """```
{"competitors": ["CompanyA", "CompanyB"]}
```"""

        result = tool._extract_json_from_response(response)

        assert result == {"competitors": ["CompanyA", "CompanyB"]}

    def test_extract_embedded_json(self):
        """Test extraction of JSON embedded in text"""
        tool = MockResearchTool(project_id="test")
        response = 'Here are the results: {"keywords": ["SEO", "content"]} as requested.'

        result = tool._extract_json_from_response(response)

        assert result == {"keywords": ["SEO", "content"]}

    def test_no_valid_json_raises_error(self):
        """Test that invalid responses raise ValueError"""
        tool = MockResearchTool(project_id="test")
        response = "This is just plain text with no JSON at all."

        with pytest.raises(ValueError) as exc_info:
            tool._extract_json_from_response(response)

        assert "Could not extract valid JSON" in str(exc_info.value)


class TestCallClaudeApi:
    """Test unified Claude API call method"""

    @patch("src.research.base.get_default_client")
    def test_call_api_returns_text(self, mock_get_client):
        """Test API call returns raw text when extract_json=False"""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This is the analysis result.")]
        mock_client.create_message.return_value = mock_response
        mock_get_client.return_value = mock_client

        tool = MockResearchTool(project_id="test")

        result = tool._call_claude_api("Analyze this business", extract_json=False)

        assert result == "This is the analysis result."
        mock_client.create_message.assert_called_once()

    @patch("src.research.base.get_default_client")
    def test_call_api_extracts_json(self, mock_get_client):
        """Test API call extracts and returns JSON when extract_json=True"""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"market": "B2B", "size": 1000}')]
        mock_client.create_message.return_value = mock_response
        mock_get_client.return_value = mock_client

        tool = MockResearchTool(project_id="test")

        result = tool._call_claude_api("Analyze this business", extract_json=True)

        assert result == {"market": "B2B", "size": 1000}

    @patch("src.research.base.get_default_client")
    def test_call_api_uses_custom_parameters(self, mock_get_client):
        """Test API call uses custom max_tokens and temperature"""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Result")]
        mock_client.create_message.return_value = mock_response
        mock_get_client.return_value = mock_client

        tool = MockResearchTool(project_id="test")

        tool._call_claude_api("Test prompt", max_tokens=5000, temperature=0.8)

        # Verify API was called with correct parameters
        call_args = mock_client.create_message.call_args
        assert call_args.kwargs["max_tokens"] == 5000
        assert call_args.kwargs["temperature"] == 0.8

    @patch("src.research.base.get_default_client")
    def test_call_api_with_fallback_on_error(self, mock_get_client):
        """Test API call returns fallback value on error"""
        # Setup mock to raise error
        mock_client = MagicMock()
        mock_client.create_message.side_effect = Exception("API Error")
        mock_get_client.return_value = mock_client

        tool = MockResearchTool(project_id="test")

        fallback = {"error": "Analysis failed", "competitors": []}
        result = tool._call_claude_api(
            "Analyze competitors", extract_json=True, fallback_on_error=fallback
        )

        assert result == fallback

    @patch("src.research.base.get_default_client")
    def test_call_api_raises_without_fallback(self, mock_get_client):
        """Test API call raises exception when no fallback specified"""
        # Setup mock to raise error
        mock_client = MagicMock()
        mock_client.create_message.side_effect = Exception("API Error")
        mock_get_client.return_value = mock_client

        tool = MockResearchTool(project_id="test")

        with pytest.raises(Exception) as exc_info:
            tool._call_claude_api("Analyze business")

        assert "API Error" in str(exc_info.value)


class TestCreateMarkdownHeader:
    """Test markdown header creation"""

    def test_level_1_header(self):
        """Test creating a level 1 header"""
        tool = MockResearchTool(project_id="test")

        result = tool._create_markdown_header("Executive Summary", level=1)

        assert result == "# Executive Summary\n\n"

    def test_level_2_header(self):
        """Test creating a level 2 header"""
        tool = MockResearchTool(project_id="test")

        result = tool._create_markdown_header("Key Findings", level=2)

        assert result == "## Key Findings\n\n"

    def test_level_3_header_no_spacing(self):
        """Test creating a header without spacing"""
        tool = MockResearchTool(project_id="test")

        result = tool._create_markdown_header("Notes", level=3, add_spacing=False)

        assert result == "### Notes\n"

    def test_level_6_header(self):
        """Test creating a level 6 header (maximum)"""
        tool = MockResearchTool(project_id="test")

        result = tool._create_markdown_header("Detail", level=6)

        assert result == "###### Detail\n\n"

    def test_invalid_level_raises_error(self):
        """Test that invalid header levels raise ValueError"""
        tool = MockResearchTool(project_id="test")

        with pytest.raises(ValueError) as exc_info:
            tool._create_markdown_header("Test", level=7)

        assert "must be 1-6" in str(exc_info.value)

    def test_zero_level_raises_error(self):
        """Test that level 0 raises ValueError"""
        tool = MockResearchTool(project_id="test")

        with pytest.raises(ValueError) as exc_info:
            tool._create_markdown_header("Test", level=0)

        assert "must be 1-6" in str(exc_info.value)


class TestFormatMarkdownList:
    """Test markdown list formatting"""

    def test_unordered_list(self):
        """Test creating a bullet list"""
        tool = MockResearchTool(project_id="test")
        items = ["First item", "Second item", "Third item"]

        result = tool._format_markdown_list(items)

        assert result == "- First item\n- Second item\n- Third item\n"

    def test_ordered_list(self):
        """Test creating a numbered list"""
        tool = MockResearchTool(project_id="test")
        items = ["First", "Second", "Third"]

        result = tool._format_markdown_list(items, ordered=True)

        assert result == "1. First\n2. Second\n3. Third\n"

    def test_indented_list(self):
        """Test creating an indented list"""
        tool = MockResearchTool(project_id="test")
        items = ["Item A", "Item B"]

        result = tool._format_markdown_list(items, indent_level=2)

        assert result == "  - Item A\n  - Item B\n"

    def test_empty_list(self):
        """Test that empty list returns empty string"""
        tool = MockResearchTool(project_id="test")

        result = tool._format_markdown_list([])

        assert result == ""

    def test_custom_formatter(self):
        """Test using a custom item formatter"""
        tool = MockResearchTool(project_id="test")
        items = ["important", "critical", "urgent"]

        def bold_formatter(item):
            return f"**{item}**"

        result = tool._format_markdown_list(items, item_formatter=bold_formatter)

        assert result == "- **important**\n- **critical**\n- **urgent**\n"

    def test_ordered_list_with_indent(self):
        """Test ordered list with indentation"""
        tool = MockResearchTool(project_id="test")
        items = ["Sub-task A", "Sub-task B"]

        result = tool._format_markdown_list(items, ordered=True, indent_level=4)

        assert result == "    1. Sub-task A\n    2. Sub-task B\n"

    def test_non_string_items(self):
        """Test formatting non-string items (integers)"""
        tool = MockResearchTool(project_id="test")
        items = [100, 200, 300]

        result = tool._format_markdown_list(items)

        assert result == "- 100\n- 200\n- 300\n"

    def test_complex_custom_formatter(self):
        """Test custom formatter with complex objects"""
        tool = MockResearchTool(project_id="test")
        items = [
            {"name": "Task 1", "priority": "high"},
            {"name": "Task 2", "priority": "low"},
        ]

        def task_formatter(task):
            return f"{task['name']} (Priority: {task['priority']})"

        result = tool._format_markdown_list(items, item_formatter=task_formatter)

        expected = "- Task 1 (Priority: high)\n" "- Task 2 (Priority: low)\n"
        assert result == expected
