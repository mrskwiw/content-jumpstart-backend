"""
Query profiling and performance monitoring.

Tracks database query execution times, identifies slow queries,
and generates performance reports.
"""
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Query performance thresholds
SLOW_QUERY_THRESHOLD_MS = 100  # Queries slower than 100ms are flagged
VERY_SLOW_QUERY_THRESHOLD_MS = 500  # Queries slower than 500ms are critical

# Query statistics storage
_query_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
    "count": 0,
    "total_time_ms": 0.0,
    "min_time_ms": float('inf'),
    "max_time_ms": 0.0,
    "slow_count": 0,
    "very_slow_count": 0,
    "samples": []
})

# Recent slow queries (circular buffer)
_slow_queries: List[Dict[str, Any]] = []
MAX_SLOW_QUERIES = 100


@dataclass
class QueryProfile:
    """Profile of a single query execution."""
    query: str
    params: Dict[str, Any]
    duration_ms: float
    timestamp: datetime
    endpoint: Optional[str] = None
    is_slow: bool = False
    is_very_slow: bool = False


@dataclass
class QueryStatistics:
    """Aggregated statistics for a query pattern."""
    query_hash: str
    query_sample: str
    execution_count: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    slow_count: int
    very_slow_count: int
    recent_samples: List[QueryProfile] = field(default_factory=list)


def _normalize_query(query: str) -> str:
    """
    Normalize query for grouping similar queries.

    Removes parameter values to group queries with same structure.
    """
    import re

    # Remove whitespace variations
    normalized = re.sub(r'\s+', ' ', query.strip())

    # Replace numeric literals
    normalized = re.sub(r'\b\d+\b', '?', normalized)

    # Replace string literals
    normalized = re.sub(r"'[^']*'", '?', normalized)

    return normalized


def _hash_query(query: str) -> str:
    """Generate hash for query grouping."""
    import hashlib
    normalized = _normalize_query(query)
    return hashlib.md5(normalized.encode()).hexdigest()[:12]


def record_query(
    query: str,
    duration_ms: float,
    params: Optional[Dict] = None,
    endpoint: Optional[str] = None
):
    """
    Record query execution for profiling.

    Args:
        query: SQL query string
        duration_ms: Execution time in milliseconds
        params: Query parameters (optional)
        endpoint: API endpoint that triggered query (optional)
    """
    query_hash = _hash_query(query)
    stats = _query_stats[query_hash]

    # Update aggregated statistics
    stats["count"] += 1
    stats["total_time_ms"] += duration_ms
    stats["min_time_ms"] = min(stats["min_time_ms"], duration_ms)
    stats["max_time_ms"] = max(stats["max_time_ms"], duration_ms)

    # Check if slow
    is_slow = duration_ms >= SLOW_QUERY_THRESHOLD_MS
    is_very_slow = duration_ms >= VERY_SLOW_QUERY_THRESHOLD_MS

    if is_slow:
        stats["slow_count"] += 1
    if is_very_slow:
        stats["very_slow_count"] += 1

    # Create profile
    profile = QueryProfile(
        query=query,
        params=params or {},
        duration_ms=duration_ms,
        timestamp=datetime.utcnow(),
        endpoint=endpoint,
        is_slow=is_slow,
        is_very_slow=is_very_slow
    )

    # Store sample
    if "samples" not in stats:
        stats["samples"] = []

    samples = stats["samples"]
    samples.append(profile)

    # Keep only last 5 samples per query pattern
    if len(samples) > 5:
        samples.pop(0)

    # Store in slow queries list
    if is_slow:
        _slow_queries.append({
            "query": query,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow(),
            "endpoint": endpoint,
            "is_very_slow": is_very_slow
        })

        # Keep circular buffer size
        if len(_slow_queries) > MAX_SLOW_QUERIES:
            _slow_queries.pop(0)


def get_query_statistics(
    min_execution_count: int = 0,
    min_avg_time_ms: float = 0,
    only_slow: bool = False
) -> List[QueryStatistics]:
    """
    Get aggregated query statistics.

    Args:
        min_execution_count: Only return queries executed at least this many times
        min_avg_time_ms: Only return queries with average time >= this threshold
        only_slow: Only return queries with slow executions

    Returns:
        List of QueryStatistics sorted by total time (descending)
    """
    results = []

    for query_hash, stats in _query_stats.items():
        # Skip if below execution count threshold
        if stats["count"] < min_execution_count:
            continue

        # Calculate average time
        avg_time_ms = stats["total_time_ms"] / stats["count"]

        # Skip if below average time threshold
        if avg_time_ms < min_avg_time_ms:
            continue

        # Skip if only_slow and no slow executions
        if only_slow and stats["slow_count"] == 0:
            continue

        # Get sample query (first sample's query string)
        query_sample = stats["samples"][0].query if stats["samples"] else "N/A"

        results.append(QueryStatistics(
            query_hash=query_hash,
            query_sample=query_sample,
            execution_count=stats["count"],
            total_time_ms=stats["total_time_ms"],
            avg_time_ms=avg_time_ms,
            min_time_ms=stats["min_time_ms"],
            max_time_ms=stats["max_time_ms"],
            slow_count=stats["slow_count"],
            very_slow_count=stats["very_slow_count"],
            recent_samples=stats["samples"][-3:]  # Last 3 samples
        ))

    # Sort by total time (most expensive first)
    results.sort(key=lambda x: x.total_time_ms, reverse=True)

    return results


