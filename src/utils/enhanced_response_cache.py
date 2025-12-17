"""Enhanced Response Cache with Similarity Detection

Provides two-tier caching for API responses:
- Level 1: Exact match (SHA256 hash-based, fast)
- Level 2: Similarity match (MinHash/LSH, approximate)

Expected token savings: 10-20% additional on top of prompt caching
"""

import json
import time
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional, Tuple

from .logger import logger
from .response_cache import ResponseCache

# Try to import MinHash/LSH for similarity detection
try:
    from datasketch import MinHash, MinHashLSH

    MINHASH_AVAILABLE = True
except ImportError:
    MINHASH_AVAILABLE = False
    logger.warning("datasketch not available - similarity caching disabled")


class CacheStatistics:
    """Track cache performance metrics"""

    def __init__(self):
        self.exact_hits = 0
        self.similarity_hits = 0
        self.misses = 0
        self.total_requests = 0
        self.tokens_saved_exact = 0
        self.tokens_saved_similarity = 0
        self._lock = RLock()

    def record_exact_hit(self, estimated_tokens: int = 0) -> None:
        """Record an exact cache hit"""
        with self._lock:
            self.exact_hits += 1
            self.total_requests += 1
            self.tokens_saved_exact += estimated_tokens

    def record_similarity_hit(self, estimated_tokens: int = 0) -> None:
        """Record a similarity cache hit"""
        with self._lock:
            self.similarity_hits += 1
            self.total_requests += 1
            self.tokens_saved_similarity += estimated_tokens

    def record_miss(self) -> None:
        """Record a cache miss"""
        with self._lock:
            self.misses += 1
            self.total_requests += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        with self._lock:
            total_hits = self.exact_hits + self.similarity_hits
            hit_rate = total_hits / self.total_requests if self.total_requests > 0 else 0.0

            return {
                "total_requests": self.total_requests,
                "exact_hits": self.exact_hits,
                "similarity_hits": self.similarity_hits,
                "misses": self.misses,
                "total_hits": total_hits,
                "hit_rate": hit_rate,
                "exact_hit_rate": self.exact_hits / self.total_requests
                if self.total_requests > 0
                else 0.0,
                "similarity_hit_rate": self.similarity_hits / self.total_requests
                if self.total_requests > 0
                else 0.0,
                "tokens_saved_exact": self.tokens_saved_exact,
                "tokens_saved_similarity": self.tokens_saved_similarity,
                "total_tokens_saved": self.tokens_saved_exact + self.tokens_saved_similarity,
            }

    def reset(self) -> None:
        """Reset all statistics"""
        with self._lock:
            self.exact_hits = 0
            self.similarity_hits = 0
            self.misses = 0
            self.total_requests = 0
            self.tokens_saved_exact = 0
            self.tokens_saved_similarity = 0


class SimilarityIndex:
    """MinHash/LSH index for finding similar prompts"""

    def __init__(self, similarity_threshold: float = 0.85, num_perm: int = 128):
        """
        Initialize similarity index

        Args:
            similarity_threshold: Minimum similarity to consider a match (0.0-1.0)
            num_perm: Number of permutations for MinHash (higher = more accurate, slower)
        """
        if not MINHASH_AVAILABLE:
            raise ImportError("datasketch required for similarity caching")

        self.similarity_threshold = similarity_threshold
        self.num_perm = num_perm
        self.lsh = MinHashLSH(threshold=similarity_threshold, num_perm=num_perm)
        self.minhashes: Dict[str, MinHash] = {}
        self._lock = RLock()

    def _create_minhash(self, text: str) -> MinHash:
        """Create MinHash signature from text"""
        m = MinHash(num_perm=self.num_perm)

        # Tokenize text (simple word-based tokenization)
        words = text.lower().split()

        # Also include character n-grams for better similarity detection
        for word in words:
            m.update(word.encode("utf-8"))
            # Add character trigrams
            for i in range(len(word) - 2):
                trigram = word[i : i + 3]
                m.update(trigram.encode("utf-8"))

        return m

    def add(self, cache_key: str, text: str) -> None:
        """
        Add text to similarity index

        Args:
            cache_key: Unique identifier for this text
            text: Text content to index
        """
        with self._lock:
            minhash = self._create_minhash(text)
            self.lsh.insert(cache_key, minhash)
            self.minhashes[cache_key] = minhash

    def find_similar(self, text: str) -> Optional[str]:
        """
        Find similar text in index

        Args:
            text: Text to search for

        Returns:
            Cache key of similar text, or None if no match found
        """
        with self._lock:
            if not self.minhashes:
                return None

            query_minhash = self._create_minhash(text)
            candidates = self.lsh.query(query_minhash)

            # Return first candidate (LSH already filtered by threshold)
            if candidates:
                return candidates[0]

            return None

    def remove(self, cache_key: str) -> None:
        """Remove entry from index"""
        with self._lock:
            if cache_key in self.minhashes:
                # Note: MinHashLSH doesn't support removal, so we just remove from our dict
                # This is a known limitation - index will accumulate stale entries
                # In production, you'd periodically rebuild the index
                del self.minhashes[cache_key]

    def size(self) -> int:
        """Get number of entries in index"""
        with self._lock:
            return len(self.minhashes)


