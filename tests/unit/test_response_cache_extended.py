"""Extended unit tests for response_cache module.

Tests cover additional paths not covered by existing tests:
- Cache directory initialization edge cases
- get() method error handling
- get_stats() method with various states
- clear() method with files and errors
"""

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.response_cache import ResponseCache


class TestResponseCacheInit:
    """Tests for ResponseCache initialization."""

    def test_init_default_directory(self, tmp_path, monkeypatch):
        """Test default cache directory creation."""
        monkeypatch.chdir(tmp_path)

        cache = ResponseCache()

        assert cache.enabled is True

    def test_init_custom_directory(self, tmp_path):
        """Test custom cache directory."""
        custom_dir = tmp_path / "custom_cache"
        cache = ResponseCache(cache_dir=custom_dir)

        assert cache.cache_dir == custom_dir
        assert custom_dir.exists()

    def test_init_disabled(self, tmp_path):
        """Test cache disabled on init."""
        cache = ResponseCache(cache_dir=tmp_path, enabled=False)

        assert cache.enabled is False

    def test_init_creates_parent_directories(self, tmp_path):
        """Test that init creates nested directories."""
        nested_dir = tmp_path / "a" / "b" / "c" / "cache"
        cache = ResponseCache(cache_dir=nested_dir)

        assert nested_dir.exists()
        assert cache.enabled is True

    def test_init_permission_error_disables_cache(self, tmp_path, monkeypatch):
        """Test that permission error disables cache."""
        # Mock mkdir to raise PermissionError
        with patch.object(Path, "mkdir", side_effect=PermissionError("No access")):
            cache = ResponseCache(cache_dir=tmp_path / "new_dir")
            assert cache.enabled is False


class TestResponseCacheGet:
    """Tests for ResponseCache get() method."""

    def test_get_disabled_cache(self, tmp_path):
        """Test get returns None when cache disabled."""
        cache = ResponseCache(cache_dir=tmp_path, enabled=False)
        messages = [{"role": "user", "content": "test"}]

        result = cache.get(messages, "system", 0.7)

        assert result is None

    def test_get_cache_miss(self, tmp_path):
        """Test get returns None for cache miss."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "not cached"}]

        result = cache.get(messages, "system", 0.7)

        assert result is None

    def test_get_cache_hit(self, tmp_path):
        """Test get returns cached value."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "test"}]

        cache.put(messages, "system", 0.7, "cached response")
        result = cache.get(messages, "system", 0.7)

        assert result == "cached response"

    def test_get_expired_cache(self, tmp_path):
        """Test get returns None for expired cache."""
        cache = ResponseCache(cache_dir=tmp_path, ttl_seconds=1)
        messages = [{"role": "user", "content": "test"}]

        cache.put(messages, "system", 0.7, "cached response")
        time.sleep(1.1)

        result = cache.get(messages, "system", 0.7)

        assert result is None

    def test_get_invalid_json_removes_file(self, tmp_path):
        """Test that invalid JSON cache file is removed."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "test"}]

        # Create cache entry
        cache.put(messages, "system", 0.7, "response")
        key = cache._get_cache_key(messages, "system", 0.7)
        cache_file = cache.cache_dir / f"{key}.json"

        # Corrupt the file
        cache_file.write_text("not valid json{{{")

        result = cache.get(messages, "system", 0.7)

        assert result is None
        assert not cache_file.exists()  # File should be removed

    def test_get_missing_fields_removes_file(self, tmp_path):
        """Test that cache file with missing fields is removed."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "test"}]

        # Create cache entry
        cache.put(messages, "system", 0.7, "response")
        key = cache._get_cache_key(messages, "system", 0.7)
        cache_file = cache.cache_dir / f"{key}.json"

        # Write file without required fields
        cache_file.write_text('{"only_one_field": "value"}')

        result = cache.get(messages, "system", 0.7)

        assert result is None
        assert not cache_file.exists()

    def test_get_invalid_structure_removes_file(self, tmp_path):
        """Test that cache file with invalid structure is removed."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "test"}]

        # Create cache entry
        cache.put(messages, "system", 0.7, "response")
        key = cache._get_cache_key(messages, "system", 0.7)
        cache_file = cache.cache_dir / f"{key}.json"

        # Write array instead of dict
        cache_file.write_text("[1, 2, 3]")

        result = cache.get(messages, "system", 0.7)

        assert result is None
        assert not cache_file.exists()

    def test_get_handles_read_error(self, tmp_path):
        """Test get handles file read errors."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "test"}]

        # Create cache entry
        cache.put(messages, "system", 0.7, "response")

        # Mock open to raise an error
        with patch("builtins.open", side_effect=IOError("Read error")):
            result = cache.get(messages, "system", 0.7)

        assert result is None


