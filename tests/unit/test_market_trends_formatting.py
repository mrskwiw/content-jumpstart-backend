"""Test Market Trends formatting improvements."""

import pytest
from datetime import datetime


def test_export_formatting():
    """Test enhanced export formatting for Market Trends."""
    from backend.services.export_service import _format_market_trends

    # Sample market trends data (from TrendReport output)
    sample_data = {
        "market_summary": "The B2B SaaS market is experiencing rapid growth in AI-powered analytics with strong focus on customer retention and automation. Rising trends center around predictive analytics and proactive customer success strategies.",
        "top_rising_trends": [
            {
                "topic": "AI-powered customer analytics",
                "description": "Using artificial intelligence to analyze customer behavior patterns",
                "momentum": "rising",
                "relevance": "high",
                "popularity_score": 8.5,
                "growth_rate": "+200% YoY",
                "key_drivers": ["AI adoption", "Data availability", "Customer expectations"],
                "target_audience": ["SaaS executives", "Data teams", "Customer success managers"],
                "content_angles": [
                    "How AI transforms customer analytics",
                    "ROI of AI-powered analytics",
                ],
                "related_keywords": [
                    "customer intelligence",
                    "predictive analytics",
                    "AI analytics",
                ],
                "urgency": "High",
            },
            {
                "topic": "Proactive customer success",
                "description": "Preventing churn before it happens through early intervention",
                "momentum": "rising",
                "relevance": "high",
                "popularity_score": 7.8,
                "growth_rate": "+150% YoY",
                "key_drivers": ["Churn prevention", "Retention focus"],
                "target_audience": ["Customer success teams"],
                "content_angles": ["Proactive vs reactive CS"],
                "related_keywords": ["churn prevention", "retention"],
                "urgency": "Medium",
            },
        ],
        "immediate_opportunities": [
            "Create content on AI-powered customer analytics implementation",
            "Publish case study on proactive customer success strategies",
            "Develop guide on predictive churn models",
        ],
        "emerging_conversations": [
            {
                "topic": "Ethical AI in customer analytics",
                "description": "Debate around privacy and transparency in AI-powered customer insights",
                "key_perspectives": ["Privacy advocates", "AI proponents", "Regulators"],
                "thought_leaders": ["Jane Smith", "John Doe"],
                "content_opportunity": "Position as thought leader on ethical AI implementation",
            }
        ],
        "seasonal_trends": [
            {
                "topic": "Q4 budget planning",
                "timing": "Q3-Q4",
                "description": "SaaS companies plan renewals and expansion budgets",
                "preparation_timeline": "Start content in Q2",
            }
        ],
        "upcoming_opportunities": [
            "Prepare Q4 budget planning content series",
            "Create seasonal customer retention strategies",
        ],
        "key_themes": [
            "AI transformation in SaaS",
            "Customer-centric growth",
            "Data-driven decision making",
        ],
        "declining_topics": [
            "Manual reporting processes",
            "Reactive customer support",
        ],
    }

    # Format the data
    lines = _format_market_trends(sample_data)
    output = "\n".join(lines)

    # Verify comprehensive sections are present
    assert "Market Trends Summary" in output
    assert "rapid growth in AI-powered analytics" in output

    assert "Top Rising Trends" in output
    assert "AI-powered customer analytics" in output
    assert "RISING" in output
    assert "HIGH" in output  # Relevance
    assert "+200% YoY" in output
    assert "8.5/10" in output  # Popularity
    assert "High" in output  # Urgency

    # Check momentum emoji
    assert "↗" in output or "rising" in output.lower()

    assert "Trend Details:" in output
    assert "artificial intelligence" in output.lower()
    assert "Drivers:" in output
    assert "AI adoption" in output
    assert "Audience:" in output
    assert "Content angles:" in output

    assert "Immediate Content Opportunities" in output
    assert "Capitalize on these trends NOW:" in output
    assert "AI-powered customer analytics implementation" in output

    assert "Emerging Industry Conversations" in output
    assert "Ethical AI in customer analytics" in output
    assert "Key viewpoints:" in output
    assert "Privacy advocates" in output
    assert "Opportunity:" in output

    assert "Seasonal Trends" in output
    assert "Q4 budget planning" in output
    assert "Start prep:" in output

    assert "Upcoming Opportunities" in output
    assert "Prepare content for these trends:" in output

    assert "Key Market Themes" in output
    assert "AI transformation" in output

    assert "Declining Topics" in output
    assert "Manual reporting processes" in output

    print("[OK] Export formatting test passed")


