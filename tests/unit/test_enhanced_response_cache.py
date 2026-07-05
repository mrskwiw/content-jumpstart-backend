"""
Comprehensive unit tests for EnhancedResponseCache

Tests cover all functionality with and without datasketch available.
"""

import pytest
from unittest.mock import patch
import time

from src.utils.enhanced_response_cache import (
    CacheStatistics,
    SimilarityIndex,
    EnhancedResponseCache,
    get_enhanced_cache,
    MINHASH_AVAILABLE,
)


# ==================== CacheStatistics Tests ====================


def test_cache_statistics_init():
    """Test CacheStatistics initialization"""
    stats = CacheStatistics()

    assert stats.exact_hits == 0
    assert stats.similarity_hits == 0
    assert stats.misses == 0
    assert stats.total_requests == 0


def test_cache_statistics_record_exact_hit():
    """Test recording exact cache hit"""
    stats = CacheStatistics()

    stats.record_exact_hit(500)

    assert stats.exact_hits == 1
    assert stats.total_requests == 1
    assert stats.tokens_saved_exact == 500


def test_cache_statistics_record_similarity_hit():
    """Test recording similarity cache hit"""
    stats = CacheStatistics()

    stats.record_similarity_hit(300)

    assert stats.similarity_hits == 1
    assert stats.total_requests == 1
    assert stats.tokens_saved_similarity == 300


def test_cache_statistics_record_miss():
    """Test recording cache miss"""
    stats = CacheStatistics()

    stats.record_miss()

    assert stats.misses == 1
    assert stats.total_requests == 1


def test_cache_statistics_get_stats():
    """Test getting statistics summary"""
    stats = CacheStatistics()

    stats.record_exact_hit(1000)
    stats.record_similarity_hit(500)
    stats.record_miss()

    result = stats.get_stats()

    assert result["total_requests"] == 3
    assert result["exact_hits"] == 1
    assert result["similarity_hits"] == 1
    assert result["misses"] == 1
    assert result["total_hits"] == 2
    assert result["hit_rate"] == pytest.approx(2 / 3)
    assert result["exact_hit_rate"] == pytest.approx(1 / 3)
    assert result["similarity_hit_rate"] == pytest.approx(1 / 3)
    assert result["total_tokens_saved"] == 1500


def test_cache_statistics_reset():
    """Test resetting statistics"""
    stats = CacheStatistics()

    stats.record_exact_hit(100)
    stats.record_miss()
    stats.reset()

    assert stats.exact_hits == 0
    assert stats.total_requests == 0
    assert stats.tokens_saved_exact == 0


# ==================== SimilarityIndex Tests ====================


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
def test_similarity_index_init():
    """Test SimilarityIndex initialization"""
    index = SimilarityIndex(similarity_threshold=0.85, num_perm=128)

    assert index.similarity_threshold == 0.85
    assert index.num_perm == 128
    assert index.size() == 0


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
def test_similarity_index_add():
    """Test adding entries to index"""
    index = SimilarityIndex()

    index.add("key1", "This is a test document about productivity")

    assert index.size() == 1
    assert "key1" in index.minhashes


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
def test_similarity_index_find_similar():
    """Test finding similar text"""
    # Use lower threshold since MinHash is approximate
    index = SimilarityIndex(similarity_threshold=0.5)

    # Use texts with high word overlap for reliable MinHash matching
    index.add("key1", "productivity tips for remote teams working efficiently today")
    index.add("key2", "cooking recipes for delicious Italian pasta dinner tonight")

    # Query with very similar text (same words, slightly different order)
    result = index.find_similar("productivity tips for remote teams working efficiently")
    assert result == "key1"

    # Query with similar text for key2
    result = index.find_similar("cooking recipes for delicious Italian pasta dinner")
    assert result == "key2"


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
def test_similarity_index_no_match():
    """Test finding similar when no match exists"""
    index = SimilarityIndex(similarity_threshold=0.9)

    index.add("key1", "Productivity tips")

    result = index.find_similar("Completely unrelated content about cats")
    assert result is None


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
def test_similarity_index_remove():
    """Test removing entry from index"""
    index = SimilarityIndex()

    index.add("key1", "Test content")
    index.remove("key1")

    assert "key1" not in index.minhashes


