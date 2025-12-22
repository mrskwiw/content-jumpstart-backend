"""
End-to-End Multi-Platform Content Generation Test

Tests the complete pipeline for all platforms:
1. Brief parsing
2. Platform-specific content generation
3. Platform-specific validation (Length, Hook, CTA, Headline)
4. Quality scoring
5. Output formatting

This test verifies that the entire system works correctly for:
- LinkedIn (200-300 words)
- Twitter (12-18 words)
- Facebook (10-15 words)
- Blog (1500-2000 words)
- Email (150-250 words)
"""

import pytest
from pathlib import Path
from typing import Dict, Any

from src.models.client_brief import ClientBrief, Platform
from src.agents.brief_parser import BriefParserAgent
from src.agents.content_generator import ContentGeneratorAgent
from src.validators.length_validator import LengthValidator
from src.validators.hook_validator import HookValidator
from src.validators.cta_validator import CTAValidator
from src.validators.headline_validator import HeadlineValidator
from src.models.post import Post


# Test brief content
TEST_BRIEF = """
COMPANY INFORMATION
Company Name: TechFlow Solutions
Business Description: B2B SaaS platform for project management and team collaboration
Website: www.techflow.com

IDEAL CUSTOMER PROFILE
Industry: Technology startups and SMBs
Company Size: 10-100 employees
Job Titles: CTOs, Engineering Managers, Product Managers
Pain Points: Scattered communication, missed deadlines, unclear priorities

CONTENT GOALS
Platform: LinkedIn
Tone: Professional and authoritative
Topics: Agile methodology, remote team management, productivity tools
Call-to-Action: Book a demo, download whitepaper

BRAND VOICE
We write clearly and directly. We avoid jargon. We back claims with data.
"""


@pytest.fixture
def brief_parser():
    """Brief parser agent"""
    return BriefParserAgent()


@pytest.fixture
def content_generator():
    """Content generator agent"""
    return ContentGeneratorAgent()


@pytest.fixture
def sample_brief_file(tmp_path):
    """Create temporary brief file"""
    brief_file = tmp_path / "test_brief.txt"
    brief_file.write_text(TEST_BRIEF)
    return brief_file


