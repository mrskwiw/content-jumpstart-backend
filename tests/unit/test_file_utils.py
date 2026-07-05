"""Unit tests for backend.utils.file_utils."""

import pytest
from pathlib import Path

from backend.utils.file_utils import calculate_file_size, format_file_size


class TestCalculateFileSize:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello world")  # 11 bytes
        assert calculate_file_size(str(f)) == 11

    def test_nonexistent_file_returns_zero(self):
        assert calculate_file_size("/does/not/exist/file.txt") == 0

    def test_empty_file_returns_zero(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        assert calculate_file_size(str(f)) == 0

    def test_directory_path_returns_zero(self, tmp_path):
        assert calculate_file_size(str(tmp_path)) == 0

    def test_returns_zero_on_exception(self):
        # Passing a None-like invalid arg should not raise
        assert calculate_file_size("") == 0


class TestFormatFileSize:
    def test_zero_bytes(self):
        assert format_file_size(0) == "0 B"

    def test_bytes_exact(self):
        assert format_file_size(500) == "500 B"

    def test_kilobytes(self):
        result = format_file_size(1024)
        assert "KB" in result

    def test_megabytes(self):
        result = format_file_size(1024 * 1024)
        assert "MB" in result

    def test_gigabytes(self):
        result = format_file_size(1024 * 1024 * 1024)
        assert "GB" in result

    def test_small_kb_has_decimal(self):
        result = format_file_size(1024)  # 1.0 KB
        assert "." in result

    def test_large_kb_no_decimal(self):
        result = format_file_size(100 * 1024)  # 100 KB — >= 10 uses no decimal
        assert "." not in result

    def test_single_byte(self):
        # size < 10 uses :.1f format → "1.0 B"
        assert format_file_size(1) == "1.0 B"
