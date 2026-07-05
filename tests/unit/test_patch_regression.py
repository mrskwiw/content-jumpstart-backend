"""
Patch Regression Tests — Semi-Formal Reasoning Methodology
===========================================================

Each test group pins one specific code path changed in a recent bug fix.
Every assertion cites the file:line it targets. Execution traces and
counterexample checks are documented inline per the Agentic Code Reasoning
methodology (Ugare & Chandra, 2026).

Coverage:
  Bug #85 — validate_optional_industry truncation  (validation_mixin.py:129-130)
  Bug #86 — "Technology" default industry         (market_trends_research.py:163)
  Bug #87 — set_default_client injection          (web_search.py:383-384)
  Bug #88 — unhashable key_drivers in set.add()   (market_trends_research.py:957-959)
  Bug #89 — credits display label                 (GenerationPanel.tsx — Python-side constant)
  Export  — _platform_display_name mapping        (export_service.py:35-37)
  SEO     — MIN_CONTENT_LENGTH lowered 1500→800   (seo_validator.py:75)
"""

import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Bug #85 — validate_optional_industry: truncate not raise on >200 chars
#
# Execution trace:
#   validation_mixin.py:124 — guard: missing/empty input returns None
#   validation_mixin.py:129 — isinstance(value, str) and len(value) > max_length
#   validation_mixin.py:130 — value = value[:max_length]          ← patch site
#   validation_mixin.py:132 — validator.validate_text(value, ...)
#
# Counterexample check: truncated value is always exactly max_length (200) chars,
# which is ≥ min_length (2), so validate_text will never raise on too-short. Safe.
# ---------------------------------------------------------------------------

from src.research.validation_mixin import CommonValidationMixin
from src.validators.research_input_validator import ResearchInputValidator


class _MixinUnderTest(CommonValidationMixin):
    """Minimal concrete class that exercises CommonValidationMixin."""

    def __init__(self):
        self.validator = ResearchInputValidator(strict_mode=False)


@pytest.fixture()
def mixin():
    return _MixinUnderTest()


class TestValidateOptionalIndustryTruncation:
    """Template 1: Patch Verification — validation_mixin.py:129-130"""

    def test_missing_key_returns_none(self, mixin):
        # validation_mixin.py:124 — "industry" not in inputs → None
        assert mixin.validate_optional_industry({}) is None

    def test_empty_string_returns_none(self, mixin):
        # validation_mixin.py:124 — not inputs["industry"] → None
        assert mixin.validate_optional_industry({"industry": ""}) is None

    def test_normal_short_value_passes_unchanged(self, mixin):
        # Happy path — under 200 chars, no truncation branch taken
        result = mixin.validate_optional_industry({"industry": "Dental"})
        assert result == "Dental"

    def test_exactly_200_chars_passes_without_truncation(self, mixin):
        # Boundary: len == max_length → truncation condition is False
        value = "A" * 200
        result = mixin.validate_optional_industry({"industry": value})
        assert result is not None
        assert len(result) <= 200

    def test_201_chars_truncated_to_200(self, mixin):
        # Boundary+1: patch fires at validation_mixin.py:130
        value = "B" * 201
        result = mixin.validate_optional_industry({"industry": value})
        assert result is not None
        assert len(result) <= 200

    def test_222_chars_truncated_not_raised(self, mixin):
        # Actual bug reproduction: a 222-char business_description fed into industry field
        # Pre-patch: raised ValueError("industry too long: maximum 200 characters, got 222")
        # Post-patch: returns truncated string
        business_desc_as_industry = "C" * 222
        assert len(business_desc_as_industry) == 222  # confirm test input is correct
        result = mixin.validate_optional_industry({"industry": business_desc_as_industry})
        assert result is not None
        assert len(result) <= 200

    def test_truncation_does_not_produce_too_short_value(self, mixin):
        # Counterexample guard: truncating a >200-char string always yields exactly
        # 200 chars, which is ≥ min_length (2). validate_text must not raise.
        long_value = "X" * 500
        result = mixin.validate_optional_industry({"industry": long_value})
        assert result is not None
        assert len(result) >= 2


# ---------------------------------------------------------------------------
# Bug #86 — "Technology" hardcoded fallback replaced with "General business"
#
# Execution trace:
#   market_trends_research.py:162 — if not industry:
#   market_trends_research.py:163 — industry = inputs.get("industry_from_db") or "General business"
#
# Counterexample check: "General business" is longer than "Technology" so no
# length validator would reject it. The string is used only in Claude prompts,
# not validated further. Safe.
# ---------------------------------------------------------------------------


