"""
Unit tests for ContentGeneratorAgent._generate_twitter_share_copy
"""

from __future__ import annotations

import pytest

# Import directly via the class to avoid heavyweight agent init
from src.agents.content_generator import ContentGeneratorAgent


_gen = ContentGeneratorAgent._generate_twitter_share_copy


# ---------------------------------------------------------------------------
# Basic output contract
# ---------------------------------------------------------------------------
class TestBasicContract:
    def test_returns_string(self):
        result = _gen("This is a blog post about content marketing.")
        assert isinstance(result, str)

    def test_never_empty(self):
        result = _gen("Short.")
        assert result.strip() != ""

    def test_contains_url_placeholder(self):
        result = _gen("This is a blog post about content marketing.")
        assert "[YOUR_BLOG_URL]" in result

    def test_total_length_le_280(self):
        long_content = "Word " * 200
        result = _gen(long_content)
        assert len(result) <= 280


# ---------------------------------------------------------------------------
# Hook extraction
# ---------------------------------------------------------------------------
class TestHookExtraction:
    def test_uses_first_sentence(self):
        content = "The future of AI is bright. But challenges remain. Read more inside."
        result = _gen(content)
        assert "future of AI is bright" in result

    def test_truncates_very_long_first_sentence(self):
        # 300-char single sentence
        long_sentence = "A " + "very long content " * 15 + "ends here."
        result = _gen(long_sentence)
        assert len(result) <= 280

    def test_truncated_hook_ends_with_ellipsis(self):
        long_sentence = "A " + "word " * 50 + "end."
        result = _gen(long_sentence)
        if "..." in result:
            hook_part = result.split("\n")[0]
            assert hook_part.endswith("...")

    def test_skips_very_short_fragments(self):
        content = "Hi.\n\nThis is the real first sentence worth using."
        result = _gen(content)
        assert "real first sentence" in result

    def test_handles_content_with_no_sentences(self):
        result = _gen("nodot")
        assert "[YOUR_BLOG_URL]" in result

    def test_handles_empty_string(self):
        # Should not raise
        result = _gen("")
        assert isinstance(result, str)

    def test_handles_whitespace_only(self):
        result = _gen("   \n\n   ")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# URL placeholder positioning
# ---------------------------------------------------------------------------
class TestUrlPlaceholder:
    def test_url_placeholder_on_its_own_line(self):
        result = _gen("Great post about marketing trends.")
        lines = result.split("\n")
        assert any("[YOUR_BLOG_URL]" in line for line in lines)

    def test_hook_appears_before_url(self):
        content = "Here is a great insight about email marketing."
        result = _gen(content)
        hook_pos = result.find("insight")
        url_pos = result.find("[YOUR_BLOG_URL]")
        assert hook_pos < url_pos


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------
class TestEdgeCases:
    def test_multiline_content(self):
        content = "Line one sets the stage.\nLine two adds detail.\nLine three concludes."
        result = _gen(content)
        assert "[YOUR_BLOG_URL]" in result
        assert len(result) <= 280

    def test_content_with_special_characters(self):
        content = '5 reasons why "content marketing" matters & why you can\'t ignore it.'
        result = _gen(content)
        assert "[YOUR_BLOG_URL]" in result

    def test_unicode_content(self):
        content = "Le contenu est roi. Voici pourquoi. Lisez la suite."
        result = _gen(content)
        assert "[YOUR_BLOG_URL]" in result
        assert len(result) <= 280
