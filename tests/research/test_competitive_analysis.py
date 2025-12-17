"""Test competitive analysis tool"""

from pathlib import Path

import pytest

from src.research.competitive_analysis import CompetitiveAnalyzer


def test_competitive_analysis_basic():
    """Test basic competitive analysis"""

    # Sample business info
    business_description = """
    We help B2B SaaS companies predict and prevent customer churn using advanced
    analytics and machine learning. Our platform analyzes 47 different behavioral
    signals to identify at-risk accounts 35 days before they cancel, giving customer
    success teams time to intervene with targeted retention strategies.

    We serve mid-market and enterprise SaaS companies who want to reduce churn rates
    and increase customer lifetime value through proactive, data-driven customer success.
    """

    target_audience = "Customer success teams, revenue operations leaders, SaaS executives"
    competitors = ["ChurnZero", "Gainsight", "Totango"]

    # Initialize analyzer
    analyzer = CompetitiveAnalyzer(project_id="test_acme_competitive")

    # Run analysis
    result = analyzer.execute(
        {
            "business_description": business_description,
            "target_audience": target_audience,
            "competitors": competitors,
            "business_name": "Acme Analytics",
            "industry": "B2B SaaS - Customer Success",
        }
    )

    # Verify success
    assert result.success
    assert result.tool_name == "competitive_analysis"
    assert "json" in result.outputs
    assert "markdown" in result.outputs
    assert "text" in result.outputs

    # Check all output files exist
    for format_type, file_path in result.outputs.items():
        assert Path(file_path).exists(), f"{format_type} file not created"

    print("\n[OK] Competitive Analysis Test PASSED")
    print(f"Generated {len(result.outputs)} output files:")
    for format_type, file_path in result.outputs.items():
        print(f"  - {format_type}: {file_path}")

    return result


def test_competitive_analysis_validation():
    """Test input validation"""

    analyzer = CompetitiveAnalyzer(project_id="test_validation")

    # Test missing input
    with pytest.raises(ValueError, match="Missing required input"):
        analyzer.validate_inputs({})

    # Test description too short
    with pytest.raises(ValueError, match="too short"):
        analyzer.validate_inputs(
            {
                "business_description": "Short",
                "target_audience": "Teams",
                "competitors": ["Competitor1"],
            }
        )

    # Test no competitors
    with pytest.raises(ValueError, match="at least 1 competitor"):
        analyzer.validate_inputs(
            {"business_description": "A" * 100, "target_audience": "Teams", "competitors": []}
        )

    # Test too many competitors
    with pytest.raises(ValueError, match="Maximum 5 competitors"):
        analyzer.validate_inputs(
            {
                "business_description": "A" * 100,
                "target_audience": "Teams",
                "competitors": ["C1", "C2", "C3", "C4", "C5", "C6"],
            }
        )

    print("[OK] Validation tests passed")


if __name__ == "__main__":
    # Run basic test
    result = test_competitive_analysis_basic()

    # Print summary
    print(f"\n{'='*60}")
    print("COMPETITIVE ANALYSIS SUMMARY")
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
        # Print first 2000 characters
        print(f"\n{'='*60}")
        print("MARKDOWN REPORT (excerpt)")
        print(f"{'='*60}")
        print(content[:2000] + "...")

    print("\n[OK] Competitive Analysis tool is working!")
