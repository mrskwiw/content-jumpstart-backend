"""Tests for skill integrations

Tests the integration of external skills from the skills repository:
- Hook copywriting frameworks
- SEO validation for blog posts
- Enhanced voice guide fields
- Calendar optimization
"""

from src.config.hook_frameworks import (
    build_hook_guidance,
    get_frameworks_for_template,
    get_framework_by_name,
    get_power_words_for_emotion,
    get_all_power_words,
    PRIMARY_FRAMEWORKS,
    SECONDARY_FRAMEWORKS,
    ADVANCED_FRAMEWORKS,
    ALL_FRAMEWORKS,
    HookCategory,
)
from src.validators.seo_validator import SEOValidator
from src.models.client_brief import Platform
from src.models.post import Post
from src.models.voice_guide import EnhancedVoiceGuide
from src.utils.schedule_generator import ScheduleGenerator


class TestHookFrameworks:
    """Test hook copywriting frameworks integration"""

    def test_frameworks_exist(self):
        """Verify all framework categories are populated"""
        assert len(PRIMARY_FRAMEWORKS) == 5
        assert len(SECONDARY_FRAMEWORKS) == 5
        assert len(ADVANCED_FRAMEWORKS) == 5
        assert len(ALL_FRAMEWORKS) == 15

    def test_framework_structure(self):
        """Verify framework dataclass structure"""
        framework = PRIMARY_FRAMEWORKS[0]
        assert framework.name == "Curiosity Gap"
        assert framework.category == HookCategory.CURIOSITY_BASED
        assert framework.template  # Has template
        assert framework.example  # Has example
        assert len(framework.best_for) > 0
        assert len(framework.power_words) > 0

    def test_get_frameworks_for_template(self):
        """Test template-to-framework mapping"""
        # Problem recognition should get specific frameworks
        frameworks = get_frameworks_for_template("problem_recognition")
        assert len(frameworks) == 3
        framework_names = [fw.name for fw in frameworks]
        assert "Pain-Agitation-Solution" in framework_names

        # How-to should get different frameworks
        frameworks = get_frameworks_for_template("how_to")
        framework_names = [fw.name for fw in frameworks]
        assert "How-To Promise" in framework_names

        # Unknown template should get defaults
        frameworks = get_frameworks_for_template("unknown_template")
        assert len(frameworks) == 3  # Returns primary defaults

    def test_get_framework_by_name(self):
        """Test framework lookup by name"""
        framework = get_framework_by_name("Curiosity Gap")
        assert framework is not None
        assert framework.category == HookCategory.CURIOSITY_BASED

        # Case insensitive
        framework = get_framework_by_name("curiosity gap")
        assert framework is not None

        # Non-existent
        framework = get_framework_by_name("Not A Framework")
        assert framework is None

    def test_get_power_words(self):
        """Test power words retrieval"""
        urgency_words = get_power_words_for_emotion("urgency")
        assert "now" in urgency_words
        assert "limited" in urgency_words

        all_words = get_all_power_words()
        assert len(all_words) > 20  # Should have many words

    def test_build_hook_guidance(self):
        """Test hook guidance generation for system prompt"""
        guidance = build_hook_guidance(
            template_type="problem_recognition",
            platform="linkedin",
            include_examples=True,
        )

        assert "HOOK WRITING FRAMEWORKS" in guidance
        assert "Framework 1:" in guidance
        assert "Power Words" in guidance
        assert "Pain-Agitation-Solution" in guidance or "Curiosity Gap" in guidance


