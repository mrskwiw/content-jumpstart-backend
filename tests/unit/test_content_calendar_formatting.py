"""Test Content Calendar formatting improvements."""

import pytest
from datetime import datetime


def test_export_formatting():
    """Test enhanced export formatting for Content Calendar."""
    from backend.services.export_service import _format_content_calendar

    # Sample content calendar data
    sample_data = {
        "business_name": "Acme Analytics",
        "industry": "B2B SaaS",
        "target_audience": "Customer success teams",
        "strategy_start_date": "2026-03-17",
        "analysis_date": "2026-03-13",
        "executive_summary": "90-day content calendar focusing on educational content (40%), thought leadership (30%), and case studies (20%). Post 3x per week on LinkedIn with monthly themes aligned to customer success challenges.",
        "primary_goals": ["thought_leadership", "leads", "education"],
        "content_pillars": ["education", "thought_leadership", "case_studies", "product"],
        "pillar_rationale": "Focus on education to attract awareness, thought leadership to build authority, case studies for social proof, and product updates for existing customers.",
        "content_mix": "40% Education (how-tos, guides), 30% Thought Leadership (insights, opinions), 20% Case Studies (success stories), 10% Product (features, updates)",
        "themes": [
            {
                "name": "Predictive Customer Success",
                "description": "Focus on predictive analytics and early warning systems",
                "pillars": ["education", "thought_leadership"],
                "weeks": [1, 2, 3, 4],
                "goal": "thought_leadership",
            },
            {
                "name": "Scaling CS Operations",
                "description": "Content about scaling teams and processes",
                "pillars": ["education", "case_studies"],
                "weeks": [5, 6, 7, 8],
                "goal": "leads",
            },
        ],
        "weekly_calendar": [
            {
                "week_number": 1,
                "start_date": "2026-03-17",
                "end_date": "2026-03-23",
                "theme": "Introduction to Predictive Churn Analytics",
                "pillar": "education",
                "post_count": 3,
                "post_ideas": [
                    "What is predictive churn analytics? (101 guide)",
                    "5 early warning signs your customer is about to churn",
                    "How we predict churn 35 days in advance (case study)",
                ],
                "goal": "awareness",
                "key_message": "Predictive analytics can identify at-risk customers before they churn",
                "cta_focus": "Download: Churn Prediction Guide",
                "holidays_events": [],
            },
            {
                "week_number": 2,
                "start_date": "2026-03-24",
                "end_date": "2026-03-30",
                "theme": "Building a Churn Prevention Framework",
                "pillar": "thought_leadership",
                "post_count": 3,
                "post_ideas": [
                    "Why reactive customer success fails (opinion)",
                    "The 35-day window: When intervention actually works",
                    "Data shows: Proactive CS reduces churn by 40%",
                ],
                "goal": "thought_leadership",
                "key_message": "Proactive beats reactive every time",
                "cta_focus": "Book demo",
                "holidays_events": [],
            },
        ],
        "platform_calendars": [
            {
                "platform": "LinkedIn",
                "frequency": "3x_per_week",
                "best_days": ["Tuesday", "Wednesday", "Thursday"],
                "best_times": ["9:00 AM", "3:00 PM"],
                "content_mix": "Mix educational and thought leadership - save case studies for Thursday",
            },
            {
                "platform": "Blog",
                "frequency": "2x_per_week",
                "best_days": ["Tuesday", "Thursday"],
                "best_times": ["Morning"],
                "content_mix": "Long-form educational guides and comprehensive case studies",
            },
        ],
        "recommended_frequency": "3x_per_week",
        "total_posts_90_days": 39,
        "seasonal_opportunities": [
            "Q2 budget planning (April)",
            "Mid-year review season (June)",
            "SaaStr conference (May)",
        ],
        "quick_start_actions": [
            "Batch create first 4 weeks of content",
            "Schedule posts in LinkedIn",
            "Set up content review calendar",
            "Create content template library",
        ],
        "content_creation_workflow": "Plan monthly themes → Outline weekly topics → Batch create 4-6 posts → Review and edit → Schedule → Monitor performance",
        "batch_creation_tips": [
            "Block 4 hours weekly for content creation",
            "Use templates for consistency",
            "Create in batches of 4-6 posts",
        ],
        "success_metrics": [
            "Engagement rate (target: 5%+)",
            "Follower growth (target: 10% monthly)",
            "Lead generation (target: 15 MQLs/month)",
        ],
        "review_schedule": "Review weekly metrics every Monday, adjust strategy monthly",
        "key_insights": [
            "Consistency beats volume - 3x/week sustainable is better than sporadic daily",
            "Educational content performs best for B2B audiences",
        ],
        "common_pitfalls": [
            "Creating content day-of - batch ahead",
            "No theme or strategy - random content performs poorly",
        ],
    }

    lines = _format_content_calendar(sample_data)
    output = "\n".join(lines)

    # Verify sections
    assert "Content Calendar Strategy" in output
    assert "2026-03-17" in output
    assert "39" in output or "Total Posts" in output
    assert "Thought Leadership" in output
    assert "Content Pillars" in output
    assert "Education" in output
    assert "Content Mix" in output
    assert "40%" in output
    assert "Content Themes" in output
    assert "Predictive Customer Success" in output
    assert "90-Day Weekly Calendar" in output
    assert "Week 1" in output
    assert "predictive churn analytics" in output.lower()
    assert "Post Ideas" in output
    assert "Platform Posting Schedule" in output
    assert "LinkedIn" in output
    assert "3X Per Week" in output or "3x Per Week" in output
    assert "Seasonal Content Opportunities" in output
    assert "Quick Start" in output
    assert "Batch create" in output
    assert "Success Metrics" in output
    assert "Engagement rate" in output

    print("[OK] Export formatting test passed")


