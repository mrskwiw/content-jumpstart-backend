"""Integration tests for Bug #42 - Template Prerequisites and Unused Fields.

Tests verify that previously unused brief fields (tone_preference, data_preference,
industry, location, competitors) are now properly used in generation prompts.

NOTE: These tests verify field presence in context and prompts, not actual
AI generation quality (which would require expensive API calls).
"""

import pytest
from src.models.client_brief import (
    ClientBrief,
    DataUsagePreference,
    Platform,
    TonePreference,
)
from src.agents.content_generator import ContentGeneratorAgent
from src.utils.template_loader import TemplateLoader


class TestBug42UnusedFieldsInPrompts:
    """Test that unused fields are now properly integrated into prompts."""

    @pytest.fixture
    def generator(self):
        """Create content generator instance."""
        return ContentGeneratorAgent()

    @pytest.fixture
    def template_loader(self):
        """Create template loader instance."""
        return TemplateLoader()

    @pytest.fixture
    def sample_brief_with_all_fields(self):
        """Create a client brief with all previously unused fields populated."""
        return ClientBrief(
            company_name="Test Corp",
            business_description="We provide SaaS solutions",
            ideal_customer="B2B tech companies",
            main_problem_solved="Simplifying data analytics",
            customer_pain_points=["Complex tools", "No insights"],
            brand_personality=["direct", "approachable"],  # List of strings, not enum
            key_phrases=["Data made simple"],
            tone_preference=TonePreference.CONVERSATIONAL,  # Previously unused
            data_usage=DataUsagePreference.HEAVY,  # Previously unused
            industry="SaaS",  # Previously not in context
            location="San Francisco",  # Previously not in context
            competitors=[
                "Competitor A",
                "Competitor B",
                "Competitor C",
            ],  # Previously not in context
            measurable_results="50% faster analytics",  # Previously unused
            main_cta="Book a demo",
        )

    def test_tone_preference_in_system_prompt(self, generator, sample_brief_with_all_fields):
        """Verify tone_preference is included in system prompt (Bug #42 Fix #1)."""
        # Build system prompt
        system_prompt = generator._build_system_prompt(
            sample_brief_with_all_fields, platform=Platform.LINKEDIN
        )

        # Verify tone guidance is present
        assert "TONE:" in system_prompt or "tone" in system_prompt.lower()
        assert "conversational" in system_prompt.lower()

    def test_data_preference_in_system_prompt(self, generator, sample_brief_with_all_fields):
        """Verify data_preference is used in system prompt (Bug #42 Fix #2)."""
        # Build system prompt with heavy data preference
        system_prompt = generator._build_system_prompt(
            sample_brief_with_all_fields, platform=Platform.LINKEDIN
        )

        # Verify data usage guidance is present
        assert "DATA USAGE:" in system_prompt or "statistics" in system_prompt.lower()
        # Heavy preference should mention statistics/data
        assert "statistics" in system_prompt.lower() or "data points" in system_prompt.lower()

    def test_data_preference_minimal(self, generator):
        """Verify minimal data preference produces appropriate guidance."""
        brief = ClientBrief(
            company_name="Test Corp",
            business_description="Test business",
            ideal_customer="Test audience",
            main_problem_solved="Test problem",
            data_usage=DataUsagePreference.MINIMAL,
        )

        system_prompt = generator._build_system_prompt(brief, platform=Platform.LINKEDIN)

        # Minimal preference should mention minimizing data/statistics
        # or focusing on stories/narrative
        assert "minimal" in system_prompt.lower() or "stories" in system_prompt.lower()

    def test_industry_in_system_prompt(self, generator, sample_brief_with_all_fields):
        """Verify industry field is included in system prompt (Bug #42 Fix #4)."""
        system_prompt = generator._build_system_prompt(
            sample_brief_with_all_fields, platform=Platform.LINKEDIN
        )

        # Verify industry context is present
        assert "INDUSTRY" in system_prompt or "SaaS" in system_prompt

    def test_industry_location_competitors_in_context(
        self, generator, template_loader, sample_brief_with_all_fields
    ):
        """Verify industry, location, competitors are in context dict (Bug #42 Fix #4)."""
        # Load a template
        template = template_loader.get_template_by_id(1)

        # Build context
        base_context = sample_brief_with_all_fields.to_context_dict()
        context = generator._build_context(
            sample_brief_with_all_fields, template, variant=1, base_context=base_context
        )

        # Verify all previously missing fields are now present
        assert "industry" in context
        assert context["industry"] == "SaaS"

        assert "location" in context
        assert context["location"] == "San Francisco"

        assert "competitors" in context
        assert context["competitors"] == ["Competitor A", "Competitor B", "Competitor C"]

    def test_measurable_results_for_data_templates(
        self, generator, template_loader, sample_brief_with_all_fields
    ):
        """Verify measurable_results is used for data-driven templates (Bug #42 Fix #3)."""
        # Template 2 (Statistic) requires_data = True
        template_2 = template_loader.get_template_by_id(2)

        base_context = sample_brief_with_all_fields.to_context_dict()
        context = generator._build_context(
            sample_brief_with_all_fields, template_2, variant=1, base_context=base_context
        )

        # For data-driven templates, should have guidance to use results
        # The context dict should have "results" field from base_context
        assert "results" in context
        assert context["results"] == "50% faster analytics"

        # Should also have guidance field for data templates
        if template_2.requires_data:
            assert "use_measurable_results" in context

    def test_competitors_for_comparison_template(
        self, generator, template_loader, sample_brief_with_all_fields
    ):
        """Verify competitors are specially handled for Template 10 (Comparison)."""
        # Template 10 (Comparison)
        template_10 = template_loader.get_template_by_id(10)

        base_context = sample_brief_with_all_fields.to_context_dict()
        context = generator._build_context(
            sample_brief_with_all_fields, template_10, variant=1, base_context=base_context
        )

        # For comparison template, should have competitors guidance
        assert "competitors" in context
        assert "comparison_guidance" in context

    def test_all_collected_fields_available_in_workflow(
        self, generator, template_loader, sample_brief_with_all_fields
    ):
        """End-to-end test: all collected fields flow through to context."""
        template = template_loader.get_template_by_id(1)

        # Build system prompt
        system_prompt = generator._build_system_prompt(
            sample_brief_with_all_fields, platform=Platform.LINKEDIN
        )

        # Build context
        base_context = sample_brief_with_all_fields.to_context_dict()
        context = generator._build_context(
            sample_brief_with_all_fields, template, variant=1, base_context=base_context
        )

        # Verify no collected fields are lost
        # System prompt level (client-wide)
        assert "conversational" in system_prompt.lower()  # tone_preference
        assert (
            "statistics" in system_prompt.lower() or "data" in system_prompt.lower()
        )  # data_usage
        assert "SaaS" in system_prompt  # industry

        # Context level (template-specific)
        assert context["industry"] == "SaaS"
        assert context["location"] == "San Francisco"
        assert len(context["competitors"]) == 3
        assert context["results"] == "50% faster analytics"

    def test_fields_not_present_when_empty(self, generator):
        """Verify fields are not forced when not provided by user."""
        minimal_brief = ClientBrief(
            company_name="Minimal Corp",
            business_description="Minimal business",
            ideal_customer="Minimal audience",
            main_problem_solved="Minimal problem",
            # No tone_preference, industry, location, competitors, etc.
        )

        system_prompt = generator._build_system_prompt(minimal_brief, platform=Platform.LINKEDIN)

        context = minimal_brief.to_context_dict()

        # Fields should be present but None/empty
        assert "industry" in context
        assert context["industry"] is None

        assert "location" in context
        assert context["location"] is None

        # System prompt should not fail if fields are missing
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0


