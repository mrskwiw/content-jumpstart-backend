"""Unit tests for brand_frameworks module.

Tests cover:
- BRAND_ARCHETYPES dictionary validation
- WRITING_PRINCIPLES dictionary validation
- CUSTOMER_CENTRIC_PRINCIPLES dictionary validation
- get_archetype_guidance() function
- get_writing_principles_guidance() function
- infer_archetype_from_voice_dimensions() function
- get_archetype_from_client_type() function
"""

from src.config.brand_frameworks import (
    BRAND_ARCHETYPES,
    WRITING_PRINCIPLES,
    CUSTOMER_CENTRIC_PRINCIPLES,
    get_archetype_guidance,
    get_writing_principles_guidance,
    infer_archetype_from_voice_dimensions,
    get_archetype_from_client_type,
)


class TestBrandArchetypes:
    """Tests for BRAND_ARCHETYPES dictionary."""

    def test_expected_archetypes_exist(self):
        """Test that all expected archetypes are defined."""
        expected = ["Expert", "Friend", "Innovator", "Guide", "Motivator"]
        for archetype in expected:
            assert archetype in BRAND_ARCHETYPES, f"Missing archetype: {archetype}"

    def test_archetype_count(self):
        """Test the number of archetypes."""
        assert len(BRAND_ARCHETYPES) == 5

    def test_expert_archetype(self):
        """Test Expert archetype fields."""
        expert = BRAND_ARCHETYPES["Expert"]
        assert "tone" in expert
        assert "content_style" in expert
        assert "example_phrase" in expert
        assert "when_to_use" in expert
        assert "formality" in expert
        assert "typical_perspective" in expert

        assert expert["formality"] == "professional"
        assert expert["typical_perspective"] == "authoritative"

    def test_friend_archetype(self):
        """Test Friend archetype fields."""
        friend = BRAND_ARCHETYPES["Friend"]
        assert "Warm" in friend["tone"]
        assert friend["formality"] == "conversational"
        assert friend["typical_perspective"] == "collaborative"

    def test_innovator_archetype(self):
        """Test Innovator archetype fields."""
        innovator = BRAND_ARCHETYPES["Innovator"]
        assert "Visionary" in innovator["tone"]
        assert "disruptive" in innovator["content_style"].lower()

    def test_guide_archetype(self):
        """Test Guide archetype fields."""
        guide = BRAND_ARCHETYPES["Guide"]
        assert "Wise" in guide["tone"]
        assert "Step-by-step" in guide["content_style"]
        assert guide["formality"] == "conversational"

    def test_motivator_archetype(self):
        """Test Motivator archetype fields."""
        motivator = BRAND_ARCHETYPES["Motivator"]
        assert "Energetic" in motivator["tone"]
        # Content style is "Empowering, action-oriented, transformative"
        assert "empowering" in motivator["content_style"].lower()

    def test_all_archetypes_have_required_fields(self):
        """Test that all archetypes have required fields."""
        required_fields = [
            "tone",
            "content_style",
            "example_phrase",
            "when_to_use",
            "formality",
            "typical_perspective",
        ]
        for name, archetype in BRAND_ARCHETYPES.items():
            for field in required_fields:
                assert field in archetype, f"Missing {field} in {name} archetype"

    def test_formality_values_are_valid(self):
        """Test that formality values are from expected set."""
        valid_formality = {"professional", "conversational", "casual", "formal"}
        for name, archetype in BRAND_ARCHETYPES.items():
            assert (
                archetype["formality"] in valid_formality
            ), f"Invalid formality '{archetype['formality']}' in {name}"


