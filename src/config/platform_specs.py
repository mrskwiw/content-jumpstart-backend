"""Platform-specific content length specifications

Based on 2025 industry research and engagement data.
See: project/docs/platform_length_specifications_2025.md
"""

from typing import Any, Dict

from ..models.client_brief import Platform

# Platform length specifications
PLATFORM_LENGTH_SPECS: Dict[Platform, Dict[str, int]] = {
    Platform.LINKEDIN: {
        "min_words": 200,
        "optimal_min_words": 220,
        "optimal_max_words": 280,
        "max_words": 300,
        "min_chars": 800,
        "optimal_min_chars": 1200,
        "optimal_max_chars": 1800,
        "max_chars": 1800,
        "hook_chars": 140,  # Critical first chars before "see more"
    },
    Platform.TWITTER: {
        "min_words": 8,
        "optimal_min_words": 12,
        "optimal_max_words": 18,
        "max_words": 50,
        "min_chars": 40,
        "optimal_min_chars": 70,
        "optimal_max_chars": 100,
        "max_chars": 280,  # Free account limit / hard fail in validator
        "thread_mode": True,  # Can split into threads
        "thread_min_posts": 4,
        "thread_max_posts": 8,
    },
    Platform.FACEBOOK: {
        "min_words": 40,
        "optimal_min_words": 50,
        "optimal_max_words": 80,
        "max_words": 100,
        "min_chars": 200,
        "optimal_min_chars": 300,
        "optimal_max_chars": 500,
        "max_chars": 650,
    },
    Platform.BLOG: {
        "min_words": 800,
        "optimal_min_words": 1500,
        "optimal_max_words": 2000,
        "max_words": 3000,
        "min_chars": 4800,
        "optimal_min_chars": 9000,
        "optimal_max_chars": 12000,
        "max_chars": 18000,
    },
    Platform.EMAIL: {
        # Email newsletters - similar to LinkedIn
        "min_words": 100,
        "optimal_min_words": 150,
        "optimal_max_words": 250,
        "max_words": 300,
        "min_chars": 600,
        "optimal_min_chars": 900,
        "optimal_max_chars": 1500,
        "max_chars": 1800,
    },
}


# Hook/Opening requirements by platform
PLATFORM_HOOK_SPECS: Dict[Platform, Dict[str, Any]] = {
    Platform.LINKEDIN: {
        "hook_max_chars": 140,  # Mobile cutoff
        "hook_critical": True,
        "hook_must_contain_key_message": True,
        "description": "First 140 characters must contain key message (mobile 'see more' cutoff)",
    },
    Platform.TWITTER: {
        "hook_max_chars": 100,  # Entire post often IS the hook
        "hook_critical": True,
        "hook_must_contain_key_message": True,
        "description": "Entire post is the hook - punchy and direct",
    },
    Platform.FACEBOOK: {
        "hook_max_chars": 120,  # First sentence grabs attention
        "hook_critical": True,
        "hook_must_contain_key_message": True,
        "description": "First sentence hooks; full post delivers complete insight",
    },
    Platform.BLOG: {
        "hook_max_words": 50,  # Introduction paragraph
        "hook_critical": True,
        "hook_must_contain_key_message": False,  # Can build up to it
        "description": "Strong introduction paragraph to hook readers",
    },
    Platform.EMAIL: {
        "hook_max_chars": 100,  # Subject line + preview text
        "hook_critical": True,
        "hook_must_contain_key_message": True,
        "description": "Strong opening that follows compelling subject line",
    },
}


