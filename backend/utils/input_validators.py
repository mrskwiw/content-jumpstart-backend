"""
Input Validation Utilities (TR-003)

Centralized input validation to prevent:
- SQL Injection (OWASP A03:2021)
- XSS Attacks (OWASP A03:2021)
- Command Injection
- Path Traversal
- DoS via large inputs
- Invalid data formats

Usage:
    from utils.input_validators import (
        validate_string_field,
        validate_email,
        validate_id_field,
        sanitize_html,
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        return validate_string_field(v, field_name="name", min_length=1, max_length=100)
"""
import re
from typing import Optional
from pydantic import ValidationError


# Dangerous patterns that might indicate injection attempts
DANGEROUS_PATTERNS = [
    r'<script[^>]*>',  # XSS
    r'javascript:',     # XSS
    r'on\w+\s*=',      # Event handlers (XSS)
    r'--',             # SQL comment
    r';.*(?:DROP|DELETE|INSERT|UPDATE|ALTER|CREATE)',  # SQL injection
    r'\.\./|\.\.',     # Path traversal
    r'\$\{',           # Template injection
    r'`.*`',           # Command execution
    r'\|.*\|',         # Command piping
]

# Compile patterns for performance
DANGEROUS_REGEX = [re.compile(pattern, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS]


def validate_string_field(
    value: str,
    field_name: str,
    min_length: int = 1,
    max_length: int = 500,
    allow_empty: bool = False,
    pattern: Optional[str] = None,
) -> str:
    """
    Validate and sanitize string fields.

    Args:
        value: String to validate
        field_name: Field name for error messages
        min_length: Minimum allowed length
        max_length: Maximum allowed length
        allow_empty: Whether to allow empty strings
        pattern: Optional regex pattern to match

    Returns:
        Validated and sanitized string

    Raises:
        ValueError: If validation fails
    """
    if value is None:
        if allow_empty:
            return ""
        raise ValueError(f"{field_name} cannot be None")

    # Convert to string and strip whitespace
    value = str(value).strip()

    # Check empty
    if not value and not allow_empty:
        raise ValueError(f"{field_name} cannot be empty")

    # Check length
    if len(value) < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters")
    if len(value) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters")

    # Check for dangerous patterns
    for regex in DANGEROUS_REGEX:
        if regex.search(value):
            raise ValueError(
                f"{field_name} contains potentially dangerous content. "
                f"Please remove special characters and try again."
            )

    # Check custom pattern
    if pattern and not re.match(pattern, value):
        raise ValueError(f"{field_name} format is invalid")

    return value


def validate_email(email: str) -> str:
    """
    Validate email format.

    Args:
        email: Email address to validate

    Returns:
        Validated email (lowercase)

    Raises:
        ValueError: If email format is invalid
    """
    email = email.strip().lower()

    # Basic email regex (RFC 5322 simplified)
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(email_pattern, email):
        raise ValueError("Invalid email format")

    if len(email) > 255:
        raise ValueError("Email cannot exceed 255 characters")

    return email


def validate_id_field(
    value: str,
    field_name: str,
    prefix: Optional[str] = None,
    min_length: int = 5,
    max_length: int = 100,
) -> str:
    """
    Validate ID fields (UUIDs, database IDs, etc.).

    Args:
        value: ID to validate
        field_name: Field name for error messages
        prefix: Optional required prefix (e.g., "proj-", "user-")
        min_length: Minimum ID length
        max_length: Maximum ID length

    Returns:
        Validated ID

    Raises:
        ValueError: If validation fails
    """
    if not value:
        raise ValueError(f"{field_name} cannot be empty")

    value = str(value).strip()

    # Check length
    if len(value) < min_length:
        raise ValueError(f"{field_name} is too short (min: {min_length})")
    if len(value) > max_length:
        raise ValueError(f"{field_name} is too long (max: {max_length})")

    # Check prefix if required
    if prefix and not value.startswith(prefix):
        raise ValueError(f"{field_name} must start with '{prefix}'")

    # IDs should only contain safe characters
    if not re.match(r'^[a-zA-Z0-9_-]+$', value):
        raise ValueError(f"{field_name} contains invalid characters")

    return value


def validate_integer_field(
    value: int,
    field_name: str,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
) -> int:
    """
    Validate integer fields with bounds checking.

    Args:
        value: Integer to validate
        field_name: Field name for error messages
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Returns:
        Validated integer

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(value, int):
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"{field_name} must be an integer")

    if min_value is not None and value < min_value:
        raise ValueError(f"{field_name} must be at least {min_value}")

    if max_value is not None and value > max_value:
        raise ValueError(f"{field_name} cannot exceed {max_value}")

    return value


def validate_float_field(
    value: float,
    field_name: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> float:
    """
    Validate float fields with bounds checking.

    Args:
        value: Float to validate
        field_name: Field name for error messages
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Returns:
        Validated float

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(value, (int, float)):
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"{field_name} must be a number")

    if min_value is not None and value < min_value:
        raise ValueError(f"{field_name} must be at least {min_value}")

    if max_value is not None and value > max_value:
        raise ValueError(f"{field_name} cannot exceed {max_value}")

    return value


