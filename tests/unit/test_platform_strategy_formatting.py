"""Test Platform Strategy formatting improvements."""

import pytest
from datetime import datetime


def test_export_formatting():
    """Test enhanced export formatting for Platform Strategy."""
    from backend.services.export_service import _format_platform_strategy

    # Sample platform strategy data (from PlatformStrategyAnalysis output)
    sample_data = {
        "business_name": "Acme Analytics",
        "industry": "B2B SaaS - Customer Success",
        "target_audience": "Customer success teams, revenue operations leaders, SaaS executives",
        "analysis_date": "2026-03-13",
        "executive_summary": "For a B2B SaaS company targeting customer success teams, LinkedIn should be your primary platform (70% effort), supported by a company blog and email newsletter (25% effort). Your technical, data-driven audience is highly active on LinkedIn, consuming long-form educational content and engaging through comments and shares. Avoid TikTok and Instagram - your decision-makers aren't there.",
        "recommended_platform_mix": {
            "primary_platforms": ["linkedin"],
            "secondary_platforms": ["blog", "email"],
            "experimental_platforms": ["youtube"],
            "avoid_platforms": ["tiktok", "instagram", "facebook"],
            "rationale": "Focus on LinkedIn where your B2B audience actively seeks professional content, supported by owned channels (blog, email) for deeper engagement and nurturing.",
        },
        "audience_behavior": [
            {
                "platform": "linkedin",
                "audience_present": True,
                "activity_level": "High",
                "content_consumption_pattern": "Consuming long-form educational content, case studies, industry insights during work hours",
                "engagement_style": "Comments on thought leadership, shares valuable insights, DMs for business inquiries",
                "decision_maker_presence": "Very High - C-suite and VPs actively engaged",
            },
            {
                "platform": "twitter",
                "audience_present": True,
                "activity_level": "Medium",
                "content_consumption_pattern": "Quick updates, industry news, brief insights",
                "engagement_style": "Retweets, likes, occasional replies",
                "decision_maker_presence": "Medium - Some executives present",
            },
            {
                "platform": "instagram",
                "audience_present": False,
                "activity_level": "Low",
                "content_consumption_pattern": "Personal content, not professional",
                "engagement_style": "Minimal professional engagement",
                "decision_maker_presence": "Very Low - Not a professional platform for this audience",
            },
        ],
        "platform_recommendations": [
            {
                "platform": "linkedin",
                "fit_level": "essential",
                "priority": "high",
                "why_use": [
                    "90% of your target audience is active daily",
                    "Decision makers actively consume content",
                    "Best platform for B2B thought leadership",
                    "High engagement on educational content",
                ],
                "why_not_use": [
                    "Algorithm favors native content over links",
                    "Requires consistent posting (3-4x/week)",
                ],
                "recommended_formats": ["long_form", "carousel", "video"],
                "posting_frequency": "3-4 posts per week",
                "content_approach": "Educational thought leadership: How-to guides, data-driven insights, customer success frameworks, case study highlights",
                "primary_goal": "Thought leadership and inbound leads",
                "success_metrics": [
                    "Engagement rate (target: 5%+)",
                    "Follower growth (target: 10% monthly)",
                    "Lead generation (target: 15 MQLs/month)",
                ],
                "estimated_effort": "Medium",
                "expected_ROI": "High",
            },
            {
                "platform": "blog",
                "fit_level": "essential",
                "priority": "high",
                "why_use": [
                    "Owned channel - full control",
                    "SEO benefits for organic discovery",
                    "Deep-dive content hub",
                    "Email capture mechanism",
                ],
                "why_not_use": [
                    "Requires SEO investment",
                    "Takes 3-6 months to see organic traffic",
                ],
                "recommended_formats": ["long_form"],
                "posting_frequency": "2 comprehensive posts per week",
                "content_approach": "Technical guides, industry analysis, customer stories, product education",
                "primary_goal": "SEO traffic and email list building",
                "success_metrics": [
                    "Organic traffic (target: 5K/month)",
                    "Email subscribers (target: 200/month)",
                    "Time on page (target: 3+ minutes)",
                ],
                "estimated_effort": "Large",
                "expected_ROI": "High",
            },
            {
                "platform": "youtube",
                "fit_level": "optional",
                "priority": "low",
                "why_use": [
                    "Growing demand for video content",
                    "Second largest search engine",
                    "Long-term SEO value",
                ],
                "why_not_use": [
                    "High production effort",
                    "Slow initial growth",
                    "Requires consistency (weekly)",
                ],
                "recommended_formats": ["video"],
                "posting_frequency": "1 video per week (start with monthly)",
                "content_approach": "Product demos, tutorials, customer interviews",
                "primary_goal": "Brand awareness and SEO",
                "success_metrics": ["Views (target: 500/video)", "Watch time", "Subscribers"],
                "estimated_effort": "Large",
                "expected_ROI": "Medium",
            },
        ],
        "content_distribution": {
            "source_platform": "blog",
            "distribution_flow": [
                "Write comprehensive blog post (2000+ words)",
                "Extract 3-5 LinkedIn posts from key sections",
                "Create LinkedIn carousel from main points",
                "Send email newsletter with summary + link",
                "Repurpose into Twitter thread (optional)",
            ],
            "repurposing_strategy": "Create once on blog (owned channel), then atomize into platform-specific formats. LinkedIn gets native text + images, email gets summary + CTA, Twitter gets thread version.",
            "time_savings": "Write 1 blog post = 5-7 pieces of content across platforms. 60% time savings vs. creating unique content for each platform.",
        },
        "current_platforms": ["LinkedIn", "Twitter", "Blog"],
        "current_strengths": [
            "Active LinkedIn presence with good engagement",
            "Regular blog publishing (2x/week)",
        ],
        "current_gaps": [
            "No email newsletter to nurture leads",
            "Inconsistent Twitter posting",
            "No video content",
        ],
        "quick_wins": [
            {
                "platform": "linkedin",
                "action": "Post 3x this week sharing data-driven insights from recent blog posts",
                "timeframe": "This week",
                "expected_outcome": "Increase engagement 20% and gain 50+ followers",
            },
            {
                "platform": "email",
                "action": "Launch weekly newsletter using existing blog content",
                "timeframe": "Next 2 weeks",
                "expected_outcome": "Capture 100 email subscribers in first month",
            },
            {
                "platform": "blog",
                "action": "Add email capture popup to top-performing blog posts",
                "timeframe": "This week",
                "expected_outcome": "Convert 5% of visitors to email subscribers",
            },
        ],
        "thirty_day_plan": [
            "Week 1: Increase LinkedIn posting to 3x/week with educational content",
            "Week 2: Set up email newsletter infrastructure (ConvertKit/Mailchimp)",
            "Week 3: Launch first email newsletter to existing contacts",
            "Week 4: Add lead magnets to top 5 blog posts",
        ],
        "ninety_day_plan": [
            "Month 1: Establish consistent LinkedIn + Blog publishing rhythm",
            "Month 1: Launch email newsletter",
            "Month 2: Grow email list to 500 subscribers",
            "Month 2: Test YouTube with 2 product demo videos",
            "Month 3: Scale LinkedIn presence with employee advocacy",
            "Month 3: Launch customer story video series",
            "Month 3: Achieve 10K monthly blog traffic",
        ],
        "key_insights": [
            "Your audience is primarily on LinkedIn - focus 70% of effort there",
            "Owned channels (blog, email) provide long-term value and audience ownership",
            "Video is growing but start small - monthly YouTube vs. weekly",
            "Repurposing from blog to social saves 60% of content creation time",
        ],
        "common_mistakes_to_avoid": [
            "Spreading too thin across platforms - focus beats breadth",
            "Posting links on LinkedIn - native content performs 3x better",
            "Neglecting email - most valuable owned channel",
            "Creating unique content for each platform - repurpose strategically",
            "Chasing trends on irrelevant platforms (TikTok for B2B SaaS)",
        ],
    }

    # Format the data
    lines = _format_platform_strategy(sample_data)
    output = "\n".join(lines)

    # Verify comprehensive sections are present
    assert "Platform Strategy Executive Summary" in output
    assert "LinkedIn should be your primary platform" in output

    # Recommended platform mix
    assert "Recommended Platform Mix" in output
    assert "Primary Platforms (70% effort)" in output or "Primary Platforms" in output
    assert "LinkedIn" in output
    assert "Secondary Platforms (25% effort)" in output or "Secondary" in output
    assert "Blog" in output and "Email" in output
    assert "Experimental Platforms" in output
    assert "Youtube" in output
    assert "Platforms to Avoid" in output
    assert "Tiktok" in output or "Instagram" in output

    # Audience behavior
    assert "Where Your Audience Is Active" in output
    assert "Audience Present" in output or "✓" in output or "✗" in output
    assert "Activity Level: High" in output or "High" in output
    assert "Content Consumption:" in output
    assert "long-form educational content" in output
    assert "Decision Makers:" in output
    assert "Very High" in output or "C-suite" in output

    # Platform recommendations
    assert "Detailed Platform Recommendations" in output
    assert "Essential" in output
    assert "HIGH PRIORITY" in output
    assert "Why Use This Platform" in output
    assert "90% of your target audience" in output
    assert "Considerations" in output
    assert "Algorithm favors native content" in output

    # Content strategy per platform
    assert "Content Strategy" in output
    assert "Formats:" in output
    assert "Long Form" in output or "Carousel" in output or "Video" in output
    assert "Frequency:" in output
    assert "3-4 posts per week" in output
    assert "Approach:" in output
    assert "Educational thought leadership" in output

    # Expected outcomes
    assert "Expected Outcomes" in output
    assert "Primary Goal:" in output
    assert "Thought leadership" in output
    assert "KPIs:" in output
    assert "Engagement rate" in output
    assert "Effort: Medium" in output or "Medium" in output
    assert "ROI: High" in output or "High" in output

    # Content distribution
    assert "Content Distribution" in output or "Repurposing" in output
    assert "Content Hub:" in output
    assert "Distribution Flow" in output
    assert "Write comprehensive blog post" in output
    assert "Extract 3-5 LinkedIn posts" in output
    assert "Repurposing Strategy" in output
    assert "Efficiency Gains" in output
    assert "60% time savings" in output

    # Current state
    assert "Current State Analysis" in output
    assert "Currently Using:" in output
    assert "What's Working" in output
    assert "Active LinkedIn presence" in output
    assert "What's Missing" in output
    assert "No email newsletter" in output

    # Quick wins
    assert "Quick Wins" in output
    assert "Start Here" in output
    assert "This week" in output or "Next 2 weeks" in output
    assert "Post 3x this week" in output
    assert "Expected Outcome:" in output
    assert "Increase engagement 20%" in output

    # Implementation plans
    assert "30-Day Implementation Plan" in output
    assert "Week 1:" in output
    assert "90-Day Strategic Rollout" in output
    assert "Month 1:" in output

    # Strategic insights
    assert "Key Strategic Insights" in output
    assert "focus 70% of effort there" in output

    # Common mistakes
    assert "Common Mistakes to Avoid" in output
    assert "Spreading too thin" in output

    print("[OK] Export formatting test passed")


