"""System-wide constants and configuration values

This module centralizes all magic numbers and constants used throughout
the Content Jumpstart system. Centralizing these values makes it easier to:
- Adjust thresholds and limits from one place
- Understand system constraints
- Maintain consistency across modules
- Document the reasoning behind specific values
"""

# ============================================================================
# POST LENGTH CONSTRAINTS
# ============================================================================

# Minimum word count for engagement (too short feels incomplete)
MIN_POST_WORD_COUNT = 75

# Maximum word count (LinkedIn character limit consideration)
MAX_POST_WORD_COUNT = 350

# Optimal range for maximum engagement
OPTIMAL_POST_MIN_WORDS = 150
OPTIMAL_POST_MAX_WORDS = 250

# ============================================================================
# VALIDATION THRESHOLDS
# ============================================================================

# Hook similarity threshold (0.0-1.0, higher = more similar)
# Hooks with 80%+ similarity are considered duplicates
HOOK_SIMILARITY_THRESHOLD = 0.80

# CTA variety threshold (minimum ratio of unique CTA types)
# Require at least 40% variety in calls-to-action
CTA_VARIETY_THRESHOLD = 0.40

# Minimum engagement elements in headlines
# Strong hooks should have at least 3 elements (questions, numbers, power words)
MIN_HEADLINE_ELEMENTS = 3

# ============================================================================
# API RATE LIMITING
# ============================================================================

# Maximum concurrent API calls to prevent rate limiting
DEFAULT_MAX_CONCURRENT_CALLS = 5

# Batch size for parallel processing
DEFAULT_BATCH_SIZE = 10

# Initial retry delay in seconds (exponential backoff)
DEFAULT_RETRY_DELAY = 1.0

# Maximum number of API retries on failure
DEFAULT_MAX_RETRIES = 3

# API timeout in seconds
DEFAULT_API_TIMEOUT = 120

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

# Maximum number of template sets to cache in memory
TEMPLATE_CACHE_MAX_SIZE = 100

# Template cache TTL in seconds (1 hour)
TEMPLATE_CACHE_TTL = 3600

# API response cache TTL in seconds (24 hours)
RESPONSE_CACHE_TTL = 86400

# Enable response caching (dev/testing only)
ENABLE_RESPONSE_CACHE_DEFAULT = False

# ============================================================================
# CONTENT GENERATION
# ============================================================================

# Default number of templates to use per client
DEFAULT_TEMPLATE_COUNT = 15

# Default number of posts to generate
DEFAULT_POST_COUNT = 30

# Default number of uses per template (30 posts / 15 templates = 2)
DEFAULT_USES_PER_TEMPLATE = 2

# Randomize output order by default
DEFAULT_RANDOMIZE_OUTPUT = True

# ============================================================================
# AI TELL PHRASES TO AVOID
# ============================================================================
# These phrases are overused by AI and should be avoided for authenticity

AI_TELL_PHRASES = [
    "in today's world",
    "in today's digital landscape",
    "dive deep",
    "deep dive",
    "unlock",
    "unlock the power",
    "game-changer",
    "game changer",
    "revolutionize",
    "revolutionary",
    "cutting-edge",
    "cutting edge",
    "leverage",
    "leveraging",
    "seamless",
    "seamlessly",
    "robust",
    "elevate",
    "transform",
    "transformative",
    "empower",
    "empowering",
    "optimize",
    "optimization",
    "synergy",
    "paradigm shift",
    "at the end of the day",
    "think outside the box",
    "low-hanging fruit",
    "move the needle",
    "boil the ocean",
]

# ============================================================================
# TEMPERATURE SETTINGS
# ============================================================================

# Temperature for creative post generation (0.0-1.0)
# Higher = more creative, lower = more deterministic
POST_GENERATION_TEMPERATURE = 0.7

# Temperature for structured data extraction (brief parsing)
# Lower temperature for more consistent JSON extraction
BRIEF_PARSING_TEMPERATURE = 0.3

# Temperature for voice analysis
VOICE_ANALYSIS_TEMPERATURE = 0.5

# ============================================================================
# FILE SIZE LIMITS
# ============================================================================

# Maximum brief file size in bytes (1MB)
MAX_BRIEF_FILE_SIZE = 1_048_576

# Maximum output file size in bytes (10MB)
MAX_OUTPUT_FILE_SIZE = 10_485_760

# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

# Enable performance metrics tracking
ENABLE_PERFORMANCE_METRICS = True

# Enable token usage tracking
ENABLE_TOKEN_TRACKING = True

# Log performance warnings for operations exceeding this threshold (seconds)
SLOW_OPERATION_THRESHOLD = 5.0

# ============================================================================
# QUALITY ASSURANCE
# ============================================================================

# Minimum quality score to pass QA (0.0-1.0)
MIN_QUALITY_SCORE = 0.75

# Maximum posts that can be flagged for review (warn if exceeded)
MAX_FLAGGED_POSTS_WARNING = 5

# ============================================================================
# POST REGENERATION THRESHOLDS
# ============================================================================

# Automatically regenerate posts that fall outside these quality parameters

# Readability constraints (Flesch Reading Ease 0-100)
MIN_READABILITY_SCORE = 50.0  # Minimum: Fairly difficult (high school)
MAX_READABILITY_SCORE = 65.0  # Maximum: Standard (8th-9th grade) - keeps professional tone

# Length constraints for regeneration (stricter than validation)
REGEN_MIN_WORDS = 150  # Regenerate if too short
REGEN_MAX_WORDS = 300  # Regenerate if too long

# Minimum headline engagement score (out of potential elements)
REGEN_MIN_ENGAGEMENT_SCORE = 2  # At least 2/3 engagement elements

# Require clear CTA in all posts
REGEN_REQUIRE_CTA = True

# Maximum regeneration attempts per post (prevent infinite loops)
MAX_REGENERATION_ATTEMPTS = 2

# Enable auto-regeneration by default (can be disabled via CLI)
ENABLE_AUTO_REGENERATION_DEFAULT = False

# ============================================================================
# PLATFORM-SPECIFIC DEFAULTS
# ============================================================================

# Default platform if not specified
DEFAULT_PLATFORM = "linkedin"

# Maximum blog posts for multi-platform generation
MAX_BLOG_POSTS = 10

# Social teasers per blog post
SOCIAL_TEASERS_PER_BLOG = 2
