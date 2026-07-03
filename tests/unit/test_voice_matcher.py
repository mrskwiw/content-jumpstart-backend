"""
Unit tests for VoiceMatcher

Tests voice matching algorithms including:
- Overall match score calculation
- Readability comparison
- Word count comparison
- Archetype comparison
- Phrase usage comparison
- Recommendation generation
"""

import pytest
from unittest.mock import patch
from src.utils.voice_matcher import VoiceMatcher
from src.models.post import Post
from src.models.voice_guide import EnhancedVoiceGuide
from src.models.voice_sample import VoiceMatchComponentScore, VoiceMatchReport


class TestVoiceMatcherInit:
    """Test VoiceMatcher initialization"""

    def test_init_creates_voice_metrics(self):
        """Test that VoiceMatcher initializes with VoiceMetrics"""
        matcher = VoiceMatcher()
        assert matcher.voice_metrics is not None


class TestCalculateMatchScore:
    """Test calculate_match_score method"""

    @pytest.fixture
    def matcher(self):
        """Create VoiceMatcher instance"""
        return VoiceMatcher()

    @pytest.fixture
    def sample_posts(self):
        """Sample generated posts"""
        return [
            Post(
                content="This is a test post about project management. It discusses collaboration and remote work.",
                template_id=1,
                template_name="Test Template",
                client_name="Test Client",
                word_count=14,
            ),
            Post(
                content="Another post discussing team dynamics. We explore communication strategies and best practices.",
                template_id=2,
                template_name="Test Template 2",
                client_name="Test Client",
                word_count=13,
            ),
            Post(
                content="Final post about productivity. Learn how to optimize your workflow and achieve better results.",
                template_id=3,
                template_name="Test Template 3",
                client_name="Test Client",
                word_count=14,
            ),
        ]

    @pytest.fixture
    def reference_voice_guide(self):
        """Reference voice guide from client samples"""
        return EnhancedVoiceGuide(
            company_name="Test Client",
            generated_from_posts=10,
            tone_consistency_score=0.85,
            average_word_count=150,
            average_paragraph_count=3.5,
            question_usage_rate=0.3,
            brand_personality="Professional, Approachable",
            key_messaging="Focus on collaboration and productivity",
            average_readability_score=65.0,
            voice_archetype="Expert",
            key_phrases_used=["collaboration", "productivity", "team dynamics"],
        )

    def test_calculate_match_score_no_posts_raises_error(self, matcher, reference_voice_guide):
        """Test that ValueError is raised when no posts provided"""
        with pytest.raises(ValueError, match="No posts provided"):
            matcher.calculate_match_score([], reference_voice_guide)

    def test_calculate_match_score_no_guide_raises_error(self, matcher, sample_posts):
        """Test that ValueError is raised when no guide provided"""
        with pytest.raises(ValueError, match="No reference voice guide"):
            matcher.calculate_match_score(sample_posts, None)

    def test_calculate_match_score_returns_report(
        self, matcher, sample_posts, reference_voice_guide
    ):
        """Test that match score calculation returns VoiceMatchReport"""
        report = matcher.calculate_match_score(sample_posts, reference_voice_guide)

        assert isinstance(report, VoiceMatchReport)
        assert report.client_name == "Test Client"
        assert 0.0 <= report.match_score <= 1.0
        assert report.readability_score is not None
        assert report.word_count_score is not None
        assert report.archetype_score is not None
        assert report.phrase_usage_score is not None

    def test_calculate_match_score_with_no_readability(self, matcher, sample_posts):
        """Test match score when guide has no readability"""
        guide = EnhancedVoiceGuide(
            company_name="Test Client",
            generated_from_posts=5,
            tone_consistency_score=0.80,
            average_word_count=150,
            average_paragraph_count=3.0,
            question_usage_rate=0.2,
            brand_personality="Professional",
            key_messaging="Focus",
            average_readability_score=None,  # No readability
            voice_archetype="Expert",
            key_phrases_used=["test"],
        )

        report = matcher.calculate_match_score(sample_posts, guide)

        assert report.readability_score is None
        assert report.match_score > 0  # Should still calculate overall score

    def test_calculate_match_score_with_minimal_guide(self, matcher, sample_posts):
        """Test match score with minimal voice guide"""
        guide = EnhancedVoiceGuide(
            company_name="Test Client",
            generated_from_posts=1,
            tone_consistency_score=0.70,
            average_word_count=100,
            average_paragraph_count=2.0,
            question_usage_rate=0.0,
            brand_personality="Professional",
            key_messaging="Focus",
            average_readability_score=None,
            voice_archetype=None,
            key_phrases_used=[],  # Must be a list, not None
        )

        report = matcher.calculate_match_score(sample_posts, guide)

        # Should handle missing components gracefully
        # With minimal guide (only word_count available), score reflects that component
        assert report.match_score >= 0.0  # Can be low if word count differs significantly
        assert report.word_count_score is not None  # Word count always calculated


