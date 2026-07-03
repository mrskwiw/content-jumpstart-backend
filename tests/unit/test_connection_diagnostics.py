"""Unit tests for connection diagnostics module.

Tests cover:
- ConnectionErrorType classification
- ConnectionDiagnostics dataclass
- ConnectionDiagnosticsRunner methods
- Error suggestion generation
"""

import socket
import ssl
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.utils.connection_diagnostics import (
    ConnectionDiagnostics,
    ConnectionDiagnosticsRunner,
    ConnectionErrorType,
    check_anthropic_connectivity,
    diagnose_connection_error,
    get_diagnostics_runner,
)


class TestConnectionErrorType:
    """Tests for ConnectionErrorType enum."""

    def test_all_error_types_have_values(self):
        """Verify all error types have string values."""
        for error_type in ConnectionErrorType:
            assert isinstance(error_type.value, str)
            assert len(error_type.value) > 0

    def test_error_type_values(self):
        """Test specific error type values."""
        assert ConnectionErrorType.DNS_RESOLUTION_FAILED.value == "dns_resolution_failed"
        assert ConnectionErrorType.CONNECTION_TIMEOUT.value == "connection_timeout"
        assert ConnectionErrorType.SSL_CERTIFICATE_ERROR.value == "ssl_certificate_error"
        assert ConnectionErrorType.RATE_LIMITED.value == "rate_limited"
        assert ConnectionErrorType.UNKNOWN.value == "unknown"


class TestConnectionDiagnostics:
    """Tests for ConnectionDiagnostics dataclass."""

    def test_default_values(self):
        """Test that diagnostics initialize with default values."""
        diag = ConnectionDiagnostics()

        assert isinstance(diag.timestamp, datetime)
        assert diag.endpoint == ""
        assert diag.error_type == ConnectionErrorType.UNKNOWN
        assert diag.dns_resolved is False
        assert diag.port_open is False
        assert diag.ssl_valid is False
        assert diag.suggestions == []

    def test_to_dict(self):
        """Test conversion to dictionary."""
        diag = ConnectionDiagnostics(
            endpoint="https://api.anthropic.com",
            error_type=ConnectionErrorType.CONNECTION_TIMEOUT,
            error_message="Connection timed out",
            dns_resolved=True,
            resolved_ip="192.168.1.1",
            dns_resolution_time_ms=50.5,
        )

        result = diag.to_dict()

        assert result["endpoint"] == "https://api.anthropic.com"
        assert result["error_type"] == "connection_timeout"
        assert result["error_message"] == "Connection timed out"
        assert result["network"]["dns_resolved"] is True
        assert result["network"]["resolved_ip"] == "192.168.1.1"
        assert result["timing"]["dns_resolution_ms"] == 50.5

    def test_to_report(self):
        """Test human-readable report generation."""
        diag = ConnectionDiagnostics(
            endpoint="https://api.anthropic.com",
            error_type=ConnectionErrorType.DNS_RESOLUTION_FAILED,
            error_message="Failed to resolve hostname",
            dns_resolved=False,
            attempt_number=2,
            max_attempts=3,
            suggestions=["Check internet connection", "Verify DNS settings"],
        )

        report = diag.to_report()

        assert "CONNECTION DIAGNOSTIC REPORT" in report
        assert "https://api.anthropic.com" in report
        assert "DNS RESOLUTION FAILED" in report
        assert "DNS Resolution: ✗ Failed" in report
        assert "Attempt: 2 of 3" in report
        assert "Check internet connection" in report
        assert "Verify DNS settings" in report

    def test_to_report_with_timing(self):
        """Test report includes timing information."""
        diag = ConnectionDiagnostics(
            dns_resolved=True,
            port_open=True,
            ssl_valid=True,
            dns_resolution_time_ms=25.5,
            connection_time_ms=100.3,
            ssl_handshake_time_ms=150.7,
            total_time_ms=276.5,
        )

        report = diag.to_report()

        assert "DNS Resolution: 25.5ms" in report
        assert "Connection: 100.3ms" in report
        assert "SSL Handshake: 150.7ms" in report
        assert "Total: 276.5ms" in report