class EnhancedResponseCache:
    """
    Two-tier response cache with exact and similarity matching

    Features:
    - Level 1: Exact match using SHA256 hash (fast, 100% accuracy)
    - Level 2: Similarity match using MinHash/LSH (approximate, catches similar prompts)
    - Statistics tracking for performance monitoring
    - Thread-safe operations
    - Configurable similarity threshold
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl_seconds: int = 86400,
        enable_similarity: bool = True,
        similarity_threshold: float = 0.85,
        max_index_size: int = 1000,
    ):
        """
        Initialize enhanced cache

        Args:
            cache_dir: Directory for cache files (default: .cache/api_responses)
            ttl_seconds: Time to live for cache entries (default: 24 hours)
            enable_similarity: Enable similarity matching (default: True)
            similarity_threshold: Minimum similarity for approximate match (default: 0.85)
            max_index_size: Maximum entries in similarity index (default: 1000)
        """
        # Initialize exact match cache (Level 1)
        self.exact_cache = ResponseCache(cache_dir=cache_dir, ttl_seconds=ttl_seconds)

        # Initialize similarity index (Level 2)
        self.enable_similarity = enable_similarity and MINHASH_AVAILABLE
        self.max_index_size = max_index_size

        if self.enable_similarity:
            try:
                self.similarity_index = SimilarityIndex(
                    similarity_threshold=similarity_threshold, num_perm=128
                )
            except ImportError:
                logger.warning(
                    "Failed to initialize similarity index - falling back to exact match only"
                )
                self.enable_similarity = False

        # Initialize statistics
        self.stats = CacheStatistics()

        logger.info(
            f"Enhanced response cache initialized "
            f"(similarity={'enabled' if self.enable_similarity else 'disabled'}, "
            f"threshold={similarity_threshold}, ttl={ttl_seconds}s)"
        )

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate of tokens in text (1 token ≈ 4 characters)"""
        return len(text) // 4

    def _create_prompt_text(self, messages: List[Dict], system: str) -> str:
        """Create combined text from messages and system prompt for similarity matching"""
        parts = [system]
        for msg in messages:
            if isinstance(msg, dict) and "content" in msg:
                parts.append(msg["content"])
        return "\n".join(parts)

    def get(
        self, messages: List[Dict], system: str, temperature: float
    ) -> Optional[Tuple[str, str]]:
        """
        Get cached response if available

        Args:
            messages: List of message dictionaries
            system: System prompt
            temperature: Temperature setting

        Returns:
            Tuple of (response, cache_type) where cache_type is 'exact' or 'similarity'
            Returns None if no cached response found
        """
        # Level 1: Try exact match first
        exact_response = self.exact_cache.get(messages, system, temperature)
        if exact_response:
            estimated_tokens = self._estimate_tokens(exact_response)
            self.stats.record_exact_hit(estimated_tokens)
            logger.debug(
                f"Cache HIT (exact) - saved ~{estimated_tokens} tokens "
                f"(hit rate: {self.stats.get_stats()['hit_rate']:.1%})"
            )
            return (exact_response, "exact")

        # Level 2: Try similarity match if enabled
        if self.enable_similarity:
            prompt_text = self._create_prompt_text(messages, system)
            similar_key = self.similarity_index.find_similar(prompt_text)

            if similar_key:
                # Try to load the similar response from disk
                # We need to reconstruct the cache path from the key
                cache_path = self.exact_cache.cache_dir / f"{similar_key}.json"
                if cache_path.exists():
                    try:
                        with open(cache_path, "r", encoding="utf-8") as f:
                            cache_data = json.load(f)

                        # Check TTL
                        if time.time() - cache_data["timestamp"] <= self.exact_cache.ttl_seconds:
                            response = cache_data["response"]
                            estimated_tokens = self._estimate_tokens(response)
                            self.stats.record_similarity_hit(estimated_tokens)
                            logger.debug(
                                f"Cache HIT (similarity) - saved ~{estimated_tokens} tokens "
                                f"(hit rate: {self.stats.get_stats()['hit_rate']:.1%})"
                            )
                            return (response, "similarity")
                    except (json.JSONDecodeError, KeyError, IOError) as e:
                        logger.warning(f"Failed to load similar cache entry: {e}")

        # Cache miss
        self.stats.record_miss()
        logger.debug(f"Cache MISS (hit rate: {self.stats.get_stats()['hit_rate']:.1%})")
        return None

    def put(self, messages: List[Dict], system: str, temperature: float, response: str) -> None:
        """
        Cache API response

        Args:
            messages: List of message dictionaries
            system: System prompt
            temperature: Temperature setting
            response: API response to cache
        """
        # Store in exact match cache
        self.exact_cache.put(messages, system, temperature, response)

        # Add to similarity index if enabled
        if self.enable_similarity:
            # Check index size limit
            if self.similarity_index.size() >= self.max_index_size:
                logger.warning(
                    f"Similarity index at max size ({self.max_index_size}), "
                    "skipping index update. Consider periodic index rebuild."
                )
                return

            # Get cache key for this entry
            cache_key = self.exact_cache._get_cache_key(messages, system, temperature)
            prompt_text = self._create_prompt_text(messages, system)

            try:
                self.similarity_index.add(cache_key, prompt_text)
                logger.debug(f"Added to similarity index (size: {self.similarity_index.size()})")
            except Exception as e:
                logger.warning(f"Failed to add to similarity index: {e}")

    def clear(self) -> None:
        """Clear all cached responses and reset statistics"""
        self.exact_cache.clear()
        if self.enable_similarity:
            # Rebuild similarity index
            self.similarity_index = SimilarityIndex(
                similarity_threshold=self.similarity_index.similarity_threshold,
                num_perm=self.similarity_index.num_perm,
            )
        self.stats.reset()
        logger.info("Enhanced response cache cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache performance statistics

        Returns:
            Dictionary with detailed statistics
        """
        stats = self.stats.get_stats()
        stats["similarity_enabled"] = self.enable_similarity
        if self.enable_similarity:
            stats["similarity_index_size"] = self.similarity_index.size()
            stats["similarity_index_max_size"] = self.max_index_size
        return stats


# Global cache instance
_global_enhanced_cache: Optional[EnhancedResponseCache] = None


def get_enhanced_cache(
    cache_dir: Optional[Path] = None,
    ttl_seconds: int = 86400,
    enable_similarity: bool = True,
    similarity_threshold: float = 0.85,
    max_index_size: int = 1000,
) -> EnhancedResponseCache:
    """
    Get or create global enhanced cache instance

    Args:
        cache_dir: Cache directory (only used on first call)
        ttl_seconds: TTL in seconds (only used on first call)
        enable_similarity: Enable similarity matching (only used on first call)
        similarity_threshold: Similarity threshold (only used on first call)
        max_index_size: Max index size (only used on first call)

    Returns:
        Global EnhancedResponseCache instance
    """
    global _global_enhanced_cache

    if _global_enhanced_cache is None:
        _global_enhanced_cache = EnhancedResponseCache(
            cache_dir=cache_dir,
            ttl_seconds=ttl_seconds,
            enable_similarity=enable_similarity,
            similarity_threshold=similarity_threshold,
            max_index_size=max_index_size,
        )

    return _global_enhanced_cache