def validate_enum_field(
    value: str,
    field_name: str,
    allowed_values: list[str],
    case_sensitive: bool = False,
) -> str:
    """
    Validate enum/choice fields.

    Args:
        value: Value to validate
        field_name: Field name for error messages
        allowed_values: List of allowed values
        case_sensitive: Whether comparison is case-sensitive

    Returns:
        Validated value

    Raises:
        ValueError: If value not in allowed list
    """
    if not value:
        raise ValueError(f"{field_name} cannot be empty")

    value = str(value).strip()

    # Case-insensitive comparison if needed
    if not case_sensitive:
        value_lower = value.lower()
        allowed_lower = [v.lower() for v in allowed_values]
        if value_lower not in allowed_lower:
            raise ValueError(
                f"{field_name} must be one of: {', '.join(allowed_values)}"
            )
        # Return the original casing from allowed_values
        idx = allowed_lower.index(value_lower)
        return allowed_values[idx]
    else:
        if value not in allowed_values:
            raise ValueError(
                f"{field_name} must be one of: {', '.join(allowed_values)}"
            )
        return value


def sanitize_html(html: str, allow_tags: Optional[list[str]] = None) -> str:
    """
    Sanitize HTML content to prevent XSS attacks.

    Args:
        html: HTML content to sanitize
        allow_tags: List of allowed HTML tags (default: none)

    Returns:
        Sanitized HTML (or plain text if no tags allowed)
    """
    if not html:
        return ""

    if allow_tags is None:
        # Strip all HTML tags by default
        return re.sub(r'<[^>]+>', '', html)

    # For now, just strip all tags
    # In production, use a library like bleach for proper HTML sanitization
    return re.sub(r'<[^>]+>', '', html)


def validate_json_field(
    value: dict,
    field_name: str,
    required_keys: Optional[list[str]] = None,
    max_depth: int = 10,
) -> dict:
    """
    Validate JSON/dict fields.

    Args:
        value: Dict to validate
        field_name: Field name for error messages
        required_keys: List of required keys
        max_depth: Maximum nesting depth (DoS prevention)

    Returns:
        Validated dict

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a valid JSON object")

    # Check required keys
    if required_keys:
        missing = set(required_keys) - set(value.keys())
        if missing:
            raise ValueError(
                f"{field_name} is missing required keys: {', '.join(missing)}"
            )

    # Check depth (prevent DoS via deeply nested objects)
    def check_depth(obj, current_depth=0):
        if current_depth > max_depth:
            raise ValueError(f"{field_name} exceeds maximum nesting depth")
        if isinstance(obj, dict):
            for v in obj.values():
                check_depth(v, current_depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                check_depth(item, current_depth + 1)

    check_depth(value)

    return value