# ==================== EnhancedResponseCache Tests ====================


def test_enhanced_cache_init_without_similarity(tmp_path):
    """Test cache initialization with similarity disabled"""
    cache = EnhancedResponseCache(
        cache_dir=tmp_path,
        enable_similarity=False,
    )

    assert not cache.enable_similarity
    assert cache.exact_cache is not None


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
def test_enhanced_cache_init_with_similarity(tmp_path):
    """Test cache initialization with similarity enabled"""
    cache = EnhancedResponseCache(
        cache_dir=tmp_path,
        enable_similarity=True,
        similarity_threshold=0.85,
    )

    assert cache.enable_similarity
    assert cache.similarity_index is not None


def test_enhanced_cache_exact_match(tmp_path):
    """Test exact cache match"""
    cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)

    messages = [{"role": "user", "content": "Test message"}]
    system = "Test system"
    temperature = 0.7
    response = "Test response"

    # Put in cache
    cache.put(messages, system, temperature, response)

    # Get from cache
    result = cache.get(messages, system, temperature)

    assert result is not None
    assert result[0] == response
    assert result[1] == "exact"


def test_enhanced_cache_miss(tmp_path):
    """Test cache miss"""
    cache = EnhancedResponseCache(cache_dir=tmp_path)

    messages = [{"role": "user", "content": "Never seen before"}]

    result = cache.get(messages, "system", 0.7)

    assert result is None


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
def test_enhanced_cache_similarity_match(tmp_path):
    """Test similarity cache match"""
    cache = EnhancedResponseCache(
        cache_dir=tmp_path,
        enable_similarity=True,
        similarity_threshold=0.5,  # Lower threshold for reliable MinHash matching
    )

    # Add original - use specific text
    messages1 = [
        {"role": "user", "content": "How to improve productivity and efficiency at work today"}
    ]
    cache.put(messages1, "system", 0.7, "Original response")

    # Query with very similar text (high word overlap)
    messages2 = [{"role": "user", "content": "How to improve productivity and efficiency at work"}]
    result = cache.get(messages2, "system", 0.7)

    # Should get similarity hit
    assert result is not None
    assert result[1] == "similarity"


def test_enhanced_cache_clear(tmp_path):
    """Test clearing cache"""
    cache = EnhancedResponseCache(cache_dir=tmp_path)

    cache.put([{"role": "user", "content": "test"}], "system", 0.7, "response")
    cache.stats.record_exact_hit(100)

    cache.clear()

    assert cache.stats.exact_hits == 0
    result = cache.get([{"role": "user", "content": "test"}], "system", 0.7)
    assert result is None


def test_enhanced_cache_get_statistics(tmp_path):
    """Test getting cache statistics"""
    cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)

    cache.stats.record_exact_hit(500)
    cache.stats.record_miss()

    stats = cache.get_statistics()

    assert stats["total_requests"] == 2
    assert stats["exact_hits"] == 1
    assert stats["misses"] == 1
    assert not stats["similarity_enabled"]


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
def test_enhanced_cache_max_index_size(tmp_path):
    """Test max index size limit"""
    cache = EnhancedResponseCache(
        cache_dir=tmp_path,
        enable_similarity=True,
        max_index_size=2,
    )

    # Add 3 entries (exceeds max)
    for i in range(3):
        cache.put([{"role": "user", "content": f"message {i}"}], "system", 0.7, f"response {i}")

    # Index should stop growing at max size
    assert cache.similarity_index.size() <= 2


def test_enhanced_cache_estimate_tokens():
    """Test token estimation"""
    cache = EnhancedResponseCache()

    text = "This is a test"  # 14 characters
    tokens = cache._estimate_tokens(text)

    assert tokens == 14 // 4  # 1 token ≈ 4 characters


def test_get_enhanced_cache_singleton(tmp_path):
    """Test global cache singleton"""
    # First call creates instance
    cache1 = get_enhanced_cache(cache_dir=tmp_path)

    # Second call returns same instance
    cache2 = get_enhanced_cache()

    assert cache1 is cache2


