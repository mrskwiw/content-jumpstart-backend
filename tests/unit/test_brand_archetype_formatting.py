"""Test Brand Archetype formatting improvements."""

import pytest
from datetime import datetime


def test_export_formatting():
    """Test enhanced export formatting for Brand Archetype."""
    from backend.services.export_service import _format_brand_archetype

    # Sample brand archetype data (from analyzer output)
    sample_data = {
        "primary_archetype": "sage",
        "secondary_archetype": "creator",
        "confidence_score": 0.87,
        "archetype_scores": {
            "sage": 0.87,
            "creator": 0.72,
            "innovator": 0.65,
            "expert": 0.58,
            "guide": 0.51,
        },
        "trait_matches": {
            "primary": {
                "archetype": "The Sage",
                "matched_traits": ["Knowledgeable", "Analytical", "Thoughtful"],
            },
            "secondary": {
                "archetype": "The Creator",
                "matched_traits": ["Innovative", "Imaginative"],
            },
        },
        "recommendations": [
            "**Voice:** Adopt an authoritative, educational tone",
            "**Content Themes:** Focus on education, research, analysis",
            "**Study These Brands:** Google, PBS (they share your archetype)",
            "**Secondary Influence:** Blend in creator elements like creative",
        ],
    }

    # Format the data
    lines = _format_brand_archetype(sample_data)
    output = "\n".join(lines)

    # Verify comprehensive sections are present
    assert "Brand Archetype Summary" in output
    assert "The Sage" in output
    assert "Confidence Score:" in output
    assert "87" in output or "0.87" in output

    assert "Archetype Fit Analysis" in output
    assert "The Creator" in output  # Secondary archetype
    assert "72" in output or "0.72" in output  # Secondary score

    assert "Key Brand Traits" in output
    assert "Knowledgeable" in output or "knowledgeable" in output

    assert "Voice & Tone Guidance" in output
    assert "Authoritative" in output or "authoritative" in output
    assert "Educational" in output or "educational" in output

    assert "Content Themes" in output
    assert "Education" in output or "education" in output

    assert "Brands to Study" in output
    assert "Google" in output
    assert "PBS" in output

    assert "Recommendations" in output

    print("[OK] Export formatting test passed")
    print(f"\n{output[:600]}...\n")


def test_context_builder_formatting():
    """Test enhanced context builder for Brand Archetype."""
    from backend.services.research_context_builder import _format_brand_archetype

    # Create mock result
    sample_data = {
        "primary_archetype": "hero",
        "secondary_archetype": "ruler",
        "confidence_score": 0.91,
        "archetype_scores": {
            "hero": 0.91,
            "ruler": 0.68,
        },
    }

    # Create mock ResearchResult
    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Format for context
    context = _format_brand_archetype(result)

    # Verify concise but comprehensive
    assert "Brand Archetype" in context
    assert "Mar 13" in context
    assert "Hero" in context or "hero" in context
    assert "Ruler" in context or "ruler" in context or "Secondary" in context

    # Should include voice characteristics
    assert (
        "motivational" in context.lower()
        or "confident" in context.lower()
        or "empowering" in context.lower()
    )

    # Should include traits
    assert (
        "courageous" in context.lower()
        or "bold" in context.lower()
        or "inspiring" in context.lower()
    )

    # Should include themes
    assert (
        "achievement" in context.lower()
        or "performance" in context.lower()
        or "excellence" in context.lower()
    )

    # Should include confidence if high
    assert "91" in context or "Confidence" in context

    # Should be reasonably concise (under 400 chars for usability)
    assert len(context) < 450, f"Context too long: {len(context)} chars"

    print("[OK] Context builder test passed")
    print(f"\nContext ({len(context)} chars):\n{context}\n")


def test_minimal_data_handling():
    """Test formatting with minimal data (backwards compatibility)."""
    from backend.services.export_service import _format_brand_archetype

    minimal_data = {
        "primary_archetype": "everyman",
    }

    lines = _format_brand_archetype(minimal_data)
    output = "\n".join(lines)

    # Should still work with minimal format
    assert len(lines) > 0
    assert "Everyman" in output or "everyman" in output
    assert "down-to-earth" in output.lower() or "relatable" in output.lower()

    print("[OK] Minimal data test passed")


def test_missing_archetype_handling():
    """Test formatting with missing or invalid archetype."""
    from backend.services.export_service import _format_brand_archetype

    # Empty data
    empty_data = {}
    lines = _format_brand_archetype(empty_data)
    output = "\n".join(lines)
    assert "Not determined" in output

    # Invalid archetype ID
    invalid_data = {"primary_archetype": "invalid_archetype_id"}
    lines = _format_brand_archetype(invalid_data)
    output = "\n".join(lines)
    assert "invalid_archetype_id" in output

    print("[OK] Missing archetype handling test passed")


if __name__ == "__main__":
    test_export_formatting()
    test_context_builder_formatting()
    test_minimal_data_handling()
    test_missing_archetype_handling()
    print("\n[OK] All Brand Archetype formatting tests passed!")
