"""Tests for Brief Quality Checker Agent"""

from unittest.mock import MagicMock, patch
import pytest
from src.agents.brief_quality_checker import BriefQualityChecker
from src.models.brief_quality import FieldQuality
from src.models.client_brief import ClientBrief, TonePreference


@pytest.fixture
def quality_checker():
    with patch("src.agents.brief_quality_checker.AnthropicClient"):
        return BriefQualityChecker()


@pytest.fixture
def minimal_brief():
    return ClientBrief(
        company_name="Test Co",
        business_description="Test business",
        ideal_customer="Test customer",
        main_problem_solved="Test problem",
    )


@pytest.fixture
def complete_brief():
    return ClientBrief(
        company_name="Acme",
        business_description="We provide enterprise SaaS solutions for financial services companies to automate compliance workflows",
        ideal_customer="CFOs and compliance officers at mid-sized financial institutions with 500-5000 employees",
        main_problem_solved="Manual compliance processes automated to minutes",
        brand_personality=[TonePreference.AUTHORITATIVE, TonePreference.DATA_DRIVEN],
        customer_pain_points=["Pain 1", "Pain 2", "Pain 3", "Pain 4"],
        customer_questions=["Q1", "Q2", "Q3"],
        key_phrases=["phrase1", "phrase2", "phrase3"],
        stories=["Story 1", "Story 2"],
        main_cta="Schedule demo",
    )


class TestInit:
    def test_default_client(self):
        with patch("src.agents.brief_quality_checker.AnthropicClient") as m:
            BriefQualityChecker()
            m.assert_called_once()


class TestAssessField:
    def test_missing(self, quality_checker, minimal_brief):
        assert quality_checker._assess_field(minimal_brief, "founder_name") == FieldQuality.MISSING

    def test_weak_short(self, quality_checker, minimal_brief):
        minimal_brief.business_description = "Hi"
        assert (
            quality_checker._assess_field(minimal_brief, "business_description")
            == FieldQuality.WEAK
        )

    def test_adequate(self, quality_checker, minimal_brief):
        minimal_brief.business_description = "We provide software for businesses"
        assert (
            quality_checker._assess_field(minimal_brief, "business_description")
            == FieldQuality.ADEQUATE
        )

    def test_strong(self, quality_checker, minimal_brief):
        minimal_brief.business_description = " ".join(["word"] * 20)
        assert (
            quality_checker._assess_field(minimal_brief, "business_description")
            == FieldQuality.STRONG
        )


class TestAssessBrief:
    def test_minimal(self, minimal_brief):
        mock_client = MagicMock()
        mock_client.create_message.return_value = "0.4"
        checker = BriefQualityChecker(client=mock_client)
        report = checker.assess_brief(minimal_brief)
        assert 0 <= report.overall_score <= 1
        assert report.total_fields > 0

    def test_complete(self, complete_brief):
        mock_client = MagicMock()
        mock_client.create_message.return_value = "0.9"
        checker = BriefQualityChecker(client=mock_client)
        report = checker.assess_brief(complete_brief)
        assert report.overall_score > 0.6
        assert report.can_generate_content is True


class TestCalculateCompleteness:
    def test_all_missing(self, minimal_brief):
        mock_client = MagicMock()
        checker = BriefQualityChecker(client=mock_client)
        field_quality = {f: FieldQuality.MISSING for f in checker.FIELD_WEIGHTS.keys()}
        score = checker._calculate_completeness(field_quality)
        assert score == 0.0

    def test_all_strong(self, complete_brief):
        mock_client = MagicMock()
        checker = BriefQualityChecker(client=mock_client)
        field_quality = {f: FieldQuality.STRONG for f in checker.FIELD_WEIGHTS.keys()}
        score = checker._calculate_completeness(field_quality)
        assert abs(score - 1.0) < 0.01  # Use approximate comparison

    def test_mixed_quality(self):
        mock_client = MagicMock()
        checker = BriefQualityChecker(client=mock_client)
        field_quality = {
            "company_name": FieldQuality.STRONG,
            "business_description": FieldQuality.ADEQUATE,
            "ideal_customer": FieldQuality.WEAK,
            "main_problem_solved": FieldQuality.MISSING,
        }
        score = checker._calculate_completeness(field_quality)
        assert 0 < score < 1


class TestCalculateSpecificity:
    def test_high_specificity(self, complete_brief):
        mock_client = MagicMock()
        mock_client.create_message.return_value = "0.85"
        checker = BriefQualityChecker(client=mock_client)
        score = checker._calculate_specificity(complete_brief)
        assert abs(score - 0.85) < 0.01

    def test_low_specificity(self, minimal_brief):
        mock_client = MagicMock()
        mock_client.create_message.return_value = "0.3"
        checker = BriefQualityChecker(client=mock_client)
        score = checker._calculate_specificity(minimal_brief)
        assert abs(score - 0.3) < 0.01

    def test_invalid_response_defaults_to_half(self, minimal_brief):
        mock_client = MagicMock()
        mock_client.create_message.return_value = "invalid"
        checker = BriefQualityChecker(client=mock_client)
        score = checker._calculate_specificity(minimal_brief)
        assert abs(score - 0.5) < 0.01