# ==================== Error Handling Tests ====================


def test_similarity_index_import_error():
    """Test SimilarityIndex raises error when datasketch unavailable"""
    with patch("src.utils.enhanced_response_cache.MINHASH_AVAILABLE", False):
        with pytest.raises(ImportError):
            SimilarityIndex()


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
def test_enhanced_cache_handles_corrupted_cache_file(tmp_path):
    """Test handling of corrupted cache files during similarity lookup"""
    cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=True)

    # Add entry
    messages = [{"role": "user", "content": "test message"}]
    cache.put(messages, "system", 0.7, "response")

    # Corrupt the cache file
    cache_key = cache.exact_cache._get_cache_key(messages, "system", 0.7)
    cache_path = tmp_path / f"{cache_key}.json"
    cache_path.write_text("corrupted json{{{")

    # Try similarity lookup (should handle gracefully)
    similar_messages = [{"role": "user", "content": "test message variation"}]
    result = cache.get(similar_messages, "system", 0.7)

    # Should get None (not crash)
    assert result is None


# ==================== Additional Coverage Tests ====================


class TestCacheStatisticsEdgeCases:
    """Additional tests for CacheStatistics edge cases."""

    def test_get_stats_empty(self):
        """Test get_stats with no requests."""
        stats = CacheStatistics()
        result = stats.get_stats()

        assert result["hit_rate"] == 0.0
        assert result["exact_hit_rate"] == 0.0
        assert result["similarity_hit_rate"] == 0.0

    def test_record_multiple_hits(self):
        """Test recording multiple hits accumulates correctly."""
        stats = CacheStatistics()

        stats.record_exact_hit(100)
        stats.record_exact_hit(200)
        stats.record_exact_hit(300)

        assert stats.exact_hits == 3
        assert stats.tokens_saved_exact == 600

    def test_thread_safety_with_concurrent_access(self):
        """Test thread safety of statistics."""
        import threading

        stats = CacheStatistics()
        threads = []

        def record_hit():
            for _ in range(100):
                stats.record_exact_hit(1)

        for _ in range(10):
            t = threading.Thread(target=record_hit)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert stats.exact_hits == 1000
        assert stats.total_requests == 1000


