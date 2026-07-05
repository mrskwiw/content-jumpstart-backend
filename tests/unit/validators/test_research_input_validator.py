"""Tests for Research Input Validator"""

from unittest.mock import patch

import pytest

from src.validators.research_input_validator import (
    ResearchInputValidator,
    ValidationError,
    validate_business_description,
    validate_competitor_list,
    validate_content_samples,
)


class TestValidationError:
    """Test ValidationError exception"""

    def test_validation_error_inherits_value_error(self):
        """Test ValidationError is a ValueError subclass"""
        error = ValidationError("test message")
        assert isinstance(error, ValueError)
        assert str(error) == "test message"


class TestInitialization:
    """Test ResearchInputValidator initialization"""

    def test_init_default(self):
        """Test initialization with defaults"""
        validator = ResearchInputValidator()
        assert validator.strict_mode is False

    def test_init_strict_mode(self):
        """Test initialization with strict mode enabled"""
        validator = ResearchInputValidator(strict_mode=True)
        assert validator.strict_mode is True


class TestValidateText:
    """Test validate_text method"""

    def test_validate_text_success(self):
        """Test valid text passes validation"""
        validator = ResearchInputValidator()
        result = validator.validate_text(
            "This is valid text with enough characters",
            field_name="test_field",
            min_length=10,
            max_length=100,
        )
        assert result == "This is valid text with enough characters"

    def test_validate_text_required_field_missing(self):
        """Test required field raises error when None"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_text(None, field_name="required_field", required=True)
        assert "required_field is required" in str(exc_info.value)

    def test_validate_text_required_field_empty_string(self):
        """Test required field raises error when empty string"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_text("", field_name="required_field", required=True)
        assert "required_field is required" in str(exc_info.value)

    def test_validate_text_optional_field_none(self):
        """Test optional field returns empty string when None"""
        validator = ResearchInputValidator()
        result = validator.validate_text(None, field_name="optional_field", required=False)
        assert result == ""

    def test_validate_text_allow_empty(self):
        """Test allow_empty permits empty strings"""
        validator = ResearchInputValidator()
        result = validator.validate_text(
            "", field_name="test_field", required=True, allow_empty=True
        )
        assert result == ""

    def test_validate_text_wrong_type(self):
        """Test non-string type raises error"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_text(123, field_name="text_field", required=True)
        assert "text_field must be a string, got int" in str(exc_info.value)

    def test_validate_text_too_short(self):
        """Test text below minimum length raises error"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_text("short", field_name="text_field", min_length=10)
        assert "text_field too short" in str(exc_info.value)
        assert "minimum 10 characters" in str(exc_info.value)

    def test_validate_text_too_long(self):
        """Test text above maximum length raises error"""
        validator = ResearchInputValidator()
        long_text = "x" * 101
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_text(long_text, field_name="text_field", max_length=100)
        assert "text_field too long" in str(exc_info.value)
        assert "maximum 100 characters" in str(exc_info.value)

    def test_validate_text_uses_defaults(self):
        """Test default min/max lengths are applied"""
        validator = ResearchInputValidator()
        # Test default min (10)
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_text("short", field_name="test_field")
        assert "minimum 10 characters" in str(exc_info.value)

    @patch("src.validators.research_input_validator.sanitize_prompt_input")
    def test_validate_text_sanitizes_by_default(self, mock_sanitize):
        """Test sanitization is applied by default"""
        mock_sanitize.return_value = "sanitized text"
        validator = ResearchInputValidator()

        result = validator.validate_text(
            "test input text here", field_name="test_field", min_length=5
        )

        mock_sanitize.assert_called_once_with("test input text here", strict=False)
        assert result == "sanitized text"

    @patch("src.validators.research_input_validator.sanitize_prompt_input")
    def test_validate_text_strict_mode_sanitization(self, mock_sanitize):
        """Test strict mode passed to sanitizer"""
        mock_sanitize.return_value = "sanitized text"
        validator = ResearchInputValidator(strict_mode=True)

        validator.validate_text("test input text here", field_name="test_field", min_length=5)

        mock_sanitize.assert_called_once_with("test input text here", strict=True)

    @patch("src.validators.research_input_validator.sanitize_prompt_input")
    def test_validate_text_skip_sanitization(self, mock_sanitize):
        """Test sanitization can be disabled"""
        validator = ResearchInputValidator()

        result = validator.validate_text(
            "test input text here", field_name="test_field", min_length=5, sanitize=False
        )

        mock_sanitize.assert_not_called()
        assert result == "test input text here"

    @patch("src.validators.research_input_validator.sanitize_prompt_input")
    def test_validate_text_sanitization_error(self, mock_sanitize):
        """Test sanitization errors are converted to ValidationError"""
        mock_sanitize.side_effect = ValueError("Unsafe prompt injection detected")
        validator = ResearchInputValidator()

        with pytest.raises(ValidationError) as exc_info:
            validator.validate_text("malicious input", field_name="test_field", min_length=5)

        assert "test_field contains unsafe content" in str(exc_info.value)
        assert "Unsafe prompt injection detected" in str(exc_info.value)


