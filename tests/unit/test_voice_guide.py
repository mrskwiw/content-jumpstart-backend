"""Unit tests for voice_guide module.

Tests cover:
- EnhancedVoiceGuide model
- to_markdown method with various configurations
- VoicePattern model
"""

import pytest

from src.models.voice_guide import EnhancedVoiceGuide, VoicePattern


class TestVoicePattern:
    """Tests for VoicePattern model."""

    def test_voice_pattern_creation(self):
        """Test basic VoicePattern creation."""
        pattern = VoicePattern(
            pattern_type="opening",
            examples=["Example 1", "Example 2"],
            frequency=5,
            description="Question opener",
        )

        assert pattern.pattern_type == "opening"
        assert len(pattern.examples) == 2
        assert pattern.frequency == 5
        assert pattern.description == "Question opener"

    def test_voice_pattern_frequency_validation(self):
        """Test that frequency must be >= 0."""
        pattern = VoicePattern(
            pattern_type="cta",
            examples=["Test"],
            frequency=0,  # Edge case: exactly 0
            description="Test description",
        )
        assert pattern.frequency == 0


class TestEnhancedVoiceGuideBasic:
    """Tests for EnhancedVoiceGuide basic functionality."""

    @pytest.fixture
    def basic_guide(self):
        """Create a minimal voice guide."""
        return EnhancedVoiceGuide(
            company_name="Test Company",
            generated_from_posts=10,
            tone_consistency_score=0.85,
            average_word_count=200,
            average_paragraph_count=3.5,
            question_usage_rate=0.6,
        )

    def test_basic_guide_creation(self, basic_guide):
        """Test creating a basic voice guide."""
        assert basic_guide.company_name == "Test Company"
        assert basic_guide.generated_from_posts == 10
        assert basic_guide.tone_consistency_score == 0.85
        assert basic_guide.generated_at is not None

    def test_guide_with_optional_fields(self):
        """Test guide with all optional fields populated."""
        guide = EnhancedVoiceGuide(
            company_name="Full Company",
            generated_from_posts=30,
            tone_consistency_score=0.9,
            average_word_count=220,
            average_paragraph_count=4.0,
            question_usage_rate=0.7,
            dominant_tones=["professional", "friendly"],
            average_readability_score=75.5,
            voice_dimensions={
                "formality": {"dominant": "casual"},
                "tone": {"dominant": "friendly"},
                "perspective": {"dominant": "first_person"},
            },
            sentence_variety="high",
            voice_archetype="Friend",
            source="client_samples",
            sample_count=5,
            sample_source="linkedin",
            emoji_frequency=1.5,
            common_emojis=["🚀", "✅", "💡"],
            jargon_ratio=0.15,
            industry_terms=["SaaS", "API", "KPI"],
        )

        assert guide.average_readability_score == 75.5
        assert guide.voice_archetype == "Friend"
        assert len(guide.common_emojis) == 3
        assert guide.jargon_ratio == 0.15


