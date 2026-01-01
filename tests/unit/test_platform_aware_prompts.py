"""
Unit tests for platform-aware prompt generation in ContentGeneratorAgent

Tests verify that:
1. System prompts are correctly customized per platform
2. Length requirements are properly enforced
3. Blog posts get structure requirements
4. Twitter/Facebook get critical length warnings
5. Platform-specific guidelines are included
"""
import pytest

from src.agents.content_generator import ContentGeneratorAgent
from src.models.client_brief import ClientBrief, Platform, TonePreference


class TestPlatformAwarePrompts:
    """Test platform-specific prompt generation"""

    @pytest.fixture
    def sample_brief(self):
        """Create a sample client brief for testing"""
        return ClientBrief(
            company_name="Test Company",
            business_description="We test things",
            ideal_customer="Software developers",
            main_problem_solved="Testing complexity",
            customer_pain_points=["Slow tests", "Flaky tests"],
            brand_personality=[TonePreference.DIRECT, TonePreference.AUTHORITATIVE],
            key_phrases=["ship fast", "move fast"],
            target_platforms=[Platform.LINKEDIN],
        )

    @pytest.fixture
    def generator(self):
        """Create ContentGeneratorAgent instance"""
        return ContentGeneratorAgent()

    def test_base_prompt_no_hardcoded_length(self, generator):
        """Test that base CONTENT_GENERATOR prompt doesn't have hardcoded length"""
        base_prompt = generator.SYSTEM_PROMPT

        # Should NOT contain hardcoded "150-250 words"
        assert "150-250 words (LinkedIn/Twitter sweet spot)" not in base_prompt
        assert "Aim for 150-250 words" not in base_prompt

        # Should defer to platform-specific targets
        assert "Follow platform-specific length targets" in base_prompt or "will be specified" in base_prompt

    def test_linkedin_prompt_construction(self, generator, sample_brief):
        """Test LinkedIn prompt includes correct specifications"""
        prompt = generator._build_system_prompt(sample_brief, Platform.LINKEDIN)

        # Should include platform header
        assert "PLATFORM-SPECIFIC REQUIREMENTS FOR LINKEDIN" in prompt
        assert "=" * 60 in prompt

        # Should include LinkedIn target length
        assert "200-300 words" in prompt
        assert "TARGET LENGTH" in prompt

        # Should include client voice
        assert "direct" in prompt.lower() or "authoritative" in prompt.lower()

        # Should include key phrases
        assert "ship fast" in prompt
        assert "move fast" in prompt

    def test_twitter_prompt_critical_warnings(self, generator, sample_brief):
        """Test Twitter prompt includes critical length warnings"""
        prompt = generator._build_system_prompt(sample_brief, Platform.TWITTER)

        # Should include platform header
        assert "PLATFORM-SPECIFIC REQUIREMENTS FOR TWITTER" in prompt

        # Should include Twitter target length
        assert "12-18 words" in prompt

        # Should include critical warning emoji
        assert "🚨" in prompt

        # Should warn about validation failure
        assert "FAIL" in prompt or "will be rejected" in prompt or "HARD LIMIT" in prompt

        # Should emphasize word economy
        assert "EVERY word count" in prompt or "earn its place" in prompt

        # Should include length reminder at end
        assert "📏 REMINDER" in prompt
        assert "DO NOT EXCEED" in prompt

    def test_facebook_prompt_critical_warnings(self, generator, sample_brief):
        """Test Facebook prompt includes critical length warnings"""
        prompt = generator._build_system_prompt(sample_brief, Platform.FACEBOOK)

        # Should include platform header
        assert "PLATFORM-SPECIFIC REQUIREMENTS FOR FACEBOOK" in prompt

        # Should include Facebook target length
        assert "10-15 words" in prompt

        # Should include critical warning
        assert "🚨" in prompt

        # Should warn about validation
        assert "FAIL" in prompt or "will be rejected" in prompt or "HARD LIMIT" in prompt

    def test_blog_prompt_structure_requirements(self, generator, sample_brief):
        """Test blog prompt includes structure requirements"""
        prompt = generator._build_system_prompt(sample_brief, Platform.BLOG)

        # Should include platform header
        assert "PLATFORM-SPECIFIC REQUIREMENTS FOR BLOG" in prompt

        # Should include blog target length
        assert "1,500-2,000 words" in prompt or "1500-2000 words" in prompt

        # Should include structure requirements
        assert "BLOG POST STRUCTURE REQUIREMENTS" in prompt

        # Should specify introduction section
        assert "Introduction" in prompt
        assert "150-200 words" in prompt

        # Should specify body section
        assert "Body" in prompt
        assert "1200-1600 words" in prompt or "1,200-1,600 words" in prompt

        # Should specify conclusion section
        assert "Conclusion" in prompt

        # Should require H2 headers
        assert "H2 headers" in prompt or "## Header" in prompt

        # Should require H3 headers
        assert "H3 headers" in prompt or "### Subheader" in prompt

        # Should mention SEO
        assert "SEO" in prompt or "search intent" in prompt

        # Should mention link placeholders
        assert "[LINK:" in prompt or "link placeholders" in prompt

    def test_email_prompt_no_critical_warning(self, generator, sample_brief):
        """Test email prompt doesn't get critical warnings (normal length platform)"""
        prompt = generator._build_system_prompt(sample_brief, Platform.EMAIL)

        # Should include platform header
        assert "PLATFORM-SPECIFIC REQUIREMENTS FOR EMAIL" in prompt

        # Should include email target length
        assert "150-250 words" in prompt

        # Should NOT include critical emoji (email length is manageable)
        assert "🚨 CRITICAL" not in prompt

        # Should still include reminder
        assert "📏 REMINDER" in prompt

    def test_all_platforms_have_headers(self, generator, sample_brief):
        """Test all platforms get prominent headers"""
        platforms = [
            Platform.LINKEDIN,
            Platform.TWITTER,
            Platform.FACEBOOK,
            Platform.BLOG,
            Platform.EMAIL,
        ]

        for platform in platforms:
            prompt = generator._build_system_prompt(sample_brief, platform)

            # All should have separator
            assert "=" * 60 in prompt

            # All should have platform name in header
            assert f"PLATFORM-SPECIFIC REQUIREMENTS FOR {platform.value.upper()}" in prompt

            # All should have target length
            assert "TARGET LENGTH" in prompt

            # All should have reminder at end
            assert "📏 REMINDER" in prompt

    def test_all_platforms_have_guidelines(self, generator, sample_brief):
        """Test all platforms include platform-specific guidelines"""
        platforms = [
            Platform.LINKEDIN,
            Platform.TWITTER,
            Platform.FACEBOOK,
            Platform.BLOG,
            Platform.EMAIL,
        ]

        for platform in platforms:
            prompt = generator._build_system_prompt(sample_brief, platform)

            # Should include platform name
            assert platform.value in prompt.lower()

            # Should have guidelines section (non-empty prompt)
            assert len(prompt) > 500  # Substantial content

    def test_prompt_includes_client_specifics(self, generator, sample_brief):
        """Test prompt includes client-specific customizations"""
        prompt = generator._build_system_prompt(sample_brief, Platform.LINKEDIN)

        # Should include brand personality
        assert "direct" in prompt.lower() or "authoritative" in prompt.lower()

        # Should include key phrases section
        assert "KEY PHRASES" in prompt
        assert "ship fast" in prompt
        assert "move fast" in prompt

    def test_prompt_with_misconceptions(self, generator):
        """Test prompt includes misconceptions when provided"""
        brief = ClientBrief(
            company_name="Test Company",
            business_description="We test things",
            ideal_customer="Developers",
            main_problem_solved="Bugs",
            customer_pain_points=["Flaky tests"],
            misconceptions=["Testing is slow", "Tests are expensive"],
        )

        prompt = generator._build_system_prompt(brief, Platform.LINKEDIN)

        # Should include misconceptions
        assert "MISCONCEPTIONS" in prompt
        assert "Testing is slow" in prompt
        assert "Tests are expensive" in prompt

    def test_short_platforms_get_strict_enforcement(self, generator, sample_brief):
        """Test Twitter and Facebook get strict length enforcement"""
        short_platforms = [Platform.TWITTER, Platform.FACEBOOK]

        for platform in short_platforms:
            prompt = generator._build_system_prompt(sample_brief, platform)

            # Should have critical warning
            assert "🚨 CRITICAL" in prompt

            # Should mention word limit
            assert "words" in prompt

            # Should emphasize strictness
            assert "MUST" in prompt or "STRICTLY" in prompt

    def test_linkedin_no_critical_warning(self, generator, sample_brief):
        """Test LinkedIn doesn't get critical emoji (more flexible length)"""
        prompt = generator._build_system_prompt(sample_brief, Platform.LINKEDIN)

        # LinkedIn is more flexible, shouldn't have critical warning
        assert "🚨 CRITICAL" not in prompt

        # But should still have target and reminder
        assert "TARGET LENGTH" in prompt
        assert "📏 REMINDER" in prompt

    def test_blog_only_gets_structure_requirements(self, generator, sample_brief):
        """Test only blog posts get structure requirements"""
        non_blog_platforms = [
            Platform.LINKEDIN,
            Platform.TWITTER,
            Platform.FACEBOOK,
            Platform.EMAIL,
        ]

        for platform in non_blog_platforms:
            prompt = generator._build_system_prompt(sample_brief, platform)

            # Should NOT have blog structure requirements
            assert "BLOG POST STRUCTURE REQUIREMENTS" not in prompt
            assert "H2 headers" not in prompt

    def test_prompt_length_reasonable(self, generator, sample_brief):
        """Test prompts aren't excessively long (token efficiency)"""
        platforms = [
            Platform.LINKEDIN,
            Platform.TWITTER,
            Platform.FACEBOOK,
            Platform.BLOG,
            Platform.EMAIL,
        ]

        for platform in platforms:
            prompt = generator._build_system_prompt(sample_brief, platform)

            # Prompt should be substantial but not excessive
            assert len(prompt) > 500  # Has content
            assert len(prompt) < 5000  # Not too long (except blog might be longer)

            # Blog can be longer due to structure requirements
            if platform == Platform.BLOG:
                assert len(prompt) < 6000  # Still reasonable


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