def test_context_builder_formatting():
    """Test enhanced context builder for Content Calendar."""
    from backend.services.research_context_builder import _format_content_calendar

    sample_data = {
        "total_posts_90_days": 39,
        "content_pillars": ["education", "thought_leadership", "case_studies"],
        "primary_goals": ["awareness", "leads"],
        "recommended_frequency": "3x_per_week",
        "weekly_calendar": [
            {"theme": "Introduction to Predictive Analytics", "pillar": "education"}
        ],
    }

    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()
    context = _format_content_calendar(result)

    assert "Content Calendar" in context
    assert "Mar 13" in context
    assert "39 posts" in context
    assert "Pillars:" in context
    assert "Goals:" in context
    assert "Frequency:" in context
    assert "This week:" in context

    assert len(context) < 500, f"Context too long: {len(context)} chars"

    print("[OK] Context builder test passed")
    print(f"\nContext ({len(context)} chars):\n{context}\n")


def test_minimal_data_handling():
    """Test formatting with minimal data."""
    from backend.services.export_service import _format_content_calendar

    minimal_data = {"total_posts_90_days": 30, "content_pillars": ["education"]}

    lines = _format_content_calendar(minimal_data)
    output = "\n".join(lines)

    assert len(lines) > 0
    assert "30" in output

    print("[OK] Minimal data test passed")


def test_stub_fix():
    """Test that context builder no longer returns stub text."""
    from backend.services.research_context_builder import _format_content_calendar

    sample_data = {"total_posts_90_days": 30}

    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()
    context = _format_content_calendar(result)

    assert "See data field" not in context
    assert "Content Calendar" in context

    print("[OK] Stub fix test passed")


def test_empty_data_handling():
    """Test formatting with empty data."""
    from backend.services.export_service import _format_content_calendar

    empty_data = {}
    lines = _format_content_calendar(empty_data)
    output = "\n".join(lines)
    assert "No data available" in output

    print("[OK] Empty data handling test passed")


if __name__ == "__main__":
    test_export_formatting()
    test_context_builder_formatting()
    test_minimal_data_handling()
    test_stub_fix()
    test_empty_data_handling()
    print("\n[OK] All Content Calendar formatting tests passed!")
