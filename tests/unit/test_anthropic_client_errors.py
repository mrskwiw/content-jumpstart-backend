"""Unit tests for AnthropicClient error handling and diagnostics.

Tests cover:
- APIErrorReport dataclass
- Error recording and tracking
- Connection health check
- Error summary generation
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.utils.anthropic_client import AnthropicClient, APIErrorReport
from src.utils.connection_diagnostics import ConnectionDiagnostics, ConnectionErrorType


class TestAPIErrorReport:
    """Tests for APIErrorReport dataclass."""

    def test_default_values(self):
        """Test APIErrorReport initializes with defaults."""
        report = APIErrorReport()

        assert isinstance(report.timestamp, datetime)
        assert report.operation == ""
        assert report.model == ""
        assert report.attempt == 1
        assert report.max_attempts == 3
        assert report.error_type == ""
        assert report.error_message == ""
        assert report.diagnostics is None
        assert report.recovery_action == ""

    def test_to_log_message(self):
        """Test log message generation."""
        report = APIErrorReport(
            operation="post_generation",
            model="claude-3-5-sonnet",
            attempt=2,
            max_attempts=3,
            error_type="APIConnectionError",
            error_message="Connection refused",
            recovery_action="Retrying connection",
        )

        message = report.to_log_message()

        assert "API Error Report" in message
        assert "post_generation" in message
        assert "claude-3-5-sonnet" in message
        assert "2/3" in message
        assert "APIConnectionError" in message
        assert "Connection refused" in message
        assert "Retrying connection" in message

    def test_log_message_truncates_long_errors(self):
        """Test that long error messages are truncated."""
        long_message = "x" * 500
        report = APIErrorReport(error_message=long_message)

        message = report.to_log_message()

        # Should only contain first 200 chars of error message
        assert "x" * 200 in message
        assert "x" * 201 not in message


class TestAnthropicClientErrorTracking:
    """Tests for AnthropicClient error tracking methods."""

    @pytest.fixture
    def mock_client(self):
        """Create mock AnthropicClient for testing."""
        with patch("src.utils.anthropic_client.Anthropic"):
            with patch("src.utils.anthropic_client.AsyncAnthropic"):
                with patch("src.utils.anthropic_client.settings") as mock_settings:
                    mock_settings.ANTHROPIC_API_KEY = (
                        "sk-ant-test-key-12345678901234567890"  # pragma: allowlist secret
                    )
                    mock_settings.ANTHROPIC_MODEL = "claude-3-5-sonnet"
                    mock_settings.MAX_TOKENS = 4096
                    mock_settings.TEMPERATURE = 0.7
                    mock_settings.ENABLE_RESPONSE_CACHE = False
                    mock_settings.ENABLE_PROMPT_CACHING = False

                    with patch("src.utils.anthropic_client.get_default_tracker"):
                        client = AnthropicClient(
                            api_key="sk-ant-test-key-12345678901234567890"
                        )  # pragma: allowlist secret
                        yield client

    def test_initial_state(self, mock_client):
        """Test client initializes with clean error state."""
        assert mock_client.error_history == []
        assert mock_client.consecutive_failures == 0
        assert mock_client.last_successful_call is None
        assert mock_client.connection_verified is False

    def test_record_success(self, mock_client):
        """Test successful call recording."""
        # Simulate some failures first
        mock_client.consecutive_failures = 5

        mock_client._record_success()

        assert mock_client.consecutive_failures == 0
        assert mock_client.last_successful_call is not None
        assert isinstance(mock_client.last_successful_call, datetime)

    def test_record_error_rate_limit(self, mock_client):
        """Test recording rate limit error."""
        from anthropic import RateLimitError

        error = RateLimitError("Rate limit exceeded", response=MagicMock(), body=None)

        with patch("src.utils.anthropic_client.diagnose_connection_error"):
            report = mock_client._record_error(
                exception=error,
                operation="test_operation",
                attempt=1,
                max_attempts=3,
                run_diagnostics=False,
            )

        assert report.error_type == "RateLimitError"
        assert report.recovery_action == "Waiting with exponential backoff"
        assert mock_client.consecutive_failures == 1
        assert len(mock_client.error_history) == 1

    def test_record_error_connection(self, mock_client):
        """Test recording connection error with diagnostics."""
        from anthropic import APIConnectionError

        # APIConnectionError requires a request parameter
        mock_request = MagicMock()
        error = APIConnectionError(message="Connection refused", request=mock_request)

        mock_diagnostics = ConnectionDiagnostics(
            error_type=ConnectionErrorType.CONNECTION_REFUSED,
            suggestions=["Check firewall", "Verify network"],
        )

        with patch(
            "src.utils.anthropic_client.diagnose_connection_error",
            return_value=mock_diagnostics,
        ):
            report = mock_client._record_error(
                exception=error,
                operation="test_operation",
                attempt=2,
                max_attempts=3,
                run_diagnostics=True,
            )

        assert report.error_type == "APIConnectionError"
        assert report.recovery_action == "Retrying connection"
        assert report.diagnostics is not None
        assert report.diagnostics.error_type == ConnectionErrorType.CONNECTION_REFUSED
        assert mock_client.consecutive_failures == 1

    def test_record_error_api_error(self, mock_client):
        """Test recording general API error."""
        from anthropic import APIError

        error = APIError(
            message="Bad request",
            request=MagicMock(),
            body={"error": "invalid_request"},
        )
        error.status_code = 400

        report = mock_client._record_error(
            exception=error,
            operation="test_operation",
            attempt=1,
            max_attempts=3,
            run_diagnostics=False,
        )

        assert "APIError" in report.error_type
        assert "400" in report.error_type
        assert report.recovery_action == "No retry - non-retryable error"

    def test_error_history_limit(self, mock_client):
        """Test error history is limited to 50 entries."""
        # Add more than 50 errors
        for i in range(60):
            mock_client._record_error(
                exception=Exception(f"Error {i}"),
                operation="test",
                attempt=1,
                max_attempts=3,
                run_diagnostics=False,
            )

        # Should only keep last 50
        assert len(mock_client.error_history) == 50
        # Most recent should be Error 59
        assert "Error 59" in mock_client.error_history[-1].error_message

    def test_get_error_summary_empty(self, mock_client):
        """Test error summary with no errors."""
        summary = mock_client.get_error_summary()

        assert summary["total_errors"] == 0
        assert summary["consecutive_failures"] == 0
        assert summary["last_successful_call"] is None
        assert summary["connection_verified"] is False
        assert summary["error_types"] == {}
        assert summary["recent_errors"] == []

    def test_get_error_summary_with_errors(self, mock_client):
        """Test error summary with recorded errors."""
        # Add some errors of different types
        mock_client._record_error(
            exception=Exception("Connection error 1"),
            operation="op1",
            attempt=1,
            max_attempts=3,
            run_diagnostics=False,
        )
        mock_client._record_error(
            exception=Exception("Connection error 2"),
            operation="op2",
            attempt=1,
            max_attempts=3,
            run_diagnostics=False,
        )
        mock_client._record_success()  # Reset consecutive failures
        mock_client._record_error(
            exception=ValueError("Different error"),
            operation="op3",
            attempt=1,
            max_attempts=3,
            run_diagnostics=False,
        )

        summary = mock_client.get_error_summary()

        assert summary["total_errors"] == 3
        assert summary["consecutive_failures"] == 1  # Only last error since success
        assert summary["last_successful_call"] is not None
        assert "Exception" in summary["error_types"]
        assert "ValueError" in summary["error_types"]
        assert len(summary["recent_errors"]) == 3


class TestAnthropicClientHealthCheck:
    """Tests for connection health check."""

    @pytest.fixture
    def mock_client(self):
        """Create mock AnthropicClient for testing."""
        with patch("src.utils.anthropic_client.Anthropic"):
            with patch("src.utils.anthropic_client.AsyncAnthropic"):
                with patch("src.utils.anthropic_client.settings") as mock_settings:
                    mock_settings.ANTHROPIC_API_KEY = (
                        "sk-ant-test-key-12345678901234567890"  # pragma: allowlist secret
                    )
                    mock_settings.ANTHROPIC_MODEL = "claude-3-5-sonnet"
                    mock_settings.MAX_TOKENS = 4096
                    mock_settings.TEMPERATURE = 0.7
                    mock_settings.ENABLE_RESPONSE_CACHE = False
                    mock_settings.ENABLE_PROMPT_CACHING = False

                    with patch("src.utils.anthropic_client.get_default_tracker"):
                        client = AnthropicClient(
                            api_key="sk-ant-test-key-12345678901234567890"
                        )  # pragma: allowlist secret
                        yield client

    def test_health_check_success(self, mock_client):
        """Test successful health check."""
        mock_diagnostics = ConnectionDiagnostics(
            dns_resolved=True,
            port_open=True,
            ssl_valid=True,
            dns_resolution_time_ms=25.0,
            connection_time_ms=100.0,
            ssl_handshake_time_ms=150.0,
        )

        with patch(
            "src.utils.anthropic_client.check_anthropic_connectivity",
            return_value=mock_diagnostics,
        ):
            result = mock_client.check_connection_health()

        assert result.dns_resolved is True
        assert result.port_open is True
        assert result.ssl_valid is True
        assert mock_client.connection_verified is True

    def test_health_check_dns_failure(self, mock_client):
        """Test health check with DNS failure."""
        mock_diagnostics = ConnectionDiagnostics(
            dns_resolved=False,
            port_open=False,
            ssl_valid=False,
        )

        with patch(
            "src.utils.anthropic_client.check_anthropic_connectivity",
            return_value=mock_diagnostics,
        ):
            result = mock_client.check_connection_health()

        assert result.dns_resolved is False
        assert mock_client.connection_verified is False

    def test_health_check_ssl_failure(self, mock_client):
        """Test health check with SSL failure."""
        mock_diagnostics = ConnectionDiagnostics(
            dns_resolved=True,
            port_open=True,
            ssl_valid=False,
        )

        with patch(
            "src.utils.anthropic_client.check_anthropic_connectivity",
            return_value=mock_diagnostics,
        ):
            result = mock_client.check_connection_health()

        assert result.dns_resolved is True
        assert result.ssl_valid is False
        assert mock_client.connection_verified is False


class TestEnhancedErrorHandling:
    """Tests for enhanced error handling in create_message."""

    @pytest.fixture
    def mock_client(self):
        """Create mock AnthropicClient for testing."""
        with patch("src.utils.anthropic_client.Anthropic") as MockAnthropic:
            with patch("src.utils.anthropic_client.AsyncAnthropic"):
                with patch("src.utils.anthropic_client.settings") as mock_settings:
                    mock_settings.ANTHROPIC_API_KEY = (
                        "sk-ant-test-key-12345678901234567890"  # pragma: allowlist secret
                    )
                    mock_settings.ANTHROPIC_MODEL = "claude-3-5-sonnet"
                    mock_settings.MAX_TOKENS = 4096
                    mock_settings.TEMPERATURE = 0.7
                    mock_settings.ENABLE_RESPONSE_CACHE = False
                    mock_settings.ENABLE_PROMPT_CACHING = False
                    mock_settings.CACHE_SYSTEM_PROMPTS = False

                    with patch("src.utils.anthropic_client.get_default_tracker"):
                        client = AnthropicClient(
                            api_key="sk-ant-test-key-12345678901234567890"
                        )  # pragma: allowlist secret
                        client.max_retries = 2  # Reduce for faster tests
                        client.retry_delay = 0.01  # Very short delay for tests
                        yield client, MockAnthropic

    def test_successful_call_records_success(self, mock_client):
        """Test that successful API calls record success."""
        client, MockAnthropic = mock_client

        # Mock successful response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Generated content")]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)
        client.client.messages.create.return_value = mock_response

        result = client.create_message(
            messages=[{"role": "user", "content": "Test"}],
            operation="test_op",
        )

        assert result == "Generated content"
        assert client.consecutive_failures == 0
        assert client.last_successful_call is not None

    def test_connection_error_records_error_with_diagnostics(self, mock_client):
        """Test that connection errors trigger diagnostics."""
        from anthropic import APIConnectionError

        client, MockAnthropic = mock_client

        # APIConnectionError requires a request parameter
        mock_request = MagicMock()

        # Make all retries fail
        client.client.messages.create.side_effect = APIConnectionError(
            message="Connection refused", request=mock_request
        )

        mock_diagnostics = ConnectionDiagnostics(
            error_type=ConnectionErrorType.CONNECTION_REFUSED,
            suggestions=["Check firewall"],
        )

        with patch(
            "src.utils.anthropic_client.diagnose_connection_error",
            return_value=mock_diagnostics,
        ):
            with pytest.raises(APIConnectionError):
                client.create_message(
                    messages=[{"role": "user", "content": "Test"}],
                    operation="test_op",
                )

        # Should have recorded errors for each retry
        assert len(client.error_history) >= 1
        assert client.consecutive_failures >= 1


class TestRateLimitHandling:
    """Tests for rate limit error handling."""

    @pytest.fixture
    def mock_client(self):
        """Create mock AnthropicClient for testing."""
        with patch("src.utils.anthropic_client.Anthropic") as MockAnthropic:
            with patch("src.utils.anthropic_client.AsyncAnthropic"):
                with patch("src.utils.anthropic_client.settings") as mock_settings:
                    mock_settings.ANTHROPIC_API_KEY = (
                        "sk-ant-test-key-12345678901234567890"  # pragma: allowlist secret
                    )
                    mock_settings.ANTHROPIC_MODEL = "claude-3-5-sonnet"
                    mock_settings.MAX_TOKENS = 4096
                    mock_settings.TEMPERATURE = 0.7
                    mock_settings.ENABLE_RESPONSE_CACHE = False
                    mock_settings.ENABLE_PROMPT_CACHING = False
                    mock_settings.CACHE_SYSTEM_PROMPTS = False

                    with patch("src.utils.anthropic_client.get_default_tracker"):
                        client = AnthropicClient(
                            api_key="sk-ant-test-key-12345678901234567890"
                        )  # pragma: allowlist secret
                        client.max_retries = 2
                        client.retry_delay = 0.01
                        yield client, MockAnthropic

    def test_rate_limit_recovery(self, mock_client):
        """Test successful recovery after rate limit."""
        from anthropic import RateLimitError

        client, MockAnthropic = mock_client

        # First call hits rate limit, second succeeds
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Success after retry")]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)

        mock_error = RateLimitError("Rate limit exceeded", response=MagicMock(), body=None)

        client.client.messages.create.side_effect = [mock_error, mock_response]

        result = client.create_message(
            messages=[{"role": "user", "content": "Test"}],
            operation="test_op",
        )

        assert result == "Success after retry"
        # Should have recorded one error then success
        assert len(client.error_history) == 1
        assert client.consecutive_failures == 0  # Reset on success


class TestAPIErrorHandling:
    """Tests for general API error handling."""

    @pytest.fixture
    def mock_client(self):
        """Create mock AnthropicClient for testing."""
        with patch("src.utils.anthropic_client.Anthropic") as MockAnthropic:
            with patch("src.utils.anthropic_client.AsyncAnthropic"):
                with patch("src.utils.anthropic_client.settings") as mock_settings:
                    mock_settings.ANTHROPIC_API_KEY = (
                        "sk-ant-test-key-12345678901234567890"  # pragma: allowlist secret
                    )
                    mock_settings.ANTHROPIC_MODEL = "claude-3-5-sonnet"
                    mock_settings.MAX_TOKENS = 4096
                    mock_settings.TEMPERATURE = 0.7
                    mock_settings.ENABLE_RESPONSE_CACHE = False
                    mock_settings.ENABLE_PROMPT_CACHING = False
                    mock_settings.CACHE_SYSTEM_PROMPTS = False

                    with patch("src.utils.anthropic_client.get_default_tracker"):
                        client = AnthropicClient(
                            api_key="sk-ant-test-key-12345678901234567890"
                        )  # pragma: allowlist secret
                        client.max_retries = 2
                        client.retry_delay = 0.01
                        yield client, MockAnthropic

    def test_api_error_no_retry(self, mock_client):
        """Test that API errors don't trigger retry."""
        from anthropic import APIError

        client, MockAnthropic = mock_client

        mock_error = APIError(
            message="Bad request",
            request=MagicMock(),
            body={"error": "invalid_request"},
        )
        mock_error.status_code = 400

        client.client.messages.create.side_effect = mock_error

        with pytest.raises(APIError):
            client.create_message(
                messages=[{"role": "user", "content": "Test"}],
                operation="test_op",
            )

        # Should only have one error (no retries)
        assert len(client.error_history) == 1
        assert "400" in client.error_history[0].error_type

    def test_empty_response_raises_error(self, mock_client):
        """Test that empty API response raises error."""
        client, MockAnthropic = mock_client

        mock_response = MagicMock()
        mock_response.content = []  # Empty content

        client.client.messages.create.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            client.create_message(
                messages=[{"role": "user", "content": "Test"}],
                operation="test_op",
            )

        assert "Empty response" in str(exc_info.value)


