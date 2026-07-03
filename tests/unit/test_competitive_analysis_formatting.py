"""Test Competitive Analysis formatting improvements."""

import pytest
from datetime import datetime


def test_export_formatting():
    """Test enhanced export formatting for Competitive Analysis."""
    from backend.services.export_service import _format_competitive_analysis

    # Sample competitive analysis data (from CompetitiveAnalysis output)
    sample_data = {
        "business_name": "Acme Analytics",
        "industry": "B2B SaaS - Customer Success",
        "analysis_date": "2026-03-13",
        "market_summary": "The customer success platform market is moderately saturated with 5-7 major players. Competition focuses on feature breadth rather than thought leadership. Content quality varies widely, creating opportunities for well-researched, actionable content.",
        "market_saturation": "Medium - established players but room for differentiation",
        "competitors": [
            {
                "name": "ChurnZero",
                "positioning": "All-in-one customer success platform for SaaS",
                "target_audience": "Mid-market and enterprise SaaS companies",
                "content_types": ["blog_posts", "webinars", "case_studies"],
                "content_frequency": "2-3x per week",
                "content_topics": [
                    "Customer retention",
                    "Churn reduction",
                    "CS best practices",
                ],
                "brand_voice": "Professional, authoritative, data-driven",
                "tone_descriptors": ["Confident", "Educational", "Corporate"],
                "strengths": [
                    "Strong brand recognition",
                    "Comprehensive feature set",
                    "Good SEO presence",
                ],
                "weaknesses": [
                    "Generic content approach",
                    "Limited thought leadership",
                    "Infrequent video content",
                ],
                "estimated_reach": "50K+ monthly visitors",
                "engagement_level": "moderate",
            },
            {
                "name": "Gainsight",
                "positioning": "Customer success platform for enterprise",
                "target_audience": "Enterprise SaaS and subscription companies",
                "content_types": ["blog_posts", "ebooks", "whitepapers"],
                "content_frequency": "1-2x per week",
                "content_topics": ["Customer success", "Product-led growth", "NPS"],
                "brand_voice": "Executive-focused, strategic, high-level",
                "tone_descriptors": ["Professional", "Strategic", "Executive"],
                "strengths": ["Enterprise focus", "High-quality whitepapers"],
                "weaknesses": ["Less frequent content", "Limited tactical guidance"],
                "estimated_reach": "75K+ monthly visitors",
                "engagement_level": "strong",
            },
        ],
        "content_gaps": [
            {
                "topic": "Predictive churn analytics",
                "description": "Deep technical content on predictive models and early warning systems",
                "opportunity_score": 8.5,
                "competitors_missing": ["ChurnZero", "Totango"],
                "suggested_content": [
                    "Building a predictive churn model: Technical guide",
                    "35-day early warning system explained",
                    "Machine learning for customer success",
                ],
            },
            {
                "topic": "Proactive intervention strategies",
                "description": "Tactical playbooks for preventing churn before it happens",
                "opportunity_score": 7.8,
                "competitors_missing": ["ChurnZero"],
                "suggested_content": [
                    "Intervention playbook for at-risk accounts",
                    "When and how to reach out to churning customers",
                ],
            },
        ],
        "quick_wins": [
            "Create technical guide on predictive analytics (no competitor coverage)",
            "Publish case study with specific ROI metrics",
            "Launch video series on tactical CS strategies",
            "Develop interactive churn calculator",
        ],
        "differentiation_strategies": [
            {
                "strategy_name": "Technical Depth",
                "description": "Go deeper on technical implementation than competitors - target data teams and technical CS leaders",
                "difficulty": "Medium",
                "potential_impact": "High",
                "examples": [
                    "Detailed ML model architecture content",
                    "API integration guides",
                    "Data engineering for CS",
                ],
            },
            {
                "strategy_name": "ROI Transparency",
                "description": "Share specific metrics and ROI data that competitors keep vague",
                "difficulty": "Low",
                "potential_impact": "High",
                "examples": [
                    "Publish case studies with actual $ saved",
                    "Show before/after churn rates",
                    "Share customer success metrics openly",
                ],
            },
        ],
        "recommended_position": {
            "positioning_statement": "The predictive customer success platform for data-driven SaaS teams who want measurable churn reduction, not just features.",
            "unique_angles": [
                "35-day predictive warning system (specific, measurable)",
                "47 behavioral signals analyzed (technical credibility)",
                "Average 40% churn reduction (ROI-focused)",
            ],
            "competitive_advantages": [
                "More technical depth than ChurnZero",
                "More actionable than Gainsight",
                "Stronger ROI focus than competitors",
                "Better content for technical audiences",
            ],
            "areas_to_improve": [
                "Build more enterprise case studies",
                "Increase content publishing frequency",
                "Develop more video content",
            ],
        },
        "priority_actions": [
            "Create 3 technical deep-dive guides on predictive analytics",
            "Publish 2 ROI-focused case studies with specific metrics",
            "Launch monthly webinar series on CS tactics",
            "Develop churn prediction calculator tool",
            "Write comparison content (Acme vs competitors)",
        ],
        "competitive_threats": [
            "Gainsight expanding into mid-market with aggressive pricing",
            "ChurnZero improving content quality and publishing frequency",
            "New AI-focused CS startups entering the market",
        ],
    }

    # Format the data
    lines = _format_competitive_analysis(sample_data)
    output = "\n".join(lines)

    # Verify comprehensive sections are present
    assert "Competitive Landscape Overview" in output
    assert "moderately saturated" in output
    assert "Medium - established players" in output

    # Competitor profiles with full details
    assert "Competitor Profiles" in output
    assert "ChurnZero" in output
    assert "Gainsight" in output

    # Positioning
    assert "All-in-one customer success platform" in output
    assert "Mid-market and enterprise" in output

    # Content strategy
    assert "Content Strategy" in output or "Formats:" in output
    assert "2-3x per week" in output or "1-2x per week" in output
    assert "Customer retention" in output or "Churn reduction" in output

    # Voice and tone
    assert "Voice & Tone" in output or "brand_voice" in output.lower()
    assert "Professional" in output or "authoritative" in output

    # Strengths and weaknesses
    assert "Strengths" in output
    assert "Strong brand recognition" in output or "Enterprise focus" in output
    assert "Weaknesses" in output or "Your Opportunity" in output
    assert "Generic content approach" in output or "Limited thought leadership" in output

    # Reach and engagement
    assert "50K+" in output or "75K+" in output
    assert "MODERATE" in output or "STRONG" in output

    # Content gaps
    assert "Content Gap Opportunities" in output
    assert "Predictive churn analytics" in output
    assert "8.5/10" in output  # Opportunity score
    assert "HIGH OPPORTUNITY" in output or "MEDIUM OPPORTUNITY" in output
    assert "ChurnZero" in output or "Totango" in output  # Competitors missing
    assert "Building a predictive churn model" in output

    # Quick wins
    assert "Quick Win Opportunities" in output
    assert "Create technical guide on predictive analytics" in output

    # Differentiation strategies
    assert "Differentiation Strategies" in output
    assert "Technical Depth" in output
    assert "ROI Transparency" in output
    assert "Medium" in output and "High" in output  # Difficulty and impact
    assert "Detailed ML model architecture" in output

    # Recommended positioning
    assert "Recommended Market Positioning" in output
    assert "Positioning Statement" in output
    assert "predictive customer success platform" in output
    assert "Unique Angles" in output
    assert "35-day predictive warning" in output
    assert "Competitive Advantages" in output
    assert "More technical depth" in output
    assert "Areas to Improve" in output
    assert "Build more enterprise case studies" in output

    # Priority actions
    assert "Priority Actions" in output
    assert "Create 3 technical deep-dive guides" in output

    # Competitive threats
    assert "Competitive Threats" in output
    assert "Gainsight expanding into mid-market" in output

    print("[OK] Export formatting test passed")


