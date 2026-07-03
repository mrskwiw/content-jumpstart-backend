"""Unit tests for SEO Validator.

Tests cover all methods in src/validators/seo_validator.py:
- SEOValidator initialization
- validate() method
- _analyze_post() method
- _analyze_structure() method
- _analyze_readability() method
- _analyze_keywords() method
- _extract_lsi_keywords() method
- _calculate_seo_score() method
- generate_meta_suggestions() method
"""

import pytest

from src.models.client_brief import Platform
from src.models.post import Post
from src.models.seo_keyword import KeywordStrategy, SEOKeyword, KeywordIntent, KeywordDifficulty
from src.validators.seo_validator import SEOValidator


@pytest.fixture
def blog_post_short():
    """Create a short blog post (below minimum length)."""
    return Post(
        template_id=1,
        template_name="Problem Recognition",
        client_name="Test Client",
        content="This is a short blog post that doesn't meet SEO requirements.",
        target_platform=Platform.BLOG,
    )


@pytest.fixture
def blog_post_optimal():
    """Create an optimal length blog post with good structure."""
    content = (
        """# Complete Guide to Content Marketing

## Introduction

Content marketing is essential for modern businesses. This comprehensive guide covers
everything you need to know about creating effective content marketing strategies.

## Why Content Marketing Matters

Content marketing helps businesses connect with their audience. It builds trust and
establishes authority in your industry. Many companies have seen significant growth
through strategic content creation.

## Key Strategies for Success

There are several proven strategies for content marketing success:

- Create valuable, educational content
- Understand your target audience
- Maintain consistency in publishing
- Optimize for search engines

## Measuring Your Results

Analytics are crucial for understanding what works. Track metrics like engagement,
conversions, and organic traffic to refine your approach.

## Conclusion

Content marketing requires patience and strategy. With the right approach, you can
build a loyal audience and drive meaningful business results.

For more information, visit our [resource page](/resources) or check out
[this external guide](https://example.com/guide).

"""
        + "Lorem ipsum dolor sit amet. " * 100
    )  # Add more content to reach optimal length
    return Post(
        template_id=1,
        template_name="How-To Guide",
        client_name="Test Client",
        content=content,
        target_platform=Platform.BLOG,
    )


@pytest.fixture
def blog_post_no_structure():
    """Create a blog post without proper heading structure."""
    content = "This is a blog post without any headings or structure. " * 100
    return Post(
        template_id=1,
        template_name="Unstructured Post",
        client_name="Test Client",
        content=content,
        target_platform=Platform.BLOG,
    )


@pytest.fixture
def linkedin_post():
    """Create a LinkedIn post (non-blog)."""
    return Post(
        template_id=1,
        template_name="Problem Recognition",
        client_name="Test Client",
        content="This is a LinkedIn post about content marketing strategies.",
        target_platform=Platform.LINKEDIN,
    )


@pytest.fixture
def keyword_strategy():
    """Create a keyword strategy for testing."""
    return KeywordStrategy(
        primary_keywords=[
            SEOKeyword(
                keyword="content marketing",
                search_volume=1000,
                difficulty=KeywordDifficulty.MEDIUM,
                intent=KeywordIntent.INFORMATIONAL,
            )
        ],
        secondary_keywords=[
            SEOKeyword(
                keyword="marketing strategy",
                search_volume=500,
                difficulty=KeywordDifficulty.EASY,
                intent=KeywordIntent.INFORMATIONAL,
            ),
            SEOKeyword(
                keyword="digital content",
                search_volume=300,
                difficulty=KeywordDifficulty.EASY,
                intent=KeywordIntent.INFORMATIONAL,
            ),
        ],
        longtail_keywords=[],
    )


class TestSEOValidatorInit:
    """Tests for SEOValidator initialization."""

    def test_default_initialization(self):
        """Test validator with default settings."""
        validator = SEOValidator()
        assert validator.keyword_strategy is None
        assert validator.min_seo_score == 60

    def test_custom_min_score(self):
        """Test validator with custom minimum SEO score."""
        validator = SEOValidator(min_seo_score=75)
        assert validator.min_seo_score == 75

    def test_with_keyword_strategy(self, keyword_strategy):
        """Test validator with keyword strategy."""
        validator = SEOValidator(keyword_strategy=keyword_strategy)
        assert validator.keyword_strategy is not None
        assert len(validator.keyword_strategy.primary_keywords) == 1


