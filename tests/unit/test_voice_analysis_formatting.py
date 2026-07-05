"""Test Voice Analysis formatting improvements."""

import pytest
from datetime import datetime


def test_export_formatting():
    """Test enhanced export formatting for Voice Analysis."""
    from backend.services.export_service import _format_voice_analysis

    # Sample voice analysis data (subset of VoiceProfile)
    sample_data = {
        "summary": "Professional yet approachable tone with data-driven insights and conversational style",
        "primary_tone": "professional",
        "secondary_tone": "conversational",
        "formality_score": 6.5,
        "confidence_score": 8.2,
        "personality_traits": ["confident", "data_driven", "approachable"],
        "sentence_analysis": {"avg_length": 18.5, "variety_score": 7.2},
        "punctuation_analysis": {"exclamation_marks": 5, "questions": 8, "em_dashes": 3},
        "vocabulary_analysis": {"lexical_diversity": 0.65},
        "pronoun_focus": "you",
        "opening_patterns": [
            {"pattern_type": "question", "example": "Ever wondered why top performers..."},
            {"pattern_type": "stat", "example": "83% of marketers struggle with..."},
        ],
        "signature_phrases": [
            {"phrase": "Here's the thing", "count": 12},
            {"phrase": "At the end of the day", "count": 8},
        ],
        "cta_patterns": [{"cta_type": "question", "example": "What's your take?"}],
        "uses_data": True,
        "data_frequency": "frequently",
        "data_examples": ["Revenue grew 150% in Q2", "83% of users reported..."],
        "uses_bullets": True,
        "uses_emojis": False,
        "uses_formatting": True,
        "readability_score": 68.5,
        "reading_level": "8th-9th grade",
        "consistency_score": 7.8,
        "strengths": [
            "Clear and direct communication",
            "Good use of data to support points",
            "Engaging opening hooks",
        ],
        "improvement_areas": [
            "Vary sentence structure more",
            "Reduce reliance on signature phrases",
        ],
    }

    # Format the data
    lines = _format_voice_analysis(sample_data)
    output = "\n".join(lines)

    # Verify key sections are present
    assert "Voice Summary:" in output
    assert "professional yet approachable" in output.lower()

    assert "Tone & Personality" in output
    assert "professional" in output.lower()
    assert "conversational" in output.lower()
    assert "Formality:" in output
    assert "Confidence Level:" in output

    assert "Writing Patterns" in output
    assert "Sentence Length:" in output
    assert "18.5 words" in output

    assert "Content Patterns" in output
    assert "Common Openings:" in output
    assert "question" in output.lower()

    assert "Signature Phrases:" in output
    assert "Here's the thing" in output

    assert "CTA Style:" in output

    assert "Uses Data/Statistics:" in output
    assert "Frequently" in output

    assert "Readability" in output
    assert "68.5" in output or "68" in output

    assert "Voice Quality" in output
    assert "Strengths:" in output
    assert "Clear and direct communication" in output

    assert "Areas to Improve:" in output
    assert "Vary sentence structure" in output

    print("[OK] Export formatting test passed")
    print(f"\n{output[:500]}...\n")


def test_context_builder_formatting():
    """Test enhanced context builder for Voice Analysis."""
    from backend.services.research_context_builder import _format_voice_analysis
    from backend.models import ResearchResult

    # Create mock result
    sample_data = {
        "summary": "Professional yet approachable tone with data-driven insights",
        "primary_tone": "professional",
        "secondary_tone": "conversational",
        "formality_score": 6.5,
        "confidence_score": 8.2,
        "personality_traits": ["confident", "data_driven", "approachable"],
        "sentence_analysis": {"avg_length": 18.5},
        "pronoun_focus": "you",
        "signature_phrases": [{"phrase": "Here's the thing", "count": 12}],
        "uses_data": True,
        "data_frequency": "frequently",
        "uses_bullets": True,
        "readability_score": 68.5,
        "opening_patterns": [{"pattern_type": "question", "example": "Ever wondered..."}],
        "cta_patterns": [{"cta_type": "question", "example": "What's your take?"}],
    }

    # Create mock ResearchResult
    class MockResult:
        def __init__(self):
            self.data = sample_data
            self.created_at = datetime(2026, 3, 13)

    result = MockResult()

    # Format for context
    context = _format_voice_analysis(result)

    # Verify concise but comprehensive
    assert "Voice Analysis" in context
    assert "Mar 13" in context
    assert "professional" in context.lower()
    assert "conversational" in context.lower() or "casual" in context.lower()
    assert "confident" in context.lower() or "data_driven" in context.lower()
    assert "reader-focused" in context.lower() or "you" in context.lower()
    assert "data-driven" in context.lower() or "frequently" in context.lower()

    # Should be reasonably concise (under 500 chars for usability)
    assert len(context) < 600, f"Context too long: {len(context)} chars"

    print("[OK] Context builder test passed")
    print(f"\nContext ({len(context)} chars):\n{context}\n")


def test_minimal_data_handling():
    """Test formatting with minimal data (backwards compatibility)."""
    from backend.services.export_service import _format_voice_analysis

    minimal_data = {
        "tone": "professional",
        "readability_score": 65.0,
        "recommendations": ["Use more questions", "Vary sentence length"],
    }

    lines = _format_voice_analysis(minimal_data)
    output = "\n".join(lines)

    # Should still work with old format
    assert len(lines) > 0
    assert "professional" in output.lower()

    print("[OK] Minimal data test passed")


if __name__ == "__main__":
    test_export_formatting()
    test_context_builder_formatting()
    test_minimal_data_handling()
    print("\n[OK] All Voice Analysis formatting tests passed!")
