"""Unit tests for platform strategy quality improvements:
- _derive_resource_level
- _validate_recommendations (self-check step)
"""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _strategist():
    """Return a PlatformStrategist with a mocked Anthropic client."""
    from src.research.platform_strategy import PlatformStrategist

    with patch("src.research.platform_strategy.get_default_client"):
        s = PlatformStrategist.__new__(PlatformStrategist)
        s.client = MagicMock()
        s.project_id = "test-project"
        s.base_output_dir = MagicMock()
        return s


def _make_mix(primary=None, secondary=None, experimental=None, avoid=None):
    from src.models.platform_strategy_models import PlatformMix, PlatformName

    def _names(lst):
        return [PlatformName(n) for n in (lst or [])]

    return PlatformMix(
        primary_platforms=_names(primary or []),
        secondary_platforms=_names(secondary or []),
        experimental_platforms=_names(experimental or []),
        avoid_platforms=_names(avoid or []),
        rationale="test rationale",
    )


def _make_rec(platform, fit_level="essential"):
    from src.models.platform_strategy_models import (
        PlatformRecommendation,
        PlatformName,
        PlatformFit,
        ContentFormat,
    )

    fit_map = {
        "essential": PlatformFit.ESSENTIAL,
        "recommended": PlatformFit.RECOMMENDED,
        "optional": PlatformFit.OPTIONAL,
        "not_recommended": PlatformFit.NOT_RECOMMENDED,
    }
    return PlatformRecommendation(
        platform=PlatformName(platform),
        fit_level=fit_map.get(fit_level, PlatformFit.RECOMMENDED),
        priority="High",
        why_use=["reason"],
        why_not_use=["concern"],
        recommended_formats=[ContentFormat.SHORT_FORM],
        posting_frequency="3x/week",
        content_approach="ORGANIC: educational posts. PAID: Sponsored content.",
        primary_goal="awareness",
        success_metrics=["metric"],
        estimated_effort="Medium",
        expected_roi="High",
    )


# ---------------------------------------------------------------------------
# _derive_resource_level
# ---------------------------------------------------------------------------


class TestDeriveResourceLevel:
    def test_daily_is_high(self):
        s = _strategist()
        result = s._derive_resource_level("daily")
        assert "high" in result.lower()

    def test_every_day_is_high(self):
        s = _strategist()
        assert "high" in s._derive_resource_level("every day").lower()

    def test_7x_is_high(self):
        s = _strategist()
        assert "high" in s._derive_resource_level("7x per week").lower()

    def test_3x_is_medium(self):
        s = _strategist()
        assert "medium" in s._derive_resource_level("3x per week").lower()

    def test_5x_is_medium(self):
        s = _strategist()
        assert "medium" in s._derive_resource_level("5x/week").lower()

    def test_2x_is_low(self):
        s = _strategist()
        assert "low" in s._derive_resource_level("2x per week").lower()

    def test_weekly_is_low(self):
        s = _strategist()
        assert "low" in s._derive_resource_level("weekly").lower()

    def test_once_is_low(self):
        s = _strategist()
        assert "low" in s._derive_resource_level("once a week").lower()

    def test_empty_string_is_unknown(self):
        s = _strategist()
        result = s._derive_resource_level("")
        assert "unknown" in result.lower()

    def test_none_is_unknown(self):
        s = _strategist()
        result = s._derive_resource_level(None)
        assert "unknown" in result.lower()

    def test_returns_string(self):
        s = _strategist()
        assert isinstance(s._derive_resource_level("3x/week"), str)


# ---------------------------------------------------------------------------
# _validate_recommendations — pass-through when LLM says valid
# ---------------------------------------------------------------------------