class TestMultiPlatformE2E:
    """End-to-end tests for multi-platform content generation"""

    @pytest.mark.asyncio
    async def test_linkedin_generation_and_validation(self, brief_parser, content_generator, sample_brief_file):
        """Test LinkedIn content generation (200-300 words) + validation"""
        # Step 1: Parse brief
        brief_data = brief_parser.parse_brief(str(sample_brief_file))
        brief = ClientBrief(**brief_data)

        # Step 2: Generate LinkedIn posts
        posts = await content_generator.generate_posts_async(
            brief=brief,
            template_ids=[1, 2, 3],  # Problem Recognition, Statistic, Contrarian
            platform=Platform.LINKEDIN,
            num_posts=3
        )

        # Verify generation
        assert len(posts) == 3
        assert all(isinstance(p, Post) for p in posts)
        assert all(p.target_platform == Platform.LINKEDIN for p in posts)

        # Step 3: Validate lengths
        length_validator = LengthValidator()
        length_results = length_validator.validate(posts)

        assert length_results["platform"] == "linkedin"
        assert length_results["optimal_range"] == "200-300 words"

        # Check that most posts are in optimal range
        in_range_count = sum(1 for p in posts if 200 <= p.word_count <= 300)
        assert in_range_count >= 2, f"Only {in_range_count}/3 posts in optimal 200-300 word range"

        # Step 4: Validate hooks
        hook_validator = HookValidator()
        hook_results = hook_validator.validate(posts)

        assert hook_results["platform"] == "linkedin"
        assert len(hook_results.get("hook_length_issues", [])) == 0, "Hooks should be under 140 chars"

        # Step 5: Validate CTAs
        cta_validator = CTAValidator()
        cta_results = cta_validator.validate(posts)

        assert cta_results["platform"] == "linkedin"
        assert cta_results["variety_threshold"] == 0.40, "LinkedIn should use 40% variety threshold"

        # Step 6: Validate headlines
        headline_validator = HeadlineValidator()
        headline_results = headline_validator.validate(posts)

        assert headline_results["platform"] == "linkedin"
        assert headline_results["min_elements"] == 2, "LinkedIn should require 2+ engagement elements"

        # Print summary
        print("\n=== LinkedIn Generation Summary ===")
        print(f"Posts generated: {len(posts)}")
        print(f"Word counts: {[p.word_count for p in posts]}")
        print(f"Length validation: {'✅' if length_results['passed'] else '❌'}")
        print(f"Hook validation: {'✅' if hook_results['passed'] else '❌'}")
        print(f"CTA validation: {'✅' if cta_results['passed'] else '❌'}")
        print(f"Headline validation: {'✅' if headline_results['passed'] else '❌'}")

    @pytest.mark.asyncio
    async def test_twitter_generation_and_validation(self, brief_parser, content_generator, sample_brief_file):
        """Test Twitter content generation (12-18 words) + validation"""
        # Step 1: Parse brief
        brief_data = brief_parser.parse_brief(str(sample_brief_file))
        brief = ClientBrief(**brief_data)

        # Step 2: Generate Twitter posts
        posts = await content_generator.generate_posts_async(
            brief=brief,
            template_ids=[1, 2, 5],  # Problem, Stat, Question
            platform=Platform.TWITTER,
            num_posts=3
        )

        # Verify generation
        assert len(posts) == 3
        assert all(p.target_platform == Platform.TWITTER for p in posts)

        # Step 3: Validate lengths
        length_validator = LengthValidator()
        length_results = length_validator.validate(posts)

        assert length_results["platform"] == "twitter"
        assert length_results["optimal_range"] == "12-18 words"

        # Check that posts are SHORT
        assert all(p.word_count <= 50 for p in posts), "Twitter posts must be under 50 words"

        # Check distribution buckets are Twitter-specific
        assert "0-10" in length_results["distribution"]
        assert "10-15" in length_results["distribution"]

        # Step 4: Validate hooks
        hook_validator = HookValidator()
        hook_results = hook_validator.validate(posts)

        assert hook_results["platform"] == "twitter"
        # Twitter posts should be under 100 chars for hook (entire post)

        # Step 5: Validate CTAs
        cta_validator = CTAValidator()
        cta_results = cta_validator.validate(posts)

        assert cta_results["platform"] == "twitter"
        assert cta_results["variety_threshold"] == 0.50, "Twitter should use 50% variety threshold"

        # Step 6: Validate headlines
        headline_validator = HeadlineValidator()
        headline_results = headline_validator.validate(posts)

        assert headline_results["platform"] == "twitter"
        assert headline_results["min_elements"] == 1, "Twitter should only require 1+ element"

        # Print summary
        print("\n=== Twitter Generation Summary ===")
        print(f"Posts generated: {len(posts)}")
        print(f"Word counts: {[p.word_count for p in posts]}")
        print(f"Character counts: {[len(p.content) for p in posts]}")
        print(f"Length validation: {'✅' if length_results['passed'] else '❌'}")
        print(f"Hook validation: {'✅' if hook_results['passed'] else '❌'}")
        print(f"CTA validation: {'✅' if cta_results['passed'] else '❌'}")
        print(f"Headline validation: {'✅' if headline_results['passed'] else '❌'}")

    @pytest.mark.asyncio
    async def test_facebook_generation_and_validation(self, brief_parser, content_generator, sample_brief_file):
        """Test Facebook content generation (10-15 words) + validation"""
        # Step 1: Parse brief
        brief_data = brief_parser.parse_brief(str(sample_brief_file))
        brief = ClientBrief(**brief_data)

        # Step 2: Generate Facebook posts
        posts = await content_generator.generate_posts_async(
            brief=brief,
            template_ids=[1, 5, 9],  # Problem, Question, How-To
            platform=Platform.FACEBOOK,
            num_posts=3
        )

        # Verify generation
        assert len(posts) == 3
        assert all(p.target_platform == Platform.FACEBOOK for p in posts)

        # Step 3: Validate lengths
        length_validator = LengthValidator()
        length_results = length_validator.validate(posts)

        assert length_results["platform"] == "facebook"
        assert length_results["optimal_range"] == "10-15 words"

        # Check that posts are ULTRA-SHORT
        assert all(p.word_count <= 25 for p in posts), "Facebook posts must be under 25 words"

        # Step 4: Validate CTAs
        cta_validator = CTAValidator()
        cta_results = cta_validator.validate(posts)

        assert cta_results["platform"] == "facebook"
        assert cta_results["variety_threshold"] == 0.50, "Facebook should use 50% variety threshold"

        # Print summary
        print("\n=== Facebook Generation Summary ===")
        print(f"Posts generated: {len(posts)}")
        print(f"Word counts: {[p.word_count for p in posts]}")
        print(f"Length validation: {'✅' if length_results['passed'] else '❌'}")
        print(f"CTA validation: {'✅' if cta_results['passed'] else '❌'}")

    @pytest.mark.asyncio
    async def test_blog_generation_and_validation(self, brief_parser, content_generator, sample_brief_file):
        """Test Blog content generation (1500-2000 words) + validation"""
        # Step 1: Parse brief
        brief_data = brief_parser.parse_brief(str(sample_brief_file))
        brief = ClientBrief(**brief_data)

        # Step 2: Generate Blog posts
        posts = await content_generator.generate_posts_async(
            brief=brief,
            template_ids=[9],  # How-To (best for blog format)
            platform=Platform.BLOG,
            num_posts=1  # Blogs are long, generate just 1
        )

        # Verify generation
        assert len(posts) == 1
        assert posts[0].target_platform == Platform.BLOG

        # Step 3: Validate lengths
        length_validator = LengthValidator()
        length_results = length_validator.validate(posts)

        assert length_results["platform"] == "blog"
        assert length_results["optimal_range"] == "1500-2000 words"

        # Check that blog is LONG
        assert posts[0].word_count >= 1500, f"Blog post only {posts[0].word_count} words, need 1500+"

        # Check for H2 headers (blog structure requirement)
        assert "##" in posts[0].content, "Blog should have H2 headers"

        # Step 4: Validate hooks
        hook_validator = HookValidator()
        hook_results = hook_validator.validate(posts)

        assert hook_results["platform"] == "blog"
        # Blog hook is first paragraph (word-based, not char-based)

        # Step 5: Validate headlines
        headline_validator = HeadlineValidator()
        headline_results = headline_validator.validate(posts)

        assert headline_results["platform"] == "blog"
        assert headline_results["min_elements"] == 3, "Blog should require 3+ engagement elements"

        # Print summary
        print("\n=== Blog Generation Summary ===")
        print(f"Posts generated: {len(posts)}")
        print(f"Word count: {posts[0].word_count}")
        print(f"Has H2 headers: {'✅' if '##' in posts[0].content else '❌'}")
        print(f"Length validation: {'✅' if length_results['passed'] else '❌'}")
        print(f"Hook validation: {'✅' if hook_results['passed'] else '❌'}")
        print(f"Headline validation: {'✅' if headline_results['passed'] else '❌'}")

    @pytest.mark.asyncio
    async def test_email_generation_and_validation(self, brief_parser, content_generator, sample_brief_file):
        """Test Email content generation (150-250 words) + validation"""
        # Step 1: Parse brief
        brief_data = brief_parser.parse_brief(str(sample_brief_file))
        brief = ClientBrief(**brief_data)

        # Step 2: Generate Email posts
        posts = await content_generator.generate_posts_async(
            brief=brief,
            template_ids=[1, 2, 9],  # Problem, Stat, How-To
            platform=Platform.EMAIL,
            num_posts=3
        )

        # Verify generation
        assert len(posts) == 3
        assert all(p.target_platform == Platform.EMAIL for p in posts)

        # Step 3: Validate lengths
        length_validator = LengthValidator()
        length_results = length_validator.validate(posts)

        assert length_results["platform"] == "email"
        assert length_results["optimal_range"] == "150-250 words"

        # Step 4: Validate CTAs
        cta_validator = CTAValidator()
        cta_results = cta_validator.validate(posts)

        assert cta_results["platform"] == "email"
        assert cta_results["variety_threshold"] == 0.70, "Email should use 70% variety threshold"

        # Print summary
        print("\n=== Email Generation Summary ===")
        print(f"Posts generated: {len(posts)}")
        print(f"Word counts: {[p.word_count for p in posts]}")
        print(f"Length validation: {'✅' if length_results['passed'] else '❌'}")
        print(f"CTA validation: {'✅' if cta_results['passed'] else '❌'}")

    @pytest.mark.asyncio
    async def test_all_platforms_comparison(self, brief_parser, content_generator, sample_brief_file):
        """Generate content for all platforms and compare results"""
        # Parse brief once
        brief_data = brief_parser.parse_brief(str(sample_brief_file))
        brief = ClientBrief(**brief_data)

        results = {}

        # Generate for each platform
        for platform in [Platform.LINKEDIN, Platform.TWITTER, Platform.FACEBOOK, Platform.BLOG, Platform.EMAIL]:
            num_posts = 1 if platform == Platform.BLOG else 3

            posts = await content_generator.generate_posts_async(
                brief=brief,
                template_ids=[1],  # Same template for fair comparison
                platform=platform,
                num_posts=num_posts
            )

            # Validate
            length_validator = LengthValidator()
            length_results = length_validator.validate(posts)

            results[platform.value] = {
                "posts_generated": len(posts),
                "word_counts": [p.word_count for p in posts],
                "avg_word_count": sum(p.word_count for p in posts) / len(posts),
                "optimal_range": length_results["optimal_range"],
                "validation_passed": length_results["passed"],
            }

        # Print comparison table
        print("\n" + "=" * 80)
        print("MULTI-PLATFORM COMPARISON")
        print("=" * 80)
        print(f"{'Platform':<12} {'Posts':<8} {'Avg Words':<12} {'Target Range':<20} {'Valid':<8}")
        print("-" * 80)

        for platform_name, data in results.items():
            print(f"{platform_name.upper():<12} "
                  f"{data['posts_generated']:<8} "
                  f"{data['avg_word_count']:<12.1f} "
                  f"{data['optimal_range']:<20} "
                  f"{'✅' if data['validation_passed'] else '❌':<8}")

        print("=" * 80)

        # Verify platform-specific ranges
        assert results["twitter"]["avg_word_count"] < 50, "Twitter should be under 50 words"
        assert results["facebook"]["avg_word_count"] < 30, "Facebook should be under 30 words"
        assert 150 <= results["linkedin"]["avg_word_count"] <= 350, "LinkedIn should be 150-350 words"
        assert results["blog"]["avg_word_count"] >= 1500, "Blog should be 1500+ words"
        assert 100 <= results["email"]["avg_word_count"] <= 300, "Email should be 100-300 words"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
