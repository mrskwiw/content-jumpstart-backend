"""Tests for template rules module

Comprehensive tests for the expanded template rules configuration including:
- ClientType enum validation
- TEMPLATE_PREFERENCES mapping
- CLIENT_TYPE_KEYWORDS mapping
- POSTING_FREQUENCY mapping
- PRIMARY_PLATFORMS mapping
- PRICING_TIER_RECOMMENDATIONS mapping
"""

from src.config.template_rules import (
    CLIENT_TYPE_KEYWORDS,
    POSTING_FREQUENCY,
    PRICING_TIER_RECOMMENDATIONS,
    PRIMARY_PLATFORMS,
    TEMPLATE_PREFERENCES,
    ClientType,
)
from src.models.template import TemplateType


class TestClientTypeEnum:
    """Tests for ClientType enum"""

    def test_all_original_types_exist(self):
        """Test that all original 4 client types exist"""
        assert ClientType.B2B_SAAS.value == "b2b_saas"
        assert ClientType.AGENCY.value == "agency"
        assert ClientType.COACH_CONSULTANT.value == "coach_consultant"
        assert ClientType.CREATOR_FOUNDER.value == "creator_founder"

    def test_phase1_types_exist(self):
        """Test that Phase 1 (high priority) client types exist"""
        assert ClientType.REAL_ESTATE.value == "real_estate"
        assert ClientType.RESTAURANT_HOSPITALITY.value == "restaurant_hospitality"
        assert ClientType.ECOMMERCE_RETAIL.value == "ecommerce_retail"

    def test_phase2_types_exist(self):
        """Test that Phase 2 (medium priority) client types exist"""
        assert ClientType.HEALTHCARE.value == "healthcare"
        assert ClientType.NONPROFIT.value == "nonprofit"
        assert ClientType.LEGAL.value == "legal"

    def test_phase3_types_exist(self):
        """Test that Phase 3 (lower priority) client types exist"""
        assert ClientType.FINANCIAL_SERVICES.value == "financial_services"
        assert ClientType.HOME_SERVICES.value == "home_services"
        assert ClientType.EDUCATION.value == "education"

    def test_unknown_type_exists(self):
        """Test that UNKNOWN fallback type exists"""
        assert ClientType.UNKNOWN.value == "unknown"

    def test_total_client_types(self):
        """Test that there are exactly 14 client types"""
        all_types = list(ClientType)
        assert len(all_types) == 14

    def test_all_values_are_strings(self):
        """Test that all enum values are strings"""
        for client_type in ClientType:
            assert isinstance(client_type.value, str)

    def test_all_values_are_unique(self):
        """Test that all enum values are unique"""
        values = [ct.value for ct in ClientType]
        assert len(values) == len(set(values))


class TestTemplatePreferences:
    """Tests for TEMPLATE_PREFERENCES mapping"""

    def test_all_client_types_have_preferences(self):
        """Test that all client types have template preferences defined"""
        for client_type in ClientType:
            assert client_type in TEMPLATE_PREFERENCES, f"Missing preferences for {client_type}"

    def test_each_preference_has_required_keys(self):
        """Test that each preference dict has 'preferred' and 'avoid' keys"""
        for client_type, prefs in TEMPLATE_PREFERENCES.items():
            assert "preferred" in prefs, f"Missing 'preferred' for {client_type}"
            assert "avoid" in prefs, f"Missing 'avoid' for {client_type}"

    def test_preferred_templates_are_template_types(self):
        """Test that all preferred templates are valid TemplateType values"""
        for client_type, prefs in TEMPLATE_PREFERENCES.items():
            for template in prefs["preferred"]:
                assert isinstance(
                    template, TemplateType
                ), f"Invalid template {template} in preferred for {client_type}"

    def test_avoided_templates_are_template_types(self):
        """Test that all avoided templates are valid TemplateType values"""
        for client_type, prefs in TEMPLATE_PREFERENCES.items():
            for template in prefs["avoid"]:
                assert isinstance(
                    template, TemplateType
                ), f"Invalid template {template} in avoid for {client_type}"

    def test_no_template_both_preferred_and_avoided(self):
        """Test that no template is both preferred and avoided"""
        for client_type, prefs in TEMPLATE_PREFERENCES.items():
            preferred_set = set(prefs["preferred"])
            avoided_set = set(prefs["avoid"])
            overlap = preferred_set & avoided_set
            assert not overlap, f"{client_type} has templates both preferred and avoided: {overlap}"

    def test_each_client_has_at_least_one_preferred(self):
        """Test that each client type has at least one preferred template"""
        for client_type, prefs in TEMPLATE_PREFERENCES.items():
            assert len(prefs["preferred"]) > 0, f"{client_type} has no preferred templates"

    def test_b2b_saas_preferences(self):
        """Test specific B2B SaaS template preferences"""
        prefs = TEMPLATE_PREFERENCES[ClientType.B2B_SAAS]
        assert TemplateType.PROBLEM_RECOGNITION in prefs["preferred"]
        assert TemplateType.HOW_TO in prefs["preferred"]
        assert TemplateType.STORY in prefs["avoid"]

    def test_healthcare_preferences(self):
        """Test specific Healthcare template preferences"""
        prefs = TEMPLATE_PREFERENCES[ClientType.HEALTHCARE]
        assert TemplateType.MYTH_BUSTING in prefs["preferred"]
        assert TemplateType.STORY in prefs["avoid"]  # HIPAA concerns

    def test_unknown_has_default_safe_set(self):
        """Test that UNKNOWN client type has default safe templates"""
        prefs = TEMPLATE_PREFERENCES[ClientType.UNKNOWN]
        assert len(prefs["preferred"]) >= 5
        assert len(prefs["avoid"]) == 0


