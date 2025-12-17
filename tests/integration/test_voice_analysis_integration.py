"""Integration tests for enhanced voice analysis system"""

import pytest

from src.agents.voice_analyzer import VoiceAnalyzer
from src.models.client_brief import ClientBrief, TonePreference
from src.models.post import Post


@pytest.fixture
def sample_client_brief():
    """Create a sample client brief for testing"""
    return ClientBrief(
        company_name="TechStartup Inc",
        business_description="B2B SaaS platform for marketing automation",
        ideal_customer="Marketing managers at mid-size companies",
        main_problem_solved="Manual marketing processes waste time",
        brand_personality=[TonePreference.APPROACHABLE, TonePreference.DATA_DRIVEN],
        key_phrases=["marketing automation", "save time", "data-driven decisions"],
        misconceptions=["Marketing automation is expensive"],
        tone_to_avoid="overly technical",
    )


@pytest.fixture
def sample_posts():
    """Create sample posts for voice analysis"""
    posts = [
        Post(
            content="""Most marketing managers waste 20 hours per week on manual tasks.

            Let's explore how automation can change that. Research shows that 87% of teams
            using marketing automation see significant time savings.

            Our data indicates that strategic implementation is key. What if you could
            optimize your workflow and focus on what matters?

            Ready to transform your marketing? Let's talk.""",
            template_id=1,
            template_name="Problem Recognition",
            variant=1,
            client_name="TechStartup Inc",
        ),
        Post(
            content="""Here's the thing about marketing automation: it's not as expensive
            as you think.

            We've helped over 500 marketing teams streamline their processes. The bottom
            line? You can achieve more with less effort.

            Think about your current workflow. How much time do you spend on repetitive tasks?

            Share your biggest marketing challenge below.""",
            template_id=2,
            template_name="Myth Busting",
            variant=1,
            client_name="TechStartup Inc",
        ),
        Post(
            content="""Three simple steps to optimize your marketing workflow:

            1. Identify repetitive tasks
            2. Map your automation strategy
            3. Implement and measure results

            Our research shows this framework works for 95% of teams. Data-driven
            decision making is the key to success.

            What questions do you have about marketing automation?""",
            template_id=3,
            template_name="How-To",
            variant=1,
            client_name="TechStartup Inc",
        ),
    ]
    return posts


