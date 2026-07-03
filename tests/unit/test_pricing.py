"""
Unit tests for research tool pricing, bundle detection, and full project price breakdown.

Covers:
- calculate_tools_cost(): a la carte, each bundle, combined bundles, priority order
- calculate_full_project_price(): combined breakdown
- KNOWN_TOOL_IDS: validates tool catalog completeness
"""

import pytest
from src.config.pricing import (
    TOOLS,
    KNOWN_TOOL_IDS,
    calculate_tools_cost,
    calculate_full_project_price,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_ids_in_group(group: str) -> list[str]:
    return [tid for tid, t in TOOLS.items() if t["group"] == group]


FOUNDATION_IDS = _all_ids_in_group("foundation")
SEO_IDS = _all_ids_in_group("seo")
ADVANCED_IDS = _all_ids_in_group("advanced")
ALL_IDS = list(TOOLS.keys())


# ---------------------------------------------------------------------------
# KNOWN_TOOL_IDS
# ---------------------------------------------------------------------------


class TestToolCatalog:
    """Sanity checks on the tool catalog itself."""

    def test_known_tool_ids_count(self):
        """12 tools must be registered."""
        assert len(KNOWN_TOOL_IDS) == 12

    def test_foundation_group_has_4_tools(self):
        assert len(FOUNDATION_IDS) == 4

    def test_seo_group_has_3_tools(self):
        assert len(SEO_IDS) == 3

    def test_advanced_group_has_5_tools(self):
        assert len(ADVANCED_IDS) == 5

    def test_all_tools_have_required_keys(self):
        for tid, tool in TOOLS.items():
            assert "name" in tool, f"Missing 'name' for {tid}"
            assert "price" in tool, f"Missing 'price' for {tid}"
            assert "group" in tool, f"Missing 'group' for {tid}"
            assert tool["price"] > 0, f"Price must be positive for {tid}"

    def test_all_groups_are_valid(self):
        valid_groups = {"foundation", "seo", "advanced"}
        for tid, tool in TOOLS.items():
            assert tool["group"] in valid_groups, f"Invalid group for {tid}: {tool['group']}"


# ---------------------------------------------------------------------------
# calculate_tools_cost — no selection
# ---------------------------------------------------------------------------


class TestToolsCostEmpty:
    def test_empty_list_returns_zeros(self):
        result = calculate_tools_cost([])
        assert result["tools_cost"] == 0.0
        assert result["discount_amount"] == 0.0
        assert result["applied_bundles"] == []

    def test_none_list_raises_or_empty(self):
        """Passing an empty list is the canonical no-op input."""
        result = calculate_tools_cost([])
        assert result["tools_cost"] == 0.0


# ---------------------------------------------------------------------------
# calculate_tools_cost — a la carte (no bundles triggered)
# ---------------------------------------------------------------------------


class TestToolsCostALaCarte:
    def test_single_foundation_tool(self):
        result = calculate_tools_cost(["voice_analysis"])
        assert result["tools_cost"] == 400.0
        assert result["discount_amount"] == 0.0
        assert result["applied_bundles"] == []

    def test_two_foundation_tools_no_bundle(self):
        # Only 2 of 4 foundation tools — no bundle
        result = calculate_tools_cost(["voice_analysis", "brand_archetype"])
        assert result["tools_cost"] == 400.0 + 300.0
        assert result["discount_amount"] == 0.0
        assert result["applied_bundles"] == []

    def test_two_seo_tools_no_bundle(self):
        result = calculate_tools_cost(["seo_keyword_research", "competitive_analysis"])
        assert result["tools_cost"] == 400.0 + 500.0
        assert result["discount_amount"] == 0.0
        assert result["applied_bundles"] == []

    def test_single_advanced_tool(self):
        result = calculate_tools_cost(["content_audit"])
        assert result["tools_cost"] == 400.0
        assert result["discount_amount"] == 0.0
        assert result["applied_bundles"] == []

    def test_multiple_advanced_tools_ala_carte(self):
        result = calculate_tools_cost(["content_audit", "platform_strategy", "market_trends"])
        expected = 400.0 + 300.0 + 400.0
        assert result["tools_cost"] == expected
        assert result["discount_amount"] == 0.0
        assert result["applied_bundles"] == []


# ---------------------------------------------------------------------------
# calculate_tools_cost — Foundation Pack
# ---------------------------------------------------------------------------


class TestFoundationPack:
    def test_all_foundation_tools_triggers_bundle(self):
        result = calculate_tools_cost(FOUNDATION_IDS)
        assert result["tools_cost"] == 1500.0
        assert result["discount_amount"] == 300.0  # a la carte 1800 − 1500
        assert "Foundation Pack" in result["applied_bundles"]

    def test_foundation_pack_with_one_advanced_tool(self):
        """Foundation Pack + one advanced tool a la carte."""
        tools = FOUNDATION_IDS + ["content_audit"]
        result = calculate_tools_cost(tools)
        assert result["tools_cost"] == 1500.0 + 400.0  # pack + audit
        assert result["discount_amount"] == 300.0
        assert "Foundation Pack" in result["applied_bundles"]

    def test_foundation_pack_with_two_seo_tools_no_seo_bundle(self):
        """Foundation Pack + 2 SEO (insufficient for SEO Pack) = pack + a la carte."""
        tools = FOUNDATION_IDS + ["seo_keyword_research", "competitive_analysis"]
        result = calculate_tools_cost(tools)
        assert result["tools_cost"] == 1500.0 + 400.0 + 500.0
        assert "Foundation Pack" in result["applied_bundles"]
        assert "SEO Pack" not in result["applied_bundles"]


# ---------------------------------------------------------------------------
# calculate_tools_cost — SEO Pack
# ---------------------------------------------------------------------------


class TestSeoPack:
    def test_all_seo_tools_triggers_bundle(self):
        result = calculate_tools_cost(SEO_IDS)
        assert result["tools_cost"] == 1300.0
        assert result["discount_amount"] == 100.0  # a la carte 1400 − 1300
        assert "SEO Pack" in result["applied_bundles"]

    def test_seo_pack_with_one_advanced_tool(self):
        tools = SEO_IDS + ["platform_strategy"]
        result = calculate_tools_cost(tools)
        assert result["tools_cost"] == 1300.0 + 300.0
        assert "SEO Pack" in result["applied_bundles"]


# ---------------------------------------------------------------------------
# calculate_tools_cost — Foundation + SEO packs separately
# ---------------------------------------------------------------------------


class TestFoundationAndSeoPacks:
    def test_both_packs_applied_independently(self):
        tools = FOUNDATION_IDS + SEO_IDS
        result = calculate_tools_cost(tools)
        # This case triggers Complete Strategy, not separate packs
        # (Complete Strategy wins because all 7 strategy tools are present)
        assert "Complete Strategy" in result["applied_bundles"]
        assert result["tools_cost"] == 2400.0

    def test_foundation_and_seo_with_one_extra_advanced(self):
        """Complete Strategy + one advanced tool a la carte."""
        tools = FOUNDATION_IDS + SEO_IDS + ["content_audit"]
        result = calculate_tools_cost(tools)
        assert "Complete Strategy" in result["applied_bundles"]
        assert result["tools_cost"] == 2400.0 + 400.0


# ---------------------------------------------------------------------------
# calculate_tools_cost — Complete Strategy
# ---------------------------------------------------------------------------


class TestCompleteStrategy:
    def test_all_strategy_tools_triggers_complete_strategy(self):
        result = calculate_tools_cost(FOUNDATION_IDS + SEO_IDS)
        assert result["tools_cost"] == 2400.0
        assert result["discount_amount"] == 800.0  # 3200 − 2400
        assert "Complete Strategy" in result["applied_bundles"]
        assert "Foundation Pack" not in result["applied_bundles"]
        assert "SEO Pack" not in result["applied_bundles"]


# ---------------------------------------------------------------------------
# calculate_tools_cost — Ultimate Pack
# ---------------------------------------------------------------------------


class TestUltimatePack:
    def test_all_12_tools_triggers_ultimate_pack(self):
        result = calculate_tools_cost(ALL_IDS)
        assert result["tools_cost"] == 4500.0
        assert result["discount_amount"] == 600.0  # 5100 − 4500
        assert "Ultimate Pack" in result["applied_bundles"]
        assert len(result["applied_bundles"]) == 1  # Only Ultimate Pack

    def test_ultimate_pack_wins_over_complete_strategy(self):
        """All 12 tools → Ultimate Pack, not Complete Strategy."""
        result = calculate_tools_cost(ALL_IDS)
        assert "Complete Strategy" not in result["applied_bundles"]
        assert "Foundation Pack" not in result["applied_bundles"]
        assert "SEO Pack" not in result["applied_bundles"]


# ---------------------------------------------------------------------------
# calculate_tools_cost — bundle priority
# ---------------------------------------------------------------------------


class TestBundlePriority:
    def test_11_tools_no_ultimate_pack(self):
        """Remove one advanced tool — should NOT trigger Ultimate Pack."""
        partial = [tid for tid in ALL_IDS if tid != "market_trends"]
        result = calculate_tools_cost(partial)
        assert "Ultimate Pack" not in result["applied_bundles"]

    def test_6_strategy_tools_no_complete_strategy(self):
        """All foundation + 2 SEO — triggers Foundation Pack only."""
        tools = FOUNDATION_IDS + SEO_IDS[:2]
        result = calculate_tools_cost(tools)
        assert "Complete Strategy" not in result["applied_bundles"]
        assert "Foundation Pack" in result["applied_bundles"]
        assert "SEO Pack" not in result["applied_bundles"]


# ---------------------------------------------------------------------------
# calculate_full_project_price
# ---------------------------------------------------------------------------


class TestFullProjectPrice:
    def test_posts_only_no_research_no_tools(self):
        result = calculate_full_project_price(num_posts=30)
        assert result["posts_cost"] == 1200.0
        assert result["research_addon_cost"] == 0.0
        assert result["tools_cost"] == 0.0
        assert result["discount_amount"] == 0.0
        assert result["total_price"] == 1200.0
        assert result["applied_bundles"] == []

    def test_with_research_addon(self):
        # Bug #43: research_per_post feature deprecated, always returns 0.0
        result = calculate_full_project_price(num_posts=30, research_per_post=True)
        assert result["posts_cost"] == 1200.0
        assert result["research_addon_cost"] == 0.0  # DEPRECATED: was 30 * $15 = 450.0
        assert result["total_price"] == 1200.0  # posts only (research addon deprecated)

    def test_with_foundation_tools(self):
        result = calculate_full_project_price(
            num_posts=30,
            research_per_post=False,
            selected_tools=FOUNDATION_IDS,
        )
        assert result["posts_cost"] == 1200.0
        assert result["tools_cost"] == 1500.0
        assert result["discount_amount"] == 300.0
        assert result["total_price"] == 2700.0
        assert "Foundation Pack" in result["applied_bundles"]

    def test_with_research_and_foundation_tools(self):
        # Bug #43: research_per_post feature deprecated
        result = calculate_full_project_price(
            num_posts=30,
            research_per_post=True,
            selected_tools=FOUNDATION_IDS,
        )
        assert result["posts_cost"] == 1200.0
        assert result["research_addon_cost"] == 0.0  # DEPRECATED: was 450.0
        assert result["tools_cost"] == 1500.0
        assert result["total_price"] == 2700.0  # posts + tools (no research addon)

    def test_complete_strategy_total(self):
        # Bug #43: research_per_post feature deprecated
        result = calculate_full_project_price(
            num_posts=30,
            research_per_post=True,
            selected_tools=FOUNDATION_IDS + SEO_IDS,
        )
        assert result["tools_cost"] == 2400.0
        assert result["discount_amount"] == 800.0
        assert result["total_price"] == 1200.0 + 2400.0  # posts + tools (no research addon)

    def test_ultimate_pack_total(self):
        result = calculate_full_project_price(
            num_posts=30,
            selected_tools=ALL_IDS,
        )
        assert result["tools_cost"] == 4500.0
        assert result["total_price"] == 1200.0 + 4500.0

    def test_none_tools_treated_as_empty(self):
        result = calculate_full_project_price(num_posts=10, selected_tools=None)
        assert result["tools_cost"] == 0.0
        assert result["total_price"] == 400.0  # 10 * $40

    def test_single_post(self):
        result = calculate_full_project_price(num_posts=1)
        assert result["posts_cost"] == 40.0
        assert result["total_price"] == 40.0

    def test_custom_price_per_post(self):
        result = calculate_full_project_price(num_posts=10, price_per_post=50.0)
        assert result["posts_cost"] == 500.0

    def test_custom_research_price(self):
        # Bug #43: Function parameter still allows custom prices for backward compatibility
        result = calculate_full_project_price(
            num_posts=10, research_per_post=True, research_price=20.0
        )
        assert result["research_addon_cost"] == 200.0  # Custom parameter overrides default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