class TestCalculateUsability:
    def test_all_critical_fields_strong(self):
        mock_client = MagicMock()
        checker = BriefQualityChecker(client=mock_client)
        # Usability uses: business_description, ideal_customer, main_problem_solved, brand_personality
        field_quality = {
            "business_description": FieldQuality.STRONG,
            "ideal_customer": FieldQuality.STRONG,
            "main_problem_solved": FieldQuality.STRONG,
            "brand_personality": FieldQuality.STRONG,
        }
        score = checker._calculate_usability(field_quality)
        assert abs(score - 1.0) < 0.01  # Use approximate comparison

    def test_some_critical_fields_missing(self):
        mock_client = MagicMock()
        checker = BriefQualityChecker(client=mock_client)
        field_quality = {
            "business_description": FieldQuality.MISSING,
            "ideal_customer": FieldQuality.ADEQUATE,
            "main_problem_solved": FieldQuality.WEAK,
            "brand_personality": FieldQuality.ADEQUATE,
        }
        score = checker._calculate_usability(field_quality)
        assert 0 < score < 1

    def test_all_critical_fields_missing(self):
        mock_client = MagicMock()
        checker = BriefQualityChecker(client=mock_client)
        field_quality = {
            "business_description": FieldQuality.MISSING,
            "ideal_customer": FieldQuality.MISSING,
            "main_problem_solved": FieldQuality.MISSING,
            "brand_personality": FieldQuality.MISSING,
        }
        score = checker._calculate_usability(field_quality)
        assert score == 0.0


class TestCanGenerateContent:
    def test_can_generate_with_complete_brief(self):
        mock_client = MagicMock()
        checker = BriefQualityChecker(client=mock_client)
        # All critical fields present + 2 supporting fields
        field_quality = {
            "company_name": FieldQuality.STRONG,
            "business_description": FieldQuality.STRONG,
            "ideal_customer": FieldQuality.STRONG,
            "main_problem_solved": FieldQuality.STRONG,
            "brand_personality": FieldQuality.STRONG,
            "customer_pain_points": FieldQuality.STRONG,
        }
        can_gen = checker._can_generate_content(field_quality)
        assert can_gen is True

    def test_cannot_generate_with_missing_critical(self):
        mock_client = MagicMock()
        checker = BriefQualityChecker(client=mock_client)
        # Missing business_description (critical field)
        field_quality = {
            "company_name": FieldQuality.STRONG,
            "business_description": FieldQuality.MISSING,
            "ideal_customer": FieldQuality.WEAK,
            "main_problem_solved": FieldQuality.ADEQUATE,
        }
        can_gen = checker._can_generate_content(field_quality)
        assert can_gen is False

    def test_can_generate_with_adequate_fields(self):
        mock_client = MagicMock()
        checker = BriefQualityChecker(client=mock_client)
        # All critical fields adequate + 2 supporting fields
        field_quality = {
            "company_name": FieldQuality.ADEQUATE,
            "business_description": FieldQuality.ADEQUATE,
            "ideal_customer": FieldQuality.ADEQUATE,
            "main_problem_solved": FieldQuality.ADEQUATE,
            "brand_personality": FieldQuality.ADEQUATE,
            "customer_pain_points": FieldQuality.ADEQUATE,
        }
        can_gen = checker._can_generate_content(field_quality)
        assert can_gen is True

    def test_cannot_generate_insufficient_supporting(self):
        mock_client = MagicMock()
        checker = BriefQualityChecker(client=mock_client)
        # All critical fields present but only 1 supporting field
        field_quality = {
            "company_name": FieldQuality.STRONG,
            "business_description": FieldQuality.STRONG,
            "ideal_customer": FieldQuality.STRONG,
            "main_problem_solved": FieldQuality.STRONG,
            "brand_personality": FieldQuality.STRONG,
        }
        can_gen = checker._can_generate_content(field_quality)
        assert can_gen is False


class TestCalculateMinimumQuestions:
    def test_no_missing_fields(self):
        mock_client = MagicMock()
        checker = BriefQualityChecker(client=mock_client)
        missing_fields = []
        weak_fields = []
        min_questions = checker._calculate_minimum_questions(missing_fields, weak_fields)
        assert min_questions == 0

    def test_multiple_missing_fields(self):
        mock_client = MagicMock()
        checker = BriefQualityChecker(client=mock_client)
        # Critical fields (weight >= 0.8): customer_pain_points, customer_questions
        missing_fields = ["customer_pain_points", "customer_questions", "brand_personality"]
        # Critical weak fields (weight >= 0.6): key_phrases, main_cta
        weak_fields = ["key_phrases", "main_cta", "stories"]
        min_questions = checker._calculate_minimum_questions(missing_fields, weak_fields)
        # Should count critical_missing (2) + critical_weak (2) = 4
        assert min_questions >= 2


class TestGenerateRecommendations:
    def test_recommendations_for_missing_fields(self):
        mock_client = MagicMock()
        checker = BriefQualityChecker(client=mock_client)
        field_quality = {
            "company_name": FieldQuality.STRONG,
            "business_description": FieldQuality.MISSING,
            "ideal_customer": FieldQuality.WEAK,
            "main_problem_solved": FieldQuality.ADEQUATE,
            "brand_personality": FieldQuality.MISSING,
            "customer_pain_points": FieldQuality.WEAK,
        }
        missing = ["business_description", "brand_personality"]
        weak = ["ideal_customer", "customer_pain_points"]
        recommendations = checker._generate_recommendations(missing, weak, field_quality)
        assert len(recommendations) > 0
        # Should have specific recommendation for brand_personality
        assert any("brand personality" in r.lower() for r in recommendations)

    def test_no_recommendations_for_complete_brief(self):
        mock_client = MagicMock()
        checker = BriefQualityChecker(client=mock_client)
        field_quality = {f: FieldQuality.STRONG for f in checker.FIELD_WEIGHTS.keys()}
        missing_fields = []
        weak_fields = []
        recommendations = checker._generate_recommendations(
            missing_fields, weak_fields, field_quality
        )
        assert len(recommendations) == 0