class TestSEOValidator:
    """Test SEO validation integration"""

    def test_validator_initialization(self):
        """Test SEO validator can be initialized"""
        validator = SEOValidator()
        assert validator.min_seo_score == 60

    def test_skip_non_blog_posts(self):
        """SEO validation should skip non-blog posts"""
        validator = SEOValidator()
        posts = [
            Post(
                content="Short LinkedIn post",
                template_id=1,
                template_name="Test",
                variant=1,
                client_name="Test",
                target_platform=Platform.LINKEDIN,
            )
        ]

        result = validator.validate(posts)
        assert result["skipped"] is True
        assert result["passed"] is True

    def test_validate_blog_posts(self):
        """SEO validation should analyze blog posts"""
        validator = SEOValidator()

        # Create a short blog post (should fail SEO)
        posts = [
            Post(
                content="# Test Blog\n\n## Section 1\n\nThis is too short.",
                template_id=1,
                template_name="Test",
                variant=1,
                client_name="Test",
                target_platform=Platform.BLOG,
            )
        ]

        result = validator.validate(posts)
        assert result["skipped"] is False
        assert "seo_scores" in result
        assert len(result["seo_scores"]) == 1
        # Short post should have low score
        assert result["average_score"] < 60

    def test_seo_score_components(self):
        """Test that SEO score considers multiple factors"""
        validator = SEOValidator()

        # Well-structured blog post
        good_content = """# Complete Guide to Testing

## Introduction

This is a well-structured blog post that should score reasonably well on SEO metrics.
We have proper headings, good paragraph structure, and reasonable length.

## Section One: Getting Started

Testing is important for software quality. Here are some key points to consider
when building your testing strategy. Make sure to include unit tests, integration
tests, and end-to-end tests in your test suite.

## Section Two: Best Practices

Follow these best practices for effective testing:

- Write tests before code (TDD)
- Test edge cases and error conditions
- Use meaningful test names
- Keep tests focused and independent

## Section Three: Tools and Frameworks

There are many tools available for testing. Consider using pytest for Python,
Jest for JavaScript, or JUnit for Java. Each has its strengths.

## Conclusion

Testing is a crucial part of software development. Start testing today!
"""
        posts = [
            Post(
                content=good_content,
                template_id=1,
                template_name="Test",
                variant=1,
                client_name="Test",
                target_platform=Platform.BLOG,
            )
        ]

        result = validator.validate(posts)
        # Better structured post should score higher
        assert result["average_score"] > 30

    def test_structure_analysis(self):
        """Test that structure is analyzed correctly"""
        validator = SEOValidator()

        content = """# Title

## Heading 2

Some text here.

## Another Heading

- List item 1
- List item 2

[Link](/page)
"""
        # Access private method for testing
        structure = validator._analyze_structure(content)

        assert structure["headings"]["h1"] == 1
        assert structure["headings"]["h2"] == 2
        assert structure["lists"] == 2
        assert structure["links"]["internal"] == 1

    def test_readability_analysis(self):
        """Test readability scoring"""
        validator = SEOValidator()

        # Simple text
        simple = "This is easy. Short sentences. Simple words."
        result = validator._analyze_readability(simple)
        assert result["level"] == "Easy"
        assert result["score"] == 90

        # Complex text
        complex_text = (
            "The implementation of sophisticated algorithmic approaches "
            "necessitates comprehensive understanding of underlying theoretical "
            "frameworks and their practical applications in contemporary "
            "computational environments."
        )
        result = validator._analyze_readability(complex_text)
        assert result["score"] < 90  # Should be harder to read


