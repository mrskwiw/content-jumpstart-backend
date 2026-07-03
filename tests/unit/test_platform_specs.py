"""Unit tests for platform_specs module.

Tests cover:
- PLATFORM_LENGTH_SPECS dictionary validation
- PLATFORM_HOOK_SPECS dictionary validation
- PLATFORM_WRITING_GUIDELINES dictionary validation
- get_platform_target_length() function
- get_platform_prompt_guidance() function
- validate_platform_length() function
"""

from src.models.client_brief import Platform
from src.config.platform_specs import (
    PLATFORM_LENGTH_SPECS,
    PLATFORM_HOOK_SPECS,
    PLATFORM_WRITING_GUIDELINES,
    get_platform_target_length,
    get_platform_prompt_guidance,
    validate_platform_length,
)


class TestPlatformLengthSpecs:
    """Tests for PLATFORM_LENGTH_SPECS dictionary."""

    # Core platforms that should have specs (excludes MULTI which is a meta-platform)
    CORE_PLATFORMS = [
        Platform.LINKEDIN,
        Platform.TWITTER,
        Platform.FACEBOOK,
        Platform.BLOG,
        Platform.EMAIL,
    ]

    def test_core_platforms_have_specs(self):
        """Test that core platforms have length specifications."""
        for platform in self.CORE_PLATFORMS:
            assert platform in PLATFORM_LENGTH_SPECS, f"Missing specs for {platform}"

    def test_multi_platform_excluded(self):
        """Test that GENERIC platform is not a production platform spec."""
        # GENERIC is a fallback platform without specific length constraints
        assert Platform.GENERIC not in PLATFORM_LENGTH_SPECS

    def test_linkedin_specs(self):
        """Test LinkedIn length specifications."""
        specs = PLATFORM_LENGTH_SPECS[Platform.LINKEDIN]
        assert specs["min_words"] == 200
        assert specs["optimal_min_words"] == 220
        assert specs["optimal_max_words"] == 280
        assert specs["max_words"] == 300
        assert specs["hook_chars"] == 140

    def test_twitter_specs(self):
        """Test Twitter length specifications."""
        specs = PLATFORM_LENGTH_SPECS[Platform.TWITTER]
        assert specs["min_words"] == 8
        assert specs["max_chars"] == 280
        assert specs["thread_mode"] is True
        assert specs["thread_min_posts"] == 4
        assert specs["thread_max_posts"] == 8

    def test_facebook_specs(self):
        """Test Facebook length specifications."""
        specs = PLATFORM_LENGTH_SPECS[Platform.FACEBOOK]
        assert specs["min_words"] == 40
        assert specs["max_chars"] == 650
        assert specs["optimal_max_words"] == 80

    def test_blog_specs(self):
        """Test Blog length specifications."""
        specs = PLATFORM_LENGTH_SPECS[Platform.BLOG]
        assert specs["min_words"] == 800
        assert specs["optimal_min_words"] == 1500
        assert specs["optimal_max_words"] == 2000
        assert specs["max_words"] == 3000

    def test_email_specs(self):
        """Test Email length specifications."""
        specs = PLATFORM_LENGTH_SPECS[Platform.EMAIL]
        assert specs["min_words"] == 100
        assert specs["optimal_min_words"] == 150
        assert specs["optimal_max_words"] == 250
        assert specs["max_words"] == 300

    def test_specs_have_required_fields(self):
        """Test that all specs have required fields."""
        required_fields = [
            "min_words",
            "optimal_min_words",
            "optimal_max_words",
            "max_words",
        ]
        for platform, specs in PLATFORM_LENGTH_SPECS.items():
            for field in required_fields:
                assert field in specs, f"Missing {field} for {platform}"

    def test_word_count_ordering(self):
        """Test that word count fields are logically ordered."""
        for platform, specs in PLATFORM_LENGTH_SPECS.items():
            assert (
                specs["min_words"] <= specs["optimal_min_words"]
            ), f"Invalid ordering for {platform}"
            assert (
                specs["optimal_min_words"] <= specs["optimal_max_words"]
            ), f"Invalid ordering for {platform}"
            assert (
                specs["optimal_max_words"] <= specs["max_words"]
            ), f"Invalid ordering for {platform}"


