"""Unit tests for ResearchPrerequisites.get_parallel_groups."""

import pytest
from backend.services.research_prerequisites import ResearchPrerequisites


@pytest.fixture
def prereqs():
    return ResearchPrerequisites()


class TestGetParallelGroupsEmpty:
    def test_empty_list_returns_empty(self, prereqs):
        assert prereqs.get_parallel_groups([]) == []


class TestGetParallelGroupsSingleTool:
    def test_single_independent_tool(self, prereqs):
        result = prereqs.get_parallel_groups(["seo_keyword_research"])
        assert result == [["seo_keyword_research"]]

    def test_single_dependent_tool(self, prereqs):
        # content_calendar has required deps, but they're not in the list —
        # so it has in_degree 0 and is its own group.
        result = prereqs.get_parallel_groups(["content_calendar"])
        assert result == [["content_calendar"]]


class TestGetParallelGroupsTier1AllIndependent:
    def test_all_tier1_tools_in_one_group(self, prereqs):
        tools = [
            "voice_analysis",
            "brand_archetype",
            "seo_keyword_research",
            "audience_research",
            "determine_competitors",
        ]
        result = prereqs.get_parallel_groups(tools)
        assert len(result) == 1
        assert set(result[0]) == set(tools)

    def test_two_tier1_tools_one_group(self, prereqs):
        result = prereqs.get_parallel_groups(["voice_analysis", "brand_archetype"])
        assert len(result) == 1
        assert set(result[0]) == {"voice_analysis", "brand_archetype"}


class TestGetParallelGroupsWithDependencies:
    def test_tier1_before_tier3(self, prereqs):
        # platform_strategy REQUIRES audience_research
        result = prereqs.get_parallel_groups(["audience_research", "platform_strategy"])
        assert len(result) == 2
        assert result[0] == ["audience_research"]
        assert result[1] == ["platform_strategy"]

    def test_seo_before_content_calendar(self, prereqs):
        # content_calendar REQUIRES seo_keyword_research + platform_strategy
        # platform_strategy REQUIRES audience_research
        tools = [
            "seo_keyword_research",
            "audience_research",
            "platform_strategy",
            "content_calendar",
        ]
        result = prereqs.get_parallel_groups(tools)
        # Group 0: seo + audience (both Tier 1, independent)
        assert set(result[0]) == {"seo_keyword_research", "audience_research"}
        # Group 1: platform_strategy (depends on audience_research)
        assert result[1] == ["platform_strategy"]
        # Group 2: content_calendar (depends on seo + platform_strategy)
        assert result[2] == ["content_calendar"]

    def test_content_gap_after_competitive(self, prereqs):
        # content_gap_analysis REQUIRES competitive_analysis
        result = prereqs.get_parallel_groups(["competitive_analysis", "content_gap_analysis"])
        assert len(result) == 2
        assert result[0] == ["competitive_analysis"]
        assert result[1] == ["content_gap_analysis"]

    def test_independent_tool_not_delayed_by_others_dependencies(self, prereqs):
        # brand_archetype has no deps; content_gap_analysis requires competitive_analysis.
        # brand_archetype should be in the same first group as competitive_analysis,
        # not pushed back to group 2.
        tools = ["brand_archetype", "competitive_analysis", "content_gap_analysis"]
        result = prereqs.get_parallel_groups(tools)
        assert "brand_archetype" in result[0]
        assert "competitive_analysis" in result[0]
        assert result[1] == ["content_gap_analysis"]


class TestGetParallelGroupsCoverage:
    def test_all_tools_appear_exactly_once(self, prereqs):
        tools = [
            "voice_analysis",
            "brand_archetype",
            "seo_keyword_research",
            "audience_research",
            "competitive_analysis",
            "content_gap_analysis",
            "platform_strategy",
            "content_calendar",
        ]
        result = prereqs.get_parallel_groups(tools)
        all_in_groups = [t for g in result for t in g]
        assert sorted(all_in_groups) == sorted(tools)

    def test_groups_are_non_empty(self, prereqs):
        tools = ["seo_keyword_research", "platform_strategy", "audience_research"]
        result = prereqs.get_parallel_groups(tools)
        assert all(len(g) > 0 for g in result)

    def test_order_within_group_consistent(self, prereqs):
        # Calling twice with the same inputs yields the same groups
        tools = ["voice_analysis", "brand_archetype", "seo_keyword_research"]
        assert prereqs.get_parallel_groups(tools) == prereqs.get_parallel_groups(tools)


class TestGetParallelGroupsDepOutsideBatch:
    def test_dep_not_in_batch_treated_as_absent(self, prereqs):
        # platform_strategy requires audience_research, but it's not in the batch.
        # With no in-batch deps, platform_strategy gets in_degree 0 → own group.
        result = prereqs.get_parallel_groups(["platform_strategy"])
        assert result == [["platform_strategy"]]

    def test_dep_partially_in_batch(self, prereqs):
        # content_calendar requires seo_keyword_research AND platform_strategy.
        # Only seo is in the batch — platform dep is absent, so only seo→calendar edge exists.
        tools = ["seo_keyword_research", "content_calendar"]
        result = prereqs.get_parallel_groups(tools)
        assert result[0] == ["seo_keyword_research"]
        assert result[1] == ["content_calendar"]