class TestWritingPrinciples:
    """Tests for WRITING_PRINCIPLES dictionary."""

    def test_expected_categories_exist(self):
        """Test that expected writing principle categories exist."""
        expected = ["action_verbs", "positive_descriptors", "outcome_focused", "avoid_words"]
        for category in expected:
            assert category in WRITING_PRINCIPLES, f"Missing category: {category}"

    def test_action_verbs(self):
        """Test action_verbs list."""
        verbs = WRITING_PRINCIPLES["action_verbs"]
        assert isinstance(verbs, list)
        assert len(verbs) >= 10
        assert "transform" in verbs
        assert "accelerate" in verbs
        assert "empower" in verbs

    def test_positive_descriptors(self):
        """Test positive_descriptors list."""
        descriptors = WRITING_PRINCIPLES["positive_descriptors"]
        assert isinstance(descriptors, list)
        assert len(descriptors) >= 10
        assert "seamless" in descriptors
        assert "powerful" in descriptors
        assert "innovative" in descriptors

    def test_outcome_focused(self):
        """Test outcome_focused list."""
        outcomes = WRITING_PRINCIPLES["outcome_focused"]
        assert isinstance(outcomes, list)
        assert len(outcomes) >= 10
        assert "results" in outcomes
        assert "growth" in outcomes
        assert "ROI" in outcomes

    def test_avoid_words(self):
        """Test avoid_words list."""
        avoid = WRITING_PRINCIPLES["avoid_words"]
        assert isinstance(avoid, list)
        assert len(avoid) >= 15
        # Jargon
        assert "synergy" in avoid
        assert "leverage" in avoid
        # Weak modifiers
        assert "very" in avoid
        assert "really" in avoid
        # Overused buzzwords
        assert "game-changer" in avoid

    def test_all_lists_non_empty(self):
        """Test that all word lists are non-empty."""
        for category, words in WRITING_PRINCIPLES.items():
            assert len(words) > 0, f"Empty list for {category}"


class TestCustomerCentricPrinciples:
    """Tests for CUSTOMER_CENTRIC_PRINCIPLES dictionary."""

    def test_expected_principles_exist(self):
        """Test that expected principles exist."""
        expected = [
            "focus_on_benefits",
            "use_you_over_we",
            "address_pain_points",
            "include_social_proof",
            "clear_next_steps",
        ]
        for principle in expected:
            assert principle in CUSTOMER_CENTRIC_PRINCIPLES, f"Missing principle: {principle}"

    def test_principles_are_strings(self):
        """Test that all principles are non-empty strings."""
        for key, value in CUSTOMER_CENTRIC_PRINCIPLES.items():
            assert isinstance(value, str), f"{key} is not a string"
            assert len(value) > 10, f"{key} is too short"

    def test_focus_on_benefits(self):
        """Test focus_on_benefits principle content."""
        assert "benefit" in CUSTOMER_CENTRIC_PRINCIPLES["focus_on_benefits"].lower()

    def test_use_you_over_we(self):
        """Test use_you_over_we principle content."""
        principle = CUSTOMER_CENTRIC_PRINCIPLES["use_you_over_we"]
        assert "you" in principle.lower()


class TestGetArchetypeGuidance:
    """Tests for get_archetype_guidance() function."""

    def test_expert_guidance(self):
        """Test getting Expert archetype guidance."""
        result = get_archetype_guidance("Expert")
        assert "BRAND ARCHETYPE: Expert" in result
        assert "Tone:" in result
        assert "Content Style:" in result
        assert "Example:" in result

    def test_friend_guidance(self):
        """Test getting Friend archetype guidance."""
        result = get_archetype_guidance("Friend")
        assert "BRAND ARCHETYPE: Friend" in result
        assert "Warm" in result

    def test_innovator_guidance(self):
        """Test getting Innovator archetype guidance."""
        result = get_archetype_guidance("Innovator")
        assert "BRAND ARCHETYPE: Innovator" in result
        assert "Visionary" in result

    def test_guide_guidance(self):
        """Test getting Guide archetype guidance."""
        result = get_archetype_guidance("Guide")
        assert "BRAND ARCHETYPE: Guide" in result
        assert "Wise" in result

    def test_motivator_guidance(self):
        """Test getting Motivator archetype guidance."""
        result = get_archetype_guidance("Motivator")
        assert "BRAND ARCHETYPE: Motivator" in result
        assert "Energetic" in result

    def test_invalid_archetype_returns_empty(self):
        """Test that invalid archetype returns empty string."""
        result = get_archetype_guidance("InvalidArchetype")
        assert result == ""

    def test_none_archetype_returns_empty(self):
        """Test that None archetype returns empty string."""
        result = get_archetype_guidance(None)
        assert result == ""

    def test_case_sensitive(self):
        """Test that archetype names are case sensitive."""
        result = get_archetype_guidance("expert")
        assert result == ""  # Should not match "Expert"


class TestGetWritingPrinciplesGuidance:
    """Tests for get_writing_principles_guidance() function."""

    def test_returns_formatted_string(self):
        """Test that function returns a formatted string."""
        result = get_writing_principles_guidance()
        assert isinstance(result, str)
        assert len(result) > 100

    def test_includes_action_verbs(self):
        """Test that result includes action verbs section."""
        result = get_writing_principles_guidance()
        assert "Action Verbs" in result

    def test_includes_positive_descriptors(self):
        """Test that result includes positive descriptors section."""
        result = get_writing_principles_guidance()
        assert "Positive Descriptors" in result

    def test_includes_outcome_focused(self):
        """Test that result includes outcome focused section."""
        result = get_writing_principles_guidance()
        assert "Outcomes" in result

    def test_includes_avoid_words(self):
        """Test that result includes avoid words section."""
        result = get_writing_principles_guidance()
        assert "AVOID" in result

    def test_includes_sample_words(self):
        """Test that result includes sample words from each category."""
        result = get_writing_principles_guidance()
        # Should include some words from each list
        assert "transform" in result
        assert "seamless" in result
        assert "results" in result