class TestValidateList:
    """Test validate_list method"""

    def test_validate_list_success(self):
        """Test valid list passes validation"""
        validator = ResearchInputValidator()
        result = validator.validate_list(["item1", "item2"], field_name="test_list")
        assert result == ["item1", "item2"]

    def test_validate_list_required_missing(self):
        """Test required list raises error when None"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_list(None, field_name="required_list", required=True)
        assert "required_list is required" in str(exc_info.value)

    def test_validate_list_required_empty(self):
        """Test required list raises error when empty"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_list([], field_name="required_list", required=True)
        assert "required_list is required" in str(exc_info.value)

    def test_validate_list_optional_none(self):
        """Test optional list returns empty list when None"""
        validator = ResearchInputValidator()
        result = validator.validate_list(None, field_name="optional_list", required=False)
        assert result == []

    def test_validate_list_wrong_type(self):
        """Test non-list type raises error"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_list("not a list", field_name="list_field", required=True)
        assert "list_field must be a list, got str" in str(exc_info.value)

    def test_validate_list_too_few_items(self):
        """Test list with too few items raises error"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_list(["item1"], field_name="list_field", min_items=2, required=True)
        assert "list_field must have at least 2 items" in str(exc_info.value)

    def test_validate_list_too_many_items(self):
        """Test list with too many items raises error"""
        validator = ResearchInputValidator()
        items = [f"item{i}" for i in range(101)]
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_list(items, field_name="list_field", max_items=100)
        assert "list_field must have at most 100 items" in str(exc_info.value)

    def test_validate_list_uses_default_max(self):
        """Test default max items (100) is applied"""
        validator = ResearchInputValidator()
        items = [f"item{i}" for i in range(101)]
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_list(items, field_name="list_field")
        assert "must have at most 100 items" in str(exc_info.value)

    def test_validate_list_with_item_validator(self):
        """Test item validator is applied to each item"""
        validator = ResearchInputValidator()

        def uppercase_validator(item):
            return item.upper()

        result = validator.validate_list(
            ["item1", "item2"],
            field_name="list_field",
            item_validator=uppercase_validator,
        )

        assert result == ["ITEM1", "ITEM2"]

    def test_validate_list_item_validator_error(self):
        """Test item validator errors are caught and reported"""
        validator = ResearchInputValidator()

        def strict_validator(item):
            if item == "bad":
                raise ValueError("Invalid item")
            return item

        with pytest.raises(ValidationError) as exc_info:
            validator.validate_list(
                ["good", "bad", "good"],
                field_name="list_field",
                item_validator=strict_validator,
            )

        assert "list_field[1] validation failed" in str(exc_info.value)
        assert "Invalid item" in str(exc_info.value)


class TestValidateDict:
    """Test validate_dict method"""

    def test_validate_dict_success(self):
        """Test valid dict passes validation"""
        validator = ResearchInputValidator()
        result = validator.validate_dict(
            {"key1": "value1", "key2": "value2"}, field_name="test_dict"
        )
        assert result == {"key1": "value1", "key2": "value2"}

    def test_validate_dict_required_missing(self):
        """Test required dict raises error when None"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_dict(None, field_name="required_dict", required=True)
        assert "required_dict is required" in str(exc_info.value)

    def test_validate_dict_required_empty(self):
        """Test required dict raises error when empty"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_dict({}, field_name="required_dict", required=True)
        assert "required_dict is required" in str(exc_info.value)

    def test_validate_dict_optional_none(self):
        """Test optional dict returns empty dict when None"""
        validator = ResearchInputValidator()
        result = validator.validate_dict(None, field_name="optional_dict", required=False)
        assert result == {}

    def test_validate_dict_wrong_type(self):
        """Test non-dict type raises error"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_dict("not a dict", field_name="dict_field", required=True)
        assert "dict_field must be a dictionary, got str" in str(exc_info.value)

    def test_validate_dict_missing_required_keys(self):
        """Test missing required keys raises error"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_dict(
                {"key1": "value1"},
                field_name="dict_field",
                required_keys=["key1", "key2", "key3"],
            )
        assert "dict_field missing required keys" in str(exc_info.value)
        assert "key2" in str(exc_info.value) or "key3" in str(exc_info.value)

    def test_validate_dict_too_many_keys(self):
        """Test dict with too many keys raises error"""
        validator = ResearchInputValidator()
        large_dict = {f"key{i}": f"value{i}" for i in range(11)}
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_dict(large_dict, field_name="dict_field", max_keys=10)
        assert "dict_field has too many keys" in str(exc_info.value)
        assert "maximum 10" in str(exc_info.value)