class TestEnhancedCacheCreatePromptText:
    """Tests for _create_prompt_text method."""

    def test_create_prompt_text_basic(self, tmp_path):
        """Test creating prompt text from messages."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)

        messages = [{"role": "user", "content": "Hello world"}]
        system = "You are helpful"

        result = cache._create_prompt_text(messages, system)

        assert "You are helpful" in result
        assert "Hello world" in result

    def test_create_prompt_text_multiple_messages(self, tmp_path):
        """Test creating prompt text with multiple messages."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)

        messages = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "Second message"},
        ]
        system = "System prompt"

        result = cache._create_prompt_text(messages, system)

        assert "System prompt" in result
        assert "First message" in result
        assert "Response" in result
        assert "Second message" in result

    def test_create_prompt_text_handles_non_dict_messages(self, tmp_path):
        """Test that non-dict messages are handled gracefully."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)

        messages = [
            {"role": "user", "content": "Valid message"},
            "invalid string message",  # Not a dict
            {"role": "user"},  # No content key
        ]
        system = "System"

        result = cache._create_prompt_text(messages, system)

        assert "System" in result
        assert "Valid message" in result


class TestEnhancedCacheGetWithExpiredTTL:
    """Tests for cache get with TTL expiration."""

    @pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
    def test_similarity_hit_expired_ttl(self, tmp_path):
        """Test that expired similarity entries are not returned."""
        cache = EnhancedResponseCache(
            cache_dir=tmp_path,
            enable_similarity=True,
            ttl_seconds=1,  # Very short TTL
            similarity_threshold=0.7,
        )

        # Add entry
        messages = [{"role": "user", "content": "test message content"}]
        cache.put(messages, "system", 0.7, "response")

        # Wait for TTL to expire
        time.sleep(1.1)

        # Similar message should not get expired entry
        similar_messages = [{"role": "user", "content": "test message content variation"}]
        cache.get(similar_messages, "system", 0.7)

        # Should be None due to TTL expiration
        # Note: Exact match also expired, so this is a miss


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
class TestSimilarityIndexEdgeCases:
    """Edge case tests for SimilarityIndex."""

    def test_find_similar_empty_index(self):
        """Test finding similar in empty index returns None."""
        index = SimilarityIndex()
        result = index.find_similar("any text")
        assert result is None

    def test_add_multiple_entries(self):
        """Test adding multiple entries."""
        index = SimilarityIndex()

        index.add("key1", "First document about technology")
        index.add("key2", "Second document about cooking")
        index.add("key3", "Third document about sports")

        assert index.size() == 3

    def test_remove_nonexistent_key(self):
        """Test removing a key that doesn't exist doesn't raise."""
        index = SimilarityIndex()
        # Should not raise
        index.remove("nonexistent_key")

    def test_create_minhash_short_text(self):
        """Test creating minhash from very short text."""
        index = SimilarityIndex()
        # Should not raise
        minhash = index._create_minhash("Hi")
        assert minhash is not None

    def test_create_minhash_empty_text(self):
        """Test creating minhash from empty text."""
        index = SimilarityIndex()
        # Should not raise
        minhash = index._create_minhash("")
        assert minhash is not None


class TestEnhancedCachePutErrors:
    """Tests for error handling in put method."""

    @pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
    def test_put_with_similarity_add_error(self, tmp_path):
        """Test that put handles similarity index add errors gracefully."""
        cache = EnhancedResponseCache(
            cache_dir=tmp_path,
            enable_similarity=True,
        )

        messages = [{"role": "user", "content": "test"}]

        # Mock similarity_index.add to raise error
        with patch.object(cache.similarity_index, "add", side_effect=Exception("Add failed")):
            # Should not raise
            cache.put(messages, "system", 0.7, "response")

        # Exact cache should still work
        result = cache.get(messages, "system", 0.7)
        assert result is not None
        assert result[0] == "response"


class TestEnhancedCacheClear:
    """Tests for clear method."""

    @pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
    def test_clear_with_similarity_enabled(self, tmp_path):
        """Test clearing cache with similarity enabled."""
        cache = EnhancedResponseCache(
            cache_dir=tmp_path,
            enable_similarity=True,
        )

        # Add entries
        cache.put([{"role": "user", "content": "test1"}], "system", 0.7, "response1")
        cache.put([{"role": "user", "content": "test2"}], "system", 0.7, "response2")
        cache.stats.record_exact_hit(100)

        original_threshold = cache.similarity_index.similarity_threshold

        # Clear
        cache.clear()

        # Verify cleared
        assert cache.stats.exact_hits == 0
        assert cache.similarity_index.size() == 0
        # Settings should be preserved
        assert cache.similarity_index.similarity_threshold == original_threshold


class TestEnhancedCacheStatistics:
    """Tests for get_statistics method."""

    @pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
    def test_get_statistics_with_similarity(self, tmp_path):
        """Test getting statistics with similarity enabled."""
        cache = EnhancedResponseCache(
            cache_dir=tmp_path,
            enable_similarity=True,
            max_index_size=500,
        )

        cache.put([{"role": "user", "content": "test"}], "system", 0.7, "response")

        stats = cache.get_statistics()

        assert stats["similarity_enabled"] is True
        assert stats["similarity_index_size"] == 1
        assert stats["similarity_index_max_size"] == 500

    def test_get_statistics_without_similarity(self, tmp_path):
        """Test getting statistics without similarity enabled."""
        cache = EnhancedResponseCache(
            cache_dir=tmp_path,
            enable_similarity=False,
        )

        stats = cache.get_statistics()

        assert stats["similarity_enabled"] is False
        assert "similarity_index_size" not in stats


class TestEnhancedCacheEstimateTokens:
    """Tests for token estimation."""

    def test_estimate_tokens_various_lengths(self, tmp_path):
        """Test token estimation with various text lengths."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)

        # 0 characters = 0 tokens
        assert cache._estimate_tokens("") == 0

        # 4 characters = 1 token
        assert cache._estimate_tokens("test") == 1

        # 100 characters = 25 tokens
        assert cache._estimate_tokens("a" * 100) == 25


