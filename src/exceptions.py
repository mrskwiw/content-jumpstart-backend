"""Custom exceptions for the Content Jumpstart system

This module defines a hierarchy of custom exceptions that provide clear,
specific error messages and make it easier to handle different failure modes
throughout the application.

Exception Hierarchy:
    ContentJumpstartError (base)
    ├── BriefParsingError
    ├── TemplateError
    │   ├── TemplateNotFoundError
    │   └── TemplateLoadError
    ├── GenerationError
    │   ├── APIError
    │   └── ContentGenerationError
    ├── ValidationError
    │   ├── BriefValidationError
    │   └── PostValidationError
    └── OutputError
        ├── FileWriteError
        └── FormatError
"""


class ContentJumpstartError(Exception):
    """Base exception for all Content Jumpstart errors

    All custom exceptions should inherit from this class for consistent
    error handling and logging.
    """


# ============================================================================
# BRIEF PROCESSING ERRORS
# ============================================================================


class BriefParsingError(ContentJumpstartError):
    """Raised when client brief parsing fails

    This can occur when:
    - API fails to extract structured data from brief
    - Brief is malformed or missing required fields
    - JSON parsing fails
    """


class BriefValidationError(ContentJumpstartError):
    """Raised when client brief validation fails

    This occurs when parsed brief data doesn't meet requirements:
    - Missing required fields
    - Invalid enum values
    - Data type mismatches
    """


# ============================================================================
# TEMPLATE ERRORS
# ============================================================================


class TemplateError(ContentJumpstartError):
    """Base exception for template-related errors"""


class TemplateNotFoundError(TemplateError):
    """Raised when template file or specific template cannot be found

    This can occur when:
    - Template library file is missing
    - Template ID doesn't exist
    - Template file path is incorrect
    """


class TemplateLoadError(TemplateError):
    """Raised when template file cannot be loaded or parsed

    This can occur when:
    - File permissions prevent reading
    - File encoding is incorrect
    - Markdown parsing fails
    - Template structure is malformed
    """


# ============================================================================
# CONTENT GENERATION ERRORS
# ============================================================================


class GenerationError(ContentJumpstartError):
    """Base exception for content generation errors"""


class APIError(GenerationError):
    """Raised when Anthropic API call fails

    This can occur when:
    - Rate limits exceeded
    - Network connection fails
    - API key is invalid
    - Request timeout
    """


class ContentGenerationError(GenerationError):
    """Raised when post generation fails

    This can occur when:
    - Generated content is empty
    - Content doesn't match expected format
    - Template filling fails
    """


# ============================================================================
# VALIDATION ERRORS
# ============================================================================


class ValidationError(ContentJumpstartError):
    """Base exception for validation errors"""


class PostValidationError(ValidationError):
    """Raised when post validation fails

    This can occur when:
    - Post doesn't meet quality thresholds
    - Post length is out of bounds
    - Required elements are missing
    """


# ============================================================================
# OUTPUT ERRORS
# ============================================================================


class OutputError(ContentJumpstartError):
    """Base exception for output/file generation errors"""


class FileWriteError(OutputError):
    """Raised when file writing fails

    This can occur when:
    - Output directory doesn't exist
    - Permissions prevent writing
    - Disk space is insufficient
    """


class FormatError(OutputError):
    """Raised when output formatting fails

    This can occur when:
    - DOCX generation fails
    - Excel formatting fails
    - iCal generation fails
    """


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def format_error_message(error: Exception, context: str = "") -> str:
    """Format error message with context for logging

    Args:
        error: Exception that was raised
        context: Additional context about where error occurred

    Returns:
        Formatted error message string

    Example:
        >>> try:
        ...     raise BriefParsingError("Invalid JSON")
        ... except Exception as e:
        ...     msg = format_error_message(e, "parsing client brief")
        ...     print(msg)
        [BriefParsingError] parsing client brief: Invalid JSON
    """
    error_type = type(error).__name__
    if context:
        return f"[{error_type}] {context}: {str(error)}"
    return f"[{error_type}] {str(error)}"


def is_retriable_error(error: Exception) -> bool:
    """Determine if an error should trigger a retry

    Args:
        error: Exception that was raised

    Returns:
        True if error is retriable (network, rate limit, etc.)

    Example:
        >>> try:
        ...     # API call
        ... except Exception as e:
        ...     if is_retriable_error(e):
        ...         # Retry the operation
        ...         pass
    """
    retriable_types = (
        APIError,
        FileWriteError,  # Might be transient disk issue
    )

    # Check if error is instance of retriable types
    if isinstance(error, retriable_types):
        return True

    # Check error message for retriable indicators
    error_msg = str(error).lower()
    retriable_indicators = [
        "rate limit",
        "timeout",
        "connection",
        "network",
        "temporary",
        "unavailable",
    ]

    return any(indicator in error_msg for indicator in retriable_indicators)