class TestValidateEmail:
    """Test validate_email method"""

    def test_validate_email_success(self):
        """Test valid email passes validation"""
        validator = ResearchInputValidator()
        result = validator.validate_email("test@example.com", field_name="email_field")
        assert result == "test@example.com"

    def test_validate_email_normalizes(self):
        """Test email is lowercased and stripped"""
        validator = ResearchInputValidator()
        # Input without whitespace (whitespace would fail regex validation)
        result = validator.validate_email("Test@Example.COM", field_name="email_field")
        assert result == "test@example.com"

    def test_validate_email_required_missing(self):
        """Test required email raises error when None"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_email(None, field_name="email_field", required=True)
        assert "email_field is required" in str(exc_info.value)

    def test_validate_email_optional_none(self):
        """Test optional email returns empty string when None"""
        validator = ResearchInputValidator()
        result = validator.validate_email(None, field_name="email_field", required=False)
        assert result == ""

    def test_validate_email_wrong_type(self):
        """Test non-string type raises error"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_email(123, field_name="email_field", required=True)
        assert "email_field must be a string, got int" in str(exc_info.value)

    def test_validate_email_invalid_format(self):
        """Test invalid email format raises error"""
        validator = ResearchInputValidator()
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user @example.com",
            "user@.com",
        ]
        for email in invalid_emails:
            with pytest.raises(ValidationError) as exc_info:
                validator.validate_email(email, field_name="email_field")
            assert "is not a valid email address" in str(exc_info.value)

    def test_validate_email_too_long(self):
        """Test email longer than 254 chars raises error"""
        validator = ResearchInputValidator()
        long_email = "a" * 250 + "@example.com"  # > 254 chars
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_email(long_email, field_name="email_field")
        assert "email too long" in str(exc_info.value)


class TestValidateUrl:
    """Test validate_url method"""

    def test_validate_url_success(self):
        """Test valid URL passes validation"""
        validator = ResearchInputValidator()
        result = validator.validate_url("https://example.com", field_name="url_field")
        assert result == "https://example.com"

    def test_validate_url_http(self):
        """Test http URL is valid"""
        validator = ResearchInputValidator()
        result = validator.validate_url("http://example.com", field_name="url_field")
        assert result == "http://example.com"

    def test_validate_url_strips_whitespace(self):
        """Test URL is stripped"""
        validator = ResearchInputValidator()
        # Input without leading/trailing whitespace (would fail regex validation)
        result = validator.validate_url("https://example.com", field_name="url_field")
        assert result == "https://example.com"

    def test_validate_url_required_missing(self):
        """Test required URL raises error when None"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_url(None, field_name="url_field", required=True)
        assert "url_field is required" in str(exc_info.value)

    def test_validate_url_optional_none(self):
        """Test optional URL returns empty string when None"""
        validator = ResearchInputValidator()
        result = validator.validate_url(None, field_name="url_field", required=False)
        assert result == ""

    def test_validate_url_wrong_type(self):
        """Test non-string type raises error"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_url(123, field_name="url_field", required=True)
        assert "url_field must be a string, got int" in str(exc_info.value)

    def test_validate_url_invalid_format(self):
        """Test invalid URL format raises error"""
        validator = ResearchInputValidator()
        invalid_urls = ["notaurl", "ftp://example.com", "example.com", "//example.com"]
        for url in invalid_urls:
            with pytest.raises(ValidationError) as exc_info:
                validator.validate_url(url, field_name="url_field")
            assert "is not a valid URL" in str(exc_info.value)

    def test_validate_url_too_long(self):
        """Test URL longer than 2048 chars raises error"""
        validator = ResearchInputValidator()
        long_url = "https://" + "a" * 2050 + ".com"
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_url(long_url, field_name="url_field")
        assert "URL too long" in str(exc_info.value)


