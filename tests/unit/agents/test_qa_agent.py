"""Unit tests for QA Agent"""

import pytest
from unittest.mock import patch
from src.agents.qa_agent import QAAgent
from src.models.post import Post
from src.models.qa_report import QAReport
from src.models.seo_keyword import KeywordStrategy


class TestQAAgent:
    """Test suite for QAAgent"""

    @pytest.fixture
    def sample_posts(self):
        """Create sample posts for testing"""
        return [
            Post(
                content="This is post 1 with a unique hook. What do you think?",
                template_id=1,
                template_name="Template 1",
                client_name="Test Client",
            ),
            Post(
                content="This is post 2 with different opening. Comment below!",
                template_id=2,
                template_name="Template 2",
                client_name="Test Client",
            ),
            Post(
                content="Here's post 3 starting differently. Share your thoughts?",
                template_id=3,
                template_name="Template 3",
                client_name="Test Client",
            ),
        ]

    @pytest.fixture
    def keyword_strategy(self):
        """Sample keyword strategy"""
        from src.models.seo_keyword import SEOKeyword, KeywordIntent, KeywordDifficulty

        return KeywordStrategy(
            client_name="Test Client",
            primary_keywords=[
                SEOKeyword(
                    keyword="project management",
                    intent=KeywordIntent.COMMERCIAL,
                    difficulty=KeywordDifficulty.MEDIUM,
                    priority=1,
                ),
                SEOKeyword(
                    keyword="remote work",
                    intent=KeywordIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.EASY,
                    priority=2,
                ),
                SEOKeyword(
                    keyword="productivity",
                    intent=KeywordIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.EASY,
                    priority=3,
                ),
            ],
            secondary_keywords=[
                SEOKeyword(
                    keyword="collaboration",
                    intent=KeywordIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.EASY,
                    priority=4,
                ),
                SEOKeyword(
                    keyword="team efficiency",
                    intent=KeywordIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.EASY,
                    priority=5,
                ),
            ],
            longtail_keywords=[
                SEOKeyword(
                    keyword="how to manage remote teams effectively",
                    intent=KeywordIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.EASY,
                    priority=6,
                ),
            ],
        )

    def test_initialization_without_keywords(self):
        """Test QA Agent initializes without keyword strategy"""
        agent = QAAgent()

        assert agent.hook_validator is not None
        assert agent.cta_validator is not None
        assert agent.length_validator is not None
        # headline_validator is constructed per-call in validate_posts (its threshold
        # depends on client_type), so it is no longer an __init__-time attribute.
        assert agent.keyword_validator is None

    def test_initialization_with_keywords(self, keyword_strategy):
        """Test QA Agent initializes with keyword strategy"""
        agent = QAAgent(keyword_strategy=keyword_strategy)

        assert agent.keyword_validator is not None

    def test_validators_configured_correctly(self):
        """Test validators are configured with correct thresholds"""
        agent = QAAgent()

        assert agent.hook_validator.similarity_threshold == 0.80
        assert agent.cta_validator.variety_threshold == 0.40

    def test_default_headline_threshold_is_three(self, sample_posts):
        """Headline validator is built per-call with default min_elements=3.

        The headline threshold now depends on client_type (local-service clients
        get 2), so the validator is constructed inside validate_posts rather than
        __init__. With no client_type the default threshold is 3.
        """
        agent = QAAgent()

        with patch("src.agents.qa_agent.HeadlineValidator") as mock_headline_cls:
            mock_headline_cls.return_value.validate.return_value = {
                "passed": True,
                "headlines_analyzed": 0,
                "issues": [],
            }
            agent.validate_posts(sample_posts, "Test Client")

        mock_headline_cls.assert_called_once_with(min_elements=3)

    def test_validate_posts_calls_all_validators(self, sample_posts):
        """Test validate_posts calls all required validators"""
        agent = QAAgent()

        with (
            patch.object(agent.hook_validator, "validate") as mock_hook,
            patch.object(agent.cta_validator, "validate") as mock_cta,
            patch.object(agent.length_validator, "validate") as mock_length,
            patch("src.agents.qa_agent.HeadlineValidator") as mock_headline_cls,
        ):
            # HeadlineValidator is constructed inside validate_posts; its instance's
            # .validate is the mock the assertions below target.
            mock_headline = mock_headline_cls.return_value.validate

            # Mock validator responses
            mock_hook.return_value = {
                "passed": True,
                "uniqueness_score": 0.9,
                "metric": "90% unique",
                "issues": [],
            }
            mock_cta.return_value = {
                "passed": True,
                "variety_score": 0.5,
                "metric": "50% variety",
                "cta_distribution": {},
                "issues": [],
            }
            mock_length.return_value = {
                "passed": True,
                "average_length": 200,
                "metric": "200 words",
                "optimal_ratio": 0.9,
                "length_distribution": {},
                "issues": [],
            }
            mock_headline.return_value = {
                "passed": True,
                "average_elements": 3.5,
                "metric": "3.5 elements",
                "headlines_analyzed": 3,
                "issues": [],
            }

            agent.validate_posts(sample_posts, "Test Client")

            # Verify all validators called
            mock_hook.assert_called_once_with(sample_posts)
            mock_cta.assert_called_once_with(sample_posts)
            mock_length.assert_called_once_with(sample_posts)
            mock_headline.assert_called_once_with(sample_posts)

    def test_validate_posts_with_keyword_validator(self, sample_posts, keyword_strategy):
        """Test validate_posts calls keyword validator when available"""
        agent = QAAgent(keyword_strategy=keyword_strategy)

        with (
            patch.object(agent.hook_validator, "validate") as mock_hook,
            patch.object(agent.cta_validator, "validate") as mock_cta,
            patch.object(agent.length_validator, "validate") as mock_length,
            patch("src.agents.qa_agent.HeadlineValidator") as mock_headline_cls,
            patch.object(agent.keyword_validator, "validate") as mock_keyword,
        ):
            # HeadlineValidator is constructed inside validate_posts; its instance's
            # .validate is the mock the assertions below target.
            mock_headline = mock_headline_cls.return_value.validate

            # Mock all validator responses
            mock_hook.return_value = {
                "passed": True,
                "uniqueness_score": 0.9,
                "metric": "test",
                "issues": [],
            }
            mock_cta.return_value = {
                "passed": True,
                "variety_score": 0.5,
                "metric": "test",
                "cta_distribution": {},
                "issues": [],
            }
            mock_length.return_value = {
                "passed": True,
                "average_length": 200,
                "metric": "test",
                "optimal_ratio": 0.9,
                "length_distribution": {},
                "issues": [],
            }
            mock_headline.return_value = {
                "passed": True,
                "average_elements": 3.5,
                "metric": "test",
                "headlines_analyzed": 3,
                "issues": [],
            }
            mock_keyword.return_value = {
                "passed": True,
                "primary_usage_ratio": 0.8,
                "metric": "test",
                "issues": [],
            }

            agent.validate_posts(sample_posts, "Test Client")

            # Verify keyword validator called
            mock_keyword.assert_called_once_with(sample_posts)

    def test_validate_posts_returns_qa_report(self, sample_posts):
        """Test validate_posts returns QAReport instance"""
        agent = QAAgent()

        result = agent.validate_posts(sample_posts, "Test Client")

        assert isinstance(result, QAReport)
        assert result.client_name == "Test Client"
        assert result.total_posts == len(sample_posts)

    def test_validate_posts_collects_all_issues(self, sample_posts):
        """Test all issues from validators are collected"""
        agent = QAAgent()

        with (
            patch.object(agent.hook_validator, "validate") as mock_hook,
            patch.object(agent.cta_validator, "validate") as mock_cta,
            patch.object(agent.length_validator, "validate") as mock_length,
            patch("src.agents.qa_agent.HeadlineValidator") as mock_headline_cls,
        ):
            # HeadlineValidator is constructed inside validate_posts; its instance's
            # .validate is the mock the assertions below target.
            mock_headline = mock_headline_cls.return_value.validate

            # Mock validators with issues
            mock_hook.return_value = {
                "passed": False,
                "uniqueness_score": 0.7,
                "metric": "test",
                "issues": ["Hook issue 1", "Hook issue 2"],
            }
            mock_cta.return_value = {
                "passed": False,
                "variety_score": 0.3,
                "metric": "test",
                "cta_distribution": {},
                "issues": ["CTA issue 1"],
            }
            mock_length.return_value = {
                "passed": True,
                "average_length": 200,
                "metric": "test",
                "optimal_ratio": 0.9,
                "length_distribution": {},
                "issues": [],
            }
            mock_headline.return_value = {
                "passed": False,
                "average_elements": 2.0,
                "metric": "test",
                "headlines_analyzed": 3,
                "issues": ["Headline issue 1"],
            }

            result = agent.validate_posts(sample_posts, "Test Client")

            # Should collect all 4 issues
            assert result.total_issues == 4
            assert "Hook issue 1" in result.all_issues
            assert "Hook issue 2" in result.all_issues
            assert "CTA issue 1" in result.all_issues
            assert "Headline issue 1" in result.all_issues

    def test_validate_posts_calculates_quality_score(self, sample_posts):
        """Test quality score is calculated as average of validator scores"""
        agent = QAAgent()

        with (
            patch.object(agent.hook_validator, "validate") as mock_hook,
            patch.object(agent.cta_validator, "validate") as mock_cta,
            patch.object(agent.length_validator, "validate") as mock_length,
            patch("src.agents.qa_agent.HeadlineValidator") as mock_headline_cls,
        ):
            # HeadlineValidator is constructed inside validate_posts; its instance's
            # .validate is the mock the assertions below target.
            mock_headline = mock_headline_cls.return_value.validate

            # Mock validators with specific scores
            mock_hook.return_value = {
                "passed": True,
                "uniqueness_score": 0.9,
                "metric": "test",
                "issues": [],
            }
            mock_cta.return_value = {
                "passed": True,
                "variety_score": 0.8,
                "metric": "test",
                "cta_distribution": {},
                "issues": [],
            }
            mock_length.return_value = {
                "passed": True,
                "average_length": 200,
                "metric": "test",
                "optimal_ratio": 0.7,
                "length_distribution": {},
                "issues": [],
            }
            mock_headline.return_value = {
                "passed": True,
                "average_elements": 3.5,
                "metric": "test",
                "headlines_analyzed": 3,
                "below_threshold_count": 0,
                "issues": [],
            }

            result = agent.validate_posts(sample_posts, "Test Client")

            # Average: (0.9 + 0.8 + 0.7 + 1.0) / 4 = 0.85
            assert result.quality_score == pytest.approx(0.85, rel=0.01)

    def test_validate_posts_overall_passed_all_validators_pass(self, sample_posts):
        """Test overall_passed is True when all validators pass"""
        agent = QAAgent()

        with (
            patch.object(agent.hook_validator, "validate") as mock_hook,
            patch.object(agent.cta_validator, "validate") as mock_cta,
            patch.object(agent.length_validator, "validate") as mock_length,
            patch("src.agents.qa_agent.HeadlineValidator") as mock_headline_cls,
        ):
            # HeadlineValidator is constructed inside validate_posts; its instance's
            # .validate is the mock the assertions below target.
            mock_headline = mock_headline_cls.return_value.validate

            # All validators pass
            mock_hook.return_value = {
                "passed": True,
                "uniqueness_score": 0.9,
                "metric": "test",
                "issues": [],
            }
            mock_cta.return_value = {
                "passed": True,
                "variety_score": 0.5,
                "metric": "test",
                "cta_distribution": {},
                "issues": [],
            }
            mock_length.return_value = {
                "passed": True,
                "average_length": 200,
                "metric": "test",
                "optimal_ratio": 0.9,
                "length_distribution": {},
                "issues": [],
            }
            mock_headline.return_value = {
                "passed": True,
                "average_elements": 3.5,
                "metric": "test",
                "headlines_analyzed": 3,
                "issues": [],
            }

            result = agent.validate_posts(sample_posts, "Test Client")

            assert result.overall_passed is True

    def test_validate_posts_overall_passed_one_validator_fails(self, sample_posts):
        """Test overall_passed is False when any validator fails"""
        agent = QAAgent()

        with (
            patch.object(agent.hook_validator, "validate") as mock_hook,
            patch.object(agent.cta_validator, "validate") as mock_cta,
            patch.object(agent.length_validator, "validate") as mock_length,
            patch("src.agents.qa_agent.HeadlineValidator") as mock_headline_cls,
        ):
            # HeadlineValidator is constructed inside validate_posts; its instance's
            # .validate is the mock the assertions below target.
            mock_headline = mock_headline_cls.return_value.validate

            # Hook validator fails
            mock_hook.return_value = {
                "passed": False,
                "uniqueness_score": 0.7,
                "metric": "test",
                "issues": ["Issue"],
            }
            mock_cta.return_value = {
                "passed": True,
                "variety_score": 0.5,
                "metric": "test",
                "cta_distribution": {},
                "issues": [],
            }
            mock_length.return_value = {
                "passed": True,
                "average_length": 200,
                "metric": "test",
                "optimal_ratio": 0.9,
                "length_distribution": {},
                "issues": [],
            }
            mock_headline.return_value = {
                "passed": True,
                "average_elements": 3.5,
                "metric": "test",
                "headlines_analyzed": 3,
                "issues": [],
            }

            result = agent.validate_posts(sample_posts, "Test Client")

            assert result.overall_passed is False

    def test_validate_posts_headline_score_calculation(self, sample_posts):
        """Test headline score calculated correctly from threshold counts"""
        agent = QAAgent()

        with (
            patch.object(agent.hook_validator, "validate") as mock_hook,
            patch.object(agent.cta_validator, "validate") as mock_cta,
            patch.object(agent.length_validator, "validate") as mock_length,
            patch("src.agents.qa_agent.HeadlineValidator") as mock_headline_cls,
        ):
            # HeadlineValidator is constructed inside validate_posts; its instance's
            # .validate is the mock the assertions below target.
            mock_headline = mock_headline_cls.return_value.validate

            mock_hook.return_value = {
                "passed": True,
                "uniqueness_score": 0.9,
                "metric": "test",
                "issues": [],
            }
            mock_cta.return_value = {
                "passed": True,
                "variety_score": 0.5,
                "metric": "test",
                "cta_distribution": {},
                "issues": [],
            }
            mock_length.return_value = {
                "passed": True,
                "average_length": 200,
                "metric": "test",
                "optimal_ratio": 0.9,
                "length_distribution": {},
                "issues": [],
            }
            # 10 analyzed, 2 below threshold = 80% score
            mock_headline.return_value = {
                "passed": True,
                "average_elements": 3.5,
                "metric": "test",
                "headlines_analyzed": 10,
                "below_threshold_count": 2,
                "issues": [],
            }

            result = agent.validate_posts(sample_posts, "Test Client")

            # Quality score includes headline score of 0.8
            # (0.9 + 0.5 + 0.9 + 0.8) / 4 = 0.775
            assert result.quality_score == pytest.approx(0.775, rel=0.01)

    def test_validate_posts_with_keyword_score(self, sample_posts, keyword_strategy):
        """Test keyword score included in quality calculation"""
        agent = QAAgent(keyword_strategy=keyword_strategy)

        with (
            patch.object(agent.hook_validator, "validate") as mock_hook,
            patch.object(agent.cta_validator, "validate") as mock_cta,
            patch.object(agent.length_validator, "validate") as mock_length,
            patch("src.agents.qa_agent.HeadlineValidator") as mock_headline_cls,
            patch.object(agent.keyword_validator, "validate") as mock_keyword,
        ):
            # HeadlineValidator is constructed inside validate_posts; its instance's
            # .validate is the mock the assertions below target.
            mock_headline = mock_headline_cls.return_value.validate

            mock_hook.return_value = {
                "passed": True,
                "uniqueness_score": 0.9,
                "metric": "test",
                "issues": [],
            }
            mock_cta.return_value = {
                "passed": True,
                "variety_score": 0.8,
                "metric": "test",
                "cta_distribution": {},
                "issues": [],
            }
            mock_length.return_value = {
                "passed": True,
                "average_length": 200,
                "metric": "test",
                "optimal_ratio": 0.7,
                "length_distribution": {},
                "issues": [],
            }
            mock_headline.return_value = {
                "passed": True,
                "average_elements": 3.5,
                "metric": "test",
                "headlines_analyzed": 3,
                "below_threshold_count": 0,
                "issues": [],
            }
            mock_keyword.return_value = {
                "passed": True,
                "primary_usage_ratio": 0.85,
                "metric": "test",
                "issues": [],
            }

            result = agent.validate_posts(sample_posts, "Test Client")

            # (0.9 + 0.8 + 0.7 + 1.0 + 0.85) / 5 = 0.85
            assert result.quality_score == pytest.approx(0.85, rel=0.01)

    def test_validate_posts_empty_posts_list(self):
        """Test validation with empty posts list"""
        agent = QAAgent()

        result = agent.validate_posts([], "Test Client")

        assert isinstance(result, QAReport)
        assert result.total_posts == 0
        assert result.total_issues == 0

    def test_validate_posts_logging(self, sample_posts):
        """Test validation logs start and completion"""
        agent = QAAgent()

        with patch("src.agents.qa_agent.logger") as mock_logger:
            agent.validate_posts(sample_posts, "Test Client")

            # Should log start and completion
            assert mock_logger.info.call_count >= 2

    def test_validate_posts_report_structure(self, sample_posts):
        """Test QA report has correct structure"""
        agent = QAAgent()

        result = agent.validate_posts(sample_posts, "Test Client")

        # Verify all required fields present
        assert hasattr(result, "client_name")
        assert hasattr(result, "total_posts")
        assert hasattr(result, "overall_passed")
        assert hasattr(result, "quality_score")
        assert hasattr(result, "hook_validation")
        assert hasattr(result, "cta_validation")
        assert hasattr(result, "length_validation")
        assert hasattr(result, "headline_validation")
        assert hasattr(result, "keyword_validation")
        assert hasattr(result, "total_issues")
        assert hasattr(result, "all_issues")

    def test_validate_posts_keyword_validation_optional(self, sample_posts):
        """Test keyword_validation is None when no strategy provided"""
        agent = QAAgent()  # No keyword strategy

        result = agent.validate_posts(sample_posts, "Test Client")

        assert result.keyword_validation is None

    def test_validate_posts_missing_score_fields(self, sample_posts):
        """Test handles validators with missing score fields gracefully"""
        agent = QAAgent()

        with (
            patch.object(agent.hook_validator, "validate") as mock_hook,
            patch.object(agent.cta_validator, "validate") as mock_cta,
            patch.object(agent.length_validator, "validate") as mock_length,
            patch("src.agents.qa_agent.HeadlineValidator") as mock_headline_cls,
        ):
            # HeadlineValidator is constructed inside validate_posts; its instance's
            # .validate is the mock the assertions below target.
            mock_headline = mock_headline_cls.return_value.validate

            # Mock validators with some missing score fields
            mock_hook.return_value = {
                "passed": True,
                # Missing uniqueness_score
                "metric": "test",
                "issues": [],
            }
            mock_cta.return_value = {
                "passed": True,
                "variety_score": 0.5,
                "metric": "test",
                "cta_distribution": {},
                "issues": [],
            }
            mock_length.return_value = {
                "passed": True,
                "average_length": 200,
                "metric": "test",
                # Missing optimal_ratio
                "length_distribution": {},
                "issues": [],
            }
            mock_headline.return_value = {
                "passed": True,
                "average_elements": 3.5,
                "metric": "test",
                "headlines_analyzed": 0,  # Will skip headline score
                "issues": [],
            }

            result = agent.validate_posts(sample_posts, "Test Client")

            # Should handle gracefully and calculate score from available fields
            assert isinstance(result.quality_score, float)
            assert 0.0 <= result.quality_score <= 1.0

    def test_validate_posts_zero_headlines_analyzed(self, sample_posts):
        """Test headline score calculation when no headlines analyzed"""
        agent = QAAgent()

        with (
            patch.object(agent.hook_validator, "validate") as mock_hook,
            patch.object(agent.cta_validator, "validate") as mock_cta,
            patch.object(agent.length_validator, "validate") as mock_length,
            patch("src.agents.qa_agent.HeadlineValidator") as mock_headline_cls,
        ):
            # HeadlineValidator is constructed inside validate_posts; its instance's
            # .validate is the mock the assertions below target.
            mock_headline = mock_headline_cls.return_value.validate

            mock_hook.return_value = {
                "passed": True,
                "uniqueness_score": 0.9,
                "metric": "test",
                "issues": [],
            }
            mock_cta.return_value = {
                "passed": True,
                "variety_score": 0.5,
                "metric": "test",
                "cta_distribution": {},
                "issues": [],
            }
            mock_length.return_value = {
                "passed": True,
                "average_length": 200,
                "metric": "test",
                "optimal_ratio": 0.9,
                "length_distribution": {},
                "issues": [],
            }
            mock_headline.return_value = {
                "passed": True,
                "average_elements": 0.0,
                "metric": "test",
                "headlines_analyzed": 0,  # No headlines
                "issues": [],
            }

            result = agent.validate_posts(sample_posts, "Test Client")

            # Should calculate score without headline component
            # (0.9 + 0.5 + 0.9) / 3 = 0.767
            assert result.quality_score == pytest.approx(0.767, rel=0.01)