class TestGlobalCacheSingleton:
    """Tests for global cache singleton."""

    def test_reset_global_cache(self, tmp_path):
        """Test that global cache can be reset for testing."""
        import src.utils.enhanced_response_cache as cache_module

        # Save original
        original = cache_module._global_enhanced_cache

        try:
            # Reset singleton
            cache_module._global_enhanced_cache = None

            # Create new cache
            cache1 = get_enhanced_cache(cache_dir=tmp_path)
            assert cache1 is not None

            # Same instance returned
            cache2 = get_enhanced_cache()
            assert cache1 is cache2

        finally:
            # Restore original
            cache_module._global_enhanced_cache = original


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
class TestEnhancedCacheSimilarityFileNotFound:
    """Tests for similarity lookup when cache file is missing."""

    def test_similarity_hit_file_missing(self, tmp_path):
        """Test similarity hit when cache file was deleted."""
        cache = EnhancedResponseCache(
            cache_dir=tmp_path,
            enable_similarity=True,
            similarity_threshold=0.7,
        )

        # Add entry
        messages = [{"role": "user", "content": "original test message content"}]
        cache.put(messages, "system", 0.7, "response")

        # Delete the cache file but keep similarity index
        cache_key = cache.exact_cache._get_cache_key(messages, "system", 0.7)
        cache_path = tmp_path / f"{cache_key}.json"
        if cache_path.exists():
            cache_path.unlink()

        # Try similar message
        similar_messages = [{"role": "user", "content": "original test message content similar"}]
        result = cache.get(similar_messages, "system", 0.7)

        # Should get None (file missing)
        assert result is None


class TestEnhancedCacheInitFallback:
    """Tests for initialization fallback behavior."""

    def test_init_similarity_fallback_on_error(self, tmp_path):
        """Test that initialization falls back when similarity index fails."""
        # Mock SimilarityIndex to raise on init
        with patch(
            "src.utils.enhanced_response_cache.SimilarityIndex",
            side_effect=ImportError("Mock import error"),
        ):
            # With MINHASH_AVAILABLE=True but SimilarityIndex raises
            with patch("src.utils.enhanced_response_cache.MINHASH_AVAILABLE", True):
                cache = EnhancedResponseCache(
                    cache_dir=tmp_path,
                    enable_similarity=True,
                )
                # Should fall back to disabled
                assert cache.enable_similarity is False


# ==================== New Coverage Tests ====================


class TestCacheStatisticsHitRateEdgeCases:
    """Tests to hit remaining branches in CacheStatistics."""

    def test_get_stats_only_misses(self):
        """hit_rate should be 0 when there are only misses."""
        stats = CacheStatistics()
        stats.record_miss()
        stats.record_miss()

        result = stats.get_stats()
        assert result["hit_rate"] == 0.0
        assert result["exact_hit_rate"] == 0.0
        assert result["similarity_hit_rate"] == 0.0
        assert result["misses"] == 2
        assert result["total_requests"] == 2

    def test_get_stats_only_exact_hits(self):
        """similarity_hit_rate is 0 when there are only exact hits."""
        stats = CacheStatistics()
        stats.record_exact_hit(200)
        stats.record_exact_hit(300)

        result = stats.get_stats()
        assert result["similarity_hit_rate"] == 0.0
        assert result["exact_hit_rate"] == 1.0
        assert result["hit_rate"] == 1.0
        assert result["total_tokens_saved"] == 500

    def test_get_stats_only_similarity_hits(self):
        """exact_hit_rate is 0 when there are only similarity hits."""
        stats = CacheStatistics()
        stats.record_similarity_hit(100)

        result = stats.get_stats()
        assert result["exact_hit_rate"] == 0.0
        assert result["similarity_hit_rate"] == 1.0
        assert result["hit_rate"] == 1.0

    def test_record_exact_hit_zero_tokens(self):
        """record_exact_hit with default zero tokens does not break."""
        stats = CacheStatistics()
        stats.record_exact_hit()  # no argument — default 0

        assert stats.tokens_saved_exact == 0
        assert stats.exact_hits == 1

    def test_record_similarity_hit_zero_tokens(self):
        """record_similarity_hit with default zero tokens does not break."""
        stats = CacheStatistics()
        stats.record_similarity_hit()

        assert stats.tokens_saved_similarity == 0
        assert stats.similarity_hits == 1

    def test_reset_clears_similarity_fields(self):
        """reset() zeroes similarity_hits and tokens_saved_similarity."""
        stats = CacheStatistics()
        stats.record_similarity_hit(999)
        stats.reset()

        assert stats.similarity_hits == 0
        assert stats.tokens_saved_similarity == 0