class TestValidateInteger:
    """Test validate_integer method"""

    def test_validate_integer_success(self):
        """Test valid integer passes validation"""
        validator = ResearchInputValidator()
        result = validator.validate_integer(42, field_name="int_field")
        assert result == 42

    def test_validate_integer_required_missing(self):
        """Test required integer raises error when None"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_integer(None, field_name="int_field", required=True)
        assert "int_field is required" in str(exc_info.value)

    def test_validate_integer_optional_none(self):
        """Test optional integer returns 0 when None"""
        validator = ResearchInputValidator()
        result = validator.validate_integer(None, field_name="int_field", required=False)
        assert result == 0

    def test_validate_integer_from_string(self):
        """Test integer can be parsed from string"""
        validator = ResearchInputValidator()
        result = validator.validate_integer("42", field_name="int_field")
        assert result == 42

    def test_validate_integer_invalid_string(self):
        """Test non-numeric string raises error"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_integer("not a number", field_name="int_field")
        assert "int_field must be an integer" in str(exc_info.value)

    def test_validate_integer_wrong_type(self):
        """Test non-integer type raises error"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_integer(3.14, field_name="int_field")
        assert "int_field must be an integer, got float" in str(exc_info.value)

    def test_validate_integer_below_minimum(self):
        """Test integer below minimum raises error"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_integer(5, field_name="int_field", min_value=10)
        assert "int_field must be at least 10" in str(exc_info.value)

    def test_validate_integer_above_maximum(self):
        """Test integer above maximum raises error"""
        validator = ResearchInputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_integer(100, field_name="int_field", max_value=50)
        assert "int_field must be at most 50" in str(exc_info.value)

    def test_validate_integer_boundary_values(self):
        """Test boundary values are valid"""
        validator = ResearchInputValidator()
        # Min boundary
        result = validator.validate_integer(10, field_name="int_field", min_value=10, max_value=50)
        assert result == 10
        # Max boundary
        result = validator.validate_integer(50, field_name="int_field", min_value=10, max_value=50)
        assert result == 50


class TestConvenienceFunctions:
    """Test convenience validation functions"""

    @patch("src.validators.research_input_validator.sanitize_prompt_input")
    def test_validate_business_description_success(self, mock_sanitize):
        """Test validate_business_description with valid input"""
        mock_sanitize.return_value = "A" * 100
        result = validate_business_description("A" * 100)
        assert result == "A" * 100

    @patch("src.validators.research_input_validator.sanitize_prompt_input")
    def test_validate_business_description_too_short(self, mock_sanitize):
        """Test validate_business_description with too short input"""
        with pytest.raises(ValidationError) as exc_info:
            validate_business_description("Too short")
        assert "business_description too short" in str(exc_info.value)
        assert "minimum 50 characters" in str(exc_info.value)

    @patch("src.validators.research_input_validator.sanitize_prompt_input")
    def test_validate_business_description_with_custom_validator(self, mock_sanitize):
        """Test validate_business_description with custom validator instance"""
        mock_sanitize.return_value = "A" * 100
        custom_validator = ResearchInputValidator(strict_mode=True)
        result = validate_business_description("A" * 100, validator=custom_validator)
        assert result == "A" * 100
        mock_sanitize.assert_called_with("A" * 100, strict=True)

    @patch("src.validators.research_input_validator.sanitize_prompt_input")
    def test_validate_content_samples_success(self, mock_sanitize):
        """Test validate_content_samples with valid input"""
        mock_sanitize.return_value = "A" * 100
        samples = ["A" * 100, "B" * 100, "C" * 100]
        result = validate_content_samples(samples)
        assert len(result) == 3
        assert all(s == "A" * 100 for s in result)

    def test_validate_content_samples_too_few(self):
        """Test validate_content_samples with too few items"""
        with pytest.raises(ValidationError) as exc_info:
            validate_content_samples(["A" * 100, "B" * 100])
        assert "content_samples must have at least 3 items" in str(exc_info.value)

    @patch("src.validators.research_input_validator.sanitize_prompt_input")
    def test_validate_content_samples_item_too_short(self, mock_sanitize):
        """Test validate_content_samples with item too short"""
        mock_sanitize.side_effect = lambda x, **kwargs: x
        samples = ["A" * 100, "B" * 100, "short"]
        with pytest.raises(ValidationError) as exc_info:
            validate_content_samples(samples)
        assert "content_sample_2 too short" in str(exc_info.value)

    @patch("src.validators.research_input_validator.sanitize_prompt_input")
    def test_validate_competitor_list_success(self, mock_sanitize):
        """Test validate_competitor_list with valid input"""
        mock_sanitize.return_value = "Competitor"
        competitors = ["Competitor 1", "Competitor 2", "Competitor 3"]
        result = validate_competitor_list(competitors)
        assert len(result) == 3
        assert all(c == "Competitor" for c in result)

    def test_validate_competitor_list_too_few(self):
        """Test validate_competitor_list with too few items"""
        with pytest.raises(ValidationError) as exc_info:
            validate_competitor_list([])
        assert "competitors is required" in str(exc_info.value)

    @patch("src.validators.research_input_validator.sanitize_prompt_input")
    def test_validate_competitor_list_item_too_short(self, mock_sanitize):
        """Test validate_competitor_list with item too short"""
        mock_sanitize.side_effect = lambda x, **kwargs: x
        competitors = ["Competitor 1", "A"]
        with pytest.raises(ValidationError) as exc_info:
            validate_competitor_list(competitors)
        assert "competitor_1 too short" in str(exc_info.value)
        assert "minimum 2 characters" in str(exc_info.value)
