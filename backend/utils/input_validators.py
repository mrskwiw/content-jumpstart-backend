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
        raise ValueError(f"{field_name} is required. Please provide a value.")

    # Convert to string and strip whitespace
    value = str(value).strip()

    # Check empty
    if not value and not allow_empty:
        raise ValueError(f"{field_name} is required. Please provide a value.")

    # Check length
    if len(value) < min_length:
        raise ValueError(
            f"{field_name} is too short. "
            f"Please enter at least {min_length} character{'s' if min_length > 1 else ''} "
            f"(currently {len(value)} character{'s' if len(value) != 1 else ''})."
        )
    if len(value) > max_length:
        raise ValueError(
            f"{field_name} is too long. "
            f"Maximum length is {max_length} characters "
            f"(currently {len(value)} characters). "
            f"Please shorten your input."
        )

    # Check for dangerous patterns
    for regex in DANGEROUS_REGEX:
        if regex.search(value):
            raise ValueError(
                f"{field_name} contains invalid characters or formatting. "
                f"Please avoid using special symbols like <, >, $, backticks, or SQL keywords. "
                f"Use only letters, numbers, and basic punctuation."
            )

    # Check custom pattern
    if pattern and not re.match(pattern, value):
        raise ValueError(
            f"{field_name} format is invalid. "
            f"Please check the format and try again."
        )

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
        raise ValueError(
            "Email address format is invalid. "
            "Please enter a valid email address (e.g., name@example.com)."
        )

    if len(email) > 255:
        raise ValueError(
            "Email address is too long. "
            "Maximum length is 255 characters. "
            "Please use a shorter email address."
        )

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
        raise ValueError(f"{field_name} is required. Please provide a valid ID.")

    value = str(value).strip()

    # Check length
    if len(value) < min_length:
        raise ValueError(
            f"{field_name} is too short. "
            f"Minimum length is {min_length} characters (currently {len(value)}). "
            f"Please use a valid ID."
        )
    if len(value) > max_length:
        raise ValueError(
            f"{field_name} is too long. "
            f"Maximum length is {max_length} characters (currently {len(value)}). "
            f"Please use a valid ID."
        )

    # Check prefix if required
    if prefix and not value.startswith(prefix):
        raise ValueError(
            f"{field_name} must start with '{prefix}'. "
            f"Example: {prefix}12345. "
            f"Current value: '{value}' does not match this format."
        )

    # IDs should only contain safe characters
    if not re.match(r'^[a-zA-Z0-9_-]+$', value):
        raise ValueError(
            f"{field_name} contains invalid characters. "
            f"Please use only letters, numbers, hyphens (-), and underscores (_)."
        )

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
            raise ValueError(
                f"{field_name} must be a whole number. "
                f"Please enter a valid integer (e.g., 1, 10, 100)."
            )

    if min_value is not None and value < min_value:
        raise ValueError(
            f"{field_name} is too small. "
            f"Minimum value is {min_value} (currently {value}). "
            f"Please enter a higher number."
        )

    if max_value is not None and value > max_value:
        raise ValueError(
            f"{field_name} is too large. "
            f"Maximum value is {max_value} (currently {value}). "
            f"Please enter a lower number."
        )

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
            raise ValueError(
                f"{field_name} must be a valid number. "
                f"Please enter a numeric value (e.g., 1.50, 10, 99.99)."
            )

    if min_value is not None and value < min_value:
        raise ValueError(
            f"{field_name} is too small. "
            f"Minimum value is {min_value} (currently {value}). "
            f"Please enter a higher number."
        )

    if max_value is not None and value > max_value:
        raise ValueError(
            f"{field_name} is too large. "
            f"Maximum value is {max_value} (currently {value}). "
            f"Please enter a lower number."
        )

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
        raise ValueError(f"{field_name} is required. Please select a value.")

    value = str(value).strip()

    # Case-insensitive comparison if needed
    if not case_sensitive:
        value_lower = value.lower()
        allowed_lower = [v.lower() for v in allowed_values]
        if value_lower not in allowed_lower:
            # Format allowed values nicely
            if len(allowed_values) <= 3:
                options_str = ', '.join(f"'{v}'" for v in allowed_values)
            else:
                options_str = ', '.join(f"'{v}'" for v in allowed_values[:3]) + f", or {len(allowed_values) - 3} more"

            raise ValueError(
                f"{field_name} has an invalid value: '{value}'. "
                f"Please choose one of: {options_str}."
            )
        # Return the original casing from allowed_values
        idx = allowed_lower.index(value_lower)
        return allowed_values[idx]
    else:
        if value not in allowed_values:
            # Format allowed values nicely
            if len(allowed_values) <= 3:
                options_str = ', '.join(f"'{v}'" for v in allowed_values)
            else:
                options_str = ', '.join(f"'{v}'" for v in allowed_values[:3]) + f", or {len(allowed_values) - 3} more"

            raise ValueError(
                f"{field_name} has an invalid value: '{value}'. "
                f"Please choose one of: {options_str}."
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
