"""
Caching Utility

Provides in-memory caching with TTL and invalidation support.
Designed to be easily swapped with Redis for production scaling.
"""

import asyncio
import hashlib
import json
import logging
import time
from functools import wraps
from typing import Any, Callable, Optional, Dict
from collections import OrderedDict

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a single cache entry with TTL"""

    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Check if this cache entry has expired"""
        if self.ttl == 0:  # 0 means never expire
            return False
        return time.time() - self.created_at > self.ttl


class InMemoryCache:
    """
    Thread-safe in-memory cache with TTL and LRU eviction.

    Features:
    - TTL (time-to-live) support
    - LRU eviction when max_size reached
    - Pattern-based invalidation
    - Hit/miss metrics
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of entries (LRU eviction when exceeded)
            default_ttl: Default TTL in seconds (0 = never expire)
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

        # Metrics
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired():
                # Remove expired entry
                del self._cache[key]
                self._misses += 1
                logger.debug(f"Cache EXPIRED: {key}")
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            self._hits += 1
            logger.debug(f"Cache HIT: {key}")
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (None = use default)
        """
        async with self._lock:
            # Evict oldest entry if at max size
            if len(self._cache) >= self._max_size and key not in self._cache:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(f"Cache EVICTED (LRU): {oldest_key}")

            ttl = ttl if ttl is not None else self._default_ttl
            self._cache[key] = CacheEntry(value, ttl)
            self._cache.move_to_end(key)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")

    async def delete(self, key: str):
        """
        Delete entry from cache.

        Args:
            key: Cache key
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache DELETE: {key}")

    async def clear(self):
        """Clear all cache entries"""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache CLEARED: {count} entries removed")

    async def invalidate_pattern(self, pattern: str):
        """
        Invalidate all keys matching a pattern.

        Args:
            pattern: Pattern to match (supports * wildcard)
        """
        async with self._lock:
            # Convert pattern to regex.
            # `*` is the only supported wildcard; every other character is a
            # literal. Escape the whole pattern first (neutralizing any regex
            # metacharacters in the caller-supplied string, which reaches this
            # method from an HTTP path parameter), then restore `*` as `.*`.
            # This prevents regex-injection / ReDoS and re.error 500s.
            import re

            regex_pattern = re.escape(pattern).replace(r"\*", ".*")
            regex = re.compile(f"^{regex_pattern}$")

            keys_to_delete = [key for key in self._cache.keys() if regex.match(key)]

            for key in keys_to_delete:
                del self._cache[key]

            if keys_to_delete:
                logger.info(
                    f"Cache INVALIDATED: {len(keys_to_delete)} entries matching '{pattern}'"
                )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
        }


# Global cache instance
_cache: Optional[InMemoryCache] = None


def get_cache() -> InMemoryCache:
    """Get the global cache instance"""
    global _cache
    if _cache is None:
        _cache = InMemoryCache(max_size=1000, default_ttl=300)
    return _cache


def cache_key(*args, **kwargs) -> str:
    """
    Generate a cache key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Hash-based cache key
    """
    # Create a stable representation of arguments
    key_data = {
        "args": [str(arg) for arg in args],
        "kwargs": {k: str(v) for k, v in sorted(kwargs.items())},
    }

    # Generate hash
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results.

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys (useful for invalidation)

    Example:
        @cached(ttl=600, key_prefix="research_results")
        async def get_research_results(project_id: str):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            func_name = f"{func.__module__}.{func.__qualname__}"
            arg_key = cache_key(*args, **kwargs)
            full_key = (
                f"{key_prefix}:{func_name}:{arg_key}" if key_prefix else f"{func_name}:{arg_key}"
            )

            # Try to get from cache
            cache = get_cache()
            cached_value = await cache.get(full_key)

            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = await func(*args, **kwargs)
            await cache.set(full_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator
