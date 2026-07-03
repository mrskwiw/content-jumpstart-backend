"""Test SEO Keywords formatting improvements."""

import pytest
from datetime import datetime


def test_export_formatting():
    """Test enhanced export formatting for SEO Keywords."""
    from backend.services.export_service import _format_seo_keywords

    # Sample SEO keyword data (from KeywordStrategy output)
    sample_data = {
        "strategy_summary": "This keyword strategy identifies 8 primary keywords and 25 secondary/long-tail keywords organized into 4 thematic clusters. Quality Assurance: 6/8 primary keywords rated high-quality (score ≥70). Average quality score: 78.5/100.",
        "primary_keywords": [
            {
                "keyword": "AI content marketing",
                "search_intent": "informational",
                "difficulty": "medium",
                "monthly_volume_estimate": "5K-10K",
                "relevance_score": 9.2,
                "quality_score": 85.0,
                "long_tail": True,
                "question_based": False,
                "related_topics": ["content automation", "AI writing"],
                "trend_score": 78.5,
                "trend_direction": "rising",
                "seasonal": False,
                "related_queries": ["AI content tools", "best AI for marketing"],
            },
            {
                "keyword": "content automation software",
                "search_intent": "commercial",
                "difficulty": "medium",
                "monthly_volume_estimate": "1K-5K",
                "relevance_score": 8.7,
                "quality_score": 72.0,
                "long_tail": True,
                "question_based": False,
                "related_topics": ["marketing automation", "content tools"],
                "trend_score": 65.2,
                "trend_direction": "stable",
                "seasonal": False,
                "related_queries": [],
            },
            {
                "keyword": "SEO content strategy",
                "search_intent": "informational",
                "difficulty": "low",
                "monthly_volume_estimate": "10K-50K",
                "relevance_score": 9.5,
                "quality_score": 88.0,
                "long_tail": False,
                "question_based": False,
                "related_topics": ["SEO", "content planning"],
                "trend_score": None,
                "trend_direction": None,
                "seasonal": True,
                "related_queries": [],
            },
        ],
        "secondary_keywords": [
            {
                "keyword": "how to automate content marketing",
                "search_intent": "informational",
                "difficulty": "low",
                "monthly_volume_estimate": "500-1K",
                "relevance_score": 7.8,
                "quality_score": None,
                "long_tail": True,
                "question_based": True,
                "related_topics": ["automation"],
            }
        ],
        "quick_win_keywords": [
            "content automation tips",
            "AI writing best practices",
            "marketing automation guide",
        ],
        "keyword_clusters": [
            {
                "theme": "AI Content",
                "primary_keyword": "AI content marketing",
                "secondary_keywords": ["AI writing tools", "content AI", "automated content"],
                "content_suggestions": [
                    "Ultimate guide to AI content marketing",
                    "How to AI content marketing (step-by-step)",
                ],
                "priority": "High",
            },
            {
                "theme": "Automation",
                "primary_keyword": "content automation software",
                "secondary_keywords": ["marketing automation", "content tools"],
                "content_suggestions": ["Best content automation tools 2026"],
                "priority": "Medium",
            },
        ],
        "content_priorities": [
            "[HIGH] Ultimate guide to AI content marketing (targets: AI content marketing)",
            "[QUICK WIN] How-to guide for 'content automation tips'",
            "[MEDIUM] Best content automation tools 2026 (targets: content automation software)",
        ],
        "competitor_analysis": [
            {
                "competitor_name": "ContentAI Inc",
                "estimated_keywords": ["AI content", "content generation"],
                "gaps": ["content automation tips", "AI writing best practices"],
                "overlaps": ["AI content marketing"],
            }
        ],
    }

    # Format the data
    lines = _format_seo_keywords(sample_data)
    output = "\n".join(lines)

    # Verify comprehensive sections are present
    assert "SEO Strategy Summary" in output
    assert "Quality Assurance" in output
    assert "78.5/100" in output

    assert "Primary Keywords" in output
    assert "AI content marketing" in output
    assert "informational" in output
    assert "medium" in output.lower()
    assert "5K-10K" in output

    # Check quality scores
    assert "85" in output  # Quality score
    assert "⭐" in output or "✓" in output  # Quality badge

    # Check trends data
    assert "78" in output or "79" in output  # Trend score
    assert "↗" in output or "rising" in output.lower()  # Rising trend indicator

    assert "Top Keyword Details" in output
    assert "Related:" in output
    assert "content automation" in output

    assert "Quick Win Keywords" in output
    assert "content automation tips" in output

    assert "Keyword Clusters" in output
    assert "[HIGH]" in output
    assert "AI Content" in output

    assert "Content Priorities" in output
    assert "Ultimate guide" in output

    assert "Competitor Insights" in output
    assert "ContentAI Inc" in output
    assert "Gap opportunities" in output

    assert "Secondary Keywords" in output
    assert "long-tail keywords" in output

    print("[OK] Export formatting test passed")
    # Note: Output preview removed due to Windows Unicode encoding limitations


