"""Unit tests for Research Prerequisites System

Tests the dependency registry and prerequisite checking logic.
"""

import pytest

from backend.services.research_prerequisites import (
    PrerequisiteType,
    ResearchPrerequisites,
    ToolDependencies,
    ToolPrerequisite,
    TOOL_DEPENDENCIES,
)


class TestPrerequisiteRegistry:
    """Test the prerequisites registry structure"""

    def test_all_tools_defined(self):
        """Verify all 14 research tools are in registry"""
        expected_tools = {
            "voice_analysis",
            "brand_archetype",
            "seo_keyword_research",
            "audience_research",
            "competitive_analysis",
            "content_gap_analysis",
            "market_trends_research",
            "icp_workshop",
            "content_audit",
            "platform_strategy",
            "story_mining",
            "content_calendar",
            "business_report",
            "determine_competitors",
        }

        assert set(TOOL_DEPENDENCIES.keys()) == expected_tools

    def test_tier_1_has_no_prerequisites(self):
        """Tier 1 foundation tools should have no prerequisites"""
        tier_1_tools = [
            "voice_analysis",
            "brand_archetype",
            "seo_keyword_research",
            "audience_research",
            # competitive_analysis was promoted to Tier 2 (requires determine_competitors)
        ]

        for tool_id in tier_1_tools:
            deps = TOOL_DEPENDENCIES[tool_id]
            assert deps.tier == 1, f"{tool_id} should be Tier 1"
            assert len(deps.prerequisites) == 0, f"{tool_id} should have no prerequisites"

    def test_competitive_analysis_requires_determine_competitors(self):
        """competitive_analysis is Tier 2 with a REQUIRED dep on determine_competitors"""
        from backend.services.research_prerequisites import PrerequisiteType

        deps = TOOL_DEPENDENCIES["competitive_analysis"]
        assert deps.tier == 2
        assert len(deps.prerequisites) == 1
        prereq = deps.prerequisites[0]
        assert prereq.tool_id == "determine_competitors"
        assert prereq.type == PrerequisiteType.REQUIRED

    def test_seo_keywords_has_no_prerequisites(self):
        """SEO Keywords tool should have no prerequisites"""
        deps = TOOL_DEPENDENCIES["seo_keyword_research"]

        assert deps.tier == 1
        assert len(deps.prerequisites) == 0
        assert "market_trends_research" in deps.used_by
        assert "content_gap_analysis" in deps.used_by
        assert "content_calendar" in deps.used_by

    def test_content_calendar_has_required_prerequisites(self):
        """Content Calendar should REQUIRE SEO and Platform Strategy"""
        deps = TOOL_DEPENDENCIES["content_calendar"]

        assert deps.tier == 4

        required = [p for p in deps.prerequisites if p.type == PrerequisiteType.REQUIRED]
        required_tools = [p.tool_id for p in required]

        assert "seo_keyword_research" in required_tools
        assert "platform_strategy" in required_tools

    def test_platform_strategy_requires_audience(self):
        """Platform Strategy should REQUIRE Audience Research"""
        deps = TOOL_DEPENDENCIES["platform_strategy"]

        required = [p for p in deps.prerequisites if p.type == PrerequisiteType.REQUIRED]
        required_tools = [p.tool_id for p in required]

        assert "audience_research" in required_tools

    def test_market_trends_recommends_seo(self):
        """Market Trends should RECOMMEND SEO Keywords"""
        deps = TOOL_DEPENDENCIES["market_trends_research"]

        recommended = [p for p in deps.prerequisites if p.type == PrerequisiteType.RECOMMENDED]
        recommended_tools = [p.tool_id for p in recommended]

        assert "seo_keyword_research" in recommended_tools

    def test_all_prerequisites_exist(self):
        """All prerequisite tool_ids should exist in registry"""
        for tool_id, deps in TOOL_DEPENDENCIES.items():
            for prereq in deps.prerequisites:
                assert (
                    prereq.tool_id in TOOL_DEPENDENCIES
                ), f"{tool_id} references non-existent prerequisite: {prereq.tool_id}"

    def test_all_used_by_exist(self):
        """All 'used_by' tool_ids should exist in registry"""
        for tool_id, deps in TOOL_DEPENDENCIES.items():
            for used_by_tool in deps.used_by:
                assert (
                    used_by_tool in TOOL_DEPENDENCIES
                ), f"{tool_id} references non-existent used_by tool: {used_by_tool}"


