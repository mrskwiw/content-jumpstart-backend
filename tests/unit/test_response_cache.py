"""Unit tests for response_cache.py"""

import json
import time

import pytest

from src.utils.response_cache import ResponseCache


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory for testing"""
    cache_dir = tmp_path / "test_cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def cache(temp_cache_dir):
    """Create a ResponseCache instance with temp directory"""
    return ResponseCache(cache_dir=temp_cache_dir, ttl_seconds=60, enabled=True)


def test_cache_initialization(temp_cache_dir):
    """Test cache initialization"""
    cache = ResponseCache(cache_dir=temp_cache_dir, enabled=True)
    assert cache.enabled is True
    assert cache.cache_dir == temp_cache_dir
    assert cache.ttl_seconds == 86400  # default


def test_cache_disabled():
    """Test that disabled cache returns None"""
    cache = ResponseCache(enabled=False)
    messages = [{"role": "user", "content": "test"}]

    # Put should do nothing
    cache.put(messages, "system", 0.7, "response")

    # Get should return None
    result = cache.get(messages, "system", 0.7)
    assert result is None


def test_cache_put_and_get(cache):
    """Test basic cache put and get operations"""
    messages = [{"role": "user", "content": "Hello"}]
    system = "You are a helpful assistant"
    temperature = 0.7
    response = "Hi there!"

    # Put into cache
    cache.put(messages, system, temperature, response)

    # Get from cache
    cached_response = cache.get(messages, system, temperature)
    assert cached_response == response


def test_cache_miss(cache):
    """Test cache miss returns None"""
    messages = [{"role": "user", "content": "Test"}]
    result = cache.get(messages, "system", 0.7)
    assert result is None


def test_cache_key_generation(cache):
    """Test that different inputs generate different cache keys"""
    messages1 = [{"role": "user", "content": "Test 1"}]
    messages2 = [{"role": "user", "content": "Test 2"}]

    cache.put(messages1, "system", 0.7, "response1")
    cache.put(messages2, "system", 0.7, "response2")

    assert cache.get(messages1, "system", 0.7) == "response1"
    assert cache.get(messages2, "system", 0.7) == "response2"


def test_cache_temperature_sensitivity(cache):
    """Test that temperature affects cache key"""
    messages = [{"role": "user", "content": "Test"}]

    cache.put(messages, "system", 0.7, "response_07")
    cache.put(messages, "system", 0.5, "response_05")

    assert cache.get(messages, "system", 0.7) == "response_07"
    assert cache.get(messages, "system", 0.5) == "response_05"


def test_cache_system_prompt_sensitivity(cache):
    """Test that system prompt affects cache key"""
    messages = [{"role": "user", "content": "Test"}]

    cache.put(messages, "system1", 0.7, "response1")
    cache.put(messages, "system2", 0.7, "response2")

    assert cache.get(messages, "system1", 0.7) == "response1"
    assert cache.get(messages, "system2", 0.7) == "response2"


def test_cache_expiration(temp_cache_dir):
    """Test that expired cache entries return None"""
    # Create cache with 1-second TTL
    cache = ResponseCache(cache_dir=temp_cache_dir, ttl_seconds=1, enabled=True)

    messages = [{"role": "user", "content": "Test"}]
    cache.put(messages, "system", 0.7, "response")

    # Should be cached immediately
    assert cache.get(messages, "system", 0.7) == "response"

    # Wait for expiration
    time.sleep(2)

    # Should be expired
    assert cache.get(messages, "system", 0.7) is None


def test_cache_corrupted_file(cache, temp_cache_dir):
    """Test handling of corrupted cache files"""
    messages = [{"role": "user", "content": "Test"}]

    # Put valid entry
    cache.put(messages, "system", 0.7, "response")

    # Corrupt the cache file
    cache_files = list(temp_cache_dir.glob("*.json"))
    assert len(cache_files) == 1

    with open(cache_files[0], "w") as f:
        f.write("invalid json{")

    # Should handle corruption gracefully
    result = cache.get(messages, "system", 0.7)
    assert result is None

    # Corrupted file should be removed
    assert not cache_files[0].exists()


def test_cache_empty_system_prompt(cache):
    """Test cache with empty system prompt"""
    messages = [{"role": "user", "content": "Test"}]

    cache.put(messages, "", 0.7, "response")
    assert cache.get(messages, "", 0.7) == "response"


def test_cache_complex_messages(cache):
    """Test cache with complex message structures"""
    messages = [
        {"role": "user", "content": "First message"},
        {"role": "assistant", "content": "First response"},
        {"role": "user", "content": "Second message"},
    ]

    cache.put(messages, "system", 0.7, "final response")
    assert cache.get(messages, "system", 0.7) == "final response"


def test_cache_unicode_content(cache):
    """Test cache with Unicode content"""
    messages = [{"role": "user", "content": "Hello 世界 🌍"}]
    response = "你好 World 🌎"

    cache.put(messages, "system", 0.7, response)
    assert cache.get(messages, "system", 0.7) == response


def test_cache_json_serialization(cache, temp_cache_dir):
    """Test that cache uses safe JSON serialization"""
    messages = [{"role": "user", "content": "Test"}]
    cache.put(messages, "system", 0.7, "response")

    # Check that file is valid JSON
    cache_files = list(temp_cache_dir.glob("*.json"))
    assert len(cache_files) == 1

    with open(cache_files[0], "r") as f:
        data = json.load(f)
        assert "response" in data
        assert "timestamp" in data
        assert data["response"] == "response"


def test_cache_clear_on_different_params(cache):
    """Test that cache keys are unique for different parameters"""
    base_messages = [{"role": "user", "content": "Test"}]

    # Same messages, different parameters should not collide
    cache.put(base_messages, "system1", 0.7, "response1")
    cache.put(base_messages, "system2", 0.7, "response2")
    cache.put(base_messages, "system1", 0.5, "response3")

    assert cache.get(base_messages, "system1", 0.7) == "response1"
    assert cache.get(base_messages, "system2", 0.7) == "response2"
    assert cache.get(base_messages, "system1", 0.5) == "response3"