class TestErrorSummaryDetails:
    """Tests for detailed error summary functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create mock AnthropicClient for testing."""
        with patch("src.utils.anthropic_client.Anthropic"):
            with patch("src.utils.anthropic_client.AsyncAnthropic"):
                with patch("src.utils.anthropic_client.settings") as mock_settings:
                    mock_settings.ANTHROPIC_API_KEY = (
                        "sk-ant-test-key-12345678901234567890"  # pragma: allowlist secret
                    )
                    mock_settings.ANTHROPIC_MODEL = "claude-3-5-sonnet"
                    mock_settings.MAX_TOKENS = 4096
                    mock_settings.TEMPERATURE = 0.7
                    mock_settings.ENABLE_RESPONSE_CACHE = False
                    mock_settings.ENABLE_PROMPT_CACHING = False

                    with patch("src.utils.anthropic_client.get_default_tracker"):
                        client = AnthropicClient(
                            api_key="sk-ant-test-key-12345678901234567890"
                        )  # pragma: allowlist secret
                        yield client

    def test_error_summary_counts_by_type(self, mock_client):
        """Test error summary correctly counts errors by type."""
        # Add errors of different types
        mock_client._record_error(
            exception=TimeoutError("Timeout 1"),
            operation="op1",
            attempt=1,
            max_attempts=3,
            run_diagnostics=False,
        )
        mock_client._record_error(
            exception=TimeoutError("Timeout 2"),
            operation="op2",
            attempt=1,
            max_attempts=3,
            run_diagnostics=False,
        )
        mock_client._record_error(
            exception=ConnectionRefusedError("Refused"),
            operation="op3",
            attempt=1,
            max_attempts=3,
            run_diagnostics=False,
        )

        summary = mock_client.get_error_summary()

        assert summary["total_errors"] == 3
        assert summary["error_types"]["TimeoutError"] == 2
        assert summary["error_types"]["ConnectionRefusedError"] == 1

    def test_error_summary_recent_errors(self, mock_client):
        """Test error summary shows recent errors correctly."""
        # Add 7 errors
        for i in range(7):
            mock_client._record_error(
                exception=Exception(f"Error {i}"),
                operation=f"op{i}",
                attempt=1,
                max_attempts=3,
                run_diagnostics=False,
            )

        summary = mock_client.get_error_summary()

        # Should only show last 5 errors
        assert len(summary["recent_errors"]) == 5
        # Most recent should be Error 6
        assert "Error 6" in summary["recent_errors"][-1]["message"]

    def test_error_summary_truncates_message(self, mock_client):
        """Test error summary truncates long messages."""
        long_message = "x" * 200
        mock_client._record_error(
            exception=Exception(long_message),
            operation="op",
            attempt=1,
            max_attempts=3,
            run_diagnostics=False,
        )

        summary = mock_client.get_error_summary()

        # Message should be truncated to 100 chars
        assert len(summary["recent_errors"][0]["message"]) == 100


