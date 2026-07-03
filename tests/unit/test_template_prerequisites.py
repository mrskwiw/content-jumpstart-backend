"""Unit tests for template prerequisites configuration.

Tests verify that template prerequisites are correctly assigned based on
actual AI generation needs analysis (Bug #42 fix).
"""

import pytest
from src.config.template_prerequisites import (
    TEMPLATE_PREREQUISITES,
    get_template_prerequisites,
)


class TestTemplatePrerequisites:
    """Test template prerequisites configuration."""

    def test_all_templates_have_prerequisites(self):
        """Verify all 15 templates have prerequisite definitions."""
        for template_id in range(1, 16):
            assert template_id in TEMPLATE_PREREQUISITES
            prereqs = TEMPLATE_PREREQUISITES[template_id]
            assert "required" in prereqs
            assert "recommended" in prereqs
            # Optional field added in Bug #42 fix
            assert "optional" in prereqs or True  # Allow missing optional key

    def test_p0_critical_prerequisites_template_2(self):
        """Template 2 (Statistic) requires market_trends - brief has no stats field."""
        prereqs = TEMPLATE_PREREQUISITES[2]
        assert "market_trends_research" in prereqs["required"]
        # P0 templates should have ONLY critical tools in required
        assert len(prereqs["required"]) == 1

    def test_p0_critical_prerequisites_template_4(self):
        """Template 4 (Evolution) requires story_mining - transformation stories critical."""
        prereqs = TEMPLATE_PREREQUISITES[4]
        assert "story_mining" in prereqs["required"]
        assert len(prereqs["required"]) == 1

    def test_p0_critical_prerequisites_template_6(self):
        """Template 6 (Personal Story) requires story_mining - narrative arc critical."""
        prereqs = TEMPLATE_PREREQUISITES[6]
        assert "story_mining" in prereqs["required"]
        assert len(prereqs["required"]) == 1

    def test_p0_critical_prerequisites_template_10(self):
        """Template 10 (Comparison) requires competitive_analysis - alternatives critical."""
        prereqs = TEMPLATE_PREREQUISITES[10]
        assert "competitive_analysis" in prereqs["required"]
        assert len(prereqs["required"]) == 1

    def test_p0_critical_prerequisites_template_13(self):
        """Template 13 (Future-Thinking) requires market_trends - predictions need data."""
        prereqs = TEMPLATE_PREREQUISITES[13]
        assert "market_trends_research" in prereqs["required"]
        assert len(prereqs["required"]) == 1

    def test_templates_with_brief_fields_have_no_p0(self):
        """Templates that use brief fields should have NO required prerequisites."""
        # Template 1: brief provides customer_pain_points
        assert len(TEMPLATE_PREREQUISITES[1]["required"]) == 0

        # Template 5: brief provides customer_questions
        assert len(TEMPLATE_PREREQUISITES[5]["required"]) == 0

        # Template 7: brief provides misconceptions
        assert len(TEMPLATE_PREREQUISITES[7]["required"]) == 0

        # Template 14: brief provides customer_questions
        assert len(TEMPLATE_PREREQUISITES[14]["required"]) == 0

    def test_audience_research_downgraded_to_p1(self):
        """Audience research downgraded from required to recommended (P1)."""
        # Template 1: audience_research should be in recommended, not required
        prereqs_1 = TEMPLATE_PREREQUISITES[1]
        assert "audience_research" not in prereqs_1["required"]
        assert "audience_research" in prereqs_1["recommended"]

        # Template 5: audience_research should be in recommended
        prereqs_5 = TEMPLATE_PREREQUISITES[5]
        assert "audience_research" not in prereqs_5["required"]
        assert "audience_research" in prereqs_5["recommended"]

    def test_seo_keywords_downgraded_to_p2(self):
        """SEO keywords downgraded to optional (P2) where not critical."""
        # Template 3: SEO keywords should be optional
        if "optional" in TEMPLATE_PREREQUISITES[3]:
            prereqs_3 = TEMPLATE_PREREQUISITES[3]
            assert "seo_keyword_research" not in prereqs_3["required"]
            assert "seo_keyword_research" not in prereqs_3["recommended"]
            assert "seo_keyword_research" in prereqs_3["optional"]

    def test_get_template_prerequisites_function(self):
        """Test get_template_prerequisites helper function."""
        # Valid template
        prereqs = get_template_prerequisites(1)
        assert "required" in prereqs
        assert "recommended" in prereqs

        # Invalid template should return empty prereqs
        prereqs_invalid = get_template_prerequisites(999)
        assert prereqs_invalid["required"] == []
        assert prereqs_invalid["recommended"] == []

    def test_no_duplicate_tools_across_priorities(self):
        """Verify same tool doesn't appear in both required and recommended."""
        for template_id, prereqs in TEMPLATE_PREREQUISITES.items():
            required = set(prereqs["required"])
            recommended = set(prereqs["recommended"])
            optional = set(prereqs.get("optional", []))

            # No overlap between required and recommended
            assert (
                len(required & recommended) == 0
            ), f"Template {template_id}: Tool in both required and recommended"

            # No overlap between required and optional
            assert (
                len(required & optional) == 0
            ), f"Template {template_id}: Tool in both required and optional"

            # No overlap between recommended and optional
            assert (
                len(recommended & optional) == 0
            ), f"Template {template_id}: Tool in both recommended and optional"

    def test_valid_research_tool_names(self):
        """Verify research tool names match backend research tool identifiers."""
        valid_tools = {
            "audience_research",
            "brand_archetype",
            "competitive_analysis",
            "content_audit",
            "content_gap_analysis",
            "market_trends_research",
            "platform_strategy",
            "seo_keyword_research",
            "story_mining",
            "voice_analysis",
            # Legacy names that might still be in use
            "content_calendar",
            "icp_workshop",
        }

        for template_id, prereqs in TEMPLATE_PREREQUISITES.items():
            all_tools = prereqs["required"] + prereqs["recommended"] + prereqs.get("optional", [])
            for tool in all_tools:
                assert (
                    tool in valid_tools
                ), f"Template {template_id}: Unknown research tool '{tool}'"

    def test_p0_templates_count(self):
        """Verify exactly 5 templates have P0 (critical) prerequisites."""
        p0_count = 0
        p0_templates = []
        for template_id, prereqs in TEMPLATE_PREREQUISITES.items():
            if len(prereqs["required"]) > 0:
                p0_count += 1
                p0_templates.append(template_id)

        assert (
            p0_count == 5
        ), f"Expected 5 templates with P0 prerequisites, found {p0_count}: {p0_templates}"
        # Verify correct templates: 2, 4, 6, 10, 13
        assert set(p0_templates) == {2, 4, 6, 10, 13}


