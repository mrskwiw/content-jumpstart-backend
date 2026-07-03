"""Unit tests for QA Report model"""

import pytest
from datetime import datetime
from src.models.qa_report import QAReport


class TestQAReport:
    """Test suite for QAReport model"""

    @pytest.fixture
    def sample_hook_validation(self):
        """Sample hook validation results"""
        return {
            "passed": True,
            "uniqueness_score": 0.92,
            "metric": "92% unique hooks (23/25 posts)",
            "issues": [],
        }

    @pytest.fixture
    def sample_cta_validation(self):
        """Sample CTA validation results"""
        return {
            "passed": True,
            "variety_score": 0.65,
            "metric": "65% CTA variety (5/8 unique CTAs)",
            "cta_distribution": {
                "question": 10,
                "engagement": 8,
                "action": 7,
                "sharing": 5,
            },
            "issues": [],
        }

    @pytest.fixture
    def sample_length_validation(self):
        """Sample length validation results"""
        return {
            "passed": True,
            "average_length": 185,
            "metric": "Average 185 words (optimal range)",
            "optimal_ratio": 0.88,
            "length_distribution": {
                "150-200": 15,
                "200-250": 10,
                "100-150": 3,
                "250-300": 2,
            },
            "issues": [],
        }

    @pytest.fixture
    def sample_headline_validation(self):
        """Sample headline validation results"""
        return {
            "passed": True,
            "average_elements": 3.8,
            "metric": "Average 3.8 engagement elements per headline",
            "issues": [],
        }

    @pytest.fixture
    def sample_keyword_validation(self):
        """Sample keyword validation results"""
        return {
            "passed": True,
            "primary_usage_ratio": 0.87,
            "metric": "87% primary keyword usage (26/30 posts)",
            "issues": [],
        }

    @pytest.fixture
    def passing_qa_report(
        self,
        sample_hook_validation,
        sample_cta_validation,
        sample_length_validation,
        sample_headline_validation,
    ):
        """Sample QA report with all validators passing"""
        return QAReport(
            client_name="Test Client",
            total_posts=30,
            overall_passed=True,
            quality_score=0.92,
            hook_validation=sample_hook_validation,
            cta_validation=sample_cta_validation,
            length_validation=sample_length_validation,
            headline_validation=sample_headline_validation,
            total_issues=0,
            all_issues=[],
        )

    @pytest.fixture
    def failing_qa_report(
        self,
        sample_cta_validation,
        sample_length_validation,
        sample_headline_validation,
    ):
        """Sample QA report with hook validation failing"""
        return QAReport(
            client_name="Test Client",
            total_posts=30,
            overall_passed=False,
            quality_score=0.68,
            hook_validation={
                "passed": False,
                "uniqueness_score": 0.65,
                "metric": "65% unique hooks (below 80% threshold)",
                "issues": [
                    "Duplicate hooks found: Posts #3 and #12",
                    "Duplicate hooks found: Posts #7 and #18",
                ],
            },
            cta_validation=sample_cta_validation,
            length_validation=sample_length_validation,
            headline_validation=sample_headline_validation,
            total_issues=2,
            all_issues=[
                "Duplicate hooks found: Posts #3 and #12",
                "Duplicate hooks found: Posts #7 and #18",
            ],
        )

    def test_qa_report_initialization(self, passing_qa_report):
        """Test QA report can be initialized with valid data"""
        assert passing_qa_report.client_name == "Test Client"
        assert passing_qa_report.total_posts == 30
        assert passing_qa_report.overall_passed is True
        assert passing_qa_report.quality_score == 0.92
        assert passing_qa_report.total_issues == 0

    def test_qa_report_default_timestamp(self):
        """Test generated_at defaults to current timestamp"""
        report = QAReport(
            client_name="Test",
            total_posts=30,
            overall_passed=True,
            quality_score=0.9,
            hook_validation={
                "passed": True,
                "uniqueness_score": 0.9,
                "metric": "test",
                "issues": [],
            },
            cta_validation={"passed": True, "variety_score": 0.9, "metric": "test", "issues": []},
            length_validation={
                "passed": True,
                "average_length": 200,
                "metric": "test",
                "optimal_ratio": 0.9,
                "length_distribution": {},
                "issues": [],
            },
            headline_validation={
                "passed": True,
                "average_elements": 3.5,
                "metric": "test",
                "issues": [],
            },
        )
        assert isinstance(report.generated_at, datetime)
        # Should be recent (within last minute)
        time_diff = (datetime.now() - report.generated_at).total_seconds()
        assert time_diff < 60

    def test_qa_report_with_keyword_validation(
        self,
        sample_hook_validation,
        sample_cta_validation,
        sample_length_validation,
        sample_headline_validation,
        sample_keyword_validation,
    ):
        """Test QA report with optional keyword validation"""
        report = QAReport(
            client_name="Test Client",
            total_posts=30,
            overall_passed=True,
            quality_score=0.92,
            hook_validation=sample_hook_validation,
            cta_validation=sample_cta_validation,
            length_validation=sample_length_validation,
            headline_validation=sample_headline_validation,
            keyword_validation=sample_keyword_validation,
        )
        assert report.keyword_validation is not None
        assert report.keyword_validation["passed"] is True

    def test_to_markdown_passing_report(self, passing_qa_report):
        """Test markdown generation for passing report"""
        markdown = passing_qa_report.to_markdown()

        # Check header
        assert "# Quality Assurance Report" in markdown
        assert "**Client:** Test Client" in markdown
        assert "**Posts Validated:** 30" in markdown

        # Check status
        assert "## Overall Status: [PASS]" in markdown
        assert "**Quality Score:** 92.0%" in markdown
        assert "**Total Issues:** 0" in markdown

        # Check sections
        assert "## Hook Uniqueness" in markdown
        assert "## CTA Variety" in markdown
        assert "## Post Length" in markdown
        assert "## Headline Engagement (SEO Best Practices)" in markdown

        # Check validator results
        assert "[PASS] PASSED" in markdown
        assert "**Uniqueness Score:** 92.0%" in markdown
        assert "**Variety Score:** 65.0%" in markdown

        # Should not have recommendations section for passing report
        assert "## Recommendations" not in markdown

    def test_to_markdown_failing_report(self, failing_qa_report):
        """Test markdown generation for failing report"""
        markdown = failing_qa_report.to_markdown()

        # Check warning status
        assert "## Overall Status: [WARN]" in markdown
        assert "**Quality Score:** 68.0%" in markdown
        assert "**Total Issues:** 2" in markdown

        # Check issues listed
        assert "Duplicate hooks found: Posts #3 and #12" in markdown
        assert "Duplicate hooks found: Posts #7 and #18" in markdown

        # Should have recommendations section
        assert "## Recommendations" in markdown
        assert "**Hook Uniqueness:** Review duplicate hooks and revise for uniqueness" in markdown

    def test_to_markdown_with_keyword_validation(
        self,
        sample_hook_validation,
        sample_cta_validation,
        sample_length_validation,
        sample_headline_validation,
        sample_keyword_validation,
    ):
        """Test markdown includes keyword validation when present"""
        report = QAReport(
            client_name="Test Client",
            total_posts=30,
            overall_passed=True,
            quality_score=0.92,
            hook_validation=sample_hook_validation,
            cta_validation=sample_cta_validation,
            length_validation=sample_length_validation,
            headline_validation=sample_headline_validation,
            keyword_validation=sample_keyword_validation,
        )
        markdown = report.to_markdown()

        assert "## SEO Keyword Usage" in markdown
        assert "**Primary Usage Ratio:** 87.0%" in markdown
        assert "*Note: Keywords should be integrated naturally, not forced*" in markdown

    def test_to_markdown_cta_distribution(self, passing_qa_report):
        """Test CTA distribution is rendered correctly"""
        markdown = passing_qa_report.to_markdown()

        # Check distribution section
        assert "**Distribution:**" in markdown
        assert "question: 10 posts" in markdown
        assert "engagement: 8 posts" in markdown
        # Verify all CTAs are present (sorted by count descending)
        assert "action: 7 posts" in markdown
        assert "sharing: 5 posts" in markdown

    def test_to_markdown_length_distribution(self, passing_qa_report):
        """Test length distribution is rendered correctly"""
        markdown = passing_qa_report.to_markdown()

        assert "150-200 words: 15 posts" in markdown
        assert "200-250 words: 10 posts" in markdown
        assert "100-150 words: 3 posts" in markdown
        assert "250-300 words: 2 posts" in markdown

    def test_to_summary_string_passing(self, passing_qa_report):
        """Test summary string for passing report"""
        summary = passing_qa_report.to_summary_string()

        assert "[PASS] PASSED" in summary
        assert "Quality: 92%" in summary
        assert "Issues: 0" in summary

    def test_to_summary_string_failing(self, failing_qa_report):
        """Test summary string for failing report"""
        summary = failing_qa_report.to_summary_string()

        assert "[WARN] NEEDS REVIEW" in summary
        assert "Quality: 68%" in summary
        assert "Issues: 2" in summary

    def test_empty_issues_list(self):
        """Test report with empty issues"""
        report = QAReport(
            client_name="Test",
            total_posts=30,
            overall_passed=True,
            quality_score=0.95,
            hook_validation={
                "passed": True,
                "uniqueness_score": 0.95,
                "metric": "test",
                "issues": [],
            },
            cta_validation={
                "passed": True,
                "variety_score": 0.95,
                "metric": "test",
                "cta_distribution": {},
                "issues": [],
            },
            length_validation={
                "passed": True,
                "average_length": 200,
                "metric": "test",
                "optimal_ratio": 0.95,
                "length_distribution": {},
                "issues": [],
            },
            headline_validation={
                "passed": True,
                "average_elements": 4.0,
                "metric": "test",
                "issues": [],
            },
            total_issues=0,
            all_issues=[],
        )
        markdown = report.to_markdown()

        # Issues section should not show empty bullet points
        assert "**Issues:**\n\n" not in markdown

    def test_multiple_validator_failures(self):
        """Test report with multiple validators failing"""
        report = QAReport(
            client_name="Test Client",
            total_posts=30,
            overall_passed=False,
            quality_score=0.55,
            hook_validation={
                "passed": False,
                "uniqueness_score": 0.65,
                "metric": "65% unique",
                "issues": ["Hook issue 1"],
            },
            cta_validation={
                "passed": False,
                "variety_score": 0.30,
                "metric": "30% variety",
                "cta_distribution": {},
                "issues": ["CTA issue 1"],
            },
            length_validation={
                "passed": False,
                "average_length": 350,
                "metric": "350 words (too long)",
                "optimal_ratio": 0.45,
                "length_distribution": {},
                "issues": ["Length issue 1"],
            },
            headline_validation={
                "passed": False,
                "average_elements": 1.5,
                "metric": "1.5 elements",
                "issues": ["Headline issue 1"],
            },
            total_issues=4,
            all_issues=["Hook issue 1", "CTA issue 1", "Length issue 1", "Headline issue 1"],
        )

        markdown = report.to_markdown()

        # All recommendations should appear
        assert "**Hook Uniqueness:** Review duplicate hooks and revise for uniqueness" in markdown
        assert "**CTA Variety:** Diversify call-to-action patterns across posts" in markdown
        assert "**Length:** Adjust post lengths to optimal range (150-250 words)" in markdown
        assert "**Headline Engagement:**" in markdown

    def test_custom_timestamp(self):
        """Test QA report with custom timestamp"""
        custom_time = datetime(2025, 1, 15, 10, 30, 0)
        report = QAReport(
            client_name="Test",
            total_posts=30,
            overall_passed=True,
            quality_score=0.9,
            hook_validation={
                "passed": True,
                "uniqueness_score": 0.9,
                "metric": "test",
                "issues": [],
            },
            cta_validation={
                "passed": True,
                "variety_score": 0.9,
                "metric": "test",
                "cta_distribution": {},
                "issues": [],
            },
            length_validation={
                "passed": True,
                "average_length": 200,
                "metric": "test",
                "optimal_ratio": 0.9,
                "length_distribution": {},
                "issues": [],
            },
            headline_validation={
                "passed": True,
                "average_elements": 3.5,
                "metric": "test",
                "issues": [],
            },
            generated_at=custom_time,
        )

        assert report.generated_at == custom_time
        markdown = report.to_markdown()
        assert "**Generated:** 2025-01-15 10:30:00" in markdown

    def test_edge_case_zero_posts(self):
        """Test report with zero posts (edge case)"""
        report = QAReport(
            client_name="Test",
            total_posts=0,
            overall_passed=True,
            quality_score=0.0,
            hook_validation={
                "passed": True,
                "uniqueness_score": 0.0,
                "metric": "N/A",
                "issues": [],
            },
            cta_validation={
                "passed": True,
                "variety_score": 0.0,
                "metric": "N/A",
                "cta_distribution": {},
                "issues": [],
            },
            length_validation={
                "passed": True,
                "average_length": 0,
                "metric": "N/A",
                "optimal_ratio": 0.0,
                "length_distribution": {},
                "issues": [],
            },
            headline_validation={
                "passed": True,
                "average_elements": 0.0,
                "metric": "N/A",
                "issues": [],
            },
        )

        assert report.total_posts == 0
        markdown = report.to_markdown()
        assert "**Posts Validated:** 0" in markdown

    def test_quality_score_formatting(self):
        """Test quality score is formatted correctly in all outputs"""
        report = QAReport(
            client_name="Test",
            total_posts=30,
            overall_passed=True,
            quality_score=0.8765,  # Test decimal precision
            hook_validation={
                "passed": True,
                "uniqueness_score": 0.9,
                "metric": "test",
                "issues": [],
            },
            cta_validation={
                "passed": True,
                "variety_score": 0.9,
                "metric": "test",
                "cta_distribution": {},
                "issues": [],
            },
            length_validation={
                "passed": True,
                "average_length": 200,
                "metric": "test",
                "optimal_ratio": 0.9,
                "length_distribution": {},
                "issues": [],
            },
            headline_validation={
                "passed": True,
                "average_elements": 3.5,
                "metric": "test",
                "issues": [],
            },
        )

        markdown = report.to_markdown()
        summary = report.to_summary_string()

        # Markdown should show 1 decimal place percentage (87.65% rounds to 87.7%)
        assert "87.6%" in markdown or "87.7%" in markdown

        # Summary should show no decimal places (rounds to 88%)
        assert "88%" in summary or "87%" in summary

    def test_validator_score_formatting(self, passing_qa_report):
        """Test validator scores are formatted with 1 decimal place"""
        markdown = passing_qa_report.to_markdown()

        # All scores should have 1 decimal place
        assert "92.0%" in markdown  # uniqueness_score
        assert "65.0%" in markdown  # variety_score
        assert "88.0%" in markdown  # optimal_ratio

    def test_keyword_validation_with_issues(
        self,
        sample_hook_validation,
        sample_cta_validation,
        sample_length_validation,
        sample_headline_validation,
    ):
        """Test markdown includes keyword validation issues (lines 156-160)."""
        keyword_validation_with_issues = {
            "passed": False,
            "primary_usage_ratio": 0.45,
            "metric": "45% primary keyword usage (below 70% threshold)",
            "issues": [
                "Primary keyword missing in posts #3, #7, #15",
                "Keyword density too low in posts #12, #20",
            ],
        }
        report = QAReport(
            client_name="Test Client",
            total_posts=30,
            overall_passed=False,
            quality_score=0.75,
            hook_validation=sample_hook_validation,
            cta_validation=sample_cta_validation,
            length_validation=sample_length_validation,
            headline_validation=sample_headline_validation,
            keyword_validation=keyword_validation_with_issues,
            total_issues=2,
            all_issues=keyword_validation_with_issues["issues"],
        )
        markdown = report.to_markdown()

        # Check keyword validation section
        assert "## SEO Keyword Usage" in markdown
        assert "[FAIL] FAILED" in markdown or "[WARN]" in markdown
        assert "**Primary Usage Ratio:** 45.0%" in markdown
        # Check issues are listed (lines 157-160)
        assert "**Issues:**" in markdown
        assert "Primary keyword missing in posts #3, #7, #15" in markdown
        assert "Keyword density too low in posts #12, #20" in markdown

    def test_seo_validation_passing(
        self,
        sample_hook_validation,
        sample_cta_validation,
        sample_length_validation,
        sample_headline_validation,
    ):
        """Test markdown includes SEO validation for blog posts (lines 169-186)."""
        seo_validation = {
            "passed": True,
            "skipped": False,
            "average_score": 85.5,
            "metric": "Average SEO Score: 85.5/100 (5 blog posts)",
            "seo_scores": [88, 82, 90, 85, 82],
            "recommendations": [
                "Add more internal links to improve site structure",
                "Include primary keyword in first paragraph",
            ],
            "issues": [],
        }
        report = QAReport(
            client_name="Test Client",
            total_posts=30,
            overall_passed=True,
            quality_score=0.90,
            hook_validation=sample_hook_validation,
            cta_validation=sample_cta_validation,
            length_validation=sample_length_validation,
            headline_validation=sample_headline_validation,
            seo_validation=seo_validation,
        )
        markdown = report.to_markdown()

        # Check SEO validation section (lines 169-186)
        assert "## SEO Optimization (Blog Posts)" in markdown
        assert "[PASS] PASSED" in markdown
        assert "**Average SEO Score:** 85.5/100" in markdown
        assert "**SEO Recommendations:**" in markdown
        assert "Add more internal links to improve site structure" in markdown
        assert "Include primary keyword in first paragraph" in markdown

    def test_seo_validation_failing_with_issues(
        self,
        sample_hook_validation,
        sample_cta_validation,
        sample_length_validation,
        sample_headline_validation,
    ):
        """Test SEO validation displays issues when failing (lines 181-185)."""
        seo_validation = {
            "passed": False,
            "skipped": False,
            "average_score": 45.0,
            "metric": "Average SEO Score: 45/100 (3 blog posts)",
            "seo_scores": [40, 45, 50],
            "recommendations": [
                "Increase content length to at least 1500 words",
                "Add more H2 headings for better structure",
            ],
            "issues": [
                "Blog 1: Content too short (800 words, min 1500)",
                "Blog 2: Missing H2 headings (0 found, min 3)",
                "Blog 3: Keyword density too low (0.5%, target 1-3%)",
            ],
        }
        report = QAReport(
            client_name="Test Client",
            total_posts=30,
            overall_passed=False,
            quality_score=0.65,
            hook_validation=sample_hook_validation,
            cta_validation=sample_cta_validation,
            length_validation=sample_length_validation,
            headline_validation=sample_headline_validation,
            seo_validation=seo_validation,
            total_issues=3,
            all_issues=seo_validation["issues"],
        )
        markdown = report.to_markdown()

        # Check SEO validation failing section
        assert "## SEO Optimization (Blog Posts)" in markdown
        assert "[FAIL] FAILED" in markdown
        assert "**Average SEO Score:** 45.0/100" in markdown
        # Check issues are listed (lines 181-185)
        assert "**Issues:**" in markdown
        assert "Blog 1: Content too short" in markdown
        assert "Blog 2: Missing H2 headings" in markdown
        assert "Blog 3: Keyword density too low" in markdown

    def test_seo_validation_skipped(
        self,
        sample_hook_validation,
        sample_cta_validation,
        sample_length_validation,
        sample_headline_validation,
    ):
        """Test SEO validation is not shown when skipped (no blog posts)."""
        seo_validation = {
            "passed": True,
            "skipped": True,  # Set to true when no blog posts
            "average_score": 0,
            "metric": "No blog posts to validate",
            "seo_scores": [],
            "recommendations": [],
            "issues": [],
        }
        report = QAReport(
            client_name="Test Client",
            total_posts=30,
            overall_passed=True,
            quality_score=0.92,
            hook_validation=sample_hook_validation,
            cta_validation=sample_cta_validation,
            length_validation=sample_length_validation,
            headline_validation=sample_headline_validation,
            seo_validation=seo_validation,
        )
        markdown = report.to_markdown()

        # SEO section should NOT appear when skipped (line 169 condition)
        assert "## SEO Optimization (Blog Posts)" not in markdown

    def test_seo_validation_with_many_recommendations(
        self,
        sample_hook_validation,
        sample_cta_validation,
        sample_length_validation,
        sample_headline_validation,
    ):
        """Test SEO validation only shows top 5 recommendations (line 179)."""
        seo_validation = {
            "passed": True,
            "skipped": False,
            "average_score": 75.0,
            "metric": "Average SEO Score: 75/100 (5 blog posts)",
            "seo_scores": [75, 75, 75, 75, 75],
            "recommendations": [
                "Recommendation 1",
                "Recommendation 2",
                "Recommendation 3",
                "Recommendation 4",
                "Recommendation 5",
                "Recommendation 6 - should not appear",
                "Recommendation 7 - should not appear",
            ],
            "issues": [],
        }
        report = QAReport(
            client_name="Test Client",
            total_posts=30,
            overall_passed=True,
            quality_score=0.85,
            hook_validation=sample_hook_validation,
            cta_validation=sample_cta_validation,
            length_validation=sample_length_validation,
            headline_validation=sample_headline_validation,
            seo_validation=seo_validation,
        )
        markdown = report.to_markdown()

        # Should show first 5 recommendations (line 179)
        assert "Recommendation 1" in markdown
        assert "Recommendation 5" in markdown
        # Should NOT show recommendations beyond 5
        assert "Recommendation 6" not in markdown
        assert "Recommendation 7" not in markdown
