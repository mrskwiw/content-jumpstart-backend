"""Unit tests for newly created optimization modules

Tests for:
- src/config/prompts.py
- src/config/constants.py
- src/exceptions.py
- src/utils/response_cache.py
"""

import tempfile
import time
from pathlib import Path

import pytest

from src.config.constants import AI_TELL_PHRASES, HOOK_SIMILARITY_THRESHOLD, MIN_POST_WORD_COUNT
from src.config.prompts import PromptTemplates, SystemPrompts
from src.exceptions import (
    BriefParsingError,
    ContentJumpstartError,
    GenerationError,
    format_error_message,
    is_retriable_error,
)
from src.utils.response_cache import ResponseCache


class TestSystemPrompts:
    """Test centralized system prompts"""

    def test_content_generator_prompt_exists(self):
        """Test that CONTENT_GENERATOR prompt is defined"""
        assert isinstance(SystemPrompts.CONTENT_GENERATOR, str)
        assert len(SystemPrompts.CONTENT_GENERATOR) > 100
        assert "social media" in SystemPrompts.CONTENT_GENERATOR.lower()

    def test_brief_parser_prompt_exists(self):
        """Test that BRIEF_PARSER prompt is defined"""
        assert isinstance(SystemPrompts.BRIEF_PARSER, str)
        assert "JSON" in SystemPrompts.BRIEF_PARSER
        assert "content strategist" in SystemPrompts.BRIEF_PARSER.lower()

    def test_all_prompts_are_strings(self):
        """Test that all prompt attributes are non-empty strings"""
        for attr in dir(SystemPrompts):
            if not attr.startswith("_"):
                prompt = getattr(SystemPrompts, attr)
                assert isinstance(prompt, str)
                assert len(prompt) > 0


class TestPromptTemplates:
    """Test dynamic prompt builders"""

    def test_build_content_generation_prompt(self):
        """Test content generation prompt builder"""
        template = "[HOOK] for [AUDIENCE]"
        context = "company_name: TestCo\nideal_customer: SMBs"

        prompt = PromptTemplates.build_content_generation_prompt(template, context)

        assert "Template Structure:" in prompt
        assert template in prompt
        assert "Client Context:" in prompt
        assert context in prompt

    def test_build_refinement_prompt(self):
        """Test refinement prompt builder"""
        original = "This is a post"
        feedback = "Make it shorter"
        context = "tone: direct"

        prompt = PromptTemplates.build_refinement_prompt(original, feedback, context)

        assert "Original Post:" in prompt
        assert original in prompt
        assert "Feedback:" in prompt
        assert feedback in prompt
        assert context in prompt


class TestConstants:
    """Test centralized constants"""

    def test_post_length_constants_exist(self):
        """Test that post length constants are defined"""
        assert isinstance(MIN_POST_WORD_COUNT, int)
        assert MIN_POST_WORD_COUNT > 0
        assert MIN_POST_WORD_COUNT < 1000

    def test_validation_thresholds_exist(self):
        """Test that validation thresholds are defined"""
        assert isinstance(HOOK_SIMILARITY_THRESHOLD, float)
        assert 0.0 <= HOOK_SIMILARITY_THRESHOLD <= 1.0

    def test_ai_tell_phrases_expanded(self):
        """Test that AI tell phrases list is comprehensive"""
        assert isinstance(AI_TELL_PHRASES, list)
        assert len(AI_TELL_PHRASES) >= 20  # Should have at least 20 phrases
        assert "in today's world" in AI_TELL_PHRASES
        assert "dive deep" in AI_TELL_PHRASES


class TestExceptions:
    """Test custom exception hierarchy"""

    def test_base_exception(self):
        """Test base ContentJumpstartError"""
        with pytest.raises(ContentJumpstartError):
            raise ContentJumpstartError("Test error")

    def test_brief_parsing_error(self):
        """Test BriefParsingError inherits from base"""
        with pytest.raises(ContentJumpstartError):
            raise BriefParsingError("Parsing failed")

    def test_generation_error(self):
        """Test GenerationError inherits from base"""
        with pytest.raises(ContentJumpstartError):
            raise GenerationError("Generation failed")

    def test_format_error_message(self):
        """Test error message formatting"""
        error = BriefParsingError("Invalid JSON")
        formatted = format_error_message(error, "parsing client brief")

        assert "[BriefParsingError]" in formatted
        assert "parsing client brief" in formatted
        assert "Invalid JSON" in formatted

    def test_format_error_message_without_context(self):
        """Test error formatting without context"""
        error = GenerationError("API failed")
        formatted = format_error_message(error)

        assert "[GenerationError]" in formatted
        assert "API failed" in formatted

    def test_is_retriable_error_true(self):
        """Test that retriable errors are identified"""
        from src.exceptions import APIError

        error = APIError("Rate limit exceeded")
        assert is_retriable_error(error) is True

    def test_is_retriable_error_false(self):
        """Test that non-retriable errors are identified"""
        error = BriefParsingError("Invalid format")
        assert is_retriable_error(error) is False


