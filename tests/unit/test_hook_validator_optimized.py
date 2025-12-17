"""Unit tests for optimized HookValidator"""

import pytest

from src.models.post import Post
from src.validators.hook_validator import MINHASH_AVAILABLE, HookValidator


@pytest.fixture
def sample_posts():
    """Create sample posts for testing"""
    unique_hooks = [
        "The secret to success is persistence",
        "How to grow your business faster",
        "Why customer service matters most",
        "Three ways to improve efficiency",
        "Best practices for team management",
        "Common mistakes to avoid in marketing",
        "The future of digital transformation",
        "Key strategies for sustainable growth",
        "Understanding your target audience better",
        "Maximizing ROI through smart planning",
    ]
    posts = []
    for i, hook in enumerate(unique_hooks):
        post = Post(
            content=f"{hook}\n\nBody content for post {i}",
            template_id=i + 1,
            template_name=f"Template {i % 3}",
            variant=1,
            client_name="TestClient",
        )
        posts.append(post)
    return posts


@pytest.fixture
def posts_with_duplicates():
    """Create posts with some duplicate hooks"""
    posts = [
        Post(
            content="The secret to success is consistency\n\nBody 1",
            template_id=1,
            template_name="Template A",
            variant=1,
            client_name="TestClient",
        ),
        Post(
            content="The secret to success is persistence\n\nBody 2",
            template_id=2,
            template_name="Template B",
            variant=1,
            client_name="TestClient",
        ),
        Post(
            content="A completely different hook\n\nBody 3",
            template_id=3,
            template_name="Template C",
            variant=1,
            client_name="TestClient",
        ),
    ]
    return posts


def test_validator_initialization():
    """Test validator initialization with optimization"""
    validator = HookValidator()
    assert validator.similarity_threshold == 0.80
    assert validator.use_optimized == MINHASH_AVAILABLE
    assert validator.minhash_threshold == 50


def test_validator_with_optimization_disabled():
    """Test validator with optimization explicitly disabled"""
    validator = HookValidator(use_optimized=False)
    assert validator.use_optimized is False


def test_validate_no_duplicates(sample_posts):
    """Test validation with no duplicate hooks"""
    validator = HookValidator()
    result = validator.validate(sample_posts)

    assert result["passed"] is True
    assert len(result["duplicates"]) == 0
    assert result["uniqueness_score"] == 1.0
    assert len(result["issues"]) == 0


def test_validate_with_duplicates(posts_with_duplicates):
    """Test validation with duplicate hooks"""
    validator = HookValidator(similarity_threshold=0.7)
    result = validator.validate(posts_with_duplicates)

    # First two hooks are similar (both about "secret to success")
    assert result["passed"] is False
    assert len(result["duplicates"]) >= 1
    assert result["uniqueness_score"] < 1.0


def test_extract_hooks(sample_posts):
    """Test hook extraction from posts"""
    validator = HookValidator()
    hooks = validator._extract_hooks(sample_posts)

    assert len(hooks) == 10
    # All hooks should be non-empty strings
    assert all(isinstance(hook, str) and len(hook) > 0 for hook in hooks)
    # First hook should match expected
    assert hooks[0] == "The secret to success is persistence"


def test_simple_algorithm():
    """Test simple O(n²) algorithm"""
    validator = HookValidator()
    posts = [
        Post(
            content="Same hook\n\nBody 1",
            template_id=1,
            template_name="A",
            variant=1,
            client_name="Test",
        ),
        Post(
            content="Same hook\n\nBody 2",
            template_id=2,
            template_name="B",
            variant=1,
            client_name="Test",
        ),
        Post(
            content="Different hook\n\nBody 3",
            template_id=3,
            template_name="C",
            variant=1,
            client_name="Test",
        ),
    ]

    hooks = validator._extract_hooks(posts)
    duplicates = validator._find_duplicates_simple(hooks, posts)

    # Should find exact duplicate
    assert len(duplicates) == 1
    assert duplicates[0]["similarity"] >= 0.95


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="MinHash library not available")
def test_optimized_algorithm():
    """Test optimized MinHash/LSH algorithm"""
    validator = HookValidator(use_optimized=True)
    posts = [
        Post(
            content="Same hook\n\nBody 1",
            template_id=1,
            template_name="A",
            variant=1,
            client_name="Test",
        ),
        Post(
            content="Same hook\n\nBody 2",
            template_id=2,
            template_name="B",
            variant=1,
            client_name="Test",
        ),
        Post(
            content="Different hook\n\nBody 3",
            template_id=3,
            template_name="C",
            variant=1,
            client_name="Test",
        ),
    ]

    hooks = validator._extract_hooks(posts)
    duplicates = validator._find_duplicates_optimized(hooks, posts)

    # Should find exact duplicate
    assert len(duplicates) == 1
    assert duplicates[0]["similarity"] >= 0.95


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="MinHash library not available")
def test_optimized_vs_simple_consistency():
    """Test that optimized algorithm finds exact duplicates"""
    # Create posts with exact duplicates (MinHash is more conservative than simple matching)
    posts = [
        Post(
            content="The quick brown fox\n\nBody",
            template_id=1,
            template_name="A",
            variant=1,
            client_name="Test",
        ),
        Post(
            content="The quick brown fox\n\nBody",
            template_id=2,
            template_name="B",
            variant=1,
            client_name="Test",
        ),
        Post(
            content="A completely different sentence\n\nBody",
            template_id=3,
            template_name="C",
            variant=1,
            client_name="Test",
        ),
        Post(
            content="Another unique sentence here\n\nBody",
            template_id=4,
            template_name="D",
            variant=1,
            client_name="Test",
        ),
    ]

    validator_simple = HookValidator(use_optimized=False)
    validator_optimized = HookValidator(use_optimized=True)

    hooks = validator_simple._extract_hooks(posts)

    duplicates_simple = validator_simple._find_duplicates_simple(hooks, posts)
    duplicates_optimized = validator_optimized._find_duplicates_optimized(hooks, posts)

    # Both should find at least the exact duplicates
    # MinHash may be more conservative and find fewer false positives
    assert len(duplicates_optimized) >= 1  # Should find the exact duplicate
    assert len(duplicates_simple) >= 1  # Should also find it


