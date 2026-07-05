"""
Unit tests for query_cache decorator methods - Tests for MyPy fix
"""

import time
from typing import Any

import pytest

from backend.utils.query_cache import cached, clear_cache, get_cache_info


class TestCachedDecoratorMethods:
    """Tests for cached decorator's cache_clear and cache_info methods"""

    def test_cache_clear_method_exists(self):
        """Test that cached decorator adds cache_clear method"""

        @cached(ttl="short")
        def test_func(x: int) -> int:
            return x * 2

        # Check that cache_clear method was added (MyPy fix verification)
        assert hasattr(test_func, "cache_clear")
        assert callable(test_func.cache_clear)

    def test_cache_info_method_exists(self):
        """Test that cached decorator adds cache_info method"""

        @cached(ttl="short")
        def test_func(x: int) -> int:
            return x * 2

        # Check that cache_info method was added (MyPy fix verification)
        assert hasattr(test_func, "cache_info")
        assert callable(test_func.cache_info)

    def test_cache_clear_clears_cache(self):
        """Test that cache_clear actually clears the cache"""
        call_count = 0

        @cached(ttl="short", key_prefix="test_clear")
        def test_func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - cache miss
        result1 = test_func(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - cache hit
        result2 = test_func(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment (cached)

        # Clear cache
        test_func.cache_clear()

        # Third call - cache miss again after clear
        result3 = test_func(5)
        assert result3 == 10
        assert call_count == 2  # Should increment (cache was cleared)

    def test_cache_info_returns_stats(self):
        """Test that cache_info returns cache statistics"""

        @cached(ttl="short")
        def test_func(x: int) -> int:
            return x * 2

        # Make some calls
        test_func(1)
        test_func(1)  # Cache hit
        test_func(2)

        # Get cache info
        info = test_func.cache_info()

        # Verify it returns a dict with stats
        assert isinstance(info, dict)
        assert "hits" in info
        assert "misses" in info
        assert "sets" in info
        assert info["hits"] >= 1
        assert info["misses"] >= 2

    def test_cache_clear_with_key_prefix(self):
        """Test cache_clear respects key_prefix"""
        call_count_a = 0
        call_count_b = 0

        @cached(ttl="short", key_prefix="func_a")
        def func_a(x: int) -> int:
            nonlocal call_count_a
            call_count_a += 1
            return x * 2

        @cached(ttl="short", key_prefix="func_b")
        def func_b(x: int) -> int:
            nonlocal call_count_b
            call_count_b += 1
            return x * 3

        # Call both functions
        func_a(5)
        func_b(5)
        assert call_count_a == 1
        assert call_count_b == 1

        # Call again (should be cached)
        func_a(5)
        func_b(5)
        assert call_count_a == 1
        assert call_count_b == 1

        # Clear only func_a cache
        func_a.cache_clear()

        # Call again
        func_a(5)  # Should recompute
        func_b(5)  # Should still be cached
        assert call_count_a == 2
        assert call_count_b == 1

    def test_cache_clear_all_ttl_tiers(self):
        """Test clearing cache for different TTL tiers"""

        @cached(ttl="short")
        def short_func(x: int) -> int:
            return x * 2

        @cached(ttl="medium")
        def medium_func(x: int) -> int:
            return x * 3

        @cached(ttl="long")
        def long_func(x: int) -> int:
            return x * 4

        # Call all functions
        short_func(1)
        medium_func(1)
        long_func(1)

        # Clear all caches
        short_func.cache_clear()
        medium_func.cache_clear()
        long_func.cache_clear()

        # No errors should occur
        assert True

    def test_cache_info_per_ttl_tier(self):
        """Test cache_info for different TTL tiers"""

        @cached(ttl="short")
        def short_func(x: int) -> int:
            return x * 2

        @cached(ttl="medium")
        def medium_func(x: int) -> int:
            return x * 3

        # Make calls
        short_func(1)
        short_func(1)  # Hit
        medium_func(1)
        medium_func(2)  # Miss

        # Get info
        short_info = short_func.cache_info()
        medium_info = medium_func.cache_info()

        # Both should return valid stats
        assert isinstance(short_info, dict)
        assert isinstance(medium_info, dict)
        assert short_info["hits"] >= 1
        assert medium_info["misses"] >= 2

    def test_multiple_decorators_have_independent_methods(self):
        """Test that multiple decorated functions have independent cache methods"""

        @cached(ttl="short")
        def func1(x: int) -> int:
            return x * 2

        @cached(ttl="short")
        def func2(x: int) -> int:
            return x * 3

        # Both should have their own methods
        assert hasattr(func1, "cache_clear")
        assert hasattr(func2, "cache_clear")
        assert hasattr(func1, "cache_info")
        assert hasattr(func2, "cache_info")

        # Methods should be different instances
        assert func1.cache_clear != func2.cache_clear
        assert func1.cache_info != func2.cache_info


class TestCacheMethodsWithDifferentParameters:
    """Test cache methods with various function parameters"""

    def test_cache_clear_with_args_and_kwargs(self):
        """Test cache_clear works with functions that have args and kwargs"""

        @cached(ttl="short")
        def complex_func(a: int, b: int, c: int = 0, d: str = "default") -> str:
            return f"{a}-{b}-{c}-{d}"

        # Call with different parameter combinations
        complex_func(1, 2)
        complex_func(1, 2, c=3)
        complex_func(1, 2, c=3, d="custom")

        # Clear should work without errors
        complex_func.cache_clear()
        assert True

    def test_cache_info_with_no_calls(self):
        """Test cache_info when function hasn't been called yet"""

        @cached(ttl="short")
        def unused_func(x: int) -> int:
            return x * 2

        # Should still return valid stats
        info = unused_func.cache_info()
        assert isinstance(info, dict)
        assert "hits" in info
        assert "misses" in info
        assert "sets" in info


class TestCacheMethodsEdgeCases:
    """Test edge cases for cache methods"""

    def test_cache_clear_called_multiple_times(self):
        """Test calling cache_clear multiple times"""

        @cached(ttl="short")
        def test_func(x: int) -> int:
            return x * 2

        test_func(1)

        # Clear multiple times
        test_func.cache_clear()
        test_func.cache_clear()
        test_func.cache_clear()

        # Should not raise errors
        assert True

    def test_cache_info_called_multiple_times(self):
        """Test calling cache_info multiple times"""

        @cached(ttl="short")
        def test_func(x: int) -> int:
            return x * 2

        # Call info multiple times
        info1 = test_func.cache_info()
        info2 = test_func.cache_info()
        info3 = test_func.cache_info()

        # All should return valid dicts
        assert isinstance(info1, dict)
        assert isinstance(info2, dict)
        assert isinstance(info3, dict)

    def test_cache_methods_after_function_execution(self):
        """Test cache methods work correctly after function execution"""
        executed = False

        @cached(ttl="short")
        def test_func(x: int) -> int:
            nonlocal executed
            executed = True
            return x * 2

        # Execute function
        result = test_func(5)
        assert result == 10
        assert executed

        # Methods should still work
        info = test_func.cache_info()
        assert isinstance(info, dict)

        test_func.cache_clear()
        assert True

    def test_cache_methods_with_exceptions(self):
        """Test cache methods when function raises exceptions"""

        @cached(ttl="short")
        def failing_func(x: int) -> int:
            if x < 0:
                raise ValueError("Negative value")
            return x * 2

        # Call with valid value
        failing_func(5)

        # Try with invalid value (should raise)
        with pytest.raises(ValueError):
            failing_func(-1)

        # Cache methods should still work
        info = failing_func.cache_info()
        assert isinstance(info, dict)

        failing_func.cache_clear()
        assert True


class TestCacheMethodsIntegration:
    """Integration tests for cache methods with global cache functions"""

    def test_clear_cache_function_vs_method(self):
        """Test that clear_cache function and method both work"""

        @cached(ttl="short", key_prefix="integration_test")
        def test_func(x: int) -> int:
            return x * 2

        # Call function
        test_func(5)

        # Clear using method
        test_func.cache_clear()

        # Clear using global function (should also work)
        clear_cache(ttl="short", key_prefix="integration_test")

        # No errors
        assert True

    def test_get_cache_info_function_vs_method(self):
        """Test that get_cache_info function and method both work"""

        @cached(ttl="short")
        def test_func(x: int) -> int:
            return x * 2

        test_func(5)

        # Get info using method
        info1 = test_func.cache_info()

        # Get info using global function
        info2 = get_cache_info("short")

        # Both should return valid stats
        assert isinstance(info1, dict)
        assert isinstance(info2, dict)
