"""Test SEO keyword research tool"""

from pathlib import Path

import pytest

from src.research.seo_keyword_research import SEOKeywordResearcher


def test_seo_keyword_research_basic():
    """Test basic SEO keyword research"""

    # Sample business info (B2B SaaS, churn prediction)
    business_description = """
    We help B2B SaaS companies predict and prevent customer churn using advanced
    analytics and machine learning. Our platform analyzes 47 different behavioral
    signals to identify at-risk accounts 35 days before they cancel, giving customer
    success teams time to intervene.

    We serve customer success teams, revenue operations leaders, and executive teams
    who want to reduce churn and increase customer lifetime value. Our approach combines
    cutting-edge technology with proven customer success methodologies.
    """

    target_audience = "Customer success teams, revenue operations leaders, SaaS executives"
    main_topics = [
        "churn prediction",
        "customer retention",
        "behavioral analytics",
        "customer success automation",
    ]

    # Initialize researcher
    researcher = SEOKeywordResearcher(project_id="test_acme_analytics_seo")

    # Run analysis
    result = researcher.execute(
        {
            "business_description": business_description,
            "target_audience": target_audience,
            "main_topics": main_topics,
            "business_name": "Acme Analytics",
            "industry": "B2B SaaS",
        }
    )

    # Verify success
    assert result.success
    assert result.tool_name == "seo_keyword_research"
    assert "json" in result.outputs
    assert "markdown" in result.outputs
    assert "text" in result.outputs

    # Check all output files exist
    for format_type, file_path in result.outputs.items():
        assert Path(file_path).exists(), f"{format_type} file not created"

    print("\n[OK] SEO Keyword Research Test PASSED")
    print(f"Generated {len(result.outputs)} output files:")
    for format_type, file_path in result.outputs.items():
        print(f"  - {format_type}: {file_path}")

    return result


def test_seo_keyword_research_with_competitors():
    """Test keyword research with competitor analysis"""

    business_description = """
    AI-powered customer churn prediction platform for B2B SaaS companies.
    We identify at-risk accounts 35 days before cancellation using behavioral analytics.
    """

    researcher = SEOKeywordResearcher(project_id="test_with_competitors")

    result = researcher.execute(
        {
            "business_description": business_description,
            "target_audience": "Customer success teams",
            "main_topics": ["churn prediction", "retention"],
            "competitors": ["ChurnZero", "Gainsight"],
            "business_name": "Test Company",
            "industry": "B2B SaaS",
        }
    )

    assert result.success
    print("\n[OK] SEO with competitors test passed")

    return result


def test_seo_keyword_research_validation():
    """Test input validation"""

    researcher = SEOKeywordResearcher(project_id="test_validation")

    # Test missing input
    with pytest.raises(ValueError, match="Missing required input"):
        researcher.validate_inputs({})

    # Test description too short
    with pytest.raises(ValueError, match="too short"):
        researcher.validate_inputs(
            {"business_description": "Short", "target_audience": "Teams", "main_topics": ["test"]}
        )

    # Test missing topics
    with pytest.raises(ValueError, match="at least 1 main topic"):
        researcher.validate_inputs(
            {"business_description": "A" * 100, "target_audience": "Teams", "main_topics": []}
        )

    print("[OK] Validation tests passed")


if __name__ == "__main__":
    # Run basic test
    result = test_seo_keyword_research_basic()

    # Print summary
    print(f"\n{'='*60}")
    print("SEO KEYWORD RESEARCH SUMMARY")
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
        # Print first 1500 characters
        print(f"\n{'='*60}")
        print("MARKDOWN REPORT (excerpt)")
        print(f"{'='*60}")
        print(content[:1500] + "...")

    print("\n[OK] SEO Keyword Research tool is working!")
