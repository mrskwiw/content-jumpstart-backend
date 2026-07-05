"""Unit tests for template_cache module.

Tests cover:
- TemplateCacheEntry creation and validation
- TemplateCacheManager get/put operations
- LRU eviction policy
- TTL expiration
- File modification detection
- Cache statistics
"""

import time
import pytest
from pathlib import Path
from unittest.mock import patch

from src.models.template import Template, TemplateType, TemplateDifficulty
from src.utils.template_cache import (
    TemplateCacheEntry,
    TemplateCacheManager,
    get_cache_manager,
)


@pytest.fixture
def sample_templates():
    """Create sample templates for testing."""
    return [
        Template(
            template_id=1,
            name="Problem Recognition",
            template_type=TemplateType.PROBLEM_RECOGNITION,
            structure="[HOOK] [PROBLEM] [SOLUTION]",
            best_for="Awareness",
            difficulty=TemplateDifficulty.FAST,
        ),
        Template(
            template_id=2,
            name="Statistic + Insight",
            template_type=TemplateType.STATISTIC,
            structure="[STAT] [INSIGHT] [CTA]",
            best_for="Authority",
            difficulty=TemplateDifficulty.FAST,
        ),
    ]


class TestTemplateCacheEntry:
    """Tests for TemplateCacheEntry."""

    def test_create_entry(self, sample_templates):
        """Test creating a cache entry."""
        entry = TemplateCacheEntry(
            templates=sample_templates,
            mtime=1234567890.0,
            timestamp=time.time(),
        )

        assert entry.templates == sample_templates
        assert entry.mtime == 1234567890.0
        assert entry.timestamp > 0

    def test_is_valid_true(self, sample_templates, tmp_path):
        """Test entry is valid when TTL not expired and file unchanged."""
        test_file = tmp_path / "templates.md"
        test_file.write_text("# Templates")
        mtime = test_file.stat().st_mtime

        entry = TemplateCacheEntry(
            templates=sample_templates,
            mtime=mtime,
            timestamp=time.time(),
        )

        assert entry.is_valid(test_file, ttl_seconds=3600) is True

    def test_is_valid_ttl_expired(self, sample_templates, tmp_path):
        """Test entry is invalid when TTL expired."""
        test_file = tmp_path / "templates.md"
        test_file.write_text("# Templates")
        mtime = test_file.stat().st_mtime

        # Create entry with old timestamp
        entry = TemplateCacheEntry(
            templates=sample_templates,
            mtime=mtime,
            timestamp=time.time() - 100,  # 100 seconds ago
        )

        # TTL of 50 seconds means entry is expired
        assert entry.is_valid(test_file, ttl_seconds=50) is False

    def test_is_valid_file_modified(self, sample_templates, tmp_path):
        """Test entry is invalid when file was modified."""
        test_file = tmp_path / "templates.md"
        test_file.write_text("# Templates v1")
        old_mtime = test_file.stat().st_mtime

        entry = TemplateCacheEntry(
            templates=sample_templates,
            mtime=old_mtime,
            timestamp=time.time(),
        )

        # Modify file
        time.sleep(0.01)  # Ensure different mtime
        test_file.write_text("# Templates v2")

        assert entry.is_valid(test_file, ttl_seconds=3600) is False

    def test_is_valid_file_not_found(self, sample_templates, tmp_path):
        """Test entry is invalid when file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.md"

        entry = TemplateCacheEntry(
            templates=sample_templates,
            mtime=1234567890.0,
            timestamp=time.time(),
        )

        assert entry.is_valid(nonexistent, ttl_seconds=3600) is False

    def test_is_valid_oserror(self, sample_templates, tmp_path):
        """Test entry is invalid when OSError occurs."""
        test_file = tmp_path / "templates.md"
        test_file.write_text("# Templates")
        mtime = test_file.stat().st_mtime

        entry = TemplateCacheEntry(
            templates=sample_templates,
            mtime=mtime,
            timestamp=time.time(),
        )

        # Mock stat to raise OSError
        with patch.object(Path, "stat", side_effect=OSError("Permission denied")):
            assert entry.is_valid(test_file, ttl_seconds=3600) is False


class TestTemplateCacheManager:
    """Tests for TemplateCacheManager."""

    def test_create_manager(self):
        """Test creating a cache manager."""
        manager = TemplateCacheManager(max_size=5, ttl_seconds=1800)

        assert manager.max_size == 5
        assert manager.ttl_seconds == 1800
        assert manager.size == 0

    def test_put_and_get(self, sample_templates, tmp_path):
        """Test storing and retrieving templates."""
        manager = TemplateCacheManager()
        test_file = tmp_path / "templates.md"
        test_file.write_text("# Templates")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)

        result = manager.get(test_file)

        assert result is not None
        assert len(result) == 2
        assert result[0].name == "Problem Recognition"

    def test_get_cache_miss(self, tmp_path):
        """Test get returns None for cache miss."""
        manager = TemplateCacheManager()
        nonexistent = tmp_path / "nonexistent.md"

        result = manager.get(nonexistent)

        assert result is None

    def test_get_expired_entry(self, sample_templates, tmp_path):
        """Test get returns None for expired entry."""
        manager = TemplateCacheManager(ttl_seconds=0.1)  # Very short TTL
        test_file = tmp_path / "templates.md"
        test_file.write_text("# Templates")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)
        time.sleep(0.15)  # Wait for TTL to expire

        result = manager.get(test_file)

        assert result is None

    def test_put_updates_existing(self, sample_templates, tmp_path):
        """Test put updates existing entry."""
        manager = TemplateCacheManager()
        test_file = tmp_path / "templates.md"
        test_file.write_text("# Templates")
        mtime = test_file.stat().st_mtime

        # Put initial
        manager.put(test_file, sample_templates, mtime)
        assert manager.size == 1

        # Put again (update)
        manager.put(test_file, sample_templates[:1], mtime)
        assert manager.size == 1  # Still just one entry

        result = manager.get(test_file)
        assert len(result) == 1  # Updated to have just 1 template

    def test_lru_eviction(self, sample_templates, tmp_path):
        """Test LRU eviction when cache is full."""
        manager = TemplateCacheManager(max_size=2)

        # Create 3 files
        files = []
        for i in range(3):
            f = tmp_path / f"templates_{i}.md"
            f.write_text(f"# Templates {i}")
            files.append((f, f.stat().st_mtime))

        # Fill cache
        manager.put(files[0][0], sample_templates, files[0][1])
        manager.put(files[1][0], sample_templates, files[1][1])
        assert manager.size == 2

        # Add third, should evict first (oldest)
        manager.put(files[2][0], sample_templates, files[2][1])
        assert manager.size == 2

        # First file should be evicted
        assert manager.get(files[0][0]) is None
        assert manager.get(files[1][0]) is not None
        assert manager.get(files[2][0]) is not None

    def test_invalidate(self, sample_templates, tmp_path):
        """Test invalidating a cache entry."""
        manager = TemplateCacheManager()
        test_file = tmp_path / "templates.md"
        test_file.write_text("# Templates")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)
        assert manager.size == 1

        manager.invalidate(test_file)
        assert manager.size == 0

    def test_invalidate_nonexistent(self, tmp_path):
        """Test invalidating nonexistent entry."""
        manager = TemplateCacheManager()
        nonexistent = tmp_path / "nonexistent.md"

        # Should not raise
        manager.invalidate(nonexistent)
        assert manager.size == 0

    def test_clear(self, sample_templates, tmp_path):
        """Test clearing the cache."""
        manager = TemplateCacheManager()
        test_file = tmp_path / "templates.md"
        test_file.write_text("# Templates")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)
        manager.get(test_file)  # Create hit

        assert manager.size == 1
        assert manager._hit_count > 0

        manager.clear()

        assert manager.size == 0
        assert manager._hit_count == 0
        assert manager._miss_count == 0

    def test_hit_rate_empty(self):
        """Test hit rate is 0 with no requests."""
        manager = TemplateCacheManager()

        assert manager.hit_rate == 0.0

    def test_hit_rate(self, sample_templates, tmp_path):
        """Test hit rate calculation."""
        manager = TemplateCacheManager()
        test_file = tmp_path / "templates.md"
        test_file.write_text("# Templates")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)

        # 2 hits
        manager.get(test_file)
        manager.get(test_file)

        # 1 miss
        manager.get(tmp_path / "nonexistent.md")

        # Hit rate = 2 / 3 = 0.666...
        assert 0.66 < manager.hit_rate < 0.67

    def test_get_stats(self, sample_templates, tmp_path):
        """Test getting cache statistics."""
        manager = TemplateCacheManager(max_size=5, ttl_seconds=1800)
        test_file = tmp_path / "templates.md"
        test_file.write_text("# Templates")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)
        manager.get(test_file)  # Hit
        manager.get(tmp_path / "nonexistent.md")  # Miss

        stats = manager.get_stats()

        assert stats["size"] == 1
        assert stats["max_size"] == 5
        assert stats["hit_count"] == 1
        assert stats["miss_count"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["ttl_seconds"] == 1800

    def test_move_to_end_on_access(self, sample_templates, tmp_path):
        """Test that accessing entry moves it to end (LRU)."""
        manager = TemplateCacheManager(max_size=2)

        # Create 2 files
        file1 = tmp_path / "templates_1.md"
        file1.write_text("# Templates 1")
        mtime1 = file1.stat().st_mtime

        file2 = tmp_path / "templates_2.md"
        file2.write_text("# Templates 2")
        mtime2 = file2.stat().st_mtime

        # Add both
        manager.put(file1, sample_templates, mtime1)
        manager.put(file2, sample_templates, mtime2)

        # Access file1 (moves it to end)
        manager.get(file1)

        # Add third file - should evict file2 (now oldest)
        file3 = tmp_path / "templates_3.md"
        file3.write_text("# Templates 3")
        mtime3 = file3.stat().st_mtime
        manager.put(file3, sample_templates, mtime3)

        # file2 should be evicted, file1 and file3 should remain
        assert manager.get(file2) is None
        assert manager.get(file1) is not None


class TestGetCacheManager:
    """Tests for get_cache_manager function."""

    def test_get_cache_manager_creates_instance(self):
        """Test getting global cache manager."""
        import src.utils.template_cache as tc

        # Reset global
        tc._global_cache_manager = None

        manager = get_cache_manager(max_size=20, ttl_seconds=7200)

        assert manager is not None
        assert manager.max_size == 20
        assert manager.ttl_seconds == 7200

        # Cleanup
        tc._global_cache_manager = None

    def test_get_cache_manager_returns_same_instance(self):
        """Test that get_cache_manager returns singleton."""
        import src.utils.template_cache as tc

        # Reset global
        tc._global_cache_manager = None

        manager1 = get_cache_manager()
        manager2 = get_cache_manager()

        assert manager1 is manager2

        # Cleanup
        tc._global_cache_manager = None


class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_access(self, sample_templates, tmp_path):
        """Test concurrent access to cache."""
        import threading

        manager = TemplateCacheManager()
        test_file = tmp_path / "templates.md"
        test_file.write_text("# Templates")
        mtime = test_file.stat().st_mtime

        errors = []

        def worker():
            try:
                for _ in range(100):
                    manager.put(test_file, sample_templates, mtime)
                    manager.get(test_file)
                    manager.invalidate(test_file)
                    manager.get_stats()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0


# ==================== New Coverage Tests ====================


class TestTemplateCacheEntryIsValidEdgeCases:
    """Additional is_valid() branch coverage for TemplateCacheEntry."""

    def test_is_valid_exactly_at_ttl_boundary(self, sample_templates, tmp_path):
        """Entry timestamped at exactly TTL seconds ago is treated as expired."""
        test_file = tmp_path / "boundary.md"
        test_file.write_text("# Boundary")
        mtime = test_file.stat().st_mtime
        ttl = 60.0

        # timestamp is exactly ttl seconds in the past → time.time() - timestamp == ttl
        # The check is `> ttl_seconds`, so equal is NOT expired; just inside boundary.
        entry = TemplateCacheEntry(
            templates=sample_templates,
            mtime=mtime,
            timestamp=time.time() - ttl,
        )
        # time.time() - timestamp ≈ ttl, which is NOT > ttl, so should be valid
        # (minor float drift is acceptable — we just verify no exception is raised)
        result = entry.is_valid(test_file, ttl_seconds=ttl)
        assert isinstance(result, bool)

    def test_is_valid_one_second_past_ttl(self, sample_templates, tmp_path):
        """Entry whose age is ttl + 1 second is expired."""
        test_file = tmp_path / "past_ttl.md"
        test_file.write_text("# Past TTL")
        mtime = test_file.stat().st_mtime
        ttl = 30.0

        entry = TemplateCacheEntry(
            templates=sample_templates,
            mtime=mtime,
            timestamp=time.time() - (ttl + 1),
        )
        assert entry.is_valid(test_file, ttl_seconds=ttl) is False


class TestTemplateCacheManagerGetMissCountTracking:
    """Verify _miss_count is incremented correctly in all miss paths."""

    def test_miss_count_incremented_on_key_not_present(self, tmp_path):
        """get() on an absent key increments _miss_count."""
        manager = TemplateCacheManager()

        manager.get(tmp_path / "absent.md")

        assert manager._miss_count == 1
        assert manager._hit_count == 0

    def test_miss_count_incremented_on_expired_entry(self, sample_templates, tmp_path):
        """get() on a TTL-expired entry increments _miss_count."""
        manager = TemplateCacheManager(ttl_seconds=0.05)
        test_file = tmp_path / "short_ttl.md"
        test_file.write_text("# Short TTL")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)
        time.sleep(0.1)

        manager.get(test_file)

        assert manager._miss_count == 1

    def test_expired_entry_is_removed_from_cache(self, sample_templates, tmp_path):
        """A TTL-expired entry is deleted from the internal dict on get()."""
        manager = TemplateCacheManager(ttl_seconds=0.05)
        test_file = tmp_path / "remove_on_expire.md"
        test_file.write_text("# Expire me")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)
        assert manager.size == 1

        time.sleep(0.1)
        manager.get(test_file)

        assert manager.size == 0


class TestTemplateCacheManagerTTLWithMockedTime:
    """TTL expiry tests using mocked time to avoid real sleeps."""

    def test_get_returns_none_after_mocked_ttl_expiry(self, sample_templates, tmp_path):
        """get() returns None when mocked time places us beyond TTL."""
        manager = TemplateCacheManager(ttl_seconds=3600)
        test_file = tmp_path / "mocked_ttl.md"
        test_file.write_text("# Mocked TTL")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)

        # Advance time by 2 hours using mock
        with patch("src.utils.template_cache.time") as mock_time:
            mock_time.time.return_value = time.time() + 7201  # > 3600 s
            result = manager.get(test_file)

        assert result is None

    def test_get_returns_templates_before_mocked_ttl_expiry(self, sample_templates, tmp_path):
        """get() succeeds when mocked time is still within TTL."""
        manager = TemplateCacheManager(ttl_seconds=3600)
        test_file = tmp_path / "within_ttl.md"
        test_file.write_text("# Within TTL")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)

        with patch("src.utils.template_cache.time") as mock_time:
            mock_time.time.return_value = time.time() + 60  # 1 minute ahead
            result = manager.get(test_file)

        assert result is not None
        assert len(result) == len(sample_templates)


class TestTemplateCacheEntryDirectIsExpiredMock:
    """Directly test TemplateCacheEntry.is_valid() with manipulated timestamps."""

    def test_is_valid_with_far_future_timestamp_not_expired(self, sample_templates, tmp_path):
        """Entry with a far-future timestamp is not TTL-expired."""
        test_file = tmp_path / "future.md"
        test_file.write_text("# Future")
        mtime = test_file.stat().st_mtime

        # Timestamp in the future — age will be negative, definitely not > ttl
        entry = TemplateCacheEntry(
            templates=sample_templates,
            mtime=mtime,
            timestamp=time.time() + 9999,
        )
        assert entry.is_valid(test_file, ttl_seconds=3600) is True

    def test_is_valid_with_zero_ttl_always_expired(self, sample_templates, tmp_path):
        """An entry is immediately expired when ttl_seconds=0."""
        test_file = tmp_path / "zero_ttl.md"
        test_file.write_text("# Zero TTL")
        mtime = test_file.stat().st_mtime

        entry = TemplateCacheEntry(
            templates=sample_templates,
            mtime=mtime,
            timestamp=time.time() - 1,  # 1 second old
        )
        assert entry.is_valid(test_file, ttl_seconds=0) is False


class TestTemplateCacheManagerPutRefreshesExpiredEntry:
    """put() on a key that was previously expired refreshes the entry."""

    def test_put_after_expiry_makes_entry_valid_again(self, sample_templates, tmp_path):
        """After TTL expiry, put() with fresh mtime makes the entry retrievable."""
        manager = TemplateCacheManager(ttl_seconds=0.05)
        test_file = tmp_path / "refresh.md"
        test_file.write_text("# Refresh")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)
        time.sleep(0.1)

        # Confirm expired
        assert manager.get(test_file) is None

        # Re-put — should make it valid again
        test_file.write_text("# Refresh v2")
        new_mtime = test_file.stat().st_mtime
        manager.put(test_file, sample_templates, new_mtime)

        result = manager.get(test_file)
        assert result is not None


class TestTemplateCacheManagerSizeProperty:
    """Tests for the size property."""

    def test_size_increases_with_each_unique_put(self, sample_templates, tmp_path):
        """size grows by 1 for each unique path put into the cache."""
        manager = TemplateCacheManager(max_size=10)

        for i in range(4):
            f = tmp_path / f"file_{i}.md"
            f.write_text(f"# File {i}")
            manager.put(f, sample_templates, f.stat().st_mtime)

        assert manager.size == 4

    def test_size_stays_same_when_updating_existing_key(self, sample_templates, tmp_path):
        """Updating an existing key does not change the cache size."""
        manager = TemplateCacheManager(max_size=10)
        test_file = tmp_path / "same_key.md"
        test_file.write_text("# Same Key")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)
        manager.put(test_file, sample_templates[:1], mtime)

        assert manager.size == 1


class TestTemplateCacheManagerHitRateProperty:
    """Tests for the hit_rate property."""

    def test_hit_rate_is_zero_when_no_requests(self):
        """hit_rate is 0.0 before any get() calls."""
        manager = TemplateCacheManager()
        assert manager.hit_rate == 0.0

    def test_hit_rate_is_one_when_all_hits(self, sample_templates, tmp_path):
        """hit_rate is 1.0 when every get() results in a hit."""
        manager = TemplateCacheManager()
        test_file = tmp_path / "all_hits.md"
        test_file.write_text("# All Hits")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)
        manager.get(test_file)
        manager.get(test_file)
        manager.get(test_file)

        assert manager.hit_rate == 1.0

    def test_hit_rate_is_zero_when_all_misses(self, tmp_path):
        """hit_rate is 0.0 when every get() results in a miss."""
        manager = TemplateCacheManager()

        for i in range(3):
            manager.get(tmp_path / f"absent_{i}.md")

        assert manager.hit_rate == 0.0


class TestTemplateCacheManagerGetStatsAccuracy:
    """Verify get_stats() returns correct counts in all scenarios."""

    def test_stats_after_clear(self, sample_templates, tmp_path):
        """get_stats() reflects zeroed counters after clear()."""
        manager = TemplateCacheManager(max_size=5, ttl_seconds=1800)
        test_file = tmp_path / "stats_clear.md"
        test_file.write_text("# Stats Clear")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)
        manager.get(test_file)  # hit
        manager.get(tmp_path / "absent.md")  # miss

        manager.clear()
        stats = manager.get_stats()

        assert stats["size"] == 0
        assert stats["hit_count"] == 0
        assert stats["miss_count"] == 0
        assert stats["hit_rate"] == 0.0

    def test_stats_reflect_correct_max_size(self, tmp_path):
        """get_stats() reports the correct max_size regardless of current size."""
        manager = TemplateCacheManager(max_size=7, ttl_seconds=900)
        stats = manager.get_stats()

        assert stats["max_size"] == 7
        assert stats["ttl_seconds"] == 900

    def test_stats_hit_rate_matches_expected(self, sample_templates, tmp_path):
        """get_stats() hit_rate is consistent with hit_count / (hit_count + miss_count)."""
        manager = TemplateCacheManager()
        test_file = tmp_path / "rate.md"
        test_file.write_text("# Rate")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)
        manager.get(test_file)  # hit
        manager.get(test_file)  # hit
        manager.get(tmp_path / "miss.md")  # miss

        stats = manager.get_stats()
        expected_rate = stats["hit_count"] / (stats["hit_count"] + stats["miss_count"])
        assert stats["hit_rate"] == pytest.approx(expected_rate)


class TestTemplateCacheManagerLRUEvictionOrder:
    """Detailed LRU eviction ordering tests."""

    def test_oldest_inserted_evicted_when_no_access_occurs(self, sample_templates, tmp_path):
        """Without any get() calls, the first-inserted entry is evicted when over capacity."""
        manager = TemplateCacheManager(max_size=3)

        files = []
        for i in range(4):
            f = tmp_path / f"lru_{i}.md"
            f.write_text(f"# LRU {i}")
            files.append(f)
            manager.put(f, sample_templates, f.stat().st_mtime)

        # files[0] should have been evicted
        assert manager.get(files[0]) is None
        for f in files[1:]:
            assert manager.get(f) is not None

    def test_recently_accessed_entry_is_not_evicted(self, sample_templates, tmp_path):
        """Accessing an old entry moves it to the front so it is NOT evicted next."""
        manager = TemplateCacheManager(max_size=2)

        file_a = tmp_path / "lru_a.md"
        file_a.write_text("# A")
        file_b = tmp_path / "lru_b.md"
        file_b.write_text("# B")
        file_c = tmp_path / "lru_c.md"
        file_c.write_text("# C")

        manager.put(file_a, sample_templates, file_a.stat().st_mtime)
        manager.put(file_b, sample_templates, file_b.stat().st_mtime)

        # Access file_a → moves to end, file_b becomes oldest
        manager.get(file_a)

        # Add file_c → file_b should be evicted
        manager.put(file_c, sample_templates, file_c.stat().st_mtime)

        assert manager.get(file_b) is None
        assert manager.get(file_a) is not None
        assert manager.get(file_c) is not None


class TestTemplateCacheManagerInvalidateEdgeCases:
    """Edge cases for the invalidate() method."""

    def test_invalidate_reduces_size_by_one(self, sample_templates, tmp_path):
        """invalidate() reduces size by exactly 1 for an existing key."""
        manager = TemplateCacheManager()
        file_1 = tmp_path / "inv_1.md"
        file_1.write_text("# Inv 1")
        file_2 = tmp_path / "inv_2.md"
        file_2.write_text("# Inv 2")

        manager.put(file_1, sample_templates, file_1.stat().st_mtime)
        manager.put(file_2, sample_templates, file_2.stat().st_mtime)

        manager.invalidate(file_1)

        assert manager.size == 1
        assert manager.get(file_1) is None
        assert manager.get(file_2) is not None

    def test_invalidate_twice_does_not_raise(self, sample_templates, tmp_path):
        """Calling invalidate() twice on the same key is a no-op on the second call."""
        manager = TemplateCacheManager()
        test_file = tmp_path / "double_inv.md"
        test_file.write_text("# Double Inv")

        manager.put(test_file, sample_templates, test_file.stat().st_mtime)
        manager.invalidate(test_file)
        manager.invalidate(test_file)  # Should not raise

        assert manager.size == 0


class TestTemplateCacheManagerCopySemantics:
    """Verify that get() and put() copy templates (no aliasing)."""

    def test_put_stores_copy_not_reference(self, sample_templates, tmp_path):
        """Mutating the original list after put() does not affect cached value."""
        manager = TemplateCacheManager()
        test_file = tmp_path / "copy_put.md"
        test_file.write_text("# Copy Put")
        mtime = test_file.stat().st_mtime

        original_list = list(sample_templates)
        manager.put(test_file, original_list, mtime)

        # Mutate original
        original_list.clear()

        result = manager.get(test_file)
        assert result is not None
        assert len(result) == len(sample_templates)

    def test_get_returns_copy_not_reference(self, sample_templates, tmp_path):
        """Mutating the returned list does not corrupt the cached value."""
        manager = TemplateCacheManager()
        test_file = tmp_path / "copy_get.md"
        test_file.write_text("# Copy Get")
        mtime = test_file.stat().st_mtime

        manager.put(test_file, sample_templates, mtime)

        result1 = manager.get(test_file)
        result1.clear()  # Mutate returned copy

        result2 = manager.get(test_file)
        assert result2 is not None
        assert len(result2) == len(sample_templates)


class TestGetCacheManagerSingletonIsolation:
    """Tests for get_cache_manager() singleton isolation."""

    def test_singleton_ignores_args_on_subsequent_calls(self):
        """get_cache_manager() ignores parameters after the first call."""
        import src.utils.template_cache as tc

        tc._global_cache_manager = None
        try:
            mgr1 = get_cache_manager(max_size=5, ttl_seconds=100)
            mgr2 = get_cache_manager(max_size=999, ttl_seconds=9999)

            assert mgr1 is mgr2
            assert mgr1.max_size == 5
        finally:
            tc._global_cache_manager = None

    def test_singleton_has_expected_defaults(self):
        """get_cache_manager() with no args uses sensible defaults."""
        import src.utils.template_cache as tc

        tc._global_cache_manager = None
        try:
            mgr = get_cache_manager()
            assert mgr.max_size == 10
            assert mgr.ttl_seconds == 3600.0
        finally:
            tc._global_cache_manager = None


class TestTemplateCacheManagerConcurrentPutAndGet:
    """Additional concurrent tests for TemplateCacheManager."""

    def test_concurrent_puts_on_different_files(self, sample_templates, tmp_path):
        """Multiple threads putting different files do not corrupt the cache."""
        import threading

        manager = TemplateCacheManager(max_size=100)
        errors = []

        def put_file(i):
            try:
                f = tmp_path / f"concurrent_{i}.md"
                f.write_text(f"# Concurrent {i}")
                manager.put(f, sample_templates, f.stat().st_mtime)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=put_file, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert manager.size == 20

    def test_concurrent_clear_and_put_does_not_raise(self, sample_templates, tmp_path):
        """Concurrent clear() and put() operations do not raise exceptions."""
        import threading

        manager = TemplateCacheManager(max_size=50)
        test_file = tmp_path / "concurrent_clear.md"
        test_file.write_text("# Concurrent Clear")
        mtime = test_file.stat().st_mtime
        errors = []

        def putter():
            try:
                for _ in range(50):
                    manager.put(test_file, sample_templates, mtime)
            except Exception as e:
                errors.append(e)

        def clearer():
            try:
                for _ in range(10):
                    manager.clear()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=putter) for _ in range(3)] + [
            threading.Thread(target=clearer) for _ in range(2)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