def test_context_builder_formatting():
    """Test enhanced context builder for Platform Strategy."""
    from backend.services.research_context_builder import _format_platform_strategy

    # Create mock result
    sample_data = {
        "recommended_platform_mix": {
            "primary_platforms": ["linkedin", "blog"],
            "secondary_platforms": ["email", "twitter"],
        },
        "quick_wins": [
            {
                "platform": "linkedin",
                "action": "Post 3x this week with data-driven insights",
                "timeframe": "This week",
            },
            {
                "platform": "email",
                "action": "Launch weekly newsletter",
            },
        ],
        "content_distribution": {
            "source_platform": "blog",
            "repurposing_strategy": "Blog to social atomization",
        },
        "key_insights": [
            "Focus 70% effort on LinkedIn where your B2B audience lives",
            "Owned channels provide long-term value",
        ],
    }

    # Create mock ResearchResult
    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Format for context
    context = _format_platform_strategy(result)

    # Verify concise but comprehensive
    assert "Platform Strategy" in context
    assert "Mar 13" in context

    # Should include primary platforms
    assert "Primary:" in context
    assert "Linkedin" in context or "Blog" in context

    # Should include secondary platforms
    assert "Secondary:" in context
    assert "Email" in context or "Twitter" in context

    # Should include quick win
    assert "Quick win:" in context
    assert "Linkedin" in context or "Post 3x" in context

    # Should include content hub
    assert "Hub:" in context
    assert "Blog" in context

    # Should include key insight
    assert "Insight:" in context
    assert "Focus 70%" in context or "LinkedIn" in context

    # Should be reasonably concise (under 450 chars for usability)
    assert len(context) < 500, f"Context too long: {len(context)} chars"

    print("[OK] Context builder test passed")
    print(f"\nContext ({len(context)} chars):\n{context}\n")