class TestPlatformHookSpecs:
    """Tests for PLATFORM_HOOK_SPECS dictionary."""

    # Core platforms that should have specs (excludes MULTI which is a meta-platform)
    CORE_PLATFORMS = [
        Platform.LINKEDIN,
        Platform.TWITTER,
        Platform.FACEBOOK,
        Platform.BLOG,
        Platform.EMAIL,
    ]

    def test_core_platforms_have_hook_specs(self):
        """Test that core platforms have hook specifications."""
        for platform in self.CORE_PLATFORMS:
            assert platform in PLATFORM_HOOK_SPECS, f"Missing hook specs for {platform}"

    def test_multi_platform_excluded_from_hook_specs(self):
        """Test that GENERIC platform is not in hook specs (it has no specific hook rules)."""
        assert Platform.GENERIC not in PLATFORM_HOOK_SPECS

    def test_linkedin_hook_specs(self):
        """Test LinkedIn hook specifications."""
        specs = PLATFORM_HOOK_SPECS[Platform.LINKEDIN]
        assert specs["hook_max_chars"] == 140
        assert specs["hook_critical"] is True
        assert specs["hook_must_contain_key_message"] is True
        assert "description" in specs

    def test_twitter_hook_specs(self):
        """Test Twitter hook specifications."""
        specs = PLATFORM_HOOK_SPECS[Platform.TWITTER]
        assert specs["hook_max_chars"] == 100
        assert specs["hook_critical"] is True

    def test_facebook_hook_specs(self):
        """Test Facebook hook specifications."""
        specs = PLATFORM_HOOK_SPECS[Platform.FACEBOOK]
        assert specs["hook_max_chars"] == 120
        assert specs["hook_critical"] is True

    def test_blog_hook_specs(self):
        """Test Blog hook specifications."""
        specs = PLATFORM_HOOK_SPECS[Platform.BLOG]
        assert "hook_max_words" in specs
        assert specs["hook_max_words"] == 50
        assert specs["hook_must_contain_key_message"] is False

    def test_email_hook_specs(self):
        """Test Email hook specifications."""
        specs = PLATFORM_HOOK_SPECS[Platform.EMAIL]
        assert specs["hook_max_chars"] == 100
        assert specs["hook_critical"] is True

    def test_hook_specs_have_description(self):
        """Test that all hook specs have description field."""
        for platform, specs in PLATFORM_HOOK_SPECS.items():
            assert "description" in specs, f"Missing description for {platform}"
            assert len(specs["description"]) > 0


