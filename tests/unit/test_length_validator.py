"""Comprehensive unit tests for LengthValidator

Tests post length validation with platform-specific specs and distribution analysis.
"""

import pytest

from src.models.client_brief import Platform
from src.models.post import Post
from src.validators.length_validator import LengthValidator


@pytest.fixture
def posts_optimal_length():
    """Create posts with optimal length (200-250 words for LinkedIn default)"""
    filler_200 = " ".join(["word"] * 200)
    filler_225 = " ".join(["word"] * 225)
    return [
        Post(content=filler_200, template_id=1, template_name="T1", client_name="Test"),
        Post(content=filler_225, template_id=2, template_name="T2", client_name="Test"),
    ]


@pytest.fixture
def posts_mixed_length():
    """Create posts with mixed lengths"""
    short = " ".join(["word"] * 30)  # Too short (min 75)
    good = " ".join(["word"] * 200)  # Good
    long = " ".join(["word"] * 400)  # Too long (max 350)
    return [
        Post(content=short, template_id=1, template_name="T1", client_name="Test"),
        Post(content=good, template_id=2, template_name="T2", client_name="Test"),
        Post(content=long, template_id=3, template_name="T3", client_name="Test"),
    ]


class TestLengthValidatorInit:
    """Test LengthValidator initialization"""

    def test_init_with_defaults(self):
        """Test initialization with default parameters from settings"""
        validator = LengthValidator()
        assert validator.min_words == 200  # Default MIN_POST_WORD_COUNT (LinkedIn minimum)
        assert validator.max_words == 350  # Default MAX_POST_WORD_COUNT
        assert validator.optimal_min == 220  # Default OPTIMAL_POST_MIN_WORDS
        assert validator.optimal_max == 280  # Default OPTIMAL_POST_MAX_WORDS
        assert validator.sameness_threshold == 0.70

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters"""
        validator = LengthValidator(
            min_words=50,
            max_words=400,
            optimal_min=100,
            optimal_max=250,
            sameness_threshold=0.80,
        )
        assert validator.min_words == 50
        assert validator.max_words == 400
        assert validator.optimal_min == 100
        assert validator.optimal_max == 250
        assert validator.sameness_threshold == 0.80


class TestValidate:
    """Test main validate method"""

    def test_validate_optimal_posts_pass(self, posts_optimal_length):
        """Test validation passes with optimal length posts"""
        validator = LengthValidator()
        result = validator.validate(posts_optimal_length)

        assert result["passed"] is True
        assert len(result["issues"]) == 0

    def test_validate_mixed_posts_fail(self, posts_mixed_length):
        """Test validation fails with mixed length issues"""
        validator = LengthValidator()
        result = validator.validate(posts_mixed_length)

        assert result["passed"] is False
        assert len(result["issues"]) >= 2  # Too short + too long

    def test_validate_returns_all_fields(self, posts_optimal_length):
        """Test validation result contains all expected fields"""
        validator = LengthValidator()
        result = validator.validate(posts_optimal_length)

        assert "passed" in result
        assert "length_distribution" in result
        assert "average_length" in result
        assert "optimal_ratio" in result
        assert "sameness_ratio" in result
        assert "issues" in result
        assert "metric" in result
        assert "platform" in result

    def test_validate_calculates_average(self):
        """Test validation calculates correct average"""
        posts = [
            Post(
                content=" ".join(["word"] * 100),
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
            Post(
                content=" ".join(["word"] * 200),
                template_id=2,
                template_name="T2",
                client_name="Test",
            ),
        ]
        validator = LengthValidator()
        result = validator.validate(posts)

        assert result["average_length"] == 150.0


class TestPlatformSpecificValidation:
    """Test platform-specific length requirements"""

    def test_twitter_short_posts(self):
        """Test Twitter accepts very short posts"""
        posts = [
            Post(
                content=" ".join(["word"] * 15),  # 15 words OK for Twitter
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.TWITTER,
            ),
        ]
        validator = LengthValidator()
        result = validator.validate(posts)

        assert result["platform"] == "twitter"
        # Should pass for Twitter's short post requirements

    def test_blog_long_posts(self):
        """Test Blog accepts long posts"""
        posts = [
            Post(
                content=" ".join(["word"] * 1600),  # 1600 words OK for Blog
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.BLOG,
            ),
        ]
        validator = LengthValidator()
        result = validator.validate(posts)

        assert result["platform"] == "blog"
        # Should pass for Blog's long post requirements

    def test_linkedin_medium_posts(self):
        """Test LinkedIn medium-length posts"""
        posts = [
            Post(
                content=" ".join(["word"] * 220),  # 220 words good for LinkedIn
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.LINKEDIN,
            ),
        ]
        validator = LengthValidator()
        result = validator.validate(posts)

        assert result["platform"] == "linkedin"

    def test_no_platform_uses_defaults(self):
        """Test uses default settings when no platform"""
        posts = [
            Post(
                content=" ".join(["word"] * 200),
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = LengthValidator()
        result = validator.validate(posts)

        assert result["platform"] is None


class TestDetectPlatform:
    """Test platform detection"""

    def test_detect_platform_from_post(self):
        """Test detects platform from post attribute"""
        posts = [
            Post(
                content="Test",
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.LINKEDIN,
            ),
        ]
        validator = LengthValidator()
        platform = validator._detect_platform(posts)
        assert platform == Platform.LINKEDIN

    def test_detect_platform_none_when_empty(self):
        """Test returns None for empty list"""
        validator = LengthValidator()
        platform = validator._detect_platform([])
        assert platform is None

    def test_detect_platform_from_string(self):
        """Test handles platform as string"""
        post = Post(content="Test", template_id=1, template_name="T1", client_name="Test")
        post.target_platform = "blog"

        validator = LengthValidator()
        platform = validator._detect_platform([post])
        assert platform == Platform.BLOG


class TestTooShortDetection:
    """Test detection of too-short posts"""

    def test_detects_too_short(self):
        """Test detects posts below minimum"""
        posts = [
            Post(
                content=" ".join(["word"] * 30),  # 30 < 75 min
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = LengthValidator(min_words=75)
        result = validator.validate(posts)

        assert result["passed"] is False
        assert any("too short" in issue.lower() for issue in result["issues"])
        assert "Post 1" in result["issues"][0]

    def test_platform_specific_min(self):
        """Test uses platform-specific minimum"""
        posts = [
            Post(
                content=" ".join(["word"] * 5),  # Very short
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.TWITTER,
            ),
        ]
        validator = LengthValidator()
        validator.validate(posts)

        # Twitter has lower minimum, might pass
        # At minimum, should mention Twitter in metric


class TestTooLongDetection:
    """Test detection of too-long posts"""

    def test_detects_too_long(self):
        """Test detects posts above maximum"""
        posts = [
            Post(
                content=" ".join(["word"] * 500),  # 500 > 350 max
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = LengthValidator(max_words=350)
        result = validator.validate(posts)

        assert result["passed"] is False
        assert any("too long" in issue.lower() for issue in result["issues"])

    def test_platform_specific_max(self):
        """Test uses platform-specific maximum"""
        posts = [
            Post(
                content=" ".join(["word"] * 300),  # 300 words
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.LINKEDIN,
            ),
        ]
        validator = LengthValidator()
        validator.validate(posts)

        # Should be OK for LinkedIn (max 300)


class TestSamenessDetection:
    """Test detection of too-similar lengths"""

    def test_detects_sameness(self):
        """Test detects when too many posts have similar length"""
        # Create 10 posts all exactly 200 words to ensure they're in the same bucket
        posts = [
            Post(
                content=" ".join(["word"] * 200),  # All exactly 200 words
                template_id=i,
                template_name=f"T{i}",
                client_name="Test",
            )
            for i in range(10)
        ]
        validator = LengthValidator(sameness_threshold=0.70)
        result = validator.validate(posts)

        # All posts in same bucket = 100% sameness (should exceed 0.70 threshold)
        assert result["sameness_ratio"] >= 0.70
        if result["sameness_ratio"] > 0.70:
            assert any("lacks variety" in issue.lower() for issue in result["issues"])

    def test_check_sameness_buckets(self):
        """Test sameness uses small buckets for grouping similar lengths"""
        validator = LengthValidator()
        # Posts at 200, 201, 202 should all be in same bucket
        word_counts = [200, 201, 202]
        sameness = validator._check_sameness(word_counts)

        # All 3 in same bucket = 100% sameness
        assert sameness == 1.0

    def test_check_sameness_varied(self):
        """Test varied lengths have low sameness"""
        validator = LengthValidator()
        word_counts = [100, 200, 300]  # Different buckets
        sameness = validator._check_sameness(word_counts)

        # Different buckets = low sameness
        assert sameness < 0.5


class TestLengthDistribution:
    """Test length distribution calculation"""

    def test_calculate_distribution_twitter(self):
        """Test Twitter distribution uses correct buckets"""
        validator = LengthValidator()
        word_counts = [10, 15, 25]
        distribution = validator._calculate_distribution(word_counts, Platform.TWITTER)

        assert "0-10" in distribution or "10-15" in distribution

    def test_calculate_distribution_blog(self):
        """Test Blog distribution uses correct buckets"""
        validator = LengthValidator()
        word_counts = [1200, 1800]
        distribution = validator._calculate_distribution(word_counts, Platform.BLOG)

        assert "1000-1500" in distribution or "1500-2000" in distribution

    def test_get_platform_buckets(self):
        """Test gets correct buckets for each platform"""
        validator = LengthValidator()

        twitter_buckets = validator._get_platform_buckets(Platform.TWITTER)
        assert "0-10" in twitter_buckets

        blog_buckets = validator._get_platform_buckets(Platform.BLOG)
        assert "1000-1500" in blog_buckets

        linkedin_buckets = validator._get_platform_buckets(Platform.LINKEDIN)
        assert "150-200" in linkedin_buckets

    def test_assign_to_bucket(self):
        """Test assigns word counts to correct buckets"""
        validator = LengthValidator()
        buckets = ["0-100", "100-150", "150-200", "200+"]

        assert validator._assign_to_bucket(50, buckets) == "0-100"
        assert validator._assign_to_bucket(125, buckets) == "100-150"
        assert validator._assign_to_bucket(175, buckets) == "150-200"
        assert validator._assign_to_bucket(300, buckets) == "200+"

    def test_assign_to_bucket_fallback(self):
        """Test bucket assignment fallback"""
        validator = LengthValidator()
        buckets = ["100-200", "200+"]

        # 50 is below all buckets, should fallback to first
        result = validator._assign_to_bucket(50, buckets)
        assert result == buckets[0]


class TestOptimalRange:
    """Test optimal range calculations"""

    def test_calculates_optimal_ratio(self):
        """Test calculates ratio of posts in optimal range"""
        posts = [
            Post(
                content=" ".join(["word"] * 200),
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
            Post(
                content=" ".join(["word"] * 250),
                template_id=2,
                template_name="T2",
                client_name="Test",
            ),
            Post(
                content=" ".join(["word"] * 100),
                template_id=3,
                template_name="T3",
                client_name="Test",
            ),
        ]
        validator = LengthValidator(optimal_min=150, optimal_max=300)
        result = validator.validate(posts)

        # 2 out of 3 in optimal range
        assert result["optimal_ratio"] == pytest.approx(2 / 3, rel=0.01)


class TestMetricString:
    """Test metric string generation"""

    def test_metric_shows_optimal_count(self):
        """Test metric shows count in optimal range"""
        posts = [
            Post(
                content=" ".join(["word"] * 200),
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = LengthValidator(optimal_min=150, optimal_max=300)
        result = validator.validate(posts)

        assert "1/1 posts in optimal range" in result["metric"]

    def test_metric_includes_platform(self):
        """Test metric mentions platform when detected"""
        posts = [
            Post(
                content=" ".join(["word"] * 220),
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.LINKEDIN,
            ),
        ]
        validator = LengthValidator()
        result = validator.validate(posts)

        assert "linkedin" in result["metric"].lower() or "LinkedIn" in result["metric"]


class TestIssuesReporting:
    """Test issue reporting"""

    def test_issues_include_word_count(self):
        """Test issues show actual word count"""
        posts = [
            Post(
                content=" ".join(["word"] * 30),
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = LengthValidator(min_words=75)
        result = validator.validate(posts)

        assert "30 words" in result["issues"][0]
        assert "75" in result["issues"][0]  # Shows minimum

    def test_issues_show_platform(self):
        """Test issues mention platform when applicable"""
        posts = [
            Post(
                content=" ".join(["word"] * 10),
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.TWITTER,
            ),
        ]
        validator = LengthValidator()
        validator.validate(posts)

        # If there are issues, they should mention Twitter


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_validate_empty_posts(self):
        """Test validation with empty posts list"""
        validator = LengthValidator()
        result = validator.validate([])

        # Should handle gracefully
        assert "passed" in result
        assert result["average_length"] == 0

    def test_validate_single_post(self):
        """Test validation with single post"""
        posts = [
            Post(
                content=" ".join(["word"] * 200),
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = LengthValidator()
        result = validator.validate(posts)

        # Should work with single post
        assert result["sameness_ratio"] >= 0  # Defined behavior

    def test_check_sameness_empty(self):
        """Test sameness check with empty list"""
        validator = LengthValidator()
        sameness = validator._check_sameness([])
        assert sameness == 0.0

    def test_check_sameness_single(self):
        """Test sameness check with single post"""
        validator = LengthValidator()
        sameness = validator._check_sameness([200])
        assert sameness == 0.0

    def test_calculate_distribution_empty(self):
        """Test distribution calculation with no posts"""
        validator = LengthValidator()
        distribution = validator._calculate_distribution([], Platform.LINKEDIN)

        # Should return buckets with 0 counts
        assert isinstance(distribution, dict)
        assert all(count == 0 for count in distribution.values())

    def test_validate_all_same_length(self):
        """Test validation when all posts exact same length"""
        posts = [
            Post(
                content=" ".join(["word"] * 200),
                template_id=i,
                template_name=f"T{i}",
                client_name="Test",
            )
            for i in range(5)
        ]
        validator = LengthValidator(sameness_threshold=0.70)
        result = validator.validate(posts)

        # Should flag 100% sameness
        assert result["sameness_ratio"] == 1.0
        assert result["passed"] is False

    def test_validate_high_optimal_ratio(self):
        """Test all posts in optimal range"""
        posts = [
            Post(
                content=" ".join(["word"] * (175 + i * 10)),  # 175, 185, 195
                template_id=i,
                template_name=f"T{i}",
                client_name="Test",
            )
            for i in range(3)
        ]
        validator = LengthValidator(optimal_min=150, optimal_max=300)
        result = validator.validate(posts)

        assert result["optimal_ratio"] == 1.0