class TestToMarkdownBasic:
    """Tests for to_markdown method - basic output."""

    def test_to_markdown_header(self):
        """Test markdown header section."""
        guide = EnhancedVoiceGuide(
            company_name="Test Co",
            generated_from_posts=15,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
        )

        markdown = guide.to_markdown()

        assert "# Enhanced Brand Voice Guide: Test Co" in markdown
        assert "15 posts" in markdown

    def test_to_markdown_dominant_tones(self):
        """Test markdown with dominant tones."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.75,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            dominant_tones=["professional", "authoritative"],
        )

        markdown = guide.to_markdown()

        assert "**Dominant Tones:** Professional, Authoritative" in markdown

    def test_to_markdown_high_consistency_score(self):
        """Test checkmark for high consistency score (>= 70%)."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.85,  # 85% >= 70%
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
        )

        markdown = guide.to_markdown()

        assert "85% ✓" in markdown

    def test_to_markdown_low_consistency_score(self):
        """Test tilde for low consistency score (< 70%)."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.65,  # 65% < 70%
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
        )

        markdown = guide.to_markdown()

        assert "65% ~" in markdown


class TestToMarkdownVoiceMetrics:
    """Tests for to_markdown voice metrics section."""

    def test_voice_metrics_with_archetype(self):
        """Test voice metrics section with archetype."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            voice_archetype="Expert",
        )

        markdown = guide.to_markdown()

        assert "### Voice Metrics" in markdown
        assert "**Brand Archetype:** Expert" in markdown

    def test_readability_very_easy(self):
        """Test readability score >= 80 (Very Easy)."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            average_readability_score=85.0,
        )

        markdown = guide.to_markdown()

        assert "Very Easy - 6th grade" in markdown

    def test_readability_fairly_easy(self):
        """Test readability score 70-79 (Fairly Easy)."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            average_readability_score=75.0,
        )

        markdown = guide.to_markdown()

        assert "Fairly Easy - 7th grade" in markdown

    def test_readability_standard(self):
        """Test readability score 60-69 (Standard)."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            average_readability_score=65.0,
        )

        markdown = guide.to_markdown()

        assert "Standard - 8th-9th grade" in markdown

    def test_readability_fairly_difficult(self):
        """Test readability score 50-59 (Fairly Difficult)."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            average_readability_score=55.0,
        )

        markdown = guide.to_markdown()

        assert "Fairly Difficult - High school" in markdown

    def test_readability_difficult(self):
        """Test readability score < 50 (Difficult)."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            average_readability_score=45.0,
        )

        markdown = guide.to_markdown()

        assert "Difficult - College level" in markdown

    def test_sentence_variety_low(self):
        """Test sentence variety low."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            voice_archetype="Test",  # Needed to show metrics section
            sentence_variety="low",
        )

        markdown = guide.to_markdown()

        assert "**Sentence Variety:** Low 📉" in markdown

    def test_sentence_variety_medium(self):
        """Test sentence variety medium."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            voice_archetype="Test",
            sentence_variety="medium",
        )

        markdown = guide.to_markdown()

        assert "**Sentence Variety:** Medium 📊" in markdown

    def test_sentence_variety_high(self):
        """Test sentence variety high."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            voice_archetype="Test",
            sentence_variety="high",
        )

        markdown = guide.to_markdown()

        assert "**Sentence Variety:** High 📈" in markdown

    def test_voice_dimensions(self):
        """Test voice dimensions display."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            voice_archetype="Guide",
            voice_dimensions={
                "formality": {"dominant": "casual"},
                "tone": {"dominant": "friendly"},
                "perspective": {"dominant": "first_person"},
            },
        )

        markdown = guide.to_markdown()

        assert "**Voice Dimensions:**" in markdown
        assert "Formality: Casual" in markdown
        assert "Tone: Friendly" in markdown
        assert "Perspective: First_Person" in markdown


class TestToMarkdownPatterns:
    """Tests for to_markdown pattern sections."""

    def test_opening_hooks(self):
        """Test opening hooks section."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            common_opening_hooks=[
                VoicePattern(
                    pattern_type="opening",
                    examples=["Did you know that...", "Ever wondered why..."],
                    frequency=8,
                    description="Question hook",
                )
            ],
        )

        markdown = guide.to_markdown()

        assert "## Opening Hooks" in markdown
        assert "**Question hook**" in markdown
        assert "appears 8 times" in markdown
        assert "Did you know that..." in markdown

    def test_common_transitions(self):
        """Test common transitions section."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            common_transitions=[
                VoicePattern(
                    pattern_type="transition",
                    examples=["Here's the thing:", "But wait, there's more"],
                    frequency=5,
                    description="Attention grabber",
                )
            ],
        )

        markdown = guide.to_markdown()

        assert "## Common Transitions" in markdown
        assert "Here's the thing:" in markdown
        assert "5 times" in markdown
        assert "**Pattern:** Attention grabber" in markdown

    def test_cta_with_questions(self):
        """Test CTA patterns with question CTAs."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            common_ctas=[
                VoicePattern(
                    pattern_type="cta",
                    examples=["What do you think?", "Have you tried this?"],
                    frequency=6,
                    description="Engagement question",
                ),
                VoicePattern(
                    pattern_type="cta",
                    examples=["Learn more", "Click here"],
                    frequency=4,
                    description="Direct action",
                ),
            ],
        )

        markdown = guide.to_markdown()

        assert "## Call-to-Action Patterns" in markdown
        assert "**Open-ended questions**" in markdown
        assert "6 posts" in markdown
        assert "**Direct action**" in markdown
        assert "4 posts" in markdown

    def test_cta_without_questions(self):
        """Test CTA patterns without question CTAs."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            common_ctas=[
                VoicePattern(
                    pattern_type="cta",
                    examples=["Sign up now", "Try it free"],
                    frequency=7,
                    description="Direct call to action",
                )
            ],
        )

        markdown = guide.to_markdown()

        assert "## Call-to-Action Patterns" in markdown
        assert "**Direct call to action**" in markdown
        assert "7 posts" in markdown

    def test_key_phrases(self):
        """Test key phrases section."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            key_phrases_used=["game changer", "bottom line", "at the end of the day"],
        )

        markdown = guide.to_markdown()

        assert "## Key Phrases (Used 3+ Times)" in markdown
        assert '"game changer"' in markdown
        assert '"bottom line"' in markdown