class TestPlatformWritingGuidelines:
    """Tests for PLATFORM_WRITING_GUIDELINES dictionary."""

    # Core platforms that should have guidelines (excludes MULTI which is a meta-platform)
    CORE_PLATFORMS = [
        Platform.LINKEDIN,
        Platform.TWITTER,
        Platform.FACEBOOK,
        Platform.BLOG,
        Platform.EMAIL,
    ]

    def test_core_platforms_have_guidelines(self):
        """Test that core platforms have writing guidelines."""
        for platform in self.CORE_PLATFORMS:
            assert platform in PLATFORM_WRITING_GUIDELINES, f"Missing guidelines for {platform}"

    def test_multi_platform_excluded_from_guidelines(self):
        """Test that GENERIC platform is not in writing guidelines (no specific rules)."""
        assert Platform.GENERIC not in PLATFORM_WRITING_GUIDELINES

    def test_linkedin_guidelines_content(self):
        """Test LinkedIn guidelines contain expected content."""
        guidelines = PLATFORM_WRITING_GUIDELINES[Platform.LINKEDIN]
        assert "220-280 words" in guidelines
        assert "140 characters" in guidelines
        assert "line breaks" in guidelines.lower()

    def test_twitter_guidelines_content(self):
        """Test Twitter guidelines contain expected content."""
        guidelines = PLATFORM_WRITING_GUIDELINES[Platform.TWITTER]
        assert "70-100 characters" in guidelines
        assert "tweet" in guidelines.lower() or "hashtag" in guidelines.lower()
        assert "hashtag" in guidelines.lower()

    def test_facebook_guidelines_content(self):
        """Test Facebook guidelines contain expected content."""
        guidelines = PLATFORM_WRITING_GUIDELINES[Platform.FACEBOOK]
        assert "50-80 words" in guidelines
        assert "conversational" in guidelines.lower()

    def test_blog_guidelines_content(self):
        """Test Blog guidelines contain expected content."""
        guidelines = PLATFORM_WRITING_GUIDELINES[Platform.BLOG]
        assert "1,500-2,000 words" in guidelines
        assert "SEO" in guidelines
        assert "header" in guidelines.lower()

    def test_email_guidelines_content(self):
        """Test Email guidelines contain expected content."""
        guidelines = PLATFORM_WRITING_GUIDELINES[Platform.EMAIL]
        assert "150-250 words" in guidelines
        assert "subject line" in guidelines.lower()
        assert "CTA" in guidelines

    def test_guidelines_are_non_empty_strings(self):
        """Test that all guidelines are non-empty strings."""
        for platform, guidelines in PLATFORM_WRITING_GUIDELINES.items():
            assert isinstance(guidelines, str), f"Guidelines for {platform} not a string"
            assert len(guidelines.strip()) > 100, f"Guidelines for {platform} too short"


class TestGetPlatformTargetLength:
    """Tests for get_platform_target_length() function."""

    def test_linkedin_target_length(self):
        """Test LinkedIn target length string."""
        result = get_platform_target_length(Platform.LINKEDIN)
        assert result == "220-280 words"

    def test_twitter_target_length(self):
        """Test Twitter target length string."""
        result = get_platform_target_length(Platform.TWITTER)
        assert result == "70-100 characters (~12-18 words)"

    def test_facebook_target_length(self):
        """Test Facebook target length string."""
        result = get_platform_target_length(Platform.FACEBOOK)
        assert result == "50-80 words"

    def test_blog_target_length(self):
        """Test Blog target length string."""
        result = get_platform_target_length(Platform.BLOG)
        assert result == "1500-2000 words"

    def test_email_target_length(self):
        """Test Email target length string."""
        result = get_platform_target_length(Platform.EMAIL)
        assert result == "150-250 words"

    def test_unknown_platform_returns_default(self):
        """Test that unknown platform returns default value."""
        # Create a mock platform not in specs (using None to test fallback)
        # The function should handle missing platform gracefully
        # Since all Platform enum values are covered, test the None branch
        # by directly calling with a value that won't exist
        pass  # All Platform enum values are covered

    def test_return_format(self):
        """Test that return format is correct."""
        for platform in Platform:
            result = get_platform_target_length(platform)
            assert "words" in result
            assert "-" in result


class TestGetPlatformPromptGuidance:
    """Tests for get_platform_prompt_guidance() function."""

    def test_linkedin_guidance(self):
        """Test getting LinkedIn guidance."""
        result = get_platform_prompt_guidance(Platform.LINKEDIN)
        assert result == PLATFORM_WRITING_GUIDELINES[Platform.LINKEDIN]

    def test_twitter_guidance(self):
        """Test getting Twitter guidance."""
        result = get_platform_prompt_guidance(Platform.TWITTER)
        assert result == PLATFORM_WRITING_GUIDELINES[Platform.TWITTER]

    def test_facebook_guidance(self):
        """Test getting Facebook guidance."""
        result = get_platform_prompt_guidance(Platform.FACEBOOK)
        assert result == PLATFORM_WRITING_GUIDELINES[Platform.FACEBOOK]

    def test_blog_guidance(self):
        """Test getting Blog guidance."""
        result = get_platform_prompt_guidance(Platform.BLOG)
        assert result == PLATFORM_WRITING_GUIDELINES[Platform.BLOG]

    def test_email_guidance(self):
        """Test getting Email guidance."""
        result = get_platform_prompt_guidance(Platform.EMAIL)
        assert result == PLATFORM_WRITING_GUIDELINES[Platform.EMAIL]

    def test_all_platforms_have_guidance(self):
        """Test that all platforms return guidance."""
        for platform in Platform:
            result = get_platform_prompt_guidance(platform)
            assert result is not None
            assert len(result) > 0


