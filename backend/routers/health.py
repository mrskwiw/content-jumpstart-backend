"""
Health and monitoring endpoints.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query

from backend.middleware.auth_dependency import get_current_user
from backend.models.user import User
from backend.utils.db_monitor import get_pool_status, get_pool_events
from backend.utils.logger import logger
from backend.utils.query_cache import get_cache_info, clear_cache, reset_cache_stats
from backend.utils.query_profiler import (
    get_query_statistics,
    get_slow_queries,
    get_profiling_report,
    reset_statistics,
    SLOW_QUERY_THRESHOLD_MS,
    VERY_SLOW_QUERY_THRESHOLD_MS,
)

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to verify user is an admin (superuser).

    Health management operations (cache clear, stats reset) require admin privileges
    to prevent performance degradation attacks.

    Raises:
        HTTPException 403: User is not an admin

    Returns:
        User instance if admin
    """
    from fastapi import HTTPException, status

    if not current_user.is_superuser:
        logger.warning(
            f"Admin access denied: User {current_user.email} "
            f"attempted health management operation without superuser privileges"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for health management operations",
        )
    return current_user


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Returns:
        Health status dictionary
    """
    return {
        "status": "healthy",
        "service": "Content Jumpstart API",
        "version": "1.0.0",
    }


@router.get("/health/database")
async def database_health():
    """
    Database connection pool health check.

    Returns detailed information about:
    - Connection pool status
    - Pool utilization
    - Health recommendations
    - Configuration settings

    Use this endpoint to:
    - Monitor pool usage
    - Tune pool settings
    - Diagnose connection issues
    - Track performance over time
    """
    pool_status = get_pool_status()
    return pool_status


@router.get("/health/database/events")
async def database_events():
    """
    Database pool event counters.

    Returns:
        Pool event statistics (if available)
    """
    events = get_pool_events()
    return events


@router.get("/health/cache")
async def cache_health(tier: str = Query(None, description="Cache tier (short, medium, long)")):
    """
    Query cache statistics and health.

    Returns detailed information about:
    - Cache size and capacity
    - Hit/miss rates
    - Cache effectiveness
    - TTL settings

    Query Parameters:
        tier: Optional cache tier to view (short, medium, long)
              If not specified, returns stats for all tiers

    Use this endpoint to:
    - Monitor cache performance
    - Tune cache sizes
    - Diagnose caching issues
    - Track cache hit rates
    """
    cache_info = get_cache_info(tier)

    # Add recommendations based on hit rates
    if tier:
        hit_rate = cache_info.get("hit_rate_percent", 0)
        recommendations = []

        if hit_rate < 50:
            recommendations.append("Low hit rate - consider increasing TTL or cache size")
        elif hit_rate < 70:
            recommendations.append("Moderate hit rate - cache is working but could be optimized")
        else:
            recommendations.append("Good hit rate - cache is effective")

        cache_info["recommendations"] = recommendations

    return cache_info


@router.post("/health/cache/clear")
async def clear_query_cache(
    tier: str = Query(None, description="Cache tier to clear (short, medium, long)"),
    key_prefix: str = Query(None, description="Key prefix to selectively clear (e.g., 'projects')"),
    admin: User = Depends(require_admin),
):
    """
    Clear query cache.

    **ADMIN ONLY**: Requires superuser privileges.

    Use this endpoint to manually invalidate caches when needed.

    Security (TR-024): Admin-only to prevent performance degradation attacks.

    Query Parameters:
        tier: Optional cache tier to clear (if not specified, clears all tiers)
        key_prefix: Optional key prefix for selective clearing

    Examples:
        - Clear all caches: POST /health/cache/clear
        - Clear short tier: POST /health/cache/clear?tier=short
        - Clear projects: POST /health/cache/clear?key_prefix=projects
        - Clear short projects: POST /health/cache/clear?tier=short&key_prefix=projects
    """
    logger.info(
        f"Admin {admin.email} clearing cache "
        f"(tier={tier or 'all'}, key_prefix={key_prefix or 'none'})"
    )

    before_info = get_cache_info(tier)

    clear_cache(ttl=tier, key_prefix=key_prefix)

    after_info = get_cache_info(tier)

    return {
        "success": True,
        "message": "Cache cleared successfully",
        "before": before_info,
        "after": after_info,
    }


@router.post("/health/cache/reset-stats")
async def reset_cache_statistics(admin: User = Depends(require_admin)):
    """
    Reset cache statistics counters.

    **ADMIN ONLY**: Requires superuser privileges.

    This resets hit/miss/set/invalidation counters to zero
    without clearing the cached data.

    Security (TR-024): Admin-only to prevent hiding evidence of attacks.

    Useful for measuring cache performance over a specific period.
    """
    logger.info(f"Admin {admin.email} resetting cache statistics")

    reset_cache_stats()

    return {
        "success": True,
        "message": "Cache statistics reset successfully",
        "stats": get_cache_info(),
    }


@router.get("/health/full")
async def full_health_check():
    """
    Comprehensive health check including all subsystems.

    Returns:
        Complete health status with all components
    """
    pool_status = get_pool_status()
    cache_info = get_cache_info()
    profiling_report = get_profiling_report()

    return {
        "status": "healthy",
        "service": "Content Jumpstart API",
        "version": "1.0.0",
        "components": {
            "api": {"status": "healthy"},
            "database": pool_status,
            "cache": cache_info,
            "profiling": profiling_report["summary"],
        },
    }


@router.get("/health/profiling")
async def profiling_overview():
    """
    Query profiling overview and performance report.

    Returns detailed information about:
    - Total queries executed
    - Query performance statistics
    - Top slowest queries
    - Recent slow queries
    - Performance recommendations

    Use this endpoint to:
    - Identify slow queries
    - Find optimization opportunities
    - Monitor query performance trends
    - Debug performance issues
    """
    report = get_profiling_report()

    # Add threshold information
    report["thresholds"] = {
        "slow_query_ms": SLOW_QUERY_THRESHOLD_MS,
        "very_slow_query_ms": VERY_SLOW_QUERY_THRESHOLD_MS,
    }

    return report


@router.get("/health/profiling/queries")
async def profiling_query_statistics(
    min_execution_count: int = Query(0, ge=0, description="Minimum execution count"),
    min_avg_time_ms: float = Query(0, ge=0, description="Minimum average time (ms)"),
    only_slow: bool = Query(False, description="Only show queries with slow executions"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
):
    """
    Detailed query statistics.

    Query Parameters:
        min_execution_count: Only return queries executed at least this many times
        min_avg_time_ms: Only return queries with avg time >= this threshold
        only_slow: Only return queries with slow executions
        limit: Maximum results to return

    Returns:
        List of query statistics with execution metrics

    Examples:
        - All queries: GET /health/profiling/queries
        - Slow queries only: GET /health/profiling/queries?only_slow=true
        - Frequently executed: GET /health/profiling/queries?min_execution_count=100
        - Slowest on average: GET /health/profiling/queries?min_avg_time_ms=50
    """
    stats = get_query_statistics(
        min_execution_count=min_execution_count,
        min_avg_time_ms=min_avg_time_ms,
        only_slow=only_slow,
    )

    # Limit results
    stats = stats[:limit]

    # Format response
    return {
        "count": len(stats),
        "limit": limit,
        "filters": {
            "min_execution_count": min_execution_count,
            "min_avg_time_ms": min_avg_time_ms,
            "only_slow": only_slow,
        },
        "queries": [
            {
                "query_hash": s.query_hash,
                "query_sample": (
                    s.query_sample[:300] + "..." if len(s.query_sample) > 300 else s.query_sample
                ),
                "execution_count": s.execution_count,
                "total_time_ms": round(s.total_time_ms, 2),
                "avg_time_ms": round(s.avg_time_ms, 2),
                "min_time_ms": round(s.min_time_ms, 2),
                "max_time_ms": round(s.max_time_ms, 2),
                "slow_count": s.slow_count,
                "very_slow_count": s.very_slow_count,
            }
            for s in stats
        ],
    }


@router.get("/health/profiling/slow-queries")
async def profiling_slow_queries(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    since_minutes: int = Query(60, ge=1, le=1440, description="Show queries from last N minutes"),
    very_slow_only: bool = Query(False, description="Only show very slow queries (>500ms)"),
):
    """
    Recent slow query executions.

    Query Parameters:
        limit: Maximum number of results
        since_minutes: Show queries from last N minutes
        very_slow_only: Only show very slow queries (>500ms)

    Returns:
        List of recent slow queries with timestamps

    Examples:
        - Last 50 slow queries: GET /health/profiling/slow-queries
        - Last hour: GET /health/profiling/slow-queries?since_minutes=60
        - Critical only: GET /health/profiling/slow-queries?very_slow_only=true
    """
    since = datetime.utcnow() - timedelta(minutes=since_minutes)

    queries = get_slow_queries(limit=limit, since=since, very_slow_only=very_slow_only)

    return {
        "count": len(queries),
        "limit": limit,
        "since_minutes": since_minutes,
        "very_slow_only": very_slow_only,
        "thresholds": {
            "slow_query_ms": SLOW_QUERY_THRESHOLD_MS,
            "very_slow_query_ms": VERY_SLOW_QUERY_THRESHOLD_MS,
        },
        "queries": [
            {
                "query": q["query"][:300] + "..." if len(q["query"]) > 300 else q["query"],
                "duration_ms": round(q["duration_ms"], 2),
                "timestamp": q["timestamp"].isoformat(),
                "endpoint": q["endpoint"],
                "is_very_slow": q["is_very_slow"],
            }
            for q in queries
        ],
    }


@router.post("/health/profiling/reset")
async def reset_profiling_statistics(admin: User = Depends(require_admin)):
    """
    Reset query profiling statistics.

    **ADMIN ONLY**: Requires superuser privileges.

    This clears all accumulated profiling data:
    - Query statistics
    - Slow query history
    - Performance metrics

    Security (TR-024): Admin-only to prevent hiding evidence of attacks.

    Useful for:
    - Starting fresh profiling session
    - Clearing old data after optimization
    - Resetting after load testing
    """
    logger.info(f"Admin {admin.email} resetting query profiling statistics")

    reset_statistics()

    return {"success": True, "message": "Profiling statistics reset successfully"}