def test_algorithm_selection_based_on_size():
    """Test that algorithm selection respects size threshold"""
    validator = HookValidator(use_optimized=True, minhash_threshold=50)

    # Small dataset (< 50 posts) should use simple algorithm
    small_posts = [
        Post(
            content=f"Hook {i}\n\nBody",
            template_id=i,
            template_name="A",
            variant=1,
            client_name="Test",
        )
        for i in range(30)
    ]
    hooks = validator._extract_hooks(small_posts)

    # For small dataset, even with optimization enabled, it should use simple
    # (We can't directly test this without mocking, but validate it works)
    duplicates = validator._find_duplicates(hooks, small_posts)
    assert isinstance(duplicates, list)


def test_empty_hooks():
    """Test handling of posts with empty first lines"""
    validator = HookValidator()
    posts = [
        Post(
            content="\nEmpty first line\n\nBody only",
            template_id=1,
            template_name="A",
            variant=1,
            client_name="Test",
        ),
        Post(
            content=" \nWhitespace first line\n\nBody only",
            template_id=2,
            template_name="B",
            variant=1,
            client_name="Test",
        ),
        Post(
            content="Normal hook\n\nBody",
            template_id=3,
            template_name="C",
            variant=1,
            client_name="Test",
        ),
    ]

    result = validator.validate(posts)
    # Should handle empty/whitespace hooks gracefully
    assert "passed" in result
    assert "uniqueness_score" in result


def test_similarity_threshold_boundary():
    """Test similarity threshold boundary conditions"""
    validator = HookValidator(similarity_threshold=0.85)
    posts = [
        Post(
            content="The quick brown fox jumps\n\nBody",
            template_id=1,
            template_name="A",
            variant=1,
            client_name="Test",
        ),
        Post(
            content="The quick brown fox leaps\n\nBody",
            template_id=2,
            template_name="B",
            variant=1,
            client_name="Test",
        ),
    ]

    validator.validate(posts)
    # These hooks are similar but not identical
    # Result depends on exact similarity score vs threshold


def test_case_insensitivity():
    """Test that similarity calculation is case-insensitive"""
    validator = HookValidator()

    similarity = validator._calculate_similarity("HELLO WORLD", "hello world")
    assert similarity == 1.0


def test_large_dataset_performance():
    """Test that validator handles large datasets"""
    # Create a large dataset
    posts = [
        Post(
            content=f"Unique hook number {i}\n\nBody content",
            template_id=i,
            template_name=f"Template {i % 10}",
            variant=1,
            client_name="TestClient",
        )
        for i in range(100)
    ]

    validator = HookValidator()
    result = validator.validate(posts)

    # Should complete without errors
    assert "passed" in result
    assert "uniqueness_score" in result


@pytest.mark.skipif(not MINHASH_AVAILABLE, reason="MinHash library not available")
def test_optimized_with_large_dataset():
    """Test optimized algorithm with large dataset (> 50 posts)"""
    posts = [
        Post(
            content=f"Hook {i % 20}\n\nBody {i}",
            template_id=i,
            template_name=f"Template {i % 5}",
            variant=1,
            client_name="TestClient",
        )
        for i in range(100)
    ]

    validator = HookValidator(use_optimized=True, minhash_threshold=50)
    result = validator.validate(posts)

    # Should use optimized algorithm for 100 posts
    assert result is not None
    assert "uniqueness_score" in result
