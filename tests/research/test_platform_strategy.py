"""Test platform strategy tool"""

from pathlib import Path

import pytest

from src.research.platform_strategy import PlatformStrategist


def test_platform_strategy_basic():
    """Test basic platform strategy analysis"""

    # Sample business info
    business_description = """
    We're a B2B SaaS company that helps mid-market sales teams automate their
    prospecting and outreach workflows. Our platform integrates with LinkedIn,
    email, and CRM systems to identify high-value prospects, personalize outreach
    at scale, and track engagement metrics.

    We serve sales teams at companies with 50-500 employees who are struggling
    with manual prospecting processes and want to increase their pipeline velocity
    while maintaining personalization.
    """

    target_audience = """
    - Sales Directors and VPs at B2B companies
    - Sales Operations Managers
    - Account Executives looking to scale their outreach
    - RevOps teams focused on pipeline growth
    """

    # Initialize strategist
    strategist = PlatformStrategist(project_id="test_sales_platform")

    # Run analysis
    result = strategist.execute(
        {
            "business_description": business_description,
            "target_audience": target_audience,
            "business_name": "SalesFlow Pro",
            "industry": "B2B SaaS - Sales Automation",
            "current_platforms": ["LinkedIn", "Twitter"],
            "content_goals": "Lead generation and thought leadership",
        }
    )

    # Verify success
    if not result.success:
        print(f"\n[ERROR] Tool failed with error: {result.error}")
    assert result.success, f"Tool failed: {result.error}"
    assert result.tool_name == "platform_strategy"
    assert "json" in result.outputs
    assert "markdown" in result.outputs
    assert "text" in result.outputs

    # Check all output files exist
    for format_type, file_path in result.outputs.items():
        assert Path(file_path).exists(), f"{format_type} file not created"

    print("\n[OK] Platform Strategy Test PASSED")
    print(f"Generated {len(result.outputs)} output files:")
    for format_type, file_path in result.outputs.items():
        print(f"  - {format_type}: {file_path}")

    return result


def test_platform_strategy_validation():
    """Test input validation"""

    strategist = PlatformStrategist(project_id="test_validation")

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


def test_platform_strategy_current_platforms_type_normalization():
    """
    Test Bug #38 fix: current_platforms type normalization

    Verifies that current_platforms field handles:
    - Empty string (converts to empty list)
    - None (converts to empty list)
    - Comma-separated string (converts to list)
    - Already valid list (passes through)
    """

    strategist = PlatformStrategist(project_id="test_bug_38")

    base_inputs = {
        "business_description": "We help businesses grow through digital marketing strategies and execution.",
        "target_audience": "Small to medium business owners looking to scale their online presence.",
        "business_name": "Growth Marketing Co",
        "industry": "Digital Marketing",
        "content_goals": "Lead generation and brand awareness",
    }

    # Test 1: Empty string should convert to empty list
    inputs_empty_string = {**base_inputs, "current_platforms": ""}
    assert strategist.validate_inputs(inputs_empty_string) == True
    assert inputs_empty_string["current_platforms"] == []
    print("[OK] Empty string converts to empty list")

    # Test 2: None should be handled gracefully (not in dict)
    inputs_none = {**base_inputs}
    # Don't include current_platforms at all
    assert strategist.validate_inputs(inputs_none) == True
    print("[OK] Missing current_platforms handled gracefully")

    # Test 3: Comma-separated string should convert to list
    inputs_comma_string = {**base_inputs, "current_platforms": "LinkedIn, Twitter, Facebook"}
    assert strategist.validate_inputs(inputs_comma_string) == True
    assert isinstance(inputs_comma_string["current_platforms"], list)
    assert "LinkedIn" in inputs_comma_string["current_platforms"]
    assert "Twitter" in inputs_comma_string["current_platforms"]
    assert "Facebook" in inputs_comma_string["current_platforms"]
    print("[OK] Comma-separated string converts to list")

    # Test 4: Valid list should pass through
    inputs_valid_list = {**base_inputs, "current_platforms": ["LinkedIn", "Blog"]}
    assert strategist.validate_inputs(inputs_valid_list) == True
    assert inputs_valid_list["current_platforms"] == ["LinkedIn", "Blog"]
    print("[OK] Valid list passes through")

    # Test 5: Empty list should be accepted
    inputs_empty_list = {**base_inputs, "current_platforms": []}
    assert strategist.validate_inputs(inputs_empty_list) == True
    assert inputs_empty_list["current_platforms"] == []
    print("[OK] Empty list accepted")

    print("\n[OK] Bug #38 type normalization tests PASSED")


if __name__ == "__main__":
    # Run basic test
    result = test_platform_strategy_basic()

    # Print summary
    print(f"\n{'='*60}")
    print("PLATFORM STRATEGY SUMMARY")
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

    print("\n[OK] Platform Strategy tool is working!")
