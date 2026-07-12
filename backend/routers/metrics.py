"""
Metrics Router

Exposes application metrics for monitoring and observability.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict

from backend.models import User
from backend.middleware.auth_dependency import get_current_user
from backend.utils.metrics import get_metrics
from backend.utils.cache import get_cache


router = APIRouter(prefix="/metrics", tags=["metrics"])


class MetricsSummary(BaseModel):
    """Overall application metrics"""

    uptime_seconds: int
    total_requests: int
    total_errors: int
    error_rate: float
    endpoints_tracked: int


class EndpointMetrics(BaseModel):
    """Metrics for a specific endpoint"""

    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    p95_duration_ms: float


class CacheMetrics(BaseModel):
    """Cache performance metrics"""

    size: int
    max_size: int
    hits: int
    misses: int
    hit_rate: float


class FullMetricsResponse(BaseModel):
    """Complete metrics response"""

    summary: MetricsSummary
    endpoints: Dict[str, EndpointMetrics]
    cache: CacheMetrics
    errors: Dict[str, int]


@router.get("/summary", response_model=MetricsSummary)
async def get_metrics_summary(
    current_user: User = Depends(get_current_user),
):
    """
    Get high-level application metrics summary.

    Returns overall stats like uptime, total requests, error rate.
    """
    metrics = get_metrics()
    summary = metrics.get_summary()
    return MetricsSummary(**summary)


@router.get("/endpoints")
async def get_endpoint_metrics(
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed metrics for all API endpoints.

    Returns request counts, success rates, and response times per endpoint.
    """
    metrics = get_metrics()
    return metrics.get_endpoint_stats()


@router.get("", response_model=FullMetricsResponse)
async def get_all_metrics(
    current_user: User = Depends(get_current_user),
):
    """
    Get complete metrics including summary, endpoints, cache, and errors.

    Provides full observability into application performance.
    """
    metrics = get_metrics()
    cache = get_cache()

    return FullMetricsResponse(
        summary=MetricsSummary(**metrics.get_summary()),
        endpoints=metrics.get_endpoint_stats(),
        cache=CacheMetrics(**cache.get_stats()),
        errors=metrics.get_error_summary(),
    )


@router.get("/prometheus", dependencies=[Depends(get_current_user)])
async def get_prometheus_metrics():
    """
    Get metrics in Prometheus exposition format.

    Can be scraped by Prometheus for monitoring and alerting.
    """
    metrics = get_metrics()
    cache = get_cache()

    summary = metrics.get_summary()
    endpoint_stats = metrics.get_endpoint_stats()
    cache_stats = cache.get_stats()

    # Build Prometheus format output
    lines = [
        "# HELP app_uptime_seconds Application uptime in seconds",
        "# TYPE app_uptime_seconds gauge",
        f"app_uptime_seconds {summary['uptime_seconds']}",
        "",
        "# HELP app_requests_total Total number of HTTP requests",
        "# TYPE app_requests_total counter",
        f"app_requests_total {summary['total_requests']}",
        "",
        "# HELP app_errors_total Total number of HTTP errors",
        "# TYPE app_errors_total counter",
        f"app_errors_total {summary['total_errors']}",
        "",
        "# HELP app_error_rate Error rate percentage",
        "# TYPE app_error_rate gauge",
        f"app_error_rate {summary['error_rate']}",
        "",
        "# HELP cache_size Number of entries in cache",
        "# TYPE cache_size gauge",
        f"cache_size {cache_stats['size']}",
        "",
        "# HELP cache_hits_total Total cache hits",
        "# TYPE cache_hits_total counter",
        f"cache_hits_total {cache_stats['hits']}",
        "",
        "# HELP cache_misses_total Total cache misses",
        "# TYPE cache_misses_total counter",
        f"cache_misses_total {cache_stats['misses']}",
        "",
        "# HELP cache_hit_rate Cache hit rate percentage",
        "# TYPE cache_hit_rate gauge",
        f"cache_hit_rate {cache_stats['hit_rate']}",
        "",
    ]

    # Add endpoint-specific metrics
    for endpoint, stats in endpoint_stats.items():
        lines.extend(
            [
                f'http_requests_total{{endpoint="{endpoint}"}} {stats["total_requests"]}',
                f'http_request_duration_ms_avg{{endpoint="{endpoint}"}} {stats["avg_duration_ms"]}',
                f'http_request_duration_ms_p95{{endpoint="{endpoint}"}} {stats["p95_duration_ms"]}',
            ]
        )

    return "\n".join(lines)