class TestGetParallelGroupsCircularDependency:
    def test_raises_on_circular_dependency(self, prereqs):
        """Circular dependencies must raise ValueError, not return an unsafe order."""
        # Inject a fake cycle by monkeypatching the dependency graph temporarily.
        import backend.services.research_prerequisites as prereqs_module
        from backend.services.research_prerequisites import (
            ToolDependencies,
            ToolPrerequisite,
            PrerequisiteType,
        )

        original = prereqs.dependencies.copy()
        try:
            # A → B → A (cycle)
            prereqs.dependencies["_fake_a"] = ToolDependencies(
                tool_id="_fake_a",
                tier=1,
                prerequisites=[ToolPrerequisite("_fake_b", PrerequisiteType.REQUIRED, "test")],
                used_by=[],
                description="",
            )
            prereqs.dependencies["_fake_b"] = ToolDependencies(
                tool_id="_fake_b",
                tier=1,
                prerequisites=[ToolPrerequisite("_fake_a", PrerequisiteType.REQUIRED, "test")],
                used_by=[],
                description="",
            )
            with pytest.raises(ValueError, match="Circular dependency"):
                prereqs.get_parallel_groups(["_fake_a", "_fake_b"])
        finally:
            prereqs.dependencies = original
            # prereqs.dependencies is a reference to the module-level TOOL_DEPENDENCIES dict.
            # Reassigning the instance attribute leaves TOOL_DEPENDENCIES polluted, which breaks
            # other tests that import it directly. Restore the global too.
            prereqs_module.TOOL_DEPENDENCIES.clear()
            prereqs_module.TOOL_DEPENDENCIES.update(original)


# ---------------------------------------------------------------------------
# get_dependency_map — adaptive execution foundation
# ---------------------------------------------------------------------------


class TestGetDependencyMapBasics:
    def test_empty_list(self, prereqs):
        assert prereqs.get_dependency_map([]) == {}

    def test_independent_tool_has_empty_deps(self, prereqs):
        result = prereqs.get_dependency_map(["seo_keyword_research"])
        assert result == {"seo_keyword_research": []}

    def test_all_tier1_tools_have_empty_deps(self, prereqs):
        tools = [
            "voice_analysis",
            "brand_archetype",
            "seo_keyword_research",
            "audience_research",
            "determine_competitors",
        ]
        result = prereqs.get_dependency_map(tools)
        for tool in tools:
            assert result[tool] == [], f"{tool} should have no in-run deps"


class TestGetDependencyMapInRunOnly:
    def test_required_dep_in_run_is_listed(self, prereqs):
        # competitive_analysis REQUIRES determine_competitors (REQUIRED)
        result = prereqs.get_dependency_map(["determine_competitors", "competitive_analysis"])
        assert result["competitive_analysis"] == ["determine_competitors"]
        assert result["determine_competitors"] == []

    def test_required_dep_outside_run_not_listed(self, prereqs):
        # competitive_analysis requires determine_competitors but it's not in the batch
        result = prereqs.get_dependency_map(["competitive_analysis"])
        assert result["competitive_analysis"] == []

    def test_recommended_dep_never_listed(self, prereqs):
        # content_gap_analysis RECOMMENDs seo_keyword_research — must NOT appear
        result = prereqs.get_dependency_map(
            ["seo_keyword_research", "content_gap_analysis", "competitive_analysis"]
        )
        # competitive_analysis is REQUIRED; seo is only RECOMMENDED
        assert "seo_keyword_research" not in result["content_gap_analysis"]
        assert "competitive_analysis" in result["content_gap_analysis"]


class TestGetDependencyMapChain:
    def test_three_level_chain(self, prereqs):
        # determine_competitors → competitive_analysis → content_gap_analysis
        tools = ["determine_competitors", "competitive_analysis", "content_gap_analysis"]
        result = prereqs.get_dependency_map(tools)
        assert result["determine_competitors"] == []
        assert result["competitive_analysis"] == ["determine_competitors"]
        assert result["content_gap_analysis"] == ["competitive_analysis"]

    def test_all_tools_present_in_result(self, prereqs):
        tools = ["voice_analysis", "audience_research", "platform_strategy"]
        result = prereqs.get_dependency_map(tools)
        assert set(result.keys()) == set(tools)

    def test_platform_strategy_requires_audience_research_when_both_selected(self, prereqs):
        result = prereqs.get_dependency_map(["audience_research", "platform_strategy"])
        assert result["platform_strategy"] == ["audience_research"]

    def test_full_cascade(self, prereqs):
        # Full chain: determine_competitors → competitive_analysis → content_gap_analysis
        # seo_keyword_research fires independently (no in-run REQUIRED deps)
        tools = [
            "seo_keyword_research",
            "determine_competitors",
            "competitive_analysis",
            "content_gap_analysis",
        ]
        result = prereqs.get_dependency_map(tools)
        assert result["seo_keyword_research"] == []
        assert result["determine_competitors"] == []
        assert result["competitive_analysis"] == ["determine_competitors"]
        assert result["content_gap_analysis"] == ["competitive_analysis"]