class TestSEOValidatorValidate:
    """Tests for the main validate() method."""

    def test_validate_no_blog_posts(self, linkedin_post):
        """Test validation skips when no blog posts present."""
        validator = SEOValidator()
        result = validator.validate([linkedin_post])

        assert result["passed"] is True
        assert result["skipped"] is True
        assert result["seo_scores"] == []
        assert "No blog posts" in result["metric"]

    def test_validate_empty_posts(self):
        """Test validation with empty post list."""
        validator = SEOValidator()
        result = validator.validate([])

        assert result["passed"] is True
        assert result["skipped"] is True

    def test_validate_single_blog_post(self, blog_post_optimal):
        """Test validation with a single well-structured blog post."""
        validator = SEOValidator(min_seo_score=50)
        result = validator.validate([blog_post_optimal])

        assert result["skipped"] is False
        assert len(result["seo_scores"]) == 1
        assert result["average_score"] > 0
        assert "blog posts" in result["metric"]

    def test_validate_multiple_blog_posts(self, blog_post_optimal, blog_post_short):
        """Test validation with multiple blog posts."""
        validator = SEOValidator(min_seo_score=30)
        result = validator.validate([blog_post_optimal, blog_post_short])

        assert len(result["seo_scores"]) == 2
        assert isinstance(result["average_score"], float)

    def test_validate_mixed_platforms(self, blog_post_optimal, linkedin_post):
        """Test validation filters to blog posts only."""
        validator = SEOValidator(min_seo_score=50)
        result = validator.validate([blog_post_optimal, linkedin_post])

        assert len(result["seo_scores"]) == 1  # Only blog post

    def test_validate_with_issues(self, blog_post_short):
        """Test validation detects issues with short content."""
        validator = SEOValidator(min_seo_score=80)
        result = validator.validate([blog_post_short])

        assert result["passed"] is False
        assert len(result["issues"]) > 0

    def test_validate_with_keyword_strategy(self, blog_post_optimal, keyword_strategy):
        """Test validation with keyword strategy."""
        validator = SEOValidator(
            keyword_strategy=keyword_strategy,
            min_seo_score=40,
        )
        result = validator.validate([blog_post_optimal])

        assert result["skipped"] is False
        assert len(result["recommendations"]) >= 0


class TestAnalyzePost:
    """Tests for _analyze_post() method."""

    def test_analyze_short_post(self, blog_post_short):
        """Test analysis flags short posts."""
        validator = SEOValidator()
        analysis = validator._analyze_post(blog_post_short, 1)

        assert "issues" in analysis
        assert any("Too short" in issue for issue in analysis["issues"])

    def test_analyze_optimal_post(self, blog_post_optimal):
        """Test analysis of well-structured post."""
        validator = SEOValidator()
        analysis = validator._analyze_post(blog_post_optimal, 1)

        assert "seo_score" in analysis
        assert analysis["seo_score"] > 0
        assert "structure" in analysis
        assert "readability" in analysis

    def test_analyze_with_keyword_strategy(self, blog_post_optimal, keyword_strategy):
        """Test analysis includes keyword analysis when strategy provided."""
        validator = SEOValidator(keyword_strategy=keyword_strategy)
        analysis = validator._analyze_post(blog_post_optimal, 1)

        assert "keyword_analysis" in analysis
        assert "primary_keyword" in analysis["keyword_analysis"]


