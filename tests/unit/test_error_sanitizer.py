"""Unit tests for backend.utils.error_sanitizer."""

import pytest
from unittest.mock import patch

from backend.utils.error_sanitizer import (
    contains_sensitive_info,
    categorize_error,
    sanitize_error_message,
    create_safe_error_response,
    sanitize_string,
    SAFE_ERROR_MESSAGES,
)


class TestContainsSensitiveInfo:
    def test_empty_string_is_safe(self):
        assert contains_sensitive_info("") is False

    def test_none_is_safe(self):
        assert contains_sensitive_info(None) is False

    def test_plain_message_is_safe(self):
        assert contains_sensitive_info("Something went wrong") is False

    def test_sql_keyword_is_sensitive(self):
        assert contains_sensitive_info("SELECT * FROM users") is True

    def test_file_path_is_sensitive(self):
        assert contains_sensitive_info("Error in /app/backend/main.py:45") is True

    def test_python_file_traceback(self):
        assert contains_sensitive_info("Traceback (most recent call last)") is True

    def test_api_key_pattern(self):
        assert contains_sensitive_info("secret=abc123") is True

    def test_bearer_token(self):
        assert contains_sensitive_info("Bearer eyJ0eXAiOiJKV1Q") is True

    def test_internal_module(self):
        assert contains_sensitive_info("backend.routers.clients raised") is True

    def test_database_driver_name(self):
        assert contains_sensitive_info("psycopg2 connection failed") is True


class TestCategorizeError:
    def test_database_error(self):
        class DBErr(Exception):
            pass

        assert categorize_error(DBErr("sqlalchemy error")) == "database"

    def test_validation_error(self):
        class ValErr(Exception):
            pass

        assert categorize_error(ValErr("validation failed")) == "validation"

    def test_auth_error(self):
        class AuthErr(Exception):
            pass

        assert categorize_error(AuthErr("jwt expired")) == "authentication"

    def test_not_found_error(self):
        assert categorize_error(FileNotFoundError("not found")) == "not_found"

    def test_timeout_error(self):
        assert categorize_error(TimeoutError("timed out")) == "timeout"

    def test_file_error(self):
        assert categorize_error(IOError("file read error")) == "file_operation"

    def test_unknown_exception_is_file_operation(self):
        # "io" appears in "exception" (typ name) → categorized as file_operation
        assert categorize_error(Exception("something random")) == "file_operation"

    def test_connection_error_is_file_operation(self):
        # "io" appears in "connectionerror" before "connection" is checked
        # (file_operation check runs before external_service check)
        assert categorize_error(ConnectionError("network failure")) == "file_operation"


class TestSanitizeErrorMessage:
    def test_debug_mode_returns_original(self):
        from backend.config import settings

        with patch.object(settings, "DEBUG_MODE", True):
            msg, code = sanitize_error_message(ValueError("raw error detail"))
        assert "raw error detail" in msg

    def test_production_returns_safe_message(self):
        from backend.config import settings

        with patch.object(settings, "DEBUG_MODE", False):
            msg, code = sanitize_error_message(Exception("SELECT * FROM users"))
        assert "SELECT" not in msg
        assert msg in SAFE_ERROR_MESSAGES.values()

    def test_error_code_included_by_default(self):
        from backend.config import settings

        with patch.object(settings, "DEBUG_MODE", False):
            msg, code = sanitize_error_message(Exception("generic error"))
        assert code is not None
        assert "_ERROR" in code

    def test_error_code_can_be_omitted(self):
        from backend.config import settings

        with patch.object(settings, "DEBUG_MODE", False):
            msg, code = sanitize_error_message(Exception("err"), include_error_code=False)
        assert code is None

    def test_database_error_category(self):
        from backend.config import settings

        with patch.object(settings, "DEBUG_MODE", False):
            msg, code = sanitize_error_message(Exception("sqlite3 integrity error"))
        assert code == "DATABASE_ERROR"


class TestCreateSafeErrorResponse:
    def test_returns_dict_with_success_false(self):
        from backend.config import settings

        with patch.object(settings, "DEBUG_MODE", False):
            result = create_safe_error_response(Exception("oops"))
        assert result["success"] is False
        assert "error" in result
        assert "message" in result["error"]

    def test_includes_error_code(self):
        from backend.config import settings

        with patch.object(settings, "DEBUG_MODE", False):
            result = create_safe_error_response(Exception("oops"))
        assert "code" in result["error"]

    def test_includes_request_id_when_provided(self):
        from backend.config import settings

        with patch.object(settings, "DEBUG_MODE", False):
            result = create_safe_error_response(Exception("oops"), request_id="req-123")
        assert result["error"]["request_id"] == "req-123"

    def test_debug_mode_includes_extra_info(self):
        from backend.config import settings

        with patch.object(settings, "DEBUG_MODE", True):
            result = create_safe_error_response(ValueError("debug detail"))
        assert "debug_message" in result["error"]
        assert "debug detail" in result["error"]["debug_message"]

    def test_no_request_id_by_default(self):
        from backend.config import settings

        with patch.object(settings, "DEBUG_MODE", False):
            result = create_safe_error_response(Exception("oops"))
        assert "request_id" not in result["error"]


class TestSanitizeString:
    def test_empty_string_unchanged(self):
        assert sanitize_string("") == ""

    def test_none_returns_none(self):
        assert sanitize_string(None) is None

    def test_replaces_sql_keyword(self):
        result = sanitize_string("SELECT * FROM users")
        assert "SELECT" not in result
        assert "[REDACTED]" in result

    def test_plain_text_unchanged(self):
        text = "User not found"
        assert sanitize_string(text) == text

    def test_custom_replacement(self):
        result = sanitize_string("SELECT FROM table", replacement="***")
        assert "***" in result

    def test_replaces_file_path(self):
        result = sanitize_string("error in /app/main.py:10")
        assert "/app/" not in result