class TestConnectionDiagnosticsRunner:
    """Tests for ConnectionDiagnosticsRunner class."""

    @pytest.fixture
    def runner(self):
        """Create diagnostics runner for testing."""
        return ConnectionDiagnosticsRunner(timeout=5.0)

    def test_check_dns_resolution_success(self, runner):
        """Test successful DNS resolution."""
        with patch("socket.gethostbyname") as mock_dns:
            mock_dns.return_value = "104.18.7.192"

            success, ip, time_ms = runner.check_dns_resolution("api.anthropic.com")

            assert success is True
            assert ip == "104.18.7.192"
            assert time_ms is not None
            assert time_ms >= 0

    def test_check_dns_resolution_failure(self, runner):
        """Test DNS resolution failure."""
        with patch("socket.gethostbyname") as mock_dns:
            mock_dns.side_effect = socket.gaierror(8, "Name not resolved")

            success, ip, time_ms = runner.check_dns_resolution("invalid.hostname.test")

            assert success is False
            assert ip is None
            assert time_ms is not None

    def test_check_port_connectivity_success(self, runner):
        """Test successful port connectivity."""
        mock_sock = MagicMock()
        with patch("socket.create_connection") as mock_conn:
            mock_conn.return_value = mock_sock

            success, time_ms = runner.check_port_connectivity("api.anthropic.com", 443)

            assert success is True
            assert time_ms is not None
            mock_sock.close.assert_called_once()

    def test_check_port_connectivity_timeout(self, runner):
        """Test port connectivity timeout."""
        with patch("socket.create_connection") as mock_conn:
            mock_conn.side_effect = socket.timeout("timed out")

            success, time_ms = runner.check_port_connectivity("api.anthropic.com", 443)

            assert success is False
            assert time_ms is not None

    def test_check_port_connectivity_refused(self, runner):
        """Test connection refused."""
        with patch("socket.create_connection") as mock_conn:
            mock_conn.side_effect = ConnectionRefusedError("Connection refused")

            success, time_ms = runner.check_port_connectivity("api.anthropic.com", 443)

            assert success is False
            assert time_ms is not None

    def test_classify_error_dns(self, runner):
        """Test DNS error classification."""
        dns_error = socket.gaierror(8, "Name or service not known")
        result = runner.classify_error(dns_error)
        assert result == ConnectionErrorType.DNS_RESOLUTION_FAILED

    def test_classify_error_timeout(self, runner):
        """Test timeout error classification."""
        timeout_error = TimeoutError("Connection timed out")
        result = runner.classify_error(timeout_error)
        assert result == ConnectionErrorType.CONNECTION_TIMEOUT

    def test_classify_error_connection_refused(self, runner):
        """Test connection refused classification."""
        refused_error = ConnectionRefusedError("Connection refused")
        result = runner.classify_error(refused_error)
        assert result == ConnectionErrorType.CONNECTION_REFUSED

    def test_classify_error_ssl(self, runner):
        """Test SSL error classification."""
        ssl_error = ssl.SSLError(1, "certificate verify failed")
        result = runner.classify_error(ssl_error)
        assert result == ConnectionErrorType.SSL_CERTIFICATE_ERROR

    def test_classify_error_connection_reset(self, runner):
        """Test connection reset classification."""
        reset_error = ConnectionResetError("Connection reset by peer")
        result = runner.classify_error(reset_error)
        assert result == ConnectionErrorType.CONNECTION_RESET

    def test_classify_error_unknown(self, runner):
        """Test unknown error classification."""
        unknown_error = ValueError("Some random error")
        result = runner.classify_error(unknown_error)
        assert result == ConnectionErrorType.UNKNOWN

    def test_get_suggestions_dns(self, runner):
        """Test suggestions for DNS errors."""
        suggestions = runner.get_suggestions(ConnectionErrorType.DNS_RESOLUTION_FAILED)

        assert len(suggestions) > 0
        assert any("DNS" in s or "internet" in s.lower() for s in suggestions)

    def test_get_suggestions_timeout(self, runner):
        """Test suggestions for timeout errors."""
        suggestions = runner.get_suggestions(ConnectionErrorType.CONNECTION_TIMEOUT)

        assert len(suggestions) > 0
        assert any("slow" in s.lower() or "timeout" in s.lower() for s in suggestions)

    def test_get_suggestions_rate_limit(self, runner):
        """Test suggestions for rate limit errors."""
        suggestions = runner.get_suggestions(ConnectionErrorType.RATE_LIMITED)

        assert len(suggestions) > 0
        assert any("rate limit" in s.lower() or "wait" in s.lower() for s in suggestions)

    def test_get_suggestions_auth(self, runner):
        """Test suggestions for authentication errors."""
        suggestions = runner.get_suggestions(ConnectionErrorType.AUTHENTICATION_FAILED)

        assert len(suggestions) > 0
        assert any("api key" in s.lower() for s in suggestions)

    def test_run_full_diagnostics_basic(self, runner):
        """Test running full diagnostics."""
        with patch.object(runner, "check_dns_resolution") as mock_dns:
            mock_dns.return_value = (True, "104.18.7.192", 25.0)

            with patch.object(runner, "check_port_connectivity") as mock_port:
                mock_port.return_value = (True, 100.0)

                with patch.object(runner, "check_ssl_certificate") as mock_ssl:
                    mock_ssl.return_value = (True, datetime(2025, 12, 31), 150.0)

                    diag = runner.run_full_diagnostics()

                    assert diag.dns_resolved is True
                    assert diag.resolved_ip == "104.18.7.192"
                    assert diag.port_open is True
                    assert diag.ssl_valid is True
                    assert diag.total_time_ms is not None

    def test_run_full_diagnostics_with_exception(self, runner):
        """Test diagnostics with an exception."""
        test_exception = TimeoutError("Connection timed out")

        with patch.object(runner, "check_dns_resolution") as mock_dns:
            mock_dns.return_value = (True, "104.18.7.192", 25.0)

            with patch.object(runner, "check_port_connectivity") as mock_port:
                mock_port.return_value = (False, 5000.0)

                diag = runner.run_full_diagnostics(
                    exception=test_exception,
                    endpoint="https://api.anthropic.com",
                    attempt=2,
                    max_attempts=3,
                    retry_delay=4.0,
                )

                assert diag.error_type == ConnectionErrorType.CONNECTION_TIMEOUT
                assert diag.error_message == "Connection timed out"
                assert diag.attempt_number == 2
                assert diag.max_attempts == 3
                assert diag.retry_delay_seconds == 4.0
                assert len(diag.suggestions) > 0


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_diagnostics_runner_singleton(self):
        """Test that get_diagnostics_runner returns singleton."""
        runner1 = get_diagnostics_runner()
        runner2 = get_diagnostics_runner()

        assert runner1 is runner2
        assert isinstance(runner1, ConnectionDiagnosticsRunner)

    def test_diagnose_connection_error(self):
        """Test diagnose_connection_error convenience function."""
        test_error = socket.gaierror(8, "Name not resolved")

        with patch.object(ConnectionDiagnosticsRunner, "run_full_diagnostics") as mock_diag:
            mock_diag.return_value = ConnectionDiagnostics(
                error_type=ConnectionErrorType.DNS_RESOLUTION_FAILED
            )

            result = diagnose_connection_error(
                exception=test_error,
                endpoint="https://api.anthropic.com",
                attempt=1,
                max_attempts=3,
            )

            assert result.error_type == ConnectionErrorType.DNS_RESOLUTION_FAILED

    def test_check_anthropic_connectivity(self):
        """Test check_anthropic_connectivity convenience function."""
        with patch.object(ConnectionDiagnosticsRunner, "run_full_diagnostics") as mock_diag:
            mock_diag.return_value = ConnectionDiagnostics(
                dns_resolved=True,
                port_open=True,
                ssl_valid=True,
            )

            result = check_anthropic_connectivity()

            assert result.dns_resolved is True
            assert result.port_open is True
            assert result.ssl_valid is True


