"""
Unit tests for pricing calculation functionality.

Tests the pricing configuration module, preset packages, and calculation helpers.
"""
import pytest
from src.config.pricing import (
    PricingConfig,
    PresetPackage,
    PackageTier,
    PRESET_PACKAGES,
    calculate_price,
    calculate_price_from_quantities,
    get_preset_package,
)


class TestPricingConfig:
    """Test pricing configuration constants"""

    def test_pricing_config_constants(self):
        """Test that pricing config has correct values"""
        config = PricingConfig()
        assert config.PRICE_PER_POST == 40.0
        assert config.RESEARCH_PRICE_PER_POST == 15.0
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
        """Test price calculation with research"""
        price = calculate_price(num_posts=30, research_per_post=True)
        assert price == 1650.0  # 30 * ($40 + $15)

    def test_calculate_price_starter_package(self):
        """Test starter package pricing"""
        price = calculate_price(num_posts=15, research_per_post=False)
        assert price == 600.0

    def test_calculate_price_premium_package(self):
        """Test premium package pricing"""
        price = calculate_price(num_posts=50, research_per_post=True)
        assert price == 2750.0

    def test_calculate_price_custom_quantity(self):
        """Test pricing for custom post quantities"""
        # 100 posts without research
        price = calculate_price(num_posts=100, research_per_post=False)
        assert price == 4000.0  # 100 * $40

        # 100 posts with research
        price = calculate_price(num_posts=100, research_per_post=True)
        assert price == 5500.0  # 100 * ($40 + $15)

    def test_calculate_price_single_post(self):
        """Test pricing for single post"""
        price = calculate_price(num_posts=1, research_per_post=False)
        assert price == 40.0

        price = calculate_price(num_posts=1, research_per_post=True)
        assert price == 55.0

    def test_calculate_price_zero_posts(self):
        """Test pricing for zero posts"""
        price = calculate_price(num_posts=0, research_per_post=False)
        assert price == 0.0


class TestPresetPackages:
    """Test preset package definitions"""

    def test_preset_packages_count(self):
        """Test that we have exactly 3 preset packages"""
        assert len(PRESET_PACKAGES) == 3

    def test_preset_packages_tiers(self):
        """Test that all tiers are represented"""
        tiers = [pkg.tier for pkg in PRESET_PACKAGES]
        assert PackageTier.STARTER in tiers
        assert PackageTier.PROFESSIONAL in tiers
        assert PackageTier.PREMIUM in tiers

    def test_starter_package_structure(self):
        """Test starter package configuration"""
        starter = next(pkg for pkg in PRESET_PACKAGES if pkg.tier == PackageTier.STARTER)

        assert starter.name == "Quick Start (15 Posts)"
        assert starter.price == 600.0
        assert starter.research_included is False
        assert "Fast templates" in starter.description

        # Verify template quantities sum to 15
        assert starter.total_posts == 15

    def test_professional_package_structure(self):
        """Test professional package configuration"""
        professional = next(
            pkg for pkg in PRESET_PACKAGES if pkg.tier == PackageTier.PROFESSIONAL
        )

        assert professional.name == "Professional (30 Posts)"
        assert professional.price == 1200.0
        assert professional.research_included is False
        assert "Balanced variety" in professional.description

        # Verify template quantities sum to 30
        assert professional.total_posts == 30

    def test_premium_package_structure(self):
        """Test premium package configuration"""
        premium = next(pkg for pkg in PRESET_PACKAGES if pkg.tier == PackageTier.PREMIUM)

        assert premium.name == "Premium (50 Posts)"
        assert premium.price == 2750.0
        assert premium.research_included is True
        assert "research" in premium.description.lower()

        # Verify template quantities sum to 50
        assert premium.total_posts == 50

    def test_package_pricing_consistency(self):
        """Test that package prices match calculated prices"""
        for package in PRESET_PACKAGES:
            expected_price = calculate_price(
                num_posts=package.total_posts, research_per_post=package.research_included
            )
            assert (
                package.price == expected_price
            ), f"{package.name} price mismatch: {package.price} != {expected_price}"

    def test_package_templates_valid(self):
        """Test that all packages use valid template IDs"""
        # Valid template IDs are 1-15
        valid_template_ids = set(range(1, 16))

        for package in PRESET_PACKAGES:
            template_ids = set(package.template_quantities.keys())
            assert template_ids.issubset(
                valid_template_ids
            ), f"{package.name} has invalid template IDs"

    def test_package_quantities_positive(self):
        """Test that all template quantities are positive"""
        for package in PRESET_PACKAGES:
            for template_id, quantity in package.template_quantities.items():
                assert quantity > 0, f"{package.name} has zero/negative quantity for template {template_id}"


