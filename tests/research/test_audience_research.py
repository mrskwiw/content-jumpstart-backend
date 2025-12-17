"""Test audience research tool"""

from pathlib import Path

import pytest

from src.research.audience_research import AudienceResearcher


def test_audience_research_basic():
    """Test basic audience research analysis"""

    # Sample business info
    business_description = """
    We're a B2B SaaS company that provides project management software for
    remote teams. Our platform helps distributed teams coordinate work, track
    progress, and communicate effectively across time zones.

    We focus on fast-growing tech companies (50-500 employees) that have recently
    gone remote-first or hybrid. Our main value prop is simplifying async
    communication and reducing meeting fatigue while maintaining team alignment.
    """

    target_audience = """
    - Engineering managers at tech companies
    - Product managers leading remote teams
    - VP of Engineering at growing startups
    - Tech leads managing distributed developers
    - Remote-first startup founders
    """

    # Initialize researcher
    researcher = AudienceResearcher(project_id="test_saas_company")

    # Run analysis
    result = researcher.execute(
        {
            "business_description": business_description,
            "target_audience": target_audience,
            "business_name": "AsyncTeam",
            "industry": "B2B SaaS - Project Management",
        }
    )

    # Verify success
    if not result.success:
        print(f"\n[ERROR] Tool failed with error: {result.error}")
    assert result.success, f"Tool failed: {result.error}"
    assert result.tool_name == "audience_research"
    assert "json" in result.outputs
    assert "markdown" in result.outputs
    assert "text" in result.outputs

    # Check all output files exist
    for format_type, file_path in result.outputs.items():
        assert Path(file_path).exists(), f"{format_type} file not created"

    print("\n[OK] Audience Research Test PASSED")
    print(f"Generated {len(result.outputs)} output files:")
    for format_type, file_path in result.outputs.items():
        print(f"  - {format_type}: {file_path}")

    return result


def test_audience_research_validation():
    """Test input validation"""

    researcher = AudienceResearcher(project_id="test_validation")

    # Test missing input
    with pytest.raises(ValueError, match="Missing required input"):
        researcher.validate_inputs({})

    # Test description too short
    with pytest.raises(ValueError, match="too short"):
        researcher.validate_inputs(
            {"business_description": "Short", "target_audience": "Engineering managers"}
        )

    # Test audience too short
    with pytest.raises(ValueError, match="too short"):
        researcher.validate_inputs({"business_description": "A" * 100, "target_audience": "Tech"})

    print("[OK] Validation tests passed")


if __name__ == "__main__":
    # Run basic test
    result = test_audience_research_basic()

    # Print summary
    print(f"\n{'='*60}")
    print("AUDIENCE RESEARCH SUMMARY")
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

    print("\n[OK] Audience Research tool is working!")
