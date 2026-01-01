"""Tests for QA validators (Phase 3)"""

import pytest

from src.models.post import Post
from src.validators.cta_validator import CTAValidator
from src.validators.hook_validator import HookValidator
from src.validators.length_validator import LengthValidator


class TestHookValidator:
    """Test cases for HookValidator"""

    def test_all_unique_hooks(self):
        """Test validation passes when all hooks are unique"""
        # Create posts with sufficient word count (minimum 50 words)
        filler = " ".join(["word"] * 50)
        posts = [
            Post(
                content=f"How do you handle content marketing?\n\n{filler}",
                template_id=1,
                template_name="Template 1",
                client_name="Test Client",
            ),
            Post(
                content=f"Most people don't understand sales.\n\n{filler}",
                template_id=2,
                template_name="Template 2",
                client_name="Test Client",
            ),
            Post(
                content=f"Building a personal brand takes courage.\n\n{filler}",
                template_id=3,
                template_name="Template 3",
                client_name="Test Client",
            ),
        ]

        validator = HookValidator(similarity_threshold=0.80)
        result = validator.validate(posts)

        assert result["passed"] is True
        assert result["uniqueness_score"] == 1.0
        assert len(result["duplicates"]) == 0
        assert len(result["issues"]) == 0

    def test_exact_duplicate_hooks(self):
        """Test validation fails when hooks are exact duplicates"""
        filler = " ".join(["word"] * 50)
        posts = [
            Post(
                content=f"Same hook here\n\n{filler}",
                template_id=1,
                template_name="Template 1",
                client_name="Test Client",
            ),
            Post(
                content=f"Same hook here\n\n{filler}",
                template_id=2,
                template_name="Template 2",
                client_name="Test Client",
            ),
        ]

        validator = HookValidator(similarity_threshold=0.80)
        result = validator.validate(posts)

        assert result["passed"] is False
        assert result["uniqueness_score"] < 1.0
        assert len(result["duplicates"]) == 1
        assert len(result["issues"]) == 1
        assert "similar hooks" in result["issues"][0]

    def test_near_duplicate_hooks(self):
        """Test validation catches near-duplicate hooks (>80% similar)"""
        filler = " ".join(["word"] * 50)
        posts = [
            Post(
                content=f"How do you handle content marketing?\n\n{filler}",
                template_id=1,
                template_name="Template 1",
                client_name="Test Client",
            ),
            Post(
                content=f"How do you handle content marketing today?\n\n{filler}",
                template_id=2,
                template_name="Template 2",
                client_name="Test Client",
            ),
        ]

        validator = HookValidator(similarity_threshold=0.80)
        result = validator.validate(posts)

        # These should be flagged as similar (>80%)
        assert result["passed"] is False
        assert len(result["duplicates"]) == 1
        assert result["duplicates"][0]["similarity"] >= 0.80

    def test_dissimilar_hooks(self):
        """Test validation passes when hooks are sufficiently different"""
        filler = " ".join(["word"] * 50)
        posts = [
            Post(
                content=f"How do you handle content marketing?\n\n{filler}",
                template_id=1,
                template_name="Template 1",
                client_name="Test Client",
            ),
            Post(
                content=f"Here's a completely different approach to sales.\n\n{filler}",
                template_id=2,
                template_name="Template 2",
                client_name="Test Client",
            ),
        ]

        validator = HookValidator(similarity_threshold=0.80)
        result = validator.validate(posts)

        assert result["passed"] is True
        assert result["uniqueness_score"] == 1.0

    def test_empty_posts(self):
        """Test validation handles empty post list gracefully"""
        posts = []

        validator = HookValidator()
        result = validator.validate(posts)

        assert result["passed"] is True
        assert result["uniqueness_score"] == 1.0

    def test_single_post(self):
        """Test validation passes with single post"""
        filler = " ".join(["word"] * 50)
        posts = [
            Post(
                content=f"Single hook\n\n{filler}",
                template_id=1,
                template_name="Template 1",
                client_name="Test Client",
            ),
        ]

        validator = HookValidator()
        result = validator.validate(posts)

        assert result["passed"] is True
        assert result["uniqueness_score"] == 1.0


