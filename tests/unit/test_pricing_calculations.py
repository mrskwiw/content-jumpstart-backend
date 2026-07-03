"""
Unit tests for pricing calculation functionality.

Tests the pricing configuration module and calculation helpers.
"""

import pytest
from src.config.pricing import (
    PricingConfig,
    calculate_price,
    calculate_price_from_quantities,
)


class TestPricingConfig:
    """Test pricing configuration constants"""

    def test_pricing_config_constants(self):
        """Test that pricing config has correct values"""
        config = PricingConfig()
        assert (
            config.PRICE_PER_POST == 0.0
        )  # DEPRECATED: system uses credits only (20 credits/post)
        assert config.RESEARCH_PRICE_PER_POST == 0.0  # DEPRECATED (Bug #43): was 15.0
        assert config.UNLIMITED_REVISIONS is True

    def test_pricing_config_limits(self):
        """Test min/max post limits"""
        config = PricingConfig()
        assert config.MIN_POSTS == 1
        assert config.MAX_POSTS == 100


class TestCalculatePrice:
    """Test calculate_price helper function"""

    def test_calculate_price_no_research(self):
        """Test price calculation without research"""
        price = calculate_price(num_posts=30, research_per_post=False)
        assert price == 1200.0  # 30 * $40

    def test_calculate_price_with_research(self):
        """Test price calculation with research (DEPRECATED - Bug #43)"""
        price = calculate_price(num_posts=30, research_per_post=True)
        assert price == 1200.0  # 30 * $40 (research addon deprecated, was 1650)

    def test_calculate_price_starter_package(self):
        """Test starter package pricing"""
        price = calculate_price(num_posts=15, research_per_post=False)
        assert price == 600.0

    def test_calculate_price_premium_package(self):
        """Test premium package pricing (DEPRECATED - Bug #43)"""
        price = calculate_price(num_posts=50, research_per_post=True)
        assert price == 2000.0  # 50 * $40 (research addon deprecated, was 2750)

    def test_calculate_price_custom_quantity(self):
        """Test pricing for custom post quantities"""
        # 100 posts without research
        price = calculate_price(num_posts=100, research_per_post=False)
        assert price == 4000.0  # 100 * $40

        # 100 posts with research (DEPRECATED - Bug #43)
        price = calculate_price(num_posts=100, research_per_post=True)
        assert price == 4000.0  # 100 * $40 (research addon deprecated, was 5500)

    def test_calculate_price_single_post(self):
        """Test pricing for single post"""
        price = calculate_price(num_posts=1, research_per_post=False)
        assert price == 40.0

        # DEPRECATED (Bug #43): research addon no longer adds cost
        price = calculate_price(num_posts=1, research_per_post=True)
        assert price == 40.0  # research addon deprecated, was 55

    def test_calculate_price_zero_posts(self):
        """Test pricing for zero posts"""
        price = calculate_price(num_posts=0, research_per_post=False)
        assert price == 0.0


class TestPricingEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_large_post_quantity(self):
        """Test pricing for very large quantities"""
        price = calculate_price(num_posts=1000, research_per_post=False)
        assert price == 40000.0

        # DEPRECATED (Bug #43): research addon no longer adds cost
        price = calculate_price(num_posts=1000, research_per_post=True)
        assert price == 40000.0  # research addon deprecated, was 55000

    def test_pricing_precision(self):
        """Test that pricing calculations maintain precision"""
        # Test with quantities that might have floating point issues
        # DEPRECATED (Bug #43): research addon no longer adds cost
        price = calculate_price(num_posts=33, research_per_post=True)
        assert price == 1320.0  # 33 * $40 (research addon deprecated, was 1815)


class TestCalculatePriceFromQuantities:
    """Test calculate_price_from_quantities helper"""

    def test_calculate_from_quantities_basic(self):
        """Test calculating price from template quantities"""
        quantities = {1: 3, 2: 5, 9: 2}  # 10 total
        price = calculate_price_from_quantities(quantities, research_per_post=False)
        assert price == 400.0  # 10 * $40

    def test_calculate_from_quantities_with_research(self):
        """Test calculating price with research (DEPRECATED - Bug #43)"""
        quantities = {1: 3, 2: 5, 9: 2}  # 10 total
        price = calculate_price_from_quantities(quantities, research_per_post=True)
        assert price == 400.0  # 10 * $40 (research addon deprecated, was 550)

    def test_calculate_from_quantities_empty(self):
        """Test with empty quantities"""
        price = calculate_price_from_quantities({}, research_per_post=False)
        assert price == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
