"""
Research Input Validator (Phase 2 Security - TR-019)

Comprehensive input validation for research tools to prevent:
- Prompt injection attacks
- DOS attacks via huge inputs
- Invalid data types
- Missing required fields

Security Features:
1. Length validation (min/max)
2. Prompt injection sanitization
3. Type checking
4. Field presence validation
"""

import re
from typing import Any, Dict, List, Optional

from .prompt_injection_defense import sanitize_prompt_input


class ValidationError(ValueError):
    """Input validation failed"""

    pass


class ResearchInputValidator:
    """
    Validates inputs for research tools with security-first approach

    Usage:
        validator = ResearchInputValidator()

        # Validate text field
        business_desc = validator.validate_text(
            inputs.get("business_description"),
            field_name="business_description",
            min_length=50,
            max_length=5000,
            required=True
        )

        # Validate list field
        competitors = validator.validate_list(
            inputs.get("competitors"),
            field_name="competitors",
            min_items=1,
            max_items=10,
            required=True
        )
    """

    # Default limits
    DEFAULT_TEXT_MIN = 10
    DEFAULT_TEXT_MAX = 10000  # 10K chars max (prevent DOS)
    DEFAULT_LIST_MAX = 100  # Max 100 items in lists

    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator

        Args:
            strict_mode: If True, blocks medium-risk prompt injection patterns too
        """
        self.strict_mode = strict_mode

    def validate_text(
        self,
        value: Any,
        field_name: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        required: bool = True,
        allow_empty: bool = False,
        sanitize: bool = True,
    ) -> str:
        """
        Validate and sanitize text input

        Args:
            value: Input value to validate
            field_name: Name of field (for error messages)
            min_length: Minimum length (default: 10)
            max_length: Maximum length (default: 10000)
            required: If True, field must be present
            allow_empty: If True, empty strings are valid
            sanitize: If True, sanitize against prompt injection

        Returns:
            Validated and sanitized text

        Raises:
            ValidationError: If validation fails
        """
        # Check presence
        if value is None or value == "":
            if required and not allow_empty:
                raise ValidationError(f"{field_name} is required")
            return ""

        # Check type
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string, got {type(value).__name__}")

        # Apply defaults
        min_len = min_length if min_length is not None else self.DEFAULT_TEXT_MIN
        max_len = max_length if max_length is not None else self.DEFAULT_TEXT_MAX

        # Check length
        if len(value) < min_len:
            raise ValidationError(
                f"{field_name} too short (minimum {min_len} characters, got {len(value)})"
            )

        if len(value) > max_len:
            raise ValidationError(
                f"{field_name} too long (maximum {max_len} characters, got {len(value)})"
            )

        # Sanitize prompt injection
        if sanitize:
            try:
                value = sanitize_prompt_input(value, strict=self.strict_mode)
            except ValueError as e:
                raise ValidationError(f"{field_name} contains unsafe content: {str(e)}") from e

        return value

    def validate_list(
        self,
        value: Any,
        field_name: str,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        required: bool = True,
        item_validator: Optional[callable] = None,
    ) -> List[Any]:
        """
        Validate list input

        Args:
            value: Input value to validate
            field_name: Name of field (for error messages)
            min_items: Minimum number of items
            max_items: Maximum number of items (default: 100)
            required: If True, field must be present
            item_validator: Optional function to validate each item

        Returns:
            Validated list

        Raises:
            ValidationError: If validation fails
        """
        # Check presence
        if value is None or value == []:
            if required:
                raise ValidationError(f"{field_name} is required")
            return []

        # Check type
        if not isinstance(value, list):
            raise ValidationError(f"{field_name} must be a list, got {type(value).__name__}")

        # Apply defaults
        max_count = max_items if max_items is not None else self.DEFAULT_LIST_MAX

        # Check size
        if min_items is not None and len(value) < min_items:
            raise ValidationError(
                f"{field_name} must have at least {min_items} items, got {len(value)}"
            )

        if len(value) > max_count:
            raise ValidationError(
                f"{field_name} must have at most {max_count} items, got {len(value)}"
            )

        # Validate each item if validator provided
        if item_validator:
            validated_items = []
            for i, item in enumerate(value):
                try:
                    validated_item = item_validator(item)
                    validated_items.append(validated_item)
                except (ValidationError, ValueError) as e:
                    raise ValidationError(f"{field_name}[{i}] validation failed: {str(e)}") from e
            return validated_items

        return value

    def validate_dict(
        self,
        value: Any,
        field_name: str,
        required_keys: Optional[List[str]] = None,
        max_keys: Optional[int] = None,
        required: bool = True,
    ) -> Dict[str, Any]:
        """
        Validate dictionary input

        Args:
            value: Input value to validate
            field_name: Name of field (for error messages)
            required_keys: Keys that must be present
            max_keys: Maximum number of keys allowed
            required: If True, field must be present

        Returns:
            Validated dictionary

        Raises:
            ValidationError: If validation fails
        """
        # Check presence
        if value is None or value == {}:
            if required:
                raise ValidationError(f"{field_name} is required")
            return {}

        # Check type
        if not isinstance(value, dict):
            raise ValidationError(f"{field_name} must be a dictionary, got {type(value).__name__}")

        # Check required keys
        if required_keys:
            missing_keys = set(required_keys) - set(value.keys())
            if missing_keys:
                raise ValidationError(
                    f"{field_name} missing required keys: {', '.join(missing_keys)}"
                )

        # Check max keys
        if max_keys is not None and len(value) > max_keys:
            raise ValidationError(
                f"{field_name} has too many keys (maximum {max_keys}, got {len(value)})"
            )

        return value

    def validate_email(self, value: Any, field_name: str, required: bool = True) -> str:
        """
        Validate email address

        Args:
            value: Input value to validate
            field_name: Name of field (for error messages)
            required: If True, field must be present

        Returns:
            Validated email

        Raises:
            ValidationError: If validation fails
        """
        # Check presence
        if value is None or value == "":
            if required:
                raise ValidationError(f"{field_name} is required")
            return ""

        # Check type
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string, got {type(value).__name__}")

        # Simple email validation (RFC 5322 simplified)
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, value):
            raise ValidationError(f"{field_name} is not a valid email address")

        # Length check (max 254 chars per RFC)
        if len(value) > 254:
            raise ValidationError(f"{field_name} email too long (max 254 characters)")

        return value.lower().strip()

    def validate_url(self, value: Any, field_name: str, required: bool = True) -> str:
        """
        Validate URL

        Args:
            value: Input value to validate
            field_name: Name of field (for error messages)
            required: If True, field must be present

        Returns:
            Validated URL

        Raises:
            ValidationError: If validation fails
        """
        # Check presence
        if value is None or value == "":
            if required:
                raise ValidationError(f"{field_name} is required")
            return ""

        # Check type
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string, got {type(value).__name__}")

        # Simple URL validation
        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        if not re.match(url_pattern, value, re.IGNORECASE):
            raise ValidationError(f"{field_name} is not a valid URL")

        # Length check
        if len(value) > 2048:
            raise ValidationError(f"{field_name} URL too long (max 2048 characters)")

        return value.strip()

    def validate_integer(
        self,
        value: Any,
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        required: bool = True,
    ) -> int:
        """
        Validate integer input

        Args:
            value: Input value to validate
            field_name: Name of field (for error messages)
            min_value: Minimum value
            max_value: Maximum value
            required: If True, field must be present

        Returns:
            Validated integer

        Raises:
            ValidationError: If validation fails
        """
        # Check presence
        if value is None:
            if required:
                raise ValidationError(f"{field_name} is required")
            return 0

        # Check type and convert
        if not isinstance(value, int):
            if isinstance(value, str):
                try:
                    value = int(value)
                except ValueError:
                    raise ValidationError(f"{field_name} must be an integer, got '{value}'")
            else:
                raise ValidationError(
                    f"{field_name} must be an integer, got {type(value).__name__}"
                )

        # Check range
        if min_value is not None and value < min_value:
            raise ValidationError(f"{field_name} must be at least {min_value}, got {value}")

        if max_value is not None and value > max_value:
            raise ValidationError(f"{field_name} must be at most {max_value}, got {value}")

        return value


# Convenience functions for common validations
def validate_business_description(
    value: Any, validator: Optional[ResearchInputValidator] = None
) -> str:
    """
    Validate business description field (common across research tools)

    Args:
        value: Input value
        validator: Optional validator instance (creates new if not provided)

    Returns:
        Validated and sanitized business description
    """
    if validator is None:
        validator = ResearchInputValidator()

    return validator.validate_text(
        value,
        field_name="business_description",
        min_length=50,
        max_length=5000,
        required=True,
    )


def validate_content_samples(
    value: Any, validator: Optional[ResearchInputValidator] = None
) -> List[str]:
    """
    Validate content samples list (common across research tools)

    Args:
        value: Input value
        validator: Optional validator instance

    Returns:
        Validated list of sanitized content samples
    """
    if validator is None:
        validator = ResearchInputValidator()

    # Validate list
    samples = validator.validate_list(
        value, field_name="content_samples", min_items=3, max_items=20, required=True
    )

    # Validate each sample
    validated_samples = []
    for i, sample in enumerate(samples):
        validated_sample = validator.validate_text(
            sample,
            field_name=f"content_sample_{i}",
            min_length=50,
            max_length=5000,
            required=True,
        )
        validated_samples.append(validated_sample)

    return validated_samples


def validate_competitor_list(
    value: Any, validator: Optional[ResearchInputValidator] = None
) -> List[str]:
    """
    Validate competitor list (common across research tools)

    Args:
        value: Input value
        validator: Optional validator instance

    Returns:
        Validated list of competitor names
    """
    if validator is None:
        validator = ResearchInputValidator()

    # Validate list
    competitors = validator.validate_list(
        value, field_name="competitors", min_items=1, max_items=20, required=True
    )

    # Validate each competitor name
    validated_competitors = []
    for i, competitor in enumerate(competitors):
        validated_competitor = validator.validate_text(
            competitor,
            field_name=f"competitor_{i}",
            min_length=2,
            max_length=200,
            required=True,
        )
        validated_competitors.append(validated_competitor)

    return validated_competitors
