"""Unit tests for client_brief module.

Tests cover:
- Platform enum case-insensitive lookup
- ClientBrief field validation
- get_missing_fields method
- to_context_dict method
"""

import pytest
from pydantic import ValidationError

from src.models.client_brief import (
    ClientBrief,
    Platform,
    TonePreference,
    DataUsagePreference,
)


class TestPlatformEnum:
    """Tests for Platform enum."""

    def test_platform_case_insensitive_lookup(self):
        """Test that Platform enum handles case-insensitive lookup."""
        # Lowercase
        assert Platform("linkedin") == Platform.LINKEDIN
        # Uppercase
        assert Platform("LINKEDIN") == Platform.LINKEDIN
        # Mixed case
        assert Platform("LinkedIn") == Platform.LINKEDIN
        assert Platform("Twitter") == Platform.TWITTER
        assert Platform("FaceBook") == Platform.FACEBOOK

    def test_platform_missing_value_returns_none(self):
        """Test that invalid platform returns None via _missing_."""
        # Invalid platform should trigger _missing_ and return None
        result = Platform._missing_("invalid_platform")
        assert result is None

    def test_platform_values(self):
        """Test platform values."""
        assert Platform.LINKEDIN.value == "linkedin"
        assert Platform.TWITTER.value == "twitter"
        assert Platform.FACEBOOK.value == "facebook"
        assert Platform.BLOG.value == "blog"
        assert Platform.EMAIL.value == "email"
        assert Platform.GENERIC.value == "generic"


class TestClientBriefValidation:
    """Tests for ClientBrief validation."""

    def test_customer_questions_limit_exceeded(self):
        """Test that customer_questions list with >10 items raises ValueError (line 113)."""
        with pytest.raises(ValidationError) as exc_info:
            ClientBrief(
                company_name="Test Co",
                business_description="Test business",
                ideal_customer="Test customer",
                main_problem_solved="Test problem",
                customer_questions=[f"Question {i}" for i in range(15)],  # 15 items > 10
            )

        assert "at most 10 items" in str(exc_info.value)

    def test_customer_questions_at_limit(self):
        """Test that exactly 10 customer_questions is valid."""
        brief = ClientBrief(
            company_name="Test Co",
            business_description="Test business",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
            customer_questions=[f"Question {i}" for i in range(10)],  # Exactly 10
        )
        assert len(brief.customer_questions) == 10

    def test_required_fields_only(self):
        """Test creating brief with only required fields."""
        brief = ClientBrief(
            company_name="Test Company",
            business_description="We do testing",
            ideal_customer="Testers",
            main_problem_solved="Testing issues",
        )
        assert brief.company_name == "Test Company"
        assert brief.founder_name is None
        assert brief.stories == []
        assert brief.data_usage == DataUsagePreference.MODERATE


class TestGetMissingFields:
    """Tests for get_missing_fields method (lines 116-127)."""

    def test_all_fields_missing(self):
        """Test get_missing_fields when all optional fields are missing."""
        brief = ClientBrief(
            company_name="Test Co",
            business_description="Test business",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
            # All optional fields that get_missing_fields checks are missing
        )

        missing = brief.get_missing_fields()

        assert "founder_name" in missing
        assert "stories (needed for personal story templates)" in missing
        assert "main_cta" in missing
        assert "measurable_results" in missing

    def test_no_fields_missing(self):
        """Test get_missing_fields when all optional fields are present."""
        brief = ClientBrief(
            company_name="Test Co",
            business_description="Test business",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
            founder_name="John Doe",
            stories=["Story 1", "Story 2"],
            main_cta="Learn more",
            measurable_results="50% improvement",
        )

        missing = brief.get_missing_fields()

        assert missing == []

    def test_some_fields_missing(self):
        """Test get_missing_fields with partial fields."""
        brief = ClientBrief(
            company_name="Test Co",
            business_description="Test business",
            ideal_customer="Test customer",
            main_problem_solved="Test problem",
            founder_name="Jane Doe",  # Present
            stories=["A story"],  # Present
            # main_cta is missing
            # measurable_results is missing
        )

        missing = brief.get_missing_fields()

        assert "founder_name" not in missing
        assert "stories (needed for personal story templates)" not in missing
        assert "main_cta" in missing
        assert "measurable_results" in missing