class TestInferArchetypeFromVoiceDimensions:
    """Tests for infer_archetype_from_voice_dimensions() function."""

    def test_formal_authoritative_returns_expert(self):
        """Test formal + authoritative returns Expert."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="formal", tone_dominant="authoritative", perspective_dominant="any"
        )
        assert result == "Expert"

    def test_professional_authoritative_returns_expert(self):
        """Test professional + authoritative returns Expert."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="professional",
            tone_dominant="authoritative",
            perspective_dominant="any",
        )
        assert result == "Expert"

    def test_formal_innovative_returns_innovator(self):
        """Test formal + innovative returns Innovator."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="formal", tone_dominant="innovative", perspective_dominant="any"
        )
        assert result == "Innovator"

    def test_professional_innovative_returns_innovator(self):
        """Test professional + innovative returns Innovator."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="professional",
            tone_dominant="innovative",
            perspective_dominant="any",
        )
        assert result == "Innovator"

    def test_formal_default_returns_expert(self):
        """Test formal with unknown tone defaults to Expert."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="formal", tone_dominant="unknown", perspective_dominant="any"
        )
        assert result == "Expert"

    def test_conversational_friendly_returns_friend(self):
        """Test conversational + friendly returns Friend."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="conversational",
            tone_dominant="friendly",
            perspective_dominant="any",
        )
        assert result == "Friend"

    def test_conversational_educational_returns_guide(self):
        """Test conversational + educational returns Guide."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="conversational",
            tone_dominant="educational",
            perspective_dominant="any",
        )
        assert result == "Guide"

    def test_conversational_with_conversational_perspective_returns_motivator(self):
        """Test conversational with conversational perspective returns Motivator."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="conversational",
            tone_dominant="other",
            perspective_dominant="conversational",
        )
        assert result == "Motivator"

    def test_conversational_default_returns_guide(self):
        """Test conversational with unknown values defaults to Guide."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="conversational",
            tone_dominant="unknown",
            perspective_dominant="unknown",
        )
        assert result == "Guide"

    def test_casual_friendly_returns_friend(self):
        """Test casual + friendly returns Friend."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="casual", tone_dominant="friendly", perspective_dominant="any"
        )
        assert result == "Friend"

    def test_casual_default_returns_motivator(self):
        """Test casual with unknown tone returns Motivator."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="casual", tone_dominant="other", perspective_dominant="any"
        )
        assert result == "Motivator"

    def test_unknown_formality_returns_guide(self):
        """Test unknown formality defaults to Guide."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="unknown", tone_dominant="any", perspective_dominant="any"
        )
        assert result == "Guide"


class TestGetArchetypeFromClientType:
    """Tests for get_archetype_from_client_type() function."""

    def test_b2b_saas_returns_expert(self):
        """Test B2B_SAAS client type returns Expert."""
        result = get_archetype_from_client_type("B2B_SAAS")
        assert result == "Expert"

    def test_agency_returns_expert(self):
        """Test AGENCY client type returns Expert."""
        result = get_archetype_from_client_type("AGENCY")
        assert result == "Expert"

    def test_coach_consultant_returns_guide(self):
        """Test COACH_CONSULTANT client type returns Guide."""
        result = get_archetype_from_client_type("COACH_CONSULTANT")
        assert result == "Guide"

    def test_creator_founder_returns_friend(self):
        """Test CREATOR_FOUNDER client type returns Friend."""
        result = get_archetype_from_client_type("CREATOR_FOUNDER")
        assert result == "Friend"

    def test_unknown_returns_guide(self):
        """Test UNKNOWN client type returns Guide."""
        result = get_archetype_from_client_type("UNKNOWN")
        assert result == "Guide"

    def test_invalid_client_type_returns_guide(self):
        """Test invalid client type returns Guide as default."""
        result = get_archetype_from_client_type("INVALID_TYPE")
        assert result == "Guide"

    def test_empty_string_returns_guide(self):
        """Test empty string returns Guide as default."""
        result = get_archetype_from_client_type("")
        assert result == "Guide"

    def test_case_sensitive(self):
        """Test that client type matching is case sensitive."""
        # Lowercase should not match (returns default)
        result = get_archetype_from_client_type("b2b_saas")
        assert result == "Guide"


