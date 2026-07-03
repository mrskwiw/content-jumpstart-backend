"""
Unit tests for backend configuration and credit pricing helpers.
"""

import pytest

from backend.config import Settings
from backend.pricing.credit_pricing import (
    ADDITIONAL_CREDIT_RATE,
    CONTENT_COSTS,
    MAX_OPERATION_CREDITS,
    MIN_RESEARCH_TOOL_CREDITS,
    RESEARCH_TOOL_COSTS,
    STANDARD_PACKAGE_RATE,
    calculate_project_cost,
    get_content_cost,
    get_research_tool_cost,
)


class TestSettings:
    def test_cors_origins_list_strips_whitespace(self):
        settings = Settings(SECRET_KEY="x" * 32, ANTHROPIC_API_KEY="test-key")
        settings.CORS_ORIGINS = " http://localhost:3000 ,https://example.com "

        assert settings.cors_origins_list == ["http://localhost:3000", "https://example.com"]

    def test_super_admin_emails_list_normalizes(self):
        settings = Settings(SECRET_KEY="x" * 32, ANTHROPIC_API_KEY="test-key")
        settings.SUPER_ADMIN_EMAILS = "Admin@Example.com, OWNER@example.com "

        assert settings.super_admin_emails_list == ["admin@example.com", "owner@example.com"]

    def test_allowed_extensions_list(self):
        settings = Settings(SECRET_KEY="x" * 32, ANTHROPIC_API_KEY="test-key")
        settings.ALLOWED_BRIEF_EXTENSIONS = ".txt, .md, .docx"

        assert settings.allowed_extensions_list == [".txt", ".md", ".docx"]

    def test_validate_secret_key_rejects_weak_values(self):
        with pytest.raises(ValueError):
            Settings.validate_secret_key("change-me")

    def test_validate_secret_key_rejects_placeholder_values(self):
        with pytest.raises(ValueError):
            Settings.validate_secret_key("replace-with-your-secret")

    def test_validate_secret_key_accepts_strong_value(self):
        assert Settings.validate_secret_key("x" * 32) == "x" * 32


class TestCreditPricing:
    def test_get_costs(self):
        assert get_content_cost("blog_post") == CONTENT_COSTS["blog_post"]
        assert get_content_cost("missing") == 0
        assert (
            get_research_tool_cost("platform_strategy") == RESEARCH_TOOL_COSTS["platform_strategy"]
        )
        assert get_research_tool_cost("missing") == 0

    def test_calculate_project_cost_breakdown(self):
        result = calculate_project_cost(
            num_blog_posts=3,
            research_tools=["platform_strategy", "missing", "content_calendar"],
        )

        assert result["blog_posts"]["count"] == 3
        assert result["blog_posts"]["credits_per_post"] == 20
        assert result["blog_posts"]["total"] == 60
        assert result["research_tools"]["breakdown"] == {
            "platform_strategy": 150,
            "content_calendar": 150,
        }
        assert result["research_tools"]["total"] == 300
        assert result["total_credits"] == 360
        assert result["estimated_cost"]["standard_rate"] == 360 * STANDARD_PACKAGE_RATE
        assert result["estimated_cost"]["additional_rate"] == 360 * ADDITIONAL_CREDIT_RATE

    def test_pricing_constants(self):
        assert MIN_RESEARCH_TOOL_CREDITS == 50
        assert MAX_OPERATION_CREDITS == 200
