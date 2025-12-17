"""Test content audit tool"""

from pathlib import Path

import pytest

from src.research.content_audit import ContentAuditor


def test_content_audit_basic():
    """Test basic content audit"""

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

    # Sample content inventory
    content_inventory = [
        {
            "title": "Complete Guide to Churn Prediction",
            "type": "blog_post",
            "description": "Comprehensive guide covering churn prediction basics",
            "publish_date": "2024-01-15",
            "last_updated": "2024-01-15",
            "word_count": 2500,
            "keyword": "churn prediction",
        },
        {
            "title": "5 Warning Signs Your Customer is About to Churn",
            "type": "blog_post",
            "description": "List of behavioral signals indicating churn risk",
            "publish_date": "2023-06-10",
            "last_updated": "2023-06-10",
            "word_count": 1200,
            "keyword": "customer churn",
        },
        {
            "title": "Customer Success Metrics That Matter",
            "type": "guide",
            "description": "Deep dive into CS metrics",
            "publish_date": "2024-03-20",
            "word_count": 3500,
            "keyword": "customer success metrics",
        },
        {
            "title": "How to Calculate Customer Lifetime Value",
            "type": "blog_post",
            "description": "Step-by-step CLV calculation guide",
            "publish_date": "2023-12-05",
            "word_count": 1800,
            "keyword": "customer lifetime value",
        },
        {
            "title": "Retention vs. Acquisition: Where to Focus?",
            "type": "blog_post",
            "description": "ROI comparison of retention vs acquisition",
            "publish_date": "2024-02-14",
            "word_count": 1500,
            "keyword": "customer retention",
        },
    ]

    # Initialize auditor
    auditor = ContentAuditor(project_id="test_acme_audit")

    # Run analysis
    result = auditor.execute(
        {
            "business_description": business_description,
            "target_audience": target_audience,
            "content_inventory": content_inventory,
            "business_name": "Acme Analytics",
            "industry": "B2B SaaS - Customer Success",
        }
    )

    # Verify success
    assert result.success
    assert result.tool_name == "content_audit"
    assert "json" in result.outputs
    assert "markdown" in result.outputs
    assert "text" in result.outputs

    # Check all output files exist
    for format_type, file_path in result.outputs.items():
        assert Path(file_path).exists(), f"{format_type} file not created"

    print("\n[OK] Content Audit Test PASSED")
    print(f"Generated {len(result.outputs)} output files:")
    for format_type, file_path in result.outputs.items():
        print(f"  - {format_type}: {file_path}")

    return result


def test_content_audit_validation():
    """Test input validation"""

    auditor = ContentAuditor(project_id="test_validation")

    # Test missing input
    with pytest.raises(ValueError, match="Missing required input"):
        auditor.validate_inputs({})

    # Test description too short
    with pytest.raises(ValueError, match="too short"):
        auditor.validate_inputs(
            {
                "business_description": "Short",
                "target_audience": "Teams",
                "content_inventory": [{"title": "Post 1"}],
            }
        )

    # Test empty content inventory
    with pytest.raises(ValueError, match="at least 1 content piece"):
        auditor.validate_inputs(
            {"business_description": "A" * 100, "target_audience": "Teams", "content_inventory": []}
        )

    # Test too many content pieces
    with pytest.raises(ValueError, match="Maximum 100 content pieces"):
        auditor.validate_inputs(
            {
                "business_description": "A" * 100,
                "target_audience": "Teams",
                "content_inventory": [{"title": f"Post {i}"} for i in range(101)],
            }
        )

    print("[OK] Validation tests passed")


if __name__ == "__main__":
    # Run basic test
    result = test_content_audit_basic()

    # Print summary
    print(f"\n{'='*60}")
    print("CONTENT AUDIT SUMMARY")
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

    print("\n[OK] Content Audit tool is working!")
