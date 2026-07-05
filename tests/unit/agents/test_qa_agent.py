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
        assert agent.headline_validator is not None
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
        assert agent.headline_validator.min_elements == 3

    def test_validate_posts_calls_all_validators(self, sample_posts):
        """Test validate_posts calls all required validators"""
        agent = QAAgent()

        with (
            patch.object(agent.hook_validator, "validate") as mock_hook,
            patch.object(agent.cta_validator, "validate") as mock_cta,
            patch.object(agent.length_validator, "validate") as mock_length,
            patch.object(agent.headline_validator, "validate") as mock_headline,
        ):

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
            patch.object(agent.headline_validator, "validate") as mock_headline,
            patch.object(agent.keyword_validator, "validate") as mock_keyword,
        ):

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
            patch.object(agent.headline_validator, "validate") as mock_headline,
        ):

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
            patch.object(agent.headline_validator, "validate") as mock_headline,
        ):

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
            patch.object(agent.headline_validator, "validate") as mock_headline,
        ):

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
            patch.object(agent.headline_validator, "validate") as mock_headline,
        ):

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
            patch.object(agent.headline_validator, "validate") as mock_headline,
        ):

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
            patch.object(agent.headline_validator, "validate") as mock_headline,
            patch.object(agent.keyword_validator, "validate") as mock_keyword,
        ):

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
            patch.object(agent.headline_validator, "validate") as mock_headline,
        ):

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
            patch.object(agent.headline_validator, "validate") as mock_headline,
        ):

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