class TestRateLimitClassification:
    """Tests for rate limit error classification."""

    def test_classify_rate_limit_by_name(self):
        """Test rate limit classification by exception name."""
        runner = ConnectionDiagnosticsRunner()

        # Create a mock exception with 'RateLimitError' in its type name
        class RateLimitError(Exception):
            pass

        error = RateLimitError("Rate limit exceeded")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.RATE_LIMITED

    def test_classify_rate_limit_by_message(self):
        """Test rate limit classification by message content."""
        runner = ConnectionDiagnosticsRunner()

        error = Exception("rate limit exceeded")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.RATE_LIMITED


class TestServerErrorClassification:
    """Tests for server error classification."""

    def test_classify_500_error(self):
        """Test 500 server error classification."""
        runner = ConnectionDiagnosticsRunner()

        error = Exception("Server returned 500 Internal Server Error")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.SERVER_ERROR

    def test_classify_503_error(self):
        """Test 503 server error classification."""
        runner = ConnectionDiagnosticsRunner()

        error = Exception("503 Service Unavailable")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.SERVER_ERROR

    def test_classify_502_error(self):
        """Test 502 Bad Gateway classification."""
        runner = ConnectionDiagnosticsRunner()

        error = Exception("502 Bad Gateway")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.SERVER_ERROR

    def test_classify_504_error(self):
        """Test 504 Gateway Timeout classification.

        Note: 504 with 'Timeout' in message matches timeout first,
        so we use a message without 'Timeout' to test server error detection.
        """
        runner = ConnectionDiagnosticsRunner()

        # Use message without 'Timeout' to avoid matching timeout pattern first
        error = Exception("504 Bad Gateway response from upstream")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.SERVER_ERROR