class TestToMarkdownStructure:
    """Tests for to_markdown structural patterns section."""

    def test_mid_length_posts_insight(self):
        """Test insight for mid-length posts (200-250 words)."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=225,  # Between 200 and 250
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
        )

        markdown = guide.to_markdown()

        assert "You favor mid-length posts (200-250 words)" in markdown

    def test_concise_posts_insight(self):
        """Test insight for concise posts (<200 words)."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=150,  # < 200
            average_paragraph_count=2.0,
            question_usage_rate=0.5,
        )

        markdown = guide.to_markdown()

        assert "You write concise posts (<200 words)" in markdown

    def test_detailed_posts_insight(self):
        """Test insight for detailed posts (>250 words)."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=300,  # > 250
            average_paragraph_count=5.0,
            question_usage_rate=0.5,
        )

        markdown = guide.to_markdown()

        assert "You write detailed posts (>250 words)" in markdown


class TestToMarkdownGuidelines:
    """Tests for to_markdown guidelines section."""

    def test_dos_section(self):
        """Test DO recommendations section."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            dos=["Use active voice", "Include statistics", "Ask questions"],
        )

        markdown = guide.to_markdown()

        assert "### ✅ DO:" in markdown
        assert "- Use active voice" in markdown
        assert "- Include statistics" in markdown
        assert "- Ask questions" in markdown

    def test_donts_section(self):
        """Test DON'T recommendations section."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            donts=["Use jargon", "Write long paragraphs", "Be overly formal"],
        )

        markdown = guide.to_markdown()

        assert "### ❌ DON'T:" in markdown
        assert "- Use jargon" in markdown
        assert "- Write long paragraphs" in markdown

    def test_examples_section(self):
        """Test strong examples section."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            examples=["This is a great opening hook that captures attention."],
        )

        markdown = guide.to_markdown()

        assert "## Strong Examples" in markdown
        assert "**Example:**" in markdown
        assert "> This is a great opening hook" in markdown


class TestToMarkdownEmptyFields:
    """Tests for to_markdown with empty optional fields."""

    def test_no_optional_sections(self):
        """Test markdown with no optional fields populated."""
        guide = EnhancedVoiceGuide(
            company_name="Minimal Co",
            generated_from_posts=5,
            tone_consistency_score=0.7,
            average_word_count=180,
            average_paragraph_count=2.5,
            question_usage_rate=0.3,
            # All optional fields default to empty/None
        )

        markdown = guide.to_markdown()

        # Should still have basic sections
        assert "# Enhanced Brand Voice Guide: Minimal Co" in markdown
        assert "## Structural Patterns" in markdown
        assert "## Writing Guidelines" in markdown

        # Should not have sections that require data
        assert "## Opening Hooks" not in markdown
        assert "## Common Transitions" not in markdown
        assert "## Call-to-Action Patterns" not in markdown
        assert "## Key Phrases" not in markdown
        assert "### Voice Metrics" not in markdown