class TestValidateRecommendationsValid:
    def _run(self, mix, recs, llm_response):
        s = _strategist()
        s.client.create_message.return_value = llm_response
        result_mix, result_recs = s._validate_recommendations(
            s.client,
            business_description="B2B SaaS analytics platform",
            target_audience="Customer success managers, SaaS executives 35-55",
            industry="B2B SaaS",
            tone_preference="professional",
            brand_personality=["authoritative", "helpful"],
            resource_level="medium (3-5 posts/week)",
            platform_mix=mix,
            recommendations=recs,
        )
        return result_mix, result_recs

    def test_returns_original_when_valid(self):
        mix = _make_mix(primary=["linkedin"], secondary=["blog"])
        recs = [_make_rec("linkedin"), _make_rec("blog")]
        response = '{"valid": true, "issues": [], "remove_from_primary": [], "remove_from_secondary": [], "add_to_avoid": []}'
        result_mix, result_recs = self._run(mix, recs, response)
        assert [p.value for p in result_mix.primary_platforms] == ["linkedin"]
        assert [p.value for p in result_mix.secondary_platforms] == ["blog"]

    def test_recommendations_unchanged_when_valid(self):
        mix = _make_mix(primary=["linkedin"])
        recs = [_make_rec("linkedin")]
        response = '{"valid": true, "issues": [], "remove_from_primary": [], "remove_from_secondary": [], "add_to_avoid": []}'
        _, result_recs = self._run(mix, recs, response)
        assert len(result_recs) == 1
        assert result_recs[0].platform.value == "linkedin"

    def test_empty_mix_passes_through_without_api_call(self):
        s = _strategist()
        mix = _make_mix()  # no platforms
        recs = []
        result_mix, result_recs = s._validate_recommendations(
            s.client,
            "desc",
            "audience",
            "B2B SaaS",
            "",
            [],
            "low",
            mix,
            recs,
        )
        s.client.create_message.assert_not_called()
        assert result_mix is mix


# ---------------------------------------------------------------------------
# _validate_recommendations — corrections applied when LLM flags issues
# ---------------------------------------------------------------------------


class TestValidateRecommendationsCorrections:
    def _run(self, mix, recs, llm_response):
        s = _strategist()
        s.client.create_message.return_value = llm_response
        return s._validate_recommendations(
            s.client,
            "B2B SaaS analytics for enterprise",
            "C-suite executives and VP-level buyers, age 40-60",
            "Enterprise B2B SaaS",
            "professional",
            ["authoritative"],
            "low (1-2 posts/week)",
            mix,
            recs,
        )

    def test_removes_flagged_platform_from_primary(self):
        mix = _make_mix(primary=["tiktok", "linkedin"])
        recs = [_make_rec("tiktok"), _make_rec("linkedin")]
        response = '{"valid": false, "issues": ["TikTok mismatch for 40-60 exec audience"], "remove_from_primary": ["tiktok"], "remove_from_secondary": [], "add_to_avoid": []}'
        result_mix, _ = self._run(mix, recs, response)
        primary_names = [p.value for p in result_mix.primary_platforms]
        assert "tiktok" not in primary_names
        assert "linkedin" in primary_names

    def test_removed_platform_not_auto_added_to_avoid(self):
        # Bug #159: removing from primary must NOT implicitly promote to avoid.
        # A platform only lands in avoid when explicitly listed in add_to_avoid.
        mix = _make_mix(primary=["tiktok", "linkedin"])
        recs = [_make_rec("tiktok"), _make_rec("linkedin")]
        response = '{"valid": false, "issues": ["TikTok audience mismatch"], "remove_from_primary": ["tiktok"], "remove_from_secondary": [], "add_to_avoid": []}'
        result_mix, _ = self._run(mix, recs, response)
        avoid_names = [p.value for p in result_mix.avoid_platforms]
        assert "tiktok" not in avoid_names

    def test_explicit_add_to_avoid_respected(self):
        # When add_to_avoid explicitly names a platform it must appear in avoid.
        mix = _make_mix(primary=["tiktok", "linkedin"])
        recs = [_make_rec("tiktok"), _make_rec("linkedin")]
        response = '{"valid": false, "issues": ["TikTok audience mismatch"], "remove_from_primary": ["tiktok"], "remove_from_secondary": [], "add_to_avoid": ["tiktok"]}'
        result_mix, _ = self._run(mix, recs, response)
        avoid_names = [p.value for p in result_mix.avoid_platforms]
        assert "tiktok" in avoid_names

    def test_flagged_recommendation_marked_not_recommended(self):
        from src.models.platform_strategy_models import PlatformFit

        mix = _make_mix(primary=["tiktok", "linkedin"])
        recs = [_make_rec("tiktok", "essential"), _make_rec("linkedin")]
        response = '{"valid": false, "issues": ["TikTok mismatch"], "remove_from_primary": ["tiktok"], "remove_from_secondary": [], "add_to_avoid": []}'
        _, result_recs = self._run(mix, recs, response)
        tiktok_rec = next(r for r in result_recs if r.platform.value == "tiktok")
        assert tiktok_rec.fit_level == PlatformFit.NOT_RECOMMENDED

    def test_remove_from_secondary(self):
        # facebook is a valid PlatformName; use it as the "wrong fit" platform here
        mix = _make_mix(primary=["linkedin"], secondary=["facebook"])
        recs = [_make_rec("linkedin"), _make_rec("facebook")]
        response = '{"valid": false, "issues": ["Facebook weak fit for enterprise B2B"], "remove_from_primary": [], "remove_from_secondary": ["facebook"], "add_to_avoid": []}'
        result_mix, _ = self._run(mix, recs, response)
        secondary_names = [p.value for p in result_mix.secondary_platforms]
        assert "facebook" not in secondary_names

    def test_unflagged_platforms_preserved(self):
        mix = _make_mix(primary=["tiktok", "linkedin"])
        recs = [_make_rec("tiktok"), _make_rec("linkedin")]
        response = '{"valid": false, "issues": ["TikTok mismatch"], "remove_from_primary": ["tiktok"], "remove_from_secondary": [], "add_to_avoid": []}'
        result_mix, _ = self._run(mix, recs, response)
        assert "linkedin" in [p.value for p in result_mix.primary_platforms]


