"""
Unit tests for Platform enum.

Tests platform enumeration including:
- All platform values
- Case-insensitive lookup
- Invalid platform handling
- Platform value validation
"""

from src.models.client_brief import Platform


class TestPlatformEnum:
    """Test Platform enum functionality"""

    def test_all_platforms_defined(self):
        """Test all expected platforms are defined"""
        expected_platforms = [
            "linkedin",
            "twitter",
            "facebook",
            "blog",
            "email",
            "generic",
        ]

        for platform_name in expected_platforms:
            # Should be able to access each platform
            platform = Platform[platform_name.upper()]
            assert platform.value == platform_name

    def test_platform_values(self):
        """Test platform enum values are correct"""
        assert Platform.LINKEDIN.value == "linkedin"
        assert Platform.TWITTER.value == "twitter"
        assert Platform.FACEBOOK.value == "facebook"
        assert Platform.BLOG.value == "blog"
        assert Platform.EMAIL.value == "email"
        assert Platform.GENERIC.value == "generic"

    def test_case_insensitive_lookup(self):
        """Test _missing_ method handles case-insensitive lookup"""
        # Lowercase
        assert Platform._missing_("linkedin") == Platform.LINKEDIN
        assert Platform._missing_("twitter") == Platform.TWITTER

        # Uppercase
        assert Platform._missing_("LINKEDIN") == Platform.LINKEDIN
        assert Platform._missing_("TWITTER") == Platform.TWITTER

        # Mixed case
        assert Platform._missing_("LinkedIn") == Platform.LINKEDIN
        assert Platform._missing_("Twitter") == Platform.TWITTER

    def test_invalid_platform_returns_none(self):
        """Test invalid platform values return None"""
        assert Platform._missing_("invalid") is None
        assert Platform._missing_("tiktok") is None
        assert Platform._missing_("") is None
        assert Platform._missing_("123") is None

    def test_platform_comparison(self):
        """Test platform enum comparison"""
        assert Platform.LINKEDIN == Platform.LINKEDIN
        assert Platform.LINKEDIN != Platform.TWITTER
        assert Platform.LINKEDIN.value == "linkedin"

    def test_platform_string_representation(self):
        """Test platform converts to string correctly"""
        # str() returns "Platform.LINKEDIN", use .value for lowercase name
        assert Platform.LINKEDIN.value == "linkedin"
        assert Platform.TWITTER.value == "twitter"
        assert Platform.GENERIC.value == "generic"

    def test_social_platforms_group(self):
        """Test social media platforms are defined"""
        social_platforms = [
            Platform.LINKEDIN,
            Platform.TWITTER,
            Platform.FACEBOOK,
        ]

        for platform in social_platforms:
            assert platform.value in [
                "linkedin",
                "twitter",
                "facebook",
            ]

    def test_publishing_platforms_group(self):
        """Test publishing/long-form platforms are defined"""
        publishing_platforms = [
            Platform.BLOG,
            Platform.EMAIL,
        ]

        for platform in publishing_platforms:
            assert platform.value in [
                "blog",
                "email",
            ]

    def test_platform_enumeration(self):
        """Test iterating over all platforms"""
        platforms = list(Platform)
        assert len(platforms) == 6  # linkedin, twitter, facebook, blog, email, generic

        # Check LinkedIn is in the list
        assert Platform.LINKEDIN in platforms
        assert Platform.GENERIC in platforms

    def test_platform_membership(self):
        """Test platform membership checks"""
        assert "linkedin" in [p.value for p in Platform]
        assert "generic" in [p.value for p in Platform]
        assert "tiktok" not in [p.value for p in Platform]
