"""Test Content Audit formatting improvements."""

import pytest
from datetime import datetime


def test_export_formatting():
    """Test enhanced export formatting for Content Audit."""
    from backend.services.export_service import _format_content_audit

    # Sample content audit data (from ContentAuditAnalysis output)
    sample_data = {
        "business_name": "Acme Analytics",
        "industry": "B2B SaaS - Customer Success",
        "analysis_date": "2026-03-13",
        "total_content_pieces": 45,
        "overall_health_score": 72.5,
        "executive_summary": "Analysis of 45 content pieces reveals strong performance in educational content (guides, how-tos) but underperformance in case studies and customer stories. Overall health score of 72.5/100 indicates good foundation with room for improvement. Top priority: refresh outdated technical content and create more customer-focused stories.",
        "content_by_type": {
            "blog_post": 25,
            "guide": 10,
            "case_study": 5,
            "video": 3,
            "webinar": 2,
        },
        "content_by_health": {
            "excellent": 8,
            "good": 20,
            "needs_update": 12,
            "needs_refresh": 4,
            "archive": 1,
        },
        "content_by_performance": {
            "top_performer": 9,
            "good_performer": 15,
            "average": 16,
            "underperforming": 5,
        },
        "top_performers": [
            {
                "title": "Complete Guide to Churn Prediction with Machine Learning",
                "content_type": "guide",
                "performance_level": "top_performer",
                "engagement_score": 92.5,
                "traffic_estimate": "High: 2.5K/mo",
                "health_status": "excellent",
                "strengths": [
                    "Comprehensive technical depth",
                    "Strong SEO performance",
                    "High engagement metrics",
                ],
            },
            {
                "title": "35-Day Early Warning System Explained",
                "content_type": "blog_post",
                "performance_level": "top_performer",
                "engagement_score": 88.0,
                "traffic_estimate": "High: 1.8K/mo",
                "health_status": "excellent",
                "strengths": ["Unique value proposition", "Data-driven approach"],
            },
        ],
        "underperformers": [
            {
                "title": "Customer Success Basics 101",
                "content_type": "blog_post",
                "performance_level": "underperforming",
                "health_status": "needs_refresh",
                "recommended_action": "Refresh with current examples",
                "action_priority": "high",
                "weaknesses": ["Outdated examples", "Generic approach", "Low engagement"],
                "specific_updates_needed": [
                    "Update statistics to 2026",
                    "Add specific Acme examples",
                    "Include video walkthrough",
                ],
            },
            {
                "title": "Churn Prevention Tips",
                "content_type": "blog_post",
                "performance_level": "underperforming",
                "health_status": "needs_update",
                "recommended_action": "Update and republish",
                "action_priority": "medium",
                "weaknesses": ["Short length", "Lacks depth"],
                "specific_updates_needed": ["Expand to 2000+ words", "Add case study"],
            },
        ],
        "topic_performance": [
            {
                "topic": "Churn Prediction",
                "content_count": 8,
                "avg_performance": "Good",
                "top_performing_piece": "Complete Guide to Churn Prediction",
                "underperforming_pieces": ["Basic Churn Metrics"],
                "recommendation": "Continue focusing on technical depth - it's working well",
            },
            {
                "topic": "Customer Success Strategy",
                "content_count": 6,
                "avg_performance": "Average",
                "top_performing_piece": "Proactive CS Playbook",
                "underperforming_pieces": ["CS Basics 101", "Generic CS Tips"],
                "recommendation": "Refresh outdated basics or archive them",
            },
        ],
        "content_gaps": [
            {
                "gap_description": "Customer success stories and case studies",
                "content_type_needed": "Case study with metrics",
                "priority": "high",
                "reason": "Prospects need proof of results - only 5 case studies for 45 pieces",
            },
            {
                "gap_description": "Video content for technical topics",
                "content_type_needed": "Video tutorials and demos",
                "priority": "high",
                "reason": "Only 3 videos - competitors have 15+",
            },
        ],
        "refresh_opportunities": [
            {
                "content_title": "Customer Success Basics 101",
                "last_updated": "2024-06-15",
                "why_refresh": "Outdated examples and statistics",
                "refresh_approach": "Update stats to 2026, add Acme-specific examples, include video",
                "estimated_impact": "High",
                "estimated_effort": "Medium",
            },
            {
                "content_title": "Churn Prevention Tips",
                "last_updated": "2024-08-20",
                "why_refresh": "Too short and generic",
                "refresh_approach": "Expand to comprehensive guide with case study",
                "estimated_impact": "Medium",
                "estimated_effort": "Large",
            },
        ],
        "repurpose_opportunities": [
            {
                "source_content": "Complete Guide to Churn Prediction",
                "repurpose_into": "LinkedIn carousel series",
                "target_platform": "LinkedIn",
                "why_repurpose": "Top performing content - maximize reach",
                "estimated_reach": "5K+ impressions per post",
            },
            {
                "source_content": "35-Day Early Warning System",
                "repurpose_into": "Short-form video series",
                "target_platform": "YouTube/LinkedIn",
                "why_repurpose": "Complex topic benefits from visual explanation",
                "estimated_reach": "10K+ views",
            },
        ],
        "archive_recommendations": [
            {
                "content_title": "Old Product Announcement (2023)",
                "reason": "Outdated and no longer relevant",
                "action": "Archive",
                "consolidate_into": None,
            },
            {
                "content_title": "5 Quick CS Tips",
                "reason": "Redundant with newer comprehensive guides",
                "action": "Consolidate",
                "consolidate_into": "Customer Success Basics 101",
            },
        ],
        "content_strengths": [
            "Strong technical content performance",
            "Good SEO foundation for guides",
            "High engagement on data-driven content",
        ],
        "content_weaknesses": [
            "Insufficient customer stories and case studies",
            "Limited video content",
            "Outdated evergreen content needs refresh",
        ],
        "immediate_actions": [
            "Refresh 'Customer Success Basics 101' with 2026 data",
            "Create 2 new case studies with ROI metrics",
            "Produce video version of '35-Day Early Warning System'",
        ],
        "thirty_day_plan": [
            "Week 1: Refresh 2 high-priority outdated guides",
            "Week 2: Create case study #1 with customer metrics",
            "Week 3: Produce video tutorial for top-performing content",
            "Week 4: Create case study #2 and LinkedIn carousel",
        ],
        "ninety_day_plan": [
            "Month 1: Refresh top 5 outdated pieces",
            "Month 1: Create 2 customer case studies",
            "Month 2: Launch video content program (4 videos)",
            "Month 2: Repurpose top content into social series",
            "Month 3: Archive or consolidate low performers",
            "Month 3: Fill identified content gaps",
        ],
    }

    # Format the data
    lines = _format_content_audit(sample_data)
    output = "\n".join(lines)

    # Verify comprehensive sections are present
    assert "Content Audit Executive Summary" in output
    assert "45 pieces" in output or "Total Content Analyzed: 45" in output
    assert "72.5/100" in output
    assert "Good" in output  # Health label
    assert "educational content" in output or "technical content" in output

    # Content distribution
    assert "Content Distribution" in output
    assert "By Content Type" in output or "Blog Post" in output
    assert "25" in output  # Blog post count
    assert "By Health Status" in output or "Excellent" in output
    assert "By Performance Level" in output or "Top Performer" in output

    # Top performers
    assert "Top Performing Content" in output
    assert "Complete Guide to Churn Prediction" in output
    assert "92" in output or "93" in output  # Engagement score
    assert "2.5K/mo" in output or "High" in output
    assert "Comprehensive technical depth" in output

    # Underperformers
    assert "Underperforming Content" in output
    assert "Customer Success Basics 101" in output
    assert "Needs Refresh" in output
    assert "HIGH PRIORITY" in output
    assert "Outdated examples" in output
    assert "Update statistics to 2026" in output

    # Topic performance
    assert "Performance by Topic" in output
    assert "Churn Prediction" in output
    assert "8 pieces" in output
    assert "Continue focusing on technical depth" in output

    # Content gaps
    assert "Content Gaps" in output or "Opportunities" in output
    assert "Customer success stories" in output or "case studies" in output
    assert "[HIGH]" in output
    assert "Prospects need proof" in output

    # Refresh opportunities
    assert "Refresh Opportunities" in output
    assert "Update stats to 2026" in output
    assert "Impact: High" in output or "High" in output
    assert "Effort: Medium" in output or "Medium" in output

    # Repurpose opportunities
    assert "Repurposing Opportunities" in output
    assert "LinkedIn carousel" in output
    assert "5K+ impressions" in output

    # Archive recommendations
    assert "Archive" in output
    assert "Old Product Announcement" in output
    assert "Consolidate" in output

    # Strategic insights
    assert "Strategic Insights" in output
    assert "What's Working Well" in output or "Strengths" in output
    assert "Strong technical content" in output
    assert "What Needs Improvement" in output or "Weaknesses" in output
    assert "Insufficient customer stories" in output

    # Action plans
    assert "Immediate Actions" in output
    assert "30-Day Action Plan" in output
    assert "90-Day Strategic Plan" in output
    assert "Refresh 'Customer Success Basics 101'" in output

    print("[OK] Export formatting test passed")


