"""
Unit tests for research output file reading in export service.
"""

import json


from backend.services.export_service import _read_output_files


def test_read_output_files_markdown(tmp_path):
    """Test reading markdown output file"""
    md_file = tmp_path / "test.md"
    md_file.write_text("# Test Report\n\nContent", encoding="utf-8")

    outputs = {"markdown": str(md_file)}
    lines = _read_output_files(outputs)

    assert len(lines) > 0
    assert "# Test Report" in "\n".join(lines)
    assert "Content" in "\n".join(lines)


def test_read_output_files_json(tmp_path):
    """Test reading JSON output file"""
    json_file = tmp_path / "test.json"
    test_data = {"title": "Test Report", "data": [1, 2, 3]}
    json_file.write_text(json.dumps(test_data), encoding="utf-8")

    outputs = {"json": str(json_file)}
    lines = _read_output_files(outputs)

    assert len(lines) > 0
    content = "\n".join(lines)
    assert "```json" in content
    assert "Test Report" in content


def test_read_output_files_prefers_markdown_over_json(tmp_path):
    """Test that markdown is preferred when both formats exist"""
    md_file = tmp_path / "test.md"
    md_file.write_text("# Markdown Report", encoding="utf-8")

    json_file = tmp_path / "test.json"
    json_file.write_text('{"title": "JSON Report"}', encoding="utf-8")

    outputs = {"markdown": str(md_file), "json": str(json_file)}
    lines = _read_output_files(outputs)

    content = "\n".join(lines)
    assert "# Markdown Report" in content
    assert "JSON Report" not in content


def test_read_output_files_missing_markdown_file():
    """Test graceful handling of missing markdown file"""
    outputs = {"markdown": "nonexistent/file.md"}
    lines = _read_output_files(outputs)

    assert len(lines) > 0
    assert "unavailable" in "\n".join(lines).lower()
    assert "not found" in "\n".join(lines).lower()


def test_read_output_files_missing_json_file():
    """Test graceful handling of missing JSON file"""
    outputs = {"json": "nonexistent/file.json"}
    lines = _read_output_files(outputs)

    assert len(lines) > 0
    assert "unavailable" in "\n".join(lines).lower()
    assert "not found" in "\n".join(lines).lower()


def test_read_output_files_no_outputs():
    """Test handling of no outputs"""
    outputs = {}
    lines = _read_output_files(outputs)

    assert len(lines) == 0


def test_read_output_files_none_outputs():
    """Test handling of None outputs"""
    outputs = None
    lines = _read_output_files(outputs)

    assert len(lines) == 0


def test_read_output_files_unsupported_format():
    """Test handling of unsupported output format"""
    outputs = {"pdf": "test.pdf"}
    lines = _read_output_files(outputs)

    assert len(lines) > 0
    assert "not available" in "\n".join(lines).lower()


def test_read_output_files_invalid_json(tmp_path):
    """Test handling of invalid JSON file"""
    json_file = tmp_path / "invalid.json"
    json_file.write_text("not valid json {", encoding="utf-8")

    outputs = {"json": str(json_file)}
    lines = _read_output_files(outputs)

    assert len(lines) > 0
    content = "\n".join(lines).lower()
    assert "unavailable" in content or "error" in content


def test_read_output_files_unicode_content(tmp_path):
    """Test handling of Unicode content in markdown"""
    md_file = tmp_path / "unicode.md"
    md_file.write_text("# Report with émojis 🎉\n\nCafé ☕", encoding="utf-8")

    outputs = {"markdown": str(md_file)}
    lines = _read_output_files(outputs)

    content = "\n".join(lines)
    assert "émojis" in content
    assert "🎉" in content
    assert "Café" in content
    assert "☕" in content


def test_read_output_files_empty_markdown(tmp_path):
    """Test handling of empty markdown file"""
    md_file = tmp_path / "empty.md"
    md_file.write_text("", encoding="utf-8")

    outputs = {"markdown": str(md_file)}
    lines = _read_output_files(outputs)

    # Should have at least one line (empty content)
    assert len(lines) >= 1


def test_read_output_files_large_file(tmp_path):
    """Test handling of large file (no size limit initially)"""
    md_file = tmp_path / "large.md"
    large_content = "# Large Report\n\n" + ("Line of content\n" * 10000)
    md_file.write_text(large_content, encoding="utf-8")

    outputs = {"markdown": str(md_file)}
    lines = _read_output_files(outputs)

    # Should successfully read large file
    assert len(lines) > 0
    assert "# Large Report" in "\n".join(lines)
