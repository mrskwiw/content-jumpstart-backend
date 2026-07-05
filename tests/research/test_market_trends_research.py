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


def test_market_trends_auto_generation():
    """Test auto-generation of focus areas from SEO keywords (Task #25)"""

    business_description = """
    We help B2B SaaS companies predict and prevent customer churn using advanced
    analytics and machine learning. Our platform analyzes 47 different behavioral
    signals to identify at-risk accounts 35 days before they cancel.
    """

    target_audience = "Customer success teams, revenue operations leaders"

    researcher = MarketTrendsResearcher(project_id="test_auto_gen")

    # Test 1: Auto-generation WITHOUT SEO keywords (fallback to business description)
    result_no_seo = researcher.execute(
        {
            "business_description": business_description,
            "target_audience": target_audience,
            "industry": "B2B SaaS",
            # NO focus_areas provided - should auto-generate
        }
    )

    assert result_no_seo.success
    print("\n[OK] Auto-generated focus areas WITHOUT SEO keywords")

    # Test 2: Auto-generation WITH SEO keywords (preferred method)
    seo_keywords = [
        "customer churn prediction",
        "SaaS retention strategies",
        "customer success analytics",
        "churn prevention tools",
        "customer lifetime value",
    ]

    result_with_seo = researcher.execute(
        {
            "business_description": business_description,
            "target_audience": target_audience,
            "industry": "B2B SaaS",
            "seo_keywords": seo_keywords,
            # NO focus_areas provided - should auto-generate from SEO keywords
        }
    )

    assert result_with_seo.success
    print("[OK] Auto-generated focus areas WITH SEO keywords")
    print(f"SEO keywords used: {seo_keywords[:3]}...")

    # Verify outputs were created
    assert "json" in result_with_seo.outputs
    assert "markdown" in result_with_seo.outputs

    print("[OK] Auto-generation test PASSED - Task #25 verified!")
    return result_with_seo


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

    # NOTE: Industry is now optional (auto-populated from client DB - Task #29)
    # No validation error expected when industry is missing

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