class TestCTAValidator:
    """Test cases for CTAValidator"""

    def test_good_cta_variety(self):
        """Test validation passes with good CTA variety"""
        filler = " ".join(["word"] * 45)
        posts = [
            Post(
                content=f"Post 1\n\n{filler}\n\nWhat's your take on this?",
                template_id=1,
                template_name="Template 1",
                client_name="Test Client",
            ),
            Post(
                content=f"Post 2\n\n{filler}\n\nDrop a comment below.",
                template_id=2,
                template_name="Template 2",
                client_name="Test Client",
            ),
            Post(
                content=f"Post 3\n\n{filler}\n\nDM me if you're interested.",
                template_id=3,
                template_name="Template 3",
                client_name="Test Client",
            ),
            Post(
                content=f"Post 4\n\n{filler}\n\nWhat's your biggest challenge with this?",
                template_id=4,
                template_name="Template 4",
                client_name="Test Client",
            ),
        ]

        validator = CTAValidator(variety_threshold=0.40)
        result = validator.validate(posts)

        assert result["passed"] is True
        assert len(result["cta_distribution"]) >= 3  # At least 3 different types
        assert result["variety_score"] > 0.0

    def test_overused_cta(self):
        """Test validation fails when one CTA is overused"""
        # 6 out of 10 posts with same CTA pattern (60% > 40% threshold)
        filler = " ".join(["word"] * 45)
        posts = []
        for i in range(6):
            posts.append(
                Post(
                    content=f"Post {i}\n\n{filler}\n\nWhat's your take on this?",
                    template_id=i,
                    template_name=f"Template {i}",
                    client_name="Test Client",
                )
            )
        for i in range(6, 10):
            posts.append(
                Post(
                    content=f"Post {i}\n\n{filler}\n\nDrop a comment below.",
                    template_id=i,
                    template_name=f"Template {i}",
                    client_name="Test Client",
                )
            )

        validator = CTAValidator(variety_threshold=0.40)
        result = validator.validate(posts)

        assert result["passed"] is False
        assert len(result["issues"]) > 0
        assert "overused" in result["issues"][0]

    def test_missing_ctas(self):
        """Test validation detects posts without clear CTAs"""
        filler = " ".join(["word"] * 45)
        posts = [
            Post(
                content=f"Post 1\n\n{filler} This is just a statement.",
                template_id=1,
                template_name="Template 1",
                client_name="Test Client",
            ),
            Post(
                content=f"Post 2\n\n{filler} Another statement here.",
                template_id=2,
                template_name="Template 2",
                client_name="Test Client",
            ),
        ]

        validator = CTAValidator()
        result = validator.validate(posts)

        assert "missing clear CTA" in str(result["issues"])
        assert result["cta_distribution"].get("no_cta", 0) == 2

    def test_cta_pattern_detection(self):
        """Test various CTA patterns are detected correctly"""
        filler = " ".join(["word"] * 45)
        test_cases = [
            ("What's your take on this?", "question_take"),
            ("Drop your comment below", "comment_request"),
            ("DM me for details", "direct_contact"),
            ("Reply with your thoughts", "reply_request"),
            ("What's your biggest challenge?", "question_biggest"),
        ]

        for content, expected_type in test_cases:
            posts = [
                Post(
                    content=f"Hook\n\n{filler}\n\n{content}",
                    template_id=1,
                    template_name="Template 1",
                    client_name="Test Client",
                )
            ]

            validator = CTAValidator()
            result = validator.validate(posts)

            assert (
                expected_type in result["cta_distribution"]
            ), f"Failed to detect CTA type: {expected_type}"