class TestEngagementPrediction:
    """PREDICT-01 wired into the QA report as an advisory pre-publish signal."""

    def _posts(self, n=3):
        return [
            Post(
                content=f"Post {i} with a specific hook and a clear closing line.",
                template_id=i + 1,
                template_name=f"Template {i + 1}",
                client_name="Test Client",
            )
            for i in range(n)
        ]

    def test_summary_none_for_empty_batch(self):
        assert QAAgent()._predict_engagement_summary([]) is None

    def test_summary_has_expected_shape(self):
        summary = QAAgent()._predict_engagement_summary(self._posts(3))
        assert summary is not None
        assert set(summary) == {
            "average_score",
            "min_score",
            "weak_count",
            "weak_floor",
            "total",
        }
        assert summary["total"] == 3
        assert 0 <= summary["average_score"] <= 100
        assert 0 <= summary["weak_count"] <= 3
        assert summary["min_score"] <= summary["average_score"]

    def test_score_matches_canonical_assess_post_with_hashtags(self):
        # The QA score must equal the regenerator's canonical assess_post score for
        # the same post — including trailing hashtags (which assess_post strips and
        # content_generator appends). Guards against a divergent pre-publish signal.
        from src.analysis.content_intelligence import assess_post

        content = (
            "3 words killed our onboarding conversion.\n\nWe A/B tested the signup copy "
            "for six weeks across 12,000 visitors and the boring literal version won by "
            "34% on completed signups.\n\nShip the boring version and measure it."
            "\n\n#growth #saas #onboarding"
        )
        post = Post(
            content=content,
            template_id=1,
            template_name="T",
            client_name="C",
            target_platform="linkedin",
        )
        summary = QAAgent()._predict_engagement_summary([post])
        expected = assess_post(content, platform="linkedin").predicted_score

        assert summary is not None
        assert summary["average_score"] == round(expected, 1)
        assert summary["min_score"] == expected

    def test_validate_posts_populates_prediction_and_renders(self):
        # Real validators (no mocks) so to_markdown has every field it renders.
        agent = QAAgent()
        report = agent.validate_posts(self._posts(3), "Test Client")

        assert report.engagement_prediction is not None
        assert report.engagement_prediction["total"] == 3
        assert "Predicted Engagement" in report.to_markdown()

    def test_prediction_is_advisory_present_in_serialized_report(self):
        # The engagement summary is surfaced on the report; pass/fail is decided by
        # the validators, not by predicted engagement.
        agent = QAAgent()
        report = agent.validate_posts(self._posts(2), "Test Client")
        assert "engagement_prediction" in report.model_dump()
        assert report.engagement_prediction["total"] == 2


