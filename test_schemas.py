"""
Test Pydantic schema validators for template quantities and pricing.
"""
import sys
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "backend"))

from schemas.project import ProjectCreate, ProjectUpdate

print("=" * 60)
print("PYDANTIC SCHEMA VALIDATOR TESTS")
print("=" * 60)


def test_auto_calculate_num_posts():
    """Test auto-calculation of num_posts from template_quantities"""
    print("\n>> Test 1: Auto-calculate num_posts")

    project = ProjectCreate(
        name="Test Project",
        client_id="cli-123",
        template_quantities={"1": 3, "2": 5, "9": 2}  # 10 total
    )

    assert project.num_posts == 10, f"Expected 10, got {project.num_posts}"
    print(f"  ✓ num_posts auto-calculated: {project.num_posts}")


def test_auto_calculate_total_price():
    """Test auto-calculation of total_price"""
    print("\n>> Test 2: Auto-calculate total_price")

    # Test 1: 30 posts, no research
    project1 = ProjectCreate(
        name="Test Project 1",
        client_id="cli-123",
        template_quantities={"1": 10, "2": 10, "3": 10},  # 30 total
        price_per_post=40.0,
        research_price_per_post=0.0
    )

    assert project1.num_posts == 30
    assert project1.total_price == 1200.0, f"Expected 1200.0, got {project1.total_price}"
    print(f"  ✓ 30 posts, no research: ${project1.total_price}")

    # Test 2: 30 posts, with research
    project2 = ProjectCreate(
        name="Test Project 2",
        client_id="cli-123",
        template_quantities={"1": 10, "2": 10, "3": 10},  # 30 total
        price_per_post=40.0,
        research_price_per_post=15.0
    )

    assert project2.total_price == 1650.0, f"Expected 1650.0, got {project2.total_price}"
    print(f"  ✓ 30 posts, with research: ${project2.total_price}")

    # Test 3: 50 posts, with research
    project3 = ProjectCreate(
        name="Test Project 3",
        client_id="cli-123",
        template_quantities={"1": 25, "2": 25},  # 50 total
        price_per_post=40.0,
        research_price_per_post=15.0
    )

    assert project3.total_price == 2750.0, f"Expected 2750.0, got {project3.total_price}"
    print(f"  ✓ 50 posts, with research: ${project3.total_price}")


def test_camelcase_aliases():
    """Test camelCase field aliases work"""
    print("\n>> Test 3: CamelCase aliases")

    # Frontend sends camelCase
    project = ProjectCreate(
        name="Test Project",
        clientId="cli-123",  # camelCase
        templateQuantities={"1": 5, "2": 5},  # camelCase
        pricePerPost=40.0,  # camelCase
        researchPricePerPost=15.0  # camelCase
    )

    assert project.client_id == "cli-123"
    assert project.template_quantities == {"1": 5, "2": 5}
    assert project.num_posts == 10
    assert project.total_price == 550.0  # 10 * (40 + 15)
    print(f"  ✓ CamelCase aliases work correctly")
    print(f"  ✓ client_id: {project.client_id}")
    print(f"  ✓ template_quantities: {project.template_quantities}")
    print(f"  ✓ total_price: ${project.total_price}")


def test_backward_compatibility():
    """Test backward compatibility with legacy templates field"""
    print("\n>> Test 4: Backward compatibility")

    # Old format: just templates array (no quantities)
    project = ProjectCreate(
        name="Legacy Project",
        client_id="cli-123",
        templates=["1", "2", "3"],  # Legacy format
        platforms=["linkedin"]
    )

    # Should not auto-calculate num_posts from templates (only from template_quantities)
    assert project.templates == ["1", "2", "3"]
    assert project.template_quantities is None
    assert project.num_posts is None
    print(f"  ✓ Legacy templates field preserved: {project.templates}")
    print(f"  ✓ No auto-calculation from legacy templates")


def test_explicit_values_not_overridden():
    """Test explicitly provided values are not overridden"""
    print("\n>> Test 5: Explicit values preserved")

    project = ProjectCreate(
        name="Test Project",
        client_id="cli-123",
        template_quantities={"1": 10},  # Would auto-calc to 10
        num_posts=15,  # Explicit override
        total_price=800.0  # Explicit override
    )

    # Explicit values should be preserved
    assert project.num_posts == 15, f"Expected 15, got {project.num_posts}"
    assert project.total_price == 800.0, f"Expected 800.0, got {project.total_price}"
    print(f"  ✓ Explicit num_posts preserved: {project.num_posts}")
    print(f"  ✓ Explicit total_price preserved: ${project.total_price}")


if __name__ == "__main__":
    try:
        test_auto_calculate_num_posts()
        test_auto_calculate_total_price()
        test_camelcase_aliases()
        test_backward_compatibility()
        test_explicit_values_not_overridden()

        print("\n" + "=" * 60)
        print("✓✓✓ ALL SCHEMA TESTS PASSED ✓✓✓")
        print("=" * 60)
        print("\nPydantic validators are working correctly!")
        print("Schemas ready for API integration.")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
