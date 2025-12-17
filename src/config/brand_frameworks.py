"""
Brand framework definitions and writing principles.

Extracted from content-creator skill's brand_guidelines.md to provide
expert copywriting frameworks for content generation.
"""

from typing import Dict, List

# Brand Personality Archetypes
# Based on proven brand voice frameworks
BRAND_ARCHETYPES: Dict[str, Dict[str, str]] = {
    "Expert": {
        "tone": "Knowledgeable, confident, informative",
        "content_style": "Data-driven, research-backed, educational",
        "example_phrase": "Our research shows that 87% of businesses...",
        "when_to_use": "B2B SaaS, consulting, professional services",
        "formality": "professional",
        "typical_perspective": "authoritative",
    },
    "Friend": {
        "tone": "Warm, supportive, conversational",
        "content_style": "Relatable, helpful, encouraging",
        "example_phrase": "We get it - marketing can be overwhelming...",
        "when_to_use": "Consumer brands, coaching, community-focused",
        "formality": "conversational",
        "typical_perspective": "collaborative",
    },
    "Innovator": {
        "tone": "Visionary, bold, forward-thinking",
        "content_style": "Cutting-edge, disruptive, trendsetting",
        "example_phrase": "The future of marketing is here...",
        "when_to_use": "Startups, tech companies, disruptive products",
        "formality": "professional",
        "typical_perspective": "authoritative",
    },
    "Guide": {
        "tone": "Wise, patient, instructive",
        "content_style": "Step-by-step, clear, actionable",
        "example_phrase": "Let's walk through this together...",
        "when_to_use": "Education, training, how-to content",
        "formality": "conversational",
        "typical_perspective": "collaborative",
    },
    "Motivator": {
        "tone": "Energetic, positive, inspiring",
        "content_style": "Empowering, action-oriented, transformative",
        "example_phrase": "You have the power to transform your business...",
        "when_to_use": "Coaches, self-improvement, transformation services",
        "formality": "conversational",
        "typical_perspective": "conversational",
    },
}


# Writing Principles for Quality Content
WRITING_PRINCIPLES: Dict[str, List[str]] = {
    # Strong action verbs to use
    "action_verbs": [
        "transform",
        "accelerate",
        "optimize",
        "unlock",
        "elevate",
        "streamline",
        "amplify",
        "revolutionize",
        "maximize",
        "empower",
        "discover",
        "create",
        "build",
        "achieve",
        "master",
    ],
    # Positive descriptors for products/services
    "positive_descriptors": [
        "seamless",
        "powerful",
        "intuitive",
        "strategic",
        "comprehensive",
        "efficient",
        "effective",
        "proven",
        "reliable",
        "innovative",
        "flexible",
        "scalable",
        "user-friendly",
        "cutting-edge",
    ],
    # Outcome-focused language
    "outcome_focused": [
        "results",
        "growth",
        "success",
        "impact",
        "ROI",
        "performance",
        "productivity",
        "efficiency",
        "revenue",
        "engagement",
        "conversion",
        "retention",
        "value",
    ],
    # Words to avoid (weak or overused)
    "avoid_words": [
        # Jargon
        "synergy",
        "leverage",
        "bandwidth",
        "circle back",
        "touch base",
        "low-hanging fruit",
        "move the needle",
        # Weak modifiers
        "very",
        "really",
        "just",
        "quite",
        "fairly",
        "pretty",
        "somewhat",
        "maybe",
        "hopefully",
        # Overused buzzwords (unless genuinely applicable)
        "game-changer",
        "revolutionary",
        "disruptive",
        "next-generation",
        "best-in-class",
        "world-class",
        # Negative framing
        "problem",
        "can't",
        "won't",
        "impossible",
        "never",
    ],
}


# Customer-Centric Language Guidelines
CUSTOMER_CENTRIC_PRINCIPLES: Dict[str, str] = {
    "focus_on_benefits": "Emphasize outcomes and benefits over features",
    "use_you_over_we": "Address reader directly with 'you' more than talking about 'we'",
    "address_pain_points": "Acknowledge customer challenges before offering solutions",
    "include_social_proof": "Reference customer success stories and results",
    "clear_next_steps": "Always provide actionable next steps or CTAs",
}


def get_archetype_guidance(archetype_name: str) -> str:
    """
    Get formatted guidance for a specific brand archetype.

    Args:
        archetype_name: One of: Expert, Friend, Innovator, Guide, Motivator

    Returns:
        Formatted string with archetype guidance for prompts
    """
    archetype = BRAND_ARCHETYPES.get(archetype_name)

    if not archetype:
        return ""

    return f"""
BRAND ARCHETYPE: {archetype_name}
- Tone: {archetype['tone']}
- Content Style: {archetype['content_style']}
- Example: {archetype['example_phrase']}
"""


def get_writing_principles_guidance() -> str:
    """
    Get formatted writing principles for inclusion in prompts.

    Returns:
        Formatted string with writing principles
    """
    return f"""
WRITING PRINCIPLES:

Use Strong Action Verbs:
{', '.join(WRITING_PRINCIPLES['action_verbs'][:10])}

Use Positive Descriptors:
{', '.join(WRITING_PRINCIPLES['positive_descriptors'][:10])}

Focus on Outcomes:
{', '.join(WRITING_PRINCIPLES['outcome_focused'][:10])}

AVOID These Words:
{', '.join(WRITING_PRINCIPLES['avoid_words'][:15])}
"""


def infer_archetype_from_voice_dimensions(
    formality_dominant: str, tone_dominant: str, perspective_dominant: str
) -> str:
    """
    Infer brand archetype from voice dimension analysis.

    Args:
        formality_dominant: Dominant formality level
        tone_dominant: Dominant tone characteristic
        perspective_dominant: Dominant perspective

    Returns:
        Best-fit archetype name
    """
    # Mapping logic based on voice dimensions
    if formality_dominant == "formal" or formality_dominant == "professional":
        if tone_dominant == "authoritative":
            return "Expert"
        elif tone_dominant == "innovative":
            return "Innovator"
        else:
            return "Expert"  # Default for professional/formal

    elif formality_dominant == "conversational":
        if tone_dominant == "friendly":
            return "Friend"
        elif tone_dominant == "educational":
            return "Guide"
        elif perspective_dominant == "conversational":
            return "Motivator"
        else:
            return "Guide"  # Default for conversational

    elif formality_dominant == "casual":
        if tone_dominant == "friendly":
            return "Friend"
        else:
            return "Motivator"

    # Default fallback
    return "Guide"


def get_archetype_from_client_type(client_type: str) -> str:
    """
    Get recommended archetype based on client type.

    Args:
        client_type: Client classification (B2B_SAAS, AGENCY, etc.)

    Returns:
        Recommended archetype name
    """
    archetype_mapping = {
        "B2B_SAAS": "Expert",
        "AGENCY": "Expert",
        "COACH_CONSULTANT": "Guide",
        "CREATOR_FOUNDER": "Friend",
        "UNKNOWN": "Guide",  # Safe default
    }

    return archetype_mapping.get(client_type, "Guide")