class TestSSLCertificateChecking:
    """Tests for SSL certificate checking."""

    @pytest.fixture
    def runner(self):
        """Create diagnostics runner for testing."""
        return ConnectionDiagnosticsRunner(timeout=5.0)

    def test_check_ssl_success_with_cert(self, runner):
        """Test SSL check with valid certificate."""
        mock_cert = {
            "notAfter": "Dec 31 23:59:59 2025 GMT",
            "subject": ((("commonName", "api.anthropic.com"),),),
        }

        mock_ssock = MagicMock()
        mock_ssock.getpeercert.return_value = mock_cert
        mock_ssock.__enter__ = MagicMock(return_value=mock_ssock)
        mock_ssock.__exit__ = MagicMock(return_value=False)

        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)

        with patch("socket.create_connection", return_value=mock_sock):
            with patch("ssl.create_default_context") as mock_ctx:
                mock_ctx.return_value.wrap_socket.return_value = mock_ssock

                valid, expiry, time_ms = runner.check_ssl_certificate("api.anthropic.com")

        assert valid is True
        assert expiry is not None
        assert expiry.year == 2025
        assert time_ms is not None

    def test_check_ssl_success_no_expiry(self, runner):
        """Test SSL check with certificate missing notAfter."""
        mock_cert = {"subject": ((("commonName", "api.anthropic.com"),),)}

        mock_ssock = MagicMock()
        mock_ssock.getpeercert.return_value = mock_cert
        mock_ssock.__enter__ = MagicMock(return_value=mock_ssock)
        mock_ssock.__exit__ = MagicMock(return_value=False)

        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)

        with patch("socket.create_connection", return_value=mock_sock):
            with patch("ssl.create_default_context") as mock_ctx:
                mock_ctx.return_value.wrap_socket.return_value = mock_ssock

                valid, expiry, time_ms = runner.check_ssl_certificate("api.anthropic.com")

        assert valid is True
        assert expiry is None  # No expiry date in cert

    def test_check_ssl_success_no_cert(self, runner):
        """Test SSL check when getpeercert returns None."""
        mock_ssock = MagicMock()
        mock_ssock.getpeercert.return_value = None
        mock_ssock.__enter__ = MagicMock(return_value=mock_ssock)
        mock_ssock.__exit__ = MagicMock(return_value=False)

        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)

        with patch("socket.create_connection", return_value=mock_sock):
            with patch("ssl.create_default_context") as mock_ctx:
                mock_ctx.return_value.wrap_socket.return_value = mock_ssock

                valid, expiry, time_ms = runner.check_ssl_certificate("api.anthropic.com")

        assert valid is True
        assert expiry is None

    def test_check_ssl_invalid_date_format(self, runner):
        """Test SSL check with invalid date format in certificate."""
        mock_cert = {
            "notAfter": "invalid date format",
            "subject": ((("commonName", "api.anthropic.com"),),),
        }

        mock_ssock = MagicMock()
        mock_ssock.getpeercert.return_value = mock_cert
        mock_ssock.__enter__ = MagicMock(return_value=mock_ssock)
        mock_ssock.__exit__ = MagicMock(return_value=False)

        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)

        with patch("socket.create_connection", return_value=mock_sock):
            with patch("ssl.create_default_context") as mock_ctx:
                mock_ctx.return_value.wrap_socket.return_value = mock_ssock

                valid, expiry, time_ms = runner.check_ssl_certificate("api.anthropic.com")

        assert valid is True
        assert expiry is None  # Falls back to None on parse error

    def test_check_ssl_ssl_error(self, runner):
        """Test SSL check when SSL error occurs."""
        with patch("socket.create_connection") as mock_conn:
            mock_sock = MagicMock()
            mock_sock.__enter__ = MagicMock(return_value=mock_sock)
            mock_sock.__exit__ = MagicMock(return_value=False)
            mock_conn.return_value = mock_sock

            with patch("ssl.create_default_context") as mock_ctx:
                mock_ctx.return_value.wrap_socket.side_effect = ssl.SSLError(
                    1, "certificate verify failed"
                )

                valid, expiry, time_ms = runner.check_ssl_certificate("api.anthropic.com")

        assert valid is False
        assert expiry is None
        assert time_ms is not None

    def test_check_ssl_general_exception(self, runner):
        """Test SSL check when general exception occurs."""
        with patch("socket.create_connection") as mock_conn:
            mock_conn.side_effect = Exception("Network error")

            valid, expiry, time_ms = runner.check_ssl_certificate("api.anthropic.com")

        assert valid is False
        assert expiry is None
        assert time_ms is not None