class TestResearchPrerequisitesClass:
    """Test the ResearchPrerequisites class methods"""

    @pytest.fixture
    def prerequisites(self):
        """Create ResearchPrerequisites instance"""
        return ResearchPrerequisites()

    def test_get_dependencies(self, prerequisites):
        """Test getting dependencies for a tool"""
        deps = prerequisites.get_dependencies("seo_keyword_research")

        assert deps is not None
        assert deps.tool_id == "seo_keyword_research"
        assert deps.tier == 1

    def test_get_dependencies_invalid_tool(self, prerequisites):
        """Test getting dependencies for non-existent tool"""
        deps = prerequisites.get_dependencies("invalid_tool")

        assert deps is None

    def test_get_required_prerequisites(self, prerequisites):
        """Test getting required prerequisites"""
        # Content Calendar requires SEO + Platform
        required = prerequisites.get_required_prerequisites("content_calendar")

        assert "seo_keyword_research" in required
        assert "platform_strategy" in required
        assert len(required) == 2

    def test_get_required_prerequisites_none(self, prerequisites):
        """Test getting required prerequisites for tool with none"""
        # SEO has no prerequisites
        required = prerequisites.get_required_prerequisites("seo_keyword_research")

        assert required == []

    def test_get_recommended_prerequisites(self, prerequisites):
        """Test getting recommended prerequisites"""
        # Market Trends recommends SEO
        recommended = prerequisites.get_recommended_prerequisites("market_trends_research")

        assert "seo_keyword_research" in recommended

    def test_get_optional_prerequisites(self, prerequisites):
        """Test getting optional prerequisites"""
        # Content Audit has SEO as optional
        optional = prerequisites.get_optional_prerequisites("content_audit")

        assert "seo_keyword_research" in optional

    def test_get_tool_tier(self, prerequisites):
        """Test getting tool tier"""
        assert prerequisites.get_tool_tier("seo_keyword_research") == 1
        assert prerequisites.get_tool_tier("market_trends_research") == 2
        assert prerequisites.get_tool_tier("platform_strategy") == 3
        assert prerequisites.get_tool_tier("content_calendar") == 4

    def test_get_tool_tier_invalid(self, prerequisites):
        """Test getting tier for invalid tool"""
        tier = prerequisites.get_tool_tier("invalid_tool")

        assert tier == 999  # Unknown tools go last


class TestPrerequisiteChecking:
    """Test prerequisite checking logic"""

    @pytest.fixture
    def prerequisites(self):
        return ResearchPrerequisites()

    def test_check_prerequisites_met_all_complete(self, prerequisites):
        """Test when all prerequisites are met"""
        completed = {"seo_keyword_research", "platform_strategy"}

        can_run, missing_required, missing_recommended = prerequisites.check_prerequisites_met(
            "content_calendar", completed
        )

        assert can_run is True
        assert missing_required == []

    def test_check_prerequisites_met_missing_required(self, prerequisites):
        """Test when required prerequisites are missing"""
        completed = {"seo_keyword_research"}  # Missing platform_strategy

        can_run, missing_required, missing_recommended = prerequisites.check_prerequisites_met(
            "content_calendar", completed
        )

        assert can_run is False
        assert "platform_strategy" in missing_required

    def test_check_prerequisites_met_missing_all(self, prerequisites):
        """Test when all prerequisites are missing"""
        completed = set()

        can_run, missing_required, missing_recommended = prerequisites.check_prerequisites_met(
            "content_calendar", completed
        )

        assert can_run is False
        assert "seo_keyword_research" in missing_required
        assert "platform_strategy" in missing_required

    def test_check_prerequisites_met_no_prerequisites(self, prerequisites):
        """Test tool with no prerequisites"""
        completed = set()

        can_run, missing_required, missing_recommended = prerequisites.check_prerequisites_met(
            "seo_keyword_research", completed
        )

        assert can_run is True
        assert missing_required == []
        assert missing_recommended == []

    def test_check_prerequisites_met_missing_recommended(self, prerequisites):
        """Test when recommended prerequisites are missing"""
        # Market Trends recommends SEO but doesn't require it
        completed = set()

        can_run, missing_required, missing_recommended = prerequisites.check_prerequisites_met(
            "market_trends_research", completed
        )

        assert can_run is True  # Can still run
        assert missing_required == []
        assert "seo_keyword_research" in missing_recommended

    def test_check_prerequisites_platform_requires_audience(self, prerequisites):
        """Test Platform Strategy requires Audience Research"""
        completed = set()

        can_run, missing_required, missing_recommended = prerequisites.check_prerequisites_met(
            "platform_strategy", completed
        )

        assert can_run is False
        assert "audience_research" in missing_required