class TestClientTypeKeywords:
    """Tests for CLIENT_TYPE_KEYWORDS mapping"""

    def test_all_client_types_have_keywords(self):
        """Test that all client types (except UNKNOWN) have keywords"""
        for client_type in ClientType:
            if client_type != ClientType.UNKNOWN:
                # UNKNOWN may not have keywords as it's a fallback
                if client_type in CLIENT_TYPE_KEYWORDS:
                    assert len(CLIENT_TYPE_KEYWORDS[client_type]) > 0

    def test_keywords_have_required_categories(self):
        """Test that keywords have business_description and ideal_customer"""
        for client_type, keywords in CLIENT_TYPE_KEYWORDS.items():
            assert (
                "business_description" in keywords
            ), f"Missing business_description for {client_type}"
            assert "ideal_customer" in keywords, f"Missing ideal_customer for {client_type}"

    def test_keywords_are_lists_of_strings(self):
        """Test that all keywords are lists of strings"""
        for client_type, keywords in CLIENT_TYPE_KEYWORDS.items():
            for category, keyword_list in keywords.items():
                assert isinstance(keyword_list, list), f"{client_type}.{category} is not a list"
                for keyword in keyword_list:
                    assert isinstance(
                        keyword, str
                    ), f"Non-string keyword in {client_type}.{category}: {keyword}"

    def test_keywords_are_lowercase(self):
        """Test that keywords are lowercase for matching"""
        for client_type, keywords in CLIENT_TYPE_KEYWORDS.items():
            for category, keyword_list in keywords.items():
                for keyword in keyword_list:
                    # Keywords should be lowercase for case-insensitive matching
                    assert (
                        keyword == keyword.lower()
                    ), f"Non-lowercase keyword: {keyword} in {client_type}.{category}"

    def test_b2b_saas_keywords(self):
        """Test specific B2B SaaS keywords"""
        keywords = CLIENT_TYPE_KEYWORDS[ClientType.B2B_SAAS]
        assert "saas" in keywords["business_description"]
        assert "software" in keywords["business_description"]
        assert "companies" in keywords["ideal_customer"]

    def test_real_estate_keywords(self):
        """Test specific real estate keywords"""
        keywords = CLIENT_TYPE_KEYWORDS[ClientType.REAL_ESTATE]
        assert "realtor" in keywords["business_description"]
        assert "buyers" in keywords["ideal_customer"]

    def test_restaurant_hospitality_keywords(self):
        """Test specific restaurant/hospitality keywords"""
        keywords = CLIENT_TYPE_KEYWORDS[ClientType.RESTAURANT_HOSPITALITY]
        assert "restaurant" in keywords["business_description"]
        assert "diners" in keywords["ideal_customer"]

    def test_healthcare_keywords(self):
        """Test specific healthcare keywords"""
        keywords = CLIENT_TYPE_KEYWORDS[ClientType.HEALTHCARE]
        assert "medical" in keywords["business_description"]
        assert "patients" in keywords["ideal_customer"]

    def test_nonprofit_keywords(self):
        """Test specific nonprofit keywords"""
        keywords = CLIENT_TYPE_KEYWORDS[ClientType.NONPROFIT]
        assert "nonprofit" in keywords["business_description"]
        assert "donors" in keywords["ideal_customer"]

    def test_each_type_has_multiple_keywords(self):
        """Test that each type has multiple keywords for better classification"""
        for client_type, keywords in CLIENT_TYPE_KEYWORDS.items():
            assert (
                len(keywords["business_description"]) >= 3
            ), f"{client_type} has too few business_description keywords"
            assert (
                len(keywords["ideal_customer"]) >= 3
            ), f"{client_type} has too few ideal_customer keywords"


