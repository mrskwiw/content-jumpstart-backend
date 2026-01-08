"""
Unit tests for research tool parameter validation schemas.

Tests comprehensive input validation including:
- Length limits (prevent DoS)
- Type checking (prevent type confusion)
- List size limits (prevent resource exhaustion)
- Sanitization (whitespace stripping)
"""

import pytest
from pydantic import ValidationError

from backend.schemas import (
    VoiceAnalysisParams,
    SEOKeywordParams,
    CompetitiveAnalysisParams,
    ContentGapParams,
    ContentAuditParams,
    ContentPiece,
    MarketTrendsParams,
    PlatformStrategyParams,
    ContentCalendarParams,
    AudienceResearchParams,
    ICPWorkshopParams,
    StoryMiningParams,
    BrandArchetypeParams,
)


# Voice Analysis Validation Tests


def test_voice_analysis_valid_minimum():
    """Test voice analysis with minimum valid input (5 samples)."""
    params = VoiceAnalysisParams(content_samples=["A" * 50] * 5)  # 5 samples, each 50 chars
    assert len(params.content_samples) == 5
    assert all(len(sample) == 50 for sample in params.content_samples)


def test_voice_analysis_valid_maximum():
    """Test voice analysis with maximum valid input (30 samples)."""
    params = VoiceAnalysisParams(content_samples=["B" * 100] * 30)  # 30 samples, each 100 chars
    assert len(params.content_samples) == 30


def test_voice_analysis_too_few_samples():
    """Test voice analysis rejects too few samples."""
    with pytest.raises(ValidationError) as exc_info:
        VoiceAnalysisParams(content_samples=["A" * 50] * 4)  # Only 4 samples

    errors = exc_info.value.errors()
    assert any("5-30 content samples" in str(error["msg"]) for error in errors)


def test_voice_analysis_too_many_samples():
    """Test voice analysis rejects too many samples."""
    with pytest.raises(ValidationError) as exc_info:
        VoiceAnalysisParams(content_samples=["A" * 50] * 31)  # 31 samples

    errors = exc_info.value.errors()
    assert any("5-30 content samples" in str(error["msg"]) for error in errors)


def test_voice_analysis_sample_too_short():
    """Test voice analysis rejects samples that are too short."""
    with pytest.raises(ValidationError) as exc_info:
        VoiceAnalysisParams(content_samples=["A" * 49] * 5)  # Samples only 49 chars (min is 50)

    errors = exc_info.value.errors()
    assert any("too short" in str(error["msg"]).lower() for error in errors)


def test_voice_analysis_sample_too_long():
    """Test voice analysis rejects samples that are too long (DoS prevention)."""
    with pytest.raises(ValidationError) as exc_info:
        VoiceAnalysisParams(
            content_samples=["A" * 10001] * 5  # Samples 10,001 chars (max is 10,000)
        )

    errors = exc_info.value.errors()
    assert any("too long" in str(error["msg"]).lower() for error in errors)


def test_voice_analysis_whitespace_stripping():
    """Test that whitespace is stripped from samples."""
    params = VoiceAnalysisParams(
        content_samples=[f"  {'A' * 50}  "] * 5  # Samples with leading/trailing whitespace
    )
    # After validation, whitespace should be stripped
    assert all(not sample.startswith(" ") for sample in params.content_samples)
    assert all(not sample.endswith(" ") for sample in params.content_samples)


# SEO Keyword Validation Tests


def test_seo_keywords_valid():
    """Test SEO keywords with valid input."""
    params = SEOKeywordParams(main_topics=["AI automation", "content marketing", "SEO"])
    assert len(params.main_topics) == 3


def test_seo_keywords_too_few():
    """Test SEO keywords rejects empty list."""
    with pytest.raises(ValidationError):
        SEOKeywordParams(main_topics=[])


def test_seo_keywords_too_many():
    """Test SEO keywords rejects more than 10 topics."""
    with pytest.raises(ValidationError) as exc_info:
        SEOKeywordParams(main_topics=[f"topic{i}" for i in range(11)])  # 11 topics

    errors = exc_info.value.errors()
    assert any("1-10" in str(error["msg"]) for error in errors)


def test_seo_keywords_topic_too_short():
    """Test SEO keywords rejects topics that are too short."""
    with pytest.raises(ValidationError) as exc_info:
        SEOKeywordParams(main_topics=["AI", "OK", "NO"])  # Topics only 2 chars

    errors = exc_info.value.errors()
    assert any("too short" in str(error["msg"]).lower() for error in errors)


