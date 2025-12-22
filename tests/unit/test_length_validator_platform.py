"""
Unit tests for platform-specific length validation in LengthValidator

Tests verify that:
1. Platform detection works with both enum and string
2. Platform-specific buckets are correctly defined
3. Word counts are assigned to correct buckets
4. Distribution calculation uses platform-specific buckets
5. Validation uses platform-specific min/max/optimal ranges
"""
import pytest

from src.models.client_brief import Platform
from src.models.post import Post
from src.validators.length_validator import LengthValidator


class TestLengthValidatorPlatform:
    """Test platform-specific length validation"""

    @pytest.fixture
    def validator(self):
        """Create LengthValidator instance"""
        return LengthValidator()

    def test_detect_platform_with_enum(self, validator):
        """Test platform detection when target_platform is Platform enum"""
        posts = [
            Post(
                content="Test post",
                template_id=1,
                template_name="Test Template",
                client_name="Test Client",
                variant=1,
                target_platform=Platform.TWITTER,
            )
        ]

        platform = validator._detect_platform(posts)
        assert platform == Platform.TWITTER

    def test_detect_platform_with_string(self, validator):
        """Test platform detection when target_platform is string (backward compat)"""
        posts = [
            Post(
                content="Test post",
                template_id=1,
                template_name="Test Template",
                client_name="Test Client",
                variant=1,
                target_platform="linkedin",  # String instead of enum
            )
        ]

        platform = validator._detect_platform(posts)
        assert platform == Platform.LINKEDIN

    def test_detect_platform_none(self, validator):
        """Test platform detection returns None for empty posts"""
        posts = []
        platform = validator._detect_platform(posts)
        assert platform is None

    def test_detect_platform_no_target(self, validator):
        """Test platform detection returns None when no target_platform"""
        posts = [
            Post(
                content="Test post",
                template_id=1,
                template_name="Test Template",
                client_name="Test Client",
                variant=1,
            )
        ]
        platform = validator._detect_platform(posts)
        assert platform is None

    def test_twitter_buckets(self, validator):
        """Test Twitter gets correct distribution buckets"""
        buckets = validator._get_platform_buckets(Platform.TWITTER)
        assert buckets == ["0-10", "10-15", "15-20", "20-30", "30+"]

    def test_facebook_buckets(self, validator):
        """Test Facebook gets correct distribution buckets"""
        buckets = validator._get_platform_buckets(Platform.FACEBOOK)
        assert buckets == ["0-8", "8-12", "12-18", "18-25", "25+"]

    def test_linkedin_buckets(self, validator):
        """Test LinkedIn gets correct distribution buckets"""
        buckets = validator._get_platform_buckets(Platform.LINKEDIN)
        assert buckets == ["0-150", "150-200", "200-250", "250-300", "300+"]

    def test_blog_buckets(self, validator):
        """Test Blog gets correct distribution buckets"""
        buckets = validator._get_platform_buckets(Platform.BLOG)
        assert buckets == ["0-1000", "1000-1500", "1500-2000", "2000-2500", "2500+"]

    def test_email_buckets(self, validator):
        """Test Email gets correct distribution buckets"""
        buckets = validator._get_platform_buckets(Platform.EMAIL)
        assert buckets == ["0-100", "100-150", "150-200", "200-250", "250+"]

    def test_default_buckets_for_none(self, validator):
        """Test default buckets when platform is None"""
        buckets = validator._get_platform_buckets(None)
        assert buckets == ["0-100", "100-150", "150-200", "200-250", "250-300", "300+"]

    def test_assign_to_twitter_bucket(self, validator):
        """Test word count assignment to Twitter buckets"""
        twitter_buckets = ["0-10", "10-15", "15-20", "20-30", "30+"]

        assert validator._assign_to_bucket(5, twitter_buckets) == "0-10"
        assert validator._assign_to_bucket(12, twitter_buckets) == "10-15"
        assert validator._assign_to_bucket(18, twitter_buckets) == "15-20"
        assert validator._assign_to_bucket(25, twitter_buckets) == "20-30"
        assert validator._assign_to_bucket(50, twitter_buckets) == "30+"

    def test_assign_to_blog_bucket(self, validator):
        """Test word count assignment to Blog buckets"""
        blog_buckets = ["0-1000", "1000-1500", "1500-2000", "2000-2500", "2500+"]

        assert validator._assign_to_bucket(500, blog_buckets) == "0-1000"
        assert validator._assign_to_bucket(1200, blog_buckets) == "1000-1500"
        assert validator._assign_to_bucket(1800, blog_buckets) == "1500-2000"
        assert validator._assign_to_bucket(2200, blog_buckets) == "2000-2500"
        assert validator._assign_to_bucket(3000, blog_buckets) == "2500+"

    def test_twitter_distribution(self, validator):
        """Test distribution calculation for Twitter posts"""
        # Twitter posts: 8w, 14w, 17w, 25w, 40w
        word_counts = [8, 14, 17, 25, 40]

        distribution = validator._calculate_distribution(word_counts, Platform.TWITTER)

        assert distribution["0-10"] == 1  # 8w
        assert distribution["10-15"] == 1  # 14w
        assert distribution["15-20"] == 1  # 17w
        assert distribution["20-30"] == 1  # 25w
        assert distribution["30+"] == 1  # 40w

    def test_blog_distribution(self, validator):
        """Test distribution calculation for Blog posts"""
        # Blog posts: 500w, 1200w, 1800w, 2300w, 3000w
        word_counts = [500, 1200, 1800, 2300, 3000]

        distribution = validator._calculate_distribution(word_counts, Platform.BLOG)

        assert distribution["0-1000"] == 1  # 500w
        assert distribution["1000-1500"] == 1  # 1200w
        assert distribution["1500-2000"] == 1  # 1800w
        assert distribution["2000-2500"] == 1  # 2300w
        assert distribution["2500+"] == 1  # 3000w

    def test_validate_twitter_posts(self, validator):
        """Test validation uses Twitter-specific specs"""
        posts = [
            Post(
                content="Short tweet",
                template_id=1,
                template_name="Test Template",
                client_name="Test Client",
                variant=i,
                target_platform=Platform.TWITTER,
            )
            for i in range(1, 6)
        ]

        # Manually set word counts (Twitter optimal: 12-18 words)
        posts[0]._word_count = 5  # Too short
        posts[1]._word_count = 14  # Optimal
        posts[2]._word_count = 16  # Optimal
        posts[3]._word_count = 25  # Too long
        posts[4]._word_count = 50  # Way too long

        result = validator.validate(posts)

        # Should use Twitter specs (min: 8, max: 50, optimal: 12-18)
        assert result["platform"] == "twitter"
        assert "twitter" in result["metric"].lower()

        # Check distribution uses Twitter buckets
        assert "0-10" in result["length_distribution"]
        assert "10-15" in result["length_distribution"]
        assert "30+" in result["length_distribution"]

        # Should NOT have LinkedIn buckets
        assert "150-200" not in result["length_distribution"]

    def test_validate_blog_posts(self, validator):
        """Test validation uses Blog-specific specs"""
        posts = [
            Post(
                content="Long blog post content",
                template_id=1,
                template_name="Test Template",
                client_name="Test Client",
                variant=i,
                target_platform=Platform.BLOG,
            )
            for i in range(1, 6)
        ]

        # Manually set word counts (Blog optimal: 1500-2500 words)
        posts[0]._word_count = 500  # Too short
        posts[1]._word_count = 1600  # Optimal
        posts[2]._word_count = 2000  # Optimal
        posts[3]._word_count = 2400  # Optimal
        posts[4]._word_count = 3500  # Too long

        result = validator.validate(posts)

        # Should use Blog specs
        assert result["platform"] == "blog"

        # Check distribution uses Blog buckets
        assert "0-1000" in result["length_distribution"]
        assert "1500-2000" in result["length_distribution"]
        assert "2500+" in result["length_distribution"]

        # Should NOT have Twitter buckets
        assert "10-15" not in result["length_distribution"]

    def test_validate_linkedin_posts(self, validator):
        """Test validation uses LinkedIn-specific specs"""
        posts = [
            Post(
                content="LinkedIn post content",
                template_id=1,
                template_name="Test Template",
                client_name="Test Client",
                variant=i,
                target_platform=Platform.LINKEDIN,
            )
            for i in range(1, 6)
        ]

        # Manually set word counts (LinkedIn optimal: 200-300 words)
        posts[0]._word_count = 100  # Too short
        posts[1]._word_count = 220  # Optimal
        posts[2]._word_count = 250  # Optimal
        posts[3]._word_count = 280  # Optimal
        posts[4]._word_count = 350  # Too long

        result = validator.validate(posts)

        # Should use LinkedIn specs
        assert result["platform"] == "linkedin"

        # Check distribution uses LinkedIn buckets
        assert "0-150" in result["length_distribution"]
        assert "200-250" in result["length_distribution"]
        assert "250-300" in result["length_distribution"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
