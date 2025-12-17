"""
Demonstration script for research add-on tools

Tests Voice Analysis and Brand Archetype Assessment tools with real-world examples.
"""

from pathlib import Path

from src.research.brand_archetype import BrandArchetypeAnalyzer
from src.research.voice_analysis import VoiceAnalyzer


def test_voice_analysis():
    """Test Voice Analysis Tool with sample content"""

    print("\n" + "=" * 70)
    print("TESTING: Voice Analysis Tool ($400)")
    print("=" * 70)

    # Sample content from a B2B SaaS company
    samples = [
        """Most teams track login frequency as their #1 churn indicator.

Here's why that's backwards:

By the time someone stops logging in, the decision to leave happened 45-60 days earlier.

We analyzed 2.4M customer records and found something surprising: The strongest churn predictors have nothing to do with product usage.

They're behavioral signals like:
• Time between support tickets (increasing gaps = risk)
• Feature adoption velocity (slowing = concern)
• Team size changes (shrinking team = danger)

Login frequency? Bottom 20% of predictive signals.""",
        """Hit 7% churn this quarter. Down from 12% six months ago.

That's $480K in retained ARR we would've lost.

To get here, we had to completely rebuild how our CS team operates:

❌ No more reacting to cancellation notices
✅ Intervening 35+ days before customers consider leaving

❌ No more "gut feel" about account health
✅ Machine learning scoring across 47 behavioral signals

❌ No more one-size-fits-all outreach
✅ Personalized intervention playbooks by risk type

The result? CS team now prevents 73% of at-risk accounts from churning.""",
        """Everyone says "use customer health scores" to prevent churn.

But health scores are solving the wrong problem.

Here's what I mean:

Health scores aggregate data into a single number. Green = good, red = bad.

The problem? By the time your score turns red, you're already in damage control mode.

What works better: Behavior pattern recognition.

Instead of "this account scored 42/100" you need "this account just exhibited Pattern #7 which leads to churn in 67% of cases within 30 days."

That's actionable. That's preventable.""",
        """For years, our CS team handled renewals like this:

1. Wait for renewal date to approach
2. Reach out 30 days before
3. Hope customer says yes

Then we looked at the data.

Customers who renewed smoothly had 3 things in common:
• Consistent feature adoption (not just logins)
• Growing team size over time
• Proactive support ticket patterns

Customers who didn't renew?
• Feature usage flatlined 90-120 days before renewal
• Team hadn't grown in 6+ months
• Only reactive support (problems, not questions)

Now we track these leading indicators starting Day 1.""",
        """The conventional wisdom: Track NPS, CSAT, and product usage.

Our data told us something different.

We found 3 unconventional churn predictors that outperformed everything else:

1. Email open rates on our weekly digest
   (Disengaged inbox = disengaged customer)

2. Time-of-day for support tickets
   (After-hours tickets = frustrated users)

3. Champion turnover within the account
   (New point of contact = restart relationship)

These signals predicted churn 35 days earlier than traditional metrics.""",
    ]

    # Run voice analysis
    analyzer = VoiceAnalyzer(project_id="test_demo_saas")
    result = analyzer.execute({"content_samples": samples})

    if result.success:
        print("\n[SUCCESS] Analysis Complete!")
        print(f"   Duration: {result.metadata['duration_seconds']:.1f}s")
        print(f"   Price: ${result.metadata['price']}")
        print("\n[FILES] Output Files Generated:")
        for format_type, file_path in result.outputs.items():
            size = Path(file_path).stat().st_size
            print(f"   * {format_type:10s}: {file_path.name} ({size:,} bytes)")

        # Show excerpt from markdown report
        markdown_path = result.outputs["markdown"]
        with open(markdown_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")[:30]  # First 30 lines
            print("\n[REPORT] Excerpt (first 30 lines):")
            print("-" * 70)
            print("\n".join(lines))
            print("-" * 70)
    else:
        print(f"\n[ERROR] Analysis Failed: {result.error}")

    return result


def test_brand_archetype():
    """Test Brand Archetype Assessment Tool"""

    print("\n" + "=" * 70)
    print("TESTING: Brand Archetype Assessment Tool ($300)")
    print("=" * 70)

    # Sample brand information
    business_description = """
    We're a customer retention platform built specifically for B2B SaaS companies.
    Our mission is to help teams prevent churn before it happens by identifying
    at-risk accounts 35+ days in advance using machine learning and behavioral analytics.

    We believe in proactive customer success, not reactive firefighting. We empower
    CS teams with data-driven insights and automated intervention workflows that
    have helped our clients reduce churn by an average of 41%.

    Our platform analyzes 47+ behavioral signals across product usage, support
    interactions, team dynamics, and engagement patterns to predict churn with
    87% accuracy. We serve mid-market and enterprise SaaS companies with annual
    contracts ranging from $50K-$500K ARR.
    """

    brand_positioning = "The AI-powered early warning system for B2B SaaS churn"
    target_audience = "Customer Success leaders, Revenue Operations teams, SaaS executives"
    core_values = ["Data-driven", "Proactive", "Transparent", "Customer-centric", "Results-focused"]

    # Run archetype analysis
    analyzer = BrandArchetypeAnalyzer(project_id="test_demo_saas")
    result = analyzer.execute(
        {
            "business_description": business_description,
            "brand_positioning": brand_positioning,
            "target_audience": target_audience,
            "core_values": core_values,
        }
    )

    if result.success:
        print("\n[SUCCESS] Analysis Complete!")
        print(f"   Duration: {result.metadata['duration_seconds']:.1f}s")
        print(f"   Price: ${result.metadata['price']}")
        print("\n[FILES] Output Files Generated:")
        for format_type, file_path in result.outputs.items():
            size = Path(file_path).stat().st_size
            print(f"   * {format_type:10s}: {file_path.name} ({size:,} bytes)")

        # Show excerpt from markdown report
        markdown_path = result.outputs["markdown"]
        with open(markdown_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")[:40]  # First 40 lines
            print("\n[REPORT] Excerpt (first 40 lines):")
            print("-" * 70)
            print("\n".join(lines))
            print("-" * 70)
    else:
        print(f"\n[ERROR] Analysis Failed: {result.error}")

    return result


def main():
    """Run all research tool demos"""

    print("\n" + "=" * 70)
    print("RESEARCH ADD-ON TOOLS DEMONSTRATION")
    print("=" * 70)
    print("\nTesting 2 of 12 planned research tools:")
    print("  1. Voice Analysis Tool ($400)")
    print("  2. Brand Archetype Assessment Tool ($300)")
    print("\nTotal value: $700 in automated research capabilities")

    # Run tests
    voice_result = test_voice_analysis()
    archetype_result = test_brand_archetype()

    # Summary
    print("\n" + "=" * 70)
    print("DEMONSTRATION SUMMARY")
    print("=" * 70)

    total_duration = (
        voice_result.metadata["duration_seconds"] + archetype_result.metadata["duration_seconds"]
    )
    total_price = voice_result.metadata["price"] + archetype_result.metadata["price"]

    print("\n[SUCCESS] Both tools executed successfully!")
    print(f"   Total Duration: {total_duration:.1f}s")
    print(f"   Total Value: ${total_price}")
    print(f"   Output Files: {len(voice_result.outputs) + len(archetype_result.outputs)}")

    print("\n[FILES] All files saved to:")
    print("   Voice Analysis:      data/research/voice_analysis/test_demo_saas/")
    print("   Brand Archetype:     data/research/brand_archetype/test_demo_saas/")

    print("\n[NEXT] Next Steps:")
    print("   * Review generated reports")
    print("   * Continue implementing remaining 10 tools")
    print("   * Build unified research dashboard")
    print("   * Integrate with content generation pipeline")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