class TestLengthValidator:
    """Test cases for LengthValidator"""

    def test_all_posts_in_optimal_range(self):
        """Test validation passes when all posts are optimal length"""
        # Create posts with varied lengths within optimal range (150-250)
        # to avoid triggering sameness detection (>70% same length)
        word_counts = [155, 175, 195, 215, 235]  # Varied within optimal range
        posts = []
        for i, wc in enumerate(word_counts):
            content = "Hook here\n\n" + " ".join(["word"] * (wc - 2))
            post = Post(
                content=content,
                template_id=i,
                template_name=f"Template {i}",
                client_name="Test Client",
            )
            post.word_count = wc  # Override word count to expected value
            posts.append(post)

        validator = LengthValidator()
        result = validator.validate(posts)

        assert result["passed"] is True
        assert result["optimal_ratio"] == 1.0
        assert len(result["issues"]) == 0

    def test_too_short_posts(self):
        """Test validation catches posts that are too short"""
        posts = [
            Post(
                content="Hook\n\n" + " ".join(["word"] * 50),  # 50 words (< 75 minimum)
                template_id=1,
                template_name="Template 1",
                client_name="Test Client",
            ),
        ]

        # Note: Post model validator will catch this, but length validator should too
        # We need to bypass model validation for this test
        posts[0].word_count = 50  # Override word count

        validator = LengthValidator(min_words=75)
        result = validator.validate(posts)

        assert result["passed"] is False
        assert any("too short" in issue for issue in result["issues"])

    def test_too_long_posts(self):
        """Test validation catches posts that are too long"""
        posts = [
            Post(
                content="Hook\n\n" + " ".join(["word"] * 375),  # 375 words (> 350 maximum)
                template_id=1,
                template_name="Template 1",
                client_name="Test Client",
            ),
        ]

        posts[0].word_count = 375  # Override

        validator = LengthValidator(max_words=350)
        result = validator.validate(posts)

        assert result["passed"] is False
        assert any("too long" in issue for issue in result["issues"])

    def test_lack_of_variety(self):
        """Test validation catches when posts lack length variety"""
        posts = []
        # Create 8 posts with exactly 150 words (80% same length)
        for i in range(8):
            posts.append(
                Post(
                    content="Hook\n\n" + " ".join(["word"] * 150),
                    template_id=i,
                    template_name=f"Template {i}",
                    client_name="Test Client",
                )
            )
        # Add 2 posts with 200 words
        for i in range(8, 10):
            posts.append(
                Post(
                    content="Hook\n\n" + " ".join(["word"] * 200),
                    template_id=i,
                    template_name=f"Template {i}",
                    client_name="Test Client",
                )
            )

        validator = LengthValidator(sameness_threshold=0.70)
        result = validator.validate(posts)

        assert result["passed"] is False
        assert any("lacks variety" in issue for issue in result["issues"])

    def test_length_distribution(self):
        """Test length distribution is calculated correctly"""
        posts = [
            Post(
                content="Hook\n\n" + " ".join(["word"] * 90),
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),  # 0-100
            Post(
                content="Hook\n\n" + " ".join(["word"] * 125),
                template_id=2,
                template_name="T2",
                client_name="Test",
            ),  # 100-150
            Post(
                content="Hook\n\n" + " ".join(["word"] * 175),
                template_id=3,
                template_name="T3",
                client_name="Test",
            ),  # 150-200
            Post(
                content="Hook\n\n" + " ".join(["word"] * 225),
                template_id=4,
                template_name="T4",
                client_name="Test",
            ),  # 200-250
            Post(
                content="Hook\n\n" + " ".join(["word"] * 275),
                template_id=5,
                template_name="T5",
                client_name="Test",
            ),  # 250-300
        ]

        for i, post in enumerate(posts):
            expected_counts = [90, 125, 175, 225, 275]
            post.word_count = expected_counts[i]

        validator = LengthValidator()
        result = validator.validate(posts)

        dist = result["length_distribution"]
        assert dist["0-100"] == 1
        assert dist["100-150"] == 1
        assert dist["150-200"] == 1
        assert dist["200-250"] == 1
        assert dist["250-300"] == 1

    def test_average_length_calculation(self):
        """Test average length is calculated correctly"""
        posts = [
            Post(
                content="Hook\n\n" + " ".join(["word"] * 100),
                template_id=1,
                template_name="T1",
                client_name="Test",
            ),
            Post(
                content="Hook\n\n" + " ".join(["word"] * 200),
                template_id=2,
                template_name="T2",
                client_name="Test",
            ),
        ]

        posts[0].word_count = 100
        posts[1].word_count = 200

        validator = LengthValidator()
        result = validator.validate(posts)

        assert result["average_length"] == 150.0


