"""
Unit tests for backend metrics collection and logger setup.
"""

import logging

from backend.utils.logger import setup_logger
from backend.utils.metrics import MetricsCollector, get_metrics


class TestMetricsCollector:
    def test_record_and_summarize_requests(self):
        collector = MetricsCollector()

        collector.record_request("/api/clients", "GET", 200, 10.2)
        collector.record_request("/api/clients", "GET", 500, 20.8)
        collector.record_request("/api/posts", "POST", 201, 5.0)

        endpoint_stats = collector.get_endpoint_stats()
        assert endpoint_stats["GET /api/clients"]["total_requests"] == 2
        assert endpoint_stats["GET /api/clients"]["successful_requests"] == 1
        assert endpoint_stats["GET /api/clients"]["failed_requests"] == 1
        assert endpoint_stats["GET /api/clients"]["min_duration_ms"] == 10.2
        assert endpoint_stats["GET /api/clients"]["max_duration_ms"] == 20.8
        assert endpoint_stats["GET /api/clients"]["success_rate"] == 50.0

        summary = collector.get_summary()
        assert summary["total_requests"] == 3
        assert summary["total_errors"] == 1
        assert summary["endpoints_tracked"] == 2

        errors = collector.get_error_summary()
        assert errors["500_/api/clients"] == 1

    def test_global_metrics_singleton(self):
        first = get_metrics()
        second = get_metrics()

        assert first is second

    def test_reset_clears_state(self):
        collector = MetricsCollector()
        collector.record_request("/api/posts", "POST", 200, 1.0)
        collector.reset()

        assert collector.get_endpoint_stats() == {}
        assert collector.get_error_summary() == {}


class TestLoggerSetup:
    def test_setup_logger_writes_to_file(self, tmp_path):
        log_file = tmp_path / "backend.log"
        logger = setup_logger(name="test.backend", level=logging.INFO, log_file=log_file)

        logger.info("hello world")
        assert log_file.exists()
        contents = log_file.read_text(encoding="utf-8")
        assert "hello world" in contents

    def test_setup_logger_clears_existing_handlers(self, tmp_path):
        log_file = tmp_path / "test.log"
        logger = setup_logger(name="test.clear", level=logging.INFO, log_file=log_file)
        handler_count = len(logger.handlers)

        logger = setup_logger(name="test.clear", level=logging.INFO, log_file=log_file)

        assert len(logger.handlers) == handler_count
