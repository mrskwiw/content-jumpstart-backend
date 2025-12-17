"""Unit tests for Voice Analyzer"""

import pytest

from src.agents.voice_analyzer import VoiceAnalyzer
from src.models.client_brief import ClientBrief, TonePreference
from src.models.post import Post


@pytest.fixture
def sample_posts():
    """Create sample posts"""
    posts = [
        Post(
            content="Most B2B SaaS founders struggle with retention. Here'''s why. Customer onboarding is rushed.",
            template_id=1,
            template_name="Problem Recognition",
            client_name="TestClient",
        ),
        Post(
            content="What if you could reduce churn by 40%? What'''s your biggest retention challenge?",
            template_id=5,
            template_name="Question Post",
            client_name="TestClient",
        ),
        Post(
            content="Customer success isn'''t about features. The reality is most companies focus wrong.",
            template_id=3,
            template_name="Contrarian Take",
            client_name="TestClient",
        ),
    ]
    return posts


@pytest.fixture
def sample_client_brief():
    """Create sample client brief"""
    return ClientBrief(
        company_name="TestClient",
        business_description="B2B SaaS retention platform",
        ideal_customer="Series A SaaS founders",
        main_problem_solved="Customer churn reduction",
        brand_personality=[TonePreference.DIRECT, TonePreference.DATA_DRIVEN],
        key_phrases=["customer success", "proactive approach"],
        tone_to_avoid="overly promotional",
    )


class TestVoiceAnalyzer:
    """Test Voice Analyzer"""

    def test_extract_hook(self, sample_posts):
        analyzer = VoiceAnalyzer()
        hook = analyzer._extract_hook(sample_posts[0].content)
        assert "retention" in hook
        assert hook.endswith(".")

    def test_extract_transitions(self, sample_posts):
        analyzer = VoiceAnalyzer()
        transitions = analyzer._extract_transitions(sample_posts[2].content)
        assert isinstance(transitions, list)

    def test_extract_cta(self, sample_posts):
        analyzer = VoiceAnalyzer()
        cta = analyzer._extract_cta(sample_posts[1].content)
        assert "?" in cta or "challenge" in cta.lower()

    def test_cluster_patterns(self):
        analyzer = VoiceAnalyzer()
        items = ["Test", "Test", "Similar"]
        patterns = analyzer._cluster_patterns(items, "opening")
        assert len(patterns) >= 1
        assert patterns[0].frequency >= 1

    def test_find_recurring_ngrams(self):
        analyzer = VoiceAnalyzer()
        text = "customer success is key. customer success drives results. customer success matters."
        phrases = analyzer._find_recurring_ngrams(text, min_freq=3)
        assert "customer success" in phrases

    def test_calculate_avg_paragraphs(self, sample_posts):
        analyzer = VoiceAnalyzer()
        avg = analyzer._calculate_avg_paragraphs(sample_posts)
        assert avg >= 1.0

    def test_calculate_tone_consistency(self, sample_posts, sample_client_brief):
        analyzer = VoiceAnalyzer()
        score = analyzer._calculate_tone_consistency(sample_posts, sample_client_brief)
        assert 0.0 <= score <= 1.0

    def test_analyze_complete(self, sample_posts, sample_client_brief):
        analyzer = VoiceAnalyzer()
        voice_guide = analyzer.analyze_voice_patterns(sample_posts, sample_client_brief)

        assert voice_guide.company_name == "TestClient"
        assert voice_guide.generated_from_posts == 3
        assert 0.0 <= voice_guide.tone_consistency_score <= 1.0
        assert voice_guide.average_word_count > 0
        assert len(voice_guide.dos) >= 3
        assert len(voice_guide.donts) >= 3

    def test_markdown_export(self, sample_posts, sample_client_brief):
        analyzer = VoiceAnalyzer()
        voice_guide = analyzer.analyze_voice_patterns(sample_posts, sample_client_brief)
        markdown = voice_guide.to_markdown()

        assert "# Enhanced Brand Voice Guide" in markdown
        assert "TestClient" in markdown
        assert "Tone Consistency Score" in markdown
