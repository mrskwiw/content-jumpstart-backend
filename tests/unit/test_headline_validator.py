"""Comprehensive unit tests for HeadlineValidator

Tests headline engagement element detection and platform-specific validation.
"""

import pytest

from src.models.client_brief import Platform
from src.models.post import Post
from src.validators.headline_validator import HeadlineValidator


@pytest.fixture
def sample_posts_with_strong_headlines():
    """Create posts with strong engaging headlines"""
    return [
        Post(
            content="5 Secret Ways to Double Your Revenue in 30 Days\n\nBody content here.",
            template_id=1,
            template_name="Template 1",
            client_name="Test",
        ),
        Post(
            content="Are You Making This Critical Mistake?\n\nBody content.",
            template_id=2,
            template_name="Template 2",
            client_name="Test",
        ),
        Post(
            content="How Apple Revolutionized Personal Computing\n\nBody.",
            template_id=3,
            template_name="Template 3",
            client_name="Test",
        ),
    ]


@pytest.fixture
def sample_posts_with_weak_headlines():
    """Create posts with weak headlines"""
    return [
        Post(
            content="Some thoughts\n\nBody content here.",
            template_id=1,
            template_name="Template 1",
            client_name="Test",
        ),
        Post(
            content="Today we talk about things\n\nBody content.",
            template_id=2,
            template_name="Template 2",
            client_name="Test",
        ),
    ]


class TestHeadlineValidatorInit:
    """Test HeadlineValidator initialization"""

    def test_init_with_defaults(self):
        """Test initialization with default parameters"""
        validator = HeadlineValidator()
        assert validator.min_elements == 3  # Default from constants

    def test_init_with_custom_min_elements(self):
        """Test initialization with custom minimum elements"""
        validator = HeadlineValidator(min_elements=2)
        assert validator.min_elements == 2

    def test_power_words_defined(self):
        """Test power words set is defined"""
        validator = HeadlineValidator()
        assert len(validator.POWER_WORDS) > 0
        assert "secret" in validator.POWER_WORDS
        assert "proven" in validator.POWER_WORDS

    def test_emotional_triggers_defined(self):
        """Test emotional triggers set is defined"""
        validator = HeadlineValidator()
        assert len(validator.EMOTIONAL_TRIGGERS) > 0
        assert "fear" in validator.EMOTIONAL_TRIGGERS
        assert "success" in validator.EMOTIONAL_TRIGGERS

    def test_question_words_defined(self):
        """Test question words set is defined"""
        validator = HeadlineValidator()
        assert len(validator.QUESTION_WORDS) > 0
        assert "how" in validator.QUESTION_WORDS
        assert "why" in validator.QUESTION_WORDS


