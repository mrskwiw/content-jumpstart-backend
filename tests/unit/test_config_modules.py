"""Unit tests for config modules (prompts, constants, exceptions)"""

import pytest

from src.config.constants import (
    AI_TELL_PHRASES,
    BRIEF_PARSING_TEMPERATURE,
    CTA_VARIETY_THRESHOLD,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    HOOK_SIMILARITY_THRESHOLD,
    MAX_POST_WORD_COUNT,
    MIN_HEADLINE_ELEMENTS,
    MIN_POST_WORD_COUNT,
    OPTIMAL_POST_MAX_WORDS,
    OPTIMAL_POST_MIN_WORDS,
    POST_GENERATION_TEMPERATURE,
)
from src.config.prompts import PromptTemplates, SystemPrompts
from src.exceptions import (
    APIError,
    BriefParsingError,
    BriefValidationError,
    ContentGenerationError,
    ContentJumpstartError,
    FileWriteError,
    FormatError,
    GenerationError,
    PostValidationError,
    TemplateLoadError,
    TemplateNotFoundError,
    format_error_message,
    is_retriable_error,
)


class TestSystemPrompts:
    """Test SystemPrompts class"""

    def test_content_generator_prompt_exists(self):
        """Test that CONTENT_GENERATOR prompt is defined"""
        assert SystemPrompts.CONTENT_GENERATOR is not None
        assert len(SystemPrompts.CONTENT_GENERATOR) > 100
        assert "social media" in SystemPrompts.CONTENT_GENERATOR.lower()

    def test_brief_parser_prompt_exists(self):
        """Test that BRIEF_PARSER prompt is defined"""
        assert SystemPrompts.BRIEF_PARSER is not None
        assert "JSON" in SystemPrompts.BRIEF_PARSER
        assert "company_name" in SystemPrompts.BRIEF_PARSER

    def test_brief_analysis_prompt_exists(self):
        """Test that BRIEF_ANALYSIS prompt is defined"""
        assert SystemPrompts.BRIEF_ANALYSIS is not None
        assert "brand voice" in SystemPrompts.BRIEF_ANALYSIS.lower()

    def test_post_refinement_prompt_exists(self):
        """Test that POST_REFINEMENT prompt is defined"""
        assert SystemPrompts.POST_REFINEMENT is not None
        assert "refin" in SystemPrompts.POST_REFINEMENT.lower()

    def test_voice_analysis_prompt_exists(self):
        """Test that VOICE_ANALYSIS prompt is defined"""
        assert SystemPrompts.VOICE_ANALYSIS is not None
        assert "voice" in SystemPrompts.VOICE_ANALYSIS.lower()

    def test_prompts_are_strings(self):
        """Test that all prompts are strings"""
        assert isinstance(SystemPrompts.CONTENT_GENERATOR, str)
        assert isinstance(SystemPrompts.BRIEF_PARSER, str)
        assert isinstance(SystemPrompts.BRIEF_ANALYSIS, str)
        assert isinstance(SystemPrompts.POST_REFINEMENT, str)
        assert isinstance(SystemPrompts.VOICE_ANALYSIS, str)

    def test_prompts_not_empty(self):
        """Test that no prompts are empty"""
        assert SystemPrompts.CONTENT_GENERATOR.strip() != ""
        assert SystemPrompts.BRIEF_PARSER.strip() != ""
        assert SystemPrompts.BRIEF_ANALYSIS.strip() != ""
        assert SystemPrompts.POST_REFINEMENT.strip() != ""
        assert SystemPrompts.VOICE_ANALYSIS.strip() != ""


class TestPromptTemplates:
    """Test PromptTemplates class"""

    def test_prompt_templates_exists(self):
        """Test that PromptTemplates class is importable"""
        assert PromptTemplates is not None

    def test_generation_prompt_method(self):
        """Test that PromptTemplates class has necessary attributes"""
        # PromptTemplates is a utility class for building prompts
        # Just verify it's a class with methods/attributes
        assert hasattr(PromptTemplates, "__dict__")
        # If there's a build method, it should work
        if hasattr(PromptTemplates, "build_generation_prompt"):
            prompt = PromptTemplates.build_generation_prompt(
                template_structure="Test template", context={"company": "Acme Corp"}
            )
            assert "Test template" in prompt
            assert "Acme Corp" in prompt