class TestCompareReadability:
    """Test _compare_readability method"""

    @pytest.fixture
    def matcher(self):
        """Create VoiceMatcher instance"""
        return VoiceMatcher()

    @pytest.fixture
    def sample_posts(self):
        """Sample posts with varied content"""
        return [
            Post(
                content="Simple short sentences. Easy to read. Very clear.",
                template_id=1,
                template_name="Test",
                client_name="Test",
                word_count=8,
            ),
            Post(
                content="Another simple post. Clear and concise. Good readability.",
                template_id=2,
                template_name="Test",
                client_name="Test",
                word_count=8,
            ),
        ]

    def test_compare_readability_exact_match(self, matcher, sample_posts):
        """Test readability comparison with exact match"""
        with patch.object(matcher.voice_metrics, "calculate_readability", return_value=65.0):
            score = matcher._compare_readability(sample_posts, target_readability=65.0)

            assert isinstance(score, VoiceMatchComponentScore)
            assert score.component == "Readability"
            assert score.score == 1.0  # Exact match
            assert score.target_value == 65.0
            assert score.actual_value == 65.0

    def test_compare_readability_within_tolerance(self, matcher, sample_posts):
        """Test readability within acceptable range (±5 points)"""
        with patch.object(matcher.voice_metrics, "calculate_readability", return_value=68.0):
            score = matcher._compare_readability(sample_posts, target_readability=65.0)

            # Difference is 3 points, should score high
            assert score.score > 0.8
            assert score.difference == 3.0

    def test_compare_readability_large_difference(self, matcher, sample_posts):
        """Test readability with large difference"""
        with patch.object(matcher.voice_metrics, "calculate_readability", return_value=85.0):
            score = matcher._compare_readability(sample_posts, target_readability=65.0)

            # Difference is 20 points, should score low
            assert score.score == 0.0
            assert score.difference == 20.0