def test_context_builder_formatting():
    """Test enhanced context builder for Competitive Analysis."""
    from backend.services.research_context_builder import _format_competitive_analysis

    # Create mock result
    sample_data = {
        "competitors": [
            {"name": "ChurnZero"},
            {"name": "Gainsight"},
            {"name": "Totango"},
        ],
        "quick_wins": [
            "Create technical guide on predictive analytics",
            "Publish ROI-focused case study",
        ],
        "content_gaps": [
            {
                "topic": "Predictive churn analytics",
                "opportunity_score": 8.5,
            },
            {
                "topic": "Proactive intervention strategies",
                "opportunity_score": 7.2,
            },
        ],
        "differentiation_strategies": [
            {
                "strategy_name": "Technical Depth",
                "potential_impact": "High",
            },
            {
                "strategy_name": "ROI Transparency",
                "potential_impact": "High",
            },
        ],
        "recommended_position": {
            "positioning_statement": "The predictive customer success platform for data-driven SaaS teams",
        },
        "competitive_threats": [
            "Gainsight expanding into mid-market",
            "New AI-focused CS startups",
        ],
    }

    # Create mock ResearchResult
    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Format for context
    context = _format_competitive_analysis(result)

    # Verify concise but comprehensive
    assert "Competitive Analysis" in context
    assert "Mar 13" in context

    # Should include competitor count
    assert "3 competitors" in context

    # Should include quick wins
    assert "Quick Wins:" in context
    assert "technical guide" in context or "ROI-focused" in context

    # Should include content gaps with high scores
    assert "Gaps:" in context
    assert "Predictive churn analytics" in context or "Proactive intervention" in context
    assert "(high)" in context  # High opportunity score indicator

    # Should include differentiation strategies (fixed field name)
    assert "Differentiate:" in context
    assert "Technical Depth" in context or "ROI Transparency" in context

    # Should include positioning (fixed field name)
    assert "Position:" in context
    assert "predictive customer success" in context

    # Should include competitive threats
    assert "Watch:" in context
    assert "Gainsight" in context or "mid-market" in context

    # Should be reasonably concise (under 450 chars for usability)
    assert len(context) < 500, f"Context too long: {len(context)} chars"

    print("[OK] Context builder test passed")
    print(f"\nContext ({len(context)} chars):\n{context}\n")


