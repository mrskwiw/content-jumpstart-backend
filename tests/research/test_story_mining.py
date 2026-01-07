"""Test Story Mining tool"""

from pathlib import Path

import pytest

from src.research.story_mining import StoryMiner


def test_story_mining_basic():
    """Test basic story mining interview"""

    # Sample business info
    business_description = """
    We're a marketing automation platform that helps e-commerce brands
    increase revenue through personalized email campaigns, SMS marketing,
    and customer segmentation. Our platform integrates with Shopify,
    WooCommerce, and other e-commerce platforms.
    """

    customer_context = """
    Customer: Sarah Martinez, Marketing Director at GreenLeaf Organics
    Company: E-commerce brand selling organic skincare products
    Size: $2M annual revenue, team of 8
    Challenge: Was manually sending email campaigns, struggling with segmentation
    Result: After implementing our platform, increased email revenue by 45% in 3 months
    """

    interview_notes = """
    - Before: Spending 10+ hours per week on email marketing
    - Pain: Couldn't segment customers effectively, generic campaigns
    - Decision: Chose us over Klaviyo because of easier segmentation
    - Implementation: Took 2 weeks to set up and import customer data
    - Results: 45% increase in email revenue, 32% higher open rates
    - Quote: "The automated segmentation saved us 10 hours per week"
    - Unexpected benefit: Customer insights helped with product development
    - Now expanding to SMS marketing
    """

    # Initialize story miner
    miner = StoryMiner(project_id="test_story_mining")

    # Run analysis
    result = miner.execute(
        {
            "business_description": business_description,
            "customer_context": customer_context,
            "business_name": "EmailFlow Pro",
            "interview_notes": interview_notes,
        }
    )

    # Verify success
    if not result.success:
        print(f"\n[ERROR] Tool failed with error: {result.error}")
    assert result.success, f"Tool failed: {result.error}"
    assert result.tool_name == "story_mining"
    assert "json" in result.outputs
    assert "markdown" in result.outputs
    assert "text" in result.outputs
    assert "case_study" in result.outputs

    # Check all output files exist
    for format_type, file_path in result.outputs.items():
        assert Path(file_path).exists(), f"{format_type} file not created"

    print("\n[OK] Story Mining Test PASSED")
    print(f"Generated {len(result.outputs)} output files:")
    for format_type, file_path in result.outputs.items():
        print(f"  - {format_type}: {file_path}")

    return result


def test_story_mining_validation():
    """Test input validation"""

    miner = StoryMiner(project_id="test_validation")

    # Test missing input
    with pytest.raises(ValueError, match="business_description is required"):
        miner.validate_inputs({})

    # Test description too short
    with pytest.raises(ValueError, match="too short"):
        miner.validate_inputs(
            {"business_description": "Short", "customer_context": "Customer info"}
        )

    # Test customer context too short
    with pytest.raises(ValueError, match="too short"):
        miner.validate_inputs({"business_description": "A" * 100, "customer_context": "Info"})

    print("[OK] Validation tests passed")


def test_story_mining_minimal_notes():
    """Test with minimal interview notes"""

    miner = StoryMiner(project_id="test_minimal")

    business_description = """
    We provide project management software for creative agencies, helping
    them track time, manage client projects, and generate invoices automatically.
    """

    customer_context = """
    Customer: Mike Chen, Founder of DesignWorks Agency
    Company: Boutique design agency, 12 employees
    Challenge: Using spreadsheets for project tracking, missing deadlines
    Result: Delivered projects 20% faster after implementation
    """

    result = miner.execute(
        {
            "business_description": business_description,
            "customer_context": customer_context,
            "business_name": "ProjectFlow",
        }
    )

    assert result.success, f"Tool failed: {result.error}"
    assert len(result.outputs) == 4  # JSON, Markdown, Text, Case Study

    print("[OK] Minimal notes test passed")


def test_story_mining_with_detailed_notes():
    """Test with extensive interview notes"""

    miner = StoryMiner(project_id="test_detailed")

    business_description = """
    We're a SaaS platform for remote team collaboration, offering video calls,
    screen sharing, document collaboration, and async communication tools.
    """

    customer_context = """
    Customer: Jennifer Park, COO at TechVentures Inc
    Company: Series A startup, 50 remote employees across 12 countries
    Revenue: $5M ARR, growing fast
    Challenge: Team scattered across tools (Zoom, Slack, Google Drive, etc.)
    Goal: Consolidate tools and improve team productivity
    """

    interview_notes = """
    BEFORE SITUATION:
    - Using 8 different tools for collaboration
    - Paying $15K/year for tool subscriptions
    - Employees frustrated with context switching
    - Average 45 minutes per day lost to tool switching
    - Information silos across different platforms

    DECISION PROCESS:
    - Evaluated 5 competitors over 2 months
    - Key factors: All-in-one solution, ease of use, pricing
    - Chose us for API integrations and mobile app quality
    - Internal champion: VP of Engineering loved the developer experience
    - Concerns: Migration complexity (we provided white-glove onboarding)

    IMPLEMENTATION:
    - Kicked off in January, fully deployed by March (2 months)
    - Migrated 10K documents from Google Drive
    - Trained team in weekly cohorts (10 people per session)
    - Challenge: Getting executives to adopt (solved with 1-on-1 training)

    RESULTS (after 6 months):
    - Reduced tool costs by 60% ($9K annual savings)
    - Team productivity up 25% (based on sprint velocity)
    - Employee satisfaction score increased from 6.5 to 8.2
    - Saved 40 minutes per employee per day (estimated)
    - Unexpected: Improved hiring (candidates love the unified platform)

    TESTIMONIALS:
    - "Game-changer for our distributed team" - Jennifer
    - "I can finally find everything in one place" - Developer
    - "The ROI was clear within 3 months" - CFO

    FUTURE PLANS:
    - Expanding to use for client collaboration
    - Planning to add team of 20 more employees this year
    - Became a case study we use in sales conversations
    """

    result = miner.execute(
        {
            "business_description": business_description,
            "customer_context": customer_context,
            "business_name": "UnifiedWorkspace",
            "interview_notes": interview_notes,
        }
    )

    assert result.success, f"Tool failed: {result.error}"

    # Verify case study was generated with rich content
    case_study_path = result.outputs["case_study"]
    with open(case_study_path, "r", encoding="utf-8") as f:
        case_study = f.read()
        assert len(case_study) > 1000, "Case study should be substantial"
        assert "60%" in case_study, "Should mention cost savings"
        assert "25%" in case_study, "Should mention productivity gains"

    print("[OK] Detailed notes test passed")


if __name__ == "__main__":
    # Run basic test
    result = test_story_mining_basic()

    # Print summary
    print(f"\n{'='*60}")
    print("STORY MINING SUMMARY")
    print(f"{'='*60}")
    print(f"Duration: {result.metadata['duration_seconds']:.1f} seconds")
    print(f"Price: ${result.metadata['price']}")
    print("\nOutput files:")
    for format_type, path in result.outputs.items():
        print(f"  {format_type:12s}: {path}")

    # Show case study excerpt
    case_study_path = result.outputs["case_study"]
    with open(case_study_path, "r", encoding="utf-8") as f:
        content = f.read()
        # Print first 2000 characters
        print(f"\n{'='*60}")
        print("CASE STUDY (excerpt)")
        print(f"{'='*60}")
        print(content[:2000] + "...")

    print("\n[OK] Story Mining tool is working!")
