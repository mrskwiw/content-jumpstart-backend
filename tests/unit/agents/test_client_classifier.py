"""Tests for Client Classifier Agent"""

from src.agents.client_classifier import ClientClassifier
from src.config.template_rules import ClientType
from src.models.client_brief import ClientBrief


class TestClientClassifierInit:
    """Test ClientClassifier initialization"""

    def test_init_creates_classifier(self):
        """Test creating a classifier instance"""
        classifier = ClientClassifier()
        assert classifier is not None


class TestClassifyClient:
    """Test classify_client method"""

    def test_classify_b2b_saas(self):
        """Test classifying B2B SaaS client"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="TechCo",
            business_description="We build SaaS software platforms for enterprise teams and organizations",
            ideal_customer="CTOs and VPs at B2B companies",
            main_problem_solved="API integration and technology solutions",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.B2B_SAAS
        assert confidence > 0.15  # Above threshold

    def test_classify_agency(self):
        """Test classifying agency client"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Creative Agency",
            business_description="Marketing agency providing creative services and campaign strategy",
            ideal_customer="Brands and companies needing marketing support",
            main_problem_solved="Creative marketing campaigns for clients",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.AGENCY
        assert confidence > 0.15

    def test_classify_coach_consultant(self):
        """Test classifying coach/consultant client"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Success Coach",
            business_description="Business coach providing consulting and mentoring to transform professionals",
            ideal_customer="Entrepreneurs and executives seeking guidance",
            main_problem_solved="Leadership training and advisor services",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.COACH_CONSULTANT
        assert confidence > 0.15

    def test_classify_creator_founder(self):
        """Test classifying creator/founder client"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Startup Founder",
            business_description="Indie hacker building a bootstrapped startup",
            ideal_customer="Followers and community members",
            main_problem_solved="Launched solopreneur platform for creators",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.CREATOR_FOUNDER
        assert confidence > 0.15

    def test_classify_real_estate(self):
        """Test classifying real estate client"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Real Estate Pro",
            business_description="Real estate broker specializing in residential properties and commercial listings",
            ideal_customer="Home buyers, sellers, and investors",
            main_problem_solved="Finding the perfect homes for families",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.REAL_ESTATE
        assert confidence > 0.15

    def test_classify_restaurant_hospitality(self):
        """Test classifying restaurant/hospitality client"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Fine Dining",
            business_description="Upscale restaurant offering fine cuisine and exceptional hospitality",
            ideal_customer="Food lovers and diners seeking quality dining experiences",
            main_problem_solved="Providing memorable dining and catering services",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.RESTAURANT_HOSPITALITY
        assert confidence > 0.15

    def test_classify_ecommerce_retail(self):
        """Test classifying e-commerce/retail client"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Fashion Boutique",
            business_description="Online store selling fashion clothing and accessories",
            ideal_customer="Fashion lovers and online shoppers",
            main_problem_solved="Curated products for modern retail consumers",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.ECOMMERCE_RETAIL
        assert confidence > 0.15

    def test_classify_healthcare(self):
        """Test classifying healthcare client"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Health Clinic",
            business_description="Medical clinic providing healthcare services and patient care",
            ideal_customer="Patients and families in the community",
            main_problem_solved="Quality wellness and doctor services",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.HEALTHCARE
        assert confidence > 0.15

    def test_classify_nonprofit(self):
        """Test classifying nonprofit client"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Community Foundation",
            business_description="Nonprofit charity organization supporting community causes and social impact",
            ideal_customer="Donors and volunteers passionate about advocacy",
            main_problem_solved="Advancing our mission to help communities",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.NONPROFIT
        assert confidence > 0.15

    def test_classify_legal(self):
        """Test classifying legal client"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Law Firm",
            business_description="Legal practice providing attorney services and litigation counsel",
            ideal_customer="Clients and businesses needing legal representation",
            main_problem_solved="Expert legal advocacy for individuals and companies",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.LEGAL
        assert confidence > 0.15

    def test_classify_financial_services(self):
        """Test classifying financial services client"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Wealth Advisors",
            business_description="Financial advisor providing investment and retirement planning",
            ideal_customer="Investors, retirees, and high-net-worth families",
            main_problem_solved="Tax planning and wealth management for entrepreneurs",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.FINANCIAL_SERVICES
        assert confidence > 0.15

    def test_classify_home_services(self):
        """Test classifying home services client"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Home Improvement Co",
            business_description="Contractor specializing in home improvement, renovation and remodeling",
            ideal_customer="Homeowners and property owners",
            main_problem_solved="Quality construction and HVAC services for families",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.HOME_SERVICES
        assert confidence > 0.15

    def test_classify_education(self):
        """Test classifying education client"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Online Academy",
            business_description="Education platform offering online courses and training for learning",
            ideal_customer="Students and professionals seeking career development",
            main_problem_solved="Quality university-level education for learners",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.EDUCATION
        assert confidence > 0.15

    def test_classify_unknown_low_confidence(self):
        """Test classifying as UNKNOWN when confidence is too low"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Mystery Business",
            business_description="We do various things",
            ideal_customer="People who need help",
            main_problem_solved="General solutions",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.UNKNOWN
        assert confidence < 0.15  # Below threshold

    def test_classify_unknown_no_keywords(self):
        """Test classifying as UNKNOWN when no keywords match"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Unique Business",
            business_description="Completely novel industry with no standard keywords",
            ideal_customer="Special segment not in database",
            main_problem_solved="Unique problem nobody else has",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.UNKNOWN

    def test_classify_handles_empty_fields(self):
        """Test classification with minimal/empty fields"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Test Co",
            business_description="",
            ideal_customer="",
            main_problem_solved="",
        )

        client_type, confidence = classifier.classify_client(brief)

        # Should not crash, should return UNKNOWN
        assert client_type == ClientType.UNKNOWN
        assert confidence == 0.0

    def test_classify_case_insensitive(self):
        """Test that classification is case-insensitive"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="TECH CO",
            business_description="SAAS PLATFORM FOR ENTERPRISE COMPANIES",
            ideal_customer="CTO AND VP OF TECHNOLOGY",
            main_problem_solved="SOFTWARE SOLUTIONS FOR B2B TEAMS",
        )

        client_type, confidence = classifier.classify_client(brief)

        assert client_type == ClientType.B2B_SAAS
        assert confidence > 0.15

    def test_confidence_score_increases_with_more_keywords(self):
        """Test that confidence increases with more keyword matches"""
        classifier = ClientClassifier()

        # Brief with few keywords
        brief_low = ClientBrief(
            company_name="Tech Startup",
            business_description="Software platform",
            ideal_customer="Companies",
            main_problem_solved="Technology",
        )

        # Brief with many keywords
        brief_high = ClientBrief(
            company_name="Enterprise SaaS",
            business_description="SaaS software platform with API and B2B tool for enterprise organizations",
            ideal_customer="CTOs, CEOs, VPs, and directors at companies and businesses",
            main_problem_solved="Enterprise technology solutions for teams",
        )

        _, confidence_low = classifier.classify_client(brief_low)
        _, confidence_high = classifier.classify_client(brief_high)

        # Higher keyword density should yield higher confidence
        assert confidence_high > confidence_low

    def test_classify_mixed_keywords(self):
        """Test classification when brief contains keywords from multiple types"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Hybrid Business",
            business_description="SaaS platform for coaches providing consulting services",
            ideal_customer="Professionals and businesses needing coaching software",
            main_problem_solved="Technology solutions for coaching consultants",
        )

        client_type, confidence = classifier.classify_client(brief)

        # Should pick the type with highest score (likely B2B_SAAS or COACH_CONSULTANT)
        assert client_type in [ClientType.B2B_SAAS, ClientType.COACH_CONSULTANT]
        assert confidence > 0.15


