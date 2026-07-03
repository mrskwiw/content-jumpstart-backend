"""Test Content Gap formatting improvements."""

import pytest
from datetime import datetime


def test_export_formatting():
    """Test enhanced export formatting for Content Gap Analysis."""
    from backend.services.export_service import _format_content_gap

    # Sample content gap data (from ContentGapAnalysis output)
    sample_data = {
        "business_name": "Acme Analytics",
        "industry": "B2B SaaS",
        "analysis_date": "2026-03-13",
        "executive_summary": "Analysis identified 23 content gaps across critical, high, and medium priorities. Primary gaps focus on getting started content, feature education, and use case demonstrations. Estimated opportunity: $75K+ annual traffic value.",
        "total_gaps_identified": 23,
        "estimated_opportunity": "$75K+ annual traffic value",
        "critical_gaps": [
            {
                "gap_title": "Getting Started Guide",
                "gap_type": "topic",
                "priority": "critical",
                "description": "New users need step-by-step onboarding content",
                "search_volume": "High: 4.5K/mo",
                "competition": "3 of 5 competitors cover this",
                "business_impact": "Main entry point for new users - drives activation",
                "target_audience": "New trial users, evaluators",
                "buyer_stage": "Consideration",
                "content_angle": "Interactive walkthrough with screenshots",
                "example_topics": [
                    "Complete setup guide for beginners",
                    "First 30 minutes with Acme Analytics",
                    "Quick start checklist",
                ],
                "estimated_effort": "Medium",
            },
            {
                "gap_title": "ROI Calculator Guide",
                "gap_type": "format",
                "priority": "critical",
                "description": "Prospects need to calculate value before purchase",
                "search_volume": "Medium: 2K/mo",
                "competition": "2 of 5 competitors have this",
                "business_impact": "Accelerates decision timeline by 30%",
                "target_audience": "Decision makers, finance teams",
                "buyer_stage": "Decision",
                "content_angle": "Interactive calculator with case studies",
                "example_topics": ["ROI calculator", "Business case template"],
                "estimated_effort": "Large",
            },
        ],
        "high_priority_gaps": [
            {
                "gap_title": "Advanced Analytics Tutorial",
                "gap_type": "depth",
                "priority": "high",
                "description": "Power users need advanced feature guidance",
                "search_volume": "Medium: 1.5K/mo",
                "competition": "1 of 5 competitors covers this",
                "business_impact": "Reduces churn among power users",
                "target_audience": "Existing customers, analysts",
                "buyer_stage": "Awareness",
                "content_angle": "Video series with examples",
                "example_topics": ["Advanced filtering", "Custom dashboards"],
                "estimated_effort": "Medium",
            }
        ],
        "medium_priority_gaps": [
            {
                "gap_title": "API Documentation",
                "gap_type": "topic",
                "priority": "medium",
                "description": "Developers need integration guidance",
                "search_volume": "Low: 500/mo",
                "competition": "4 of 5 competitors have this",
                "business_impact": "Enables enterprise integrations",
                "target_audience": "Developers, IT teams",
                "buyer_stage": "Consideration",
                "content_angle": "Reference docs with code examples",
                "example_topics": ["API reference", "Integration examples"],
                "estimated_effort": "Large",
            }
        ],
        "quick_wins": [
            "FAQ: How to export data",
            "Video: 2-minute product tour",
            "Checklist: Pre-launch setup",
            "Template: Dashboard templates",
            "Guide: Keyboard shortcuts",
        ],
        "buyer_journey_gaps": [
            {
                "stage": "Awareness",
                "current_coverage": "Blog posts, general content",
                "gap_description": "Missing problem-focused educational content",
                "recommended_content": [
                    "The hidden cost of manual analytics",
                    "5 signs you need better analytics",
                    "Industry trends report",
                ],
                "priority": "high",
            },
            {
                "stage": "Decision",
                "current_coverage": "Product pages",
                "gap_description": "Missing comparison and validation content",
                "recommended_content": [
                    "Acme vs Competitor comparison",
                    "Security & compliance guide",
                ],
                "priority": "critical",
            },
        ],
        "format_gaps": [
            {
                "format_name": "Video Tutorials",
                "why_needed": "Complex features need visual demonstration",
                "topics_to_cover": [
                    "Dashboard creation walkthrough",
                    "Report building tutorial",
                    "Data import guide",
                ],
                "estimated_impact": "High",
            },
            {
                "format_name": "Interactive Demos",
                "why_needed": "Prospects need hands-on experience before buying",
                "topics_to_cover": ["Product sandbox", "Live demo environment"],
                "estimated_impact": "High",
            },
        ],
        "competitor_analysis": [
            {
                "competitor_name": "DataViz Pro",
                "content_strengths": ["Excellent video content", "Strong SEO"],
                "popular_topics": ["Dashboard tutorials", "Data visualization tips"],
                "formats_used": ["Video", "Blog", "Webinars"],
                "gaps_in_their_content": [
                    "No API documentation",
                    "Missing advanced tutorials",
                ],
            },
            {
                "competitor_name": "Analytics Plus",
                "content_strengths": ["Comprehensive docs"],
                "popular_topics": ["Integration guides"],
                "formats_used": ["Docs", "Blog"],
                "gaps_in_their_content": ["No video content", "Outdated case studies"],
            },
        ],
        "immediate_actions": [
            "Create Getting Started Guide (critical gap #1)",
            "Produce 2-minute product tour video (quick win)",
            "Write Awareness-stage problem content",
            "Build ROI calculator (critical gap #2)",
            "Develop API documentation",
        ],
        "long_term_opportunities": [
            "Video tutorial series for all major features",
            "Interactive product demos and sandbox",
            "Comprehensive certification program",
            "Industry-specific solution guides",
        ],
        "ninety_day_roadmap": [
            "Month 1: Getting Started Guide + FAQ content",
            "Month 1: 2-minute product tour video",
            "Month 1: Pre-launch setup checklist",
            "Month 2: ROI calculator",
            "Month 2: Advanced Analytics Tutorial series",
            "Month 2: Awareness-stage problem content",
            "Month 3: API documentation",
            "Month 3: Video tutorials for top 5 features",
            "Month 3: Competitor comparison guide",
            "Month 3: Security & compliance content",
            "Q2: Interactive demos and sandbox",
            "Q2: Industry-specific solution guides",
        ],
    }

    # Format the data
    lines = _format_content_gap(sample_data)
    output = "\n".join(lines)

    # Verify comprehensive sections are present
    assert "Content Gap Analysis Summary" in output
    assert "23" in output or "total_gaps_identified" in output
    assert "$75K" in output

    # Critical gaps with full details
    assert "CRITICAL Priority Gaps" in output
    assert "Getting Started Guide" in output
    assert "TOPIC" in output
    assert "4.5K/mo" in output
    assert "3 of 5 competitors" in output
    assert "Main entry point" in output
    assert "New trial users" in output
    assert "Consideration" in output
    assert "Interactive walkthrough" in output
    assert "Complete setup guide" in output
    assert "Medium" in output  # Effort

    # High priority gaps
    assert "HIGH Priority Gaps" in output
    assert "Advanced Analytics Tutorial" in output

    # Medium priority gaps
    assert "MEDIUM Priority Gaps" in output
    assert "API Documentation" in output

    # Quick wins
    assert "Quick Wins" in output
    assert "FAQ: How to export data" in output
    assert "Easy content to create" in output

    # Buyer journey gaps
    assert "Buyer Journey Gaps" in output
    assert "Awareness Stage" in output
    assert "Decision Stage" in output
    assert "Missing problem-focused educational content" in output
    assert "CRITICAL PRIORITY" in output or "HIGH PRIORITY" in output

    # Format gaps
    assert "Missing Content Formats" in output
    assert "Video Tutorials" in output
    assert "High impact" in output or "High" in output
    assert "Complex features need visual demonstration" in output

    # Competitor analysis
    assert "Competitor Content Analysis" in output
    assert "DataViz Pro" in output
    assert "Excellent video content" in output
    assert "Dashboard tutorials" in output
    assert "No API documentation" in output  # Their gap = our opportunity

    # Immediate actions
    assert "Immediate Actions" in output
    assert "What to do first" in output
    assert "Create Getting Started Guide" in output

    # Long-term opportunities
    assert "Long-Term Strategic Opportunities" in output
    assert "Video tutorial series" in output

    # 90-day roadmap
    assert "90-Day Content Roadmap" in output
    assert "Month 1:" in output
    assert "Month 2:" in output
    assert "Month 3:" in output

    print("[OK] Export formatting test passed")