class TestEnhancedVoiceGuideValidationBoundaries:
    """Boundary-value tests for EnhancedVoiceGuide field validators."""

    def test_tone_consistency_score_at_zero(self):
        """tone_consistency_score of exactly 0.0 is valid."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=1,
            tone_consistency_score=0.0,
            average_word_count=0,
            average_paragraph_count=0.0,
            question_usage_rate=0.0,
        )
        assert guide.tone_consistency_score == 0.0

    def test_tone_consistency_score_at_one(self):
        """tone_consistency_score of exactly 1.0 is valid."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=1,
            tone_consistency_score=1.0,
            average_word_count=0,
            average_paragraph_count=0.0,
            question_usage_rate=0.0,
        )
        assert guide.tone_consistency_score == 1.0

    def test_question_usage_rate_boundaries(self):
        """question_usage_rate of 0.0 and 1.0 are both valid."""
        for rate in (0.0, 1.0):
            guide = EnhancedVoiceGuide(
                company_name="Test",
                generated_from_posts=1,
                tone_consistency_score=0.5,
                average_word_count=100,
                average_paragraph_count=2.0,
                question_usage_rate=rate,
            )
            assert guide.question_usage_rate == rate

    def test_generated_from_posts_minimum_one(self):
        """generated_from_posts must be at least 1."""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            EnhancedVoiceGuide(
                company_name="Test",
                generated_from_posts=0,  # below minimum
                tone_consistency_score=0.5,
                average_word_count=100,
                average_paragraph_count=2.0,
                question_usage_rate=0.5,
            )

    def test_average_readability_score_boundaries(self):
        """average_readability_score accepts 0.0 and 100.0."""
        for score in (0.0, 100.0):
            guide = EnhancedVoiceGuide(
                company_name="Test",
                generated_from_posts=1,
                tone_consistency_score=0.5,
                average_word_count=100,
                average_paragraph_count=2.0,
                question_usage_rate=0.5,
                average_readability_score=score,
            )
            assert guide.average_readability_score == score

    def test_jargon_ratio_boundaries(self):
        """jargon_ratio accepts 0.0 and 1.0."""
        for ratio in (0.0, 1.0):
            guide = EnhancedVoiceGuide(
                company_name="Test",
                generated_from_posts=1,
                tone_consistency_score=0.5,
                average_word_count=100,
                average_paragraph_count=2.0,
                question_usage_rate=0.5,
                jargon_ratio=ratio,
            )
            assert guide.jargon_ratio == ratio

    def test_sample_count_zero_is_valid(self):
        """sample_count of 0 is valid (ge=0)."""
        guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=1,
            tone_consistency_score=0.5,
            average_word_count=100,
            average_paragraph_count=2.0,
            question_usage_rate=0.5,
            sample_count=0,
        )
        assert guide.sample_count == 0


class TestVoicePatternValidation:
    """Additional VoicePattern validation tests."""

    def test_voice_pattern_all_types(self):
        """VoicePattern accepts all documented pattern_type values."""
        for ptype in ("opening", "transition", "cta", "tone"):
            pattern = VoicePattern(
                pattern_type=ptype,
                examples=["example"],
                frequency=1,
                description="desc",
            )
            assert pattern.pattern_type == ptype

    def test_voice_pattern_multiple_examples(self):
        """VoicePattern stores all provided examples."""
        pattern = VoicePattern(
            pattern_type="opening",
            examples=["ex1", "ex2", "ex3"],
            frequency=3,
            description="Multi-example pattern",
        )
        assert len(pattern.examples) == 3
        assert "ex3" in pattern.examples