class TestGetClassificationReasoning:
    """Test get_classification_reasoning method"""

    def test_reasoning_for_b2b_saas(self):
        """Test reasoning generation for B2B SaaS"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="TechCo",
            business_description="SaaS platform for enterprise teams"
            + " x" * 100,  # Long description
            ideal_customer="CTOs at companies" + " y" * 100,  # Long customer description
            main_problem_solved="Technology solutions",
        )

        reasoning = classifier.get_classification_reasoning(brief, ClientType.B2B_SAAS, 0.85)

        assert "B2B Saas" in reasoning
        assert "85" in reasoning  # Confidence percentage
        assert "Business:" in reasoning
        assert "Customer:" in reasoning
        assert "SaaS platform" in reasoning[:200]  # Should include truncated description

    def test_reasoning_for_unknown(self):
        """Test reasoning generation for UNKNOWN type"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Mystery Co",
            business_description="Various services",
            ideal_customer="People",
            main_problem_solved="General problems",
        )

        reasoning = classifier.get_classification_reasoning(brief, ClientType.UNKNOWN, 0.05)

        assert "Unknown" in reasoning
        assert "uncertain" in reasoning.lower()
        assert "default safe template" in reasoning.lower()

    def test_reasoning_includes_confidence(self):
        """Test that reasoning includes confidence score"""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Agency Co",
            business_description="Marketing agency",
            ideal_customer="Brands",
            main_problem_solved="Creative campaigns",
        )

        reasoning = classifier.get_classification_reasoning(brief, ClientType.AGENCY, 0.67)

        # Should show confidence as percentage (67%)
        assert "67" in reasoning or "67.0" in reasoning

    def test_reasoning_truncates_long_descriptions(self):
        """Test that reasoning truncates very long descriptions"""
        classifier = ClientClassifier()
        long_desc = "A" * 200  # Very long description
        brief = ClientBrief(
            company_name="Test Co",
            business_description=long_desc,
            ideal_customer="B" * 200,
            main_problem_solved="Test problem",
        )

        reasoning = classifier.get_classification_reasoning(brief, ClientType.B2B_SAAS, 0.75)

        # Should truncate to 100 chars + "..."
        assert "Business:" in reasoning
        assert "..." in reasoning
        # Full 200-char string shouldn't appear
        assert long_desc not in reasoning


