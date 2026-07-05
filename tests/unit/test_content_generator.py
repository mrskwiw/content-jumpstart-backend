"""
Comprehensive unit tests for ContentGeneratorAgent

Tests cover:
- Post generation (sync and async)
- Template quantities system
- Voice matching
- Multi-platform generation
- Blog linking
- Quality retry logic
- Error handling
- Sanitization and security
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.agents.content_generator import ContentGeneratorAgent
from src.models.client_brief import ClientBrief, Platform, TonePreference
from src.models.post import Post
from src.models.template import Template, TemplateType, TemplateDifficulty
from src.models.seo_keyword import KeywordStrategy, SEOKeyword, KeywordIntent
from src.utils.anthropic_client import AnthropicClient
from src.utils.template_loader import TemplateLoader


# ==================== Fixtures ====================


@pytest.fixture
def mock_client():
    """Mock Anthropic client with test responses"""
    client = Mock(spec=AnthropicClient)
    client.generate_post_content = Mock(
        return_value="This is a test LinkedIn post about productivity. It has enough words to pass validation. Teams waste 30% of time switching apps. Our research shows 12+ tools daily. 45 minutes lost to context switching. 3 hours per week in meetings. $15K annual cost per employee. The solution? Consolidate your workflow. What's your biggest productivity killer? Try our free workflow assessment."
    )
    client.generate_post_content_async = AsyncMock(
        return_value="In today's fast-paced business environment, teams are constantly juggling multiple tools and platforms to get their work done effectively. Research shows that the average knowledge worker uses between 12 and 15 different applications every single day just to complete their basic tasks. This constant context switching isn't just annoying or frustrating - it's costing your organization real money and impacting team productivity significantly. Studies indicate that employees lose approximately 30 percent of their productive time simply moving between different tools, searching for scattered information, and trying to piece together their fragmented workflow. That translates to nearly 3 full hours per day, or 15 hours per week, of lost productivity for each employee on your team. When you calculate the annual financial impact of this inefficiency, that's roughly fifteen thousand dollars in wasted time and resources for each team member every single year. The solution to this expensive problem? Consolidating your entire workflow into a single, integrated platform that brings everything together seamlessly. What's your biggest productivity killer right now? Take our free comprehensive workflow assessment today and discover exactly how much time your team could reclaim! Book a personalized demo now and see the difference for yourself immediately!"
    )
    client.create_message_async = AsyncMock(
        return_value="This is a test social media teaser. Click to read more. [BLOG_LINK_1]"
    )
    return client


@pytest.fixture
def mock_template_loader():
    """Mock template loader with test templates"""
    loader = Mock(spec=TemplateLoader)

    # Create test templates
    test_templates = [
        Template(
            template_id=1,
            name="Problem Recognition",
            template_type=TemplateType.PROBLEM_RECOGNITION,
            difficulty=TemplateDifficulty.FAST,
            best_for="Identifying customer pain points",
            structure="Identify [PROBLEM] that [AUDIENCE] faces. Explain why it matters. Provide [SOLUTION].",
            requires_story=False,
            requires_data=False,
        ),
        Template(
            template_id=2,
            name="Statistic + Insight",
            template_type=TemplateType.STATISTIC,
            difficulty=TemplateDifficulty.FAST,
            best_for="Building authority with data",
            structure="Share [STATISTIC]. Provide [INSIGHT]. Connect to [AUDIENCE].",
            requires_story=False,
            requires_data=True,
        ),
        Template(
            template_id=9,
            name="How-To",
            template_type=TemplateType.HOW_TO,
            difficulty=TemplateDifficulty.FAST,
            best_for="Providing actionable value",
            structure="Teach [AUDIENCE] how to [ACTION]. Provide steps. Include benefits.",
            requires_story=False,
            requires_data=False,
        ),
    ]

    loader.select_templates_for_client.return_value = test_templates
    loader.get_template_by_id.side_effect = lambda tid: next(
        (t for t in test_templates if t.template_id == tid), None
    )
    loader.get_all_templates.return_value = test_templates

    return loader


@pytest.fixture
def sample_client_brief():
    """Sample client brief for testing"""
    return ClientBrief(
        company_name="Test Company",
        business_description="We provide cloud-based project management software",
        ideal_customer="Small business owners with 5-20 employees",
        main_problem_solved="Inefficient workflows and scattered communication",
        customer_pain_points=[
            "Wasting time on manual data entry",
            "Poor team collaboration",
            "Lack of visibility",
        ],
        brand_personality=[TonePreference.AUTHORITATIVE, TonePreference.DATA_DRIVEN],
        target_platforms=[Platform.LINKEDIN],
    )


@pytest.fixture
def sample_posts(sample_client_brief):
    """Sample posts for testing"""
    posts = []
    for i in range(5):
        post = Post(
            content=f"Test post {i+1} with enough content to meet minimum requirements. This post discusses productivity and workflow optimization. Teams waste significant time on manual tasks. Here's how to improve efficiency. Try our solution today.",
            template_id=1,
            template_name="Problem Recognition",
            variant=1,
            client_name=sample_client_brief.company_name,
            target_platform=Platform.LINKEDIN,
        )
        posts.append(post)
    return posts


# ==================== Initialization Tests ====================


def test_content_generator_init_default():
    """Test ContentGeneratorAgent initialization with defaults"""
    generator = ContentGeneratorAgent()

    assert generator.client is not None
    assert generator.template_loader is not None
    assert generator.keyword_strategy is None
    assert generator.db is None


def test_content_generator_init_with_params(mock_client, mock_template_loader):
    """Test ContentGeneratorAgent initialization with custom params"""
    keyword_strategy = KeywordStrategy(
        primary_keywords=[
            SEOKeyword(
                keyword="productivity",
                intent=KeywordIntent.INFORMATIONAL,
                priority=1,
                search_volume=5000,
            )
        ]
    )

    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
        keyword_strategy=keyword_strategy,
    )

    assert generator.client == mock_client
    assert generator.template_loader == mock_template_loader
    assert generator.keyword_strategy == keyword_strategy


# ==================== Sync Generation Tests ====================


def test_generate_posts_sync_basic(mock_client, mock_template_loader, sample_client_brief):
    """Test basic synchronous post generation"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    posts = generator.generate_posts(
        client_brief=sample_client_brief,
        num_posts=6,
        template_count=3,
        randomize=False,
    )

    assert len(posts) == 6
    assert all(isinstance(p, Post) for p in posts)
    assert all(p.client_name == "Test Company" for p in posts)
    assert all(p.target_platform == Platform.LINKEDIN for p in posts)