class TestToMarkdownNewSections:
    """Cover to_markdown branches for Phase 8C and brand-voice-guide fields."""

    def _base_guide(self, **kwargs) -> EnhancedVoiceGuide:
        defaults = dict(
            company_name="Test",
            generated_from_posts=10,
            tone_consistency_score=0.8,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
        )
        defaults.update(kwargs)
        return EnhancedVoiceGuide(**defaults)

    def test_voice_spectrum_section(self):
        """Voice spectrum section appears when voice_spectrum is set."""
        guide = self._base_guide(
            voice_spectrum={
                "formal_casual": "Slightly Casual",
                "serious_playful": "Serious",
                "authoritative_collaborative": "Collaborative",
                "technical_simple": "Simple",
                "traditional_innovative": "Innovative",
            }
        )
        markdown = guide.to_markdown()

        assert "## Voice Spectrum" in markdown
        assert "Formal ←→ Casual" in markdown
        assert "Slightly Casual" in markdown
        assert "Traditional ←→ Innovative" in markdown
        assert "Innovative" in markdown

    def test_voice_spectrum_missing_key_skipped(self):
        """Keys absent from voice_spectrum dict are simply not rendered."""
        guide = self._base_guide(
            voice_spectrum={"formal_casual": "Formal"}
            # other keys absent
        )
        markdown = guide.to_markdown()

        assert "## Voice Spectrum" in markdown
        assert "Formal ←→ Casual" in markdown
        assert "Serious ←→ Playful" not in markdown

    def test_tone_by_channel_section(self):
        """Tone-by-channel section appears when tone_by_channel is set."""
        guide = self._base_guide(
            tone_by_channel={
                "linkedin": "Professional and concise",
                "twitter": "Casual and punchy",
                "email": "Warm and direct",
                "blog": "In-depth and educational",
            }
        )
        markdown = guide.to_markdown()

        assert "## Tone Variations by Channel" in markdown
        assert "Linkedin" in markdown
        assert "Professional and concise" in markdown
        assert "Twitter" in markdown

    def test_tone_by_channel_unknown_channel_gets_default_emoji(self):
        """Unknown channel key uses fallback emoji (📱) rather than raising."""
        guide = self._base_guide(tone_by_channel={"tiktok": "Short and entertaining"})
        markdown = guide.to_markdown()

        assert "Tiktok" in markdown
        assert "Short and entertaining" in markdown

    def test_words_to_use_section(self):
        """Words to use section appears when words_to_use is populated."""
        guide = self._base_guide(words_to_use=["empower", "transform", "results"])
        markdown = guide.to_markdown()

        assert "Words & Phrases to USE" in markdown
        assert '"empower"' in markdown
        assert '"transform"' in markdown

    def test_words_to_avoid_section(self):
        """Words to avoid section appears when words_to_avoid is populated."""
        guide = self._base_guide(words_to_avoid=["synergy", "leverage", "disruptive"])
        markdown = guide.to_markdown()

        assert "Words & Phrases to AVOID" in markdown
        assert '"synergy"' in markdown

    def test_punctuation_style_section(self):
        """Punctuation style line appears when punctuation_style is set."""
        guide = self._base_guide(punctuation_style="Oxford comma; avoid exclamation marks")
        markdown = guide.to_markdown()

        assert "**Punctuation Style:** Oxford comma; avoid exclamation marks" in markdown

    def test_consistency_checklist_section(self):
        """Consistency checklist section appears when populated."""
        guide = self._base_guide(
            consistency_checklist=[
                "Does the tone match our brand?",
                "Is the CTA present?",
                "Are key phrases used naturally?",
            ]
        )
        markdown = guide.to_markdown()

        assert "## Voice Consistency Checklist" in markdown
        assert "- [ ] Does the tone match our brand?" in markdown
        assert "- [ ] Is the CTA present?" in markdown

    def test_industry_terms_section(self):
        """industry_terms is stored and accessible (part of Phase 8C fields)."""
        guide = self._base_guide(
            industry_terms=["SaaS", "MRR", "churn"],
            jargon_ratio=0.08,
        )
        assert guide.industry_terms == ["SaaS", "MRR", "churn"]
        assert guide.jargon_ratio == 0.08

    def test_emoji_frequency_and_common_emojis(self):
        """emoji_frequency and common_emojis are stored (Phase 8C)."""
        guide = self._base_guide(
            emoji_frequency=2.5,
            common_emojis=["🚀", "✅"],
        )
        assert guide.emoji_frequency == 2.5
        assert "🚀" in guide.common_emojis

    def test_source_and_sample_metadata_stored(self):
        """source, sample_count, sample_source, sample_upload_date are stored."""
        from datetime import datetime

        upload_ts = datetime(2025, 1, 15, 12, 0, 0)
        guide = self._base_guide(
            source="client_samples",
            sample_count=12,
            sample_source="linkedin",
            sample_upload_date=upload_ts,
        )

        assert guide.source == "client_samples"
        assert guide.sample_count == 12
        assert guide.sample_source == "linkedin"
        assert guide.sample_upload_date == upload_ts

    def test_words_lists_capped_at_ten_in_output(self):
        """Only the first 10 words are rendered in the markdown output."""
        guide = self._base_guide(
            words_to_use=[f"word{i}" for i in range(15)],
            words_to_avoid=[f"avoid{i}" for i in range(15)],
        )
        markdown = guide.to_markdown()

        # word10..14 should NOT appear (only first 10 rendered)
        assert '"word9"' in markdown
        assert '"word10"' not in markdown
        assert '"avoid9"' in markdown
        assert '"avoid10"' not in markdown