class TestAdditionalErrorClassification:
    """Additional tests for error classification."""

    def test_classify_getaddrinfo_error(self):
        """Test getaddrinfo error classification."""
        runner = ConnectionDiagnosticsRunner()

        error = Exception("getaddrinfo failed")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.DNS_RESOLUTION_FAILED

    def test_classify_errno_111(self):
        """Test errno 111 (connection refused) classification."""
        runner = ConnectionDiagnosticsRunner()

        error = Exception("[Errno 111] Connection refused")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.CONNECTION_REFUSED

    def test_classify_errno_104(self):
        """Test errno 104 (connection reset) classification."""
        runner = ConnectionDiagnosticsRunner()

        error = Exception("[Errno 104] Connection reset by peer")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.CONNECTION_RESET

    def test_classify_errno_101(self):
        """Test errno 101 (network unreachable) classification."""
        runner = ConnectionDiagnosticsRunner()

        error = Exception("[Errno 101] Network is unreachable")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.NETWORK_UNREACHABLE

    def test_classify_errno_113(self):
        """Test errno 113 (host unreachable) classification."""
        runner = ConnectionDiagnosticsRunner()

        error = Exception("[Errno 113] No route to host")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.HOST_UNREACHABLE

    def test_classify_ssl_handshake_failed(self):
        """Test SSL handshake failure classification."""
        runner = ConnectionDiagnosticsRunner()

        error = Exception("SSL handshake failed")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.SSL_HANDSHAKE_FAILED

    def test_classify_certificate_verify_failed(self):
        """Test certificate verification failure classification."""
        runner = ConnectionDiagnosticsRunner()

        error = Exception("certificate verify failed: invalid certificate")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.SSL_CERTIFICATE_ERROR

    def test_classify_401_unauthorized(self):
        """Test 401 unauthorized classification."""
        runner = ConnectionDiagnosticsRunner()

        error = Exception("401 Unauthorized")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.AUTHENTICATION_FAILED

    def test_classify_authentication_error(self):
        """Test authentication error classification."""
        runner = ConnectionDiagnosticsRunner()

        error = Exception("Authentication failed: invalid API key")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.AUTHENTICATION_FAILED

    def test_classify_proxy_error(self):
        """Test proxy error classification."""
        runner = ConnectionDiagnosticsRunner()

        error = Exception("Proxy connection failed")
        result = runner.classify_error(error)

        assert result == ConnectionErrorType.PROXY_ERROR


