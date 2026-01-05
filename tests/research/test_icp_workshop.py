"""Test ICP Workshop tool"""

from pathlib import Path

import pytest

from src.research.icp_workshop import ICPWorkshopFacilitator


def test_icp_workshop_basic():
    """Test basic ICP workshop analysis"""

    # Sample business info
    business_description = """
    We're a B2B SaaS company that provides automated customer success software
    for mid-market subscription businesses. Our platform helps CS teams proactively
    identify at-risk accounts, automate health scoring, and drive product adoption
    through personalized engagement workflows.

    We serve customer success teams at companies with 100-500 employees who are
    struggling with manual account monitoring and want to reduce churn while
    scaling their CS operations efficiently.
    """

    target_audience = """
    - VP of Customer Success at B2B SaaS companies
    - Customer Success Operations Managers
    - CS team leads managing 50+ accounts
    - RevOps teams focused on retention and expansion
    """

    existing_customer_data = """
    Current customers:
    - Mid-market SaaS companies ($5M-$50M ARR)
    - Teams of 5-20 CS managers
    - High-touch customer success model
    - Struggling with churn rates above 10%
    - Average deal size: $30K-$100K annually
    """

    # Initialize workshop facilitator
    facilitator = ICPWorkshopFacilitator(project_id="test_icp_workshop")

    # Run analysis
    result = facilitator.execute(
        {
            "business_description": business_description,
            "target_audience": target_audience,
            "business_name": "ChurnGuard Pro",
            "existing_customer_data": existing_customer_data,
        }
    )

    # Verify success
    if not result.success:
        print(f"\n[ERROR] Tool failed with error: {result.error}")
    assert result.success, f"Tool failed: {result.error}"
    assert result.tool_name == "icp_workshop"
    assert "json" in result.outputs
    assert "markdown" in result.outputs
    assert "text" in result.outputs

    # Check all output files exist
    for format_type, file_path in result.outputs.items():
        assert Path(file_path).exists(), f"{format_type} file not created"

    print("\n[OK] ICP Workshop Test PASSED")
    print(f"Generated {len(result.outputs)} output files:")
    for format_type, file_path in result.outputs.items():
        print(f"  - {format_type}: {file_path}")

    return result


def test_icp_workshop_validation():
    """Test input validation"""

    facilitator = ICPWorkshopFacilitator(project_id="test_validation")

    # Test missing input
    with pytest.raises(ValueError, match="Missing required input"):
        facilitator.validate_inputs({})

    # Test description too short
    with pytest.raises(ValueError, match="too short"):
        facilitator.validate_inputs({
            "business_description": "Short"
        })

    # Test valid input (description is 50+ chars, target_audience is optional)
    is_valid = facilitator.validate_inputs({
        "business_description": "A" * 100
    })
    assert is_valid is True

    print("[OK] Validation tests passed")


def test_icp_workshop_minimal_inputs():
    """Test with minimal inputs (no existing customer data)"""

    facilitator = ICPWorkshopFacilitator(project_id="test_minimal")

    business_description = """
    We're a fintech startup building automated expense management software
    for small businesses. Our platform connects to bank accounts, categorizes
    expenses, and generates financial reports automatically.
    """

    target_audience = """
    Small business owners (1-20 employees) who manually track expenses in
    spreadsheets and want to save time on bookkeeping and tax preparation.
    """

    result = facilitator.execute({
        "business_description": business_description,
        "target_audience": target_audience,
        "business_name": "ExpenseFlow",
    })

    assert result.success, f"Tool failed: {result.error}"
    assert len(result.outputs) == 3  # JSON, Markdown, Text

    print("[OK] Minimal inputs test passed")


if __name__ == "__main__":
    # Run basic test
    result = test_icp_workshop_basic()

    # Print summary
    print(f"\n{'='*60}")
    print("ICP WORKSHOP SUMMARY")
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

    print("\n[OK] ICP Workshop tool is working!")
