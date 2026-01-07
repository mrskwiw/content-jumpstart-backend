"""Test voice analysis tool"""

from pathlib import Path

import pytest

from src.research.voice_analysis import VoiceAnalyzer


def test_voice_analyzer_basic():
    """Test basic voice analysis"""

    # Sample content (simulating Acme Analytics posts)
    samples = [
        """Here's something most people don't see about churn prediction:

When an account starts showing risk signals, we flag it 35 days before they cancel.

Most companies wait for the customer to miss a login or skip a call. But we track 47 different behaviors that predict churn before the customer even knows they're unhappy.

We made this choice because lagging indicators don't give you time to act. Login frequency? One of the worst predictors we've seen across 2.4M customer records.""",
        """67% of B2B SaaS companies track login frequency as their primary churn indicator.
(Source: ChurnZero 2023 SaaS Benchmarks Report)

Most assume this means engaged users = retained customers.

But I think it signals something else:
Teams are measuring activity, not value realization. And that's why they're blindsided when "active" users cancel.""",
        """For years, we handled churn prevention like this:
Wait for customers to complain. React when renewal conversations went south. Hope our CS team could salvage the relationship in those final 30 days.

Then we analyzed 2.4 million customer records and realized something brutal.

By the time a customer complains, you've already lost them. The decision to leave happened 45-60 days earlier—you just didn't see it.""",
        """Hit 7% churn this quarter. Down from 12% six months ago.

That's $480K in retained ARR we would've lost.

To get here, it required completely rebuilding how our CS team operates. We stopped reacting to cancellation notices and started intervening 35+ days before customers even considered leaving.""",
        """Everyone says "track customer health scores to prevent churn," but that's solving the wrong problem.

Look, health scores are popular for a reason. They give CS teams a dashboard, a number to rally around, something to report to leadership.

But here's what breaks: By the time your health score drops, you're already in damage control mode.""",
    ]

    # Initialize analyzer
    analyzer = VoiceAnalyzer(project_id="test_acme_analytics")

    # Run analysis
    result = analyzer.execute({"content_samples": samples})

    # Verify success
    assert result.success
    assert result.tool_name == "voice_analysis"
    assert "json" in result.outputs
    assert "markdown" in result.outputs
    assert "text" in result.outputs

    # Check all output files exist
    for format_type, file_path in result.outputs.items():
        assert Path(file_path).exists(), f"{format_type} file not created"

    print("\n✅ Voice Analysis Test PASSED")
    print(f"Generated {len(result.outputs)} output files:")
    for format_type, file_path in result.outputs.items():
        print(f"  - {format_type}: {file_path}")

    return result


def test_voice_analyzer_validation():
    """Test input validation"""

    analyzer = VoiceAnalyzer(project_id="test_validation")

    # Test missing input
    with pytest.raises(ValueError, match="business_description is required"):
        analyzer.validate_inputs({})

    # Test too few samples
    with pytest.raises(ValueError, match="at least 5"):
        analyzer.validate_inputs({"content_samples": ["short", "text"]})

    # Test samples too short
    with pytest.raises(ValueError, match="too short"):
        analyzer.validate_inputs({"content_samples": ["a", "b", "c", "d", "e", "f"]})

    print("✅ Validation tests passed")


if __name__ == "__main__":
    # Run basic test
    result = test_voice_analyzer_basic()

    # Print summary
    print(f"\n{'='*60}")
    print("VOICE ANALYSIS SUMMARY")
    print(f"{'='*60}")
    print(f"Duration: {result.metadata['duration_seconds']:.1f} seconds")
    print(f"Price: ${result.metadata['price']}")
    print("\nOutput files:")
    for format_type, path in result.outputs.items():
        print(f"  {format_type:12s}: {path}")

    # Show markdown report excerpt
    markdown_path = result.outputs["markdown"]
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()
        # Print first 1000 characters
        print(f"\n{'='*60}")
        print("MARKDOWN REPORT (excerpt)")
        print(f"{'='*60}")
        print(content[:1500] + "...")

    print("\n✅ Voice Analysis tool is working!")