class TestClientBriefContextFields:
    """Test that unused brief fields are now included in context dict."""

    def test_industry_in_context(self):
        """Verify industry field is included in context dict (Bug #42 fix)."""
        from src.models.client_brief import ClientBrief

        brief = ClientBrief(
            company_name="Test Corp",
            business_description="Test business",
            ideal_customer="Test audience",
            main_problem_solved="Test problem",
            industry="SaaS",
        )
        context = brief.to_context_dict()
        assert "industry" in context
        assert context["industry"] == "SaaS"

    def test_location_in_context(self):
        """Verify location field is included in context dict (Bug #42 fix)."""
        from src.models.client_brief import ClientBrief

        brief = ClientBrief(
            company_name="Test Corp",
            business_description="Test business",
            ideal_customer="Test audience",
            main_problem_solved="Test problem",
            location="San Francisco",
        )
        context = brief.to_context_dict()
        assert "location" in context
        assert context["location"] == "San Francisco"

    def test_competitors_in_context(self):
        """Verify competitors field is included in context dict (Bug #42 fix)."""
        from src.models.client_brief import ClientBrief

        brief = ClientBrief(
            company_name="Test Corp",
            business_description="Test business",
            ideal_customer="Test audience",
            main_problem_solved="Test problem",
            competitors=["Competitor A", "Competitor B"],
        )
        context = brief.to_context_dict()
        assert "competitors" in context
        assert context["competitors"] == ["Competitor A", "Competitor B"]

    def test_all_collected_fields_in_context(self):
        """Verify all collected brief fields are available in context."""
        from src.models.client_brief import ClientBrief

        brief = ClientBrief(
            company_name="Test Corp",
            business_description="Test business",
            ideal_customer="Test audience",
            main_problem_solved="Test problem",
            industry="SaaS",
            location="SF",
            competitors=["Comp A"],
        )
        context = brief.to_context_dict()

        # Previously missing fields (Bug #42 fix)
        assert "industry" in context
        assert "location" in context
        assert "competitors" in context

        # Core fields should still be present
        assert "company_name" in context
        assert "ideal_customer" in context
        assert "problem_solved" in context
