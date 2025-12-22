"""
Unit tests for platform-specific hook validation in HookValidator

Tests verify that:
1. Platform detection works with both enum and string
2. Platform-specific hook length limits are enforced
3. LinkedIn hooks respect 140 char limit
4. Twitter hooks respect 100 char limit
5. Facebook hooks respect 80 char limit
6. Blog hooks respect 50 word limit
7. Email hooks respect 100 char limit
8. Combined uniqueness + length validation works
"""
import pytest

from src.models.client_brief import Platform
from src.models.post import Post
from src.validators.hook_validator import HookValidator


class TestHookValidatorPlatform:
    """Test platform-specific hook validation"""

    @pytest.fixture
    def validator(self):
        """Create HookValidator instance"""
        return HookValidator()

    def test_detect_platform_with_enum(self, validator):
        """Test platform detection when target_platform is Platform enum"""
        posts = [
            Post(
                content="Test post",
                template_id=1,
                template_name="Test Template",
                client_name="Test Client",
                target_platform=Platform.LINKEDIN,
            )
        ]

        platform = validator._detect_platform(posts)
        assert platform == Platform.LINKEDIN

    def test_detect_platform_with_string(self, validator):
        """Test platform detection when target_platform is string (backward compat)"""
        posts = [
            Post(
                content="Test post",
                template_id=1,
                template_name="Test Template",
                client_name="Test Client",
                target_platform="twitter",
            )
        ]

        platform = validator._detect_platform(posts)
        assert platform == Platform.TWITTER

    def test_detect_platform_none(self, validator):
        """Test platform detection returns None for empty posts"""
        posts = []
        platform = validator._detect_platform(posts)
        assert platform is None

    def test_linkedin_hook_under_140_chars(self, validator):
        """Test LinkedIn hook under 140 chars passes"""
        posts = [
            Post(
                content="This is a short LinkedIn hook that is well under 140 characters.",
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.LINKEDIN,
            )
        ]

        result = validator.validate(posts)

        assert result["platform"] == "linkedin"
        assert len(result["hook_length_issues"]) == 0
        assert "meet linkedin hook length requirements" in result["metric"]

    def test_linkedin_hook_over_140_chars(self, validator):
        """Test LinkedIn hook over 140 chars fails"""
        long_hook = "A" * 150  # 150 characters
        posts = [
            Post(
                content=long_hook,
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.LINKEDIN,
            )
        ]

        result = validator.validate(posts)

        assert result["platform"] == "linkedin"
        assert len(result["hook_length_issues"]) == 1
        assert result["hook_length_issues"][0]["hook_length"] == 150
        assert result["hook_length_issues"][0]["max_allowed"] == 140
        assert result["hook_length_issues"][0]["unit"] == "characters"
        assert result["passed"] is False

    def test_twitter_hook_under_100_chars(self, validator):
        """Test Twitter hook under 100 chars passes"""
        posts = [
            Post(
                content="Short tweet within 100 chars",
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.TWITTER,
            )
        ]

        result = validator.validate(posts)

        assert result["platform"] == "twitter"
        assert len(result["hook_length_issues"]) == 0

    def test_twitter_hook_over_100_chars(self, validator):
        """Test Twitter hook over 100 chars fails"""
        long_hook = "B" * 110  # 110 characters
        posts = [
            Post(
                content=long_hook,
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.TWITTER,
            )
        ]

        result = validator.validate(posts)

        assert result["platform"] == "twitter"
        assert len(result["hook_length_issues"]) == 1
        assert result["hook_length_issues"][0]["hook_length"] == 110
        assert result["hook_length_issues"][0]["max_allowed"] == 100
        assert result["passed"] is False

    def test_facebook_hook_under_80_chars(self, validator):
        """Test Facebook hook under 80 chars passes"""
        posts = [
            Post(
                content="Short Facebook caption",
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.FACEBOOK,
            )
        ]

        result = validator.validate(posts)

        assert result["platform"] == "facebook"
        assert len(result["hook_length_issues"]) == 0

    def test_facebook_hook_over_80_chars(self, validator):
        """Test Facebook hook over 80 chars fails"""
        long_hook = "C" * 90  # 90 characters
        posts = [
            Post(
                content=long_hook,
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.FACEBOOK,
            )
        ]

        result = validator.validate(posts)

        assert result["platform"] == "facebook"
        assert len(result["hook_length_issues"]) == 1
        assert result["hook_length_issues"][0]["hook_length"] == 90
        assert result["hook_length_issues"][0]["max_allowed"] == 80
        assert result["passed"] is False

    def test_blog_hook_under_50_words(self, validator):
        """Test Blog hook under 50 words passes"""
        # 40 words
        hook = " ".join(["word"] * 40)
        posts = [
            Post(
                content=f"{hook}\n\nRest of the blog post content here.",
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.BLOG,
            )
        ]

        result = validator.validate(posts)

        assert result["platform"] == "blog"
        assert len(result["hook_length_issues"]) == 0

    def test_blog_hook_over_50_words(self, validator):
        """Test Blog hook over 50 words fails"""
        # 60 words in first paragraph
        hook = " ".join(["word"] * 60)
        posts = [
            Post(
                content=f"{hook}\n\nRest of the blog post content here.",
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.BLOG,
            )
        ]

        result = validator.validate(posts)

        assert result["platform"] == "blog"
        assert len(result["hook_length_issues"]) == 1
        assert result["hook_length_issues"][0]["hook_length"] == 60
        assert result["hook_length_issues"][0]["max_allowed"] == 50
        assert result["hook_length_issues"][0]["unit"] == "words"
        assert result["passed"] is False

    def test_email_hook_under_100_chars(self, validator):
        """Test Email hook under 100 chars passes"""
        posts = [
            Post(
                content="Short email opening line that hooks the reader.",
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.EMAIL,
            )
        ]

        result = validator.validate(posts)

        assert result["platform"] == "email"
        assert len(result["hook_length_issues"]) == 0

    def test_email_hook_over_100_chars(self, validator):
        """Test Email hook over 100 chars fails"""
        long_hook = "E" * 110  # 110 characters
        posts = [
            Post(
                content=long_hook,
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.EMAIL,
            )
        ]

        result = validator.validate(posts)

        assert result["platform"] == "email"
        assert len(result["hook_length_issues"]) == 1
        assert result["hook_length_issues"][0]["hook_length"] == 110
        assert result["hook_length_issues"][0]["max_allowed"] == 100
        assert result["passed"] is False

    def test_combined_uniqueness_and_length_validation(self, validator):
        """Test validation fails when both uniqueness and length issues exist"""
        posts = [
            Post(
                content="A" * 150,  # Over 140 chars for LinkedIn
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.LINKEDIN,
            ),
            Post(
                content="A" * 150,  # Duplicate AND over limit
                template_id=2,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.LINKEDIN,
            ),
        ]

        result = validator.validate(posts)

        # Should have both uniqueness and length issues
        assert len(result["duplicates"]) > 0  # Hooks are duplicates
        assert len(result["hook_length_issues"]) == 2  # Both over limit
        assert len(result["issues"]) >= 3  # At least 1 duplicate + 2 length issues
        assert result["passed"] is False

    def test_only_uniqueness_issues(self, validator):
        """Test validation fails with only uniqueness issues (hooks OK length)"""
        posts = [
            Post(
                content="Good hook under 140 chars",
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.LINKEDIN,
            ),
            Post(
                content="Good hook under 140 chars",  # Duplicate but good length
                template_id=2,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.LINKEDIN,
            ),
        ]

        result = validator.validate(posts)

        assert len(result["duplicates"]) > 0  # Has duplicates
        assert len(result["hook_length_issues"]) == 0  # No length issues
        assert result["passed"] is False  # Fails due to duplicates

    def test_only_length_issues(self, validator):
        """Test validation fails with only length issues (hooks unique)"""
        posts = [
            Post(
                content="A" * 150,  # Over 140 chars for LinkedIn
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.LINKEDIN,
            ),
            Post(
                content="B" * 150,  # Different but also over limit
                template_id=2,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.LINKEDIN,
            ),
        ]

        result = validator.validate(posts)

        assert len(result["duplicates"]) == 0  # Unique hooks
        assert len(result["hook_length_issues"]) == 2  # Both over limit
        assert result["passed"] is False  # Fails due to length

    def test_all_pass(self, validator):
        """Test validation passes when both uniqueness and length are good"""
        posts = [
            Post(
                content="Starting your product journey with clarity and purpose.",
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.LINKEDIN,
            ),
            Post(
                content="The biggest mistake founders make in year one.",
                template_id=2,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.LINKEDIN,
            ),
        ]

        result = validator.validate(posts)

        assert len(result["duplicates"]) == 0
        assert len(result["hook_length_issues"]) == 0
        assert result["passed"] is True
        assert "2/2 unique hooks" in result["metric"]
        assert "2/2 meet linkedin hook length requirements" in result["metric"]

    def test_no_platform_skips_length_validation(self, validator):
        """Test length validation is skipped when no platform detected"""
        posts = [
            Post(
                content="A" * 200,  # Would fail LinkedIn, but no platform
                template_id=1,
                template_name="Test",
                client_name="Client",
                # No target_platform
            )
        ]

        result = validator.validate(posts)

        assert result["platform"] is None
        assert len(result["hook_length_issues"]) == 0  # Skipped
        assert "unique hooks" in result["metric"]
        assert "hook length requirements" not in result["metric"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