class TestIndustryFallbackNotTechnology:
    """Template 1: Patch Verification — market_trends_research.py:163"""

    def test_general_business_is_the_fallback(self):
        # Read the source directly to verify the string literal was changed.
        import inspect
        from src.research.market_trends_research import MarketTrendsResearcher

        source = inspect.getsource(MarketTrendsResearcher.run_analysis)
        assert (
            '"Technology"' not in source
        ), 'Hardcoded "Technology" fallback found in run_analysis — Bug #86 regression'
        assert '"General business"' in source

    def test_determine_competitors_fallback_not_technology(self):
        import inspect
        from src.research.determine_competitors import CompetitorDeterminer

        source = inspect.getsource(CompetitorDeterminer.run_analysis)
        assert (
            '"Technology"' not in source
        ), 'Hardcoded "Technology" fallback found in determine_competitors — Bug #86 regression'
        assert '"General business"' in source


# ---------------------------------------------------------------------------
# Bug #87 — set_default_client injects DB-configured client into global singleton
#
# Execution trace:
#   web_search.py:383-384 — set_default_client writes to module-level _default_client
#   web_search.py:396-399 — get_search_client() reads _default_client:
#       if _default_client is None → False (injected) → returns injected client
#       if provider and provider != _default_client.provider → only if explicit provider arg
#
# Counterexample check: calling get_search_client(provider="brave") after injecting
# a tavily client would re-create (provider mismatch). That is intentional and safe —
# explicit provider always wins.
# ---------------------------------------------------------------------------


class TestSetDefaultClientInjection:
    """Template 1: Patch Verification — web_search.py:373-384"""

    def setup_method(self):
        # Reset global state before each test to ensure isolation
        import src.utils.web_search as ws

        ws._default_client = None

    def teardown_method(self):
        import src.utils.web_search as ws

        ws._default_client = None

    def test_set_default_client_is_returned_by_get_search_client(self):
        # web_search.py:383 — _default_client = client
        # web_search.py:398 — _default_client is None → False → returns it
        from src.utils.web_search import WebSearchClient, set_default_client, get_search_client

        injected = WebSearchClient(provider="stub")
        set_default_client(injected)
        result = get_search_client()
        assert result is injected

    def test_injected_tavily_client_survives_multiple_get_calls(self):
        # Verify the global persists across calls — no re-initialisation
        from src.utils.web_search import WebSearchClient, set_default_client, get_search_client

        injected = WebSearchClient(provider="stub")
        injected.provider = "tavily"  # simulate a configured client
        set_default_client(injected)
        assert get_search_client() is injected
        assert get_search_client() is injected  # second call returns same object

    def test_explicit_provider_arg_overrides_injected_client(self):
        # Counterexample path: get_search_client(provider=X) where X != injected.provider
        # web_search.py:398: `if _default_client is None or (provider and provider != _default_client.provider)`
        # → True → creates new client with requested provider
        from src.utils.web_search import WebSearchClient, set_default_client, get_search_client

        injected = WebSearchClient(provider="stub")
        injected.provider = "tavily"
        set_default_client(injected)
        result = get_search_client(provider="stub")
        # A new client was created — not the injected one
        assert result is not injected
        assert result.provider == "stub"

    def test_set_default_client_to_none_causes_env_fallback(self, monkeypatch):
        # Resetting to None forces get_search_client to re-check env vars
        import src.utils.web_search as ws
        from src.utils.web_search import set_default_client, get_search_client

        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        set_default_client(None)
        result = get_search_client()
        assert result.provider == "stub"  # no env vars → stub


# ---------------------------------------------------------------------------
# Bug #88 — _extract_key_themes: dict key_drivers no longer raise TypeError
#
# Execution trace:
#   market_trends_research.py:955 — for driver in trend.key_drivers[:1]
#   market_trends_research.py:957 — driver_str = driver if isinstance(driver, str) else str(driver)
#   market_trends_research.py:958 — if len(driver_str) > 10
#   market_trends_research.py:959 — themes.add(driver_str)   ← always a str now
#
# Pre-patch: set.add({"text": "AI adoption"}) → TypeError: unhashable type: 'dict'
# Post-patch: str({"text": "AI adoption"}) → hashable string, no exception
#
# Counterexample check: str(dict) produces an ugly string like "{'text': 'AI...'}",
# which is > 10 chars and would appear in themes. Cosmetically impure but not a crash.
# Tests verify no TypeError is raised and output is bounded to 7 themes.
# ---------------------------------------------------------------------------