# ---------------------------------------------------------------------------
# _validate_recommendations — error resilience
# ---------------------------------------------------------------------------


class TestValidateRecommendationsErrorHandling:
    def test_returns_original_on_llm_exception(self):
        s = _strategist()
        s.client.create_message.side_effect = Exception("API timeout")
        mix = _make_mix(primary=["linkedin"])
        recs = [_make_rec("linkedin")]
        result_mix, result_recs = s._validate_recommendations(
            s.client,
            "desc",
            "audience",
            "B2B",
            "",
            [],
            "medium",
            mix,
            recs,
        )
        assert result_mix is mix
        assert result_recs is recs

    def test_returns_original_on_malformed_json(self):
        s = _strategist()
        s.client.create_message.return_value = "not json at all"
        mix = _make_mix(primary=["linkedin"])
        recs = [_make_rec("linkedin")]
        result_mix, result_recs = s._validate_recommendations(
            s.client,
            "desc",
            "audience",
            "B2B",
            "",
            [],
            "medium",
            mix,
            recs,
        )
        assert result_mix is mix

    def test_returns_original_when_no_corrections_in_invalid_response(self):
        """valid:false but empty correction lists — nothing to change."""
        s = _strategist()
        s.client.create_message.return_value = '{"valid": false, "issues": ["vague"], "remove_from_primary": [], "remove_from_secondary": [], "add_to_avoid": []}'
        mix = _make_mix(primary=["linkedin"])
        recs = [_make_rec("linkedin")]
        result_mix, result_recs = s._validate_recommendations(
            s.client,
            "desc",
            "audience",
            "B2B",
            "",
            [],
            "medium",
            mix,
            recs,
        )
        assert result_mix is mix


# ---------------------------------------------------------------------------
# audience_behavior deduplication in run_analysis
# ---------------------------------------------------------------------------


