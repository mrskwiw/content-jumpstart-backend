"""
Server-side query result caching using cachetools.

Provides in-memory caching for expensive database queries to reduce
database load and improve response times.
"""
import functools
import hashlib
import json
import time
from typing import Any, Callable, Dict, Optional

from cachetools import TTLCache

# Global cache instances
# Using TTLCache for automatic expiration
_caches: Dict[str, TTLCache] = {
    # Short TTL for frequently changing data (5 minutes)
    "short": TTLCache(maxsize=100, ttl=300),
    # Medium TTL for semi-static data (10 minutes)
    "medium": TTLCache(maxsize=50, ttl=600),
    # Long TTL for static data (1 hour)
    "long": TTLCache(maxsize=20, ttl=3600),
}

# Cache statistics
_cache_stats: Dict[str, Dict[str, int]] = {
    "short": {"hits": 0, "misses": 0, "sets": 0, "invalidations": 0},
    "medium": {"hits": 0, "misses": 0, "sets": 0, "invalidations": 0},
    "long": {"hits": 0, "misses": 0, "sets": 0, "invalidations": 0},
}


def _make_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """
    Generate cache key from function name and arguments.

    Args:
        func_name: Name of the cached function
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Unique cache key string
    """
    # Filter out non-serializable args (like database sessions)
    filtered_kwargs = {
        k: v for k, v in kwargs.items() if k not in ["db", "session", "engine"]
    }

    # Create key from function name + args + kwargs
    key_data = {"func": func_name, "args": args, "kwargs": filtered_kwargs}

    # JSON serialize and hash
    key_json = json.dumps(key_data, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_json.encode()).hexdigest()

    return f"{func_name}:{key_hash}"


def cached(ttl: str = "short", key_prefix: Optional[str] = None):
    """
    Decorator for caching function results.

    Args:
        ttl: Cache TTL tier ("short", "medium", "long")
        key_prefix: Optional key prefix for cache namespacing

    Returns:
        Decorator function

    Example:
        @cached(ttl="medium", key_prefix="projects")
        def get_projects(db, skip=0, limit=100):
            return db.query(Project).offset(skip).limit(limit).all()
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache instance
            cache = _caches.get(ttl, _caches["short"])
            stats = _cache_stats.get(ttl, _cache_stats["short"])

            # Generate cache key
            cache_key_base = key_prefix or func.__name__
            cache_key = _make_cache_key(cache_key_base, args, kwargs)

            # Try to get from cache
            if cache_key in cache:
                stats["hits"] += 1
                return cache[cache_key]

            # Cache miss - execute function
            stats["misses"] += 1
            result = func(*args, **kwargs)

            # Store in cache
            cache[cache_key] = result
            stats["sets"] += 1

            return result

        # Add cache control methods to wrapped function
        wrapper.cache_clear = lambda: clear_cache(ttl, key_prefix)
        wrapper.cache_info = lambda: get_cache_info(ttl)

        return wrapper

    return decorator


def clear_cache(ttl: Optional[str] = None, key_prefix: Optional[str] = None):
    """
    Clear cache entries.

    Args:
        ttl: Cache tier to clear (None = all tiers)
        key_prefix: Optional key prefix to selectively clear

    Example:
        # Clear all caches
        clear_cache()

        # Clear specific tier
        clear_cache(ttl="short")

        # Clear specific namespace
        clear_cache(ttl="medium", key_prefix="projects")
    """
    tiers = [ttl] if ttl else _caches.keys()

    for tier in tiers:
        cache = _caches.get(tier)
        stats = _cache_stats.get(tier)

        if cache is None:
            continue

        if key_prefix:
            # Selective clear by prefix
            keys_to_delete = [k for k in cache.keys() if k.startswith(f"{key_prefix}:")]
            for key in keys_to_delete:
                del cache[key]
                if stats:
                    stats["invalidations"] += 1
        else:
            # Clear entire tier
            count = len(cache)
            cache.clear()
            if stats:
                stats["invalidations"] += count


def invalidate_related_caches(*key_prefixes: str):
    """
    Invalidate caches related to specific resources.

    Use this after mutations (create, update, delete) to ensure
    fresh data is fetched.

    Args:
        *key_prefixes: Resource names to invalidate (e.g., "projects", "posts")

    Example:
        # After creating a project
        invalidate_related_caches("projects", "clients")
    """
    for prefix in key_prefixes:
        for tier in _caches.keys():
            clear_cache(ttl=tier, key_prefix=prefix)


def get_cache_info(ttl: Optional[str] = None) -> Dict[str, Any]:
    """
    Get cache statistics.

    Args:
        ttl: Specific tier to get stats for (None = all tiers)

    Returns:
        Dictionary with cache stats including:
        - size: Current number of cached entries
        - maxsize: Maximum cache size
        - ttl: Time-to-live in seconds
        - hits: Number of cache hits
        - misses: Number of cache misses
        - hit_rate: Cache hit rate percentage
    """
    if ttl:
        cache = _caches.get(ttl)
        stats = _cache_stats.get(ttl, {})

        if cache is None:
            return {"error": f"Unknown cache tier: {ttl}"}

        total_requests = stats.get("hits", 0) + stats.get("misses", 0)
        hit_rate = (
            round((stats.get("hits", 0) / total_requests) * 100, 2)
            if total_requests > 0
            else 0.0
        )

        return {
            "tier": ttl,
            "size": len(cache),
            "maxsize": cache.maxsize,
            "ttl_seconds": cache.ttl,
            "hits": stats.get("hits", 0),
            "misses": stats.get("misses", 0),
            "sets": stats.get("sets", 0),
            "invalidations": stats.get("invalidations", 0),
            "hit_rate_percent": hit_rate,
        }
    else:
        # Return stats for all tiers
        return {tier: get_cache_info(tier) for tier in _caches.keys()}


def reset_cache_stats():
    """Reset all cache statistics counters."""
    for stats in _cache_stats.values():
        stats["hits"] = 0
        stats["misses"] = 0
        stats["sets"] = 0
        stats["invalidations"] = 0


# Convenience functions for common cache operations


def cache_short(key_prefix: Optional[str] = None):
    """Decorator for short TTL caching (5 minutes)."""
    return cached(ttl="short", key_prefix=key_prefix)


def cache_medium(key_prefix: Optional[str] = None):
    """Decorator for medium TTL caching (10 minutes)."""
    return cached(ttl="medium", key_prefix=key_prefix)


def cache_long(key_prefix: Optional[str] = None):
    """Decorator for long TTL caching (1 hour)."""
    return cached(ttl="long", key_prefix=key_prefix)