class TestResponseCachePut:
    """Tests for ResponseCache put() method."""

    def test_put_disabled_cache(self, tmp_path):
        """Test put does nothing when cache disabled."""
        cache = ResponseCache(cache_dir=tmp_path, enabled=False)
        messages = [{"role": "user", "content": "test"}]

        cache.put(messages, "system", 0.7, "response")

        # No files should be created
        cache_files = list(tmp_path.glob("*.json"))
        assert len(cache_files) == 0

    def test_put_creates_cache_file(self, tmp_path):
        """Test put creates cache file."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "test"}]

        cache.put(messages, "system", 0.7, "response")

        cache_files = list(tmp_path.glob("*.json"))
        assert len(cache_files) == 1

    def test_put_handles_write_error(self, tmp_path):
        """Test put handles write errors gracefully."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "test"}]

        # Mock open to raise an error
        with patch("builtins.open", side_effect=IOError("Write error")):
            # Should not raise
            cache.put(messages, "system", 0.7, "response")


class TestResponseCacheClear:
    """Tests for ResponseCache clear() method."""

    def test_clear_removes_all_files(self, tmp_path):
        """Test clear removes all cache files."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Create multiple cache entries
        for i in range(3):
            messages = [{"role": "user", "content": f"test{i}"}]
            cache.put(messages, "system", 0.7, f"response{i}")

        assert len(list(tmp_path.glob("*.json"))) == 3

        cache.clear()

        assert len(list(tmp_path.glob("*.json"))) == 0

    def test_clear_disabled_cache(self, tmp_path):
        """Test clear does nothing when cache disabled."""
        cache = ResponseCache(cache_dir=tmp_path, enabled=True)
        messages = [{"role": "user", "content": "test"}]
        cache.put(messages, "system", 0.7, "response")

        cache.enabled = False
        cache.clear()

        # File should still exist
        assert len(list(tmp_path.glob("*.json"))) == 1

    def test_clear_nonexistent_directory(self, tmp_path):
        """Test clear handles nonexistent directory."""
        cache = ResponseCache(cache_dir=tmp_path / "subdir")

        # Remove directory
        cache.cache_dir.rmdir()

        # Should not raise
        cache.clear()

    def test_clear_handles_delete_error(self, tmp_path):
        """Test clear handles file delete errors."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "test"}]
        cache.put(messages, "system", 0.7, "response")

        # Mock unlink to raise an error
        with patch.object(Path, "unlink", side_effect=PermissionError("Cannot delete")):
            # Should not raise
            cache.clear()


