"""Database connection pool monitoring utilities."""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional

from sqlalchemy.engine.url import make_url

from backend.config import settings


def get_engine():
    """Return the shared SQLAlchemy engine.

    Kept as a small indirection so tests can patch the lookup point that existed
    in the older utility layout.
    """

    from backend.database import engine

    return engine


def _database_type_from_url(database_url: str) -> str:
    url = make_url(database_url)
    driver = url.drivername.lower()
    if driver.startswith("sqlite"):
        return "sqlite"
    if driver.startswith("postgresql"):
        return "postgresql"
    if driver.startswith("mysql"):
        return "mysql"
    return driver.split("+", 1)[0]


def get_pool_status() -> Dict[str, Any]:
    """Return connection pool status in the shape used by the health tests."""

    try:
        engine = get_engine()
        engine_url = str(getattr(engine, "url", settings.DATABASE_URL))
        database_type = _database_type_from_url(engine_url)

        if database_type == "sqlite":
            return {
                "has_pool": False,
                "database_type": "sqlite",
                "pool_size": None,
                "max_overflow": None,
                "checked_out": 0,
                "checked_in": 0,
                "utilization_percent": 0.0,
                "health_status": "healthy",
                "recommendations": _get_recommendations(
                    {"has_pool": False, "database_type": "sqlite"}
                ),
            }

        pool = getattr(engine, "pool", None)
        if pool is None:
            return {
                "has_pool": False,
                "database_type": database_type,
                "pool_size": None,
                "max_overflow": None,
                "checked_out": 0,
                "checked_in": 0,
                "utilization_percent": 0.0,
                "health_status": "healthy",
                "recommendations": _get_recommendations(
                    {"has_pool": False, "database_type": database_type}
                ),
            }

        checked_out = int(pool.checkedout()) if hasattr(pool, "checkedout") else 0
        checked_in = int(pool.checkedin()) if hasattr(pool, "checkedin") else 0
        pool_size = int(pool.size()) if hasattr(pool, "size") else 0
        max_overflow = int(pool.overflow()) if hasattr(pool, "overflow") else 0
        capacity = pool_size or 0
        utilization = round((checked_out / capacity) * 100, 2) if capacity > 0 else 0.0

        status = "healthy"
        if utilization >= 95:
            status = "critical"
        elif utilization >= 80:
            status = "warning"

        result = {
            "has_pool": True,
            "database_type": database_type,
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "checked_out": checked_out,
            "checked_in": checked_in,
            "utilization_percent": utilization,
            "health_status": status,
        }
        result["recommendations"] = _get_recommendations(result)
        return result
    except Exception as exc:
        return {
            "has_pool": False,
            "database_type": "unknown",
            "pool_size": None,
            "max_overflow": None,
            "checked_out": 0,
            "checked_in": 0,
            "utilization_percent": 0.0,
            "health_status": "error",
            "error": str(exc),
            "recommendations": _get_recommendations({"has_pool": False, "error": str(exc)}),
        }


def _get_recommendations(
    pool_status: Dict[str, Any],
    size: Optional[int] = None,
    overflow: Optional[int] = None,
) -> List[Dict[str, str]]:
    """Build recommendation entries from a pool status payload.

    The tests exercise the legacy single-argument form, while the runtime uses
    the richer status dict returned by `get_pool_status`.
    """

    recommendations: List[Dict[str, str]] = []
    database_type = str(pool_status.get("database_type", "unknown"))
    has_pool = bool(pool_status.get("has_pool", True))
    utilization = float(pool_status.get("utilization_percent", 0.0) or 0.0)

    if not has_pool:
        recommendations.append(
            {
                "severity": "info",
                "message": f"No connection pool configured for {database_type}. Pool tuning is not applicable.",
            }
        )
        return recommendations

    if size is None:
        size = int(pool_status.get("pool_size") or 0)
    if overflow is None:
        overflow = int(pool_status.get("max_overflow") or 0)

    if utilization >= 95:
        recommendations.append(
            {
                "severity": "critical",
                "message": "Connection pool utilization is critical. Increase pool size or reduce concurrent load.",
            }
        )
    elif utilization >= 80:
        recommendations.append(
            {
                "severity": "warning",
                "message": "Connection pool has high utilization. Consider increasing DB_POOL_SIZE.",
            }
        )
    elif utilization <= 40:
        recommendations.append(
            {
                "severity": "info",
                "message": "Connection pool is healthy and has adequate capacity.",
            }
        )
    else:
        recommendations.append(
            {
                "severity": "info",
                "message": "Connection pool usage is within expected bounds.",
            }
        )

    if overflow > 0:
        severity = (
            "warning" if overflow <= max(1, int(settings.DB_MAX_OVERFLOW * 0.5)) else "critical"
        )
        recommendations.append(
            {
                "severity": severity,
                "message": f"Using {overflow} overflow connections. Consider increasing DB_POOL_SIZE.",
            }
        )

    if size and size > 10 and float(pool_status.get("checked_out", 0) or 0) / max(size, 1) < 0.3:
        recommendations.append(
            {
                "severity": "info",
                "message": "Connection pool is under-utilized. Consider reducing DB_POOL_SIZE to save resources.",
            }
        )

    return recommendations


def get_pool_events() -> Dict[str, Any]:
    """Return connection pool event counters."""

    try:
        engine = get_engine()
        database_type = "unknown"
        try:
            engine_url = str(getattr(engine, "url", settings.DATABASE_URL))
            database_type = _database_type_from_url(engine_url)
        except Exception:
            database_type = "unknown"

        if database_type == "sqlite":
            return {
                "has_listener": False,
                "database_type": "sqlite",
                "message": "Pool event listener not configured",
            }

        pool = getattr(engine, "pool", None)
        listener = getattr(pool, "_poollistener", None) if pool is not None else None
        if listener is None:
            return {
                "has_listener": False,
                "database_type": database_type,
                "message": "Pool event listener not configured",
            }

        return {
            "has_listener": True,
            "database_type": database_type,
            "connect_count": int(getattr(listener, "connect_count", 0)),
            "disconnect_count": int(getattr(listener, "disconnect_count", 0)),
            "checkout_count": int(getattr(listener, "checkout_count", 0)),
            "checkin_count": int(getattr(listener, "checkin_count", 0)),
            "reset_count": int(getattr(listener, "reset_count", 0)),
        }
    except Exception as exc:
        return {
            "has_listener": False,
            "database_type": "unknown",
            "error": str(exc),
            "message": "Unable to read pool event counters",
        }


sys.modules.setdefault("utils.db_monitor", sys.modules[__name__])
sys.modules.setdefault("backend.utils.db_monitor", sys.modules[__name__])