class TestGetPresetPackage:
    """Test get_preset_package helper function"""

    def test_get_starter_package(self):
        """Test retrieving starter package"""
        package = get_preset_package(PackageTier.STARTER)
        assert package is not None
        assert package.tier == PackageTier.STARTER
        assert package.name == "Quick Start (15 Posts)"

    def test_get_professional_package(self):
        """Test retrieving professional package"""
        package = get_preset_package(PackageTier.PROFESSIONAL)
        assert package is not None
        assert package.tier == PackageTier.PROFESSIONAL
        assert package.name == "Professional (30 Posts)"

    def test_get_premium_package(self):
        """Test retrieving premium package"""
        package = get_preset_package(PackageTier.PREMIUM)
        assert package is not None
        assert package.tier == PackageTier.PREMIUM
        assert package.name == "Premium (50 Posts)"

    def test_get_package_returns_same_object(self):
        """Test that get_preset_package returns the same package object"""
        pkg1 = get_preset_package(PackageTier.STARTER)
        pkg2 = get_preset_package(PackageTier.STARTER)

        # Should have same values
        assert pkg1.tier == pkg2.tier
        assert pkg1.price == pkg2.price
        assert pkg1.total_posts == pkg2.total_posts


class TestPricingEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_large_post_quantity(self):
        """Test pricing for very large quantities"""
        price = calculate_price(num_posts=1000, research_per_post=False)
        assert price == 40000.0

        price = calculate_price(num_posts=1000, research_per_post=True)
        assert price == 55000.0

    def test_pricing_precision(self):
        """Test that pricing calculations maintain precision"""
        # Test with quantities that might have floating point issues
        price = calculate_price(num_posts=33, research_per_post=True)
        assert price == 1815.0  # 33 * 55

    def test_template_quantities_coverage(self):
        """Test that preset packages provide good template variety"""
        for package in PRESET_PACKAGES:
            # Each package should use multiple templates
            num_templates = len(package.template_quantities)
            assert num_templates >= 5, f"{package.name} uses too few templates"

            # No single template should dominate (> 50% of posts)
            for quantity in package.template_quantities.values():
                percentage = (quantity / package.total_posts) * 100
                assert percentage <= 50, f"Single template dominates {package.name}"


class TestPackageTier:
    """Test PackageTier enum"""

    def test_package_tier_values(self):
        """Test that all tier values are defined"""
        assert PackageTier.STARTER.value == "starter"
        assert PackageTier.PROFESSIONAL.value == "professional"
        assert PackageTier.PREMIUM.value == "premium"

    def test_package_tier_from_string(self):
        """Test creating tier from string value"""
        assert PackageTier("starter") == PackageTier.STARTER
        assert PackageTier("professional") == PackageTier.PROFESSIONAL
        assert PackageTier("premium") == PackageTier.PREMIUM


class TestPresetPackageModel:
    """Test PresetPackage Pydantic model"""

    def test_preset_package_creation(self):
        """Test creating a preset package"""
        package = PresetPackage(
            tier=PackageTier.STARTER,
            name="Test Package",
            template_quantities={1: 5, 2: 5, 3: 5},
            price=600.0,
            research_included=False,
            description="Test description",
        )

        assert package.tier == PackageTier.STARTER
        assert package.name == "Test Package"
        assert package.total_posts == 15
        assert package.price == 600.0

    def test_preset_package_validation(self):
        """Test that PresetPackage validates fields"""
        # Should accept valid data
        package = PresetPackage(
            tier=PackageTier.STARTER,
            name="Valid",
            template_quantities={1: 10},
            price=400.0,
            research_included=False,
            description="Valid",
        )
        assert package is not None
        assert package.total_posts == 10

    def test_total_posts_property(self):
        """Test that total_posts property calculates correctly"""
        package = PresetPackage(
            tier=PackageTier.CUSTOM,
            name="Custom",
            template_quantities={1: 3, 2: 5, 9: 2},
            price=400.0,
            research_included=False,
            description="Custom package",
        )
        assert package.total_posts == 10  # 3 + 5 + 2


class TestCalculatePriceFromQuantities:
    """Test calculate_price_from_quantities helper"""

    def test_calculate_from_quantities_basic(self):
        """Test calculating price from template quantities"""
        quantities = {1: 3, 2: 5, 9: 2}  # 10 total
        price = calculate_price_from_quantities(quantities, research_per_post=False)
        assert price == 400.0  # 10 * $40

    def test_calculate_from_quantities_with_research(self):
        """Test calculating price with research"""
        quantities = {1: 3, 2: 5, 9: 2}  # 10 total
        price = calculate_price_from_quantities(quantities, research_per_post=True)
        assert price == 550.0  # 10 * ($40 + $15)

    def test_calculate_from_quantities_empty(self):
        """Test with empty quantities"""
        price = calculate_price_from_quantities({}, research_per_post=False)
        assert price == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