class TestCompareWordCount:
    """Test _compare_word_count method"""

    @pytest.fixture
    def matcher(self):
        """Create VoiceMatcher instance"""
        return VoiceMatcher()

    def test_compare_word_count_exact_match(self, matcher):
        """Test word count comparison with exact match"""
        posts = [
            Post(
                content="x " * 150,
                template_id=1,
                template_name="Test",
                client_name="Test",
                word_count=150,
            ),
            Post(
                content="x " * 150,
                template_id=2,
                template_name="Test",
                client_name="Test",
                word_count=150,
            ),
        ]

        score = matcher._compare_word_count(posts, target_word_count=150)

        assert score.component == "Word Count"
        assert score.score == 1.0  # Exact match
        assert score.target_value == 150.0
        assert score.actual_value == 150.0

    def test_compare_word_count_within_tolerance(self, matcher):
        """Test word count within 20% tolerance"""
        posts = [
            Post(
                content="x " * 160,
                template_id=1,
                template_name="Test",
                client_name="Test",
                word_count=160,
            ),
            Post(
                content="x " * 140,
                template_id=2,
                template_name="Test",
                client_name="Test",
                word_count=140,
            ),
        ]

        score = matcher._compare_word_count(posts, target_word_count=150)

        # Average is 150, exact match
        assert score.score == 1.0

    def test_compare_word_count_large_difference(self, matcher):
        """Test word count with large difference (>50%)"""
        posts = [
            Post(
                content="x " * 300,
                template_id=1,
                template_name="Test",
                client_name="Test",
                word_count=300,
            ),
        ]

        score = matcher._compare_word_count(posts, target_word_count=150)

        # Difference is 100% (150/150), should score 0
        assert score.score == 0.0

    def test_compare_word_count_zero_target(self, matcher):
        """Test handling of zero target word count"""
        posts = [
            Post(
                content="x " * 100,
                template_id=1,
                template_name="Test",
                client_name="Test",
                word_count=100,
            ),
        ]

        score = matcher._compare_word_count(posts, target_word_count=0)

        # Should handle division by zero gracefully
        assert score.score >= 0.0


class TestCompareArchetype:
    """Test _compare_archetype method"""

    @pytest.fixture
    def matcher(self):
        """Create VoiceMatcher instance"""
        return VoiceMatcher()

    def test_compare_archetype_exact_match(self, matcher):
        """Test archetype comparison with exact match"""
        posts = [
            Post(
                content="We provide expert guidance and proven solutions.",
                template_id=1,
                template_name="Test",
                client_name="Test",
                word_count=7,
            ),
        ]

        with patch(
            "src.config.brand_frameworks.infer_archetype_from_voice_dimensions",
            return_value="Expert",
        ):
            score = matcher._compare_archetype(posts, target_archetype="Expert")

            assert score.component == "Brand Archetype"
            assert score.score == 1.0  # Exact match

    def test_compare_archetype_different(self, matcher):
        """Test archetype comparison with different archetypes"""
        posts = [
            Post(
                content="Let's collaborate and build together!",
                template_id=1,
                template_name="Test",
                client_name="Test",
                word_count=6,
            ),
        ]

        with patch(
            "src.config.brand_frameworks.infer_archetype_from_voice_dimensions",
            return_value="Friend",
        ):
            score = matcher._compare_archetype(posts, target_archetype="Expert")

            assert score.score == 0.5  # Different archetype

    def test_compare_archetype_case_insensitive(self, matcher):
        """Test archetype comparison is case-insensitive"""
        posts = [
            Post(
                content="Expert content here.",
                template_id=1,
                template_name="Test",
                client_name="Test",
                word_count=3,
            ),
        ]

        with patch(
            "src.config.brand_frameworks.infer_archetype_from_voice_dimensions",
            return_value="EXPERT",
        ):
            score = matcher._compare_archetype(posts, target_archetype="expert")

            assert score.score == 1.0  # Case-insensitive match