class TestToContextDict:
    """Tests for to_context_dict method."""

    def test_to_context_dict_basic(self):
        """Test to_context_dict with basic fields."""
        brief = ClientBrief(
            company_name="Test Company",
            business_description="We solve problems",
            ideal_customer="Small business owners",
            main_problem_solved="Workflow inefficiency",
        )

        context = brief.to_context_dict()

        assert context["company_name"] == "Test Company"
        assert context["ideal_customer"] == "Small business owners"
        assert context["problem_solved"] == "Workflow inefficiency"
        assert context["main_cta"] == "engage with us"  # Default when None
        assert context["data_preference"] == "moderate"
        assert context["brand_voice"] == ""  # Empty list
        assert context["pain_points"] == []
        assert context["key_phrases"] == []
        assert context["stories"] == []

    def test_to_context_dict_full(self):
        """Test to_context_dict with all fields populated."""
        brief = ClientBrief(
            company_name="Full Company",
            business_description="Complete solution",
            ideal_customer="Enterprise clients",
            main_problem_solved="Complex problems",
            brand_personality=[TonePreference.AUTHORITATIVE, TonePreference.DIRECT],
            customer_pain_points=["Pain 1", "Pain 2"],
            key_phrases=["phrase one", "phrase two"],
            stories=["Story A", "Story B"],
            main_cta="Schedule a demo",
            data_usage=DataUsagePreference.HEAVY,
            misconceptions=["Myth 1"],
            customer_questions=["Q1", "Q2"],
            measurable_results="2x ROI",
        )

        context = brief.to_context_dict()

        assert context["company_name"] == "Full Company"
        assert context["brand_voice"] == "authoritative, direct"
        assert context["pain_points"] == ["Pain 1", "Pain 2"]
        assert context["key_phrases"] == ["phrase one", "phrase two"]
        assert context["stories"] == ["Story A", "Story B"]
        assert context["main_cta"] == "Schedule a demo"
        assert context["data_preference"] == "heavy"
        assert context["misconceptions"] == ["Myth 1"]
        assert context["customer_questions"] == ["Q1", "Q2"]
        assert context["results"] == "2x ROI"


class TestTonePreferenceEnum:
    """Tests for TonePreference enum."""

    def test_tone_values(self):
        """Test all tone preference values."""
        assert TonePreference.APPROACHABLE.value == "approachable"
        assert TonePreference.DIRECT.value == "direct"
        assert TonePreference.AUTHORITATIVE.value == "authoritative"
        assert TonePreference.WITTY.value == "witty"
        assert TonePreference.VULNERABLE.value == "vulnerable"
        assert TonePreference.DATA_DRIVEN.value == "data_driven"
        assert TonePreference.CONVERSATIONAL.value == "conversational"


class TestDataUsagePreferenceEnum:
    """Tests for DataUsagePreference enum."""

    def test_data_usage_values(self):
        """Test all data usage preference values."""
        assert DataUsagePreference.HEAVY.value == "heavy"
        assert DataUsagePreference.MODERATE.value == "moderate"
        assert DataUsagePreference.MINIMAL.value == "minimal"