class TestEnhancedVoiceGuide:
    """Test enhanced voice guide fields from brand-voice-guide skill"""

    def test_voice_spectrum_fields(self):
        """Test voice spectrum fields exist"""
        guide = EnhancedVoiceGuide(
            company_name="Test Co",
            generated_from_posts=10,
            tone_consistency_score=0.85,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            voice_spectrum={
                "formal_casual": "Center-casual",
                "serious_playful": "Leans serious",
            },
        )

        assert guide.voice_spectrum is not None
        assert "formal_casual" in guide.voice_spectrum

    def test_language_guidelines_fields(self):
        """Test words to use/avoid fields"""
        guide = EnhancedVoiceGuide(
            company_name="Test Co",
            generated_from_posts=10,
            tone_consistency_score=0.85,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            words_to_use=["proven", "simple", "transform"],
            words_to_avoid=["synergy", "leverage"],
            punctuation_style="Oxford comma, minimal exclamation marks",
        )

        assert len(guide.words_to_use) == 3
        assert len(guide.words_to_avoid) == 2
        assert guide.punctuation_style is not None

    def test_tone_by_channel_field(self):
        """Test tone by channel field"""
        guide = EnhancedVoiceGuide(
            company_name="Test Co",
            generated_from_posts=10,
            tone_consistency_score=0.85,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            tone_by_channel={
                "linkedin": "Professional thought leadership",
                "twitter": "Punchy and engaging",
            },
        )

        assert guide.tone_by_channel is not None
        assert "linkedin" in guide.tone_by_channel

    def test_consistency_checklist_field(self):
        """Test consistency checklist field"""
        guide = EnhancedVoiceGuide(
            company_name="Test Co",
            generated_from_posts=10,
            tone_consistency_score=0.85,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            consistency_checklist=[
                "Opening hook grabs attention",
                "Tone matches brand",
                "Clear CTA",
            ],
        )

        assert len(guide.consistency_checklist) == 3

    def test_to_markdown_includes_new_sections(self):
        """Test that markdown output includes new sections"""
        guide = EnhancedVoiceGuide(
            company_name="Test Co",
            generated_from_posts=10,
            tone_consistency_score=0.85,
            average_word_count=200,
            average_paragraph_count=3.0,
            question_usage_rate=0.5,
            voice_spectrum={
                "formal_casual": "Center-casual",
                "technical_simple": "Simple - accessible",
            },
            words_to_use=["proven", "simple"],
            words_to_avoid=["synergy"],
            tone_by_channel={
                "linkedin": "Professional",
                "twitter": "Casual",
            },
            consistency_checklist=["Check hook", "Check CTA"],
        )

        markdown = guide.to_markdown()

        assert "Voice Spectrum" in markdown
        assert "Tone Variations by Channel" in markdown
        assert "Words & Phrases to USE" in markdown
        assert "Words & Phrases to AVOID" in markdown
        assert "Voice Consistency Checklist" in markdown


