"""
Quick tests for platform-specific quality thresholds in CTAValidator and HeadlineValidator
"""
import pytest

from src.models.client_brief import Platform
from src.models.post import Post
from src.validators.cta_validator import CTAValidator
from src.validators.headline_validator import HeadlineValidator


class TestCTAValidatorPlatform:
    """Test platform-specific CTA variety thresholds"""

    def test_linkedin_uses_40_percent_threshold(self):
        """LinkedIn should use 40% variety threshold"""
        validator = CTAValidator()

        # Create 10 posts, 5 with same CTA (50% - should fail for LinkedIn 40%)
        posts = []
        for i in range(5):
            posts.append(Post(
                content="Content here.\n\nWhat's your take?",
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.LINKEDIN,
            ))
        for i in range(5):
            posts.append(Post(
                content="Different content.\n\nDrop a comment below.",
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.LINKEDIN,
            ))

        result = validator.validate(posts)

        assert result["platform"] == "linkedin"
        assert result["variety_threshold"] == 0.40
        assert result["passed"] is False  # 50% > 40%, should fail

    def test_email_uses_70_percent_threshold(self):
        """Email should use 70% variety threshold (more lenient)"""
        validator = CTAValidator()

        # Create 10 posts, 6 with same CTA (60% - should pass for Email 70%)
        posts = []
        for i in range(6):
            posts.append(Post(
                content="Content.\n\nClick the link below.",
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.EMAIL,
            ))
        for i in range(4):
            posts.append(Post(
                content="Different.\n\nReply with your thoughts.",
                template_id=1,
                template_name="Test",
                client_name="Client",
                target_platform=Platform.EMAIL,
            ))

        result = validator.validate(posts)

        assert result["platform"] == "email"
        assert result["variety_threshold"] == 0.70
        assert result["passed"] is True  # 60% < 70%, should pass


class TestHeadlineValidatorPlatform:
    """Test platform-specific headline engagement element thresholds"""

    def test_blog_uses_3_element_minimum(self):
        """Blog should require 3+ engagement elements"""
        validator = HeadlineValidator()

        # Headline with only 1 element (number)
        posts = [Post(
            content="5 things to know",  # 1 element: number
            template_id=1,
            template_name="Test",
            client_name="Client",
            target_platform=Platform.BLOG,
        )]

        result = validator.validate(posts)

        assert result["platform"] == "blog"
        assert result["min_elements"] == 3
        assert result["passed"] is False  # 1 < 3, should fail

    def test_twitter_uses_1_element_minimum(self):
        """Twitter should only require 1+ engagement element"""
        validator = HeadlineValidator()

        # Same headline with 1 element
        posts = [Post(
            content="5 things to know",  # 1 element: number
            template_id=1,
            template_name="Test",
            client_name="Client",
            target_platform=Platform.TWITTER,
        )]

        result = validator.validate(posts)

        assert result["platform"] == "twitter"
        assert result["min_elements"] == 1
        assert result["passed"] is True  # 1 >= 1, should pass

    def test_linkedin_uses_2_element_minimum(self):
        """LinkedIn should require 2+ engagement elements"""
        validator = HeadlineValidator()

        # Headline with 2 elements (number + question)
        posts = [Post(
            content="3 ways to grow your business?",  # 2 elements: number + question
            template_id=1,
            template_name="Test",
            client_name="Client",
            target_platform=Platform.LINKEDIN,
        )]

        result = validator.validate(posts)

        assert result["platform"] == "linkedin"
        assert result["min_elements"] == 2
        assert result["passed"] is True  # 2 >= 2, should pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
