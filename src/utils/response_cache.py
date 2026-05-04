"""API Response Cache using JSON serialization

This module provides disk-based caching of API responses to reduce costs
and improve development/testing workflows. Uses JSON for secure serialization
instead of pickle to avoid arbitrary code execution vulnerabilities.

Usage:
    cache = ResponseCache()

    # Try to get cached response
    cached = cache.get(messages, system, temperature)
    if cached:
        return cached

    # Make API call...
    response = api_call(...)

    # Cache the response
    cache.put(messages, system, temperature, response)
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.logger import logger


class ResponseCache:
    """Disk-based cache for API responses using JSON serialization

    Features:
    - Content-based hashing for cache keys
    - TTL-based expiration
    - JSON serialization (secure, no arbitrary code execution)
    - Automatic cleanup of corrupted cache files

    Example:
        >>> cache = ResponseCache()
        >>> messages = [{"role": "user", "content": "Hello"}]
        >>> cached = cache.get(messages, "system prompt", 0.7)
        >>> if cached:
        ...     print("Cache hit!")
        ... else:
        ...     response = make_api_call()
        ...     cache.put(messages, "system prompt", 0.7, response)
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl_seconds: int = 86400,  # 24 hours
        enabled: bool = True,
    ):
        """Initialize response cache

        Args:
            cache_dir: Directory to store cache files (default: .cache/api_responses)
            ttl_seconds: Time-to-live for cached responses in seconds
            enabled: Whether caching is enabled (useful for dev/prod toggle)
        """
        if cache_dir is None:
            # On Render/production, use /tmp (writable), otherwise use local .cache
            import os

            if (
                os.environ.get("RENDER")
                or not Path(".cache").exists()
                and not os.access(".", os.W_OK)
            ):
                cache_dir = Path(
                    "/tmp/.cache/api_responses"
                )  # nosec B108 - safe for cache directory
            else:
                cache_dir = Path(".cache/api_responses")

        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.enabled = enabled

        if self.enabled:
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Response cache initialized: {self.cache_dir}")
            except (PermissionError, OSError) as e:
                logger.warning(
                    f"Failed to create cache directory {self.cache_dir}: {e}. Disabling cache."
                )
                self.enabled = False

    def _get_cache_key(
        self,
        messages: List[Dict[str, str]],
        system: str,
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate deterministic cache key from request parameters

        Uses SHA-256 hash of sorted JSON to ensure identical requests
        produce identical cache keys regardless of dict ordering.
        max_tokens is included so that calls with different token budgets
        (e.g. blog posts at 6000 vs default 4096) never share a cache entry.

        Args:
            messages: List of message dictionaries
            system: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens for the response

        Returns:
            Hex-encoded SHA-256 hash
        """
        # Create deterministic string representation
        content = {
            "system": system,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        # Sort keys to ensure determinism
        content_str = json.dumps(content, sort_keys=True)

        # Generate hash
        return hashlib.sha256(content_str.encode()).hexdigest()

    def get(
        self,
        messages: List[Dict[str, str]],
        system: str,
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """Retrieve cached response if available and valid

        Args:
            messages: List of message dictionaries
            system: System prompt
            temperature: Sampling temperature

        Returns:
            Cached response string, or None if cache miss/expired/invalid
        """
        if not self.enabled:
            return None

        key = self._get_cache_key(messages, system, temperature, max_tokens)
        cache_file = self.cache_dir / f"{key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)

            # Validate cache structure
            if not isinstance(cached_data, dict):
                logger.warning(f"Invalid cache structure in {cache_file}")
                cache_file.unlink()
                return None

            if "response" not in cached_data or "timestamp" not in cached_data:
                logger.warning(f"Missing fields in cache {cache_file}")
                cache_file.unlink()
                return None

            # Check TTL
            age = time.time() - cached_data["timestamp"]
            if age > self.ttl_seconds:
                logger.debug(f"Cache expired (age: {age:.0f}s): {key[:8]}...")
                cache_file.unlink()
                return None

            logger.debug(f"Cache HIT (age: {age:.0f}s): {key[:8]}...")
            response: str = cached_data["response"]
            return response

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Corrupted cache file {cache_file}: {e}")
            # Remove corrupted cache file
            try:
                cache_file.unlink()
            except Exception:
                pass
            return None

        except Exception as e:
            logger.error(f"Error reading cache {cache_file}: {e}")
            return None

    def put(
        self,
        messages: List[Dict[str, str]],
        system: str,
        temperature: float,
        response: str,
        max_tokens: Optional[int] = None,
    ) -> None:
        """Cache API response for future use

        Args:
            messages: List of message dictionaries
            system: System prompt
            temperature: Sampling temperature
            response: API response to cache
            max_tokens: Maximum tokens used for this response
        """
        if not self.enabled:
            return

        key = self._get_cache_key(messages, system, temperature, max_tokens)
        cache_file = self.cache_dir / f"{key}.json"

        try:
            cache_data = {
                "response": response,
                "timestamp": time.time(),
                "ttl": self.ttl_seconds,
                "key": key[:8],  # For debugging
            }

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)

            logger.debug(f"Cached response: {key[:8]}...")

        except Exception as e:
            logger.error(f"Failed to cache response: {e}")

    def get_by_key(self, cache_key: str) -> Optional[Any]:
        """Retrieve cached data by key (generic caching)

        Args:
            cache_key: Cache key (typically a hash)

        Returns:
            Cached data if valid and not expired, None otherwise
        """
        if not self.enabled:
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            if not cache_file.exists():
                return None

            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # Check TTL
            timestamp = cache_data.get("timestamp", 0)
            ttl = cache_data.get("ttl", self.ttl_seconds)

            if time.time() - timestamp > ttl:
                logger.debug(f"Cache expired: {cache_key[:8]}...")
                cache_file.unlink()  # Clean up expired cache
                return None

            logger.debug(f"Cache hit: {cache_key[:8]}...")
            return cache_data.get("data")

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Invalid cache file {cache_key[:8]}...: {e}")
            if cache_file.exists():
                cache_file.unlink()  # Clean up corrupted cache
            return None
        except Exception as e:
            logger.error(f"Cache read error for {cache_key[:8]}...: {e}")
            return None

    def put_by_key(self, cache_key: str, data: Any) -> None:
        """Cache data by key (generic caching)

        Args:
            cache_key: Cache key (typically a hash)
            data: Data to cache (must be JSON-serializable)
        """
        if not self.enabled:
            return

        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            cache_data = {
                "data": data,
                "timestamp": time.time(),
                "ttl": self.ttl_seconds,
                "key": cache_key[:8],  # For debugging
            }

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)

            logger.debug(f"Cached data: {cache_key[:8]}...")

        except Exception as e:
            logger.error(f"Failed to cache data: {e}")

    def delete(self, cache_key: str) -> bool:
        """Delete a specific cached response by key

        Args:
            cache_key: The cache key to delete

        Returns:
            True if the cache entry was deleted, False otherwise
        """
        if not self.enabled or not self.cache_dir.exists():
            return False

        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                cache_file.unlink()
                logger.debug(f"Deleted cache entry: {cache_key[:8]}...")
                return True
            except Exception as e:
                logger.warning(f"Failed to delete cache entry {cache_key[:8]}...: {e}")
                return False
        return False

    def clear(self) -> None:
        """Clear all cached responses

        Useful for:
        - Testing
        - Forcing fresh API calls
        - Cleaning up old cache files
        """
        if not self.enabled or not self.cache_dir.exists():
            return

        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {cache_file}: {e}")

        logger.info(f"Cleared {count} cached responses")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics

        Returns:
            Dictionary with cache statistics:
            - total_files: Number of cache files
            - total_size_bytes: Total size of cache directory
            - oldest_timestamp: Timestamp of oldest cache file
            - newest_timestamp: Timestamp of newest cache file
        """
        if not self.enabled or not self.cache_dir.exists():
            return {
                "enabled": False,
                "total_files": 0,
                "total_size_bytes": 0,
            }

        files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in files)

        timestamps = []
        for f in files:
            try:
                with open(f, "r") as cf:
                    data = json.load(cf)
                    if "timestamp" in data:
                        timestamps.append(data["timestamp"])
            except Exception:
                pass

        return {
            "enabled": True,
            "total_files": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "oldest_timestamp": min(timestamps) if timestamps else None,
            "newest_timestamp": max(timestamps) if timestamps else None,
        }