class TestPlatformEnumAdditionalValues:
    """Cover the remaining Platform enum members not exercised in TestPlatformEnum."""

    def test_platform_publishing_values(self):
        """Test all current platform enum values are present."""
        expected = {"linkedin", "twitter", "facebook", "blog", "email", "generic"}
        actual = {p.value for p in Platform}
        assert actual == expected

    def test_platform_case_insensitive_publishing(self):
        """Test case-insensitive lookup for platforms."""
        assert Platform("LinkedIn") == Platform.LINKEDIN
        assert Platform("TWITTER") == Platform.TWITTER
        assert Platform("Facebook") == Platform.FACEBOOK

    def test_platform_missing_returns_none_via_constructor(self):
        """Test that a completely unknown string returns None via _missing_."""
        result = Platform._missing_("does_not_exist")
        assert result is None

    def test_platform_missing_called_with_numeric(self):
        """Test that _missing_ handles non-string input gracefully."""
        result = Platform._missing_(999)
        assert result is None


class TestClientBriefOptionalFieldDefaults:
    """Cover branches for optional fields with None defaults."""

    def test_optional_list_fields_default_to_empty(self):
        """All List fields default to empty list, not None."""
        brief = ClientBrief(
            company_name="Test Co",
            business_description="We do something",
            ideal_customer="Everyone",
            main_problem_solved="Nothing",
        )
        assert brief.keywords == []
        assert brief.competitors == []
        assert brief.customer_pain_points == []
        assert brief.brand_personality == []
        assert brief.key_phrases == []
        assert brief.customer_questions == []
        assert brief.misconceptions == []
        assert brief.target_platforms == []
        assert brief.lead_magnets == []
        assert brief.stories == []
        assert brief.case_studies == []

    def test_optional_scalar_fields_default_to_none(self):
        """All Optional scalar fields default to None."""
        brief = ClientBrief(
            company_name="Test Co",
            business_description="We do something",
            ideal_customer="Everyone",
            main_problem_solved="Nothing",
        )
        assert brief.founder_name is None
        assert brief.website is None
        assert brief.industry is None
        assert brief.location is None
        assert brief.tone_preference is None
        assert brief.brand_voice is None
        assert brief.tone_to_avoid is None
        assert brief.role_model_communicator is None
        assert brief.measurable_results is None
        assert brief.posting_frequency is None
        assert brief.main_cta is None
        assert brief.delivery_date is None

    def test_customer_questions_at_zero(self):
        """Empty customer_questions list is valid."""
        brief = ClientBrief(
            company_name="Test Co",
            business_description="We do something",
            ideal_customer="Everyone",
            main_problem_solved="Nothing",
            customer_questions=[],
        )
        assert brief.customer_questions == []


class TestToContextDictBranchCoverage:
    """Cover the remaining branches in to_context_dict."""

    def test_to_context_dict_includes_industry_location_competitors(self):
        """to_context_dict returns industry, location, competitors (Bug #42 fix)."""
        brief = ClientBrief(
            company_name="Acme",
            business_description="We build widgets",
            ideal_customer="Builders",
            main_problem_solved="Slow construction",
            industry="Manufacturing",
            location="Chicago",
            competitors=["WidgetCo", "FastBuild"],
        )

        ctx = brief.to_context_dict()

        assert ctx["industry"] == "Manufacturing"
        assert ctx["location"] == "Chicago"
        assert ctx["competitors"] == ["WidgetCo", "FastBuild"]

    def test_to_context_dict_none_industry_location_competitors(self):
        """to_context_dict returns None for unset industry/location/competitors."""
        brief = ClientBrief(
            company_name="Acme",
            business_description="We build widgets",
            ideal_customer="Builders",
            main_problem_solved="Slow construction",
        )

        ctx = brief.to_context_dict()

        assert ctx["industry"] is None
        assert ctx["location"] is None
        assert ctx["competitors"] == []

    def test_to_context_dict_data_usage_minimal(self):
        """to_context_dict reflects minimal data usage preference."""
        brief = ClientBrief(
            company_name="Test Co",
            business_description="desc",
            ideal_customer="ic",
            main_problem_solved="mp",
            data_usage=DataUsagePreference.MINIMAL,
        )

        ctx = brief.to_context_dict()

        assert ctx["data_preference"] == "minimal"