def test_seo_keywords_topic_too_long():
    """Test SEO keywords rejects topics that are too long."""
    with pytest.raises(ValidationError) as exc_info:
        SEOKeywordParams(main_topics=["A" * 101])  # Topic 101 chars (max is 100)

    errors = exc_info.value.errors()
    assert any("too long" in str(error["msg"]).lower() for error in errors)


# Competitive Analysis Validation Tests


def test_competitive_analysis_valid():
    """Test competitive analysis with valid input."""
    params = CompetitiveAnalysisParams(competitors=["HubSpot", "Mailchimp", "ConvertKit"])
    assert len(params.competitors) == 3


def test_competitive_analysis_too_many():
    """Test competitive analysis rejects more than 5 competitors."""
    with pytest.raises(ValidationError) as exc_info:
        CompetitiveAnalysisParams(competitors=[f"Competitor{i}" for i in range(6)])

    errors = exc_info.value.errors()
    assert any("1-5" in str(error["msg"]) for error in errors)


def test_competitive_analysis_competitor_too_short():
    """Test competitive analysis rejects competitors that are too short."""
    with pytest.raises(ValidationError) as exc_info:
        CompetitiveAnalysisParams(competitors=["A"])  # Only 1 char (min is 2)

    errors = exc_info.value.errors()
    assert any("too short" in str(error["msg"]).lower() for error in errors)


# Content Gap Validation Tests


def test_content_gap_valid():
    """Test content gap analysis with valid input."""
    params = ContentGapParams(current_content_topics="A" * 100)  # 100 chars
    assert len(params.current_content_topics) == 100


def test_content_gap_too_short():
    """Test content gap rejects topics that are too short."""
    with pytest.raises(ValidationError) as exc_info:
        ContentGapParams(current_content_topics="short")  # Only 5 chars (min is 10)

    errors = exc_info.value.errors()
    assert any("too short" in str(error["msg"]).lower() for error in errors)


def test_content_gap_too_long():
    """Test content gap rejects topics that are too long (DoS prevention)."""
    with pytest.raises(ValidationError) as exc_info:
        ContentGapParams(current_content_topics="A" * 5001)  # 5,001 chars (max is 5,000)

    errors = exc_info.value.errors()
    assert any("too long" in str(error["msg"]).lower() for error in errors)


# Content Audit Validation Tests


def test_content_audit_valid():
    """Test content audit with valid input."""
    pieces = [
        ContentPiece(
            title="Blog Post 1",
            url="https://example.com/post1",
            type="blog",
        ),
        ContentPiece(
            title="Blog Post 2",
            url="https://example.com/post2",
            type="blog",
        ),
    ]
    params = ContentAuditParams(content_inventory=pieces)
    assert len(params.content_inventory) == 2


def test_content_audit_empty():
    """Test content audit rejects empty inventory."""
    with pytest.raises(ValidationError):
        ContentAuditParams(content_inventory=[])


def test_content_audit_too_many():
    """Test content audit rejects more than 100 pieces."""
    pieces = [ContentPiece(title=f"Post {i}", url=f"https://example.com/{i}") for i in range(101)]
    with pytest.raises(ValidationError) as exc_info:
        ContentAuditParams(content_inventory=pieces)

    errors = exc_info.value.errors()
    assert any("1-100" in str(error["msg"]) for error in errors)


def test_content_piece_invalid_url():
    """Test content piece rejects invalid URLs."""
    with pytest.raises(ValidationError) as exc_info:
        ContentPiece(
            title="Blog Post",
            url="not-a-url",  # Invalid URL
        )

    errors = exc_info.value.errors()
    assert any("url" in str(error["msg"]).lower() for error in errors)


def test_content_piece_url_too_long():
    """Test content piece rejects URLs that are too long."""
    with pytest.raises(ValidationError) as exc_info:
        ContentPiece(
            title="Blog Post",
            url="https://example.com/" + "A" * 2000,  # URL > 2000 chars
        )

    errors = exc_info.value.errors()
    assert any("too long" in str(error["msg"]).lower() for error in errors)


def test_content_piece_title_too_short():
    """Test content piece rejects titles that are too short."""
    with pytest.raises(ValidationError) as exc_info:
        ContentPiece(title="AB")  # Only 2 chars (min is 3)

    errors = exc_info.value.errors()
    assert any("at least 3 characters" in str(error["msg"]) for error in errors)


# Market Trends Validation Tests