# ---------------------------------------------------------------------------
# Additional tests for uncovered branches
# ---------------------------------------------------------------------------


class TestGetArchetypeGuidanceAdditional:
    """Additional tests for get_archetype_guidance() — uncovered branches."""

    def test_empty_string_returns_empty(self):
        """Test that empty string returns empty string."""
        result = get_archetype_guidance("")
        assert result == ""

    def test_unknown_returns_empty(self):
        """Test that 'Unknown' archetype name returns empty string."""
        result = get_archetype_guidance("Unknown")
        assert result == ""

    def test_whitespace_returns_empty(self):
        """Test that whitespace-only string returns empty string."""
        result = get_archetype_guidance("   ")
        assert result == ""

    def test_all_five_archetypes_return_nonempty(self):
        """Test that all 5 valid archetypes return non-empty strings."""
        archetypes = ["Expert", "Friend", "Innovator", "Guide", "Motivator"]
        for name in archetypes:
            result = get_archetype_guidance(name)
            assert len(result) > 0, f"Expected non-empty result for '{name}'"

    def test_output_contains_archetype_name(self):
        """Test that each archetype's output contains the archetype name."""
        archetypes = ["Expert", "Friend", "Innovator", "Guide", "Motivator"]
        for name in archetypes:
            result = get_archetype_guidance(name)
            assert name in result, f"Archetype name '{name}' not found in guidance output"

    def test_output_format_header(self):
        """Test that output contains BRAND ARCHETYPE: header."""
        for name in ["Expert", "Friend", "Innovator", "Guide", "Motivator"]:
            result = get_archetype_guidance(name)
            assert "BRAND ARCHETYPE:" in result

    def test_output_format_tone_label(self):
        """Test that output contains Tone: label."""
        for name in ["Expert", "Friend", "Innovator", "Guide", "Motivator"]:
            result = get_archetype_guidance(name)
            assert "Tone:" in result

    def test_output_format_content_style_label(self):
        """Test that output contains Content Style: label."""
        for name in ["Expert", "Friend", "Innovator", "Guide", "Motivator"]:
            result = get_archetype_guidance(name)
            assert "Content Style:" in result

    def test_output_format_example_label(self):
        """Test that output contains Example: label."""
        for name in ["Expert", "Friend", "Innovator", "Guide", "Motivator"]:
            result = get_archetype_guidance(name)
            assert "Example:" in result

    def test_expert_guidance_content(self):
        """Test Expert guidance contains expected tone text."""
        result = get_archetype_guidance("Expert")
        assert "Knowledgeable" in result

    def test_guide_guidance_content(self):
        """Test Guide guidance contains expected tone text."""
        result = get_archetype_guidance("Guide")
        assert "Wise" in result

    def test_motivator_guidance_content(self):
        """Test Motivator guidance contains expected tone text."""
        result = get_archetype_guidance("Motivator")
        assert "Energetic" in result


class TestGetWritingPrinciplesGuidanceAdditional:
    """Additional tests for get_writing_principles_guidance() — uncovered branches."""

    def test_returns_nonempty_string(self):
        """Test that function returns a non-empty string."""
        result = get_writing_principles_guidance()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_writing_principles_header(self):
        """Test that output contains WRITING PRINCIPLES: header."""
        result = get_writing_principles_guidance()
        assert "WRITING PRINCIPLES:" in result

    def test_contains_action_verb_transform(self):
        """Test that output contains 'transform' from action_verbs."""
        result = get_writing_principles_guidance()
        assert "transform" in result

    def test_contains_action_verb_accelerate(self):
        """Test that output contains 'accelerate' from action_verbs."""
        result = get_writing_principles_guidance()
        assert "accelerate" in result

    def test_contains_positive_descriptor_seamless(self):
        """Test that output contains 'seamless' from positive_descriptors."""
        result = get_writing_principles_guidance()
        assert "seamless" in result

    def test_contains_positive_descriptor_powerful(self):
        """Test that output contains 'powerful' from positive_descriptors."""
        result = get_writing_principles_guidance()
        assert "powerful" in result

    def test_contains_outcome_word_results(self):
        """Test that output contains 'results' from outcome_focused."""
        result = get_writing_principles_guidance()
        assert "results" in result

    def test_contains_outcome_word_growth(self):
        """Test that output contains 'growth' from outcome_focused."""
        result = get_writing_principles_guidance()
        assert "growth" in result

    def test_contains_avoid_words_section(self):
        """Test that output contains an avoid-words section."""
        result = get_writing_principles_guidance()
        assert "AVOID" in result

    def test_output_is_deterministic(self):
        """Test that repeated calls return identical output."""
        result1 = get_writing_principles_guidance()
        result2 = get_writing_principles_guidance()
        assert result1 == result2