class TestPostingFrequency:
    """Tests for POSTING_FREQUENCY mapping"""

    def test_all_client_types_have_frequency(self):
        """Test that all client types have posting frequency defined"""
        for client_type in ClientType:
            assert client_type in POSTING_FREQUENCY, f"Missing posting frequency for {client_type}"

    def test_frequencies_are_strings(self):
        """Test that all frequencies are strings"""
        for client_type, frequency in POSTING_FREQUENCY.items():
            assert isinstance(
                frequency, str
            ), f"Non-string frequency for {client_type}: {frequency}"

    def test_frequencies_contain_weekly(self):
        """Test that frequencies mention 'weekly' or 'daily'"""
        for client_type, frequency in POSTING_FREQUENCY.items():
            assert (
                "weekly" in frequency.lower() or "daily" in frequency.lower()
            ), f"Frequency for {client_type} doesn't mention weekly/daily: {frequency}"

    def test_specific_frequencies(self):
        """Test specific posting frequencies"""
        assert "3-4x weekly" in POSTING_FREQUENCY[ClientType.B2B_SAAS]
        assert "daily" in POSTING_FREQUENCY[ClientType.ECOMMERCE_RETAIL].lower()
        assert "2-3x weekly" in POSTING_FREQUENCY[ClientType.LEGAL]


class TestPrimaryPlatforms:
    """Tests for PRIMARY_PLATFORMS mapping"""

    def test_all_client_types_have_platforms(self):
        """Test that all client types have primary platforms defined"""
        for client_type in ClientType:
            assert client_type in PRIMARY_PLATFORMS, f"Missing primary platforms for {client_type}"

    def test_platforms_are_lists(self):
        """Test that all platforms are lists"""
        for client_type, platforms in PRIMARY_PLATFORMS.items():
            assert isinstance(platforms, list), f"Platforms for {client_type} is not a list"

    def test_platforms_are_strings(self):
        """Test that all platform names are strings"""
        for client_type, platforms in PRIMARY_PLATFORMS.items():
            for platform in platforms:
                assert isinstance(
                    platform, str
                ), f"Non-string platform in {client_type}: {platform}"

    def test_each_type_has_at_least_two_platforms(self):
        """Test that each type has at least 2 platforms"""
        for client_type, platforms in PRIMARY_PLATFORMS.items():
            assert len(platforms) >= 2, f"{client_type} has fewer than 2 platforms"

    def test_common_platforms_exist(self):
        """Test that common social platforms appear"""
        all_platforms = set()
        for platforms in PRIMARY_PLATFORMS.values():
            all_platforms.update(platforms)

        expected_platforms = {"LinkedIn", "Facebook", "Instagram", "Twitter"}
        for expected in expected_platforms:
            assert expected in all_platforms, f"Missing common platform: {expected}"

    def test_b2b_saas_platforms(self):
        """Test B2B SaaS has LinkedIn and Twitter"""
        platforms = PRIMARY_PLATFORMS[ClientType.B2B_SAAS]
        assert "LinkedIn" in platforms
        assert "Twitter" in platforms

    def test_restaurant_hospitality_platforms(self):
        """Test restaurant/hospitality has visual platforms"""
        platforms = PRIMARY_PLATFORMS[ClientType.RESTAURANT_HOSPITALITY]
        assert "Instagram" in platforms
        assert "TikTok" in platforms

    def test_healthcare_platforms(self):
        """Test healthcare has appropriate platforms"""
        platforms = PRIMARY_PLATFORMS[ClientType.HEALTHCARE]
        assert "Facebook" in platforms
        assert "LinkedIn" in platforms


class TestPricingTierRecommendations:
    """Tests for PRICING_TIER_RECOMMENDATIONS mapping"""

    def test_all_client_types_have_pricing(self):
        """Test that all client types have pricing recommendations"""
        for client_type in ClientType:
            assert (
                client_type in PRICING_TIER_RECOMMENDATIONS
            ), f"Missing pricing recommendation for {client_type}"

    def test_pricing_are_strings(self):
        """Test that all pricing recommendations are strings"""
        for client_type, pricing in PRICING_TIER_RECOMMENDATIONS.items():
            assert isinstance(pricing, str), f"Non-string pricing for {client_type}: {pricing}"

    def test_pricing_mentions_tiers(self):
        """Test that pricing mentions specific tiers"""
        tier_keywords = ["Starter", "Professional", "Premium"]
        for client_type, pricing in PRICING_TIER_RECOMMENDATIONS.items():
            has_tier = any(tier in pricing for tier in tier_keywords)
            assert has_tier, f"Pricing for {client_type} doesn't mention a tier: {pricing}"

    def test_pricing_includes_amounts(self):
        """Test that pricing includes dollar amounts"""
        for client_type, pricing in PRICING_TIER_RECOMMENDATIONS.items():
            assert "$" in pricing, f"Pricing for {client_type} missing dollar amount: {pricing}"

    def test_specific_pricing_recommendations(self):
        """Test specific pricing recommendations"""
        # B2B SaaS should be Professional or Premium
        assert "Professional" in PRICING_TIER_RECOMMENDATIONS[ClientType.B2B_SAAS]

        # Healthcare and Legal should be Premium (high client value)
        assert "Premium" in PRICING_TIER_RECOMMENDATIONS[ClientType.HEALTHCARE]
        assert "Premium" in PRICING_TIER_RECOMMENDATIONS[ClientType.LEGAL]

        # Home services should be Starter (cost-sensitive)
        assert "Starter" in PRICING_TIER_RECOMMENDATIONS[ClientType.HOME_SERVICES]