class TestExecutionOrder:
    """Test execution order generation (topological sort)"""

    @pytest.fixture
    def prerequisites(self):
        return ResearchPrerequisites()

    def test_execution_order_simple(self, prerequisites):
        """Test simple execution order"""
        tools = ["content_calendar", "seo_keyword_research", "platform_strategy"]

        ordered = prerequisites.get_execution_order(tools)

        # SEO should come before Platform, Platform before Calendar
        seo_idx = ordered.index("seo_keyword_research")
        platform_idx = ordered.index("platform_strategy")
        calendar_idx = ordered.index("content_calendar")

        assert seo_idx < platform_idx < calendar_idx

    def test_execution_order_all_tier_1(self, prerequisites):
        """Test execution order with only Tier 1 tools (no dependencies)"""
        tools = [
            "seo_keyword_research",
            "brand_archetype",
            "audience_research",
        ]

        ordered = prerequisites.get_execution_order(tools)

        # All Tier 1 - any order is valid, should return same length
        assert len(ordered) == 3
        assert set(ordered) == set(tools)

    def test_execution_order_complex(self, prerequisites):
        """Test complex execution order with multiple tiers"""
        tools = [
            "content_calendar",  # Tier 4
            "platform_strategy",  # Tier 3
            "market_trends_research",  # Tier 2
            "seo_keyword_research",  # Tier 1
            "audience_research",  # Tier 1
        ]

        ordered = prerequisites.get_execution_order(tools)

        # Get indices
        indices = {tool: ordered.index(tool) for tool in tools}

        # Tier 1 tools should come first
        assert indices["seo_keyword_research"] < indices["market_trends_research"]
        assert indices["audience_research"] < indices["platform_strategy"]

        # Platform should come before Calendar
        assert indices["platform_strategy"] < indices["content_calendar"]

        # SEO should come before Calendar
        assert indices["seo_keyword_research"] < indices["content_calendar"]

    def test_execution_order_reverse_input(self, prerequisites):
        """Test that input order doesn't matter"""
        tools_forward = ["seo_keyword_research", "market_trends_research", "content_calendar"]
        tools_reverse = ["content_calendar", "market_trends_research", "seo_keyword_research"]

        ordered_forward = prerequisites.get_execution_order(tools_forward)
        ordered_reverse = prerequisites.get_execution_order(tools_reverse)

        # Should produce same order regardless of input order
        assert ordered_forward == ordered_reverse

    def test_execution_order_single_tool(self, prerequisites):
        """Test execution order with single tool"""
        tools = ["seo_keyword_research"]

        ordered = prerequisites.get_execution_order(tools)

        assert ordered == ["seo_keyword_research"]

    def test_execution_order_independent_tools(self, prerequisites):
        """Test tools with no dependencies between them"""
        tools = ["voice_analysis", "competitive_analysis"]

        ordered = prerequisites.get_execution_order(tools)

        # Both Tier 1, either order is valid
        assert len(ordered) == 2
        assert set(ordered) == set(tools)

    def test_execution_order_respects_tiers(self, prerequisites):
        """Test that execution order respects tier hierarchy"""
        # Get one tool from each tier
        tools = [
            "content_calendar",  # Tier 4
            "platform_strategy",  # Tier 3
            "market_trends_research",  # Tier 2
            "seo_keyword_research",  # Tier 1
        ]

        ordered = prerequisites.get_execution_order(tools)

        # Verify tier ordering
        tiers = [prerequisites.get_tool_tier(tool) for tool in ordered]

        # Tiers should be non-decreasing (tier 1 before tier 2, etc.)
        for i in range(len(tiers) - 1):
            assert tiers[i] <= tiers[i + 1]