class TestBug42TemplatePrerequisites:
    """Test that template prerequisites are correctly assigned."""

    @pytest.fixture
    def template_loader(self):
        """Create template loader instance."""
        return TemplateLoader()

    def test_p0_templates_have_critical_research(self, template_loader):
        """Verify P0 templates identify their critical research needs."""
        from src.config.template_prerequisites import TEMPLATE_PREREQUISITES

        # Template 2 (Statistic) - requires market_trends
        template_2_prereqs = TEMPLATE_PREREQUISITES[2]
        assert "market_trends_research" in template_2_prereqs["required"]

        # Template 4 (Evolution) - requires story_mining
        template_4_prereqs = TEMPLATE_PREREQUISITES[4]
        assert "story_mining" in template_4_prereqs["required"]

        # Template 6 (Personal Story) - requires story_mining
        template_6_prereqs = TEMPLATE_PREREQUISITES[6]
        assert "story_mining" in template_6_prereqs["required"]

        # Template 10 (Comparison) - requires competitive_analysis
        template_10_prereqs = TEMPLATE_PREREQUISITES[10]
        assert "competitive_analysis" in template_10_prereqs["required"]

        # Template 13 (Future-Thinking) - requires market_trends
        template_13_prereqs = TEMPLATE_PREREQUISITES[13]
        assert "market_trends_research" in template_13_prereqs["required"]

    def test_templates_with_brief_fields_no_p0(self):
        """Templates that get data from brief should have NO P0 prerequisites."""
        from src.config.template_prerequisites import TEMPLATE_PREREQUISITES

        # Template 1: brief provides customer_pain_points
        assert len(TEMPLATE_PREREQUISITES[1]["required"]) == 0

        # Template 5: brief provides customer_questions
        assert len(TEMPLATE_PREREQUISITES[5]["required"]) == 0

        # Template 7: brief provides misconceptions
        assert len(TEMPLATE_PREREQUISITES[7]["required"]) == 0

        # Template 14: brief provides customer_questions
        assert len(TEMPLATE_PREREQUISITES[14]["required"]) == 0