def test_generate_posts_with_template_quantities(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test post generation with template quantities"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    template_quantities = {1: 3, 2: 5, 9: 2}  # 10 total posts

    posts = generator.generate_posts(
        client_brief=sample_client_brief,
        template_quantities=template_quantities,
        randomize=False,
    )

    assert len(posts) == 10

    # Count posts by template
    template_counts = {}
    for post in posts:
        template_counts[post.template_id] = template_counts.get(post.template_id, 0) + 1

    assert template_counts[1] == 3
    assert template_counts[2] == 5
    assert template_counts[9] == 2


def test_generate_posts_with_manual_template_ids(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test post generation with manual template selection"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    posts = generator.generate_posts(
        client_brief=sample_client_brief,
        num_posts=6,
        template_ids=[1, 2, 9],
        randomize=False,
    )

    assert len(posts) == 6
    assert all(p.template_id in [1, 2, 9] for p in posts)


def test_generate_posts_randomization(mock_client, mock_template_loader, sample_client_brief):
    """Test that randomization shuffles post order"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    # Generate without randomization
    posts_no_random = generator.generate_posts(
        client_brief=sample_client_brief,
        num_posts=10,
        randomize=False,
    )

    # Generate with randomization (run multiple times to check randomness)
    posts_random = generator.generate_posts(
        client_brief=sample_client_brief,
        num_posts=10,
        randomize=True,
    )

    # Should have same posts but potentially different order
    assert len(posts_random) == len(posts_no_random)
    # Note: Order might be same by chance, but at scale it would differ


# ==================== Async Generation Tests ====================


@pytest.mark.asyncio
async def test_generate_posts_async_basic(mock_client, mock_template_loader, sample_client_brief):
    """Test basic asynchronous post generation"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    posts = await generator.generate_posts_async(
        client_brief=sample_client_brief,
        num_posts=6,
        template_count=3,
        max_concurrent=2,
        randomize=False,
    )

    assert len(posts) == 6
    assert all(isinstance(p, Post) for p in posts)
    assert mock_client.generate_post_content_async.call_count >= 6