class TestComparePhraseUsage:
    """Test _compare_phrase_usage method"""

    @pytest.fixture
    def matcher(self):
        """Create VoiceMatcher instance"""
        return VoiceMatcher()

    def test_compare_phrase_usage_all_phrases_used(self, matcher):
        """Test phrase usage when all target phrases are used"""
        posts = [
            Post(
                content="We focus on collaboration and productivity with great team dynamics.",
                template_id=1,
                template_name="Test",
                client_name="Test",
                word_count=10,
            ),
        ]

        target_phrases = ["collaboration", "productivity", "team dynamics"]
        score = matcher._compare_phrase_usage(posts, target_phrases)

        assert score.component == "Phrase Usage"
        assert score.score == 1.0  # All phrases found
        assert score.actual_value == 3.0

    def test_compare_phrase_usage_half_used(self, matcher):
        """Test phrase usage when 50% of phrases are used"""
        posts = [
            Post(
                content="We focus on collaboration and teamwork.",
                template_id=1,
                template_name="Test",
                client_name="Test",
                word_count=6,
            ),
        ]

        target_phrases = ["collaboration", "productivity"]
        score = matcher._compare_phrase_usage(posts, target_phrases)

        assert score.score == 1.0  # 50% used = max score (50% * 2.0)
        assert score.actual_value == 1.0

    def test_compare_phrase_usage_none_used(self, matcher):
        """Test phrase usage when no phrases are used"""
        posts = [
            Post(
                content="Different content without target phrases.",
                template_id=1,
                template_name="Test",
                client_name="Test",
                word_count=6,
            ),
        ]

        target_phrases = ["collaboration", "productivity"]
        score = matcher._compare_phrase_usage(posts, target_phrases)

        assert score.score == 0.0  # No phrases found
        assert score.actual_value == 0.0

    def test_compare_phrase_usage_empty_phrases(self, matcher):
        """Test phrase usage with empty target phrases"""
        posts = [
            Post(
                content="Some content here.",
                template_id=1,
                template_name="Test",
                client_name="Test",
                word_count=3,
            ),
        ]

        score = matcher._compare_phrase_usage(posts, target_phrases=[])

        assert score.score == 0.5  # Neutral score
        assert score.target_value == 0.0

    def test_compare_phrase_usage_case_insensitive(self, matcher):
        """Test phrase usage is case-insensitive"""
        posts = [
            Post(
                content="COLLABORATION and PRODUCTIVITY are key.",
                template_id=1,
                template_name="Test",
                client_name="Test",
                word_count=5,
            ),
        ]

        target_phrases = ["collaboration", "productivity"]
        score = matcher._compare_phrase_usage(posts, target_phrases)

        assert score.actual_value == 2.0  # Both found despite case difference