class TestResponseCacheGetStats:
    """Tests for ResponseCache get_stats() method."""

    def test_get_stats_disabled_cache(self, tmp_path):
        """Test get_stats when cache disabled."""
        cache = ResponseCache(cache_dir=tmp_path, enabled=False)

        stats = cache.get_stats()

        assert stats["enabled"] is False
        assert stats["total_files"] == 0
        assert stats["total_size_bytes"] == 0

    def test_get_stats_empty_cache(self, tmp_path):
        """Test get_stats with empty cache."""
        cache = ResponseCache(cache_dir=tmp_path)

        stats = cache.get_stats()

        assert stats["enabled"] is True
        assert stats["total_files"] == 0
        assert stats["total_size_bytes"] == 0

    def test_get_stats_with_files(self, tmp_path):
        """Test get_stats with cached files."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Create multiple cache entries
        for i in range(3):
            messages = [{"role": "user", "content": f"test{i}"}]
            cache.put(messages, "system", 0.7, f"response{i}")

        stats = cache.get_stats()

        assert stats["enabled"] is True
        assert stats["total_files"] == 3
        assert stats["total_size_bytes"] > 0
        assert stats["total_size_mb"] > 0
        assert stats["oldest_timestamp"] is not None
        assert stats["newest_timestamp"] is not None

    def test_get_stats_nonexistent_directory(self, tmp_path):
        """Test get_stats when cache directory doesn't exist."""
        cache = ResponseCache(cache_dir=tmp_path / "subdir")

        # Remove directory
        cache.cache_dir.rmdir()

        stats = cache.get_stats()

        assert stats["enabled"] is False
        assert stats["total_files"] == 0

    def test_get_stats_handles_corrupted_files(self, tmp_path):
        """Test get_stats handles corrupted cache files."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Create valid cache entry
        messages = [{"role": "user", "content": "test"}]
        cache.put(messages, "system", 0.7, "response")

        # Create corrupted file
        (tmp_path / "corrupted.json").write_text("not valid json")

        # Should not raise
        stats = cache.get_stats()

        assert stats["total_files"] == 2  # Both files counted
        assert stats["oldest_timestamp"] is not None  # Only valid file has timestamp


class TestResponseCacheKey:
    """Tests for cache key generation."""

    def test_same_content_same_key(self, tmp_path):
        """Test that identical content produces identical keys."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "test"}]

        key1 = cache._get_cache_key(messages, "system", 0.7)
        key2 = cache._get_cache_key(messages, "system", 0.7)

        assert key1 == key2

    def test_different_messages_different_key(self, tmp_path):
        """Test that different messages produce different keys."""
        cache = ResponseCache(cache_dir=tmp_path)

        key1 = cache._get_cache_key([{"role": "user", "content": "a"}], "system", 0.7)
        key2 = cache._get_cache_key([{"role": "user", "content": "b"}], "system", 0.7)

        assert key1 != key2

    def test_different_system_different_key(self, tmp_path):
        """Test that different system prompts produce different keys."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "test"}]

        key1 = cache._get_cache_key(messages, "system1", 0.7)
        key2 = cache._get_cache_key(messages, "system2", 0.7)

        assert key1 != key2

    def test_different_temperature_different_key(self, tmp_path):
        """Test that different temperatures produce different keys."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "test"}]

        key1 = cache._get_cache_key(messages, "system", 0.7)
        key2 = cache._get_cache_key(messages, "system", 0.8)

        assert key1 != key2

    def test_key_is_valid_hex(self, tmp_path):
        """Test that cache key is valid hex string."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "test"}]

        key = cache._get_cache_key(messages, "system", 0.7)

        # Should be 64 character hex string (SHA-256)
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


# ==================== New Coverage Tests ====================


class TestResponseCacheKeyGenerationConsistency:
    """Cache key generation consistency and uniqueness tests."""

    def test_key_is_deterministic_across_instances(self, tmp_path):
        """Two separate ResponseCache instances produce the same key for identical input."""
        cache_a = ResponseCache(cache_dir=tmp_path / "a")
        cache_b = ResponseCache(cache_dir=tmp_path / "b")
        messages = [{"role": "user", "content": "same input"}]

        key_a = cache_a._get_cache_key(messages, "system", 0.5)
        key_b = cache_b._get_cache_key(messages, "system", 0.5)

        assert key_a == key_b

    def test_key_differs_for_empty_vs_nonempty_messages(self, tmp_path):
        """Empty message list and a non-empty list produce different keys."""
        cache = ResponseCache(cache_dir=tmp_path)

        key_empty = cache._get_cache_key([], "system", 0.7)
        key_nonempty = cache._get_cache_key([{"role": "user", "content": "hi"}], "system", 0.7)

        assert key_empty != key_nonempty

    def test_key_differs_for_zero_vs_nonzero_temperature(self, tmp_path):
        """temperature=0 and temperature=0.0001 produce different keys."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "temp test"}]

        key_zero = cache._get_cache_key(messages, "sys", 0.0)
        key_tiny = cache._get_cache_key(messages, "sys", 0.0001)

        assert key_zero != key_tiny

    def test_key_insensitive_to_dict_insertion_order(self, tmp_path):
        """Keys with same data but different dict ordering produce the same key."""
        cache = ResponseCache(cache_dir=tmp_path)

        messages_ab = [{"role": "user", "content": "hello"}]
        messages_ba = [{"content": "hello", "role": "user"}]

        key_ab = cache._get_cache_key(messages_ab, "sys", 0.7)
        key_ba = cache._get_cache_key(messages_ba, "sys", 0.7)

        # JSON sort_keys=True ensures order independence
        assert key_ab == key_ba

    def test_key_for_empty_system_differs_from_nonempty(self, tmp_path):
        """Empty system prompt and a non-empty one produce different keys."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "x"}]

        key_empty_sys = cache._get_cache_key(messages, "", 0.7)
        key_sys = cache._get_cache_key(messages, "you are helpful", 0.7)

        assert key_empty_sys != key_sys


class TestResponseCacheGetByKey:
    """Tests for get_by_key() and put_by_key() methods."""

    def test_put_by_key_then_get_by_key_returns_data(self, tmp_path):
        """put_by_key() followed by get_by_key() returns the original data."""
        cache = ResponseCache(cache_dir=tmp_path)
        cache.put_by_key("abc123", {"value": 42, "label": "hello"})

        result = cache.get_by_key("abc123")

        assert result == {"value": 42, "label": "hello"}

    def test_get_by_key_returns_none_for_missing_key(self, tmp_path):
        """get_by_key() returns None when the key was never stored."""
        cache = ResponseCache(cache_dir=tmp_path)

        assert cache.get_by_key("never_stored") is None

    def test_get_by_key_returns_none_when_disabled(self, tmp_path):
        """get_by_key() returns None when the cache is disabled."""
        cache = ResponseCache(cache_dir=tmp_path, enabled=False)

        assert cache.get_by_key("any_key") is None

    def test_put_by_key_does_nothing_when_disabled(self, tmp_path):
        """put_by_key() is a no-op when the cache is disabled."""
        cache = ResponseCache(cache_dir=tmp_path, enabled=False)
        cache.put_by_key("key1", "value1")

        # Enabling manually to confirm nothing was written
        cache.enabled = True
        assert cache.get_by_key("key1") is None

    def test_get_by_key_returns_none_after_ttl_expiry(self, tmp_path):
        """get_by_key() returns None after the TTL has elapsed."""
        cache = ResponseCache(cache_dir=tmp_path, ttl_seconds=1)
        cache.put_by_key("short_ttl_key", "data")

        time.sleep(1.1)

        assert cache.get_by_key("short_ttl_key") is None

    def test_get_by_key_returns_none_for_corrupted_file(self, tmp_path):
        """get_by_key() returns None and removes a corrupted cache file."""
        cache = ResponseCache(cache_dir=tmp_path)
        cache.put_by_key("corrupt_key", "original data")

        corrupt_file = tmp_path / "corrupt_key.json"
        corrupt_file.write_text("{{not valid json}}")

        result = cache.get_by_key("corrupt_key")

        assert result is None
        assert not corrupt_file.exists()

    def test_put_by_key_stores_none_value(self, tmp_path):
        """put_by_key() can store None as the data value."""
        cache = ResponseCache(cache_dir=tmp_path)
        cache.put_by_key("null_data", None)

        result = cache.get_by_key("null_data")

        assert result is None  # None data returns None (same as missing)

    def test_put_by_key_stores_list(self, tmp_path):
        """put_by_key() can store a list of values."""
        cache = ResponseCache(cache_dir=tmp_path)
        cache.put_by_key("list_key", [1, 2, 3])

        result = cache.get_by_key("list_key")

        assert result == [1, 2, 3]

    def test_put_by_key_handles_write_error_gracefully(self, tmp_path):
        """put_by_key() does not raise when a write error occurs."""
        cache = ResponseCache(cache_dir=tmp_path)

        with patch("builtins.open", side_effect=IOError("disk full")):
            # Should not raise
            cache.put_by_key("wont_write", "value")

    def test_get_by_key_handles_read_error_gracefully(self, tmp_path):
        """get_by_key() returns None and does not raise on unexpected read error."""
        cache = ResponseCache(cache_dir=tmp_path)
        cache.put_by_key("error_key", "data")

        with patch("builtins.open", side_effect=Exception("unexpected")):
            result = cache.get_by_key("error_key")

        assert result is None

    def test_get_by_key_uses_per_entry_ttl_over_global_ttl(self, tmp_path):
        """get_by_key() respects the TTL stored in the cache file, not just the global."""
        cache = ResponseCache(cache_dir=tmp_path, ttl_seconds=9999)
        key = "custom_ttl_key"
        cache.put_by_key(key, "value")

        # Manually patch the stored TTL to be very short
        cache_file = tmp_path / f"{key}.json"
        import json as _json

        data = _json.loads(cache_file.read_text())
        data["ttl"] = 0  # instantly expired
        data["timestamp"] = time.time() - 1  # 1 second ago
        cache_file.write_text(_json.dumps(data))

        result = cache.get_by_key(key)

        assert result is None


class TestResponseCacheDelete:
    """Tests for the delete() method."""

    def test_delete_existing_entry_returns_true(self, tmp_path):
        """delete() returns True when the cache entry exists and is removed."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "delete me"}]
        cache.put(messages, "sys", 0.7, "response")
        key = cache._get_cache_key(messages, "sys", 0.7)

        result = cache.delete(key)

        assert result is True
        assert cache.get(messages, "sys", 0.7) is None

    def test_delete_nonexistent_entry_returns_false(self, tmp_path):
        """delete() returns False when the key does not exist in the cache."""
        cache = ResponseCache(cache_dir=tmp_path)

        result = cache.delete("key_that_does_not_exist")

        assert result is False

    def test_delete_when_cache_disabled_returns_false(self, tmp_path):
        """delete() returns False when the cache is disabled."""
        cache = ResponseCache(cache_dir=tmp_path, enabled=False)

        assert cache.delete("any_key") is False

    def test_delete_handles_permission_error(self, tmp_path):
        """delete() returns False and does not raise on unlink permission error."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "perm error"}]
        cache.put(messages, "sys", 0.7, "response")
        key = cache._get_cache_key(messages, "sys", 0.7)

        with patch.object(Path, "unlink", side_effect=PermissionError("no permission")):
            result = cache.delete(key)

        assert result is False

    def test_delete_then_get_returns_none(self, tmp_path):
        """After delete(), a subsequent get() on the same key returns None."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "delete flow"}]
        cache.put(messages, "sys", 0.7, "hello")
        key = cache._get_cache_key(messages, "sys", 0.7)

        cache.delete(key)

        assert cache.get(messages, "sys", 0.7) is None