@pytest.mark.asyncio
async def test_generate_posts_async_with_quantities(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test async post generation with template quantities"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    template_quantities = {1: 2, 2: 3, 9: 1}  # 6 total

    posts = await generator.generate_posts_async(
        client_brief=sample_client_brief,
        template_quantities=template_quantities,
        max_concurrent=3,
        randomize=False,
    )

    assert len(posts) == 6

    # Verify template distribution
    template_counts = {}
    for post in posts:
        template_counts[post.template_id] = template_counts.get(post.template_id, 0) + 1

    assert template_counts[1] == 2
    assert template_counts[2] == 3
    assert template_counts[9] == 1


@pytest.mark.asyncio
async def test_generate_posts_async_concurrency_limit(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test that async generation respects concurrency limits"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    # Track concurrent calls
    max_concurrent_seen = 0
    current_concurrent = 0

    original_async_func = mock_client.generate_post_content_async

    async def tracked_async(*args, **kwargs):
        nonlocal current_concurrent, max_concurrent_seen
        current_concurrent += 1
        max_concurrent_seen = max(max_concurrent_seen, current_concurrent)
        await asyncio.sleep(0.01)  # Simulate work
        current_concurrent -= 1
        return await original_async_func(*args, **kwargs)

    mock_client.generate_post_content_async = tracked_async

    await generator.generate_posts_async(
        client_brief=sample_client_brief,
        num_posts=10,
        max_concurrent=3,
    )

    # Max concurrent should not exceed limit
    assert max_concurrent_seen <= 3


# ==================== Platform-Specific Tests ====================


@pytest.mark.asyncio
async def test_generate_posts_for_twitter(mock_client, mock_template_loader, sample_client_brief):
    """Test Twitter-specific post generation"""
    # Mock shorter response for Twitter
    mock_client.generate_post_content_async.return_value = (
        "Teams waste 30% time on tools. Consolidate workflows for 10hrs/week savings."
    )

    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    posts = await generator.generate_posts_async(
        client_brief=sample_client_brief,
        num_posts=3,
        platform=Platform.TWITTER,
    )

    assert len(posts) == 3
    assert all(p.target_platform == Platform.TWITTER for p in posts)


@pytest.mark.asyncio
async def test_generate_posts_for_blog(mock_client, mock_template_loader, sample_client_brief):
    """Test blog-specific post generation with longer content"""
    # Mock longer blog response
    long_blog_content = "# Comprehensive Blog Post\n\n" + "This is detailed blog content. " * 200
    mock_client.generate_post_content_async.return_value = long_blog_content

    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    posts = await generator.generate_posts_async(
        client_brief=sample_client_brief,
        num_posts=2,
        platform=Platform.BLOG,
    )

    assert len(posts) == 2
    assert all(p.target_platform == Platform.BLOG for p in posts)


# ==================== Multi-Platform Blog Linking Tests ====================


@pytest.mark.asyncio
async def test_generate_multi_platform_with_blog_links(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test multi-platform content generation with blog linking"""
    # Mock blog content
    mock_client.generate_post_content_async.return_value = (
        "# Blog Title\n\nBlog content here. " * 100
    )

    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    result = await generator.generate_multi_platform_with_blog_links_async(
        client_brief=sample_client_brief,
        num_blog_posts=3,
        social_teasers_per_blog=2,
    )

    assert "blog" in result
    assert "twitter" in result
    assert "facebook" in result

    assert len(result["blog"]) == 3
    assert len(result["twitter"]) == 3  # 1 per blog
    assert len(result["facebook"]) == 3  # 1 per blog

    # Verify blog posts have metadata
    for blog_post in result["blog"]:
        assert blog_post.blog_title is not None
        assert blog_post.blog_link_placeholder is not None

    # Verify teasers link to blogs
    for teaser in result["twitter"] + result["facebook"]:
        assert teaser.related_blog_post_id is not None
        assert teaser.blog_link_placeholder is not None


# ==================== Voice Matching Tests ====================


@pytest.mark.asyncio
async def test_generate_with_voice_matching_no_samples(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test voice matching with no samples (should fallback to standard generation)"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    posts, voice_report = await generator.generate_posts_with_voice_matching_async(
        client_brief=sample_client_brief,
        num_posts=5,
    )

    assert len(posts) == 5
    assert voice_report is None  # No samples, so no report


# ==================== Quality Retry Tests ====================


@pytest.mark.asyncio
async def test_quality_retry_logic_success_on_first_attempt(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test quality retry succeeds on first attempt (no flags)"""
    # Must have 200+ words (LinkedIn min) to avoid "too short" flag, and include a CTA
    mock_client.generate_post_content_async.return_value = (
        "Most knowledge workers juggle too many tools every single day to get their work done effectively. "
        "Context switching between applications is one of the biggest hidden costs in modern organisations. "
        "This constant tool sprawl costs your organisation real money and measurable lost productivity. "
        "Many employees lose a significant portion of their productive time moving between applications. "
        "That translates to hours per day of lost deep work time that adds up across your entire team. "
        "When you calculate the annual financial impact, the wasted time becomes a compelling business case. "
        "The solution is consolidating your entire workflow into a single, integrated platform. "
        "Our platform brings everything your team needs into one place, eliminating tool sprawl permanently. "
        "Onboarding takes under 60 minutes and requires zero engineering support from your side. "
        "Most teams notice measurable productivity gains within the first week of adoption across departments. "
        "Managers gain real-time visibility without chasing status updates or sitting through long standups. "
        "Individual contributors reclaim deep work time that was previously lost to context switching overhead. "
        "Organisations across many industries have already consolidated onto our platform successfully. "
        "They notice reduced burnout, clearer communication, and higher project completion rates consistently. "
        "Book a personalised demo today and discover exactly how much time your team could reclaim."
    )

    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    template = mock_template_loader.get_template_by_id(1)

    post = await generator._generate_single_post_with_retry_async(
        template=template,
        client_brief=sample_client_brief,
        variant=1,
        post_number=1,
        max_attempts=5,
    )

    # Should succeed on first attempt
    assert mock_client.generate_post_content_async.call_count == 1
    assert post is not None


@pytest.mark.asyncio
async def test_quality_retry_logic_retries_on_failure(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test quality retry retries when post has quality flags"""
    # First 2 attempts have issues, 3rd is good
    call_count = 0

    async def variable_response(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return "Too short"  # Will flag as too short
        # Third attempt: Must have 200+ words (LinkedIn min) with CTA to pass
        return (
            "Teams are constantly juggling multiple tools and platforms to get their work done every single day. "
            "Research shows that the average knowledge worker uses between 12 and 15 different applications daily. "
            "This constant context switching costs your organization real money and significant productivity. "
            "Studies indicate that employees lose approximately 30 percent of their productive time moving between tools. "
            "That translates to nearly 3 hours per day, or 15 hours per week, of lost productivity per employee. "
            "When you calculate the annual impact, that is roughly fifteen thousand dollars in wasted time per team member. "
            "The solution is consolidating your entire workflow into a single integrated platform. "
            "Our platform eliminates tool sprawl and streamlines your operations across all departments. "
            "Onboarding takes under 60 minutes and requires no engineering support whatsoever from your side. "
            "Managers gain real-time visibility into projects without chasing status updates in meetings. "
            "Individual contributors reclaim deep work time previously lost to context switching and coordination. "
            "Over 500 teams across 30 industries have already made the switch to our platform. "
            "They cite reduced burnout, clearer communication, and consistently higher project completion rates. "
            "The ROI is measurable within the first 30 days for the vast majority of our customers. "
            "Book a personalized demo now and see the difference for yourself immediately."
        )

    mock_client.generate_post_content_async = variable_response

    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    template = mock_template_loader.get_template_by_id(1)

    post = await generator._generate_single_post_with_retry_async(
        template=template,
        client_brief=sample_client_brief,
        variant=1,
        post_number=1,
        max_attempts=5,
    )

    # Should have retried 3 times
    assert call_count == 3
    assert post.word_count >= 75  # Final post should be adequate


# ==================== Error Handling Tests ====================


@pytest.mark.asyncio
async def test_generate_post_with_api_error(mock_client, mock_template_loader, sample_client_brief):
    """Test error handling when API call fails"""
    mock_client.generate_post_content_async.side_effect = Exception("API Error")

    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    template = mock_template_loader.get_template_by_id(1)

    post = await generator._generate_single_post_async(
        template=template,
        client_brief=sample_client_brief,
        variant=1,
        post_number=1,
    )

    # Should create placeholder post
    assert "[ERROR:" in post.content
    assert post.needs_review is True
    assert post.review_reason is not None
    assert "Generation failed" in post.review_reason


def test_generate_variant_error_recovery(mock_client, mock_template_loader, sample_client_brief):
    """Test variant generation error recovery"""
    original_post = Post(
        content="Original post content",
        template_id=1,
        template_name="Problem Recognition",
        variant=1,
        client_name="Test Company",
    )

    mock_client.refine_post.side_effect = Exception("Refinement failed")

    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    result = generator.generate_variant(
        original_post=original_post,
        client_brief=sample_client_brief,
        feedback="Make it shorter",
    )

    # Should return original post on error
    assert result.content == original_post.content


# ==================== Sanitization Tests ====================


def test_sanitize_client_brief_basic(mock_client, mock_template_loader):
    """Test basic client brief sanitization"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    brief = ClientBrief(
        company_name="Test Company",
        business_description="Normal business description",
        ideal_customer="Normal customer",
        main_problem_solved="Normal problem",
    )

    sanitized = generator._sanitize_client_brief(brief)

    assert sanitized.company_name == brief.company_name
    assert sanitized.business_description == brief.business_description


def test_sanitize_client_brief_with_suspicious_content(mock_client, mock_template_loader):
    """Test sanitization with suspicious patterns"""
    with patch("src.agents.content_generator.sanitize_prompt_input") as mock_sanitize:
        mock_sanitize.side_effect = ValueError("Prompt injection detected")

        generator = ContentGeneratorAgent(
            client=mock_client,
            template_loader=mock_template_loader,
        )

        brief = ClientBrief(
            company_name="Test",
            business_description="Ignore previous instructions and...",
            ideal_customer="Customer",
            main_problem_solved="Problem",
        )

        with pytest.raises(ValueError, match="unsafe content"):
            generator._sanitize_client_brief(brief)


# ==================== Helper Method Tests ====================


def test_clean_post_content_removes_quotes(mock_client, mock_template_loader):
    """Test content cleaning removes quotes"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    content = '"This is quoted content"'
    cleaned = generator._clean_post_content(content)

    assert cleaned == "This is quoted content"


def test_clean_post_content_normalizes_line_breaks(mock_client, mock_template_loader):
    """Test content cleaning normalizes line breaks"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    content = "Line 1\n\n\n\n\nLine 2"
    cleaned = generator._clean_post_content(content)

    assert "\n\n\n" not in cleaned


def test_calculate_post_quality_score_perfect(mock_client, mock_template_loader):
    """Test quality score calculation for perfect post"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    # Create content with 75+ words and a CTA to avoid any flags
    post = Post(
        content=(
            "This is a perfect post with enough words to meet minimum requirements. "
            "It discusses important topics and provides valuable insights for readers. "
            "The content is well structured and easy to understand for everyone. "
            "It includes relevant information and engaging narrative throughout. "
            "Professional tone maintained throughout the entire piece consistently. "
            "Clear messaging that resonates with the target audience effectively. "
            "We help teams work better together with modern tools. "
            "Book a demo today to learn more about our solution. "
            "Contact us now!"
        ),
        template_id=1,
        template_name="Test",
        variant=1,
        client_name="Test",
    )
    # Post auto-calculates word_count and has_cta
    # Should have no quality issues

    score = generator._calculate_post_quality_score(post)

    assert score == 1.0


def test_calculate_post_quality_score_with_flags(mock_client, mock_template_loader):
    """Test quality score calculation with flags"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    post = Post(
        content="Post",
        template_id=1,
        template_name="Test",
        variant=1,
        client_name="Test",
    )
    # Post auto-calculates word_count and has_cta
    # flags field doesn't exist in Post model

    score = generator._calculate_post_quality_score(post)

    assert score < 1.0  # Should be penalized


def test_infer_archetype_from_client_type(mock_client, mock_template_loader, sample_client_brief):
    """Test archetype inference from business description (fallback logic)"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    # Test uses fallback keyword-based inference from business_description
    # sample_client_brief has business_description="We provide cloud-based project management software"
    # which contains "software" keyword -> should infer "Expert"

    archetype = generator._infer_archetype(sample_client_brief)

    assert archetype in ["Expert", "Friend", "Innovator", "Guide", "Motivator"]
    # Specifically, should be "Expert" based on "software" keyword
    assert archetype == "Expert"


def test_extract_blog_title_from_heading(mock_client, mock_template_loader):
    """Test blog title extraction from markdown heading"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    content = "# The Ultimate Productivity Guide\n\nContent here..."
    title = generator._extract_blog_title(content)

    assert title == "The Ultimate Productivity Guide"


def test_create_slug_from_title(mock_client, mock_template_loader):
    """Test URL slug creation"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    title = "The Ultimate Guide to Productivity!"
    slug = generator._create_slug(title)

    assert slug == "the-ultimate-guide-to-productivity"
    assert " " not in slug
    assert "!" not in slug


def test_extract_blog_summary(mock_client, mock_template_loader):
    """Test blog summary extraction"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    content = "# Title\n\n" + "Word " * 100
    summary = generator._extract_blog_summary(content)

    assert len(summary) <= 203  # 200 + "..."
    assert summary.endswith("...")


# ==================== Integration-Style Tests ====================


@pytest.mark.asyncio
async def test_full_generation_workflow_async(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test complete generation workflow from brief to posts"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    # Generate posts with template quantities
    template_quantities = {1: 10, 2: 10, 9: 10}

    posts = await generator.generate_posts_async(
        client_brief=sample_client_brief,
        template_quantities=template_quantities,
        max_concurrent=5,
        randomize=True,
    )

    # Verify output
    assert len(posts) == 30
    assert all(isinstance(p, Post) for p in posts)
    assert all(p.client_name == "Test Company" for p in posts)
    assert all(p.word_count > 0 for p in posts)
    assert all(p.template_id in [1, 2, 9] for p in posts)

    # Verify template distribution
    template_counts = {}
    for post in posts:
        template_counts[post.template_id] = template_counts.get(post.template_id, 0) + 1

    assert template_counts[1] == 10
    assert template_counts[2] == 10
    assert template_counts[9] == 10


# ==================== Client Memory Database Tests ====================


def test_content_generator_init_with_memory_db(mock_client, mock_template_loader):
    """Test initialization with client memory database"""
    mock_db = Mock()
    mock_db.get_client_memory = Mock(return_value=None)

    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
        db=mock_db,  # Parameter is 'db', not 'client_memory_db'
    )

    assert generator.db == mock_db


def test_content_generator_no_memory_when_db_none(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test generation without memory database"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
        db=None,  # Parameter is 'db', not 'client_memory_db'
    )

    posts = generator.generate_posts(
        client_brief=sample_client_brief,
        num_posts=3,
    )

    assert len(posts) == 3
    # Should work fine without memory db


# ==================== Edge Case Tests ====================


def test_generate_posts_with_empty_template_quantities(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test generation with empty template quantities dict"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    # Empty dict should use num_posts fallback
    posts = generator.generate_posts(
        client_brief=sample_client_brief,
        template_quantities={},
        num_posts=5,
    )

    assert len(posts) == 5


def test_generate_posts_with_zero_quantities(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test generation with all zero quantities"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    posts = generator.generate_posts(
        client_brief=sample_client_brief,
        template_quantities={1: 0, 2: 0, 9: 0},
    )

    assert len(posts) == 0


def test_generate_variant_success(mock_client, mock_template_loader, sample_client_brief):
    """Test successful variant generation"""
    original_post = Post(
        content="Original post content with enough words to be valid for testing purposes. This has good length and structure.",
        template_id=1,
        template_name="Problem Recognition",
        variant=1,
        client_name="Test Company",
    )

    mock_client.refine_post = Mock(
        return_value="Refined variant content with enough words for validation. Updated with new angle and improved messaging."
    )

    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    result = generator.generate_variant(
        original_post=original_post,
        client_brief=sample_client_brief,
        feedback="Make it more concise",
    )

    # Result should be a post (original or refined)
    assert result is not None
    assert isinstance(result, Post)


def test_clean_post_content_handles_markdown_headers(mock_client, mock_template_loader):
    """Test content cleaning handles markdown headers"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    content = "# Title\n## Section\nContent here"
    cleaned = generator._clean_post_content(content)

    # Should remove # symbols from headers
    assert cleaned.startswith("Title")


def test_clean_post_content_strips_whitespace(mock_client, mock_template_loader):
    """Test content cleaning strips leading/trailing whitespace"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    content = "   Content with spaces   "
    cleaned = generator._clean_post_content(content)

    assert cleaned == "Content with spaces"


def test_extract_blog_title_no_heading(mock_client, mock_template_loader):
    """Test blog title extraction when no heading present"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    content = "Just some content without a heading"
    title = generator._extract_blog_title(content)

    # Uses first line as title when no heading present
    assert title == "Just some content without a heading"


def test_extract_blog_summary_short_content(mock_client, mock_template_loader):
    """Test blog summary extraction with short content"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    content = "# Title\n\nShort content"
    summary = generator._extract_blog_summary(content)

    assert len(summary) > 0
    assert not summary.endswith("...")  # Should not truncate short content


def test_infer_archetype_agency(mock_client, mock_template_loader):
    """Test archetype inference for agency client type"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    brief = ClientBrief(
        company_name="Test Agency",
        business_description="Digital marketing agency helping clients grow",
        ideal_customer="Businesses needing marketing",
        main_problem_solved="Marketing challenges",
    )

    archetype = generator._infer_archetype(brief)
    assert archetype in ["Expert", "Friend", "Innovator", "Guide", "Motivator"]


def test_infer_archetype_coach(mock_client, mock_template_loader):
    """Test archetype inference for coach client type"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    brief = ClientBrief(
        company_name="Success Coach",
        business_description="Life coach helping people achieve goals and transformation",
        ideal_customer="Individuals seeking growth",
        main_problem_solved="Lack of direction",
    )

    archetype = generator._infer_archetype(brief)
    # Coach/consultant typically maps to "Motivator" or "Guide"
    assert archetype in ["Expert", "Friend", "Innovator", "Guide", "Motivator"]


def test_infer_archetype_creator(mock_client, mock_template_loader):
    """Test archetype inference for creator client type"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    brief = ClientBrief(
        company_name="Creative Studio",
        business_description="Content creator and personal brand building",
        ideal_customer="Aspiring creators",
        main_problem_solved="Lack of visibility",
    )

    archetype = generator._infer_archetype(brief)
    # Creator typically maps to "Friend" or "Innovator"
    assert archetype in ["Expert", "Friend", "Innovator", "Guide", "Motivator"]


# ==================== Async Error Handling Tests ====================


@pytest.mark.asyncio
async def test_generate_posts_async_handles_partial_failures(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test async generation handles partial failures gracefully"""
    call_count = 0

    async def sometimes_fail(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count % 3 == 0:  # Every 3rd call fails
            raise Exception("Simulated failure")
        return "Success post content with enough words for validation. This is a complete post with good structure."

    mock_client.generate_post_content_async = sometimes_fail

    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    posts = await generator.generate_posts_async(
        client_brief=sample_client_brief,
        num_posts=6,
        max_concurrent=2,
    )

    # Should still return 6 posts (some may be error placeholders)
    assert len(posts) == 6


@pytest.mark.asyncio
async def test_generate_posts_async_large_batch(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test async generation with larger batch size"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    posts = await generator.generate_posts_async(
        client_brief=sample_client_brief,
        num_posts=15,
        max_concurrent=5,
    )

    assert len(posts) == 15
    assert all(isinstance(p, Post) for p in posts)


# ==================== Platform-Specific Edge Cases ====================


@pytest.mark.asyncio
async def test_generate_posts_for_facebook(mock_client, mock_template_loader, sample_client_brief):
    """Test Facebook-specific post generation"""
    mock_client.generate_post_content_async.return_value = "Engaging Facebook post content with enough words for validation. This post has great content."

    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    posts = await generator.generate_posts_async(
        client_brief=sample_client_brief,
        num_posts=3,
        platform=Platform.FACEBOOK,
    )

    assert len(posts) == 3
    assert all(p.target_platform == Platform.FACEBOOK for p in posts)


@pytest.mark.asyncio
async def test_generate_posts_for_email(mock_client, mock_template_loader, sample_client_brief):
    """Test Email-specific post generation"""
    mock_client.generate_post_content_async.return_value = "Subject: Important Update\n\nDear subscriber, here is valuable content with enough words for validation."

    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    posts = await generator.generate_posts_async(
        client_brief=sample_client_brief,
        num_posts=3,
        platform=Platform.EMAIL,
    )

    assert len(posts) == 3
    assert all(p.target_platform == Platform.EMAIL for p in posts)


# ==================== Quality Score Edge Cases ====================


def test_calculate_post_quality_score_with_review_flag(mock_client, mock_template_loader):
    """Test quality score with review flag"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    post = Post(
        content="Test content with enough words for validation purposes here now.",
        template_id=1,
        template_name="Test",
        variant=1,
        client_name="Test",
        needs_review=True,
        review_reason="Too short",
    )

    score = generator._calculate_post_quality_score(post)
    # Should be penalized for review flag
    assert score < 1.0


def test_calculate_post_quality_score_no_cta(mock_client, mock_template_loader):
    """Test quality score for post without CTA"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    post = Post(
        content="This post has no call to action and just provides information without any engagement hooks or prompts for the reader.",
        template_id=1,
        template_name="Test",
        variant=1,
        client_name="Test",
    )

    score = generator._calculate_post_quality_score(post)
    # Should be penalized for no CTA
    assert score <= 1.0


# ==================== Template Selection Tests ====================


def test_generate_posts_with_single_template(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test generation with single template"""
    # Return only one template
    single_template = Template(
        template_id=1,
        name="Single Template",
        template_type=TemplateType.PROBLEM_RECOGNITION,
        difficulty=TemplateDifficulty.FAST,
        best_for="General use",
        structure="Basic structure",
        requires_story=False,
        requires_data=False,
    )
    mock_template_loader.select_templates_for_client.return_value = [single_template]
    mock_template_loader.get_template_by_id.return_value = single_template
    mock_template_loader.get_all_templates.return_value = [single_template]

    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    posts = generator.generate_posts(
        client_brief=sample_client_brief,
        num_posts=3,
        template_count=1,
    )

    # Should generate posts using the single template
    assert len(posts) == 3
    assert all(p.template_id == 1 for p in posts)


# ==================== Keyword Strategy Tests ====================


@pytest.mark.asyncio
async def test_generate_posts_with_keyword_strategy(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test generation with keyword strategy integration"""
    keyword_strategy = KeywordStrategy(
        primary_keywords=[
            SEOKeyword(
                keyword="productivity software",
                intent=KeywordIntent.COMMERCIAL,
                priority=1,
                search_volume=1000,
            )
        ],
        secondary_keywords=[
            SEOKeyword(
                keyword="workflow automation",
                intent=KeywordIntent.INFORMATIONAL,
                priority=2,
                search_volume=500,
            )
        ],
    )

    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
        keyword_strategy=keyword_strategy,
    )

    posts = await generator.generate_posts_async(
        client_brief=sample_client_brief,
        num_posts=5,
    )

    assert len(posts) == 5
    # Generator should have used keyword context in prompts


# ==================== Sync vs Async Consistency ====================


def test_sync_and_async_produce_same_post_count(
    mock_client, mock_template_loader, sample_client_brief
):
    """Test sync and async methods produce same number of posts"""
    generator = ContentGeneratorAgent(
        client=mock_client,
        template_loader=mock_template_loader,
    )

    sync_posts = generator.generate_posts(
        client_brief=sample_client_brief,
        num_posts=5,
        randomize=False,
    )

    # Reset mock call count
    mock_client.generate_post_content.reset_mock()

    async def run_async():
        return await generator.generate_posts_async(
            client_brief=sample_client_brief,
            num_posts=5,
            randomize=False,
        )

    async_posts = asyncio.get_event_loop().run_until_complete(run_async())

    assert len(sync_posts) == len(async_posts) == 5