# ---------------------------------------------------------------------------
# Additional coverage tests — appended to existing suite
# ---------------------------------------------------------------------------


class TestClassifyClientStrongSignals:
    """Test strong individual signal groups drive correct classification."""

    def test_strong_b2b_saas_signal_saas_keyword(self):
        """Multiple B2B_SAAS keywords together exceed the 15% threshold."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="SaasApp",
            business_description="saas software platform solution for businesses and companies",
            ideal_customer="teams and organizations",
            main_problem_solved="workflow automation",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.B2B_SAAS
        assert confidence > 0.15

    def test_strong_b2b_saas_signal_enterprise_keyword(self):
        """'enterprise' keyword alone is sufficient for B2B_SAAS above threshold."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="EnterpriseCo",
            business_description="enterprise solution for large organizations",
            ideal_customer="cto",
            main_problem_solved="scalability",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.B2B_SAAS
        assert confidence > 0.15

    def test_strong_b2b_saas_signal_api_keyword(self):
        """'api' keyword contributes to B2B_SAAS classification."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="ApiCo",
            business_description="api platform software for businesses",
            ideal_customer="companies and organizations",
            main_problem_solved="integration",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.B2B_SAAS
        assert confidence > 0.15

    def test_strong_agency_signal_agency_keyword(self):
        """'agency' keyword drives AGENCY classification."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="AgencyCo",
            business_description="full-service agency delivering campaigns and strategy",
            ideal_customer="brands and clients",
            main_problem_solved="creative output",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.AGENCY
        assert confidence > 0.15

    def test_strong_agency_signal_consulting_clients(self):
        """'consulting' + 'clients' drive AGENCY classification."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="ConsultingFirm",
            business_description="consulting services for clients with creative marketing campaigns",
            ideal_customer="businesses and brands",
            main_problem_solved="strategy",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.AGENCY
        assert confidence > 0.15

    def test_strong_coach_consultant_signal_coach_keyword(self):
        """'coach' keyword drives COACH_CONSULTANT classification."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="LifeCoach",
            business_description="coach helping people transform through coaching",
            ideal_customer="professionals and executives",
            main_problem_solved="personal growth",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.COACH_CONSULTANT
        assert confidence > 0.15

    def test_strong_coach_consultant_signal_mentoring_keyword(self):
        """'mentoring' keyword drives COACH_CONSULTANT classification."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="MentorPro",
            business_description="mentoring and advisor training programs for leaders",
            ideal_customer="entrepreneurs and individuals",
            main_problem_solved="career development",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.COACH_CONSULTANT
        assert confidence > 0.15

    def test_strong_creator_founder_signal_creator_keyword(self):
        """'creator' keyword drives CREATOR_FOUNDER classification."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="CreatorCo",
            business_description="content creator building an audience",
            ideal_customer="followers and community subscribers",
            main_problem_solved="engagement",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.CREATOR_FOUNDER
        assert confidence > 0.15

    def test_strong_creator_founder_signal_founder_bootstrapped(self):
        """'founder' + 'bootstrapped' signals drive CREATOR_FOUNDER."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="FounderVenture",
            business_description="founder running a bootstrapped startup building from scratch",
            ideal_customer="audience and fans",
            main_problem_solved="product-market fit",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.CREATOR_FOUNDER
        assert confidence > 0.15

    def test_strong_creator_founder_signal_solopreneur(self):
        """'solopreneur' keyword is a strong CREATOR_FOUNDER signal."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="SoloPro",
            business_description="solopreneur indie hacker building products",
            ideal_customer="community and followers",
            main_problem_solved="passive income",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.CREATOR_FOUNDER
        assert confidence > 0.15