class TestQAReport:
    """Test cases for QA Report model"""

    def test_qa_report_creation(self):
        """Test QA report can be created with valid data"""
        from src.models.qa_report import QAReport

        report = QAReport(
            client_name="Test Client",
            total_posts=10,
            overall_passed=True,
            quality_score=0.95,
            hook_validation={
                "passed": True,
                "uniqueness_score": 1.0,
                "duplicates": [],
                "issues": [],
                "metric": "10/10 unique",
            },
            cta_validation={
                "passed": True,
                "variety_score": 0.9,
                "cta_distribution": {},
                "issues": [],
                "metric": "5 types",
            },
            length_validation={
                "passed": True,
                "average_length": 175.0,
                "optimal_ratio": 1.0,
                "length_distribution": {"150-200": 10},
                "issues": [],
                "metric": "10/10 optimal",
            },
            headline_validation={
                "passed": True,
                "engagement_score": 0.92,
                "average_elements": 3.5,
                "issues": [],
                "metric": "All headlines engaging",
            },
            total_issues=0,
            all_issues=[],
        )

        assert report.client_name == "Test Client"
        assert report.total_posts == 10
        assert report.overall_passed is True
        assert report.quality_score == 0.95

    def test_qa_report_markdown_generation(self):
        """Test QA report generates valid markdown"""
        from src.models.qa_report import QAReport

        report = QAReport(
            client_name="Test Client",
            total_posts=5,
            overall_passed=False,
            quality_score=0.75,
            hook_validation={
                "passed": True,
                "uniqueness_score": 1.0,
                "duplicates": [],
                "issues": [],
                "metric": "5/5 unique",
            },
            cta_validation={
                "passed": False,
                "variety_score": 0.5,
                "cta_distribution": {"no_cta": 3},
                "issues": ["3 posts missing CTA"],
                "metric": "2 types",
            },
            length_validation={
                "passed": True,
                "average_length": 175.0,
                "optimal_ratio": 0.8,
                "length_distribution": {"150-200": 4, "200-250": 1},
                "issues": [],
                "metric": "4/5 optimal",
            },
            headline_validation={
                "passed": True,
                "engagement_score": 0.85,
                "average_elements": 3.2,
                "issues": [],
                "metric": "Good engagement",
            },
            total_issues=1,
            all_issues=["3 posts missing CTA"],
        )

        markdown = report.to_markdown()

        # Check markdown contains key sections
        assert "# Quality Assurance Report" in markdown
        assert "Test Client" in markdown
        assert "Hook Uniqueness" in markdown
        assert "CTA Variety" in markdown
        assert "Post Length" in markdown
        assert "Recommendations" in markdown

    def test_qa_report_summary_string(self):
        """Test QA report summary string generation"""
        from src.models.qa_report import QAReport

        report = QAReport(
            client_name="Test Client",
            total_posts=10,
            overall_passed=True,
            quality_score=0.85,
            hook_validation={
                "passed": True,
                "uniqueness_score": 1.0,
                "duplicates": [],
                "issues": [],
                "metric": "10/10",
            },
            cta_validation={
                "passed": True,
                "variety_score": 0.7,
                "cta_distribution": {},
                "issues": [],
                "metric": "5 types",
            },
            length_validation={
                "passed": True,
                "average_length": 175.0,
                "optimal_ratio": 0.85,
                "length_distribution": {"150-200": 8, "200-250": 2},
                "issues": [],
                "metric": "8/10",
            },
            headline_validation={
                "passed": True,
                "engagement_score": 0.88,
                "average_elements": 3.8,
                "issues": [],
                "metric": "Strong headlines",
            },
            total_issues=0,
            all_issues=[],
        )

        summary = report.to_summary_string()

        assert "QA Report" in summary
        assert "PASSED" in summary or "85%" in summary
        assert "Issues: 0" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
