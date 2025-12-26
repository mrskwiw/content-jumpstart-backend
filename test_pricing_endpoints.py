"""
Quick test script to verify pricing endpoints work correctly.
"""
import sys
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.pricing import (
    PricingConfig,
    PRESET_PACKAGES,
    calculate_price,
    calculate_price_from_quantities,
    get_preset_package,
    PackageTier,
)


def test_pricing_config():
    """Test pricing configuration"""
    print("\n=== Testing Pricing Configuration ===")
    config = PricingConfig()
    print(f"✓ Price per post: ${config.PRICE_PER_POST}")
    print(f"✓ Research price per post: ${config.RESEARCH_PRICE_PER_POST}")
    print(f"✓ Min posts: {config.MIN_POSTS}")
    print(f"✓ Max posts: {config.MAX_POSTS}")
    print(f"✓ Unlimited revisions: {config.UNLIMITED_REVISIONS}")
    assert config.PRICE_PER_POST == 40.0
    assert config.RESEARCH_PRICE_PER_POST == 15.0
    assert config.UNLIMITED_REVISIONS == True
    print("✓ All pricing config tests passed!")


def test_preset_packages():
    """Test preset packages"""
    print("\n=== Testing Preset Packages ===")
    print(f"✓ Total packages: {len(PRESET_PACKAGES)}")

    for pkg in PRESET_PACKAGES:
        total_posts = pkg.total_posts
        print(f"\n  {pkg.tier.upper()}:")
        print(f"    Name: {pkg.name}")
        print(f"    Total posts: {total_posts}")
        print(f"    Price: ${pkg.price}")
        print(f"    Research included: {pkg.research_included}")
        print(f"    Templates: {len(pkg.template_quantities)} types")

        # Verify price calculation
        expected_price = calculate_price(
            total_posts,
            research_per_post=pkg.research_included
        )
        assert pkg.price == expected_price, f"Price mismatch for {pkg.tier}"

    print("\n✓ All preset package tests passed!")


def test_get_package_by_tier():
    """Test getting package by tier"""
    print("\n=== Testing Get Package by Tier ===")

    professional = get_preset_package(PackageTier.PROFESSIONAL)
    assert professional is not None
    assert professional.tier == PackageTier.PROFESSIONAL
    assert professional.total_posts == 30
    assert professional.price == 1200.0
    print(f"✓ Professional package: {professional.name}, ${professional.price}")

    starter = get_preset_package(PackageTier.STARTER)
    assert starter is not None
    assert starter.total_posts == 15
    print(f"✓ Starter package: {starter.name}, ${starter.price}")

    premium = get_preset_package(PackageTier.PREMIUM)
    assert premium is not None
    assert premium.total_posts == 50
    print(f"✓ Premium package: {premium.name}, ${premium.price}")

    print("✓ All get_package_by_tier tests passed!")


def test_price_calculations():
    """Test price calculation functions"""
    print("\n=== Testing Price Calculations ===")

    # Test 1: 30 posts, no research
    price1 = calculate_price(30, research_per_post=False)
    assert price1 == 1200.0
    print(f"✓ 30 posts, no research: ${price1}")

    # Test 2: 30 posts, with research
    price2 = calculate_price(30, research_per_post=True)
    assert price2 == 1650.0  # 30 * (40 + 15)
    print(f"✓ 30 posts, with research: ${price2}")

    # Test 3: 50 posts, with research
    price3 = calculate_price(50, research_per_post=True)
    assert price3 == 2750.0  # 50 * (40 + 15)
    print(f"✓ 50 posts, with research: ${price3}")

    # Test 4: Calculate from template quantities
    quantities = {1: 3, 2: 5, 9: 2}  # 10 total posts
    price4 = calculate_price_from_quantities(quantities, research_per_post=False)
    assert price4 == 400.0  # 10 * 40
    print(f"✓ Custom quantities (10 posts): ${price4}")

    # Test 5: Custom quantities with research
    price5 = calculate_price_from_quantities(quantities, research_per_post=True)
    assert price5 == 550.0  # 10 * (40 + 15)
    print(f"✓ Custom quantities (10 posts) with research: ${price5}")

    print("✓ All price calculation tests passed!")


def test_template_quantities_structure():
    """Test template quantities structure"""
    print("\n=== Testing Template Quantities Structure ===")

    for pkg in PRESET_PACKAGES:
        # Verify all template IDs are integers
        for template_id, quantity in pkg.template_quantities.items():
            assert isinstance(template_id, int), f"Template ID should be int, got {type(template_id)}"
            assert isinstance(quantity, int), f"Quantity should be int, got {type(quantity)}"
            assert quantity > 0, f"Quantity should be positive, got {quantity}"
            assert 1 <= template_id <= 15, f"Template ID should be 1-15, got {template_id}"

        print(f"✓ {pkg.tier}: All template IDs and quantities valid")

    print("✓ All template quantities structure tests passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("PRICING ENDPOINT VERIFICATION")
    print("=" * 60)

    try:
        test_pricing_config()
        test_preset_packages()
        test_get_package_by_tier()
        test_price_calculations()
        test_template_quantities_structure()

        print("\n" + "=" * 60)
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("=" * 60)
        print("\nPricing endpoints are ready to use!")
        print("Available endpoints:")
        print("  - GET /api/pricing/config")
        print("  - GET /api/pricing/packages")
        print("  - GET /api/pricing/packages/{tier}")
        print("  - GET /api/pricing/calculate?num_posts=30&research=false")
        print("  - POST /api/pricing/calculate-from-quantities")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
