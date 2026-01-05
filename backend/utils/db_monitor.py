"""
Database connection pool monitoring utilities.
"""
from typing import Dict, Any
from sqlalchemy.engine.url import make_url

from backend.database import engine
from backend.config import settings


def get_pool_status() -> Dict[str, Any]:
    """
    Get current connection pool status and statistics.

    Returns:
        Dictionary with pool metrics including:
        - size: Number of connections in pool
        - checked_in: Available connections
        - checked_out: Active connections
        - overflow: Connections beyond pool_size
        - total: Total connections (size + overflow)
        - settings: Configured pool settings
    """
    database_url = make_url(settings.DATABASE_URL)

    # SQLite doesn't have meaningful pool stats
    if database_url.drivername.startswith("sqlite"):
        return {
            "database": "sqlite",
            "pooling": "disabled",
            "note": "SQLite uses single connection, pooling not applicable",
            "settings": {
                "check_same_thread": False,
            },
        }

    # Get pool instance
    pool = engine.pool

    # Calculate pool metrics
    checked_out = pool.checkedout()
    overflow = pool.overflow()
    size = pool.size()
    checked_in = size - checked_out

    return {
        "database": database_url.drivername,
        "pool_class": pool.__class__.__name__,
        "connections": {
            "pool_size": size,
            "checked_in": checked_in,  # Available for use
            "checked_out": checked_out,  # Currently in use
            "overflow": overflow,  # Beyond pool_size
            "total": size + overflow,
        },
        "settings": {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_pre_ping": settings.DB_POOL_PRE_PING,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
        },
        "utilization": {
            "percent": round((checked_out / (size + overflow)) * 100, 2)
            if (size + overflow) > 0
            else 0,
            "status": _get_utilization_status(checked_out, size, overflow),
        },
        "health": {
            "status": _get_health_status(checked_out, size, overflow),
            "recommendations": _get_recommendations(checked_out, size, overflow),
        },
    }


def _get_utilization_status(checked_out: int, size: int, overflow: int) -> str:
    """
    Get human-readable utilization status.

    Args:
        checked_out: Number of active connections
        size: Pool size
        overflow: Overflow connections

    Returns:
        Status string: "healthy", "moderate", "high", "critical"
    """
    total = size + overflow
    if total == 0:
        return "unknown"

    utilization = checked_out / total

    if utilization < 0.6:
        return "healthy"
    elif utilization < 0.8:
        return "moderate"
    elif utilization < 0.95:
        return "high"
    else:
        return "critical"


def _get_health_status(checked_out: int, size: int, overflow: int) -> str:
    """
    Get overall pool health status.

    Args:
        checked_out: Number of active connections
        size: Pool size
        overflow: Overflow connections

    Returns:
        Health status: "healthy", "degraded", "critical"
    """
    # Using overflow means we exceeded pool_size
    if overflow > settings.DB_MAX_OVERFLOW * 0.8:
        return "critical"
    elif overflow > settings.DB_MAX_OVERFLOW * 0.5:
        return "degraded"
    elif checked_out > size * 0.9:
        return "degraded"
    else:
        return "healthy"


def _get_recommendations(checked_out: int, size: int, overflow: int) -> list[str]:
    """
    Get recommendations for pool tuning.

    Args:
        checked_out: Number of active connections
        size: Pool size
        overflow: Overflow connections

    Returns:
        List of recommendation strings
    """
    recommendations = []

    # High utilization
    if checked_out / (size + overflow) > 0.8:
        recommendations.append(
            "Connection pool is highly utilized. Consider increasing DB_POOL_SIZE."
        )

    # Using overflow
    if overflow > 0:
        if overflow > settings.DB_MAX_OVERFLOW * 0.5:
            recommendations.append(
                f"Using {overflow} overflow connections (>{50}% of max). "
                "Consider increasing DB_POOL_SIZE."
            )
        else:
            recommendations.append(
                f"Using {overflow} overflow connections. This is normal for traffic spikes."
            )

    # Low utilization
    if checked_out / size < 0.3 and size > 10:
        recommendations.append(
            "Connection pool is under-utilized. Consider reducing DB_POOL_SIZE to save resources."
        )

    # No issues
    if not recommendations:
        recommendations.append("Connection pool is healthy. No tuning needed.")

    return recommendations


def get_pool_events() -> Dict[str, Any]:
    """
    Get pool event counters (if available).

    Returns:
        Dictionary with pool event counts
    """
    database_url = make_url(settings.DATABASE_URL)

    if database_url.drivername.startswith("sqlite"):
        return {"database": "sqlite", "events": "not_applicable"}

    pool = engine.pool

    # Note: These counters may not be available in all SQLAlchemy versions
    # This is a best-effort attempt to gather metrics
    events = {}

    # Try to get event listeners
    try:
        # Pool has event tracking if configured
        events["pool_events_supported"] = hasattr(pool, "_pool")
    except Exception:
        events["pool_events_supported"] = False

    return {
        "database": database_url.drivername,
        "events": events,
        "note": "Event tracking requires SQLAlchemy event listeners configured",
    }
