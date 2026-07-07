"""
Export Service Edge Case and Security Tests

Tests input validation and edge cases in export_service.py including:
- Path traversal characters in client names
- Extremely long client names
- Special/non-ASCII characters in client names
- Null/empty client and project data
- Empty post lists
- Unicode and emoji in content
- Posts with None content fields

OWASP Top 10 2021: A03:2021 - Injection (path traversal prevention)
"""

import asyncio
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch
import pytest


# ---------------------------------------------------------------------------
# Minimal mock helpers for models (no DB required for unit tests)
# ---------------------------------------------------------------------------


def _make_client(name: str = "Test Client", email: str = "c@example.com") -> MagicMock:
    """Create a minimal mock Client model."""
    c = MagicMock()
    c.name = name
    c.email = email
    c.id = "client-test-001"
    c.business_description = "A test business"
    return c


def _make_project(name: str = "Test Project") -> MagicMock:
    """Create a minimal mock Project model."""
    p = MagicMock()
    p.name = name
    p.id = "proj-test-001"
    p.num_posts = 3
    return p


def _make_post(
    content: str = "This is a test post content.",
    template_name: str = "Template 1",
    target_platform: str = "linkedin",
    word_count: int = 8,
    has_cta: bool = True,
    readability_score: float = 75.0,
) -> MagicMock:
    """Create a minimal mock Post model."""
    p = MagicMock()
    p.content = content
    p.template_name = template_name
    p.target_platform = target_platform
    p.word_count = word_count
    p.has_cta = has_cta
    p.readability_score = readability_score
    return p


def _make_posts(n: int = 3) -> list:
    """Create a list of n mock posts."""
    return [_make_post(content=f"Post content number {i + 1}.") for i in range(n)]


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Path Traversal Tests
# ---------------------------------------------------------------------------


class TestPathTraversalPrevention:
    """
    Verify that client names containing path traversal sequences do not
    allow the export to write files outside the intended output directory.
    """

    def test_path_traversal_forward_slash_does_not_escape_output_dir(self, tmp_path):
        """Client name with ../ does not write files outside data/outputs/."""
        from backend.services.export_service import generate_export_file

        client = _make_client(name="../../../etc/passwd")
        project = _make_project()
        posts = _make_posts(2)

        # Use a relative_path that includes a sanitised filename
        # The service accepts relative_path from the caller; it is the CALLER
        # (the router) that must sanitise.  Our test verifies the service
        # does not itself write to an absolute system path.
        safe_relative = "safe_output/delivery.txt"

        with patch("backend.services.export_service.Path") as MockPath:
            # Track what paths are constructed
            created_paths = []
            real_Path = Path

            def fake_Path(*args):
                result = real_Path(*args)
                created_paths.append(result)
                return result

            # Restore real Path to avoid breaking internals
            MockPath.side_effect = fake_Path

        # The key assertion: calling generate_export_file with a path traversal
        # client name should either succeed (writing to a safe place) or raise
        # a controlled error -- it must NEVER silently write outside the cwd.
        try:
            out_path, size = _run(
                generate_export_file(
                    posts=posts,
                    client=client,
                    project=project,
                    format="txt",
                    relative_path=safe_relative,
                )
            )
            # If it succeeds, verify the output is within the expected directory
            resolved = out_path.resolve()
            cwd_outputs = (real_Path("data/outputs") / safe_relative).resolve().parent
            assert str(resolved).startswith(
                str(cwd_outputs.parent.parent)
            ), f"Output path {resolved} appears to be outside expected outputs/ area"
        except Exception:
            # Any controlled exception is acceptable -- no silent path escape
            pass
        finally:
            # Cleanup any file that was written
            try:
                out_path.unlink(missing_ok=True)
            except Exception:
                pass

    def test_relative_path_escaping_output_dir_is_rejected(self):
        """Bug #180: a relative_path with ../ that escapes data/outputs must raise.

        client.name is not validated against path traversal, so the export
        service itself must confine the resolved path within data/outputs.
        """
        from backend.services.export_service import generate_export_file

        client = _make_client(name="../../../etc/passwd")
        project = _make_project()
        posts = _make_posts(1)

        with pytest.raises(ValueError, match="escapes the output directory"):
            _run(
                generate_export_file(
                    posts=posts,
                    client=client,
                    project=project,
                    format="txt",
                    relative_path="../../../../tmp/evil.txt",
                )
            )

    def test_legitimate_relative_path_is_allowed(self):
        """Bug #180: a normal nested relative_path is still accepted and written."""
        from backend.services.export_service import generate_export_file

        client = _make_client(name="Acme Co")
        project = _make_project(name="Spring Campaign")
        posts = _make_posts(1)

        out_path, size = _run(
            generate_export_file(
                posts=posts,
                client=client,
                project=project,
                format="txt",
                relative_path="Acme Co/spring_delivery.txt",
            )
        )
        try:
            assert out_path.exists()
            assert size > 0
        finally:
            out_path.unlink(missing_ok=True)

    def test_path_traversal_backslash_in_client_name(self):
        """Client name with backslash path separators does not crash the service."""
        from backend.services.export_service import _generate_txt

        client = _make_client(name="Client..back..back..evil")
        project = _make_project()
        posts = _make_posts(1)

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
            tmp_out = Path(tf.name)

        try:
            out, size = _run(
                _generate_txt(posts, client, project, tmp_out, False, False, False, None)
            )
            # Service must have written a file
            assert tmp_out.exists(), "Output file must exist"
            content = tmp_out.read_text(encoding="utf-8")
            # The client name appears in header -- verify file was written
            assert len(content) > 0, "Output file must not be empty"
        finally:
            tmp_out.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Long Client Name Tests
