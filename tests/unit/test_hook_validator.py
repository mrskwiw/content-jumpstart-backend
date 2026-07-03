"""Comprehensive unit tests for HookValidator

Tests hook uniqueness detection, platform-specific length validation, and both simple and optimized algorithms.
"""

import pytest
from unittest.mock import patch

from src.models.client_brief import Platform
from src.models.post import Post
from src.validators.hook_validator import HookValidator

# Check if datasketch is available for MinHash tests
try:
    import datasketch  # noqa: F401

    DATASKETCH_AVAILABLE = True
except ImportError:
    DATASKETCH_AVAILABLE = False


@pytest.fixture
def sample_posts():
    """Create sample posts with varied hooks"""
    return [
        Post(
            content="How do you handle content marketing?\n\nBody text here.",
            template_id=1,
            template_name="Template 1",
            client_name="Test Client",
        ),
        Post(
            content="Most people don't understand sales.\n\nMore content.",
            template_id=2,
            template_name="Template 2",
            client_name="Test Client",
        ),
        Post(
            content="Building a personal brand takes courage.\n\nFinal paragraph.",
            template_id=3,
            template_name="Template 3",
            client_name="Test Client",
        ),
    ]


@pytest.fixture
def linkedin_posts():
    """Create LinkedIn posts with platform set"""
    posts = [
        Post(
            content="Short hook\n\nBody content here.",
            template_id=1,
            template_name="LinkedIn 1",
            client_name="Test",
            target_platform=Platform.LINKEDIN,
        ),
        Post(
            content="Another concise hook for LinkedIn\n\nBody.",
            template_id=2,
            template_name="LinkedIn 2",
            client_name="Test",
            target_platform=Platform.LINKEDIN,
        ),
    ]
    return posts


class TestHookValidatorInit:
    """Test HookValidator initialization"""

    def test_init_with_defaults(self):
        """Test initialization with default parameters"""
        validator = HookValidator()
        assert validator.similarity_threshold == 0.80  # Default from constants
        # use_optimized depends on whether datasketch library is available
        assert isinstance(validator.use_optimized, bool)
        assert validator.minhash_threshold == 50

    def test_init_with_custom_threshold(self):
        """Test initialization with custom similarity threshold"""
        validator = HookValidator(similarity_threshold=0.90)
        assert validator.similarity_threshold == 0.90

    def test_init_disable_optimization(self):
        """Test initialization with optimization disabled"""
        validator = HookValidator(use_optimized=False)
        assert validator.use_optimized is False

    def test_init_custom_minhash_threshold(self):
        """Test initialization with custom minhash threshold"""
        validator = HookValidator(minhash_threshold=100)
        assert validator.minhash_threshold == 100


