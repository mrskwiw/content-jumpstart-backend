"""Test research tool execution order endpoint (Task #26)"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.research_prerequisites import ResearchPrerequisites

client = TestClient(app)


def test_execution_order_endpoint_basic(test_user_headers):
    """Test /execution-order endpoint returns correct order"""
    # Request execution order for tools with dependencies
    response = client.post(
        "/api/research/execution-order",
        json={
            "tool_names": [
                "content_calendar",
                "seo_keyword_research",
                "platform_strategy",
                "audience_research",
            ]
        },
        headers=test_user_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "execution_order" in data
    assert "tool_count" in data
    assert "parallel_groups" in data
    assert data["tool_count"] == 4

    # Verify correct order (prerequisites first)
    execution_order = data["execution_order"]

    # Tier 1 tools should come before Tier 3/4 tools
    seo_index = execution_order.index("seo_keyword_research")
    audience_index = execution_order.index("audience_research")
    platform_index = execution_order.index("platform_strategy")
    calendar_index = execution_order.index("content_calendar")

    # SEO Keywords (Tier 1) before Content Calendar (Tier 4)
    assert seo_index < calendar_index

    # Audience Research (Tier 1) before Platform Strategy (Tier 3)
    assert audience_index < platform_index

    # Platform Strategy (Tier 3) before Content Calendar (Tier 4)
    assert platform_index < calendar_index

    # Verify parallel_groups structure: each group is a list of tool IDs
    parallel_groups = data["parallel_groups"]
    assert isinstance(parallel_groups, list)
    assert all(isinstance(g, list) for g in parallel_groups)
    # All tools accounted for across all groups
    assert sorted([t for g in parallel_groups for t in g]) == sorted(execution_order)
    # Tier 1 tools (seo + audience) must be in the same first group
    assert set(parallel_groups[0]) >= {"seo_keyword_research", "audience_research"}


def test_execution_order_single_tool(test_user_headers):
    """Test execution order with single tool"""
    response = client.post(
        "/api/research/execution-order",
        json={"tool_names": ["seo_keyword_research"]},
        headers=test_user_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["execution_order"] == ["seo_keyword_research"]
    assert data["tool_count"] == 1
    assert data["parallel_groups"] == [["seo_keyword_research"]]


def test_execution_order_no_dependencies(test_user_headers):
    """Test execution order with tools that have no dependencies"""
    response = client.post(
        "/api/research/execution-order",
        json={"tool_names": ["voice_analysis", "brand_archetype", "seo_keyword_research"]},
        headers=test_user_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # All Tier 1 tools - order should maintain tier grouping
    assert data["tool_count"] == 3
    assert len(data["execution_order"]) == 3
    # All Tier 1 tools have no inter-dependencies — one group containing all three
    assert len(data["parallel_groups"]) == 1
    assert set(data["parallel_groups"][0]) == {
        "voice_analysis",
        "brand_archetype",
        "seo_keyword_research",
    }


def test_execution_order_empty_list(test_user_headers):
    """Test execution order with empty tool list"""
    response = client.post(
        "/api/research/execution-order",
        json={"tool_names": []},
        headers=test_user_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["execution_order"] == []
    assert data["tool_count"] == 0
    assert data["parallel_groups"] == []


def test_execution_order_complex_dependencies(test_user_headers):
    """Test execution order with complex dependency chain"""
    # This should order: Tier 1 → Tier 2 → Tier 3 → Tier 4
    response = client.post(
        "/api/research/execution-order",
        json={
            "tool_names": [
                "content_calendar",  # Tier 4 - requires SEO + Platform
                "platform_strategy",  # Tier 3 - requires Audience
                "market_trends_research",  # Tier 2 - recommends SEO
                "seo_keyword_research",  # Tier 1 - no deps
                "audience_research",  # Tier 1 - no deps
            ]
        },
        headers=test_user_headers,
    )

    assert response.status_code == 200
    data = response.json()
    execution_order = data["execution_order"]

    # Verify tier ordering
    tier1_tools = ["seo_keyword_research", "audience_research"]
    tier2_tools = ["market_trends_research"]
    tier3_tools = ["platform_strategy"]
    tier4_tools = ["content_calendar"]

    # Get indices
    tier1_indices = [execution_order.index(t) for t in tier1_tools if t in execution_order]
    tier2_indices = [execution_order.index(t) for t in tier2_tools if t in execution_order]
    tier3_indices = [execution_order.index(t) for t in tier3_tools if t in execution_order]
    tier4_indices = [execution_order.index(t) for t in tier4_tools if t in execution_order]

    # Tier 1 should come before Tier 2
    if tier1_indices and tier2_indices:
        assert max(tier1_indices) < min(tier2_indices)

    # Tier 2 should come before Tier 4
    if tier2_indices and tier4_indices:
        assert max(tier2_indices) < min(tier4_indices)

    # Tier 3 should come before Tier 4
    if tier3_indices and tier4_indices:
        assert max(tier3_indices) < min(tier4_indices)

    # Verify parallel_groups: Tier 1 tools are independent and share the first group
    parallel_groups = data["parallel_groups"]
    assert isinstance(parallel_groups, list)
    assert all(isinstance(g, list) for g in parallel_groups)
    all_grouped = [t for g in parallel_groups for t in g]
    assert sorted(all_grouped) == sorted(data["execution_order"])
    first_group = set(parallel_groups[0])
    assert "seo_keyword_research" in first_group
    assert "audience_research" in first_group


def test_execution_order_raises_on_circular_dependency():
    """get_execution_order must raise ValueError on circular deps, not return raw input order."""
    from backend.services.research_prerequisites import (
        ResearchPrerequisites,
        ToolDependencies,
        ToolPrerequisite,
        PrerequisiteType,
    )

    prereqs = ResearchPrerequisites()
    original = prereqs.dependencies.copy()
    try:
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
            prereqs.get_execution_order(["_fake_a", "_fake_b"])
    finally:
        prereqs.dependencies = original
        # `prereqs.dependencies` IS the module-level TOOL_DEPENDENCIES dict, so the two
        # inserts above mutate global state. Rebinding the instance attribute leaves the
        # global carrying _fake_a/_fake_b, which later broke
        # tests/unit/test_research_prerequisites.py::test_all_tools_defined — a failure
        # that only appeared in a full-suite run and passed in isolation. Restore the
        # global too. (The unit-test twin of this case, in
        # tests/unit/services/test_research_prerequisites_parallel.py, already does this.)
        import backend.services.research_prerequisites as prereqs_module

        prereqs_module.TOOL_DEPENDENCIES.clear()
        prereqs_module.TOOL_DEPENDENCIES.update(original)


def test_prerequisite_system_directly():
    """Test ResearchPrerequisites class directly"""
    prereqs = ResearchPrerequisites()

    # Test Content Calendar prerequisites
    deps = prereqs.get_dependencies("content_calendar")
    assert deps is not None
    assert deps.tier == 4

    required = prereqs.get_required_prerequisites("content_calendar")
    assert "seo_keyword_research" in required
    assert "platform_strategy" in required

    # Test Platform Strategy prerequisites
    required = prereqs.get_required_prerequisites("platform_strategy")
    assert "audience_research" in required

    # Test Market Trends prerequisites
    recommended = prereqs.get_recommended_prerequisites("market_trends_research")
    assert "seo_keyword_research" in recommended


def test_prerequisite_checking():
    """Test prerequisite checking logic"""
    prereqs = ResearchPrerequisites()

    # Test with no completed tools
    completed = set()
    can_run, missing_req, missing_rec = prereqs.check_prerequisites_met(
        "content_calendar", completed
    )

    assert not can_run  # Should be blocked
    assert "seo_keyword_research" in missing_req
    assert "platform_strategy" in missing_req

    # Test with prerequisites met
    completed = {"seo_keyword_research", "platform_strategy", "audience_research"}
    can_run, missing_req, missing_rec = prereqs.check_prerequisites_met(
        "content_calendar", completed
    )

    assert can_run  # Should be allowed
    assert len(missing_req) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