class TestAllSuggestionTypes:
    """Tests to ensure all error types have suggestions."""

    def test_all_error_types_have_suggestions(self):
        """Verify all error types return suggestions."""
        runner = ConnectionDiagnosticsRunner()

        for error_type in ConnectionErrorType:
            suggestions = runner.get_suggestions(error_type)
            assert isinstance(suggestions, list)
            assert len(suggestions) > 0, f"No suggestions for {error_type}"

    def test_ssl_handshake_suggestions(self):
        """Test SSL handshake suggestions."""
        runner = ConnectionDiagnosticsRunner()
        suggestions = runner.get_suggestions(ConnectionErrorType.SSL_HANDSHAKE_FAILED)

        assert len(suggestions) > 0
        assert any("TLS" in s or "SSL" in s for s in suggestions)

    def test_connection_refused_suggestions(self):
        """Test connection refused suggestions."""
        runner = ConnectionDiagnosticsRunner()
        suggestions = runner.get_suggestions(ConnectionErrorType.CONNECTION_REFUSED)

        assert len(suggestions) > 0
        assert any("firewall" in s.lower() for s in suggestions)

    def test_network_unreachable_suggestions(self):
        """Test network unreachable suggestions."""
        runner = ConnectionDiagnosticsRunner()
        suggestions = runner.get_suggestions(ConnectionErrorType.NETWORK_UNREACHABLE)

        assert len(suggestions) > 0
        assert any("internet" in s.lower() or "network" in s.lower() for s in suggestions)

    def test_host_unreachable_suggestions(self):
        """Test host unreachable suggestions."""
        runner = ConnectionDiagnosticsRunner()
        suggestions = runner.get_suggestions(ConnectionErrorType.HOST_UNREACHABLE)

        assert len(suggestions) > 0

    def test_connection_reset_suggestions(self):
        """Test connection reset suggestions."""
        runner = ConnectionDiagnosticsRunner()
        suggestions = runner.get_suggestions(ConnectionErrorType.CONNECTION_RESET)

        assert len(suggestions) > 0

    def test_server_error_suggestions(self):
        """Test server error suggestions."""
        runner = ConnectionDiagnosticsRunner()
        suggestions = runner.get_suggestions(ConnectionErrorType.SERVER_ERROR)

        assert len(suggestions) > 0
        assert any("retry" in s.lower() or "status" in s.lower() for s in suggestions)

    def test_proxy_error_suggestions(self):
        """Test proxy error suggestions."""
        runner = ConnectionDiagnosticsRunner()
        suggestions = runner.get_suggestions(ConnectionErrorType.PROXY_ERROR)

        assert len(suggestions) > 0
        assert any("proxy" in s.lower() for s in suggestions)

    def test_unknown_error_suggestions(self):
        """Test unknown error suggestions."""
        runner = ConnectionDiagnosticsRunner()
        suggestions = runner.get_suggestions(ConnectionErrorType.UNKNOWN)

        assert len(suggestions) > 0


class TestDiagnosticsWithDNSFailure:
    """Tests for full diagnostics when DNS fails."""

    def test_diagnostics_stops_at_dns_failure(self):
        """Test that port and SSL checks are skipped when DNS fails."""
        runner = ConnectionDiagnosticsRunner()

        with patch.object(runner, "check_dns_resolution") as mock_dns:
            mock_dns.return_value = (False, None, 100.0)

            with patch.object(runner, "check_port_connectivity") as mock_port:
                with patch.object(runner, "check_ssl_certificate") as mock_ssl:
                    diag = runner.run_full_diagnostics()

                    # DNS was called
                    mock_dns.assert_called_once()
                    # Port check should not be called when DNS fails
                    mock_port.assert_not_called()
                    # SSL check should not be called when DNS fails
                    mock_ssl.assert_not_called()

        assert diag.dns_resolved is False
        assert diag.port_open is False
        assert diag.ssl_valid is False

    def test_diagnostics_stops_at_port_failure(self):
        """Test that SSL check is skipped when port check fails."""
        runner = ConnectionDiagnosticsRunner()

        with patch.object(runner, "check_dns_resolution") as mock_dns:
            mock_dns.return_value = (True, "104.18.7.192", 25.0)

            with patch.object(runner, "check_port_connectivity") as mock_port:
                mock_port.return_value = (False, 5000.0)

                with patch.object(runner, "check_ssl_certificate") as mock_ssl:
                    diag = runner.run_full_diagnostics()

                    # DNS was called
                    mock_dns.assert_called_once()
                    # Port check was called
                    mock_port.assert_called_once()
                    # SSL check should not be called when port fails
                    mock_ssl.assert_not_called()

        assert diag.dns_resolved is True
        assert diag.port_open is False
        assert diag.ssl_valid is False


class TestDiagnosticsReportFormatting:
    """Tests for diagnostic report formatting edge cases."""

    def test_report_with_all_fields(self):
        """Test report generation with all fields populated."""
        diag = ConnectionDiagnostics(
            endpoint="https://api.anthropic.com",
            error_type=ConnectionErrorType.CONNECTION_TIMEOUT,
            error_message="Connection timed out after 30s",
            error_code=110,
            dns_resolved=True,
            resolved_ip="104.18.7.192",
            port_open=True,
            ssl_valid=True,
            ssl_expiry=datetime(2025, 12, 31, 23, 59, 59),
            dns_resolution_time_ms=25.5,
            connection_time_ms=100.3,
            ssl_handshake_time_ms=150.7,
            total_time_ms=276.5,
            attempt_number=2,
            max_attempts=3,
            retry_delay_seconds=4.0,
            raw_exception="TimeoutError: Connection timed out",
            suggestions=["Check network", "Increase timeout"],
        )

        report = diag.to_report()

        assert "CONNECTION DIAGNOSTIC REPORT" in report
        assert "https://api.anthropic.com" in report
        assert "CONNECTION TIMEOUT" in report
        assert "104.18.7.192" in report
        assert "DNS Resolution: ✓ Success" in report
        assert "Port Accessible: ✓ Yes" in report
        assert "SSL/TLS Valid: ✓ Yes" in report
        assert "SSL Expiry: 2025-12-31" in report
        assert "25.5ms" in report
        assert "100.3ms" in report
        assert "150.7ms" in report
        assert "276.5ms" in report
        assert "Attempt: 2 of 3" in report
        assert "Retry Delay: 4.0s" in report
        assert "Check network" in report
        assert "Increase timeout" in report
        assert "TimeoutError" in report

    def test_report_truncates_long_exception(self):
        """Test that long exception messages are truncated in report."""
        long_exception = "x" * 1000
        diag = ConnectionDiagnostics(raw_exception=long_exception)

        report = diag.to_report()

        # Should only include first 500 chars
        assert "x" * 500 in report
        assert "x" * 501 not in report

    def test_to_dict_with_ssl_expiry(self):
        """Test to_dict includes SSL expiry date."""
        expiry = datetime(2025, 12, 31, 23, 59, 59)
        diag = ConnectionDiagnostics(ssl_expiry=expiry)

        result = diag.to_dict()

        assert result["network"]["ssl_expiry"] == "2025-12-31T23:59:59"

    def test_to_dict_without_ssl_expiry(self):
        """Test to_dict handles None SSL expiry."""
        diag = ConnectionDiagnostics(ssl_expiry=None)

        result = diag.to_dict()

        assert result["network"]["ssl_expiry"] is None
