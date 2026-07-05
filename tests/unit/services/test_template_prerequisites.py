"""Unit tests for template_prerequisites service."""

from backend.services.template_prerequisites import (
    RiskLevel,
    check_client_field,
    check_template_prerequisites,
    TEMPLATE_PREREQUISITES,
    TEMPLATE_IDS,
)


class TestCheckClientField:
    def test_none_returns_false(self):
        assert check_client_field({"f": None}, "f") is False

    def test_missing_key_returns_false(self):
        assert check_client_field({}, "f") is False

    def test_empty_str_returns_false(self):
        assert check_client_field({"f": ""}, "f") is False

    def test_whitespace_returns_false(self):
        assert check_client_field({"f": "   "}, "f") is False

    def test_nonempty_str_returns_true(self):
        assert check_client_field({"f": "v"}, "f") is True

    def test_empty_list_returns_false(self):
        assert check_client_field({"f": []}, "f") is False

    def test_nonempty_list_returns_true(self):
        assert check_client_field({"f": ["x"]}, "f") is True

    def test_zero_returns_false(self):
        assert check_client_field({"f": 0}, "f") is False

    def test_truthy_int_returns_true(self):
        assert check_client_field({"f": 1}, "f") is True


class TestUnknownTemplate:
    def test_unknown_returns_can_generate(self):
        r = check_template_prerequisites("nonexistent", {})
        assert r["can_generate"] is True
        assert r["should_block"] is False
        assert r["risk_level"] == RiskLevel.LOW


class TestPersonalStory:
    def test_blocked_when_fields_missing(self):
        r = check_template_prerequisites("personal_story", {})
        assert r["should_block"] is True
        assert r["can_generate"] is False
        assert r["risk_level"] == RiskLevel.CRITICAL
        assert "business_description" in r["missing_required_fields"]
        assert "error_message" in r

    def test_can_generate_with_required_fields(self):
        r = check_template_prerequisites("personal_story", {"business_description": "desc"})
        assert r["can_generate"] is True
        assert r["missing_required_fields"] == []


class TestThingsIGotWrong:
    def test_blocked_when_empty(self):
        r = check_template_prerequisites("things_i_got_wrong", {})
        assert r["should_block"] is True
        assert r["risk_level"] == RiskLevel.CRITICAL

    def test_can_generate_with_business_description(self):
        r = check_template_prerequisites("things_i_got_wrong", {"business_description": "10 yrs"})
        assert r["can_generate"] is True
        assert r["missing_required_fields"] == []


class TestInsideLook:
    def test_blocked_without_description(self):
        assert check_template_prerequisites("inside_look", {})["should_block"] is True

    def test_ok_with_description(self):
        r = check_template_prerequisites("inside_look", {"business_description": "desc"})
        assert r["can_generate"] is True


class TestMilestone:
    def test_blocked_without_description(self):
        assert check_template_prerequisites("milestone", {})["should_block"] is True

    def test_ok_with_description(self):
        r = check_template_prerequisites("milestone", {"business_description": "1M ARR"})
        assert r["can_generate"] is True


class TestStatisticInsight:
    def test_not_blocked_when_fields_missing(self):
        r = check_template_prerequisites("statistic_insight", {})
        assert r["should_block"] is False
        assert r["risk_level"] == RiskLevel.HIGH

    def test_warning_present(self):
        assert "warning_message" in check_template_prerequisites("statistic_insight", {})

    def test_missing_required_tracked(self):
        r = check_template_prerequisites("statistic_insight", {})
        assert "industry" in r["missing_required_fields"]
        assert "business_description" in r["missing_required_fields"]

    def test_clean_when_all_present(self):
        r = check_template_prerequisites(
            "statistic_insight", {"industry": "x", "business_description": "y"}
        )
        assert r["missing_required_fields"] == []


class TestFutureThinking:
    def test_high_risk_not_blocked(self):
        r = check_template_prerequisites("future_thinking", {})
        assert r["risk_level"] == RiskLevel.HIGH
        assert r["can_generate"] is True


class TestProblemRecognition:
    def test_low_risk_not_blocked(self):
        r = check_template_prerequisites("problem_recognition", {})
        assert r["risk_level"] == RiskLevel.LOW
        assert r["should_block"] is False

    def test_missing_required_tracked(self):
        r = check_template_prerequisites("problem_recognition", {})
        assert "customer_pain_points" in r["missing_required_fields"]
        assert "ideal_customer" in r["missing_required_fields"]

    def test_missing_recommended_tracked(self):
        r = check_template_prerequisites(
            "problem_recognition", {"customer_pain_points": "x", "ideal_customer": "y"}
        )
        assert r["missing_recommended_fields"] == ["industry"]

    def test_all_fields_clean(self):
        r = check_template_prerequisites(
            "problem_recognition",
            {"customer_pain_points": "x", "ideal_customer": "y", "industry": "z"},
        )
        assert r["missing_required_fields"] == []
        assert r["missing_recommended_fields"] == []


class TestHowTo:
    def test_requires_two_fields(self):
        r = check_template_prerequisites("how_to", {})
        assert "business_description" in r["missing_required_fields"]
        assert "main_problem_solved" in r["missing_required_fields"]


class TestReaderQuestion:
    def test_requires_customer_questions(self):
        r = check_template_prerequisites("reader_question", {})
        assert "customer_questions" in r["missing_required_fields"]


class TestResearchTools:
    def test_personal_story_recommends_story_mining(self):
        r = check_template_prerequisites("personal_story", {"business_description": "d"})
        assert "story_mining" in r["missing_research_tools"]

    def test_comparison_recommends_competitive(self):
        r = check_template_prerequisites("comparison", {"industry": "x"})
        assert "competitive_analysis" in r["missing_research_tools"]

    def test_milestone_no_research_tools(self):
        r = check_template_prerequisites("milestone", {"business_description": "d"})
        assert r["missing_research_tools"] == []


class TestTemplateIdMapping:
    def test_15_templates_mapped(self):
        assert len(TEMPLATE_IDS) == 15

    def test_ids_1_to_15(self):
        assert set(TEMPLATE_IDS.keys()) == set(range(1, 16))

    def test_prereq_names_in_id_map(self):
        valid = set(TEMPLATE_IDS.values())
        for name in TEMPLATE_PREREQUISITES:
            assert name in valid