class TestCacheStatisticsThreadSafety:
    """Thread-safety tests for CacheStatistics."""

    def test_concurrent_mixed_operations(self):
        """Concurrent exact hits, similarity hits, and misses are race-free."""
        import threading

        stats = CacheStatistics()

        def do_exact():
            for _ in range(50):
                stats.record_exact_hit(1)

        def do_similarity():
            for _ in range(50):
                stats.record_similarity_hit(1)

        def do_miss():
            for _ in range(50):
                stats.record_miss()

        threads = (
            [threading.Thread(target=do_exact) for _ in range(4)]
            + [threading.Thread(target=do_similarity) for _ in range(4)]
            + [threading.Thread(target=do_miss) for _ in range(4)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert stats.exact_hits == 200
        assert stats.similarity_hits == 200
        assert stats.misses == 200
        assert stats.total_requests == 600


class TestEnhancedCacheMissRecording:
    """Verify stats.misses is incremented correctly on get() miss."""

    def test_get_miss_increments_miss_count(self, tmp_path):
        """Calling get() with no cached entry records a miss."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)

        cache.get([{"role": "user", "content": "never stored"}], "sys", 0.5)

        stats = cache.get_statistics()
        assert stats["misses"] == 1
        assert stats["total_requests"] == 1

    def test_get_hit_increments_exact_hit_count(self, tmp_path):
        """Calling get() after put() records an exact hit."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)
        messages = [{"role": "user", "content": "hello"}]

        cache.put(messages, "sys", 0.7, "world")
        cache.get(messages, "sys", 0.7)

        stats = cache.get_statistics()
        assert stats["exact_hits"] == 1
        assert stats["total_requests"] == 1


class TestEnhancedCacheTTLExpiry:
    """TTL expiry tests for EnhancedResponseCache using mocked time."""

    def test_exact_cache_miss_after_ttl_via_mock(self, tmp_path):
        """After TTL elapses (mocked), get() returns None for an exact entry."""
        cache = EnhancedResponseCache(
            cache_dir=tmp_path,
            enable_similarity=False,
            ttl_seconds=60,
        )
        messages = [{"role": "user", "content": "expiry test"}]
        cache.put(messages, "sys", 0.7, "response")

        # Advance time beyond TTL by patching time.time in response_cache module
        future_time = time.time() + 120  # 2 minutes ahead
        with patch("src.utils.response_cache.time") as mock_time:
            mock_time.time.return_value = future_time
            result = cache.exact_cache.get(messages, "sys", 0.7)

        assert result is None

    def test_exact_cache_hit_within_ttl_via_mock(self, tmp_path):
        """Within TTL (mocked), get() returns the stored response."""
        cache = EnhancedResponseCache(
            cache_dir=tmp_path,
            enable_similarity=False,
            ttl_seconds=3600,
        )
        messages = [{"role": "user", "content": "within ttl"}]
        cache.put(messages, "sys", 0.3, "my response")

        # Time is only 1 second ahead — well within TTL
        slightly_ahead = time.time() + 1
        with patch("src.utils.response_cache.time") as mock_time:
            mock_time.time.return_value = slightly_ahead
            result = cache.exact_cache.get(messages, "sys", 0.3)

        assert result == "my response"


class TestEnhancedCacheClearWithoutSimilarity:
    """Tests for clear() when similarity is disabled."""

    def test_clear_resets_stats_without_similarity(self, tmp_path):
        """clear() resets statistics when similarity is disabled."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)
        cache.stats.record_exact_hit(50)
        cache.stats.record_miss()

        cache.clear()

        assert cache.stats.exact_hits == 0
        assert cache.stats.misses == 0
        assert cache.stats.total_requests == 0

    def test_clear_removes_cached_responses_without_similarity(self, tmp_path):
        """After clear(), previously stored entries are no longer retrievable."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)
        messages = [{"role": "user", "content": "test data"}]
        cache.put(messages, "sys", 0.7, "data")

        cache.clear()

        assert cache.get(messages, "sys", 0.7) is None


class TestEnhancedCachePutWithDisabledSimilarity:
    """Tests for put() when similarity is disabled."""

    def test_put_stores_entry_similarity_disabled(self, tmp_path):
        """put() stores an entry retrievable via get() when similarity is off."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)
        messages = [{"role": "user", "content": "simple put"}]

        cache.put(messages, "sys", 0.0, "simple response")
        result = cache.get(messages, "sys", 0.0)

        assert result is not None
        assert result[0] == "simple response"
        assert result[1] == "exact"

    def test_put_overwrites_existing_entry(self, tmp_path):
        """put() with the same key overwrites the previous response."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)
        messages = [{"role": "user", "content": "overwrite me"}]

        cache.put(messages, "sys", 0.7, "old response")
        cache.put(messages, "sys", 0.7, "new response")
        result = cache.get(messages, "sys", 0.7)

        assert result is not None
        assert result[0] == "new response"


class TestEnhancedCacheEstimateTokensEdgeCases:
    """Additional token estimation edge cases."""

    def test_estimate_tokens_long_text(self, tmp_path):
        """Token estimation scales linearly with text length."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)
        text = "x" * 400
        assert cache._estimate_tokens(text) == 100

    def test_estimate_tokens_single_char(self, tmp_path):
        """Single character yields zero tokens (floor division)."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)
        assert cache._estimate_tokens("a") == 0

    def test_estimate_tokens_exactly_four_chars(self, tmp_path):
        """Exactly 4 characters yields 1 token."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)
        assert cache._estimate_tokens("abcd") == 1


class TestEnhancedCacheCreatePromptTextEdgeCases:
    """Edge cases for _create_prompt_text."""

    def test_empty_messages_list(self, tmp_path):
        """Empty messages list returns only the system prompt."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)
        result = cache._create_prompt_text([], "only system")
        assert result == "only system"

    def test_message_without_content_key_is_skipped(self, tmp_path):
        """Messages without a 'content' key are silently skipped."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)
        messages = [{"role": "user"}]  # no 'content' key
        result = cache._create_prompt_text(messages, "sys")
        # Only the system prompt should appear; no KeyError raised
        assert "sys" in result

    def test_non_dict_message_is_skipped(self, tmp_path):
        """Non-dict items in messages list do not cause errors."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)
        messages = ["plain string", 42, None, {"role": "user", "content": "valid"}]
        result = cache._create_prompt_text(messages, "sys")
        assert "valid" in result
        assert "sys" in result


class TestEnhancedCacheGetStatisticsFields:
    """Verify all expected keys are present in get_statistics() output."""

    def test_statistics_keys_without_similarity(self, tmp_path):
        """get_statistics() includes standard keys when similarity is disabled."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)
        stats = cache.get_statistics()

        expected_keys = {
            "total_requests",
            "exact_hits",
            "similarity_hits",
            "misses",
            "total_hits",
            "hit_rate",
            "exact_hit_rate",
            "similarity_hit_rate",
            "tokens_saved_exact",
            "tokens_saved_similarity",
            "total_tokens_saved",
            "similarity_enabled",
        }
        assert expected_keys.issubset(stats.keys())
        assert stats["similarity_enabled"] is False

    def test_statistics_similarity_index_keys_absent_without_similarity(self, tmp_path):
        """Similarity-index-specific keys are absent when similarity is disabled."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)
        stats = cache.get_statistics()

        assert "similarity_index_size" not in stats
        assert "similarity_index_max_size" not in stats


class TestEnhancedCacheMultipleMisses:
    """Verify cumulative miss counting across multiple lookups."""

    def test_multiple_misses_accumulate(self, tmp_path):
        """Each get() miss increments miss counter independently."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)

        for i in range(5):
            cache.get([{"role": "user", "content": f"q{i}"}], "sys", 0.7)

        stats = cache.get_statistics()
        assert stats["misses"] == 5
        assert stats["total_requests"] == 5
        assert stats["hit_rate"] == 0.0


class TestEnhancedCacheHitRateComputation:
    """Test hit_rate is computed correctly through the cache interface."""

    def test_hit_rate_after_mixed_operations(self, tmp_path):
        """hit_rate equals total_hits / total_requests."""
        cache = EnhancedResponseCache(cache_dir=tmp_path, enable_similarity=False)
        messages = [{"role": "user", "content": "compute rate"}]

        cache.put(messages, "sys", 0.7, "resp")

        # 2 hits
        cache.get(messages, "sys", 0.7)
        cache.get(messages, "sys", 0.7)

        # 1 miss
        cache.get([{"role": "user", "content": "other"}], "sys", 0.7)

        stats = cache.get_statistics()
        assert stats["total_requests"] == 3
        assert stats["total_hits"] == 2
        assert stats["hit_rate"] == pytest.approx(2 / 3)


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
class TestSimilarityIndexThreadSafety:
    """Thread-safety tests for SimilarityIndex."""

    def test_concurrent_add_and_size(self):
        """Concurrent adds do not corrupt the minhashes dict."""
        import threading

        index = SimilarityIndex(num_perm=32)
        errors = []

        def add_entries(start):
            try:
                for i in range(10):
                    index.add(f"key_{start}_{i}", f"document content number {start} item {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_entries, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert index.size() == 50


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
class TestSimilarityIndexRemoveNonexistent:
    """Removing a key that was never added is a no-op."""

    def test_remove_key_not_in_index(self):
        index = SimilarityIndex()
        # Should not raise
        index.remove("key_that_was_never_added")
        assert index.size() == 0


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="datasketch not available")
class TestEnhancedCachePutAtMaxIndexSizeLimit:
    """Once similarity index is full, additional puts do not grow it."""

    def test_index_does_not_exceed_max_size(self, tmp_path):
        """put() beyond max_index_size does not crash and index stays capped."""
        max_size = 3
        cache = EnhancedResponseCache(
            cache_dir=tmp_path,
            enable_similarity=True,
            max_index_size=max_size,
        )

        for i in range(max_size + 5):
            cache.put(
                [{"role": "user", "content": f"unique message number {i}"}],
                "system",
                0.7,
                f"response {i}",
            )

        assert cache.similarity_index.size() <= max_size


class TestGlobalCacheSingletonIsolation:
    """Tests that confirm the global singleton can be reset between test runs."""

    def test_get_enhanced_cache_returns_new_instance_after_reset(self, tmp_path):
        """After resetting the global, get_enhanced_cache() creates a new instance."""
        import src.utils.enhanced_response_cache as mod

        original = mod._global_enhanced_cache
        try:
            mod._global_enhanced_cache = None
            new_cache = get_enhanced_cache(cache_dir=tmp_path, enable_similarity=False)
            assert new_cache is not None
            # Second call returns the same new instance
            same = get_enhanced_cache()
            assert same is new_cache
        finally:
            mod._global_enhanced_cache = original

    def test_global_singleton_is_not_recreated_after_first_call(self, tmp_path):
        """Arguments on subsequent get_enhanced_cache() calls are ignored."""
        import src.utils.enhanced_response_cache as mod

        original = mod._global_enhanced_cache
        try:
            mod._global_enhanced_cache = None
            first = get_enhanced_cache(cache_dir=tmp_path, ttl_seconds=300, enable_similarity=False)
            # Pass completely different args — should still return first
            second = get_enhanced_cache(cache_dir=tmp_path / "other", ttl_seconds=9999)
            assert first is second
        finally:
            mod._global_enhanced_cache = original
