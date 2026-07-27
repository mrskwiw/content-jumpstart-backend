"""Unit tests for Post model"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from src.models.post import Post
from src.models.client_brief import Platform


class TestPost:
    """Test suite for Post model"""

    @pytest.fixture
    def valid_post_data(self):
        """Valid post data"""
        return {
            "content": "This is a great post about testing. It has multiple sentences. What do you think?",
            "template_id": 5,
            "template_name": "Question Post",
            "variant": 1,
            "client_name": "Test Client",
        }

    def test_post_initialization(self, valid_post_data):
        """Test post can be initialized with valid data"""
        post = Post(**valid_post_data)

        assert post.content == valid_post_data["content"]
        assert post.template_id == 5
        assert post.template_name == "Question Post"
        assert post.variant == 1
        assert post.client_name == "Test Client"
        assert isinstance(post.generated_at, datetime)

    def test_auto_calculate_word_count(self, valid_post_data):
        """Test word count is automatically calculated"""
        post = Post(**valid_post_data)

        # "This is a great post about testing. It has multiple sentences. What do you think?"
        # Expected: 15 words
        assert post.word_count == 15

    def test_auto_calculate_character_count(self, valid_post_data):
        """Test character count is automatically calculated"""
        post = Post(**valid_post_data)

        expected_length = len(valid_post_data["content"])
        assert post.character_count == expected_length

    def test_detect_cta_question_mark(self):
        """Test CTA detection with question mark"""
        post = Post(
            content="What do you think about this?",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        assert post.has_cta is True

    def test_detect_cta_reply(self):
        """Test CTA detection with 'reply'"""
        post = Post(
            content="Reply with your thoughts.",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        assert post.has_cta is True

    def test_detect_cta_comment(self):
        """Test CTA detection with 'comment'"""
        post = Post(
            content="Comment below if you agree.",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        assert post.has_cta is True

    def test_detect_cta_share(self):
        """Test CTA detection with 'share'"""
        post = Post(
            content="Share this with your network.",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        assert post.has_cta is True

    def test_detect_cta_multiple_indicators(self):
        """Test CTA detection with multiple indicators"""
        post = Post(
            content="Click here to learn more and share with your team!",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        assert post.has_cta is True

    def test_detect_cta_case_insensitive(self):
        """Test CTA detection is case insensitive"""
        post = Post(
            content="COMMENT BELOW if you agree!",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        assert post.has_cta is True

    def test_no_cta_detected(self):
        """Test post without CTA returns False"""
        post = Post(
            content="This is just a statement with no call to action.",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        assert post.has_cta is False

    def test_all_cta_indicators(self):
        """Test all CTA indicators are detected"""
        indicators = [
            "?",
            "reply",
            "comment",
            "share",
            "click",
            "book",
            "sign up",
            "download",
            "learn more",
            "contact",
            "dm me",
            "reach out",
        ]

        for indicator in indicators:
            post = Post(
                content=f"This post has {indicator} in it",
                template_id=1,
                template_name="Test",
                client_name="Test",
            )
            assert post.has_cta is True, f"Failed to detect CTA with indicator: {indicator}"

    def test_empty_content_validation(self):
        """Test empty content raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            Post(
                content="",
                template_id=1,
                template_name="Test",
                client_name="Test",
            )

        assert "Post content cannot be empty" in str(exc_info.value)

    def test_whitespace_only_content_validation(self):
        """Test whitespace-only content raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            Post(
                content="   \n\t  ",
                template_id=1,
                template_name="Test",
                client_name="Test",
            )

        assert "Post content cannot be empty" in str(exc_info.value)

    def test_target_platform_optional(self, valid_post_data):
        """Test target_platform is optional"""
        post = Post(**valid_post_data)
        assert post.target_platform is None

    def test_target_platform_linkedin(self, valid_post_data):
        """Test target_platform can be set to LinkedIn"""
        valid_post_data["target_platform"] = Platform.LINKEDIN
        post = Post(**valid_post_data)
        assert post.target_platform == Platform.LINKEDIN

    def test_all_platform_types(self, valid_post_data):
        """Test all platform types can be set"""
        platforms = [
            Platform.LINKEDIN,
            Platform.TWITTER,
            Platform.FACEBOOK,
            Platform.BLOG,
            Platform.EMAIL,
        ]

        for platform in platforms:
            valid_post_data["target_platform"] = platform
            post = Post(**valid_post_data)
            assert post.target_platform == platform

    def test_blog_linking_fields(self, valid_post_data):
        """Test blog linking fields"""
        valid_post_data["related_blog_post_id"] = 5
        valid_post_data["blog_link_placeholder"] = "[BLOG_LINK_1]"
        valid_post_data["blog_title"] = "How to Write Great Content"

        post = Post(**valid_post_data)

        assert post.related_blog_post_id == 5
        assert post.blog_link_placeholder == "[BLOG_LINK_1]"
        assert post.blog_title == "How to Write Great Content"

    def test_blog_linking_fields_optional(self, valid_post_data):
        """Test blog linking fields are optional"""
        post = Post(**valid_post_data)

        assert post.related_blog_post_id is None
        assert post.blog_link_placeholder is None
        assert post.blog_title is None

    def test_needs_review_default_false(self, valid_post_data):
        """Test needs_review defaults to False"""
        post = Post(**valid_post_data)
        assert post.needs_review is False
        assert post.review_reason is None

    def test_flag_for_review(self, valid_post_data):
        """Test flag_for_review method"""
        post = Post(**valid_post_data)
        post.flag_for_review("Too short")

        assert post.needs_review is True
        assert post.review_reason == "Too short"

    def test_flag_for_review_multiple_times(self, valid_post_data):
        """Test flagging for review multiple times updates reason"""
        post = Post(**valid_post_data)
        post.flag_for_review("Too short")
        post.flag_for_review("Hook too generic")

        assert post.needs_review is True
        assert post.review_reason == "Hook too generic"

    def test_to_formatted_string_basic(self, valid_post_data):
        """Test formatted string without metadata"""
        post = Post(**valid_post_data)
        formatted = post.to_formatted_string(include_metadata=False)

        assert valid_post_data["content"] in formatted
        assert "Metadata" not in formatted

    def test_to_formatted_string_with_metadata(self, valid_post_data):
        """Test formatted string with metadata"""
        post = Post(**valid_post_data)
        formatted = post.to_formatted_string(include_metadata=True)

        assert valid_post_data["content"] in formatted
        assert "--- Metadata ---" in formatted
        assert "Template: Question Post (#5, Variant 1)" in formatted
        assert f"Words: {post.word_count}" in formatted
        assert f"Characters: {post.character_count}" in formatted
        assert "Has CTA:" in formatted

    def test_to_formatted_string_with_platform(self, valid_post_data):
        """Test formatted string includes platform when set"""
        valid_post_data["target_platform"] = Platform.TWITTER
        post = Post(**valid_post_data)
        formatted = post.to_formatted_string(include_metadata=True)

        assert "Platform: twitter" in formatted

    def test_to_formatted_string_without_platform(self, valid_post_data):
        """Test formatted string excludes platform when not set"""
        post = Post(**valid_post_data)
        formatted = post.to_formatted_string(include_metadata=True)

        assert "Platform:" not in formatted

    def test_to_formatted_string_with_review_flag(self, valid_post_data):
        """Test formatted string includes review flag"""
        post = Post(**valid_post_data)
        post.flag_for_review("Hook too generic")
        formatted = post.to_formatted_string(include_metadata=True)

        assert "[!] NEEDS REVIEW: Hook too generic" in formatted

    def test_variant_default_value(self):
        """Test variant defaults to 1"""
        post = Post(
            content="Test content",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        assert post.variant == 1

    def test_variant_custom_value(self):
        """Test variant can be set to custom value"""
        post = Post(
            content="Test content",
            template_id=1,
            template_name="Test",
            variant=2,
            client_name="Test",
        )
        assert post.variant == 2

    def test_generated_at_default(self, valid_post_data):
        """Test generated_at defaults to current time"""
        post = Post(**valid_post_data)

        assert isinstance(post.generated_at, datetime)
        time_diff = (datetime.now() - post.generated_at).total_seconds()
        assert time_diff < 60  # Within last minute

    def test_generated_at_custom(self, valid_post_data):
        """Test generated_at can be set to custom datetime"""
        custom_time = datetime(2025, 1, 15, 10, 30, 0)
        valid_post_data["generated_at"] = custom_time
        post = Post(**valid_post_data)

        assert post.generated_at == custom_time

    def test_word_count_single_word(self):
        """Test word count with single word"""
        post = Post(
            content="Hello",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        assert post.word_count == 1

    def test_word_count_multiple_spaces(self):
        """Test word count with multiple spaces"""
        post = Post(
            content="Hello    world    test",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        # split() handles multiple spaces correctly
        assert post.word_count == 3

    def test_word_count_newlines(self):
        """Test word count with newlines"""
        post = Post(
            content="Line 1\nLine 2\nLine 3",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        assert post.word_count == 6

    def test_character_count_empty_after_strip(self):
        """Test character count for content that becomes empty after strip"""
        # This should fail validation, but let's test character counting logic
        with pytest.raises(ValidationError):
            Post(
                content="   ",
                template_id=1,
                template_name="Test",
                client_name="Test",
            )

    def test_character_count_with_special_chars(self):
        """Test character count includes special characters"""
        content = "Hello! @#$% 123 & world?"
        post = Post(
            content=content,
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        assert post.character_count == len(content)

    def test_field_defaults(self, valid_post_data):
        """Test all field defaults are correct"""
        post = Post(**valid_post_data)

        # Defaults from model definition
        assert post.variant == 1
        assert post.word_count > 0  # Auto-calculated
        assert post.character_count > 0  # Auto-calculated
        assert post.has_cta is True  # Auto-detected (has '?')
        assert post.target_platform is None
        assert post.related_blog_post_id is None
        assert post.blog_link_placeholder is None
        assert post.blog_title is None
        assert post.needs_review is False
        assert post.review_reason is None

    def test_model_post_init_called(self):
        """Test model_post_init is called during initialization"""
        post = Post(
            content="Test content with CTA?",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )

        # These should be set by model_post_init
        assert post.word_count == 4
        assert post.character_count == len("Test content with CTA?")
        assert post.has_cta is True

    def test_cta_detection_edge_cases(self):
        """Test CTA detection edge cases"""
        # Question mark in middle of sentence
        post1 = Post(
            content="Is this a question? Yes it is.",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        assert post1.has_cta is True

        # 'share' as part of another word — word-boundary check: not a CTA
        post2 = Post(
            content="We shareholder value.",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        assert post2.has_cta is False  # 'shareholder' is not a CTA

        # Multiple CTA indicators
        post3 = Post(
            content="Comment below and share your thoughts? DM me!",
            template_id=1,
            template_name="Test",
            client_name="Test",
        )
        assert post3.has_cta is True

    def test_template_id_range(self):
        """Test various template IDs (1-15 expected)"""
        for template_id in range(1, 16):
            post = Post(
                content="Test content",
                template_id=template_id,
                template_name=f"Template {template_id}",
                client_name="Test",
            )
            assert post.template_id == template_id

    def test_long_content(self):
        """Test post with very long content"""
        long_content = "word " * 1000  # 1000 words
        post = Post(
            content=long_content,
            template_id=1,
            template_name="Test",
            client_name="Test",
        )

        assert post.word_count == 1000
        assert post.character_count == len(long_content)


class TestRecomputeLength:
    """recompute_length() after content is mutated (e.g. hashtags appended post-QA)."""

    def _post(self, content: str) -> Post:
        return Post(content=content, template_id=1, template_name="T", client_name="C")

    def test_counts_reflect_actual_full_content(self):
        """word_count/character_count measure the ACTUAL content, incl. any tags
        (the field's meaning across the codebase — Decision #198). Regeneration
        diagnostics that must ignore tags do so in PostRegenerator, not here."""
        post = self._post("A concise body sentence here.")
        post.content = post.content + "\n\n#Alpha #Beta"
        post.recompute_length()
        assert post.word_count == len(post.content.split())  # includes the tags
        assert post.character_count == len(post.content)

    def test_char_count_reflects_full_mutated_content(self):
        post = self._post("Short.")
        post.content = "Short. #Tag"
        post.recompute_length()
        assert post.character_count == len("Short. #Tag")
        assert post.word_count == 2
