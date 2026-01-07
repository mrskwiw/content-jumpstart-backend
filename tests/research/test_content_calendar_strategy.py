"""Test content calendar strategy tool"""

from pathlib import Path

import pytest

from src.research.content_calendar_strategy import ContentCalendarStrategist


def test_content_calendar_strategy_basic():
    """Test basic content calendar strategy analysis"""

    # Sample business info
    business_description = """
    We're a B2B marketing agency that helps tech startups build and execute
    content marketing programs. We provide strategy, content creation, and
    distribution services focused on LinkedIn and thought leadership.

    Our typical clients are Series A/B funded startups with 10-50 employees
    who don't have dedicated marketing teams but need consistent, high-quality
    content to build awareness and generate inbound leads.
    """

    target_audience = """
    - Startup founders and CEOs
    - VP/Director of Marketing at tech startups
    - Product managers transitioning to PLG
    - B2B SaaS companies in growth phase
    """

    # Initialize strategist
    strategist = ContentCalendarStrategist(project_id="test_marketing_agency")

    # Run analysis
    result = strategist.execute(
        {
            "business_description": business_description,
            "target_audience": target_audience,
            "business_name": "ContentLab Agency",
            "industry": "B2B Marketing Services",
            "primary_platforms": ["LinkedIn", "Blog", "Email"],
            "content_goals": "Build thought leadership, generate leads, and establish authority",
        }
    )

    # Verify success
    if not result.success:
        print(f"\n[ERROR] Tool failed with error: {result.error}")
    assert result.success, f"Tool failed: {result.error}"
    assert result.tool_name == "content_calendar_strategy"
    assert "json" in result.outputs
    assert "markdown" in result.outputs
    assert "text" in result.outputs

    # Check all output files exist
    for format_type, file_path in result.outputs.items():
        assert Path(file_path).exists(), f"{format_type} file not created"

    print("\n[OK] Content Calendar Strategy Test PASSED")
    print(f"Generated {len(result.outputs)} output files:")
    for format_type, file_path in result.outputs.items():
        print(f"  - {format_type}: {file_path}")

    return result


def test_content_calendar_validation():
    """Test input validation"""

    strategist = ContentCalendarStrategist(project_id="test_validation")

    # Test missing input
    with pytest.raises(ValueError, match="business_description is required"):
        strategist.validate_inputs({})

    # Test description too short
    with pytest.raises(ValueError, match="too short"):
        strategist.validate_inputs({"business_description": "Short", "target_audience": "Teams"})

    # Test audience too short
    with pytest.raises(ValueError, match="too short"):
        strategist.validate_inputs({"business_description": "A" * 100, "target_audience": "Teams"})

    print("[OK] Validation tests passed")


if __name__ == "__main__":
    # Run basic test
    result = test_content_calendar_strategy_basic()

    # Print summary
    print(f"\n{'='*60}")
    print("CONTENT CALENDAR STRATEGY SUMMARY")
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

    print("\n[OK] Content Calendar Strategy tool is working!")