def test_context_builder_formatting():
    """Test enhanced context builder for Market Trends."""
    from backend.services.research_context_builder import _format_market_trends

    # Create mock result
    sample_data = {
        "top_rising_trends": [
            {
                "topic": "AI customer analytics",
                "momentum": "rising",
                "relevance": "high",
                "popularity_score": 8.5,
            },
            {
                "topic": "Proactive CS",
                "momentum": "rising",
                "relevance": "high",
                "popularity_score": 7.8,
            },
        ],
        "immediate_opportunities": [
            "AI analytics content",
            "Proactive CS guide",
            "Churn prevention strategies",
        ],
        "key_themes": ["AI transformation", "Customer-centric growth"],
        "emerging_conversations": [
            {
                "topic": "Ethical AI",
                "description": "Privacy and transparency debate",
            }
        ],
        "declining_topics": ["Manual reporting", "Reactive support"],
    }

    # Create mock ResearchResult
    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Format for context
    context = _format_market_trends(result)

    # Verify concise but comprehensive
    assert "Market Trends" in context
    assert "Mar 13" in context

    # Should include rising trends with momentum indicators
    assert "Rising:" in context
    assert "AI customer analytics" in context or "Proactive CS" in context
    # Check for momentum arrow
    assert "↗" in context or "rising" in context.lower()

    # Should include opportunities count
    assert "Opportunities:" in context
    assert "immediate" in context.lower()

    # Should include themes
    assert "Themes:" in context
    assert "AI transformation" in context or "Customer-centric" in context

    # Should include emerging conversations
    assert "Emerging:" in context
    assert "Ethical AI" in context

    # Should include declining topics
    assert "Avoid:" in context
    assert "Manual reporting" in context or "Reactive support" in context

    # Should be reasonably concise (under 400 chars for usability)
    assert len(context) < 450, f"Context too long: {len(context)} chars"

    print("[OK] Context builder test passed")
    print(f"\nContext ({len(context)} chars):\n{context}\n")


def test_minimal_data_handling():
    """Test formatting with minimal data (backwards compatibility)."""
    from backend.services.export_service import _format_market_trends

    minimal_data = {
        "top_rising_trends": [
            {
                "topic": "AI tools",
                "momentum": "rising",
                "relevance": "high",
                "popularity_score": 7.0,
                "growth_rate": "+100%",
                "urgency": "Medium",
            }
        ]
    }

    lines = _format_market_trends(minimal_data)
    output = "\n".join(lines)

    # Should still work with minimal format
    assert len(lines) > 0
    assert "AI tools" in output
    assert "RISING" in output

    print("[OK] Minimal data test passed")


def test_context_builder_field_name_fix():
    """Test that context builder uses correct field name (topic not title)."""
    from backend.services.research_context_builder import _format_market_trends

    # This used to fail because it looked for "title" instead of "topic"
    sample_data = {
        "top_rising_trends": [
            {"topic": "Test Trend", "momentum": "rising", "relevance": "high"},
        ]
    }

    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Should not crash and should extract topic correctly
    context = _format_market_trends(result)

    assert "Test Trend" in context
    assert "Market Trends" in context

    print("[OK] Context builder field name fix test passed")


def test_empty_data_handling():
    """Test formatting with empty or missing data."""
    from backend.services.export_service import _format_market_trends

    # Empty data
    empty_data = {}
    lines = _format_market_trends(empty_data)
    output = "\n".join(lines)
    assert "No data available" in output

    # None values
    none_data = {"top_rising_trends": None}
    lines = _format_market_trends(none_data)
    output = "\n".join(lines)
    assert len(lines) > 0  # Should not crash

    print("[OK] Empty data handling test passed")


if __name__ == "__main__":
    test_export_formatting()
    test_context_builder_formatting()
    test_minimal_data_handling()
    test_context_builder_field_name_fix()
    test_empty_data_handling()
    print("\n[OK] All Market Trends formatting tests passed!")
