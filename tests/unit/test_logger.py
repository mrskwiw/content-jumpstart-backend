"""Unit tests for logger module.

Tests cover:
- setup_logger with and without file logging
- log_client_start and log_client_complete
- log_template_selection, log_post_generated, log_api_call
- log_error and log_warning
- Module-level logger instance properties
- No duplicate handlers when setup_logger is called twice for the same name
"""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.logger import (
    setup_logger,
    log_client_start,
    log_client_complete,
    log_template_selection,
    log_post_generated,
    log_api_call,
    log_error,
    log_warning,
    console,
)


class TestSetupLogger:
    """Tests for setup_logger function."""

    def test_setup_logger_default(self):
        """Test setting up logger with defaults."""
        logger = setup_logger(name="test_default")

        assert logger.name == "test_default"
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1  # Just console handler

    def test_setup_logger_custom_level(self):
        """Test setting up logger with custom level."""
        logger = setup_logger(name="test_level", level=logging.DEBUG)

        assert logger.level == logging.DEBUG

    def test_setup_logger_with_file(self, tmp_path):
        """Test setting up logger with file logging."""
        log_file = tmp_path / "logs" / "test.log"

        logger = setup_logger(name="test_file", log_file=log_file)

        assert len(logger.handlers) == 2  # Console + file
        assert log_file.parent.exists()

        # Log something and verify file was written
        logger.info("Test message")

        # Need to flush handlers
        for handler in logger.handlers:
            handler.flush()

        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

    def test_setup_logger_creates_parent_directories(self, tmp_path):
        """Test that setup_logger creates parent directories for log file."""
        log_file = tmp_path / "deep" / "nested" / "dir" / "test.log"

        setup_logger(name="test_nested", log_file=log_file)

        assert log_file.parent.exists()

    def test_setup_logger_clears_existing_handlers(self):
        """Test that setup_logger clears existing handlers."""
        logger = setup_logger(name="test_clear")
        initial_handlers = len(logger.handlers)

        # Setup again
        logger = setup_logger(name="test_clear")

        # Should still have same number of handlers (not doubled)
        assert len(logger.handlers) == initial_handlers

    def test_setup_logger_no_duplicate_handlers_on_second_call(self):
        """Calling setup_logger twice for the same name must not add duplicate handlers.

        This guards against the common bug where a module is imported multiple
        times and each import appends a new handler to the root/named logger.
        """
        logger_first = setup_logger(name="test_no_dup")
        count_after_first = len(logger_first.handlers)

        logger_second = setup_logger(name="test_no_dup")
        count_after_second = len(logger_second.handlers)

        # Both references point to the same logger object
        assert logger_first is logger_second
        # Handler count must not grow
        assert count_after_second == count_after_first

    def test_setup_logger_no_file_handler_without_log_file(self):
        """Logger created without log_file must have exactly one handler and it must not be a FileHandler."""
        logger = setup_logger(name="test_no_file_handler")

        assert len(logger.handlers) == 1
        for handler in logger.handlers:
            assert not isinstance(
                handler, logging.FileHandler
            ), "A FileHandler was unexpectedly added when log_file was not specified"

    def test_setup_logger_file_handler_writes_to_correct_path(self, tmp_path):
        """FileHandler must write to the exact path supplied to setup_logger."""
        log_file = tmp_path / "specific.log"
        logger = setup_logger(name="test_correct_path", log_file=log_file)

        # Identify file handlers
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1

        actual_path = Path(file_handlers[0].baseFilename).resolve()
        expected_path = log_file.resolve()
        assert actual_path == expected_path

    def test_setup_logger_returns_logger_instance(self):
        """setup_logger must return a logging.Logger instance."""
        result = setup_logger(name="test_return_type")
        assert isinstance(result, logging.Logger)

    def test_setup_logger_level_propagates_to_handler(self):
        """The console handler level must match the level passed to setup_logger."""
        logger = setup_logger(name="test_handler_level", level=logging.WARNING)

        for handler in logger.handlers:
            assert handler.level == logging.WARNING

    def test_setup_logger_deep_nested_directory_created(self, tmp_path):
        """setup_logger must create arbitrarily deep directory trees for the log file."""
        log_file = tmp_path / "a" / "b" / "c" / "d" / "e" / "nested.log"
        setup_logger(name="test_deep_dir", log_file=log_file)
        assert log_file.parent.exists()


class TestLogClientFunctions:
    """Tests for client logging functions."""

    def test_log_client_start(self):
        """Test log_client_start function."""
        with patch.object(console, "print") as mock_print:
            log_client_start("TestClient")

            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "TestClient" in call_args
            assert "Starting Content Generation" in call_args

    def test_log_client_complete(self):
        """Test log_client_complete function."""
        with patch.object(console, "print") as mock_print:
            log_client_complete("TestClient", 30, 45.5)

            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "TestClient" in call_args
            assert "30" in call_args
            assert "45.5" in call_args
            assert "Completed" in call_args

    def test_log_client_start_does_not_raise(self):
        """log_client_start must not raise on a normal client name."""
        # No assertion on output — just confirm no exception
        log_client_start("AnyClient")

    def test_log_client_complete_does_not_raise(self):
        """log_client_complete must not raise with valid inputs."""
        log_client_complete("AnyClient", 15, 120.0)