# Platform-specific writing guidelines
PLATFORM_WRITING_GUIDELINES: Dict[Platform, str] = {
    Platform.LINKEDIN: """
Target length: 220-280 words (MINIMUM 200 words — posts under 200 will fail validation).

CRITICAL: First 140 characters must contain your key message (mobile cutoff).

Guidelines:
- Professional but conversational tone
- Use line breaks every 2-3 sentences for readability
- Lead with value or insight in first line
- CTAs should be questions or invitations to comment
- Moderate use of emojis (1-2 max)
- Can include data/statistics
""",
    Platform.TWITTER: """
Target length: 70-100 characters (HARD FAIL at 280 characters — posts over 280 chars fail validation and will be regenerated).

Make every word count. Punchy and direct.

PRE-OUTPUT CHARACTER CHECK (MANDATORY):
Before returning your tweet, count the characters:
- If under 70 characters → expand slightly: add a concrete detail, a number, or a sharper CTA
- If over 100 characters → cut ruthlessly: remove filler words, shorten phrases, drop a hashtag
- If over 280 characters → DO NOT OUTPUT. Rewrite from scratch. This is a hard failure.

Guidelines:
- Ultra-concise — no filler words
- One clear idea per tweet
- 1-2 hashtags maximum (count their characters toward the 200 limit)
- Hooks matter — grab attention in the first 5 words
- Direct CTAs work well
""",
    Platform.FACEBOOK: """
Target length: 50-80 words (MINIMUM 40 words — posts under 40 words will fail validation).

Complete, self-contained post. Does NOT rely on an image to make sense.

Guidelines:
- Write a COMPLETE post — not a teaser or headline
- Conversational and relatable tone
- Short paragraphs (2-3 sentences max)
- Tell a small story, share a relatable observation, or deliver one clear insight
- Questions or relatable hooks drive engagement
- Emoji usage OK (1-2 max, if appropriate to brand voice)
- End with a CTA statement or a soft engagement question on the final line
""",
    Platform.BLOG: """
Target length: 1,500-2,000 words (MINIMUM 800 words — posts under 800 will fail validation).

SEO-optimized, well-structured blog post with headers and actionable insights.

Guidelines:
- Answer search intent fully with depth and examples
- Use H2 headers (##) for 4-6 main sections
- Include concrete examples, data, and actionable insights throughout
- Short paragraphs (2-3 sentences)
- Bullet points for scannability
- Strong introduction (hook + problem + preview) and conclusion (takeaways + CTA)
- Depth and thoroughness matter — cover the topic comprehensively
""",
    Platform.EMAIL: """
Target length: 150-250 words.

Personal and valuable - readers opted in to hear from you.

Guidelines:
- Strong subject line (hook before the hook)
- Personal greeting
- Conversational tone
- One clear value proposition
- Specific CTA (link, reply, action)
- Short paragraphs
- Signature adds personality
""",
}


def get_platform_target_length(platform: Platform) -> str:
    """Get human-readable target length for a platform"""
    specs = PLATFORM_LENGTH_SPECS.get(platform)
    if not specs:
        return "150-250 words"

    if platform == Platform.TWITTER:
        return "70-100 characters (~12-18 words)"
    if platform == Platform.FACEBOOK:
        return "50-80 words"

    optimal_min = specs.get("optimal_min_words", specs.get("min_words", 100))
    optimal_max = specs.get("optimal_max_words", specs.get("max_words", 250))

    return f"{optimal_min}-{optimal_max} words"


def get_platform_prompt_guidance(platform: Platform) -> str:
    """Get platform-specific writing guidance for prompts"""
    return PLATFORM_WRITING_GUIDELINES.get(platform, PLATFORM_WRITING_GUIDELINES[Platform.LINKEDIN])


def validate_platform_length(word_count: int, platform: Platform) -> tuple[bool, str]:
    """
    Validate if word count is appropriate for platform

    Returns:
        (is_optimal, feedback_message)
    """
    specs = PLATFORM_LENGTH_SPECS.get(platform)
    if not specs:
        return True, ""

    optimal_min = specs["optimal_min_words"]
    optimal_max = specs["optimal_max_words"]
    min_words = specs["min_words"]
    max_words = specs["max_words"]

    if word_count < min_words:
        return False, f"Too short for {platform.value} (min: {min_words} words)"
    elif word_count > max_words:
        return False, f"Too long for {platform.value} (max: {max_words} words)"
    elif word_count < optimal_min:
        return (
            False,
            f"Below optimal for {platform.value} (target: {optimal_min}-{optimal_max} words)",
        )
    elif word_count > optimal_max:
        return (
            False,
            f"Above optimal for {platform.value} (target: {optimal_min}-{optimal_max} words)",
        )
    else:
        return True, f"Optimal for {platform.value}"