class TestResponseCacheMaxSizeEnforcement:
    """Verify that files accumulate correctly (ResponseCache is disk-based, no in-memory cap)."""

    def test_multiple_distinct_entries_create_multiple_files(self, tmp_path):
        """Each unique message set creates its own cache file on disk."""
        cache = ResponseCache(cache_dir=tmp_path)

        for i in range(5):
            messages = [{"role": "user", "content": f"unique message {i}"}]
            cache.put(messages, "sys", 0.7, f"response {i}")

        files = list(tmp_path.glob("*.json"))
        assert len(files) == 5

    def test_same_entry_put_twice_does_not_create_duplicate_file(self, tmp_path):
        """Calling put() twice with identical input overwrites the single cache file."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "same"}]

        cache.put(messages, "sys", 0.7, "first")
        cache.put(messages, "sys", 0.7, "second")

        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        assert cache.get(messages, "sys", 0.7) == "second"


class TestResponseCacheTTLBehaviorViaMock:
    """TTL behavior tests using mocked time (no real sleeps)."""

    def test_get_returns_response_just_before_ttl(self, tmp_path):
        """Response is returned when time is just inside the TTL window."""
        cache = ResponseCache(cache_dir=tmp_path, ttl_seconds=3600)
        messages = [{"role": "user", "content": "ttl test"}]
        cache.put(messages, "sys", 0.7, "valid response")

        with patch("src.utils.response_cache.time") as mock_time:
            mock_time.time.return_value = time.time() + 3599  # 1 second before expiry
            result = cache.get(messages, "sys", 0.7)

        assert result == "valid response"

    def test_get_returns_none_just_after_ttl(self, tmp_path):
        """Response is None when time is just past the TTL window."""
        cache = ResponseCache(cache_dir=tmp_path, ttl_seconds=3600)
        messages = [{"role": "user", "content": "ttl expired"}]
        cache.put(messages, "sys", 0.7, "stale response")

        with patch("src.utils.response_cache.time") as mock_time:
            mock_time.time.return_value = time.time() + 3601  # 1 second after expiry
            result = cache.get(messages, "sys", 0.7)

        assert result is None

    def test_expired_file_is_removed_from_disk(self, tmp_path):
        """An expired cache file is deleted from disk during get()."""
        cache = ResponseCache(cache_dir=tmp_path, ttl_seconds=60)
        messages = [{"role": "user", "content": "cleanup test"}]
        cache.put(messages, "sys", 0.7, "response to clean up")

        key = cache._get_cache_key(messages, "sys", 0.7)
        cache_file = tmp_path / f"{key}.json"
        assert cache_file.exists()

        with patch("src.utils.response_cache.time") as mock_time:
            mock_time.time.return_value = time.time() + 120
            cache.get(messages, "sys", 0.7)

        assert not cache_file.exists()


class TestResponseCacheGetStatsTimestamps:
    """Tests for timestamp fields in get_stats()."""

    def test_oldest_and_newest_timestamps_differ_for_multiple_entries(self, tmp_path):
        """oldest_timestamp <= newest_timestamp when multiple entries exist."""
        cache = ResponseCache(cache_dir=tmp_path)

        for i in range(3):
            messages = [{"role": "user", "content": f"ts test {i}"}]
            cache.put(messages, "sys", 0.7, f"resp {i}")
            time.sleep(0.01)  # Small delay to ensure distinct timestamps

        stats = cache.get_stats()

        assert stats["oldest_timestamp"] is not None
        assert stats["newest_timestamp"] is not None
        assert stats["oldest_timestamp"] <= stats["newest_timestamp"]

    def test_get_stats_timestamps_are_none_for_empty_cache(self, tmp_path):
        """oldest_timestamp and newest_timestamp are None when cache is empty."""
        cache = ResponseCache(cache_dir=tmp_path)

        stats = cache.get_stats()

        assert stats["oldest_timestamp"] is None
        assert stats["newest_timestamp"] is None

    def test_get_stats_total_size_mb_is_consistent(self, tmp_path):
        """total_size_mb equals total_size_bytes / (1024 * 1024)."""
        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "size test"}]
        cache.put(messages, "sys", 0.7, "x" * 1000)

        stats = cache.get_stats()

        assert stats["total_size_mb"] == pytest.approx(stats["total_size_bytes"] / (1024 * 1024))


class TestResponseCacheDisabledInit:
    """Test ResponseCache when the Render environment variable is set."""

    def test_render_env_uses_tmp_cache_dir(self, monkeypatch, tmp_path):
        """When RENDER env var is set, cache defaults to /tmp-based path (or custom dir)."""
        monkeypatch.setenv("RENDER", "true")
        monkeypatch.chdir(tmp_path)

        # We pass an explicit cache_dir to avoid actual /tmp creation in tests
        cache = ResponseCache(cache_dir=tmp_path / "render_cache")

        assert cache.enabled is True
        assert cache.cache_dir.exists()


class TestResponseCachePutOverwritesTimestamp:
    """Ensure put() updates the timestamp of an existing entry."""

    def test_second_put_updates_timestamp(self, tmp_path):
        """A second put() on the same key writes a fresh timestamp."""
        import json as _json

        cache = ResponseCache(cache_dir=tmp_path)
        messages = [{"role": "user", "content": "timestamp overwrite"}]
        cache.put(messages, "sys", 0.7, "v1")

        key = cache._get_cache_key(messages, "sys", 0.7)
        cache_file = tmp_path / f"{key}.json"
        ts1 = _json.loads(cache_file.read_text())["timestamp"]

        time.sleep(0.05)
        cache.put(messages, "sys", 0.7, "v2")
        ts2 = _json.loads(cache_file.read_text())["timestamp"]

        assert ts2 >= ts1
        assert cache.get(messages, "sys", 0.7) == "v2"