class TestInferArchetypeFromVoiceDimensionsAdditional:
    """Additional tests for infer_archetype_from_voice_dimensions() — uncovered branches."""

    # --- formal branches not yet covered ---

    def test_formal_friendly_returns_expert(self):
        """Test formal + friendly falls through to Expert default."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="formal",
            tone_dominant="friendly",
            perspective_dominant="any",
        )
        assert result == "Expert"

    def test_formal_educational_returns_expert(self):
        """Test formal + educational falls through to Expert default."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="formal",
            tone_dominant="educational",
            perspective_dominant="any",
        )
        assert result == "Expert"

    def test_formal_empty_tone_returns_expert(self):
        """Test formal + empty tone falls through to Expert default."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="formal",
            tone_dominant="",
            perspective_dominant="any",
        )
        assert result == "Expert"

    # --- professional branches not yet covered ---

    def test_professional_other_tone_returns_expert(self):
        """Test professional with non-authoritative/non-innovative tone returns Expert."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="professional",
            tone_dominant="educational",
            perspective_dominant="any",
        )
        assert result == "Expert"

    def test_professional_friendly_returns_expert(self):
        """Test professional + friendly falls through to Expert default."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="professional",
            tone_dominant="friendly",
            perspective_dominant="collaborative",
        )
        assert result == "Expert"

    # --- conversational branches: authoritative splits on perspective ---

    def test_conversational_authoritative_conversational_perspective_returns_motivator(self):
        """Test conversational + authoritative + conversational perspective → Motivator."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="conversational",
            tone_dominant="authoritative",
            perspective_dominant="conversational",
        )
        assert result == "Motivator"

    def test_conversational_authoritative_non_conversational_perspective_returns_guide(self):
        """Test conversational + authoritative + non-conversational perspective → Guide."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="conversational",
            tone_dominant="authoritative",
            perspective_dominant="collaborative",
        )
        assert result == "Guide"

    def test_conversational_other_tone_collaborative_perspective_returns_guide(self):
        """Test conversational + other tone + collaborative perspective → Guide."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="conversational",
            tone_dominant="analytical",
            perspective_dominant="collaborative",
        )
        assert result == "Guide"

    def test_conversational_other_tone_conversational_perspective_returns_motivator(self):
        """Test conversational + other tone + conversational perspective → Motivator."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="conversational",
            tone_dominant="analytical",
            perspective_dominant="conversational",
        )
        assert result == "Motivator"

    # --- default fallback ---

    def test_neutral_formality_returns_guide(self):
        """Test unknown/neutral formality falls through to Guide default."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="neutral",
            tone_dominant="authoritative",
            perspective_dominant="collaborative",
        )
        assert result == "Guide"

    def test_empty_formality_returns_guide(self):
        """Test empty formality string falls through to Guide default."""
        result = infer_archetype_from_voice_dimensions(
            formality_dominant="",
            tone_dominant="friendly",
            perspective_dominant="conversational",
        )
        assert result == "Guide"


class TestGetArchetypeFromClientTypeAdditional:
    """Additional tests for get_archetype_from_client_type() — uncovered branches."""

    def test_startup_returns_guide(self):
        """Test unrecognised key 'STARTUP' returns Guide via dict.get default."""
        result = get_archetype_from_client_type("STARTUP")
        assert result == "Guide"

    def test_numeric_string_returns_guide(self):
        """Test numeric string key returns Guide via dict.get default."""
        result = get_archetype_from_client_type("123")
        assert result == "Guide"

    def test_all_known_client_types(self):
        """Parameterised check for all known client types and expected archetypes."""
        expected_mapping = {
            "B2B_SAAS": "Expert",
            "AGENCY": "Expert",
            "COACH_CONSULTANT": "Guide",
            "CREATOR_FOUNDER": "Friend",
            "UNKNOWN": "Guide",
        }
        for client_type, expected_archetype in expected_mapping.items():
            result = get_archetype_from_client_type(client_type)
            assert (
                result == expected_archetype
            ), f"Expected '{expected_archetype}' for '{client_type}', got '{result}'"