def test_market_trends_valid_with_industry():
    """Test market trends with industry specified."""
    params = MarketTrendsParams(industry="SaaS")
    assert params.industry == "SaaS"


def test_market_trends_valid_without_industry():
    """Test market trends without industry (uses client profile)."""
    params = MarketTrendsParams()
    assert params.industry is None


def test_market_trends_with_focus_areas():
    """Test market trends with focus areas."""
    params = MarketTrendsParams(
        industry="Healthcare", focus_areas=["AI tools", "remote work", "compliance"]
    )
    assert len(params.focus_areas) == 3


def test_market_trends_too_many_focus_areas():
    """Test market trends rejects more than 10 focus areas."""
    with pytest.raises(ValidationError) as exc_info:
        MarketTrendsParams(focus_areas=[f"area{i}" for i in range(11)])

    errors = exc_info.value.errors()
    assert any("maximum 10" in str(error["msg"]).lower() for error in errors)


# Platform Strategy Validation Tests


def test_platform_strategy_valid():
    """Test platform strategy with valid input."""
    params = PlatformStrategyParams(
        current_platforms=["LinkedIn", "Twitter", "Blog"],
        content_goals="Increase brand awareness and generate leads",
    )
    assert len(params.current_platforms) == 3


def test_platform_strategy_too_many_platforms():
    """Test platform strategy rejects more than 10 platforms."""
    with pytest.raises(ValidationError) as exc_info:
        PlatformStrategyParams(current_platforms=[f"Platform{i}" for i in range(11)])

    errors = exc_info.value.errors()
    assert any("maximum 10" in str(error["msg"]).lower() for error in errors)


def test_platform_strategy_goals_too_long():
    """Test platform strategy rejects goals that are too long."""
    with pytest.raises(ValidationError) as exc_info:
        PlatformStrategyParams(content_goals="A" * 1001)  # 1,001 chars (max is 1,000)

    errors = exc_info.value.errors()
    assert any("too long" in str(error["msg"]).lower() for error in errors)


# Content Calendar Validation Tests


def test_content_calendar_valid():
    """Test content calendar with valid input."""
    params = ContentCalendarParams(calendar_length_days=90)
    assert params.calendar_length_days == 90


def test_content_calendar_too_short():
    """Test content calendar rejects less than 30 days."""
    with pytest.raises(ValidationError) as exc_info:
        ContentCalendarParams(calendar_length_days=29)

    errors = exc_info.value.errors()
    assert any("greater than or equal to 30" in str(error["msg"]) for error in errors)


def test_content_calendar_too_long():
    """Test content calendar rejects more than 365 days."""
    with pytest.raises(ValidationError) as exc_info:
        ContentCalendarParams(calendar_length_days=366)

    errors = exc_info.value.errors()
    assert any("less than or equal to 365" in str(error["msg"]) for error in errors)


# Audience Research Validation Tests


def test_audience_research_valid():
    """Test audience research with valid input."""
    params = AudienceResearchParams(additional_context="Enterprise customers in healthcare sector")
    assert params.additional_context == "Enterprise customers in healthcare sector"


def test_audience_research_context_too_long():
    """Test audience research rejects context that is too long."""
    with pytest.raises(ValidationError) as exc_info:
        AudienceResearchParams(additional_context="A" * 2001)  # 2,001 chars (max is 2,000)

    errors = exc_info.value.errors()
    assert any("too long" in str(error["msg"]).lower() for error in errors)


# ICP Workshop Validation Tests


def test_icp_workshop_valid():
    """Test ICP workshop with valid input."""
    params = ICPWorkshopParams(workshop_focus="Focus on B2B SaaS customers")
    assert params.workshop_focus == "Focus on B2B SaaS customers"


def test_icp_workshop_no_params():
    """Test ICP workshop works without optional params."""
    params = ICPWorkshopParams()
    assert params.workshop_focus is None


# Story Mining Validation Tests


def test_story_mining_valid():
    """Test story mining with valid input."""
    params = StoryMiningParams(
        story_type="customer success", customer_segment="Enterprise customers"
    )
    assert params.story_type == "customer success"
    assert params.customer_segment == "Enterprise customers"


def test_story_mining_no_params():
    """Test story mining works without optional params."""
    params = StoryMiningParams()
    assert params.story_type is None
    assert params.customer_segment is None


# Brand Archetype Validation Tests


def test_brand_archetype_valid():
    """Test brand archetype (no params needed)."""
    params = BrandArchetypeParams()
    assert params is not None