def test_context_builder_formatting():
    """Test enhanced context builder for Content Gap Analysis."""
    from backend.services.research_context_builder import _format_content_gap

    # Create mock result
    sample_data = {
        "total_gaps_identified": 23,
        "critical_gaps": [
            {"gap_title": "Getting Started Guide", "priority": "critical"},
            {"gap_title": "ROI Calculator", "priority": "critical"},
        ],
        "quick_wins": [
            "FAQ: How to export data",
            "Video: Product tour",
            "Checklist: Setup",
        ],
        "buyer_journey_gaps": [
            {"stage": "Awareness", "priority": "high"},
            {"stage": "Decision", "priority": "critical"},
        ],
        "immediate_actions": [
            "Create Getting Started Guide (critical gap #1)",
            "Produce 2-minute product tour video",
        ],
    }

    # Create mock ResearchResult
    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Format for context
    context = _format_content_gap(result)

    # Verify concise but comprehensive
    assert "Content Gap" in context
    assert "Mar 13" in context

    # Should include total gaps
    assert "23 gaps" in context

    # Should include critical gaps
    assert "Critical:" in context
    assert "Getting Started Guide" in context or "ROI Calculator" in context

    # Should include quick wins
    assert "Quick wins" in context
    assert "3 available" in context

    # Should include buyer journey gaps
    assert "Missing stages:" in context
    assert "Awareness" in context or "Decision" in context

    # Should include next action
    assert "Next:" in context
    assert "Create Getting Started" in context or "Getting Started Guide" in context

    # Should be reasonably concise (under 450 chars for usability)
    assert len(context) < 450, f"Context too long: {len(context)} chars"

    print("[OK] Context builder test passed")
    print(f"\nContext ({len(context)} chars):\n{context}\n")