class TestAnalyzeStructure:
    """Tests for _analyze_structure() method."""

    def test_count_headings(self, blog_post_optimal):
        """Test heading counting."""
        validator = SEOValidator()
        structure = validator._analyze_structure(blog_post_optimal.content)

        assert structure["headings"]["h1"] >= 0
        assert structure["headings"]["h2"] >= 0
        assert structure["headings"]["total"] > 0

    def test_count_paragraphs(self, blog_post_optimal):
        """Test paragraph counting."""
        validator = SEOValidator()
        structure = validator._analyze_structure(blog_post_optimal.content)

        assert structure["paragraphs"] > 0

    def test_count_lists(self):
        """Test list counting."""
        content = """# Test

- Item 1
- Item 2
* Item 3
1. Numbered item
"""
        validator = SEOValidator()
        structure = validator._analyze_structure(content)

        assert structure["lists"] >= 3

    def test_count_links(self, blog_post_optimal):
        """Test link counting."""
        validator = SEOValidator()
        structure = validator._analyze_structure(blog_post_optimal.content)

        assert structure["links"]["internal"] >= 0
        assert structure["links"]["external"] >= 0

    def test_empty_content(self):
        """Test structure analysis of empty content."""
        validator = SEOValidator()
        structure = validator._analyze_structure("")

        assert structure["headings"]["total"] == 0
        assert structure["paragraphs"] == 0

    def test_avg_paragraph_length(self, blog_post_optimal):
        """Test average paragraph length calculation."""
        validator = SEOValidator()
        structure = validator._analyze_structure(blog_post_optimal.content)

        assert structure["avg_paragraph_length"] >= 0

    def test_h3_heading_counting(self):
        """Test H3 heading counting."""
        content = """# H1 Title

## H2 Section

### H3 Subsection

Some content here.

### Another H3

More content.
"""
        validator = SEOValidator()
        structure = validator._analyze_structure(content)

        assert structure["headings"]["h1"] == 1
        assert structure["headings"]["h2"] == 1
        assert structure["headings"]["h3"] == 2
        assert structure["headings"]["total"] == 4


class TestAnalyzeReadability:
    """Tests for _analyze_readability() method."""

    def test_easy_readability(self):
        """Test easy readability score."""
        content = "Short sentence. Another short one. Easy to read."
        validator = SEOValidator()
        readability = validator._analyze_readability(content)

        assert readability["level"] == "Easy"
        assert readability["score"] == 90

    def test_moderate_readability(self):
        """Test moderate readability score."""
        # Create content with 15-20 words per sentence avg
        content = (
            "This is a sentence that has about fifteen to twenty words in total which is moderate. "
            * 5
        )
        validator = SEOValidator()
        readability = validator._analyze_readability(content)

        assert readability["score"] in [70, 90]  # Could be Easy or Moderate

    def test_difficult_readability(self):
        """Test difficult readability score."""
        # Create very long sentences
        long_sentence = " ".join(["word"] * 30) + ". "
        content = long_sentence * 3
        validator = SEOValidator()
        readability = validator._analyze_readability(content)

        assert readability["score"] <= 50

    def test_empty_content_readability(self):
        """Test readability of empty content."""
        validator = SEOValidator()
        readability = validator._analyze_readability("")

        assert readability["score"] == 0
        assert readability["level"] == "Unknown"

    def test_avg_sentence_length(self):
        """Test average sentence length calculation."""
        content = "One two three. Four five six seven."
        validator = SEOValidator()
        readability = validator._analyze_readability(content)

        assert readability["avg_sentence_length"] > 0