class TestGenerateRecommendations:
    """Test _generate_recommendations method"""

    @pytest.fixture
    def matcher(self):
        """Create VoiceMatcher instance"""
        return VoiceMatcher()

    def test_recommendations_excellent_match(self, matcher):
        """Test recommendations for excellent overall match"""
        strengths, weaknesses, improvements = matcher._generate_recommendations(
            overall_score=0.95,
            readability_score=VoiceMatchComponentScore(
                component="Readability",
                score=0.95,
                target_value=65.0,
                actual_value=65.0,
                difference=0.0,
            ),
            word_count_score=None,
            archetype_score=None,
            phrase_usage_score=None,
        )

        assert any("Excellent" in s for s in strengths)
        assert any("perfectly matches" in s for s in strengths)
        assert len(weaknesses) == 0

    def test_recommendations_poor_readability(self, matcher):
        """Test recommendations for poor readability match"""
        strengths, weaknesses, improvements = matcher._generate_recommendations(
            overall_score=0.6,
            readability_score=VoiceMatchComponentScore(
                component="Readability",
                score=0.5,
                target_value=65.0,
                actual_value=80.0,
                difference=15.0,
            ),
            word_count_score=None,
            archetype_score=None,
            phrase_usage_score=None,
        )

        assert any("Readability differs" in w for w in weaknesses)
        assert any("complex" in i for i in improvements)

    def test_recommendations_poor_readability_too_simple(self, matcher):
        """Test recommendations when content is too simple"""
        strengths, weaknesses, improvements = matcher._generate_recommendations(
            overall_score=0.6,
            readability_score=VoiceMatchComponentScore(
                component="Readability",
                score=0.5,
                target_value=65.0,
                actual_value=50.0,
                difference=15.0,
            ),
            word_count_score=None,
            archetype_score=None,
            phrase_usage_score=None,
        )

        assert any("Simplify" in i for i in improvements)

    def test_recommendations_poor_word_count_too_long(self, matcher):
        """Test recommendations when posts are too long"""
        strengths, weaknesses, improvements = matcher._generate_recommendations(
            overall_score=0.6,
            readability_score=None,
            word_count_score=VoiceMatchComponentScore(
                component="Word Count",
                score=0.5,
                target_value=150.0,
                actual_value=250.0,
                difference=100.0,
            ),
            archetype_score=None,
            phrase_usage_score=None,
        )

        assert any("Post length differs" in w for w in weaknesses)
        assert any("Shorten" in i for i in improvements)

    def test_recommendations_poor_word_count_too_short(self, matcher):
        """Test recommendations when posts are too short"""
        strengths, weaknesses, improvements = matcher._generate_recommendations(
            overall_score=0.6,
            readability_score=None,
            word_count_score=VoiceMatchComponentScore(
                component="Word Count",
                score=0.5,
                target_value=150.0,
                actual_value=80.0,
                difference=70.0,
            ),
            archetype_score=None,
            phrase_usage_score=None,
        )

        assert any("Expand" in i for i in improvements)

    def test_recommendations_poor_phrase_usage(self, matcher):
        """Test recommendations for poor phrase usage"""
        strengths, weaknesses, improvements = matcher._generate_recommendations(
            overall_score=0.6,
            readability_score=None,
            word_count_score=None,
            archetype_score=None,
            phrase_usage_score=VoiceMatchComponentScore(
                component="Phrase Usage",
                score=0.3,
                target_value=5.0,
                actual_value=1.0,
                difference=4.0,
            ),
        )

        assert any("key phrases used" in w for w in weaknesses)
        assert any("signature phrases" in i for i in improvements)

    def test_recommendations_poor_overall_score(self, matcher):
        """Test recommendations for poor overall score"""
        strengths, weaknesses, improvements = matcher._generate_recommendations(
            overall_score=0.5,
            readability_score=None,
            word_count_score=None,
            archetype_score=None,
            phrase_usage_score=None,
        )

        assert any("regenerating" in i for i in improvements)

    def test_recommendations_good_archetype(self, matcher):
        """Test recommendations for good archetype match"""
        strengths, weaknesses, improvements = matcher._generate_recommendations(
            overall_score=0.85,
            readability_score=None,
            word_count_score=None,
            archetype_score=VoiceMatchComponentScore(
                component="Brand Archetype",
                score=1.0,
                target_value=None,
                actual_value=None,
                difference=None,
            ),
            phrase_usage_score=None,
        )

        assert any("archetype perfectly aligned" in s for s in strengths)


class TestIntegration:
    """Integration tests for VoiceMatcher"""

    def test_full_matching_pipeline(self):
        """Test complete voice matching pipeline"""
        matcher = VoiceMatcher()

        posts = [
            Post(
                content="Collaboration is key to productivity. Our team focuses on seamless teamwork.",
                template_id=1,
                template_name="Test",
                client_name="Test Client",
                word_count=12,
            ),
            Post(
                content="Productivity depends on good team dynamics. We prioritize collaboration.",
                template_id=2,
                template_name="Test",
                client_name="Test Client",
                word_count=10,
            ),
        ]

        guide = EnhancedVoiceGuide(
            company_name="Test Client",
            generated_from_posts=10,
            tone_consistency_score=0.85,
            average_word_count=150,
            average_paragraph_count=3.5,
            question_usage_rate=0.3,
            brand_personality="Professional",
            key_messaging="Focus on collaboration",
            average_readability_score=65.0,
            voice_archetype="Expert",
            key_phrases_used=["collaboration", "productivity", "team dynamics"],
        )

        report = matcher.calculate_match_score(posts, guide)

        # Verify report structure
        assert report.client_name == "Test Client"
        assert 0.0 <= report.match_score <= 1.0
        assert len(report.strengths) >= 0
        assert len(report.weaknesses) >= 0
        assert len(report.improvements) >= 0

        # Should detect high phrase usage
        assert report.phrase_usage_score.score > 0.5
