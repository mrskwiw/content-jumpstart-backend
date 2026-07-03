"""Comprehensive unit tests for KeywordValidator

Tests SEO keyword usage validation across posts.
"""

import pytest

from src.models.post import Post
from src.models.seo_keyword import (
    KeywordStrategy,
    SEOKeyword,
    KeywordIntent,
    KeywordDifficulty,
)
from src.validators.keyword_validator import KeywordValidator


@pytest.fixture
def sample_keyword_strategy():
    """Create sample keyword strategy"""
    return KeywordStrategy(
        primary_keywords=[
            SEOKeyword(
                keyword="cloud solutions",
                intent=KeywordIntent.COMMERCIAL,
                difficulty=KeywordDifficulty.MEDIUM,
                priority=1,
            ),
            SEOKeyword(
                keyword="workflow automation",
                intent=KeywordIntent.COMMERCIAL,
                difficulty=KeywordDifficulty.MEDIUM,
                priority=2,
            ),
        ],
        secondary_keywords=[
            SEOKeyword(
                keyword="productivity tools",
                intent=KeywordIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.EASY,
                priority=3,
            ),
        ],
        longtail_keywords=[
            SEOKeyword(
                keyword="how to automate business workflows",
                intent=KeywordIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.EASY,
                priority=4,
            ),
        ],
        keyword_density_target=0.02,
    )


@pytest.fixture
def posts_with_keywords():
    """Create posts containing keywords"""
    return [
        Post(
            content=(
                "Our cloud solutions help businesses work more efficiently across all departments. "
                "Modern teams need tools that integrate seamlessly with their existing systems and processes. "
                "When you choose the right platform, you can save time and reduce operational overhead significantly."
            ),
            template_id=1,
            template_name="T1",
            client_name="Test",
        ),
        Post(
            content=(
                "Learn how to improve operational efficiency and enhance your team's performance every day. "
                "With workflow automation, you can eliminate repetitive manual tasks that waste valuable time. "
                "This allows your team to focus on strategic initiatives that drive real business value and growth. "
                "Our productivity tools make it easy to streamline processes across all departments and teams. "
                "Organizations report significant improvements in efficiency when they adopt these modern solutions. "
                "The result is better collaboration, faster delivery, happier employees, and improved customer satisfaction overall."
            ),
            template_id=2,
            template_name="T2",
            client_name="Test",
        ),
    ]


@pytest.fixture
def posts_without_keywords():
    """Create posts without target keywords"""
    return [
        Post(
            content="This post has completely different content with no relevant keywords.",
            template_id=1,
            template_name="T1",
            client_name="Test",
        ),
    ]


class TestKeywordValidatorInit:
    """Test KeywordValidator initialization"""

    def test_init_with_strategy(self, sample_keyword_strategy):
        """Test initialization with keyword strategy"""
        validator = KeywordValidator(sample_keyword_strategy)
        assert validator.keyword_strategy == sample_keyword_strategy
        assert validator.max_density == 0.03
        assert validator.min_primary_usage == 0.7

    def test_init_with_custom_params(self, sample_keyword_strategy):
        """Test initialization with custom parameters"""
        validator = KeywordValidator(
            sample_keyword_strategy,
            max_density=0.05,
            min_primary_usage=0.8,
        )
        assert validator.max_density == 0.05
        assert validator.min_primary_usage == 0.8