class TestAnswerBlockGeo:
    """GEO-01 check_answer_block wired into the QA report as an advisory blog signal."""

    def _blog_post(self, opening_words, i=0):
        # "My Blog Title" reads as a headline (short, no terminal punctuation) → skipped; the
        # body paragraph (opening_words tokens) becomes the evaluated answer block.
        body = " ".join(f"word{j}" for j in range(opening_words)) + "."
        return Post(
            content=f"My Blog Title\n\n{body}",
            template_id=i + 1,
            template_name=f"T{i + 1}",
            client_name="Test Client",
            target_platform="blog",
        )

    def _social_post(self, i=0):
        return Post(
            content=f"Social post {i} with a hook and a close.",
            template_id=i + 1,
            template_name=f"T{i + 1}",
            client_name="Test Client",
            target_platform="linkedin",
        )

    def test_summary_none_for_empty_batch(self):
        assert QAAgent()._answer_block_summary([]) is None

    def test_summary_none_when_no_blog_posts(self):
        # Answer blocks are blog-specific — a purely social batch yields no summary.
        assert QAAgent()._answer_block_summary([self._social_post(0), self._social_post(1)]) is None

    def test_summary_counts_well_formed_vs_weak(self):
        posts = [
            self._blog_post(50, 0),  # in range → ok
            self._blog_post(20, 1),  # too short → weak
            self._blog_post(80, 2),  # too long → weak
            self._social_post(3),  # ignored (not a blog post)
        ]
        summary = QAAgent()._answer_block_summary(posts)
        assert summary == {"total": 3, "ok_count": 1, "weak_count": 2}

    def test_validate_posts_populates_and_renders(self):
        agent = QAAgent()
        report = agent.validate_posts(
            [self._blog_post(50, 0), self._blog_post(20, 1)], "Test Client"
        )
        assert report.answer_block_geo == {"total": 2, "ok_count": 1, "weak_count": 1}
        assert "GEO Answer Blocks (advisory)" in report.to_markdown()

    def test_absent_for_social_only_batch_in_serialized_report(self):
        # No blog posts → field stays None; the report still serializes and passes/fails on
        # the validators alone (advisory, never gating).
        agent = QAAgent()
        report = agent.validate_posts([self._social_post(0)], "Test Client")
        assert "answer_block_geo" in report.model_dump()
        assert report.answer_block_geo is None
        assert "GEO Answer Blocks" not in report.to_markdown()
