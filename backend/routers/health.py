"""
Health and monitoring endpoints.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from backend.config import settings
from backend.utils.db_monitor import get_pool_events, get_pool_status
from backend.utils.query_cache import clear_cache, get_cache_info, reset_cache_stats
from backend.utils.query_profiler import (
    get_profiling_report,
    get_query_statistics,
    get_slow_queries,
    reset_statistics,
)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check() -> Dict[str, Any]:
    """Basic API health response used by the dashboard."""

    return {
        "status": "healthy",
        "service": "Content Jumpstart API",
        "version": settings.API_VERSION,
    }


@router.get("/database")
async def database_health() -> Dict[str, Any]:
    """Return database connection pool details."""

    return get_pool_status()


@router.get("/database/events")
async def database_events() -> Dict[str, Any]:
    """Return database pool event counters."""

    return get_pool_events()


def _cache_recommendations(stats: Dict[str, Any]) -> List[Dict[str, str]]:
    recommendations: List[Dict[str, str]] = []
    hit_rate = float(stats.get("hit_rate_percent", 0.0) or 0.0)
    size = int(stats.get("size", 0) or 0)
    maxsize = int(stats.get("maxsize", 0) or 0)

    if hit_rate < 40:
        recommendations.append(
            {
                "severity": "warning",
                "message": "Cache hit rate is low. Consider increasing cache TTL or reviewing cache keys.",
            }
        )
    elif hit_rate > 80:
        recommendations.append(
            {
                "severity": "info",
                "message": "Cache hit rate is healthy.",
            }
        )

    if maxsize and size >= maxsize:
        recommendations.append(
            {
                "severity": "warning",
                "message": "Cache is at capacity. Consider increasing max size for this tier.",
            }
        )

    if not recommendations:
        recommendations.append({"severity": "info", "message": "Cache tier is healthy."})

    return recommendations


@router.get("/cache")
async def cache_health(tier: Optional[str] = None) -> Dict[str, Any]:
    """Return cache statistics for one tier or all tiers."""

    if tier:
        stats = get_cache_info(tier)
        if "error" in stats:
            return {"error": stats["error"]}
        stats["recommendations"] = _cache_recommendations(stats)
        return stats

    all_stats = get_cache_info()
    return {
        tier_name: {
            **tier_stats,
            "recommendations": _cache_recommendations(tier_stats),
        }
        for tier_name, tier_stats in all_stats.items()
    }


@router.post("/cache/clear")
async def clear_cache_health(
    tier: Optional[str] = Query(default=None),
    key_prefix: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Clear cache entries and return before/after statistics."""

    before = get_cache_info(tier) if tier else get_cache_info()
    clear_cache(tier, key_prefix)
    after = get_cache_info(tier) if tier else get_cache_info()
    return {
        "success": True,
        "message": "Cache cleared successfully",
        "before": before,
        "after": after,
    }


@router.post("/cache/reset-stats")
async def reset_cache_health() -> Dict[str, Any]:
    """Reset cache statistics counters."""

    reset_cache_stats()
    return {"success": True, "stats": get_cache_info()}


@router.get("/full")
async def full_health() -> Dict[str, Any]:
    """Aggregate API, database, cache, and profiling health."""

    database = get_pool_status()
    profiling = get_profiling_report()
    cache = get_cache_info()
    api_health = await health_check()

    status = (
        "healthy"
        if api_health.get("status", "healthy") == "healthy"
        and database.get("health_status", "healthy") in {"healthy", "configured"}
        and profiling.get("summary", {}).get("slow_percentage", 0) <= 10
        else "degraded"
    )
    return {
        "status": status,
        "service": "Content Jumpstart API",
        "components": {
            "api": api_health,
            "database": database,
            "cache": cache,
            "profiling": profiling,
        },
    }


@router.get("/profiling")
async def profiling_overview() -> Dict[str, Any]:
    """Return a profiling summary for the health dashboard."""

    report = get_profiling_report()
    report["thresholds"] = {
        "slow_query_ms": 100,
        "very_slow_query_ms": 500,
    }
    return report


@router.get("/profiling/queries")
async def profiling_queries(
    min_execution_count: int = Query(default=0, ge=0),
    min_avg_time_ms: float = Query(default=0, ge=0),
    only_slow: bool = Query(default=False),
) -> Dict[str, Any]:
    """Return aggregated query statistics."""

    stats = get_query_statistics(
        min_execution_count=min_execution_count,
        min_avg_time_ms=min_avg_time_ms,
        only_slow=only_slow,
    )
    return {
        "count": len(stats),
        "limit": len(stats),
        "filters": {
            "min_execution_count": min_execution_count,
            "min_avg_time_ms": min_avg_time_ms,
            "only_slow": only_slow,
        },
        "queries": [
            {
                "query_hash": item.query_hash,
                "query_sample": item.query_sample,
                "execution_count": item.execution_count,
                "total_time_ms": item.total_time_ms,
                "avg_time_ms": item.avg_time_ms,
                "min_time_ms": item.min_time_ms,
                "max_time_ms": item.max_time_ms,
                "slow_count": item.slow_count,
                "very_slow_count": item.very_slow_count,
            }
            for item in stats
        ],
    }


@router.get("/profiling/slow-queries")
async def profiling_slow_queries(
    since_minutes: int = Query(default=60, ge=1),
    very_slow_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1),
) -> Dict[str, Any]:
    """Return the recent slow query buffer."""

    since = datetime.utcnow() - timedelta(minutes=since_minutes)
    queries = get_slow_queries(limit=limit, since=since, very_slow_only=very_slow_only)
    return {
        "count": len(queries),
        "limit": limit,
        "since_minutes": since_minutes,
        "very_slow_only": very_slow_only,
        "thresholds": {
            "slow_query_ms": 100,
            "very_slow_query_ms": 500,
        },
        "queries": queries,
    }


@router.post("/profiling/reset")
async def profiling_reset() -> Dict[str, Any]:
    """Reset profiling statistics."""

    reset_statistics()
    return {"success": True, "message": "Profiling statistics reset successfully"}


sys.modules.setdefault("routers.health", sys.modules[__name__])
sys.modules.setdefault("backend.routers.health", sys.modules[__name__])