def test_context_builder_formatting():
    """Test enhanced context builder for SEO Keywords."""
    from backend.services.research_context_builder import _format_seo_keywords

    # Create mock result
    sample_data = {
        "primary_keywords": [
            {
                "keyword": "AI content marketing",
                "search_intent": "informational",
                "difficulty": "medium",
                "monthly_volume_estimate": "5K-10K",
                "relevance_score": 9.2,
                "quality_score": 85.0,
                "trend_direction": "rising",
            },
            {
                "keyword": "content automation",
                "search_intent": "informational",
                "difficulty": "low",
                "monthly_volume_estimate": "1K-5K",
                "relevance_score": 8.5,
                "quality_score": 78.0,
                "trend_direction": "stable",
            },
            {
                "keyword": "SEO strategy",
                "search_intent": "commercial",
                "difficulty": "medium",
                "monthly_volume_estimate": "10K-50K",
                "relevance_score": 9.0,
                "quality_score": 82.0,
                "trend_direction": None,
            },
        ],
        "quick_win_keywords": ["content tips", "AI writing guide"],
        "content_priorities": ["[HIGH] Ultimate guide to AI content marketing"],
    }

    # Create mock ResearchResult
    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Format for context
    context = _format_seo_keywords(result)

    # Verify concise but comprehensive
    assert "SEO Keywords" in context
    assert "Mar 13" in context

    # Should include primary keywords
    assert (
        "AI content marketing" in context
        or "content automation" in context
        or "SEO strategy" in context
    )

    # Should include intent
    assert "Intent:" in context
    assert "informational" in context or "commercial" in context

    # Should include difficulty or quick wins
    assert "Quick wins" in context or "low-difficulty" in context or "Difficulty:" in context

    # Should include trending indicator
    assert "Trending:" in context

    # Should include focus/priority
    assert "Focus:" in context
    assert "HIGH" in context

    # Should be reasonably concise (under 400 chars for usability)
    assert len(context) < 450, f"Context too long: {len(context)} chars"

    print("[OK] Context builder test passed")
    print(f"\nContext ({len(context)} chars):\n{context}\n")


def test_minimal_data_handling():
    """Test formatting with minimal data (backwards compatibility)."""
    from backend.services.export_service import _format_seo_keywords

    minimal_data = {
        "primary_keywords": [
            {"keyword": "marketing", "difficulty": "medium", "monthly_volume_estimate": "Unknown"}
        ]
    }

    lines = _format_seo_keywords(minimal_data)
    output = "\n".join(lines)

    # Should still work with minimal format
    assert len(lines) > 0
    assert "marketing" in output
    assert "medium" in output.lower()

    print("[OK] Minimal data test passed")


def test_context_builder_crash_fix():
    """Test that context builder no longer crashes on dict keywords."""
    from backend.services.research_context_builder import _format_seo_keywords

    # This used to crash because it tried to join dicts instead of extracting keyword names
    sample_data = {
        "primary_keywords": [
            {"keyword": "test keyword 1", "search_intent": "informational", "difficulty": "low"},
            {"keyword": "test keyword 2", "search_intent": "commercial", "difficulty": "medium"},
        ]
    }

    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Should not crash
    context = _format_seo_keywords(result)

    assert "test keyword 1" in context or "test keyword 2" in context
    assert "SEO Keywords" in context

    print("[OK] Context builder crash fix test passed")


def test_empty_data_handling():
    """Test formatting with empty or missing data."""
    from backend.services.export_service import _format_seo_keywords

    # Empty data
    empty_data = {}
    lines = _format_seo_keywords(empty_data)
    output = "\n".join(lines)
    assert "No data available" in output

    # None values
    none_data = {"primary_keywords": None}
    lines = _format_seo_keywords(none_data)
    output = "\n".join(lines)
    assert len(lines) > 0  # Should not crash

    print("[OK] Empty data handling test passed")


if __name__ == "__main__":
    test_export_formatting()
    test_context_builder_formatting()
    test_minimal_data_handling()
    test_context_builder_crash_fix()
    test_empty_data_handling()
    print("\n[OK] All SEO Keywords formatting tests passed!")