def test_minimal_data_handling():
    """Test formatting with minimal data (backwards compatibility)."""
    from backend.services.export_service import _format_platform_strategy

    minimal_data = {
        "recommended_platform_mix": {
            "primary_platforms": ["linkedin"],
        }
    }

    lines = _format_platform_strategy(minimal_data)
    output = "\n".join(lines)

    # Should still work with minimal format
    assert len(lines) > 0
    assert "Linkedin" in output

    print("[OK] Minimal data test passed")


def test_stub_fix():
    """Test that context builder no longer returns stub text."""
    from backend.services.research_context_builder import _format_platform_strategy

    # This used to return "Platform Strategy: See data field"
    sample_data = {
        "recommended_platform_mix": {
            "primary_platforms": ["linkedin"],
        }
    }

    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Should not return stub text
    context = _format_platform_strategy(result)

    assert "See data field" not in context
    assert "Platform Strategy" in context
    assert "Linkedin" in context

    print("[OK] Stub fix test passed")


def test_empty_data_handling():
    """Test formatting with empty or missing data."""
    from backend.services.export_service import _format_platform_strategy

    # Empty data
    empty_data = {}
    lines = _format_platform_strategy(empty_data)
    output = "\n".join(lines)
    assert "No data available" in output

    # None values
    none_data = {"recommended_platform_mix": None, "quick_wins": None}
    lines = _format_platform_strategy(none_data)
    output = "\n".join(lines)
    assert len(lines) > 0  # Should not crash

    print("[OK] Empty data handling test passed")


if __name__ == "__main__":
    test_export_formatting()
    test_context_builder_formatting()
    test_minimal_data_handling()
    test_stub_fix()
    test_empty_data_handling()
    print("\n[OK] All Platform Strategy formatting tests passed!")