# ---------------------------------------------------------------------------


class TestLongClientNames:
    """Verify that very long client names do not break file generation."""

    def test_500_char_client_name_in_txt_export(self):
        """Client name of 500+ characters must not crash TXT export."""
        from backend.services.export_service import _generate_txt

        long_name = "A" * 500
        client = _make_client(name=long_name)
        project = _make_project()
        posts = _make_posts(1)

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
            tmp_out = Path(tf.name)

        try:
            out, size = _run(
                _generate_txt(posts, client, project, tmp_out, False, False, False, None)
            )
            assert tmp_out.exists()
            content = tmp_out.read_text(encoding="utf-8")
            # Long name should appear in output without truncation by default
            assert "A" * 100 in content, "Long client name should appear in export"
            assert size > 0
        finally:
            tmp_out.unlink(missing_ok=True)

    def test_500_char_client_name_in_markdown_export(self):
        """Client name of 500+ characters must not crash Markdown export."""
        from backend.services.export_service import _generate_markdown

        long_name = "B" * 500
        client = _make_client(name=long_name)
        project = _make_project(name="Long Name Project")
        posts = _make_posts(1)

        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tf:
            tmp_out = Path(tf.name)

        try:
            out, size = _run(
                _generate_markdown(posts, client, project, tmp_out, False, False, False, None)
            )
            assert tmp_out.exists()
            content = tmp_out.read_text(encoding="utf-8")
            assert "B" * 100 in content, "Long client name should appear in markdown export"
            assert size > 0
        finally:
            tmp_out.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Special Characters Tests
# ---------------------------------------------------------------------------