def test_context_builder_formatting():
    """Test enhanced context builder for Content Audit."""
    from backend.services.research_context_builder import _format_content_audit

    # Create mock result
    sample_data = {
        "total_content_pieces": 45,
        "overall_health_score": 72.5,
        "top_performers": [
            {"title": "Complete Guide to Churn Prediction"},
            {"title": "35-Day Early Warning System"},
        ],
        "content_gaps": [
            {"gap_description": "Customer case studies", "priority": "high"},
            {"gap_description": "Video content", "priority": "high"},
            {"gap_description": "Webinar content", "priority": "medium"},
        ],
        "refresh_opportunities": [
            {
                "content_title": "Customer Success Basics",
                "estimated_impact": "High",
            },
            {
                "content_title": "Churn Prevention Tips",
                "estimated_impact": "Medium",
            },
        ],
        "immediate_actions": [
            "Refresh 'Customer Success Basics 101' with 2026 data",
            "Create 2 new case studies",
        ],
    }

    # Create mock ResearchResult
    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Format for context
    context = _format_content_audit(result)

    # Verify concise but comprehensive
    assert "Content Audit" in context
    assert "Mar 13" in context

    # Should include total pieces
    assert "45 pieces" in context

    # Should include health score with label
    assert "72" in context or "73" in context
    assert "good" in context.lower()

    # Should include top performer
    assert "Top:" in context
    assert "Complete Guide" in context or "Churn Prediction" in context

    # Should include gaps with priority count
    assert "Gaps:" in context
    assert "3" in context  # Total gaps
    assert "2 high priority" in context

    # Should include refresh opportunities
    assert "Refresh:" in context
    assert "1 high-impact" in context or "high-impact updates" in context

    # Should include priority action
    assert "Priority:" in context
    assert "Refresh" in context or "Customer Success" in context

    # Should be reasonably concise (under 450 chars for usability)
    assert len(context) < 500, f"Context too long: {len(context)} chars"

    print("[OK] Context builder test passed")
    print(f"\nContext ({len(context)} chars):\n{context}\n")