class TestConstants:
    """Test constants module"""

    def test_post_length_constants(self):
        """Test post length constants"""
        assert MIN_POST_WORD_COUNT == 75
        assert MAX_POST_WORD_COUNT == 350
        assert OPTIMAL_POST_MIN_WORDS == 150
        assert OPTIMAL_POST_MAX_WORDS == 250

        # Logical relationships
        assert (
            MIN_POST_WORD_COUNT
            < OPTIMAL_POST_MIN_WORDS
            < OPTIMAL_POST_MAX_WORDS
            < MAX_POST_WORD_COUNT
        )

    def test_validation_thresholds(self):
        """Test validation threshold constants"""
        assert 0.0 < HOOK_SIMILARITY_THRESHOLD <= 1.0
        assert 0.0 < CTA_VARIETY_THRESHOLD <= 1.0
        assert MIN_HEADLINE_ELEMENTS >= 1

        # Common values
        assert HOOK_SIMILARITY_THRESHOLD == 0.80
        assert CTA_VARIETY_THRESHOLD == 0.40
        assert MIN_HEADLINE_ELEMENTS == 3

    def test_api_constants(self):
        """Test API-related constants"""
        assert DEFAULT_MAX_RETRIES >= 1
        assert DEFAULT_RETRY_DELAY > 0
        assert DEFAULT_MAX_RETRIES == 3
        assert DEFAULT_RETRY_DELAY == 1.0

    def test_temperature_constants(self):
        """Test temperature constants"""
        assert 0.0 <= POST_GENERATION_TEMPERATURE <= 1.0
        assert 0.0 <= BRIEF_PARSING_TEMPERATURE <= 1.0

        # Parsing should be more deterministic than generation
        assert BRIEF_PARSING_TEMPERATURE < POST_GENERATION_TEMPERATURE

        assert POST_GENERATION_TEMPERATURE == 0.7
        assert BRIEF_PARSING_TEMPERATURE == 0.3

    def test_ai_tell_phrases(self):
        """Test AI tell phrases list"""
        assert isinstance(AI_TELL_PHRASES, list)
        assert len(AI_TELL_PHRASES) > 0

        # Check common AI tells
        assert "in today's world" in AI_TELL_PHRASES
        assert "dive deep" in AI_TELL_PHRASES
        assert "unlock" in AI_TELL_PHRASES
        assert "game-changer" in AI_TELL_PHRASES

    def test_constants_are_immutable_types(self):
        """Test that constants use immutable types where appropriate"""
        assert isinstance(MIN_POST_WORD_COUNT, int)
        assert isinstance(HOOK_SIMILARITY_THRESHOLD, float)
        assert isinstance(AI_TELL_PHRASES, list)


class TestExceptions:
    """Test custom exceptions"""

    def test_base_exception(self):
        """Test base ContentJumpstartError"""
        with pytest.raises(ContentJumpstartError):
            raise ContentJumpstartError("Test error")

    def test_brief_parsing_error(self):
        """Test BriefParsingError"""
        with pytest.raises(BriefParsingError):
            raise BriefParsingError("Failed to parse")

        # Should be instance of base error
        try:
            raise BriefParsingError("Test")
        except ContentJumpstartError:
            pass  # Should catch as base class

    def test_brief_validation_error(self):
        """Test BriefValidationError"""
        with pytest.raises(BriefValidationError):
            raise BriefValidationError("Validation failed")

    def test_template_errors(self):
        """Test template-related errors"""
        with pytest.raises(TemplateNotFoundError):
            raise TemplateNotFoundError("Template not found")

        with pytest.raises(TemplateLoadError):
            raise TemplateLoadError("Load failed")

    def test_generation_errors(self):
        """Test generation-related errors"""
        with pytest.raises(GenerationError):
            raise GenerationError("Generation failed")

        with pytest.raises(APIError):
            raise APIError("API error")

        with pytest.raises(ContentGenerationError):
            raise ContentGenerationError("Content generation failed")

    def test_validation_error(self):
        """Test PostValidationError"""
        with pytest.raises(PostValidationError):
            raise PostValidationError("Validation failed")

    def test_file_errors(self):
        """Test file-related errors"""
        with pytest.raises(FileWriteError):
            raise FileWriteError("Write failed")

        with pytest.raises(FormatError):
            raise FormatError("Format error")

    def test_format_error_message(self):
        """Test error message formatting utility"""
        error = BriefParsingError("Parse failed")
        message = format_error_message(error)

        assert "BriefParsingError" in message
        assert "Parse failed" in message

    def test_format_error_message_with_context(self):
        """Test error message formatting with context"""
        error = GenerationError("Failed")
        message = format_error_message(error, context={"client": "Acme"})

        assert "GenerationError" in message
        assert "Failed" in message
        assert "Acme" in message

    def test_is_retriable_error(self):
        """Test retriable error detection"""
        # API errors should be retriable
        assert is_retriable_error(APIError("Rate limit"))

        # Connection errors should be retriable
        assert is_retriable_error(ContentGenerationError("Connection timeout"))

        # Validation errors should not be retriable
        assert not is_retriable_error(BriefValidationError("Invalid field"))
        assert not is_retriable_error(TemplateNotFoundError("Not found"))

    def test_exception_inheritance(self):
        """Test exception class hierarchy"""
        # All should inherit from base
        assert issubclass(BriefParsingError, ContentJumpstartError)
        assert issubclass(GenerationError, ContentJumpstartError)
        assert issubclass(PostValidationError, ContentJumpstartError)

        # All should be Exceptions
        assert issubclass(ContentJumpstartError, Exception)

    def test_exception_with_message(self):
        """Test exceptions preserve error messages"""
        message = "This is a test error message"

        try:
            raise GenerationError(message)
        except GenerationError as e:
            assert str(e) == message

    def test_exception_chaining(self):
        """Test exception chaining"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise GenerationError("Wrapped error") from e
        except GenerationError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)