class TestAudienceBehaviorDeduplication:
    """
    Regression for the production crash where _map_platform_name collapses
    Instagram / Google Business / blog variants onto the same PlatformName enum
    value, causing the same platform to appear 2-3 times in audience_behavior.
    Without deduplication, _generate_platform_recommendations receives duplicate
    entries, bloating platform_names and behaviors_text and pushing the response
    past max_tokens (truncated JSON -> crash).
    """

    def _make_behavior(self, platform_value: str):
        from src.models.platform_strategy_models import AudienceBehavior, PlatformName

        b = AudienceBehavior(
            platform=PlatformName(platform_value),
            audience_present=True,
            activity_level="high",
            content_consumption_pattern="test pattern",
            engagement_style="test engagement",
            decision_maker_presence="medium",
        )
        return b

    def _dedup(self, behaviors):
        """Mirror the quality-based deduplication logic in run_analysis."""
        _activity_rank = {"extremely high": 4, "high": 3, "medium": 2, "low-medium": 1, "low": 1}
        _best: dict = {}
        for b in behaviors:
            key = b.platform.value
            if key not in _best:
                _best[key] = b
            else:
                cur = _best[key]
                cur_score = int(cur.audience_present) * 10 + _activity_rank.get(
                    cur.activity_level.lower(), 0
                )
                new_score = int(b.audience_present) * 10 + _activity_rank.get(
                    b.activity_level.lower(), 0
                )
                if new_score > cur_score:
                    _best[key] = b
        order = list(dict.fromkeys(b.platform.value for b in behaviors))
        return [_best[k] for k in order]

    def test_single_duplicate_removed(self):
        behaviors = [
            self._make_behavior("blog"),
            self._make_behavior("blog"),
            self._make_behavior("facebook"),
        ]
        result = self._dedup(behaviors)
        assert [b.platform.value for b in result].count("blog") == 1
        assert len(result) == 2

    def test_three_duplicates_collapsed_to_one(self):
        """Reproduces the exact production failure: blog appeared 3x for a dental client."""
        behaviors = [
            self._make_behavior("facebook"),
            self._make_behavior("blog"),
            self._make_behavior("blog"),
            self._make_behavior("youtube"),
            self._make_behavior("email"),
            self._make_behavior("tiktok"),
            self._make_behavior("blog"),
        ]
        result = self._dedup(behaviors)
        values = [b.platform.value for b in result]
        assert values.count("blog") == 1
        assert len(result) == 5  # facebook, blog, youtube, email, tiktok

    def test_highest_activity_kept_not_first(self):
        """Quality-based: low-activity first entry loses to high-activity later entry."""
        b1 = self._make_behavior("blog")
        b1.activity_level = "low"
        b2 = self._make_behavior("blog")
        b2.activity_level = "high"
        result = self._dedup([b1, b2])
        assert result[0].activity_level == "high"

    def test_audience_present_beats_absent_regardless_of_activity(self):
        """audience_present=True always wins over False, even if False has higher activity string."""
        from src.models.platform_strategy_models import AudienceBehavior, PlatformName

        b_absent = AudienceBehavior(
            platform=PlatformName("blog"),
            audience_present=False,
            activity_level="high",
            content_consumption_pattern="x",
            engagement_style="x",
            decision_maker_presence="x",
        )
        b_present = AudienceBehavior(
            platform=PlatformName("blog"),
            audience_present=True,
            activity_level="low",
            content_consumption_pattern="x",
            engagement_style="x",
            decision_maker_presence="x",
        )
        result = self._dedup([b_absent, b_present])
        assert result[0].audience_present is True

    def test_equal_quality_first_occurrence_kept(self):
        """When quality is identical, first entry is preserved."""
        b1 = self._make_behavior("blog")
        b1.activity_level = "high"
        b2 = self._make_behavior("blog")
        b2.activity_level = "high"
        b2.content_consumption_pattern = "different"
        result = self._dedup([b1, b2])
        assert result[0].content_consumption_pattern == "test pattern"

    def test_no_duplicates_unchanged(self):
        behaviors = [
            self._make_behavior("facebook"),
            self._make_behavior("linkedin"),
            self._make_behavior("email"),
        ]
        assert len(self._dedup(behaviors)) == 3

    def test_order_preserved(self):
        behaviors = [
            self._make_behavior("email"),
            self._make_behavior("facebook"),
            self._make_behavior("blog"),
            self._make_behavior("facebook"),  # duplicate
        ]
        result = self._dedup(behaviors)
        assert [b.platform.value for b in result] == ["email", "facebook", "blog"]