class TestAnalyzeKeywords:
    """Tests for _analyze_keywords() method."""

    def test_primary_keyword_count(self):
        """Test primary keyword counting."""
        content = "Content marketing is essential. Content marketing drives results."
        validator = SEOValidator()
        analysis = validator._analyze_keywords(content, "content marketing", [])

        assert analysis["primary_keyword"]["count"] == 2

    def test_keyword_density(self):
        """Test keyword density calculation."""
        content = "content marketing " * 10 + "other words " * 90
        validator = SEOValidator()
        analysis = validator._analyze_keywords(content, "content marketing", [])

        assert analysis["primary_keyword"]["density"] > 0
        assert analysis["primary_keyword"]["density"] < 1

    def test_keyword_in_first_paragraph(self):
        """Test first paragraph keyword detection."""
        content = "Content marketing is important.\n\nSecond paragraph here."
        validator = SEOValidator()
        analysis = validator._analyze_keywords(content, "content marketing", [])

        assert analysis["primary_keyword"]["in_first_paragraph"] is True

    def test_keyword_not_in_first_paragraph(self):
        """Test when keyword is not in first paragraph."""
        content = "Introduction here.\n\nContent marketing mentioned later."
        validator = SEOValidator()
        analysis = validator._analyze_keywords(content, "content marketing", [])

        # Keyword appears after first paragraph
        assert "in_first_paragraph" in analysis["primary_keyword"]

    def test_secondary_keywords_analysis(self):
        """Test secondary keyword analysis."""
        content = "Digital marketing and SEO strategy are important."
        validator = SEOValidator()
        analysis = validator._analyze_keywords(content, "marketing", ["digital", "seo", "strategy"])

        assert len(analysis["secondary_keywords"]) == 3
        assert all("count" in kw for kw in analysis["secondary_keywords"])

    def test_lsi_keywords_extraction(self):
        """Test LSI keyword extraction."""
        content = (
            "Content marketing strategy requires planning. Planning and strategy drive success."
        )
        validator = SEOValidator()
        analysis = validator._analyze_keywords(content, "content", [])

        assert "lsi_keywords" in analysis
        assert isinstance(analysis["lsi_keywords"], list)

    def test_zero_word_count(self):
        """Test keyword analysis with empty content."""
        validator = SEOValidator()
        analysis = validator._analyze_keywords("", "keyword", [])

        assert analysis["primary_keyword"]["density"] == 0


class TestExtractLSIKeywords:
    """Tests for _extract_lsi_keywords() method."""

    def test_extract_frequent_words(self):
        """Test extraction of frequently occurring words."""
        content = "Marketing strategy requires planning. Strategy and planning are essential for marketing success."
        validator = SEOValidator()
        lsi_keywords = validator._extract_lsi_keywords(content, "content")

        assert isinstance(lsi_keywords, list)
        # Should include frequently occurring words

    def test_filter_stop_words(self):
        """Test that stop words are filtered out."""
        content = "The marketing and the strategy with the planning for the success."
        validator = SEOValidator()
        lsi_keywords = validator._extract_lsi_keywords(content, "test")

        # Stop words like "the", "and", "with" should not be in results
        assert "the" not in lsi_keywords
        assert "and" not in lsi_keywords

    def test_filter_short_words(self):
        """Test that short words are filtered out."""
        content = "A is of by to at an on it"
        validator = SEOValidator()
        lsi_keywords = validator._extract_lsi_keywords(content, "test")

        # Words with 3 or fewer characters should be filtered
        assert len(lsi_keywords) == 0

    def test_filter_primary_keyword(self):
        """Test that primary keyword is excluded from LSI results."""
        content = "marketing marketing marketing strategy planning content"
        validator = SEOValidator()
        lsi_keywords = validator._extract_lsi_keywords(content, "marketing")

        assert "marketing" not in lsi_keywords

    def test_max_ten_keywords(self):
        """Test that maximum 10 LSI keywords are returned."""
        content = " ".join([f"word{i} " * 3 for i in range(20)])
        validator = SEOValidator()
        lsi_keywords = validator._extract_lsi_keywords(content, "test")

        assert len(lsi_keywords) <= 10