class TestExtractKeyThemes:
    """Template 2: Fault Localization — market_trends_research.py:941-965"""

    @pytest.fixture()
    def researcher(self):
        from src.research.market_trends_research import MarketTrendsResearcher

        return MarketTrendsResearcher(project_id="test-project")

    def _make_trend(self, key_drivers):
        """Build a Trend bypassing Pydantic validation to inject arbitrary key_drivers."""
        from src.models.market_trends_models import Trend, TrendMomentum, TrendRelevance

        return Trend.model_construct(
            topic="Test trend",
            description="A test trend",
            momentum=TrendMomentum.RISING,
            relevance=TrendRelevance.HIGH,
            popularity_score=8.0,
            growth_rate="+30% YoY",
            key_drivers=key_drivers,
            target_audience=[],
            related_keywords=[],
            content_angles=[],
            urgency="Medium",
        )

    def _make_category(self, trends):
        from src.models.market_trends_models import TrendCategory, TrendMomentum

        return TrendCategory.model_construct(
            category_name="Test Category",
            description="A test category",
            trends=trends,
            category_momentum=TrendMomentum.RISING,
        )

    def _make_conversation(self, topic="Discussion topic that is long enough"):
        from src.models.market_trends_models import EmergingConversation

        return EmergingConversation.model_construct(
            topic=topic,
            description="A test conversation",
            key_perspectives=[],
            thought_leaders=[],
            content_opportunity="Write about it",
        )

    def test_string_drivers_work_normally(self, researcher):
        # Happy path — all drivers are strings
        trend = self._make_trend(["Artificial intelligence adoption in healthcare"])
        category = self._make_category([trend])
        result = researcher._extract_key_themes([category], [])
        assert isinstance(result, list)
        assert all(isinstance(t, str) for t in result)

    def test_dict_drivers_do_not_raise_typeerror(self, researcher):
        # Bug #88 reproduction: key_drivers contains dicts not strings
        # Pre-patch: TypeError: unhashable type: 'dict'
        trend = self._make_trend([{"driver": "AI adoption trends in the industry"}])
        category = self._make_category([trend])
        # Must not raise TypeError
        result = researcher._extract_key_themes([category], [])
        assert isinstance(result, list)

    def test_mixed_string_and_dict_drivers_handled(self, researcher):
        # Mixed list — both types coexist
        trend = self._make_trend(
            [
                "A long enough string driver for testing",
                {"key": "Another driver as a dict object"},
            ]
        )
        category = self._make_category([trend])
        result = researcher._extract_key_themes([category], [])
        assert isinstance(result, list)
        assert all(isinstance(t, str) for t in result)

    def test_short_drivers_are_skipped(self, researcher):
        # market_trends_research.py:958 — len > 10 guard
        trend = self._make_trend(["Short"])  # 5 chars — skipped
        category = self._make_category([trend])
        result = researcher._extract_key_themes([category], [])
        # Only category_name should appear (from the themes.add(category.category_name) branch)
        assert "Short" not in result

    def test_result_capped_at_seven_themes(self, researcher):
        # market_trends_research.py:965 — return list(themes)[:7]
        categories = [
            self._make_category([self._make_trend([f"Driver number {i} is long enough"])])
            for i in range(10)
        ]
        # Override category names to be unique
        for i, cat in enumerate(categories):
            cat.category_name = f"Unique Category Name {i}"
        convs = [
            self._make_conversation(f"Conversation topic number {i} long enough") for i in range(5)
        ]
        result = researcher._extract_key_themes(categories, convs)
        assert len(result) <= 7

    def test_empty_inputs_return_empty_list(self, researcher):
        result = researcher._extract_key_themes([], [])
        assert result == []


# ---------------------------------------------------------------------------
# Export service — _platform_display_name maps "generic" → "Blog"
#
# Execution trace:
#   export_service.py:37 — _PLATFORM_DISPLAY_NAMES.get((raw or "").lower(), raw or "")
#   - "generic".lower() = "generic" → key exists → "Blog"
#   - "GENERIC".lower() = "generic" → key exists → "Blog"  (case-insensitive)
#   - "unknown".lower() → key missing → fallback returns "unknown" unchanged
#   - None or "" → (raw or "") = "" → .lower() = "" → key missing → returns ""
#
# Counterexample check: any string not in the dict is returned as-is (not empty,
# not None). The "or raw" fallback ensures this.
# ---------------------------------------------------------------------------