class TestCalendarOptimization:
    """Test calendar optimization from social-media-calendar skill"""

    def test_content_mix_strategy_constants(self):
        """Test content mix strategy constants exist"""
        gen = ScheduleGenerator()
        assert gen.CONTENT_MIX_STRATEGY["educational"] == 0.40
        assert gen.CONTENT_MIX_STRATEGY["engagement"] == 0.30
        assert gen.CONTENT_MIX_STRATEGY["promotional"] == 0.20
        assert gen.CONTENT_MIX_STRATEGY["personal"] == 0.10

    def test_template_content_categories(self):
        """Test template to content category mapping"""
        gen = ScheduleGenerator()

        # Educational templates
        assert gen.TEMPLATE_CONTENT_CATEGORIES[1] == "educational"  # Problem Recognition
        assert gen.TEMPLATE_CONTENT_CATEGORIES[9] == "educational"  # How-To

        # Engagement templates
        assert gen.TEMPLATE_CONTENT_CATEGORIES[5] == "engagement"  # Question Post

        # Personal templates
        assert gen.TEMPLATE_CONTENT_CATEGORIES[6] == "personal"  # Personal Story

        # Promotional templates
        assert gen.TEMPLATE_CONTENT_CATEGORIES[15] == "promotional"  # Milestone

    def test_analyze_content_mix(self):
        """Test content mix analysis"""
        gen = ScheduleGenerator()

        # Create posts with known templates
        posts = [
            Post(
                content="Test", template_id=1, template_name="T", variant=1, client_name="C"
            ),  # educational
            Post(
                content="Test", template_id=2, template_name="T", variant=1, client_name="C"
            ),  # educational
            Post(
                content="Test", template_id=5, template_name="T", variant=1, client_name="C"
            ),  # engagement
            Post(
                content="Test", template_id=6, template_name="T", variant=1, client_name="C"
            ),  # personal
        ]

        result = gen.analyze_content_mix(posts)

        assert result["distribution"]["educational"] == 2
        assert result["distribution"]["engagement"] == 1
        assert result["distribution"]["personal"] == 1
        assert result["distribution"]["promotional"] == 0

        # Should recommend adding promotional content
        assert any("promotional" in rec for rec in result["recommendations"])

    def test_analyze_content_mix_empty(self):
        """Test content mix analysis with no posts"""
        gen = ScheduleGenerator()
        result = gen.analyze_content_mix([])

        assert result["balanced"] is True
        assert "No posts to analyze" in result["recommendations"]

    def test_analyze_content_mix_balanced(self):
        """Test content mix analysis with balanced distribution"""
        gen = ScheduleGenerator()

        # Create 10 posts with ideal distribution (4 edu, 3 engage, 2 promo, 1 personal)
        posts = [
            Post(
                content="Test", template_id=1, template_name="T", variant=1, client_name="C"
            ),  # edu
            Post(
                content="Test", template_id=2, template_name="T", variant=1, client_name="C"
            ),  # edu
            Post(
                content="Test", template_id=9, template_name="T", variant=1, client_name="C"
            ),  # edu
            Post(
                content="Test", template_id=10, template_name="T", variant=1, client_name="C"
            ),  # edu
            Post(
                content="Test", template_id=5, template_name="T", variant=1, client_name="C"
            ),  # engage
            Post(
                content="Test", template_id=14, template_name="T", variant=1, client_name="C"
            ),  # engage
            Post(
                content="Test", template_id=3, template_name="T", variant=1, client_name="C"
            ),  # engage
            Post(
                content="Test", template_id=15, template_name="T", variant=1, client_name="C"
            ),  # promo
            Post(
                content="Test", template_id=15, template_name="T", variant=2, client_name="C"
            ),  # promo
            Post(
                content="Test", template_id=6, template_name="T", variant=1, client_name="C"
            ),  # personal
        ]

        result = gen.analyze_content_mix(posts)

        # Should be close to balanced
        assert result["distribution"]["educational"] == 4
        assert result["distribution"]["engagement"] == 3
        assert result["distribution"]["promotional"] == 2
        assert result["distribution"]["personal"] == 1

    def test_optimize_post_order(self):
        """Test post order optimization"""
        gen = ScheduleGenerator()

        # Create posts in non-optimal order (all same type together)
        posts = [
            Post(content="E1", template_id=1, template_name="T", variant=1, client_name="C"),  # edu
            Post(content="E2", template_id=2, template_name="T", variant=1, client_name="C"),  # edu
            Post(content="E3", template_id=9, template_name="T", variant=1, client_name="C"),  # edu
            Post(
                content="N1", template_id=5, template_name="T", variant=1, client_name="C"
            ),  # engage
            Post(
                content="N2", template_id=14, template_name="T", variant=1, client_name="C"
            ),  # engage
            Post(
                content="P1", template_id=6, template_name="T", variant=1, client_name="C"
            ),  # personal
        ]

        optimized = gen.optimize_post_order(posts)

        # Should have all posts
        assert len(optimized) == 6

        # Should interleave - first post should be educational
        assert gen.TEMPLATE_CONTENT_CATEGORIES.get(optimized[0].template_id) == "educational"

        # Should not have all educational posts together
        edu_positions = [
            i
            for i, p in enumerate(optimized)
            if gen.TEMPLATE_CONTENT_CATEGORIES.get(p.template_id) == "educational"
        ]
        # Positions should be spread out, not consecutive
        assert edu_positions != [0, 1, 2]  # Not all at beginning

    def test_schedule_generator_platform_notes(self):
        """Test platform-specific notes exist"""
        gen = ScheduleGenerator()

        assert Platform.LINKEDIN in gen.PLATFORM_NOTES
        assert "hashtags" in gen.PLATFORM_NOTES[Platform.LINKEDIN].lower()
        assert Platform.TWITTER in gen.PLATFORM_NOTES
        assert Platform.BLOG in gen.PLATFORM_NOTES
        assert "seo" in gen.PLATFORM_NOTES[Platform.BLOG].lower()
