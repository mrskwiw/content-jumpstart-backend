"""Unit tests for backend.utils.input_validators (security-critical)."""

import pytest

from backend.utils.input_validators import (
    validate_string_field,
    validate_email,
    validate_id_field,
    validate_integer_field,
    validate_float_field,
    validate_enum_field,
    sanitize_html,
    validate_json_field,
)


class TestValidateStringField:
    # --- Happy path ---
    def test_valid_string_returned(self):
        assert validate_string_field("hello", "name") == "hello"

    def test_strips_whitespace(self):
        assert validate_string_field("  hello  ", "name") == "hello"

    def test_custom_max_length(self):
        assert validate_string_field("abc", "f", max_length=10) == "abc"

    def test_custom_min_length(self):
        assert validate_string_field("hello", "f", min_length=3) == "hello"

    def test_allow_empty_true(self):
        assert validate_string_field("", "f", allow_empty=True, min_length=0) == ""

    def test_none_with_allow_empty(self):
        assert validate_string_field(None, "f", allow_empty=True, min_length=0) == ""

    def test_pattern_match(self):
        assert validate_string_field("ABC123", "f", pattern=r"^[A-Z0-9]+$") == "ABC123"

    # --- Error cases ---
    def test_none_raises_when_required(self):
        with pytest.raises(ValueError, match="is required"):
            validate_string_field(None, "name")

    def test_empty_raises_when_required(self):
        with pytest.raises(ValueError, match="is required"):
            validate_string_field("", "name")

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="too short"):
            validate_string_field("ab", "name", min_length=5)

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="too long"):
            validate_string_field("x" * 501, "name", max_length=500)

    def test_pattern_mismatch_raises(self):
        with pytest.raises(ValueError, match="format is invalid"):
            validate_string_field("hello world", "code", pattern=r"^\w+$")

    # --- Security: injection detection ---
    def test_script_tag_rejected(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_string_field("<script>alert(1)</script>", "bio")

    def test_javascript_protocol_rejected(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_string_field("javascript:alert(1)", "url")

    def test_event_handler_rejected(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_string_field("onerror=alert(1)", "name")

    def test_sql_drop_table_rejected(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_string_field("; DROP TABLE users", "name")

    def test_path_traversal_rejected(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_string_field("../../etc/passwd", "path")

    def test_template_injection_rejected(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_string_field("${7*7}", "name")

    # --- Legitimate business text should pass ---
    def test_double_hyphen_allowed(self):
        assert "self-service" in validate_string_field("self-service platform", "name")

    def test_pipe_allowed(self):
        assert "professional | friendly" in validate_string_field(
            "professional | friendly | innovative", "tone"
        )


class TestValidateEmail:
    def test_valid_email(self):
        assert validate_email("user@example.com") == "user@example.com"

    def test_email_lowercased(self):
        assert validate_email("USER@EXAMPLE.COM") == "user@example.com"

    def test_strips_whitespace(self):
        assert validate_email("  user@example.com  ") == "user@example.com"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Email address format is invalid"):
            validate_email("not-an-email")

    def test_missing_at_sign_raises(self):
        with pytest.raises(ValueError, match="Email address format is invalid"):
            validate_email("userexample.com")

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="too long"):
            validate_email("a" * 250 + "@b.com")

    def test_plus_addressing_allowed(self):
        assert validate_email("user+tag@example.com") == "user+tag@example.com"


class TestValidateIdField:
    def test_valid_id(self):
        assert validate_id_field("proj-12345", "project_id") == "proj-12345"

    def test_strips_whitespace(self):
        assert validate_id_field("  proj-abc  ", "id") == "proj-abc"

    def test_prefix_check_passes(self):
        assert validate_id_field("proj-abc", "id", prefix="proj-") == "proj-abc"

    def test_wrong_prefix_raises(self):
        with pytest.raises(ValueError, match="must start with"):
            validate_id_field("user-abc", "id", prefix="proj-")

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="is required"):
            validate_id_field("", "id")

    def test_none_raises(self):
        with pytest.raises(ValueError, match="is required"):
            validate_id_field(None, "id")

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="too short"):
            validate_id_field("ab", "id", min_length=5)

    def test_invalid_chars_raises(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_id_field("proj@evil!", "id")

    def test_underscore_allowed(self):
        assert validate_id_field("proj_12345", "id") == "proj_12345"


class TestValidateIntegerField:
    def test_valid_int(self):
        assert validate_integer_field(5, "count") == 5

    def test_coerces_string(self):
        assert validate_integer_field("10", "count") == 10  # type: ignore

    def test_min_value_ok(self):
        assert validate_integer_field(5, "count", min_value=1) == 5

    def test_max_value_ok(self):
        assert validate_integer_field(50, "count", max_value=100) == 50

    def test_below_min_raises(self):
        with pytest.raises(ValueError, match="too small"):
            validate_integer_field(0, "count", min_value=1)

    def test_above_max_raises(self):
        with pytest.raises(ValueError, match="too large"):
            validate_integer_field(101, "count", max_value=100)

    def test_non_numeric_string_raises(self):
        with pytest.raises(ValueError, match="whole number"):
            validate_integer_field("abc", "count")  # type: ignore


class TestValidateFloatField:
    def test_valid_float(self):
        assert validate_float_field(3.14, "price") == pytest.approx(3.14)

    def test_accepts_int_as_float(self):
        assert validate_float_field(5, "price") == 5.0

    def test_below_min_raises(self):
        with pytest.raises(ValueError, match="too small"):
            validate_float_field(-1.0, "price", min_value=0.0)

    def test_above_max_raises(self):
        with pytest.raises(ValueError, match="too large"):
            validate_float_field(999.0, "price", max_value=100.0)

    def test_non_numeric_raises(self):
        with pytest.raises(ValueError, match="valid number"):
            validate_float_field("abc", "price")  # type: ignore


class TestValidateEnumField:
    SIZES = ["small", "medium", "large"]

    def test_valid_value(self):
        assert validate_enum_field("small", "size", self.SIZES) == "small"

    def test_case_insensitive_default(self):
        assert validate_enum_field("SMALL", "size", self.SIZES) == "small"

    def test_returns_original_case_from_list(self):
        assert validate_enum_field("Medium", "size", self.SIZES) == "medium"

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError, match="invalid value"):
            validate_enum_field("xlarge", "size", self.SIZES)

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="is required"):
            validate_enum_field("", "size", self.SIZES)

    def test_case_sensitive_mode(self):
        with pytest.raises(ValueError):
            validate_enum_field("Small", "size", self.SIZES, case_sensitive=True)

    def test_more_than_3_options_shows_count(self):
        many = ["a", "b", "c", "d", "e"]
        with pytest.raises(ValueError, match="or 2 more"):
            validate_enum_field("z", "field", many)


class TestSanitizeHtml:
    def test_strips_script_tag(self):
        result = sanitize_html("<script>alert(1)</script>text")
        assert "<script>" not in result
        assert "text" in result

    def test_empty_string_returned_as_empty(self):
        assert sanitize_html("") == ""

    def test_plain_text_unchanged(self):
        assert sanitize_html("Hello world") == "Hello world"

    def test_strips_all_tags_by_default(self):
        result = sanitize_html("<b>bold</b> and <i>italic</i>")
        assert "<b>" not in result
        assert "<i>" not in result
        assert "bold" in result
        assert "italic" in result


class TestValidateJsonField:
    def test_valid_dict(self):
        d = {"key": "value"}
        assert validate_json_field(d, "data") == d

    def test_required_keys_present(self):
        d = {"a": 1, "b": 2}
        assert validate_json_field(d, "data", required_keys=["a", "b"]) == d

    def test_missing_required_key_raises(self):
        with pytest.raises(ValueError, match="missing required keys"):
            validate_json_field({"a": 1}, "data", required_keys=["a", "b"])

    def test_non_dict_raises(self):
        with pytest.raises(ValueError, match="valid JSON object"):
            validate_json_field([1, 2, 3], "data")  # type: ignore

    def test_deeply_nested_raises(self):
        nested = {}
        d = nested
        for _ in range(15):
            d["child"] = {}
            d = d["child"]
        with pytest.raises(ValueError, match="maximum nesting depth"):
            validate_json_field(nested, "data", max_depth=10)

    def test_acceptable_nesting(self):
        d = {"level1": {"level2": {"level3": "value"}}}
        assert validate_json_field(d, "data", max_depth=5) == d