class TestValidate:
    """Test main validate method"""

    def test_validate_all_unique(self, sample_posts):
        """Test validation passes with all unique hooks"""
        validator = HookValidator(similarity_threshold=0.80)
        result = validator.validate(sample_posts)

        assert result["passed"] is True
        assert result["uniqueness_score"] == 1.0
        assert len(result["duplicates"]) == 0
        assert len(result["issues"]) == 0
        assert result["metric"] == "3/3 unique hooks"

    def test_validate_exact_duplicates(self):
        """Test validation detects exact duplicate hooks"""
        posts = [
            Post(
                content="Same hook\n\nBody 1",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
            Post(
                content="Same hook\n\nBody 2",
                template_id=2,
                template_name="T2",
                client_name="Test",
            ),
        ]
        validator = HookValidator()
        result = validator.validate(posts)

        assert result["passed"] is False
        assert len(result["duplicates"]) == 1
        assert result["duplicates"][0]["similarity"] == 1.0
        assert "similar hooks" in result["issues"][0]

    def test_validate_near_duplicates(self):
        """Test validation detects near-duplicate hooks"""
        posts = [
            Post(
                content="How do you handle content marketing?\n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
            Post(
                content="How do you handle content marketing today?\n\nBody",
                template_id=2,
                template_name="T2",
                client_name="Test",
            ),
        ]
        validator = HookValidator(similarity_threshold=0.80)
        result = validator.validate(posts)

        assert result["passed"] is False
        assert len(result["duplicates"]) == 1
        assert result["duplicates"][0]["similarity"] >= 0.80

    def test_validate_below_threshold(self):
        """Test validation passes when similarity is below threshold"""
        posts = [
            Post(
                content="Completely different hook here\n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
            Post(
                content="Another unique opening line\n\nBody",
                template_id=2,
                template_name="T2",
                client_name="Test",
            ),
        ]
        validator = HookValidator(similarity_threshold=0.80)
        result = validator.validate(posts)

        assert result["passed"] is True
        assert len(result["duplicates"]) == 0


class TestPlatformDetection:
    """Test platform detection from posts"""

    def test_detect_platform_linkedin(self, linkedin_posts):
        """Test detects LinkedIn platform"""
        validator = HookValidator()
        platform = validator._detect_platform(linkedin_posts)
        assert platform == Platform.LINKEDIN

    def test_detect_platform_none_when_empty(self):
        """Test returns None for empty post list"""
        validator = HookValidator()
        platform = validator._detect_platform([])
        assert platform is None

    def test_detect_platform_none_when_not_set(self, sample_posts):
        """Test returns None when platform not set"""
        validator = HookValidator()
        platform = validator._detect_platform(sample_posts)
        assert platform is None

    def test_detect_platform_from_string(self):
        """Test handles platform as string (backward compatibility)"""
        post = Post(
            content="Test\n\nBody",
            template_id=1,
            template_name="T1",
            client_name="Test",
        )
        post.target_platform = "linkedin"  # String instead of enum

        validator = HookValidator()
        platform = validator._detect_platform([post])
        assert platform == Platform.LINKEDIN


class TestExtractHooks:
    """Test hook extraction from posts"""

    def test_extract_hooks_first_line(self):
        """Test extracts first line as hook"""
        posts = [
            Post(
                content="First line hook\nSecond line\nThird line",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = HookValidator()
        hooks = validator._extract_hooks(posts)
        assert hooks[0] == "First line hook"

    def test_extract_hooks_strips_whitespace(self):
        """Test strips whitespace from hooks"""
        posts = [
            Post(
                content="  Hook with spaces  \n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = HookValidator()
        hooks = validator._extract_hooks(posts)
        assert hooks[0] == "Hook with spaces"

    def test_extract_hooks_empty_content(self):
        """Test handles minimal content gracefully"""
        # Post model doesn't allow empty content, use single word
        posts = [
            Post(
                content="word",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = HookValidator()
        hooks = validator._extract_hooks(posts)
        assert hooks[0] == "word"  # Single word on first line


class TestHookLengthValidation:
    """Test platform-specific hook length validation"""

    def test_validate_hook_lengths_linkedin(self):
        """Test LinkedIn hook length validation"""
        posts = [
            Post(
                content="This is a very long LinkedIn hook that definitely exceeds the 140 character limit that we have set for LinkedIn platform hooks and should trigger a validation error\n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.LINKEDIN,
            ),
        ]
        validator = HookValidator()
        violations = validator._validate_hook_lengths(posts, Platform.LINKEDIN)
        assert len(violations) == 1
        assert violations[0]["unit"] == "characters"
        assert "too long" in violations[0]["violation"].lower()

    def test_validate_hook_lengths_twitter(self):
        """Test Twitter hook length validation"""
        posts = [
            Post(
                content="This Twitter hook is way too long and exceeds the character limit for Twitter hooks which should be concise and punchy\n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.TWITTER,
            ),
        ]
        validator = HookValidator()
        violations = validator._validate_hook_lengths(posts, Platform.TWITTER)
        assert len(violations) == 1

    def test_validate_hook_lengths_blog(self):
        """Test Blog hook length validation (word count)"""
        # Blog hooks are measured in words, not characters
        long_hook = " ".join(["word"] * 100)  # 100 words
        posts = [
            Post(
                content=f"{long_hook}\n\nBody paragraph here.",
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.BLOG,
            ),
        ]
        validator = HookValidator()
        violations = validator._validate_hook_lengths(posts, Platform.BLOG)
        assert len(violations) == 1
        assert violations[0]["unit"] == "words"

    def test_validate_hook_lengths_no_platform(self, sample_posts):
        """Test skips validation when platform not detected"""
        validator = HookValidator()
        violations = validator._validate_hook_lengths(sample_posts, None)
        assert len(violations) == 0

    def test_validate_hook_lengths_within_limits(self):
        """Test passes when hooks within platform limits"""
        posts = [
            Post(
                content="Short LinkedIn hook\n\nBody content.",
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.LINKEDIN,
            ),
        ]
        validator = HookValidator()
        violations = validator._validate_hook_lengths(posts, Platform.LINKEDIN)
        assert len(violations) == 0


class TestFindDuplicatesSimple:
    """Test simple O(n²) duplicate detection algorithm"""

    def test_find_duplicates_simple_exact_match(self):
        """Test simple algorithm detects exact duplicates"""
        posts = [
            Post(content="Same\n\nBody1", template_id=1, template_name="T1", client_name="Test"),
            Post(content="Same\n\nBody2", template_id=2, template_name="T2", client_name="Test"),
        ]
        validator = HookValidator()
        hooks = validator._extract_hooks(posts)
        duplicates = validator._find_duplicates_simple(hooks, posts)

        assert len(duplicates) == 1
        assert duplicates[0]["similarity"] == 1.0

    def test_find_duplicates_simple_no_duplicates(self, sample_posts):
        """Test simple algorithm with all unique hooks"""
        validator = HookValidator()
        hooks = validator._extract_hooks(sample_posts)
        duplicates = validator._find_duplicates_simple(hooks, sample_posts)

        assert len(duplicates) == 0

    def test_find_duplicates_simple_includes_template_info(self):
        """Test duplicate results include template information"""
        posts = [
            Post(
                content="Hook\n\nB1", template_id=1, template_name="Template A", client_name="Test"
            ),
            Post(
                content="Hook\n\nB2", template_id=2, template_name="Template B", client_name="Test"
            ),
        ]
        validator = HookValidator()
        hooks = validator._extract_hooks(posts)
        duplicates = validator._find_duplicates_simple(hooks, posts)

        assert duplicates[0]["post1_template"] == "Template A"
        assert duplicates[0]["post2_template"] == "Template B"


class TestFindDuplicatesOptimized:
    """Test optimized MinHash/LSH duplicate detection"""

    @pytest.mark.skipif(not DATASKETCH_AVAILABLE, reason="datasketch not installed")
    @patch("src.validators.hook_validator.MINHASH_AVAILABLE", True)
    @patch("src.validators.hook_validator.MinHashLSH")
    @patch("src.validators.hook_validator.MinHash")
    def test_find_duplicates_optimized_with_minhash(self, mock_minhash, mock_lsh, sample_posts):
        """Test optimized algorithm uses MinHash when available"""
        validator = HookValidator(use_optimized=True)
        hooks = validator._extract_hooks(sample_posts)

        # Call optimized method
        validator._find_duplicates_optimized(hooks, sample_posts)

        # MinHashLSH should be initialized
        assert mock_lsh.called

    @patch("src.validators.hook_validator.MINHASH_AVAILABLE", False)
    def test_find_duplicates_optimized_fallback(self, sample_posts):
        """Test optimized algorithm falls back to simple when MinHash unavailable"""
        validator = HookValidator(use_optimized=True)
        hooks = validator._extract_hooks(sample_posts)

        # Should fall back to simple algorithm
        duplicates = validator._find_duplicates_optimized(hooks, sample_posts)
        assert isinstance(duplicates, list)

    def test_find_duplicates_uses_optimized_for_large_datasets(self):
        """Test uses optimized algorithm for large datasets"""
        # Create 60 posts (above minhash_threshold of 50)
        posts = [
            Post(
                content=f"Unique hook {i}\n\nBody {i}",
                template_id=i,
                template_name=f"T{i}",
                client_name="Test",
            )
            for i in range(60)
        ]

        validator = HookValidator(use_optimized=True, minhash_threshold=50)
        hooks = validator._extract_hooks(posts)

        # Should use optimized algorithm (won't verify MinHash internals, just that it runs)
        duplicates = validator._find_duplicates(hooks, posts)
        assert isinstance(duplicates, list)

    def test_find_duplicates_uses_simple_for_small_datasets(self, sample_posts):
        """Test uses simple algorithm for small datasets"""
        validator = HookValidator(use_optimized=True, minhash_threshold=50)
        hooks = validator._extract_hooks(sample_posts)

        # 3 posts < 50 threshold, should use simple
        with patch.object(validator, "_find_duplicates_simple") as mock_simple:
            mock_simple.return_value = []
            validator._find_duplicates(hooks, sample_posts)
            mock_simple.assert_called_once()


class TestCalculateSimilarity:
    """Test similarity calculation"""

    def test_calculate_similarity_identical(self):
        """Test identical strings have 100% similarity"""
        validator = HookValidator()
        similarity = validator._calculate_similarity("Same text", "Same text")
        assert similarity == 1.0

    def test_calculate_similarity_completely_different(self):
        """Test completely different strings have low similarity"""
        validator = HookValidator()
        similarity = validator._calculate_similarity("Hello world", "Goodbye universe")
        assert similarity < 0.5

    def test_calculate_similarity_case_insensitive(self):
        """Test similarity is case-insensitive"""
        validator = HookValidator()
        similarity = validator._calculate_similarity("Hello World", "hello world")
        assert similarity == 1.0

    def test_calculate_similarity_partial_match(self):
        """Test partial matches return moderate similarity"""
        validator = HookValidator()
        similarity = validator._calculate_similarity(
            "How do you handle content marketing?", "How do you handle content?"
        )
        assert 0.7 < similarity < 1.0


class TestValidateIntegration:
    """Test validate method integration with all features"""

    def test_validate_with_platform_linkedin(self):
        """Test validation includes platform-specific checks for LinkedIn"""
        posts = [
            Post(
                content="Good hook\n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.LINKEDIN,
            ),
            Post(
                content="Another hook\n\nBody",
                template_id=2,
                template_name="T2",
                client_name="Test",
                target_platform=Platform.LINKEDIN,
            ),
        ]
        validator = HookValidator()
        result = validator.validate(posts)

        assert result["platform"] == "linkedin"
        assert "LinkedIn" in result["metric"] or "unique hooks" in result["metric"]

    def test_validate_combines_uniqueness_and_length_issues(self):
        """Test validation combines both uniqueness and length violations"""
        long_hook = "x" * 200  # Exceeds LinkedIn 140 char limit
        posts = [
            Post(
                content=f"{long_hook}\n\nBody1",
                template_id=1,
                template_name="T1",
                client_name="Test",
                target_platform=Platform.LINKEDIN,
            ),
            Post(
                content=f"{long_hook}\n\nBody2",  # Same long hook = duplicate
                template_id=2,
                template_name="T2",
                client_name="Test",
                target_platform=Platform.LINKEDIN,
            ),
        ]
        validator = HookValidator()
        result = validator.validate(posts)

        # Should fail for both uniqueness AND length
        assert result["passed"] is False
        assert len(result["duplicates"]) == 1  # Same hooks
        assert len(result["hook_length_issues"]) == 2  # Both too long
        assert len(result["issues"]) >= 3  # At least 1 dup + 2 length issues

    def test_validate_returns_all_fields(self, sample_posts):
        """Test validation result contains all expected fields"""
        validator = HookValidator()
        result = validator.validate(sample_posts)

        # Check all expected fields present
        assert "passed" in result
        assert "duplicates" in result
        assert "uniqueness_score" in result
        assert "hook_length_issues" in result
        assert "issues" in result
        assert "metric" in result
        assert "platform" in result


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_validate_empty_posts_list(self):
        """Test validation with empty posts list"""
        validator = HookValidator()
        result = validator.validate([])

        assert result["passed"] is True
        assert result["uniqueness_score"] == 1.0
        assert len(result["duplicates"]) == 0

    def test_validate_single_post(self):
        """Test validation with single post"""
        posts = [
            Post(
                content="Single post\n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = HookValidator()
        result = validator.validate(posts)

        assert result["passed"] is True
        assert result["uniqueness_score"] == 1.0

    def test_validate_posts_with_multiline_hooks(self):
        """Test handles posts where hook might span multiple lines"""
        posts = [
            Post(
                content="First line only\nSecond line\n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
        ]
        validator = HookValidator()
        hooks = validator._extract_hooks(posts)
        # Should only extract first line
        assert hooks[0] == "First line only"
        assert "Second line" not in hooks[0]

    def test_validate_posts_with_special_characters(self):
        """Test handles hooks with special characters"""
        posts = [
            Post(
                content="Hook with émojis 🚀 and spëcial çhars!\n\nBody",
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
            Post(
                content="Different hook 你好 世界\n\nBody",
                template_id=2,
                template_name="T2",
                client_name="Test",
            ),
        ]
        validator = HookValidator()
        result = validator.validate(posts)

        # Should handle gracefully without errors
        assert isinstance(result, dict)
        assert "passed" in result


class TestScaffoldPatterns:
    """Tests for _check_scaffold_patterns — GEN-07"""

    def _make_post(self, content: str, template_id: int = 1) -> Post:
        return Post(
            content=content,
            template_id=template_id,
            template_name=f"Template {template_id}",
            client_name="Test Client",
        )

    def test_patient_anecdote_scaffold_regression(self):
        """Existing patient-anecdote pattern still detected."""
        validator = HookValidator()
        posts = [
            self._make_post(
                "Some hook.\n\nOne patient told us last month that scheduling was hard."
            ),
            self._make_post(
                "Another hook.\n\nOne patient told us recently they dreaded appointments."
            ),
        ]
        scaffolds = validator._check_scaffold_patterns(posts)
        names = [s["scaffold"] for s in scaffolds]
        assert "patient-anecdote scaffold" in names

    def test_fax_machine_analogy_flagged(self):
        """Two posts using 'fax machine' are flagged."""
        validator = HookValidator()
        posts = [
            self._make_post("Hook.\n\nUsing old software is like using a fax machine in 2025."),
            self._make_post(
                "Hook 2.\n\nRelying on spreadsheets is like keeping a fax machine around."
            ),
        ]
        scaffolds = validator._check_scaffold_patterns(posts)
        names = [s["scaffold"] for s in scaffolds]
        assert "fax-machine analogy" in names

    def test_fax_machine_single_use_not_flagged(self):
        """Single use of 'fax machine' does not trigger the flag."""
        validator = HookValidator()
        posts = [
            self._make_post("Hook.\n\nUsing old software is like using a fax machine."),
            self._make_post("Hook 2.\n\nCompletely different content here."),
        ]
        scaffolds = validator._check_scaffold_patterns(posts)
        names = [s["scaffold"] for s in scaffolds]
        assert "fax-machine analogy" not in names

    def test_monday_morning_scaffold_flagged(self):
        """Two posts with 'Monday morning hunting' pattern are flagged."""
        validator = HookValidator()
        posts = [
            self._make_post("Hook.\n\nEvery Monday morning spent hunting for the right contacts."),
            self._make_post("Hook 2.\n\nMonday mornings chasing invoices across three tools."),
        ]
        scaffolds = validator._check_scaffold_patterns(posts)
        names = [s["scaffold"] for s in scaffolds]
        assert "Monday-morning testimonial" in names

    def test_dollar_figure_anecdote_flagged(self):
        """Two posts with dollar-figure stuck-in-inbox pattern are flagged."""
        validator = HookValidator()
        posts = [
            self._make_post("Hook.\n\nA $50K contract sitting in someone's inbox for two weeks."),
            self._make_post("Hook 2.\n\nAnother $200K deal stuck waiting on a reply."),
        ]
        scaffolds = validator._check_scaffold_patterns(posts)
        names = [s["scaffold"] for s in scaffolds]
        assert "dollar-figure stuck-in-inbox anecdote" in names

    def test_full_body_scan_catches_mid_post_scaffold(self):
        """Scaffold appearing after the first 400 characters is still detected."""
        validator = HookValidator()
        # Pad first 450+ chars before the scaffold trigger
        padding = "A " * 230  # ~460 characters of filler
        posts = [
            self._make_post(f"Hook one.\n\n{padding}\n\nfax machine still in the office."),
            self._make_post(f"Hook two.\n\n{padding}\n\nRunning on a fax machine mentality."),
        ]
        scaffolds = validator._check_scaffold_patterns(posts)
        names = [s["scaffold"] for s in scaffolds]
        assert "fax-machine analogy" in names

    def test_no_false_positives_on_clean_posts(self):
        """Clean 300-word LinkedIn posts produce no scaffold flags."""
        validator = HookValidator()
        clean_content = (
            "Here is a compelling hook about operations efficiency.\n\n"
            + "Operations teams waste enormous time on manual data entry. " * 20
            + "\n\nBook a call to learn more."
        )
        posts = [self._make_post(clean_content, i) for i in range(1, 6)]
        scaffolds = validator._check_scaffold_patterns(posts)
        assert scaffolds == []