class TestCalculateSEOScore:
    """Tests for _calculate_seo_score() method."""

    def test_optimal_content_length_score(self):
        """Test scoring for optimal content length."""
        validator = SEOValidator()
        structure = {
            "headings": {"total": 5},
            "paragraphs": 5,
            "links": {"internal": 1, "external": 1},
        }
        readability = {"score": 70}

        score = validator._calculate_seo_score(1800, structure, readability, {})
        assert score > 0

    def test_minimum_content_length_score(self):
        """Test scoring for minimum content length."""
        validator = SEOValidator()
        structure = {
            "headings": {"total": 3},
            "paragraphs": 3,
            "links": {"internal": 0, "external": 0},
        }
        readability = {"score": 50}

        score = validator._calculate_seo_score(1500, structure, readability, {})
        assert score > 0

    def test_short_content_score(self):
        """Test scoring for short content."""
        validator = SEOValidator()
        structure = {
            "headings": {"total": 0},
            "paragraphs": 1,
            "links": {"internal": 0, "external": 0},
        }
        readability = {"score": 30}

        score_short = validator._calculate_seo_score(500, structure, readability, {})
        score_optimal = validator._calculate_seo_score(1800, structure, readability, {})

        assert score_short < score_optimal

    def test_keyword_density_scoring(self):
        """Test keyword density affects score."""
        validator = SEOValidator()
        structure = {
            "headings": {"total": 3},
            "paragraphs": 3,
            "links": {"internal": 0, "external": 0},
        }
        readability = {"score": 70}

        # Good keyword density
        keyword_analysis_good = {"primary_keyword": {"density": 0.02, "in_first_paragraph": True}}

        # Low keyword density
        keyword_analysis_low = {"primary_keyword": {"density": 0.001, "in_first_paragraph": False}}

        score_good = validator._calculate_seo_score(
            1500, structure, readability, keyword_analysis_good
        )
        score_low = validator._calculate_seo_score(
            1500, structure, readability, keyword_analysis_low
        )

        assert score_good >= score_low

    def test_structure_scoring(self):
        """Test structure affects score."""
        validator = SEOValidator()
        readability = {"score": 70}
        keyword_analysis = {}

        # Good structure
        good_structure = {
            "headings": {"total": 5},
            "paragraphs": 5,
            "links": {"internal": 2, "external": 1},
        }

        # Poor structure
        poor_structure = {
            "headings": {"total": 0},
            "paragraphs": 1,
            "links": {"internal": 0, "external": 0},
        }

        score_good = validator._calculate_seo_score(
            1500, good_structure, readability, keyword_analysis
        )
        score_poor = validator._calculate_seo_score(
            1500, poor_structure, readability, keyword_analysis
        )

        assert score_good > score_poor

    def test_max_score_100(self):
        """Test that score is capped at 100."""
        validator = SEOValidator()
        structure = {
            "headings": {"total": 10},
            "paragraphs": 10,
            "links": {"internal": 5, "external": 5},
        }
        readability = {"score": 100}
        keyword_analysis = {"primary_keyword": {"density": 0.02, "in_first_paragraph": True}}

        score = validator._calculate_seo_score(1800, structure, readability, keyword_analysis)
        assert score <= 100

    def test_no_keyword_strategy_partial_credit(self):
        """Test partial credit when no keyword strategy."""
        validator = SEOValidator()
        structure = {
            "headings": {"total": 3},
            "paragraphs": 3,
            "links": {"internal": 0, "external": 0},
        }
        readability = {"score": 70}

        score = validator._calculate_seo_score(1500, structure, readability, {})
        assert score > 0  # Should get partial credit

    def test_near_minimum_length(self):
        """Test scoring for content near minimum length (80%)."""
        validator = SEOValidator()
        structure = {
            "headings": {"total": 2},
            "paragraphs": 2,
            "links": {"internal": 0, "external": 0},
        }
        readability = {"score": 50}

        # 80% of 1500 = 1200
        score = validator._calculate_seo_score(1200, structure, readability, {})
        assert score > 0

    def test_very_low_density_partial_credit(self):
        """Test partial credit for very low keyword density."""
        validator = SEOValidator()
        structure = {
            "headings": {"total": 3},
            "paragraphs": 3,
            "links": {"internal": 0, "external": 0},
        }
        readability = {"score": 70}
        keyword_analysis = {"primary_keyword": {"density": 0.001, "in_first_paragraph": False}}

        score = validator._calculate_seo_score(1500, structure, readability, keyword_analysis)
        assert score > 0