def test_minimal_data_handling():
    """Test formatting with minimal data (backwards compatibility)."""
    from backend.services.export_service import _format_content_gap

    minimal_data = {
        "critical_gaps": [
            {"gap_title": "Product Guide", "gap_type": "topic", "priority": "critical"}
        ]
    }

    lines = _format_content_gap(minimal_data)
    output = "\n".join(lines)

    # Should still work with minimal format
    assert len(lines) > 0
    assert "Product Guide" in output
    assert "CRITICAL" in output

    print("[OK] Minimal data test passed")


def test_stub_fix():
    """Test that context builder no longer returns stub text."""
    from backend.services.research_context_builder import _format_content_gap

    # This used to return "Content Gap Analysis: See data field"
    sample_data = {
        "total_gaps_identified": 5,
        "critical_gaps": [{"gap_title": "Test Gap", "priority": "critical"}],
    }

    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Should not return stub text
    context = _format_content_gap(result)

    assert "See data field" not in context
    assert "Content Gap" in context
    assert "5 gaps" in context
    assert "Critical:" in context

    print("[OK] Stub fix test passed")


def test_empty_data_handling():
    """Test formatting with empty or missing data."""
    from backend.services.export_service import _format_content_gap

    # Empty data
    empty_data = {}
    lines = _format_content_gap(empty_data)
    output = "\n".join(lines)
    assert "No data available" in output

    # None values
    none_data = {"critical_gaps": None}
    lines = _format_content_gap(none_data)
    output = "\n".join(lines)
    assert len(lines) > 0  # Should not crash

    print("[OK] Empty data handling test passed")


if __name__ == "__main__":
    test_export_formatting()
    test_context_builder_formatting()
    test_minimal_data_handling()
    test_stub_fix()
    test_empty_data_handling()
    print("\n[OK] All Content Gap formatting tests passed!")