def get_slow_queries(
    limit: int = 50,
    since: Optional[datetime] = None,
    very_slow_only: bool = False
) -> List[Dict[str, Any]]:
    """
    Get recent slow queries.

    Args:
        limit: Maximum number of queries to return
        since: Only return queries since this timestamp
        very_slow_only: Only return very slow queries (>500ms)

    Returns:
        List of slow query records, most recent first
    """
    filtered = _slow_queries

    # Filter by timestamp
    if since:
        filtered = [q for q in filtered if q["timestamp"] >= since]

    # Filter by very slow
    if very_slow_only:
        filtered = [q for q in filtered if q["is_very_slow"]]

    # Sort by timestamp (most recent first)
    filtered.sort(key=lambda x: x["timestamp"], reverse=True)

    return filtered[:limit]


def get_profiling_report() -> Dict[str, Any]:
    """
    Generate comprehensive profiling report.

    Returns:
        Dictionary with profiling metrics and recommendations
    """
    # Get all statistics
    all_stats = get_query_statistics()
    slow_stats = get_query_statistics(only_slow=True)

    # Calculate totals
    total_queries = sum(s.execution_count for s in all_stats)
    total_time_ms = sum(s.total_time_ms for s in all_stats)
    total_slow = sum(s.slow_count for s in all_stats)
    total_very_slow = sum(s.very_slow_count for s in all_stats)

    # Calculate percentages
    slow_percentage = (total_slow / total_queries * 100) if total_queries > 0 else 0
    very_slow_percentage = (total_very_slow / total_queries * 100) if total_queries > 0 else 0

    # Get top 10 slowest queries
    top_slowest = all_stats[:10]

    # Get recent slow queries
    recent_slow = get_slow_queries(limit=20)

    # Generate recommendations
    recommendations = []

    if slow_percentage > 10:
        recommendations.append({
            "severity": "warning",
            "message": f"{slow_percentage:.1f}% of queries are slow (>100ms). Consider optimizing or adding indexes."
        })

    if very_slow_percentage > 1:
        recommendations.append({
            "severity": "critical",
            "message": f"{very_slow_percentage:.1f}% of queries are very slow (>500ms). Immediate optimization needed."
        })

    if total_time_ms / total_queries > 50 if total_queries > 0 else False:
        recommendations.append({
            "severity": "info",
            "message": "Average query time is high. Consider connection pooling optimization."
        })

    # Check for N+1 queries (high execution count with low avg time)
    potential_n_plus_1 = [
        s for s in all_stats
        if s.execution_count > 100 and s.avg_time_ms < 10
    ]

    if potential_n_plus_1:
        recommendations.append({
            "severity": "warning",
            "message": f"Detected {len(potential_n_plus_1)} potential N+1 query patterns. Consider using eager loading."
        })

    return {
        "summary": {
            "total_queries": total_queries,
            "total_time_ms": total_time_ms,
            "avg_time_ms": total_time_ms / total_queries if total_queries > 0 else 0,
            "slow_queries": total_slow,
            "very_slow_queries": total_very_slow,
            "slow_percentage": slow_percentage,
            "very_slow_percentage": very_slow_percentage,
            "unique_query_patterns": len(all_stats)
        },
        "top_slowest_queries": [
            {
                "query_hash": s.query_hash,
                "query_sample": s.query_sample[:200] + "..." if len(s.query_sample) > 200 else s.query_sample,
                "execution_count": s.execution_count,
                "total_time_ms": s.total_time_ms,
                "avg_time_ms": s.avg_time_ms,
                "max_time_ms": s.max_time_ms,
                "slow_count": s.slow_count,
                "very_slow_count": s.very_slow_count
            }
            for s in top_slowest
        ],
        "recent_slow_queries": [
            {
                "query": q["query"][:200] + "..." if len(q["query"]) > 200 else q["query"],
                "duration_ms": q["duration_ms"],
                "timestamp": q["timestamp"].isoformat(),
                "endpoint": q["endpoint"],
                "is_very_slow": q["is_very_slow"]
            }
            for q in recent_slow
        ],
        "recommendations": recommendations
    }


def reset_statistics():
    """Reset all profiling statistics."""
    global _query_stats, _slow_queries
    _query_stats.clear()
    _slow_queries.clear()


# SQLAlchemy event listeners for automatic profiling


def enable_sqlalchemy_profiling(engine: Engine):
    """
    Enable automatic profiling for SQLAlchemy engine.

    Hooks into SQLAlchemy's event system to track all queries.

    Args:
        engine: SQLAlchemy engine instance
    """
    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Start timing before query execution."""
        conn.info.setdefault('query_start_time', []).append(time.time())

    @event.listens_for(engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query timing after execution."""
        query_start_times = conn.info.get('query_start_time', [])
        if query_start_times:
            start_time = query_start_times.pop()
            duration_ms = (time.time() - start_time) * 1000

            # Record the query
            record_query(
                query=statement,
                duration_ms=duration_ms,
                params=parameters
            )
