"""Unit tests for backend.utils.metrics."""

import pytest
from backend.utils.metrics import EndpointStats, MetricsCollector, get_metrics


class TestEndpointStats:
    def test_add_successful_request(self):
        stats = EndpointStats()
        stats.add_request(50.0, 200)
        assert stats.total_requests == 1
        assert stats.successful_requests == 1
        assert stats.failed_requests == 0

    def test_add_failed_request(self):
        stats = EndpointStats()
        stats.add_request(100.0, 500)
        assert stats.failed_requests == 1
        assert stats.successful_requests == 0

    def test_avg_duration(self):
        stats = EndpointStats()
        stats.add_request(100.0, 200)
        stats.add_request(200.0, 200)
        assert stats.avg_duration_ms == pytest.approx(150.0)

    def test_avg_duration_empty_is_zero(self):
        assert EndpointStats().avg_duration_ms == 0.0

    def test_min_max_duration(self):
        stats = EndpointStats()
        stats.add_request(10.0, 200)
        stats.add_request(500.0, 200)
        assert stats.min_duration_ms == 10.0
        assert stats.max_duration_ms == 500.0

    def test_success_rate(self):
        stats = EndpointStats()
        stats.add_request(50.0, 200)
        stats.add_request(50.0, 200)
        stats.add_request(50.0, 500)
        assert stats.success_rate == pytest.approx(66.67, abs=0.1)

    def test_success_rate_empty_is_zero(self):
        assert EndpointStats().success_rate == 0.0

    def test_p95_single_duration(self):
        stats = EndpointStats()
        stats.add_request(42.0, 200)
        assert stats.p95_duration_ms == 42.0

    def test_p95_empty_is_zero(self):
        assert EndpointStats().p95_duration_ms == 0.0

    def test_recent_durations_capped_at_100(self):
        stats = EndpointStats()
        for i in range(150):
            stats.add_request(float(i), 200)
        assert len(stats.recent_durations) == 100


class TestMetricsCollector:
    @pytest.fixture
    def collector(self):
        c = MetricsCollector()
        return c

    def test_record_single_request(self, collector):
        collector.record_request("/api/clients", "GET", 200, 50.0)
        stats = collector.get_endpoint_stats()
        assert "GET /api/clients" in stats
        assert stats["GET /api/clients"]["total_requests"] == 1

    def test_accumulates_multiple_requests(self, collector):
        for _ in range(5):
            collector.record_request("/api/posts", "GET", 200, 30.0)
        stats = collector.get_endpoint_stats()
        assert stats["GET /api/posts"]["total_requests"] == 5

    def test_tracks_errors(self, collector):
        collector.record_request("/api/clients", "GET", 404, 10.0)
        errors = collector.get_error_summary()
        assert len(errors) > 0

    def test_no_errors_when_all_success(self, collector):
        collector.record_request("/api/clients", "GET", 200, 50.0)
        errors = collector.get_error_summary()
        assert len(errors) == 0

    def test_get_summary_fields(self, collector):
        collector.record_request("/api/x", "GET", 200, 50.0)
        summary = collector.get_summary()
        assert "total_requests" in summary
        assert "total_errors" in summary
        assert "error_rate" in summary
        assert "uptime_seconds" in summary
        assert "endpoints_tracked" in summary

    def test_summary_total_requests(self, collector):
        collector.record_request("/a", "GET", 200, 10.0)
        collector.record_request("/b", "POST", 201, 20.0)
        summary = collector.get_summary()
        assert summary["total_requests"] == 2

    def test_reset_clears_all(self, collector):
        collector.record_request("/api/x", "GET", 200, 50.0)
        collector.reset()
        assert collector.get_endpoint_stats() == {}
        assert collector.get_error_summary() == {}


class TestGetMetrics:
    def test_returns_singleton(self):
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2

    def test_returns_collector_instance(self):
        assert isinstance(get_metrics(), MetricsCollector)