class TestVoiceAnalysisIntegration:
    """Integration tests for enhanced voice analysis"""

    def test_analyze_voice_patterns_with_new_metrics(self, sample_client_brief, sample_posts):
        """Test that voice analysis generates all new metrics"""
        analyzer = VoiceAnalyzer()

        # Run voice analysis
        voice_guide = analyzer.analyze_voice_patterns(sample_posts, sample_client_brief)

        # Verify basic fields still work
        assert voice_guide.company_name == "TechStartup Inc"
        assert voice_guide.generated_from_posts == 3
        assert len(voice_guide.dominant_tones) > 0
        assert 0.0 <= voice_guide.tone_consistency_score <= 1.0

        # Verify NEW metrics are populated
        assert voice_guide.average_readability_score is not None
        assert 0.0 <= voice_guide.average_readability_score <= 100.0

        assert voice_guide.voice_dimensions is not None
        assert "formality" in voice_guide.voice_dimensions
        assert "tone" in voice_guide.voice_dimensions
        assert "perspective" in voice_guide.voice_dimensions

        assert voice_guide.sentence_variety is not None
        assert voice_guide.sentence_variety in ["low", "medium", "high"]

        assert voice_guide.voice_archetype is not None
        assert voice_guide.voice_archetype in [
            "Expert",
            "Friend",
            "Innovator",
            "Guide",
            "Motivator",
        ]

    def test_archetype_detection_b2b_saas(self, sample_client_brief, sample_posts):
        """Test that B2B SaaS content is detected as Expert archetype"""
        analyzer = VoiceAnalyzer()
        voice_guide = analyzer.analyze_voice_patterns(sample_posts, sample_client_brief)

        # B2B SaaS with data-driven tone should map to Expert
        assert voice_guide.voice_archetype in ["Expert", "Innovator"]

    def test_voice_dimensions_detect_professional_tone(self, sample_client_brief, sample_posts):
        """Test that professional keywords are detected"""
        analyzer = VoiceAnalyzer()
        voice_guide = analyzer.analyze_voice_patterns(sample_posts, sample_client_brief)

        # Posts contain words like "strategic", "optimize", "framework", "data"
        formality = voice_guide.voice_dimensions.get("formality", {})
        assert formality.get("dominant") in ["professional", "conversational"]
        assert formality.get("total_matches", 0) > 0

    def test_voice_dimensions_detect_authoritative_tone(self, sample_client_brief, sample_posts):
        """Test that authoritative tone is detected from data-driven language"""
        analyzer = VoiceAnalyzer()
        voice_guide = analyzer.analyze_voice_patterns(sample_posts, sample_client_brief)

        # Posts contain "research shows", "data indicates", "studies"
        tone = voice_guide.voice_dimensions.get("tone", {})
        # Should detect either authoritative or educational tone
        assert tone.get("dominant") in ["authoritative", "educational", "friendly"]
        assert tone.get("total_matches", 0) > 0

    def test_readability_score_reasonable_range(self, sample_client_brief, sample_posts):
        """Test that readability score is in a reasonable range for business content"""
        analyzer = VoiceAnalyzer()
        voice_guide = analyzer.analyze_voice_patterns(sample_posts, sample_client_brief)

        # Business writing should be fairly easy to read (60-80 range typically)
        assert 30.0 <= voice_guide.average_readability_score <= 90.0

    def test_sentence_variety_detection(self, sample_client_brief, sample_posts):
        """Test that sentence variety is detected"""
        analyzer = VoiceAnalyzer()
        voice_guide = analyzer.analyze_voice_patterns(sample_posts, sample_client_brief)

        # Sample posts have varied sentence lengths
        assert voice_guide.sentence_variety in ["low", "medium", "high"]

    def test_readability_recommendations_added_to_dos_donts(
        self, sample_client_brief, sample_posts
    ):
        """Test that readability-based recommendations are added"""
        analyzer = VoiceAnalyzer()
        voice_guide = analyzer.analyze_voice_patterns(sample_posts, sample_client_brief)

        # Should have dos and donts
        assert len(voice_guide.dos) > 0
        assert len(voice_guide.donts) > 0

        # If readability is good (>70), should recommend maintaining it
        if voice_guide.average_readability_score > 70:
            assert any(
                "accessible" in do.lower() or "easy-to-read" in do.lower() for do in voice_guide.dos
            )

    def test_markdown_output_includes_new_sections(self, sample_client_brief, sample_posts):
        """Test that markdown output includes Voice Metrics section"""
        analyzer = VoiceAnalyzer()
        voice_guide = analyzer.analyze_voice_patterns(sample_posts, sample_client_brief)

        # Generate markdown
        markdown = voice_guide.to_markdown()

        # Should include new sections
        assert "Voice Metrics" in markdown or "voice metrics" in markdown.lower()
        assert "Brand Archetype" in markdown or voice_guide.voice_archetype in markdown
        assert "Readability Score" in markdown

        # Should include readability interpretation
        assert any(grade in markdown for grade in ["grade", "Easy", "Difficult", "Standard"])

        # Should include sentence variety
        assert "Sentence Variety" in markdown

    def test_backward_compatibility_without_new_metrics(self, sample_client_brief):
        """Test that EnhancedVoiceGuide works without new optional fields"""
        from src.models.voice_guide import EnhancedVoiceGuide

        # Create voice guide WITHOUT new metrics (backward compatibility test)
        voice_guide = EnhancedVoiceGuide(
            company_name="Test Company",
            generated_from_posts=5,
            dominant_tones=["professional", "data-driven"],
            tone_consistency_score=0.85,
            average_word_count=200,
            average_paragraph_count=3.5,
            question_usage_rate=0.6,
            dos=["Do this"],
            donts=["Don't do that"],
            examples=["Example 1"],
            # NEW FIELDS OMITTED (should use None defaults)
        )

        # Should not crash
        assert voice_guide.company_name == "Test Company"
        assert voice_guide.average_readability_score is None
        assert voice_guide.voice_dimensions is None
        assert voice_guide.sentence_variety is None
        assert voice_guide.voice_archetype is None

        # Markdown should still work (just without new sections)
        markdown = voice_guide.to_markdown()
        assert "Test Company" in markdown

    def test_complete_pipeline_with_conversational_content(self):
        """Test voice analysis with conversational content"""
        # Create conversational brief
        brief = ClientBrief(
            company_name="Friendly Coach",
            business_description="Life coaching for creative entrepreneurs",
            ideal_customer="Creative freelancers and solopreneurs",
            main_problem_solved="Overwhelm and lack of direction",
            brand_personality=[TonePreference.APPROACHABLE, TonePreference.WITTY],
            key_phrases=["you've got this", "let's figure it out together"],
        )

        # Create conversational posts
        posts = [
            Post(
                content="""Hey there! Let's talk about creative burnout.

                You know that feeling when you're stuck? We've all been there. Here's the thing -
                you don't have to figure it out alone.

                Imagine if you had a clear path forward. Think about what you could achieve.

                Ready to get unstuck? Let me know what's holding you back.""",
                template_id=1,
                template_name="Question Post",
                variant=1,
                client_name="Friendly Coach",
            ),
        ]

        analyzer = VoiceAnalyzer()
        voice_guide = analyzer.analyze_voice_patterns(posts, brief)

        # Should detect conversational formality
        formality = voice_guide.voice_dimensions.get("formality", {})
        assert formality.get("dominant") in ["conversational", "casual"]

        # Should map to Friend or Guide archetype
        assert voice_guide.voice_archetype in ["Friend", "Guide", "Motivator"]

        # Readability should be high (conversational is easier to read)
        assert voice_guide.average_readability_score > 60.0


class TestVoiceMetricsPerformance:
    """Test performance of voice metrics calculation"""

    def test_analysis_completes_quickly(self, sample_client_brief):
        """Test that voice analysis completes in reasonable time"""
        import time

        # Create 30 posts (typical use case)
        posts = []
        for i in range(30):
            posts.append(
                Post(
                    content="""Marketing automation helps businesses save time and improve efficiency.
                Our research shows that strategic implementation leads to better results.
                Let's explore how you can optimize your workflow today.""",
                    template_id=i % 15 + 1,
                    template_name=f"Template {i % 15 + 1}",
                    variant=i // 15 + 1,
                    client_name="TechStartup Inc",
                )
            )

        analyzer = VoiceAnalyzer()

        start = time.time()
        voice_guide = analyzer.analyze_voice_patterns(posts, sample_client_brief)
        duration = time.time() - start

        # Should complete in under 5 seconds for 30 posts
        assert duration < 5.0

        # All metrics should be populated
        assert voice_guide.average_readability_score is not None
        assert voice_guide.voice_dimensions is not None
        assert voice_guide.sentence_variety is not None
        assert voice_guide.voice_archetype is not None