class TestConnectionVerification:
    """Tests for connection verification state."""

    @pytest.fixture
    def mock_client(self):
        """Create mock AnthropicClient for testing."""
        with patch("src.utils.anthropic_client.Anthropic"):
            with patch("src.utils.anthropic_client.AsyncAnthropic"):
                with patch("src.utils.anthropic_client.settings") as mock_settings:
                    mock_settings.ANTHROPIC_API_KEY = (
                        "sk-ant-test-key-12345678901234567890"  # pragma: allowlist secret
                    )
                    mock_settings.ANTHROPIC_MODEL = "claude-3-5-sonnet"
                    mock_settings.MAX_TOKENS = 4096
                    mock_settings.TEMPERATURE = 0.7
                    mock_settings.ENABLE_RESPONSE_CACHE = False
                    mock_settings.ENABLE_PROMPT_CACHING = False

                    with patch("src.utils.anthropic_client.get_default_tracker"):
                        client = AnthropicClient(
                            api_key="sk-ant-test-key-12345678901234567890"
                        )  # pragma: allowlist secret
                        yield client

    def test_health_check_partial_failure(self, mock_client):
        """Test health check with partial failure (port open, SSL fails)."""
        mock_diagnostics = ConnectionDiagnostics(
            dns_resolved=True,
            port_open=True,
            ssl_valid=False,  # SSL fails
            dns_resolution_time_ms=25.0,
            connection_time_ms=100.0,
        )

        with patch(
            "src.utils.anthropic_client.check_anthropic_connectivity",
            return_value=mock_diagnostics,
        ):
            result = mock_client.check_connection_health()

        assert result.dns_resolved is True
        assert result.port_open is True
        assert result.ssl_valid is False
        assert mock_client.connection_verified is False  # Should fail overall

    def test_health_check_included_in_summary(self, mock_client):
        """Test that connection_verified appears in error summary."""
        mock_client.connection_verified = True

        summary = mock_client.get_error_summary()

        assert summary["connection_verified"] is True


class TestAPIErrorReportDetails:
    """Additional tests for APIErrorReport."""

    def test_report_with_diagnostics(self):
        """Test error report includes diagnostics info."""
        diagnostics = ConnectionDiagnostics(
            error_type=ConnectionErrorType.DNS_RESOLUTION_FAILED,
            dns_resolved=False,
        )

        report = APIErrorReport(
            operation="test_op",
            model="claude-3-5-sonnet",
            attempt=2,
            max_attempts=3,
            error_type="APIConnectionError",
            error_message="DNS lookup failed",
            diagnostics=diagnostics,
            recovery_action="Retrying",
        )

        assert report.diagnostics is not None
        assert report.diagnostics.error_type == ConnectionErrorType.DNS_RESOLUTION_FAILED
        assert report.diagnostics.dns_resolved is False

    def test_report_timestamp_is_recent(self):
        """Test that report timestamp is automatically set to now."""
        report = APIErrorReport()

        # Timestamp should be within last second
        time_diff = (datetime.now() - report.timestamp).total_seconds()
        assert time_diff < 1.0
