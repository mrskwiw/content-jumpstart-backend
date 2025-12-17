"""Template Cache Manager with LRU eviction and TTL support

Provides efficient caching for template library with:
- LRU (Least Recently Used) eviction policy
- TTL (Time To Live) for cache entries
- File modification detection
- Size limits to prevent unbounded memory growth
"""

import time
from collections import OrderedDict
from pathlib import Path
from threading import RLock
from typing import List, Optional

from ..models.template import Template
from .logger import logger


class TemplateCacheEntry:
    """Single cache entry with metadata"""

    def __init__(self, templates: List[Template], mtime: float, timestamp: float):
        """
        Initialize cache entry

        Args:
            templates: List of Template objects
            mtime: File modification time
            timestamp: Cache entry creation timestamp
        """
        self.templates = templates
        self.mtime = mtime
        self.timestamp = timestamp

    def is_valid(self, path: Path, ttl_seconds: float) -> bool:
        """
        Check if cache entry is still valid

        Args:
            path: Path to template file
            ttl_seconds: Time to live in seconds

        Returns:
            True if entry is valid, False otherwise
        """
        # Check TTL
        if time.time() - self.timestamp > ttl_seconds:
            return False

        # Check file modification
        try:
            current_mtime = path.stat().st_mtime
            if current_mtime != self.mtime:
                return False
        except (OSError, FileNotFoundError):
            return False

        return True


class TemplateCacheManager:
    """Thread-safe LRU cache manager for templates

    Features:
    - LRU eviction when size limit reached
    - TTL (default 1 hour)
    - File modification detection
    - Thread-safe operations
    """

    def __init__(self, max_size: int = 10, ttl_seconds: float = 3600.0):
        """
        Initialize cache manager

        Args:
            max_size: Maximum number of template files to cache (default 10)
            ttl_seconds: Time to live for cache entries in seconds (default 3600 = 1 hour)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[Path, TemplateCacheEntry] = OrderedDict()
        self._lock = RLock()  # Reentrant lock for thread safety
        self._hit_count = 0
        self._miss_count = 0

    def get(self, path: Path) -> Optional[List[Template]]:
        """
        Get templates from cache if valid

        Args:
            path: Path to template file

        Returns:
            List of templates if cached and valid, None otherwise
        """
        with self._lock:
            if path not in self.cache:
                self._miss_count += 1
                return None

            entry = self.cache[path]

            # Check validity (TTL and file modification)
            if not entry.is_valid(path, self.ttl_seconds):
                logger.debug(f"Cache entry expired for {path.name}")
                del self.cache[path]
                self._miss_count += 1
                return None

            # Move to end (mark as recently used)
            self.cache.move_to_end(path)
            self._hit_count += 1

            logger.debug(f"Cache hit for {path.name} (hit rate: {self.hit_rate:.1%})")
            return entry.templates.copy()

    def put(self, path: Path, templates: List[Template], mtime: float) -> None:
        """
        Store templates in cache

        Args:
            path: Path to template file
            templates: List of Template objects
            mtime: File modification time
        """
        with self._lock:
            # Create cache entry
            entry = TemplateCacheEntry(
                templates=templates.copy(), mtime=mtime, timestamp=time.time()
            )

            # Remove if already exists (to update position)
            if path in self.cache:
                del self.cache[path]

            # Add new entry
            self.cache[path] = entry

            # Evict oldest if over size limit
            while len(self.cache) > self.max_size:
                evicted_path, _ = self.cache.popitem(last=False)  # Remove oldest (FIFO)
                logger.debug(f"Evicted cache entry for {evicted_path.name} (cache full)")

            logger.debug(
                f"Cached {len(templates)} templates for {path.name} "
                f"(cache size: {len(self.cache)}/{self.max_size})"
            )

    def invalidate(self, path: Path) -> None:
        """
        Invalidate cache entry for a specific file

        Args:
            path: Path to template file
        """
        with self._lock:
            if path in self.cache:
                del self.cache[path]
                logger.debug(f"Invalidated cache for {path.name}")

    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self.cache.clear()
            self._hit_count = 0
            self._miss_count = 0
            logger.info("Template cache cleared")

    @property
    def size(self) -> int:
        """Current number of cached entries"""
        with self._lock:
            return len(self.cache)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate (0.0-1.0)"""
        with self._lock:
            total = self._hit_count + self._miss_count
            if total == 0:
                return 0.0
            return self._hit_count / total

    def get_stats(self) -> dict:
        """
        Get cache statistics

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hit_count": self._hit_count,
                "miss_count": self._miss_count,
                "hit_rate": self.hit_rate,
                "ttl_seconds": self.ttl_seconds,
            }


# Global cache instance
_global_cache_manager: Optional[TemplateCacheManager] = None


def get_cache_manager(max_size: int = 10, ttl_seconds: float = 3600.0) -> TemplateCacheManager:
    """
    Get or create global cache manager instance

    Args:
        max_size: Maximum cache size (only used on first call)
        ttl_seconds: Cache TTL (only used on first call)

    Returns:
        Global TemplateCacheManager instance
    """
    global _global_cache_manager

    if _global_cache_manager is None:
        _global_cache_manager = TemplateCacheManager(max_size=max_size, ttl_seconds=ttl_seconds)
        logger.debug(
            f"Created template cache manager " f"(max_size={max_size}, ttl={ttl_seconds}s)"
        )

    return _global_cache_manager