class TestLogFunctions:
    """Tests for various log functions."""

    def test_log_template_selection(self):
        """Test log_template_selection function."""
        # Setup a test logger
        test_logger = setup_logger(name="test_template")

        with patch.object(test_logger, "info") as mock_info:
            # Need to patch the module's logger
            import src.utils.logger as logger_module

            original_logger = logger_module.logger
            logger_module.logger = test_logger

            try:
                log_template_selection(15, 20)
                mock_info.assert_called_once()
                call_args = mock_info.call_args[0][0]
                assert "15" in call_args
                assert "20" in call_args
            finally:
                logger_module.logger = original_logger

    def test_log_post_generated(self):
        """Test log_post_generated function."""
        test_logger = setup_logger(name="test_post", level=logging.DEBUG)

        with patch.object(test_logger, "debug") as mock_debug:
            import src.utils.logger as logger_module

            original_logger = logger_module.logger
            logger_module.logger = test_logger

            try:
                log_post_generated(1, "Problem Recognition", 200)
                mock_debug.assert_called_once()
                call_args = mock_debug.call_args[0][0]
                assert "1" in call_args
                assert "Problem Recognition" in call_args
                assert "200" in call_args
            finally:
                logger_module.logger = original_logger

    def test_log_post_generated_does_not_raise_on_valid_inputs(self):
        """log_post_generated must not raise on valid integer/string inputs."""
        # Patch the module-level logger so we don't emit real log output during tests
        import src.utils.logger as logger_module

        test_logger = setup_logger(name="test_post_valid", level=logging.DEBUG)
        original_logger = logger_module.logger
        logger_module.logger = test_logger
        try:
            log_post_generated(post_number=30, template_name="Listicle", word_count=175)
        finally:
            logger_module.logger = original_logger

    def test_log_post_generated_logs_at_debug_level(self):
        """log_post_generated must call logger.debug (not info/warning/error)."""
        import src.utils.logger as logger_module

        test_logger = setup_logger(name="test_post_level", level=logging.DEBUG)

        with (
            patch.object(test_logger, "debug") as mock_debug,
            patch.object(test_logger, "info") as mock_info,
        ):
            original_logger = logger_module.logger
            logger_module.logger = test_logger
            try:
                log_post_generated(5, "How-To", 250)
                mock_debug.assert_called_once()
                mock_info.assert_not_called()
            finally:
                logger_module.logger = original_logger

    def test_log_api_call(self):
        """Test log_api_call function."""
        test_logger = setup_logger(name="test_api", level=logging.DEBUG)

        with patch.object(test_logger, "debug") as mock_debug:
            import src.utils.logger as logger_module

            original_logger = logger_module.logger
            logger_module.logger = test_logger

            try:
                log_api_call("claude-3-sonnet", 5000)
                mock_debug.assert_called_once()
                call_args = mock_debug.call_args[0][0]
                assert "claude-3-sonnet" in call_args
                assert "5000" in call_args
            finally:
                logger_module.logger = original_logger

    def test_log_error(self):
        """Test log_error function."""
        test_logger = setup_logger(name="test_error")

        with patch.object(test_logger, "error") as mock_error:
            import src.utils.logger as logger_module

            original_logger = logger_module.logger
            logger_module.logger = test_logger

            try:
                log_error("Something went wrong")
                mock_error.assert_called_once_with("Something went wrong", exc_info=False)
            finally:
                logger_module.logger = original_logger

    def test_log_error_with_exc_info(self):
        """Test log_error with exception info."""
        test_logger = setup_logger(name="test_error_exc")

        with patch.object(test_logger, "error") as mock_error:
            import src.utils.logger as logger_module

            original_logger = logger_module.logger
            logger_module.logger = test_logger

            try:
                log_error("Error with trace", exc_info=True)
                mock_error.assert_called_once_with("Error with trace", exc_info=True)
            finally:
                logger_module.logger = original_logger

    def test_log_warning(self):
        """Test log_warning function."""
        test_logger = setup_logger(name="test_warning")

        with patch.object(test_logger, "warning") as mock_warning:
            import src.utils.logger as logger_module

            original_logger = logger_module.logger
            logger_module.logger = test_logger

            try:
                log_warning("This is a warning")
                mock_warning.assert_called_once_with("This is a warning")
            finally:
                logger_module.logger = original_logger


class TestConsoleConfiguration:
    """Tests for console configuration."""

    def test_console_exists(self):
        """Test that console is configured."""
        assert console is not None

    def test_console_has_theme(self):
        """Test that console has custom theme."""
        from src.utils.logger import custom_theme

        assert custom_theme is not None


class TestLoggerInstance:
    """Tests for default logger instance."""

    def test_default_logger_exists(self):
        """Test that default logger exists."""
        from src.utils.logger import logger

        assert logger is not None
        assert logger.name == "content_jumpstart"

    def test_default_logger_is_logging_logger(self):
        """Module-level logger must be a stdlib logging.Logger instance."""
        from src.utils.logger import logger

        assert isinstance(logger, logging.Logger)

    def test_default_logger_has_no_file_handler_by_default(self):
        """The default module-level logger must not have a FileHandler attached.

        setup_logger() is called without a log_file argument at module import
        time, so only a RichHandler (console) should be present.
        """
        from src.utils.logger import logger

        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 0, (
            "The default module-level logger must not have a FileHandler "
            "when no log_file was specified. "
            f"Found: {file_handlers}"
        )
