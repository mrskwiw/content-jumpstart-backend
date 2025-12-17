"""Test brand archetype assessment tool"""

from pathlib import Path

import pytest

from src.research.brand_archetype import BrandArchetypeAnalyzer


def test_brand_archetype_basic():
    """Test basic brand archetype assessment"""

    # Sample business description (B2B SaaS, data-driven)
    business_description = """
    We help B2B SaaS companies predict and prevent customer churn using advanced
    analytics and machine learning. Our platform analyzes 47 different behavioral
    signals to identify at-risk accounts 35 days before they cancel, giving customer
    success teams time to intervene.

    We believe in data-driven decision making and providing actionable insights that
    empower teams to retain customers. Our mission is to help companies build lasting
    relationships with their customers through better understanding and proactive support.

    We serve customer success teams, revenue operations leaders, and executive teams
    who want to reduce churn and increase customer lifetime value. Our approach combines
    cutting-edge technology with proven customer success methodologies to deliver
    measurable results.
    """

    brand_positioning = "The data-driven churn prevention platform for B2B SaaS"
    target_audience = "Customer success teams and revenue leaders"
    core_values = ["Data-driven", "Proactive", "Customer-centric", "Transparent"]

    # Initialize analyzer
    analyzer = BrandArchetypeAnalyzer(project_id="test_acme_analytics")

    # Run analysis
    result = analyzer.execute(
        {
            "business_description": business_description,
            "brand_positioning": brand_positioning,
            "target_audience": target_audience,
            "core_values": core_values,
        }
    )

    # Verify success
    assert result.success
    assert result.tool_name == "brand_archetype"
    assert "json" in result.outputs
    assert "markdown" in result.outputs
    assert "text" in result.outputs

    # Check all output files exist
    for format_type, file_path in result.outputs.items():
        assert Path(file_path).exists(), f"{format_type} file not created"

    print("\n✅ Brand Archetype Assessment Test PASSED")
    print(f"Generated {len(result.outputs)} output files:")
    for format_type, file_path in result.outputs.items():
        print(f"  - {format_type}: {file_path}")

    return result


def test_brand_archetype_validation():
    """Test input validation"""

    analyzer = BrandArchetypeAnalyzer(project_id="test_validation")

    # Test missing input
    with pytest.raises(ValueError, match="Missing required input"):
        analyzer.validate_inputs({})

    # Test description too short
    with pytest.raises(ValueError, match="too short"):
        analyzer.validate_inputs({"business_description": "Too short"})

    print("✅ Validation tests passed")


if __name__ == "__main__":
    # Run basic test
    result = test_brand_archetype_basic()

    # Print summary
    print(f"\n{'='*60}")
    print("BRAND ARCHETYPE ASSESSMENT SUMMARY")
    print(f"{'='*60}")
    print(f"Duration: {result.metadata['duration_seconds']:.1f} seconds")
    print(f"Price: ${result.metadata['price']}")
    print("\nOutput files:")
    for format_type, path in result.outputs.items():
        print(f"  {format_type:12s}: {path}")

    # Show report excerpt
    markdown_path = result.outputs["markdown"]
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()
        # Print first 1000 characters
        print(f"\n{'='*60}")
        print("MARKDOWN REPORT (excerpt)")
        print(f"{'='*60}")
        print(content[:1000] + "...")

    print("\n✅ Brand Archetype Assessment tool is working!")