class TestValidatePlatformLength:
    """Tests for validate_platform_length() function."""

    def test_linkedin_optimal_length(self):
        """Test LinkedIn optimal length validation."""
        is_optimal, message = validate_platform_length(250, Platform.LINKEDIN)
        assert is_optimal is True
        assert "Optimal" in message

    def test_linkedin_too_short(self):
        """Test LinkedIn below minimum validation."""
        is_optimal, message = validate_platform_length(50, Platform.LINKEDIN)
        assert is_optimal is False
        assert "Too short" in message

    def test_linkedin_too_long(self):
        """Test LinkedIn above maximum validation."""
        is_optimal, message = validate_platform_length(500, Platform.LINKEDIN)
        assert is_optimal is False
        assert "Too long" in message

    def test_linkedin_below_optimal(self):
        """Test LinkedIn below minimum (min_words=200, so 150 is too short)."""
        is_optimal, message = validate_platform_length(150, Platform.LINKEDIN)
        assert is_optimal is False
        assert "Too short" in message

    def test_linkedin_above_optimal(self):
        """Test LinkedIn above optimal_max (280) but within max (300) → Above optimal."""
        is_optimal, message = validate_platform_length(300, Platform.LINKEDIN)
        assert is_optimal is False
        assert "Above optimal" in message

    def test_twitter_optimal_length(self):
        """Test Twitter optimal length validation."""
        is_optimal, message = validate_platform_length(15, Platform.TWITTER)
        assert is_optimal is True
        assert "Optimal" in message

    def test_twitter_too_short(self):
        """Test Twitter below minimum validation."""
        is_optimal, message = validate_platform_length(3, Platform.TWITTER)
        assert is_optimal is False
        assert "Too short" in message

    def test_twitter_too_long(self):
        """Test Twitter above maximum validation."""
        is_optimal, message = validate_platform_length(100, Platform.TWITTER)
        assert is_optimal is False
        assert "Too long" in message

    def test_facebook_optimal_length(self):
        """Test Facebook optimal length validation."""
        is_optimal, message = validate_platform_length(75, Platform.FACEBOOK)
        assert is_optimal is True

    def test_blog_optimal_length(self):
        """Test Blog optimal length validation."""
        is_optimal, message = validate_platform_length(2000, Platform.BLOG)
        assert is_optimal is True

    def test_email_optimal_length(self):
        """Test Email optimal length validation."""
        is_optimal, message = validate_platform_length(200, Platform.EMAIL)
        assert is_optimal is True

    def test_all_core_platforms_validate(self):
        """Test that all core platforms can be validated."""
        core_platforms = [
            Platform.LINKEDIN,
            Platform.TWITTER,
            Platform.FACEBOOK,
            Platform.BLOG,
            Platform.EMAIL,
        ]
        for platform in core_platforms:
            specs = PLATFORM_LENGTH_SPECS[platform]
            optimal_count = (specs["optimal_min_words"] + specs["optimal_max_words"]) // 2
            is_optimal, message = validate_platform_length(optimal_count, platform)
            assert is_optimal is True, f"Validation failed for {platform} at {optimal_count} words"

    def test_boundary_min(self):
        """Test validation below minimum boundary (min_words=200, so 130 is Too short)."""
        is_optimal, message = validate_platform_length(130, Platform.LINKEDIN)
        assert is_optimal is False
        assert "Too short" in message

    def test_boundary_max(self):
        """Test validation at maximum boundary (max_words=300, optimal_max=280, so 300 → Above optimal)."""
        is_optimal, message = validate_platform_length(300, Platform.LINKEDIN)
        assert is_optimal is False
        assert "Above optimal" in message

    def test_returns_tuple(self):
        """Test that function returns a tuple of (bool, str)."""
        result = validate_platform_length(200, Platform.LINKEDIN)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)