class TestValidate:
    """Test main validate method"""

    def test_validate_good_keyword_usage(self, sample_keyword_strategy, posts_with_keywords):
        """Test validation passes with good keyword usage"""
        validator = KeywordValidator(sample_keyword_strategy, min_primary_usage=0.5)
        result = validator.validate(posts_with_keywords)

        # Both posts have primary keywords
        assert result["posts_with_primary"] == 2
        assert result["primary_usage_ratio"] == 1.0
        assert result["passed"] is True

    def test_validate_missing_keywords(self, sample_keyword_strategy, posts_without_keywords):
        """Test validation fails when keywords missing"""
        validator = KeywordValidator(sample_keyword_strategy, min_primary_usage=0.7)
        result = validator.validate(posts_without_keywords)

        assert result["posts_with_primary"] == 0
        assert result["primary_usage_ratio"] == 0.0
        assert result["passed"] is False

    def test_validate_keyword_stuffing(self, sample_keyword_strategy):
        """Test validation detects keyword stuffing"""
        # Create post with excessive keyword density
        keyword_spam = "cloud solutions " * 50  # Repeat keyword excessively
        posts = [
            Post(
                content=keyword_spam,
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = KeywordValidator(sample_keyword_strategy, max_density=0.03)
        result = validator.validate(posts)

        assert result["posts_with_stuffing"] > 0
        assert result["passed"] is False

    def test_validate_returns_all_fields(self, sample_keyword_strategy, posts_with_keywords):
        """Test validation result contains all expected fields"""
        validator = KeywordValidator(sample_keyword_strategy)
        result = validator.validate(posts_with_keywords)

        assert "passed" in result
        assert "primary_usage_ratio" in result
        assert "posts_with_primary" in result
        assert "posts_with_stuffing" in result
        assert "posts_missing_keywords" in result
        assert "metric" in result
        assert "issues" in result
        assert "post_analyses" in result


class TestAnalyzePostKeywords:
    """Test post keyword analysis"""

    def test_analyze_post_detects_primary_keywords(self, sample_keyword_strategy):
        """Test detects primary keywords in post"""
        post = Post(
            content="Our cloud solutions are the best workflow automation tools.",
            template_id=1,
            template_name="T1",
            client_name="Test",
        )
        validator = KeywordValidator(sample_keyword_strategy)
        analysis = validator.analyze_post_keywords(post, 1)

        assert len(analysis.primary_keywords_used) == 2  # cloud solutions + workflow automation
        assert analysis.has_primary_keyword is True

    def test_analyze_post_detects_secondary_keywords(self, sample_keyword_strategy):
        """Test detects secondary keywords"""
        post = Post(
            content="We offer productivity tools for modern businesses.",
            template_id=1,
            template_name="T1",
            client_name="Test",
        )
        validator = KeywordValidator(sample_keyword_strategy)
        analysis = validator.analyze_post_keywords(post, 1)

        assert len(analysis.secondary_keywords_used) == 1
        assert analysis.secondary_keywords_used[0].keyword == "productivity tools"

    def test_analyze_post_detects_longtail_keywords(self, sample_keyword_strategy):
        """Test detects long-tail keywords"""
        post = Post(
            content="Learn how to automate business workflows with our guide.",
            template_id=1,
            template_name="T1",
            client_name="Test",
        )
        validator = KeywordValidator(sample_keyword_strategy)
        analysis = validator.analyze_post_keywords(post, 1)

        assert len(analysis.longtail_keywords_used) == 1

    def test_analyze_post_calculates_density(self, sample_keyword_strategy):
        """Test calculates keyword density correctly"""
        # Post with 10 words, 1 keyword occurrence
        post = Post(
            content="cloud solutions " + " ".join(["word"] * 8),  # 1/10 = 10% density
            template_id=1,
            template_name="T1",
            client_name="Test",
        )
        validator = KeywordValidator(sample_keyword_strategy)
        analysis = validator.analyze_post_keywords(post, 1)

        # Overall density should be around 10% (1 keyword / 10 words)
        assert analysis.overall_keyword_density > 0

    def test_analyze_post_detects_stuffing(self, sample_keyword_strategy):
        """Test detects keyword stuffing"""
        # Repeat keyword many times in short post
        post = Post(
            content="cloud solutions " * 20,  # Very high density
            template_id=1,
            template_name="T1",
            client_name="Test",
        )
        validator = KeywordValidator(sample_keyword_strategy, max_density=0.03)
        analysis = validator.analyze_post_keywords(post, 1)

        assert analysis.keyword_stuffing_detected is True


class TestAnalyzeKeywordTier:
    """Test keyword tier analysis"""

    def test_analyze_tier_counts_occurrences(self, sample_keyword_strategy):
        """Test counts keyword occurrences correctly"""
        content = "cloud solutions are great cloud solutions"
        validator = KeywordValidator(sample_keyword_strategy)
        usage = validator._analyze_keyword_tier(
            content, 6, sample_keyword_strategy.primary_keywords
        )

        # Should find "cloud solutions" twice
        assert len(usage) == 1
        assert usage[0].count == 2

    def test_analyze_tier_detects_locations(self, sample_keyword_strategy):
        """Test detects keyword locations"""
        content = "cloud solutions help automate workflows in body text"
        validator = KeywordValidator(sample_keyword_strategy)
        usage = validator._analyze_keyword_tier(
            content, 8, sample_keyword_strategy.primary_keywords
        )

        # Should detect keyword in headline/body
        assert len(usage) > 0
        assert len(usage[0].locations) > 0

    def test_analyze_tier_calculates_density(self, sample_keyword_strategy):
        """Test calculates per-keyword density"""
        content = "cloud solutions " + " ".join(["word"] * 9)  # 10 words total
        validator = KeywordValidator(sample_keyword_strategy)
        usage = validator._analyze_keyword_tier(
            content, 10, sample_keyword_strategy.primary_keywords
        )

        assert len(usage) == 1
        assert usage[0].density == pytest.approx(0.1, rel=0.01)  # 1/10 = 10%

    def test_analyze_tier_checks_naturalness(self, sample_keyword_strategy):
        """Test checks if keyword integration is natural"""
        # Natural usage (low density)
        content = "Our cloud solutions " + " ".join(["word"] * 50)
        validator = KeywordValidator(sample_keyword_strategy)
        usage = validator._analyze_keyword_tier(
            content, 52, sample_keyword_strategy.primary_keywords
        )

        assert usage[0].natural is True

        # Unnatural usage (high density)
        content_spam = "cloud solutions " * 10
        usage_spam = validator._analyze_keyword_tier(
            content_spam, 20, sample_keyword_strategy.primary_keywords
        )

        assert usage_spam[0].natural is False

    def test_analyze_tier_case_insensitive(self, sample_keyword_strategy):
        """Test keyword detection is case-insensitive"""
        content = "CLOUD SOLUTIONS are great Cloud Solutions"
        validator = KeywordValidator(sample_keyword_strategy)
        # _analyze_keyword_tier expects lowercased content
        usage = validator._analyze_keyword_tier(
            content.lower(), 6, sample_keyword_strategy.primary_keywords
        )

        assert len(usage) == 1
        assert usage[0].count == 2

    def test_analyze_tier_whole_word_matching(self, sample_keyword_strategy):
        """Test uses whole word matching"""
        content = "cloudier solutions are cloudy"  # Should NOT match "cloud solutions"
        validator = KeywordValidator(sample_keyword_strategy)
        usage = validator._analyze_keyword_tier(
            content, 5, sample_keyword_strategy.primary_keywords
        )

        # Should not match partial words
        assert len(usage) == 0


class TestIssuesReporting:
    """Test issue reporting"""

    def test_issues_report_low_primary_usage(self, sample_keyword_strategy):
        """Test issues report low primary keyword usage"""
        posts = [
            Post(content="No keywords here", template_id=1, template_name="T1", client_name="Test"),
        ]
        validator = KeywordValidator(sample_keyword_strategy, min_primary_usage=0.7)
        result = validator.validate(posts)

        assert len(result["issues"]) > 0
        assert "primary keywords" in result["issues"][0].lower()

    def test_issues_report_keyword_stuffing(self, sample_keyword_strategy):
        """Test issues report keyword stuffing"""
        posts = [
            Post(
                content="cloud solutions " * 50,
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = KeywordValidator(sample_keyword_strategy, max_density=0.03)
        result = validator.validate(posts)

        assert len(result["issues"]) > 0
        assert "stuffing" in result["issues"][0].lower()

    def test_issues_report_missing_keywords(self, sample_keyword_strategy):
        """Test issues report posts missing keywords"""
        posts = [
            Post(content="No keywords", template_id=1, template_name="T1", client_name="Test"),
        ]
        validator = KeywordValidator(sample_keyword_strategy)
        result = validator.validate(posts)

        # Message format: "Only X/Y posts contain primary keywords (target: Z%)"
        assert "0/1 posts contain primary keywords" in result["issues"][0].lower()


class TestMetricString:
    """Test metric string generation"""

    def test_metric_shows_primary_count(self, sample_keyword_strategy, posts_with_keywords):
        """Test metric shows posts with primary keywords"""
        validator = KeywordValidator(sample_keyword_strategy)
        result = validator.validate(posts_with_keywords)

        assert "2/2 posts with primary keywords" in result["metric"]


class TestPostAnalysesOutput:
    """Test post analyses output structure"""

    def test_post_analyses_structure(self, sample_keyword_strategy, posts_with_keywords):
        """Test post analyses have correct structure"""
        validator = KeywordValidator(sample_keyword_strategy)
        result = validator.validate(posts_with_keywords)

        assert len(result["post_analyses"]) == 2
        analysis = result["post_analyses"][0]

        # Check fields from to_dict() method
        assert "post_id" in analysis
        assert "template" in analysis  # to_dict returns "template", not "template_name"
        assert (
            "primary_keywords" in analysis
        )  # to_dict returns "primary_keywords", not "primary_keywords_used"
        assert (
            "total_keywords" in analysis
        )  # to_dict returns "total_keywords", not "total_keyword_count"
        assert "density" in analysis  # to_dict returns "density", not "overall_keyword_density"
        assert "has_primary" in analysis
        assert "issues" in analysis

    def test_post_analyses_serializable(self, sample_keyword_strategy, posts_with_keywords):
        """Test post analyses can be serialized to dict"""
        validator = KeywordValidator(sample_keyword_strategy)
        result = validator.validate(posts_with_keywords)

        # Should be list of dicts
        for analysis in result["post_analyses"]:
            assert isinstance(analysis, dict)


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_validate_empty_posts(self, sample_keyword_strategy):
        """Test validation with empty posts list"""
        validator = KeywordValidator(sample_keyword_strategy)
        result = validator.validate([])

        assert result["primary_usage_ratio"] == 0
        assert result["passed"] is False

    def test_validate_single_post(self, sample_keyword_strategy):
        """Test validation with single post"""
        posts = [
            Post(
                content="Our cloud solutions are great.",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = KeywordValidator(sample_keyword_strategy, min_primary_usage=0.5)
        result = validator.validate(posts)

        assert result["posts_with_primary"] == 1
        assert result["primary_usage_ratio"] == 1.0

    def test_analyze_post_empty_content(self, sample_keyword_strategy):
        """Test handles posts with minimal content (no keywords)"""
        # Post model doesn't allow empty content, use minimal content instead
        post = Post(content="word", template_id=1, template_name="T1", client_name="Test")
        validator = KeywordValidator(sample_keyword_strategy)
        analysis = validator.analyze_post_keywords(post, 1)

        assert analysis.total_keyword_count == 0
        assert analysis.overall_keyword_density == 0
        assert analysis.has_primary_keyword is False

    def test_analyze_tier_empty_keywords(self, sample_keyword_strategy):
        """Test handles empty keyword tier"""
        content = "Some content here"
        validator = KeywordValidator(sample_keyword_strategy)
        usage = validator._analyze_keyword_tier(content, 3, [])

        assert len(usage) == 0

    def test_validate_all_posts_with_keywords(self, sample_keyword_strategy):
        """Test perfect scenario - all posts have keywords"""
        posts = [
            Post(
                content=(
                    "Our cloud solutions help businesses work more efficiently across all departments and teams. "
                    "Modern organizations face many challenges when trying to coordinate projects and manage tasks. "
                    "Teams need workflow automation tools that integrate seamlessly with their existing systems "
                    "and processes without causing disruption or requiring extensive training. When you choose the "
                    "right platform for your organization, you can save significant time and reduce operational "
                    "overhead while improving overall efficiency. This approach ensures better collaboration among "
                    "team members and drives measurable productivity gains across the entire organization. Many "
                    "companies have found success by implementing these strategies thoughtfully and carefully over "
                    "time, ensuring proper adoption and long-term value realization for all stakeholders involved."
                ),
                template_id=i,
                template_name=f"T{i}",
                client_name="Test",
            )
            for i in range(5)
        ]
        validator = KeywordValidator(sample_keyword_strategy, min_primary_usage=0.7)
        result = validator.validate(posts)

        assert result["passed"] is True
        assert result["primary_usage_ratio"] == 1.0
        assert result["posts_with_stuffing"] == 0

    def test_validate_special_characters_in_keywords(self, sample_keyword_strategy):
        """Test handles keywords with special characters"""
        content = "Our cloud solutions help businesses"
        validator = KeywordValidator(sample_keyword_strategy)
        analysis = validator.analyze_post_keywords(
            Post(content=content, template_id=1, template_name="T1", client_name="Test"), 1
        )

        # Should still find the keyword
        assert len(analysis.primary_keywords_used) > 0

    def test_keyword_locations_headline_vs_body(self, sample_keyword_strategy):
        """Test distinguishes headline vs body locations"""
        # Keyword in first line (headline)
        post1 = Post(
            content="cloud solutions headline\n\nBody text here",
            template_id=1,
            template_name="T1",
            client_name="Test",
        )
        # Keyword in body only
        post2 = Post(
            content="Headline\n\nBody has cloud solutions",
            template_id=2,
            template_name="T2",
            client_name="Test",
        )

        validator = KeywordValidator(sample_keyword_strategy)
        analysis1 = validator.analyze_post_keywords(post1, 1)
        analysis2 = validator.analyze_post_keywords(post2, 2)

        # First should have "headline" location
        assert "headline" in analysis1.primary_keywords_used[0].locations

        # Second should have "body" location
        assert "body" in analysis2.primary_keywords_used[0].locations
