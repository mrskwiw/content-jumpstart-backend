"""Unit tests for backend.pricing.credit_pricing."""

import pytest

from backend.pricing.credit_pricing import (
    CONTENT_COSTS,
    RESEARCH_TOOL_COSTS,
    STANDARD_PACKAGE_RATE,
    ADDITIONAL_CREDIT_RATE,
    get_research_tool_cost,
    get_content_cost,
    calculate_project_cost,
)


class TestGetResearchToolCost:
    def test_known_tool_returns_positive(self):
        assert get_research_tool_cost("seo_keyword_research") == 200

    def test_another_known_tool(self):
        assert get_research_tool_cost("icp_workshop") == 300

    def test_unknown_tool_returns_zero(self):
        assert get_research_tool_cost("made_up_tool") == 0

    def test_all_tools_positive(self):
        for tool, cost in RESEARCH_TOOL_COSTS.items():
            assert cost > 0, f"{tool} has non-positive cost"


class TestGetContentCost:
    def test_blog_post_cost(self):
        assert get_content_cost("blog_post") == 20

    def test_unknown_type_returns_zero(self):
        assert get_content_cost("nonexistent") == 0

    def test_all_content_types_positive(self):
        for ctype, cost in CONTENT_COSTS.items():
            assert cost > 0


class TestCalculateProjectCost:
    def test_blog_posts_only(self):
        result = calculate_project_cost(num_blog_posts=10)
        assert result["blog_posts"]["total"] == 200  # 10 * 20
        assert result["total_credits"] == 200

    def test_research_tools_only(self):
        result = calculate_project_cost(research_tools=["icp_workshop"])
        assert result["research_tools"]["total"] == 300
        assert result["total_credits"] == 300

    def test_combined_cost(self):
        result = calculate_project_cost(num_blog_posts=5, research_tools=["seo_keyword_research"])
        # 5 * 20 = 100 posts + 200 research = 300
        assert result["total_credits"] == 300

    def test_unknown_tool_excluded(self):
        result = calculate_project_cost(research_tools=["nonexistent"])
        assert result["research_tools"]["total"] == 0

    def test_cost_usd_standard_rate(self):
        result = calculate_project_cost(num_blog_posts=10)
        assert result["estimated_cost"]["standard_rate"] == 400.0  # 200 * $2

    def test_cost_usd_additional_rate(self):
        result = calculate_project_cost(num_blog_posts=10)
        assert result["estimated_cost"]["additional_rate"] == 500.0  # 200 * $2.50

    def test_zero_posts_zero_cost(self):
        result = calculate_project_cost()
        assert result["total_credits"] == 0

    def test_returns_breakdown(self):
        result = calculate_project_cost(num_blog_posts=3, research_tools=["icp_workshop"])
        assert "blog_posts" in result
        assert "research_tools" in result
        assert result["research_tools"]["breakdown"]["icp_workshop"] == 300

    def test_package_rates_consistent(self):
        result = calculate_project_cost(num_blog_posts=100)
        assert (
            result["estimated_cost"]["additional_rate"] > result["estimated_cost"]["standard_rate"]
        )