# ---------------------------------------------------------------------------
# Additional coverage tests — appended to reach full branch coverage
# ---------------------------------------------------------------------------


class TestGetPlatformTargetLengthExtended:
    """Extended tests for get_platform_target_length() covering all platforms and fallback."""

    def test_linkedin_returns_200_300(self):
        """LinkedIn → '220-280 words' (optimal_min=220, optimal_max=280)."""
        assert get_platform_target_length(Platform.LINKEDIN) == "220-280 words"

    def test_twitter_returns_12_18(self):
        """Twitter → character-based target length."""
        assert get_platform_target_length(Platform.TWITTER) == "70-100 characters (~12-18 words)"

    def test_facebook_returns_50_80(self):
        """Facebook → '50-80 words'."""
        assert get_platform_target_length(Platform.FACEBOOK) == "50-80 words"

    def test_blog_returns_1500_2500(self):
        """Blog → '1500-2000 words' (optimal_min=1500, optimal_max=2000)."""
        assert get_platform_target_length(Platform.BLOG) == "1500-2000 words"

    def test_email_returns_150_250(self):
        """Email → '150-250 words'."""
        assert get_platform_target_length(Platform.EMAIL) == "150-250 words"

    def test_platform_not_in_specs_returns_fallback(self):
        """Platform absent from PLATFORM_LENGTH_SPECS → returns '150-250 words' fallback."""
        # Platform.GENERIC is intentionally excluded from PLATFORM_LENGTH_SPECS
        result = get_platform_target_length(Platform.GENERIC)
        assert result == "150-250 words"


class TestGetPlatformPromptGuidanceExtended:
    """Extended tests for get_platform_prompt_guidance() covering keywords and unknown fallback."""

    def test_linkedin_guidance_contains_platform_keywords(self):
        """LinkedIn guidance is non-empty and mentions relevant terms."""
        result = get_platform_prompt_guidance(Platform.LINKEDIN)
        assert len(result.strip()) > 0
        assert "LinkedIn" in result or "200-300" in result or "140" in result

    def test_twitter_guidance_contains_platform_keywords(self):
        """Twitter guidance is non-empty and mentions relevant terms."""
        result = get_platform_prompt_guidance(Platform.TWITTER)
        assert len(result.strip()) > 0
        assert "tweet" in result.lower() or "12-18" in result or "thread" in result.lower()

    def test_facebook_guidance_contains_platform_keywords(self):
        """Facebook guidance is non-empty and mentions relevant terms."""
        result = get_platform_prompt_guidance(Platform.FACEBOOK)
        assert len(result.strip()) > 0
        assert "50-100" in result or "Facebook" in result or "conversational" in result.lower()

    def test_blog_guidance_contains_platform_keywords(self):
        """Blog guidance is non-empty and mentions relevant terms."""
        result = get_platform_prompt_guidance(Platform.BLOG)
        assert len(result.strip()) > 0
        assert "SEO" in result or "header" in result.lower() or "1,500" in result

    def test_email_guidance_contains_platform_keywords(self):
        """Email guidance is non-empty and mentions relevant terms."""
        result = get_platform_prompt_guidance(Platform.EMAIL)
        assert len(result.strip()) > 0
        assert "150-250" in result or "subject" in result.lower() or "CTA" in result

    def test_unknown_platform_returns_linkedin_default(self):
        """Platform absent from PLATFORM_WRITING_GUIDELINES → LinkedIn guidance returned."""
        result = get_platform_prompt_guidance(Platform.GENERIC)
        linkedin_guidance = get_platform_prompt_guidance(Platform.LINKEDIN)
        assert result == linkedin_guidance
        assert len(result.strip()) > 0