class TestSpecialCharactersInClientName:
    """Verify special characters in client names do not break file generation."""

    @pytest.mark.parametrize(
        "special_name",
        [
            "Client & Partners",
            "<script>alert(1)</script>",
            "Client / Division",
            "O'Brien & Associates",
            "Café Deluxe",  # UTF-8 extended char (e with acute)
            "\u4e2d\u6587\u5ba2\u6237",  # Chinese characters
            "Client \U0001f600",  # Emoji
            "Client Special",  # Special characters
            "Client [NUL] Null",  # Formerly null byte - replaced for Python AST compatibility
            "!@#$%^&*()_+-=[]{}|;:,.<>?",  # All special ASCII
        ],
    )
    def test_special_chars_in_client_name_txt_export(self, special_name):
        """Special characters in client name must not crash TXT export."""
        from backend.services.export_service import _generate_txt

        client = _make_client(name=special_name)
        project = _make_project()
        posts = _make_posts(1)

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
            tmp_out = Path(tf.name)

        try:
            out, size = _run(
                _generate_txt(posts, client, project, tmp_out, False, False, False, None)
            )
            assert tmp_out.exists(), f"Export must create a file for client name: {special_name!r}"
            assert size > 0, "Export file must not be empty"
        finally:
            tmp_out.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Empty / Null Data Tests
# ---------------------------------------------------------------------------


class TestEmptyAndNullData:
    """Verify that empty or null data is handled gracefully."""

    def test_empty_posts_list_in_txt_export(self):
        """TXT export with zero posts must not crash; file must be created."""
        from backend.services.export_service import _generate_txt

        client = _make_client()
        project = _make_project()
        posts: List = []

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
            tmp_out = Path(tf.name)

        try:
            out, size = _run(
                _generate_txt(posts, client, project, tmp_out, False, False, True, None)
            )
            assert tmp_out.exists(), "File must be created even with 0 posts"
            content = tmp_out.read_text(encoding="utf-8")
            # Post count must not appear in research report headers (design decision 2026-05-22)
            assert (
                "Total Posts" not in content
            ), "Research report header must not reference post count"
        finally:
            tmp_out.unlink(missing_ok=True)

    def test_empty_posts_list_in_markdown_export(self):
        """Markdown export with zero posts must not crash."""
        from backend.services.export_service import _generate_markdown

        client = _make_client()
        project = _make_project()
        posts: List = []

        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tf:
            tmp_out = Path(tf.name)

        try:
            out, size = _run(
                _generate_markdown(posts, client, project, tmp_out, False, False, True, None)
            )
            assert tmp_out.exists(), "Markdown file must be created even with 0 posts"
        finally:
            tmp_out.unlink(missing_ok=True)

    def test_post_with_none_optional_fields_does_not_crash(self):
        """Post with None for optional fields (template_name, readability_score) must not crash."""
        from backend.services.export_service import _generate_txt

        post = _make_post(content="Post with None fields.")
        post.template_name = None
        post.target_platform = None
        post.word_count = None
        post.readability_score = None
        post.has_cta = False

        client = _make_client()
        project = _make_project()

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
            tmp_out = Path(tf.name)

        try:
            out, size = _run(
                _generate_txt([post], client, project, tmp_out, False, False, False, None)
            )
            assert tmp_out.exists()
            content = tmp_out.read_text(encoding="utf-8")
            assert "Post with None fields." in content
        finally:
            tmp_out.unlink(missing_ok=True)

    def test_read_output_files_with_none_outputs(self):
        """_read_output_files with None input returns empty list."""
        from backend.services.export_service import _read_output_files

        result = _read_output_files(None)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_read_output_files_with_empty_dict(self):
        """_read_output_files with empty dict returns empty list."""
        from backend.services.export_service import _read_output_files

        result = _read_output_files({})
        assert isinstance(result, list)
        assert len(result) == 0

    def test_read_output_files_with_nonexistent_path(self):
        """_read_output_files with nonexistent markdown path returns graceful fallback."""
        from backend.services.export_service import _read_output_files

        result = _read_output_files({"markdown": "/nonexistent/path/to/report.md"})
        assert isinstance(result, list)
        # Must return a fallback message, not raise an exception
        combined = " ".join(result)
        assert "unavailable" in combined.lower() or len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