class TestClassifyClientAmbiguousAndEdgeCases:
    """Cover ambiguous input, conflicting signals, and edge cases."""

    def test_conflicting_b2b_saas_and_coach_signals_returns_one_type(self):
        """Brief with both B2B_SAAS and COACH terms must resolve to one type."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Hybrid",
            business_description="saas platform for coaching and consultant training software",
            ideal_customer="companies and professionals",
            main_problem_solved="coach management software solution",
        )
        client_type, confidence = classifier.classify_client(brief)
        # Must be a definitive classification, not UNKNOWN
        assert client_type in [ClientType.B2B_SAAS, ClientType.COACH_CONSULTANT]
        assert confidence > 0.15

    def test_conflicting_agency_and_b2b_saas_signals(self):
        """Agency + SaaS keywords: winner has more matched keywords."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="AgencySaaS",
            business_description="marketing agency using saas software platform tools for clients",
            ideal_customer="businesses and brands",
            main_problem_solved="agency campaigns",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type in [ClientType.AGENCY, ClientType.B2B_SAAS]
        assert confidence > 0.15

    def test_empty_business_description_returns_unknown(self):
        """Completely empty description → UNKNOWN."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="EmptyCo",
            business_description="",
            ideal_customer="",
            main_problem_solved="",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.UNKNOWN
        assert confidence == 0.0

    def test_single_word_description_below_threshold(self):
        """A single irrelevant word should stay below the 15% threshold."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Vague",
            business_description="misc",
            ideal_customer="everyone",
            main_problem_solved="stuff",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.UNKNOWN
        assert confidence < 0.15

    def test_returns_tuple_of_client_type_and_float(self):
        """Return type is always (ClientType, float)."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="AnyBiz",
            business_description="software saas platform",
            ideal_customer="companies",
            main_problem_solved="automation",
        )
        result = classifier.classify_client(brief)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], ClientType)
        assert isinstance(result[1], float)

    def test_confidence_is_between_zero_and_one(self):
        """Confidence score is always in [0.0, 1.0]."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="MaxKeywords",
            business_description=(
                "saas software platform api b2b enterprise tool solution technology"
            ),
            ideal_customer="companies businesses teams organizations cto ceo vp director",
            main_problem_solved="automation",
        )
        _, confidence = classifier.classify_client(brief)
        assert 0.0 <= confidence <= 1.0

    def test_no_scores_dict_returns_unknown(self):
        """When CLIENT_TYPE_KEYWORDS is empty scores dict would be empty → UNKNOWN."""
        from unittest.mock import patch

        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Test",
            business_description="saas software",
            ideal_customer="companies",
            main_problem_solved="automation",
        )
        with patch("src.agents.client_classifier.CLIENT_TYPE_KEYWORDS", {}):
            client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.UNKNOWN
        assert confidence == 0.0

    def test_subscription_keyword_contributes_to_b2b_saas(self):
        """'subscription' is not directly in keywords but 'solution'/'software' are."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="SubSaaS",
            business_description="subscription-based software solution for b2b teams",
            ideal_customer="businesses and organizations",
            main_problem_solved="recurring revenue",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.B2B_SAAS
        assert confidence > 0.15

    def test_personal_brand_and_course_drive_creator_founder(self):
        """'course' is not a direct keyword but 'creator'+'founder' dominate."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="CourseCreator",
            business_description="creator and founder building a course for personal brand",
            ideal_customer="audience followers and community",
            main_problem_solved="online education revenue",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.CREATOR_FOUNDER
        assert confidence > 0.15

    def test_influencer_related_brief_maps_to_creator_founder(self):
        """Influencer-style brief (solopreneur/creator signals) → CREATOR_FOUNDER."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="Influencer",
            business_description="solopreneur building creator brand launched online",
            ideal_customer="fans and subscribers",
            main_problem_solved="sponsorship revenue",
        )
        client_type, confidence = classifier.classify_client(brief)
        assert client_type == ClientType.CREATOR_FOUNDER
        assert confidence > 0.15


class TestGetClassificationReasoningEdgeCases:
    """Additional coverage for get_classification_reasoning."""

    def test_reasoning_for_coach_consultant(self):
        """Reasoning for COACH_CONSULTANT includes correct type name."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="CoachCo",
            business_description="coaching and mentoring consultants",
            ideal_customer="professionals",
            main_problem_solved="leadership",
        )
        reasoning = classifier.get_classification_reasoning(
            brief, ClientType.COACH_CONSULTANT, 0.50
        )
        assert "Coach Consultant" in reasoning
        assert "50" in reasoning

    def test_reasoning_for_creator_founder(self):
        """Reasoning for CREATOR_FOUNDER includes correct type name."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="FounderCo",
            business_description="startup founder building a bootstrapped product",
            ideal_customer="community followers",
            main_problem_solved="growth",
        )
        reasoning = classifier.get_classification_reasoning(brief, ClientType.CREATOR_FOUNDER, 0.40)
        assert "Creator Founder" in reasoning
        assert "40" in reasoning

    def test_reasoning_zero_confidence_unknown(self):
        """Zero-confidence UNKNOWN includes advisory text."""
        classifier = ClientClassifier()
        brief = ClientBrief(
            company_name="ZeroCo",
            business_description="",
            ideal_customer="",
            main_problem_solved="",
        )
        reasoning = classifier.get_classification_reasoning(brief, ClientType.UNKNOWN, 0.0)
        assert "Unknown" in reasoning
        assert "0.0%" in reasoning or "0%" in reasoning
        assert "uncertain" in reasoning.lower()

    def test_reasoning_description_exactly_100_chars_no_ellipsis_in_middle(self):
        """Description exactly 100 chars long should still show '...' appended."""
        classifier = ClientClassifier()
        desc_100 = "X" * 100
        brief = ClientBrief(
            company_name="ExactCo",
            business_description=desc_100,
            ideal_customer="Y" * 100,
            main_problem_solved="problem",
        )
        reasoning = classifier.get_classification_reasoning(brief, ClientType.B2B_SAAS, 0.60)
        assert "..." in reasoning