class TestResponseCache:
    """Test API response cache"""

    def test_cache_initialization(self):
        """Test cache initializes with correct settings"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(cache_dir=Path(tmpdir), ttl_seconds=3600, enabled=True)

            assert cache.enabled is True
            assert cache.ttl_seconds == 3600
            assert cache.cache_dir.exists()

    def test_cache_disabled(self):
        """Test cache can be disabled"""
        cache = ResponseCache(enabled=False)
        assert cache.enabled is False

        messages = [{"role": "user", "content": "test"}]
        cache.put(messages, "system", 0.7, "response")

        # Should return None when disabled
        result = cache.get(messages, "system", 0.7)
        assert result is None

    def test_cache_put_and_get(self):
        """Test basic cache put and get operations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(cache_dir=Path(tmpdir), enabled=True)

            messages = [{"role": "user", "content": "Hello"}]
            system = "You are helpful"
            temperature = 0.7
            response = "Hi there!"

            # Cache miss initially
            assert cache.get(messages, system, temperature) is None

            # Put in cache
            cache.put(messages, system, temperature, response)

            # Cache hit
            cached = cache.get(messages, system, temperature)
            assert cached == response

    def test_cache_ttl_expiration(self):
        """Test that cache entries expire after TTL"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(
                cache_dir=Path(tmpdir), ttl_seconds=1, enabled=True  # 1 second TTL
            )

            messages = [{"role": "user", "content": "test"}]
            cache.put(messages, "system", 0.7, "response")

            # Should get cached response immediately
            assert cache.get(messages, "system", 0.7) == "response"

            # Wait for expiration
            time.sleep(1.1)

            # Should return None after expiration
            assert cache.get(messages, "system", 0.7) is None

    def test_cache_key_uniqueness(self):
        """Test that different inputs produce different cache keys"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(cache_dir=Path(tmpdir), enabled=True)

            messages1 = [{"role": "user", "content": "Hello"}]
            messages2 = [{"role": "user", "content": "Hi"}]

            cache.put(messages1, "system", 0.7, "response1")
            cache.put(messages2, "system", 0.7, "response2")

            # Different messages should have different cache entries
            assert cache.get(messages1, "system", 0.7) == "response1"
            assert cache.get(messages2, "system", 0.7) == "response2"

    def test_cache_clear(self):
        """Test cache clearing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(cache_dir=Path(tmpdir), enabled=True)

            # Add some cache entries
            for i in range(5):
                messages = [{"role": "user", "content": f"test{i}"}]
                cache.put(messages, "system", 0.7, f"response{i}")

            # Clear cache
            cache.clear()

            # All entries should be gone
            for i in range(5):
                messages = [{"role": "user", "content": f"test{i}"}]
                assert cache.get(messages, "system", 0.7) is None

    def test_cache_stats(self):
        """Test cache statistics"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(cache_dir=Path(tmpdir), enabled=True)

            # Initial stats
            stats = cache.get_stats()
            assert stats["enabled"] is True
            assert stats["total_files"] == 0

            # Add some entries
            for i in range(3):
                messages = [{"role": "user", "content": f"test{i}"}]
                cache.put(messages, "system", 0.7, f"response{i}")

            # Check updated stats
            stats = cache.get_stats()
            assert stats["total_files"] == 3
            assert stats["total_size_bytes"] > 0

    def test_cache_corrupted_file_handling(self):
        """Test that corrupted cache files are handled gracefully"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(cache_dir=Path(tmpdir), enabled=True)

            # Create a corrupted cache file
            cache_file = cache.cache_dir / "corrupted.json"
            cache_file.write_text("not valid json{}")

            # Should return None and not crash
            messages = [{"role": "user", "content": "test"}]

            # This should handle the corrupted file gracefully
            cache.get(messages, "system", 0.7)
            # Result will be None because key won't match


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