def test_minimal_data_handling():
    """Test formatting with minimal data (backwards compatibility)."""
    from backend.services.export_service import _format_competitive_analysis

    minimal_data = {
        "competitors": [
            {
                "name": "Competitor A",
                "positioning": "Market leader",
            }
        ]
    }

    lines = _format_competitive_analysis(minimal_data)
    output = "\n".join(lines)

    # Should still work with minimal format
    assert len(lines) > 0
    assert "Competitor A" in output
    assert "Market leader" in output

    print("[OK] Minimal data test passed")


def test_field_name_fixes():
    """Test that context builder uses correct field names."""
    from backend.services.research_context_builder import _format_competitive_analysis

    # This used to fail because it looked for wrong field names
    sample_data = {
        "differentiation_strategies": [
            {
                "strategy_name": "Test Strategy",  # Correct field name
                "potential_impact": "High",
            }
        ],
        "recommended_position": {
            "positioning_statement": "Test positioning",  # Correct field name
        },
    }

    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Should not crash and should extract fields correctly
    context = _format_competitive_analysis(result)

    assert "Test Strategy" in context  # Fixed: extracts strategy_name correctly
    assert "Test positioning" in context  # Fixed: extracts positioning_statement correctly
    assert "Competitive Analysis" in context

    print("[OK] Field name fix test passed")


def test_empty_data_handling():
    """Test formatting with empty or missing data."""
    from backend.services.export_service import _format_competitive_analysis

    # Empty data
    empty_data = {}
    lines = _format_competitive_analysis(empty_data)
    output = "\n".join(lines)
    assert "No data available" in output

    # None values
    none_data = {"competitors": None}
    lines = _format_competitive_analysis(none_data)
    output = "\n".join(lines)
    assert len(lines) > 0  # Should not crash

    print("[OK] Empty data handling test passed")


if __name__ == "__main__":
    test_export_formatting()
    test_context_builder_formatting()
    test_minimal_data_handling()
    test_field_name_fixes()
    test_empty_data_handling()
    print("\n[OK] All Competitive Analysis formatting tests passed!")
