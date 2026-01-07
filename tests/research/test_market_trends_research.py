"""Test market trends research tool"""

from pathlib import Path

import pytest

from src.research.market_trends_research import MarketTrendsResearcher


def test_market_trends_research_basic():
    """Test basic market trends research"""

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

    # Initialize researcher
    researcher = MarketTrendsResearcher(project_id="test_acme_trends")

    # Run analysis
    result = researcher.execute(
        {
            "business_description": business_description,
            "target_audience": target_audience,
            "business_name": "Acme Analytics",
            "industry": "B2B SaaS - Customer Success",
        }
    )

    # Verify success
    assert result.success
    assert result.tool_name == "market_trends_research"
    assert "json" in result.outputs
    assert "markdown" in result.outputs
    assert "text" in result.outputs

    # Check all output files exist
    for format_type, file_path in result.outputs.items():
        assert Path(file_path).exists(), f"{format_type} file not created"

    print("\n[OK] Market Trends Research Test PASSED")
    print(f"Generated {len(result.outputs)} output files:")
    for format_type, file_path in result.outputs.items():
        print(f"  - {format_type}: {file_path}")

    return result


def test_market_trends_validation():
    """Test input validation"""

    researcher = MarketTrendsResearcher(project_id="test_validation")

    # Test missing input
    with pytest.raises(ValueError, match="business_description is required"):
        researcher.validate_inputs({})

    # Test description too short
    with pytest.raises(ValueError, match="too short"):
        researcher.validate_inputs(
            {"business_description": "Short", "target_audience": "Teams", "industry": "Tech"}
        )

    # Test missing industry
    with pytest.raises(ValueError, match="Missing required input: industry"):
        researcher.validate_inputs({"business_description": "A" * 100, "target_audience": "Teams"})

    print("[OK] Validation tests passed")


if __name__ == "__main__":
    # Run basic test
    result = test_market_trends_research_basic()

    # Print summary
    print(f"\n{'='*60}")
    print("MARKET TRENDS RESEARCH SUMMARY")
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

    print("\n[OK] Market Trends Research tool is working!")