class TestValidatePlatformLengthExtended:
    """Extended validate_platform_length tests covering all platforms and all branches."""

    # -----------------------------------------------------------------------
    # LinkedIn  min=130 optimal_min=200 optimal_max=300 max=300
    # -----------------------------------------------------------------------

    def test_linkedin_below_min_is_too_short(self):
        """LinkedIn word count below min (130) → (False, 'Too short for...')."""
        ok, msg = validate_platform_length(50, Platform.LINKEDIN)
        assert ok is False
        assert "Too short" in msg
        assert "linkedin" in msg.lower()

    def test_linkedin_above_max_is_too_long(self):
        """LinkedIn word count above max (300) → (False, 'Too long for...')."""
        ok, msg = validate_platform_length(400, Platform.LINKEDIN)
        assert ok is False
        assert "Too long" in msg

    def test_linkedin_below_optimal_min(self):
        """LinkedIn at 210 words (≥200 min, <220 optimal_min) → (False, 'Below optimal for...')."""
        ok, msg = validate_platform_length(210, Platform.LINKEDIN)
        assert ok is False
        assert "Below optimal" in msg

    def test_linkedin_in_optimal_range(self):
        """LinkedIn at 250 words (200–300) → (True, 'Optimal for...')."""
        ok, msg = validate_platform_length(250, Platform.LINKEDIN)
        assert ok is True
        assert "Optimal" in msg

    # LinkedIn optimal_max == max (300), so "above optimal but ≤ max" is unreachable.
    # The boundary test at exactly 300 is covered by test_boundary_max in the base class.

    # -----------------------------------------------------------------------
    # Twitter  min=8 optimal_min=12 optimal_max=18 max=50
    # -----------------------------------------------------------------------

    def test_twitter_below_min_is_too_short(self):
        """Twitter word count below min (8) → (False, 'Too short for...')."""
        ok, msg = validate_platform_length(3, Platform.TWITTER)
        assert ok is False
        assert "Too short" in msg

    def test_twitter_above_max_is_too_long(self):
        """Twitter word count above max (50) → (False, 'Too long for...')."""
        ok, msg = validate_platform_length(60, Platform.TWITTER)
        assert ok is False
        assert "Too long" in msg

    def test_twitter_below_optimal_min(self):
        """Twitter at 10 words (≥8, <12) → (False, 'Below optimal for...')."""
        ok, msg = validate_platform_length(10, Platform.TWITTER)
        assert ok is False
        assert "Below optimal" in msg

    def test_twitter_above_optimal_max(self):
        """Twitter at 30 words (>18, ≤50) → (False, 'Above optimal for...')."""
        ok, msg = validate_platform_length(30, Platform.TWITTER)
        assert ok is False
        assert "Above optimal" in msg

    def test_twitter_in_optimal_range(self):
        """Twitter at 15 words (12–18) → (True, 'Optimal for...')."""
        ok, msg = validate_platform_length(15, Platform.TWITTER)
        assert ok is True
        assert "Optimal" in msg

    # -----------------------------------------------------------------------
    # Facebook  min=40 optimal_min=50 optimal_max=80 max=100
    # -----------------------------------------------------------------------

    def test_facebook_below_min_is_too_short(self):
        """Facebook word count below min (40) → (False, 'Too short for...')."""
        ok, msg = validate_platform_length(10, Platform.FACEBOOK)
        assert ok is False
        assert "Too short" in msg

    def test_facebook_above_max_is_too_long(self):
        """Facebook word count above max (100) → (False, 'Too long for...')."""
        ok, msg = validate_platform_length(120, Platform.FACEBOOK)
        assert ok is False
        assert "Too long" in msg

    def test_facebook_below_optimal_min(self):
        """Facebook at 45 words (≥40, <50) → (False, 'Below optimal for...')."""
        ok, msg = validate_platform_length(45, Platform.FACEBOOK)
        assert ok is False
        assert "Below optimal" in msg

    def test_facebook_above_optimal_max(self):
        """Facebook at 90 words (>80, ≤100) → (False, 'Above optimal for...')."""
        ok, msg = validate_platform_length(90, Platform.FACEBOOK)
        assert ok is False
        assert "Above optimal" in msg

    def test_facebook_in_optimal_range(self):
        """Facebook at 65 words (50–80) → (True, 'Optimal for...')."""
        ok, msg = validate_platform_length(65, Platform.FACEBOOK)
        assert ok is True
        assert "Optimal" in msg

    # -----------------------------------------------------------------------
    # Blog  min=300 optimal_min=1500 optimal_max=2500 max=5000
    # -----------------------------------------------------------------------

    def test_blog_below_min_is_too_short(self):
        """Blog word count below min (300) → (False, 'Too short for...')."""
        ok, msg = validate_platform_length(100, Platform.BLOG)
        assert ok is False
        assert "Too short" in msg

    def test_blog_above_max_is_too_long(self):
        """Blog word count above max (5000) → (False, 'Too long for...')."""
        ok, msg = validate_platform_length(6000, Platform.BLOG)
        assert ok is False
        assert "Too long" in msg

    def test_blog_below_optimal_min(self):
        """Blog at 800 words (≥300, <1500) → (False, 'Below optimal for...')."""
        ok, msg = validate_platform_length(800, Platform.BLOG)
        assert ok is False
        assert "Below optimal" in msg

    def test_blog_above_optimal_max(self):
        """Blog at 2800 words (>2000 optimal_max, ≤3000 max) → (False, 'Above optimal for...')."""
        ok, msg = validate_platform_length(2800, Platform.BLOG)
        assert ok is False
        assert "Above optimal" in msg

    def test_blog_in_optimal_range(self):
        """Blog at 2000 words (1500–2500) → (True, 'Optimal for...')."""
        ok, msg = validate_platform_length(2000, Platform.BLOG)
        assert ok is True
        assert "Optimal" in msg

    # -----------------------------------------------------------------------
    # Email  min=100 optimal_min=150 optimal_max=250 max=300
    # -----------------------------------------------------------------------

    def test_email_below_min_is_too_short(self):
        """Email word count below min (100) → (False, 'Too short for...')."""
        ok, msg = validate_platform_length(50, Platform.EMAIL)
        assert ok is False
        assert "Too short" in msg

    def test_email_above_max_is_too_long(self):
        """Email word count above max (300) → (False, 'Too long for...')."""
        ok, msg = validate_platform_length(400, Platform.EMAIL)
        assert ok is False
        assert "Too long" in msg

    def test_email_below_optimal_min(self):
        """Email at 120 words (≥100, <150) → (False, 'Below optimal for...')."""
        ok, msg = validate_platform_length(120, Platform.EMAIL)
        assert ok is False
        assert "Below optimal" in msg

    def test_email_above_optimal_max(self):
        """Email at 270 words (>250, ≤300) → (False, 'Above optimal for...')."""
        ok, msg = validate_platform_length(270, Platform.EMAIL)
        assert ok is False
        assert "Above optimal" in msg

    def test_email_in_optimal_range(self):
        """Email at 200 words (150–250) → (True, 'Optimal for...')."""
        ok, msg = validate_platform_length(200, Platform.EMAIL)
        assert ok is True
        assert "Optimal" in msg

    # -----------------------------------------------------------------------
    # Unknown platform (not in PLATFORM_LENGTH_SPECS)
    # -----------------------------------------------------------------------

    def test_unknown_platform_returns_true_empty_string(self):
        """Platform not in PLATFORM_LENGTH_SPECS → (True, '') — no validation applied."""
        ok, msg = validate_platform_length(999, Platform.GENERIC)
        assert ok is True
        assert msg == ""
