"""
Unit tests for Post model Platform enum integration

Tests verify that:
1. Post accepts Platform enum values
2. Post accepts string values (auto-converted to enum)
3. Post serialization works correctly
4. Invalid platforms raise validation errors
5. None/optional platforms work correctly
"""
import pytest
from pydantic import ValidationError

from src.models.client_brief import Platform
from src.models.post import Post


class TestPostPlatformEnum:
    """Test Platform enum integration in Post model"""

    def test_post_creation_with_platform_enum(self):
        """Test creating post with Platform enum"""
        post = Post(
            content="Test post content",
            template_id=1,
            template_name="Test Template",
            variant=1,
            client_name="Test Client",
            target_platform=Platform.LINKEDIN,
        )

        assert post.target_platform == Platform.LINKEDIN
        assert isinstance(post.target_platform, Platform)

    def test_post_creation_with_all_platforms(self):
        """Test creating posts with all platform enum values"""
        platforms = [
            Platform.LINKEDIN,
            Platform.TWITTER,
            Platform.FACEBOOK,
            Platform.BLOG,
            Platform.EMAIL,
            Platform.MULTI,
        ]

        for platform in platforms:
            post = Post(
                content=f"Test post for {platform.value}",
                template_id=1,
                template_name="Test Template",
                variant=1,
                client_name="Test Client",
                target_platform=platform,
            )
            assert post.target_platform == platform
            assert isinstance(post.target_platform, Platform)

    def test_post_creation_with_string_platform(self):
        """Test creating post with string platform (should auto-convert)"""
        post = Post(
            content="Test post content",
            template_id=1,
            template_name="Test Template",
            variant=1,
            client_name="Test Client",
            target_platform="linkedin",
        )

        # Pydantic should auto-convert string to enum
        assert post.target_platform == Platform.LINKEDIN
        assert isinstance(post.target_platform, Platform)

    def test_post_creation_with_case_insensitive_string(self):
        """Test creating post with case-insensitive platform string"""
        test_cases = [
            ("LINKEDIN", Platform.LINKEDIN),
            ("LiNkEdIn", Platform.LINKEDIN),
            ("twitter", Platform.TWITTER),
            ("TWITTER", Platform.TWITTER),
        ]

        for string_value, expected_enum in test_cases:
            post = Post(
                content="Test post content",
                template_id=1,
                template_name="Test Template",
                variant=1,
                client_name="Test Client",
                target_platform=string_value,
            )
            assert post.target_platform == expected_enum

    def test_post_creation_with_none_platform(self):
        """Test creating post with None platform (optional field)"""
        post = Post(
            content="Test post content",
            template_id=1,
            template_name="Test Template",
            variant=1,
            client_name="Test Client",
            target_platform=None,
        )

        assert post.target_platform is None

    def test_post_creation_without_platform(self):
        """Test creating post without platform parameter (should be None)"""
        post = Post(
            content="Test post content",
            template_id=1,
            template_name="Test Template",
            variant=1,
            client_name="Test Client",
        )

        assert post.target_platform is None

    def test_post_creation_with_invalid_platform_string(self):
        """Test creating post with invalid platform string raises error"""
        with pytest.raises(ValidationError) as exc_info:
            Post(
                content="Test post content",
                template_id=1,
                template_name="Test Template",
                variant=1,
                client_name="Test Client",
                target_platform="invalid_platform",
            )

        # Verify error mentions the invalid value
        error = exc_info.value
        assert "target_platform" in str(error)

    def test_post_serialization_to_dict(self):
        """Test post serialization converts enum to string value"""
        post = Post(
            content="Test post content",
            template_id=1,
            template_name="Test Template",
            variant=1,
            client_name="Test Client",
            target_platform=Platform.TWITTER,
        )

        post_dict = post.model_dump()

        # Enum should be serialized to string value
        assert post_dict["target_platform"] == "twitter"
        assert isinstance(post_dict["target_platform"], str)

    def test_post_serialization_to_json(self):
        """Test post JSON serialization converts enum to string"""
        post = Post(
            content="Test post content",
            template_id=1,
            template_name="Test Template",
            variant=1,
            client_name="Test Client",
            target_platform=Platform.BLOG,
        )

        json_str = post.model_dump_json()

        # JSON should contain string value, not enum
        assert '"target_platform":"blog"' in json_str or '"target_platform": "blog"' in json_str

    def test_post_formatted_string_with_platform(self):
        """Test formatted string output includes platform value"""
        post = Post(
            content="Test post content",
            template_id=1,
            template_name="Test Template",
            variant=1,
            client_name="Test Client",
            target_platform=Platform.FACEBOOK,
        )

        formatted = post.to_formatted_string(include_metadata=True)

        # Should display platform value (not enum object)
        assert "Platform: facebook" in formatted

    def test_post_formatted_string_without_platform(self):
        """Test formatted string output when platform is None"""
        post = Post(
            content="Test post content",
            template_id=1,
            template_name="Test Template",
            variant=1,
            client_name="Test Client",
            target_platform=None,
        )

        formatted = post.to_formatted_string(include_metadata=True)

        # Platform line should not appear
        assert "Platform:" not in formatted

    def test_post_copy_with_platform(self):
        """Test copying post preserves platform enum"""
        original = Post(
            content="Original content",
            template_id=1,
            template_name="Test Template",
            variant=1,
            client_name="Test Client",
            target_platform=Platform.EMAIL,
        )

        # Create copy with updated content
        copy = original.model_copy(update={"content": "Updated content"})

        assert copy.target_platform == Platform.EMAIL
        assert isinstance(copy.target_platform, Platform)
        assert copy.content == "Updated content"

    def test_backend_schema_default_platform(self):
        """Test backend PostBase schema has correct default"""
        from backend.schemas.post import PostBase

        # Create without platform - should default to LINKEDIN
        post_schema = PostBase(content="Test content")

        assert post_schema.target_platform == Platform.LINKEDIN
        assert isinstance(post_schema.target_platform, Platform)

    def test_backend_schema_with_platform_enum(self):
        """Test backend PostBase accepts Platform enum"""
        from backend.schemas.post import PostBase

        post_schema = PostBase(
            content="Test content",
            target_platform=Platform.TWITTER,
        )

        assert post_schema.target_platform == Platform.TWITTER

    def test_backend_schema_with_platform_string(self):
        """Test backend PostBase accepts platform string"""
        from backend.schemas.post import PostBase

        post_schema = PostBase(
            content="Test content",
            target_platform="blog",
        )

        assert post_schema.target_platform == Platform.BLOG
        assert isinstance(post_schema.target_platform, Platform)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