def test_minimal_data_handling():
    """Test formatting with minimal data (backwards compatibility)."""
    from backend.services.export_service import _format_content_audit

    minimal_data = {
        "total_content_pieces": 10,
        "overall_health_score": 65.0,
        "top_performers": [
            {
                "title": "Test Content",
                "performance_level": "top_performer",
            }
        ],
    }

    lines = _format_content_audit(minimal_data)
    output = "\n".join(lines)

    # Should still work with minimal format
    assert len(lines) > 0
    assert "10 pieces" in output or "10" in output
    assert "65" in output
    assert "Test Content" in output

    print("[OK] Minimal data test passed")


def test_stub_fix():
    """Test that context builder no longer returns stub text."""
    from backend.services.research_context_builder import _format_content_audit

    # This used to return "Content Audit: See data field"
    sample_data = {
        "total_content_pieces": 20,
        "overall_health_score": 75.0,
    }

    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Should not return stub text
    context = _format_content_audit(result)

    assert "See data field" not in context
    assert "Content Audit" in context
    assert "20 pieces" in context
    assert "75" in context

    print("[OK] Stub fix test passed")


def test_empty_data_handling():
    """Test formatting with empty or missing data."""
    from backend.services.export_service import _format_content_audit

    # Empty data
    empty_data = {}
    lines = _format_content_audit(empty_data)
    output = "\n".join(lines)
    assert "No data available" in output

    # None values
    none_data = {"top_performers": None, "content_gaps": None}
    lines = _format_content_audit(none_data)
    output = "\n".join(lines)
    assert len(lines) > 0  # Should not crash

    print("[OK] Empty data handling test passed")


if __name__ == "__main__":
    test_export_formatting()
    test_context_builder_formatting()
    test_minimal_data_handling()
    test_stub_fix()
    test_empty_data_handling()
    print("\n[OK] All Content Audit formatting tests passed!")