class TestPlatformDisplayName:
    """Template 1: Patch Verification — export_service.py:35-37"""

    @pytest.fixture(autouse=True)
    def import_helper(self):
        from backend.services.export_service import _platform_display_name

        self.fn = _platform_display_name

    def test_generic_maps_to_blog(self):
        # Primary bug case: "generic" DB value → human label "Blog"
        assert self.fn("generic") == "Blog"

    def test_blog_maps_to_blog(self):
        assert self.fn("blog") == "Blog"

    def test_linkedin_maps_correctly(self):
        assert self.fn("linkedin") == "LinkedIn"

    def test_facebook_maps_correctly(self):
        assert self.fn("facebook") == "Facebook"

    def test_twitter_maps_correctly(self):
        assert self.fn("twitter") == "Microblog"

    def test_case_insensitive_lookup(self):
        # export_service.py:37 — .lower() applied before lookup
        assert self.fn("GENERIC") == "Blog"
        assert self.fn("LinkedIn") == "LinkedIn"

    def test_unknown_value_returned_unchanged(self):
        # Counterexample: unknown platform falls back to raw value, not empty string
        assert self.fn("tiktok") == "tiktok"

    def test_empty_string_returns_empty_string(self):
        # export_service.py:37 — (raw or "") handles empty input
        assert self.fn("") == ""

    def test_none_coerced_to_empty_string(self):
        # The function signature takes str, but guard (raw or "") handles None-like
        assert self.fn(None) == ""  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SEO Validator — MIN_CONTENT_LENGTH lowered from 1500 → 800
#
# Execution trace:
#   seo_validator.py:75  — MIN_CONTENT_LENGTH: int = 800   ← patch site
#   seo_validator.py:176 — if word_count < self.MIN_CONTENT_LENGTH: → append failure
#
# Counterexample check: lowering the threshold means posts 800–1499 words now pass
# the hard length check but still score below OPTIMAL_CONTENT_LENGTH (1500-2000).
# A post of 799 words still fails. Boundary is exact.
# ---------------------------------------------------------------------------


class TestSEOValidatorMinLength:
    """Template 1: Patch Verification — seo_validator.py:75"""

    def test_min_content_length_constant_is_800(self):
        # Direct assertion on the patched constant — seo_validator.py:75
        from src.validators.seo_validator import SEOValidator

        assert (
            SEOValidator.MIN_CONTENT_LENGTH == 800
        ), "MIN_CONTENT_LENGTH regressed — expected 800 (lowered from 1500 in Bug fix)"

    def test_best_practices_dict_min_content_length_is_800(self):
        # seo_validator.py:84 — BEST_PRACTICES dict kept in sync
        from src.validators.seo_validator import SEOValidator

        assert SEOValidator.BEST_PRACTICES["min_content_length"] == 800

    def test_optimal_content_length_unchanged(self):
        # Verify the optimal range was not accidentally changed
        from src.validators.seo_validator import SEOValidator

        assert SEOValidator.OPTIMAL_CONTENT_LENGTH == (1500, 2000)

    def test_post_at_exactly_800_words_passes_length_check(self):
        # Boundary: 800 words → word_count < MIN_CONTENT_LENGTH is False → no failure
        from src.models.client_brief import Platform
        from src.models.post import Post
        from src.validators.seo_validator import SEOValidator

        content = " ".join(["word"] * 800)
        post = Post(
            template_id=1,
            template_name="Blog Post",
            client_name="Test",
            content=content,
            target_platform=Platform.BLOG,
        )
        validator = SEOValidator()
        report = validator.validate([post])
        # No "too short" issue should appear in the report
        all_issues = " ".join(report["issues"])
        assert "too short" not in all_issues.lower()

    def test_post_at_799_words_fails_length_check(self):
        # Boundary-1: 799 < 800 → still a hard failure
        from src.models.client_brief import Platform
        from src.models.post import Post
        from src.validators.seo_validator import SEOValidator

        content = " ".join(["word"] * 799)
        post = Post(
            template_id=1,
            template_name="Blog Post",
            client_name="Test",
            content=content,
            target_platform=Platform.BLOG,
        )
        validator = SEOValidator()
        report = validator.validate([post])
        all_issues = " ".join(report["issues"])
        assert "too short" in all_issues.lower() or "800" in all_issues

    def test_post_at_1089_words_now_passes_length_check(self):
        # Regression guard: the observed production average (1089 words) was triggering
        # hard QA failures before the fix. Post-fix it must pass the length check.
        from src.models.client_brief import Platform
        from src.models.post import Post
        from src.validators.seo_validator import SEOValidator

        content = " ".join(["word"] * 1089)
        post = Post(
            template_id=1,
            template_name="Blog Post",
            client_name="Test",
            content=content,
            target_platform=Platform.BLOG,
        )
        validator = SEOValidator()
        report = validator.validate([post])
        all_issues = " ".join(report["issues"])
        assert (
            "too short" not in all_issues.lower()
        ), "1089-word post should no longer trigger hard length failure after MIN_CONTENT_LENGTH→800"