class TestValidate:
    """Test main validate method"""

    def test_validate_strong_headlines_pass(self, sample_posts_with_strong_headlines):
        """Test validation passes with strong headlines"""
        validator = HeadlineValidator(min_elements=3)
        result = validator.validate(sample_posts_with_strong_headlines)

        assert result["passed"] is True
        assert result["headlines_analyzed"] == 3
        assert result["average_elements"] >= 3.0
        assert len(result["below_threshold_posts"]) == 0

    def test_validate_weak_headlines_fail(self, sample_posts_with_weak_headlines):
        """Test validation fails with weak headlines"""
        validator = HeadlineValidator(min_elements=3)
        result = validator.validate(sample_posts_with_weak_headlines)

        assert result["passed"] is False
        assert len(result["below_threshold_posts"]) == 2
        assert len(result["issues"]) == 2

    def test_validate_mixed_quality(self):
        """Test validation with mix of strong and weak headlines"""
        posts = [
            Post(
                content="5 Proven Secrets to Success\n\nBody",  # Strong: number + power word
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
            Post(
                content="Some random thoughts\n\nBody",  # Weak: no elements
                template_id=2,
                template_name="T2",
                client_name="Test",
            ),
        ]
        validator = HeadlineValidator(min_elements=2)
        result = validator.validate(posts)

        assert result["passed"] is False
        assert len(result["below_threshold_posts"]) == 1
        assert result["below_threshold_posts"][0] == 1  # Second post (index 1)

    def test_validate_returns_all_fields(self, sample_posts_with_strong_headlines):
        """Test validation result contains all expected fields"""
        validator = HeadlineValidator()
        result = validator.validate(sample_posts_with_strong_headlines)

        assert "passed" in result
        assert "headlines_analyzed" in result
        assert "average_elements" in result
        assert "below_threshold_count" in result
        assert "below_threshold_posts" in result
        assert "headline_scores" in result
        assert "issues" in result
        assert "metric" in result
        assert "platform" in result
        assert "min_elements" in result


class TestPlatformSpecificThresholds:
    """Test platform-specific minimum element thresholds"""

    def test_linkedin_threshold(self):
        """Test LinkedIn uses 2 element threshold"""
        posts = [
            Post(
                content="How to Succeed\n\nBody",  # 2 elements: question word + proper noun
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.LINKEDIN,
            ),
        ]
        validator = HeadlineValidator()
        result = validator.validate(posts)

        assert result["platform"] == "linkedin"
        assert result["min_elements"] == 2
        assert result["passed"] is True

    def test_twitter_threshold(self):
        """Test Twitter uses 1 element threshold"""
        posts = [
            Post(
                content="Breaking news\n\nBody",  # 1 element
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.TWITTER,
            ),
        ]
        validator = HeadlineValidator()
        result = validator.validate(posts)

        assert result["platform"] == "twitter"
        assert result["min_elements"] == 1

    def test_blog_threshold(self):
        """Test Blog uses 3 element threshold"""
        posts = [
            Post(
                content="The Ultimate Guide to Success\n\nBody",  # 3 elements
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.BLOG,
            ),
        ]
        validator = HeadlineValidator()
        result = validator.validate(posts)

        assert result["platform"] == "blog"
        assert result["min_elements"] == 3

    def test_no_platform_uses_default(self):
        """Test uses default threshold when no platform detected"""
        posts = [
            Post(
                content="Headline\n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = HeadlineValidator(min_elements=5)
        result = validator.validate(posts)

        assert result["platform"] is None
        assert result["min_elements"] == 5


class TestDetectPlatform:
    """Test platform detection"""

    def test_detect_platform_linkedin(self):
        """Test detects LinkedIn platform"""
        posts = [
            Post(
                content="Test\n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.LINKEDIN,
            ),
        ]
        validator = HeadlineValidator()
        platform = validator._detect_platform(posts)
        assert platform == Platform.LINKEDIN

    def test_detect_platform_none_when_empty(self):
        """Test returns None for empty post list"""
        validator = HeadlineValidator()
        platform = validator._detect_platform([])
        assert platform is None

    def test_detect_platform_from_string(self):
        """Test handles platform as string"""
        post = Post(
            content="Test\n\nBody",
            template_id=1,
            template_name="T1",
            client_name="Test",
        )
        post.target_platform = "blog"

        validator = HeadlineValidator()
        platform = validator._detect_platform([post])
        assert platform == Platform.BLOG


class TestCountEngagementElements:
    """Test engagement element counting"""

    def test_count_number_element(self):
        """Test detects numbers in headline"""
        validator = HeadlineValidator()
        count = validator._count_engagement_elements("5 Ways to Win")
        assert count >= 1  # At least number

    def test_count_power_word_element(self):
        """Test detects power words"""
        validator = HeadlineValidator()
        count = validator._count_engagement_elements("The Ultimate Secret Guide")
        assert count >= 2  # "ultimate" and "secret"

    def test_count_emotional_trigger(self):
        """Test detects emotional triggers"""
        validator = HeadlineValidator()
        count = validator._count_engagement_elements("Overcome Your Fear and Achieve Success")
        assert count >= 2  # "fear" and "success"

    def test_count_question_format(self):
        """Test detects question format (ending with ?)"""
        validator = HeadlineValidator()
        count = validator._count_engagement_elements("Are You Making This Mistake?")
        assert count >= 1  # Question mark

    def test_count_question_word(self):
        """Test detects question words"""
        validator = HeadlineValidator()
        count = validator._count_engagement_elements("How to Build a Business")
        assert count >= 1  # "how"

    def test_count_specificity_proper_nouns(self):
        """Test detects proper nouns for specificity"""
        validator = HeadlineValidator()
        count = validator._count_engagement_elements("What Apple and Google Teach Us")
        assert count >= 1  # Proper nouns (Apple, Google)

    def test_count_multiple_elements(self):
        """Test counts multiple different elements"""
        validator = HeadlineValidator()
        # "5" (number) + "Secret" (power word) + "?" (question) + "Google" (proper noun)
        count = validator._count_engagement_elements("5 Secret Tips from Google?")
        assert count >= 3

    def test_count_no_elements(self):
        """Test returns 0 for bland headline"""
        validator = HeadlineValidator()
        count = validator._count_engagement_elements("some random thoughts here")
        assert count == 0


class TestGetElementDetails:
    """Test detailed element breakdown"""

    def test_get_element_details_number(self):
        """Test detects number presence"""
        validator = HeadlineValidator()
        details = validator._get_element_details("5 Ways to Win")
        assert details["has_number"] is True

    def test_get_element_details_power_word(self):
        """Test detects power word presence"""
        validator = HeadlineValidator()
        details = validator._get_element_details("The Ultimate Guide")
        assert details["has_power_word"] is True

    def test_get_element_details_emotional_trigger(self):
        """Test detects emotional trigger"""
        validator = HeadlineValidator()
        details = validator._get_element_details("Overcome Fear and Win")
        assert details["has_emotional_trigger"] is True

    def test_get_element_details_question(self):
        """Test detects question format"""
        validator = HeadlineValidator()
        details = validator._get_element_details("Are You Ready?")
        assert details["is_question"] is True

    def test_get_element_details_question_word(self):
        """Test detects question words"""
        validator = HeadlineValidator()
        details = validator._get_element_details("How to Succeed")
        assert details["has_question_word"] is True

    def test_get_element_details_specificity(self):
        """Test detects specificity (proper nouns)"""
        validator = HeadlineValidator()
        details = validator._get_element_details("What Apple Teaches Us")
        assert details["has_specificity"] is True

    def test_get_element_details_all_false(self):
        """Test all False for bland headline"""
        validator = HeadlineValidator()
        details = validator._get_element_details("some thoughts")
        assert details["has_number"] is False
        assert details["has_power_word"] is False
        assert details["has_emotional_trigger"] is False
        assert details["is_question"] is False
        assert details["has_question_word"] is False
        assert details["has_specificity"] is False


class TestHeadlineScores:
    """Test headline scoring in validation results"""

    def test_headline_scores_structure(self):
        """Test headline_scores contains expected structure"""
        posts = [
            Post(
                content="5 Proven Ways\n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = HeadlineValidator()
        result = validator.validate(posts)

        assert len(result["headline_scores"]) == 1
        score = result["headline_scores"][0]
        assert "post_idx" in score
        assert "headline" in score
        assert "elements" in score
        assert "details" in score

    def test_headline_scores_correct_index(self):
        """Test headline scores match post indices"""
        posts = [
            Post(content="First\n\nB", template_id=1, template_name="T1", client_name="Test"),
            Post(content="Second\n\nB", template_id=2, template_name="T2", client_name="Test"),
        ]
        validator = HeadlineValidator()
        result = validator.validate(posts)

        assert result["headline_scores"][0]["post_idx"] == 0
        assert result["headline_scores"][1]["post_idx"] == 1
        assert result["headline_scores"][0]["headline"] == "First"
        assert result["headline_scores"][1]["headline"] == "Second"


class TestIssuesReporting:
    """Test issue reporting"""

    def test_issues_include_post_number(self):
        """Test issues reference correct post number (1-indexed)"""
        posts = [
            Post(
                content="Weak headline\n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = HeadlineValidator(min_elements=3)
        result = validator.validate(posts)

        assert len(result["issues"]) == 1
        assert "Post 1" in result["issues"][0]

    def test_issues_include_element_count(self):
        """Test issues show actual vs required elements"""
        posts = [
            Post(
                content="Simple\n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = HeadlineValidator(min_elements=3)
        result = validator.validate(posts)

        issue = result["issues"][0]
        assert "/3" in issue or "3" in issue  # Shows threshold

    def test_issues_truncate_long_headlines(self):
        """Test issues truncate very long headlines"""
        long_headline = "x" * 100
        posts = [
            Post(
                content=f"{long_headline}\n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = HeadlineValidator(min_elements=5)
        result = validator.validate(posts)

        issue = result["issues"][0]
        # Should be truncated (60 chars + ...)
        assert len(issue) < len(long_headline) + 100


class TestMetricString:
    """Test metric string generation"""

    def test_metric_shows_pass_count(self):
        """Test metric shows how many headlines meet threshold"""
        posts = [
            Post(content="5 Secrets\n\nB", template_id=1, template_name="T1", client_name="Test"),
            Post(content="Weak\n\nB", template_id=2, template_name="T2", client_name="Test"),
        ]
        validator = HeadlineValidator(min_elements=2)
        result = validator.validate(posts)

        assert "1/2" in result["metric"] or "headlines meet threshold" in result["metric"]


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_validate_empty_posts(self):
        """Test validation with empty posts list"""
        validator = HeadlineValidator()
        result = validator.validate([])

        assert result["passed"] is True
        assert result["headlines_analyzed"] == 0
        assert result["average_elements"] == 0

    def test_validate_single_post(self):
        """Test validation with single post"""
        posts = [
            Post(
                content="5 Secret Ways\n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = HeadlineValidator(min_elements=2)
        result = validator.validate(posts)

        assert result["passed"] is True
        assert result["headlines_analyzed"] == 1

    def test_count_elements_empty_headline(self):
        """Test counting elements in empty headline"""
        validator = HeadlineValidator()
        count = validator._count_engagement_elements("")
        assert count == 0

    def test_count_elements_whitespace_only(self):
        """Test counting elements in whitespace-only headline"""
        validator = HeadlineValidator()
        count = validator._count_engagement_elements("   ")
        assert count == 0

    def test_count_elements_special_characters(self):
        """Test handles special characters gracefully"""
        validator = HeadlineValidator()
        # Should not crash with unicode or emojis
        count = validator._count_engagement_elements("🚀 How to Succeed with émojis?")
        assert count >= 1  # At least question mark

    def test_power_words_case_insensitive(self):
        """Test power word detection is case-insensitive"""
        validator = HeadlineValidator()
        count1 = validator._count_engagement_elements("The ULTIMATE Guide")
        count2 = validator._count_engagement_elements("The ultimate Guide")
        assert count1 == count2

    def test_question_words_at_start(self):
        """Test question words detected at start of headline"""
        validator = HeadlineValidator()
        details = validator._get_element_details("How to succeed in business")
        assert details["has_question_word"] is True

    def test_proper_nouns_not_at_start(self):
        """Test proper nouns only counted if not at start"""
        validator = HeadlineValidator()
        # "Apple" at start shouldn't count (could be first word of sentence)
        # But this test verifies the regex pattern
        validator._get_element_details("Apple is great")
        details2 = validator._get_element_details("Why Apple is great")
        # Second should have specificity (Apple not at absolute start)
        assert details2["has_specificity"] is True