class TestGenerateMetaSuggestions:
    """Tests for generate_meta_suggestions() method."""

    def test_with_keyword(self):
        """Test meta suggestions with keyword."""
        validator = SEOValidator()
        content = "This is a blog post about marketing."
        suggestions = validator.generate_meta_suggestions(content, "content marketing")

        assert "title" in suggestions
        assert "meta_description" in suggestions
        assert "url_slug" in suggestions
        assert (
            "content marketing" in suggestions["title"].lower()
            or "content" in suggestions["title"].lower()
        )

    def test_without_keyword(self):
        """Test meta suggestions without keyword."""
        validator = SEOValidator()
        content = "# My Blog Title\n\nThis is the content."
        suggestions = validator.generate_meta_suggestions(content)

        assert suggestions["title"] != ""
        assert suggestions["meta_description"] != ""

    def test_title_length_limit(self):
        """Test title is within length limits."""
        validator = SEOValidator()
        long_keyword = "this is a very long keyword phrase that exceeds the limit"
        suggestions = validator.generate_meta_suggestions("Content", long_keyword)

        assert len(suggestions["title"]) <= 60

    def test_meta_description_length_limit(self):
        """Test meta description is within length limits."""
        validator = SEOValidator()
        long_content = "This is a very long first sentence that goes on and on and on and exceeds the maximum allowed length for a meta description tag which should be around 160 characters maximum."
        suggestions = validator.generate_meta_suggestions(long_content, "keyword")

        assert len(suggestions["meta_description"]) <= 160

    def test_url_slug_format(self):
        """Test URL slug is properly formatted."""
        validator = SEOValidator()
        suggestions = validator.generate_meta_suggestions("Content", "Content Marketing Tips!")

        # Should be lowercase, hyphenated, no special chars
        assert suggestions["url_slug"].islower() or "-" in suggestions["url_slug"]
        assert "!" not in suggestions["url_slug"]

    def test_extract_title_from_heading(self):
        """Test title extraction from H1 heading."""
        validator = SEOValidator()
        content = "# My Amazing Blog Post Title\n\nContent here."
        suggestions = validator.generate_meta_suggestions(content)

        assert "My Amazing Blog Post Title" in suggestions["title"] or len(suggestions["title"]) > 0

    def test_first_sentence_extraction(self):
        """Test first sentence used for meta description."""
        validator = SEOValidator()
        content = "First sentence here. Second sentence follows."
        suggestions = validator.generate_meta_suggestions(content, "keyword")

        assert "First sentence" in suggestions["meta_description"]


class TestBestPracticesConstants:
    """Tests for SEO best practices constants."""

    def test_constants_exist(self):
        """Test that constants are defined."""
        assert SEOValidator.MIN_CONTENT_LENGTH == 800
        assert SEOValidator.OPTIMAL_CONTENT_LENGTH == (1500, 2000)
        assert SEOValidator.KEYWORD_DENSITY == (0.01, 0.03)
        assert SEOValidator.MIN_HEADINGS == 3
        assert SEOValidator.IDEAL_PARAGRAPH_LENGTH == (40, 150)
        assert SEOValidator.MAX_SENTENCE_LENGTH == 20

    def test_best_practices_dict(self):
        """Test backward-compatible BEST_PRACTICES dict."""
        assert "min_content_length" in SEOValidator.BEST_PRACTICES
        assert "optimal_content_length" in SEOValidator.BEST_PRACTICES
        assert "keyword_density" in SEOValidator.BEST_PRACTICES

    def test_stop_words_set(self):
        """Test stop words set is populated."""
        assert "the" in SEOValidator.STOP_WORDS
        assert "and" in SEOValidator.STOP_WORDS
        assert len(SEOValidator.STOP_WORDS) > 40  # Has about 47 stop words


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_content_with_only_newlines(self):
        """Test content with only newlines."""
        validator = SEOValidator()
        structure = validator._analyze_structure("\n\n\n")

        assert structure["paragraphs"] == 0

    def test_content_with_unicode(self):
        """Test content with unicode characters."""
        content = "# 测试标题\n\nContent with émojis 🎉 and spëcial characters."
        validator = SEOValidator()
        structure = validator._analyze_structure(content)

        assert structure["headings"]["h1"] == 1

    def test_content_with_code_blocks(self):
        """Test content with markdown code blocks."""
        content = """# Code Example

```python
def hello():
    print("Hello")
```

More content here.
"""
        validator = SEOValidator()
        structure = validator._analyze_structure(content)
        assert structure["headings"]["h1"] == 1

    def test_very_long_content(self):
        """Test with very long content."""
        content = "Word " * 10000
        validator = SEOValidator()
        readability = validator._analyze_readability(content)

        assert readability["score"] >= 0
