"""Unit tests for backend.utils.cli_executor."""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from backend.utils.cli_executor import CLIExecutor, cli_executor


class TestParseOutputFiles:
    def test_no_match_returns_defaults(self):
        executor = CLIExecutor()
        out_dir, files = executor._parse_output_files("no matching output here")
        assert "unknown" in str(out_dir)
        assert files == {}

    def test_finds_output_dir_in_stdout(self, tmp_path):
        # Create a file the scanner can find
        deliverable = tmp_path / "test_deliverable.md"
        deliverable.write_text("content")

        executor = CLIExecutor()
        stdout = f"Deliverables saved to: {tmp_path}\nOther output"
        out_dir, files = executor._parse_output_files(stdout)
        assert str(tmp_path) in str(out_dir)
        assert "deliverable" in files

    def test_finds_posts_json(self, tmp_path):
        (tmp_path / "client_posts.json").write_text("{}")
        executor = CLIExecutor()
        stdout = f"Deliverables saved to: {tmp_path}"
        _, files = executor._parse_output_files(stdout)
        assert "posts_json" in files


class TestLoadPostsFromJson:
    def test_list_json(self, tmp_path):
        p = tmp_path / "posts.json"
        posts = [{"id": "1", "content": "Post 1"}, {"id": "2", "content": "Post 2"}]
        p.write_text(json.dumps(posts))
        executor = CLIExecutor()
        result = executor._load_posts_from_json(p)
        assert len(result) == 2

    def test_dict_with_posts_key(self, tmp_path):
        p = tmp_path / "posts.json"
        data = {"posts": [{"id": "1"}], "metadata": {}}
        p.write_text(json.dumps(data))
        executor = CLIExecutor()
        result = executor._load_posts_from_json(p)
        assert len(result) == 1

    def test_missing_file_returns_empty(self, tmp_path):
        executor = CLIExecutor()
        result = executor._load_posts_from_json(tmp_path / "nonexistent.json")
        assert result == []

    def test_invalid_json_returns_empty(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not valid json {{{")
        executor = CLIExecutor()
        result = executor._load_posts_from_json(p)
        assert result == []

    def test_unexpected_structure_returns_empty(self, tmp_path):
        p = tmp_path / "weird.json"
        p.write_text('{"no_posts_key": 42}')
        executor = CLIExecutor()
        result = executor._load_posts_from_json(p)
        assert result == []


class TestRunResearchTool:
    @pytest.mark.asyncio
    async def test_returns_success(self):
        executor = CLIExecutor()
        result = await executor.run_research_tool(
            tool_name="seo_keyword_research",
            brief_path="/path/to/brief.txt",
            project_id="proj-1",
            client_id="client-1",
        )
        assert result["success"] is True
        assert "metadata" in result
        assert result["metadata"]["tool"] == "seo_keyword_research"

    @pytest.mark.asyncio
    async def test_includes_execution_metadata(self):
        executor = CLIExecutor()
        result = await executor.run_research_tool("voice_analysis", "/brief.txt", "p1", "c1")
        meta = result["metadata"]
        assert meta["project_id"] == "p1"
        assert meta["client_id"] == "c1"
        assert "executed_at" in meta


class TestRunContentGeneration:
    @pytest.mark.asyncio
    async def test_failure_on_nonzero_exit(self):
        executor = CLIExecutor()

        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error: brief not found"))

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_process)):
            result = await executor.run_content_generation(
                brief_path="/brief.txt",
                client_name="TestClient",
            )
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_success_on_zero_exit(self):
        executor = CLIExecutor()

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(
            return_value=(b"Deliverables saved to: /tmp/output\n", b"")
        )

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_process)):
            result = await executor.run_content_generation(
                brief_path="/brief.txt",
                client_name="TestClient",
            )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_exception_returns_error(self):
        executor = CLIExecutor()
        with patch("asyncio.create_subprocess_exec", side_effect=OSError("no python")):
            result = await executor.run_content_generation(
                brief_path="/brief.txt",
                client_name="TestClient",
            )
        assert result["success"] is False
        assert "no python" in result["error"]


def test_singleton_import():
    assert isinstance(cli_executor, CLIExecutor)