class TestMissingPrerequisitesMessage:
    """Test user-friendly error message generation"""

    @pytest.fixture
    def prerequisites(self):
        return ResearchPrerequisites()

    def test_missing_required_message(self, prerequisites):
        """Test message for missing required prerequisites"""
        message = prerequisites.get_missing_prerequisites_message(
            "content_calendar",
            missing_required=["seo_keyword_research", "platform_strategy"],
            missing_recommended=[],
        )

        assert "Content Calendar cannot run yet" in message
        assert "Seo Keyword Research" in message  # Title case format
        assert "Platform Strategy" in message
        assert "Provides topics to cover" in message
        assert "Determines where to post" in message

    def test_missing_recommended_message(self, prerequisites):
        """Test message for missing recommended prerequisites"""
        message = prerequisites.get_missing_prerequisites_message(
            "market_trends_research",
            missing_required=[],
            missing_recommended=["seo_keyword_research"],
        )

        assert "will run" in message
        assert "results would be better" in message
        assert "Seo Keyword Research" in message  # Title case format

    def test_missing_both_message(self, prerequisites):
        """Test message for missing both required and recommended"""
        message = prerequisites.get_missing_prerequisites_message(
            "platform_strategy",
            missing_required=["audience_research"],
            missing_recommended=["market_trends_research"],
        )

        assert "Platform Strategy cannot run yet" in message
        assert "Audience Research" in message
        assert "Market Trends Research" in message

    def test_no_missing_message(self, prerequisites):
        """Test message when nothing is missing"""
        message = prerequisites.get_missing_prerequisites_message(
            "seo_keyword_research", missing_required=[], missing_recommended=[]
        )

        assert message == ""


class TestPrerequisiteScenarios:
    """Test real-world prerequisite scenarios"""

    @pytest.fixture
    def prerequisites(self):
        return ResearchPrerequisites()

    def test_scenario_seo_first(self, prerequisites):
        """Scenario: User runs SEO Keywords first (foundation tool)"""
        completed = set()

        can_run, missing_required, _ = prerequisites.check_prerequisites_met(
            "seo_keyword_research", completed
        )

        assert can_run is True
        assert missing_required == []

    def test_scenario_market_trends_after_seo(self, prerequisites):
        """Scenario: User runs Market Trends after SEO"""
        completed = {"seo_keyword_research"}

        can_run, missing_required, missing_recommended = prerequisites.check_prerequisites_met(
            "market_trends_research", completed
        )

        assert can_run is True
        assert missing_required == []
        assert missing_recommended == []  # SEO is complete

    def test_scenario_market_trends_without_seo(self, prerequisites):
        """Scenario: User runs Market Trends without SEO (should work but warn)"""
        completed = set()

        can_run, missing_required, missing_recommended = prerequisites.check_prerequisites_met(
            "market_trends_research", completed
        )

        assert can_run is True  # Can run without SEO
        assert missing_required == []
        assert "seo_keyword_research" in missing_recommended  # But recommended

    def test_scenario_content_calendar_blocked(self, prerequisites):
        """Scenario: User tries Content Calendar without prerequisites"""
        completed = set()

        can_run, missing_required, _ = prerequisites.check_prerequisites_met(
            "content_calendar", completed
        )

        assert can_run is False
        assert "seo_keyword_research" in missing_required
        assert "platform_strategy" in missing_required

    def test_scenario_platform_strategy_blocked(self, prerequisites):
        """Scenario: User tries Platform Strategy without Audience Research"""
        completed = {"seo_keyword_research"}  # Has SEO but not Audience

        can_run, missing_required, _ = prerequisites.check_prerequisites_met(
            "platform_strategy", completed
        )

        assert can_run is False
        assert "audience_research" in missing_required

    def test_scenario_full_workflow(self, prerequisites):
        """Scenario: User runs full workflow in correct order"""
        completed = set()

        # Step 1: Run SEO Keywords
        can_run, _, _ = prerequisites.check_prerequisites_met("seo_keyword_research", completed)
        assert can_run is True
        completed.add("seo_keyword_research")

        # Step 2: Run Audience Research
        can_run, _, _ = prerequisites.check_prerequisites_met("audience_research", completed)
        assert can_run is True
        completed.add("audience_research")

        # Step 3: Run Market Trends (has SEO)
        can_run, _, _ = prerequisites.check_prerequisites_met("market_trends_research", completed)
        assert can_run is True
        completed.add("market_trends_research")

        # Step 4: Run Platform Strategy (has Audience)
        can_run, _, _ = prerequisites.check_prerequisites_met("platform_strategy", completed)
        assert can_run is True
        completed.add("platform_strategy")

        # Step 5: Run Content Calendar (has SEO + Platform)
        can_run, _, _ = prerequisites.check_prerequisites_met("content_calendar", completed)
        assert can_run is True