class TestCrossConfigurationConsistency:
    """Tests for consistency across all configuration dictionaries"""

    def test_all_configs_have_same_client_types(self):
        """Test that all configs cover the same client types"""
        template_types = set(TEMPLATE_PREFERENCES.keys())
        frequency_types = set(POSTING_FREQUENCY.keys())
        platform_types = set(PRIMARY_PLATFORMS.keys())
        pricing_types = set(PRICING_TIER_RECOMMENDATIONS.keys())
        all_client_types = set(ClientType)

        assert (
            template_types == all_client_types
        ), f"TEMPLATE_PREFERENCES missing: {all_client_types - template_types}"
        assert (
            frequency_types == all_client_types
        ), f"POSTING_FREQUENCY missing: {all_client_types - frequency_types}"
        assert (
            platform_types == all_client_types
        ), f"PRIMARY_PLATFORMS missing: {all_client_types - platform_types}"
        assert (
            pricing_types == all_client_types
        ), f"PRICING_TIER_RECOMMENDATIONS missing: {all_client_types - pricing_types}"

    def test_keywords_cover_most_client_types(self):
        """Test that keywords cover most client types (except UNKNOWN)"""
        keyword_types = set(CLIENT_TYPE_KEYWORDS.keys())

        # Keywords should cover at least the original and phase 1 types
        required_types = {
            ClientType.B2B_SAAS,
            ClientType.AGENCY,
            ClientType.COACH_CONSULTANT,
            ClientType.CREATOR_FOUNDER,
            ClientType.REAL_ESTATE,
            ClientType.RESTAURANT_HOSPITALITY,
            ClientType.ECOMMERCE_RETAIL,
        }

        for required in required_types:
            assert (
                required in keyword_types
            ), f"CLIENT_TYPE_KEYWORDS missing required type: {required}"


class TestBusinessLogicIntegrity:
    """Tests for business logic integrity"""

    def test_legal_avoids_story_for_confidentiality(self):
        """Test that Legal avoids STORY template for confidentiality"""
        prefs = TEMPLATE_PREFERENCES[ClientType.LEGAL]
        assert TemplateType.STORY in prefs["avoid"]

    def test_healthcare_avoids_story_for_hipaa(self):
        """Test that Healthcare avoids STORY template for HIPAA"""
        prefs = TEMPLATE_PREFERENCES[ClientType.HEALTHCARE]
        assert TemplateType.STORY in prefs["avoid"]

    def test_nonprofit_avoids_comparison_and_contrarian(self):
        """Test that Nonprofit avoids competitive-seeming templates"""
        prefs = TEMPLATE_PREFERENCES[ClientType.NONPROFIT]
        assert TemplateType.COMPARISON in prefs["avoid"]
        assert TemplateType.CONTRARIAN in prefs["avoid"]

    def test_real_estate_avoids_contrarian_for_market_predictions(self):
        """Test that Real Estate avoids CONTRARIAN to avoid market predictions"""
        prefs = TEMPLATE_PREFERENCES[ClientType.REAL_ESTATE]
        assert TemplateType.CONTRARIAN in prefs["avoid"]

    def test_visual_industries_have_instagram(self):
        """Test that visual industries include Instagram"""
        visual_types = [
            ClientType.RESTAURANT_HOSPITALITY,
            ClientType.ECOMMERCE_RETAIL,
            ClientType.REAL_ESTATE,
        ]
        for client_type in visual_types:
            assert (
                "Instagram" in PRIMARY_PLATFORMS[client_type]
            ), f"Visual industry {client_type} missing Instagram"

    def test_b2b_types_have_linkedin(self):
        """Test that B2B types include LinkedIn"""
        b2b_types = [
            ClientType.B2B_SAAS,
            ClientType.AGENCY,
            ClientType.LEGAL,
            ClientType.FINANCIAL_SERVICES,
        ]
        for client_type in b2b_types:
            assert (
                "LinkedIn" in PRIMARY_PLATFORMS[client_type]
            ), f"B2B type {client_type} missing LinkedIn"
