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

    # Test missing input (updated for CommonValidationMixin error messages)
    with pytest.raises(ValueError, match="business_description is required"):
        researcher.validate_inputs({})

    # Test description too short (updated for CommonValidationMixin error messages)
    with pytest.raises(ValueError, match="too short"):
        researcher.validate_inputs(
            {"business_description": "Short", "target_audience": "Teams", "main_topics": ["test"]}
        )

    # Test that empty/missing topics are now allowed (auto-generation)
    # This should NOT raise an error anymore
    inputs = {
        "business_description": "A" * 100,
        "target_audience": "Marketing teams and sales professionals",
        "main_topics": [],  # Empty topics will be auto-generated
    }
    # Should pass validation (returns True)
    assert researcher.validate_inputs(inputs) is True
    # Topics should be set to None for auto-generation
    assert inputs["main_topics"] is None

    print("[OK] Validation tests passed")


def test_auto_generation_from_business_description_only():
    """Test auto-generation with minimal data (business_description only)"""
    researcher = SEOKeywordResearcher(project_id="test_auto_gen_minimal")

    result = researcher.execute(
        {
            "business_description": "Modern family dental practice offering general dentistry, cosmetic procedures, and pediatric care. We focus on preventive care and patient education in a comfortable, anxiety-free environment.",
            "target_audience": "Families with children and anxious adults",
            # NO main_topics provided - should auto-generate
        }
    )

    assert result.success
    assert "data" in result.metadata
    # Verify topics were auto-generated
    data = result.metadata["data"]
    assert "primary_keywords" in data
    assert len(data["primary_keywords"]) > 0

    print(f"\n[OK] Auto-generated {len(data['primary_keywords'])} keywords from minimal data")
    print(f"Top 3 keywords: {[kw['keyword'] for kw in data['primary_keywords'][:3]]}")


def test_auto_generation_with_all_fields():
    """Test auto-generation using all available client fields"""
    researcher = SEOKeywordResearcher(project_id="test_auto_gen_full")

    result = researcher.execute(
        {
            "business_description": "Modern family dental practice offering general dentistry, cosmetic procedures, and pediatric care",
            "target_audience": "Families with children and anxious adults",
            "industry": "Healthcare - Dental",
            "ideal_customer": "Families seeking a dental home for all ages, adults with dental anxiety",
            "main_problem_solved": "Making dental care less scary and more accessible for families",
            # NO main_topics provided - should auto-generate from all these fields
        }
    )

    assert result.success
    assert "data" in result.metadata

    print(f"\n[OK] Auto-generation with all fields succeeded")


def test_manual_topics_override_auto_generation():
    """Test that manually provided topics are used instead of auto-generation"""
    researcher = SEOKeywordResearcher(project_id="test_manual_override")

    custom_topics = ["custom topic one", "custom topic two", "custom topic three"]

    result = researcher.execute(
        {
            "business_description": "Dental practice offering cosmetic and general dentistry",
            "target_audience": "Families and professionals",
            "main_topics": custom_topics,  # Manual topics provided
        }
    )

    assert result.success
    # Verify the tool ran successfully with manual topics
    assert "data" in result.metadata

    print(f"\n[OK] Manual topics override test passed")


def test_auto_generation_uses_user_keywords():
    """Test that user-provided keywords shortcut triggers when 5+ keywords"""
    researcher = SEOKeywordResearcher(project_id="test_keywords_shortcut")

    user_keywords = [
        "agile project management",
        "sprint planning",
        "task tracking",
        "team collaboration",
        "workflow automation",
        "resource management",
    ]

    result = researcher.execute(
        {
            "business_description": "SaaS platform for agile project management and team collaboration",
            "target_audience": "Remote teams and agile practitioners",
            "keywords": user_keywords,  # 6 keywords - should trigger shortcut
            # NO main_topics - should use keywords directly
        }
    )

    assert result.success
    assert "data" in result.metadata

    print(f"\n[OK] Keyword shortcut test passed")


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
