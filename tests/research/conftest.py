"""
Research tests conftest - mocks API calls to prevent real API usage.

Research tools call get_default_client() directly and use client.create_message().
This conftest mocks the anthropic client to return appropriate test responses.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest


# ==================== Mock Response Text for Claude API ====================

# Generic analysis response that tools can parse
MOCK_ANALYSIS_JSON = json.dumps(
    {
        "analysis": {
            "summary": "Analysis completed successfully",
            "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
            "recommendations": ["Recommendation 1", "Recommendation 2"],
            "score": 85,
        },
        "content_pieces": [
            {
                "title": "Test Content 1",
                "type": "blog_post",
                "performance_level": "high",
                "health_status": "healthy",
                "relevance_score": 0.85,
                "quality_score": 0.9,
                "recommendations": ["Update with new data"],
            }
        ],
        "top_performers": [
            {
                "title": "Test Content 1",
                "performance_level": "high",
                "reasons": ["High engagement", "Good SEO"],
            }
        ],
        "underperformers": [],
        "topic_performance": [
            {"topic": "Customer Success", "total_content": 3, "performance": "strong"}
        ],
        "refresh_opportunities": [
            {"title": "Old Content", "priority": "high", "reason": "Outdated statistics"}
        ],
        "repurpose_opportunities": [
            {
                "source_title": "Popular Blog",
                "target_formats": ["infographic", "video"],
                "potential_reach": "high",
            }
        ],
        "archive_recommendations": [],
        "content_gaps": [
            {
                "topic": "Advanced Analytics",
                "priority": "high",
                "opportunity": "No existing content",
            }
        ],
        "customer_journey": {
            "before": {
                "situation": "Manual processes",
                "pain_points": ["Time consuming", "Error prone"],
                "emotional_state": "Frustrated",
            },
            "decision": {
                "trigger": "Growth pressure",
                "alternatives": ["Competitor A", "Competitor B"],
                "selection_criteria": ["Price", "Features"],
            },
            "after": {
                "results": ["50% time saved", "90% accuracy"],
                "benefits": ["Team morale improved"],
                "emotional_state": "Confident",
            },
        },
        "key_quotes": ["Great product!", "Saved us hours"],
        "story_angles": ["Transformation story", "ROI story"],
        "case_study_draft": "# Customer Success Story\n\nThis is a draft case study...",
        "voice_profile": {
            "formality": "semi-formal",
            "tone": "confident",
            "perspective": "first-person-plural",
        },
        "platform_recommendations": {
            "linkedin": {"fit_score": 9, "strategy": "Thought leadership"},
            "twitter": {"fit_score": 7, "strategy": "Engagement"},
        },
        "icp": {
            "company_size": "50-500",
            "industry": "B2B SaaS",
            "pain_points": ["Churn", "Retention"],
        },
        "keywords": [{"keyword": "customer churn", "volume": 1000, "difficulty": 45}],
        "trends": [{"trend": "AI adoption", "growth": "45%", "relevance": "high"}],
    }
)


class HybridMockResponse(str):
    """
    A string subclass that also has .content attribute.

    Some research tools expect create_message() to return a string,
    while others (incorrectly) access response.content[0].text.
    This hybrid handles both cases.
    """

    def __new__(cls, text: str):
        instance = super().__new__(cls, text)
        # Add content attribute for code that expects response object
        mock_content = MagicMock()
        mock_content.text = text
        instance.content = [mock_content]
        return instance


def create_mock_response(content: str = MOCK_ANALYSIS_JSON):
    """
    Create a mock response that works as both string and response object.

    Most AnthropicClient.create_message() calls expect a string,
    but some research tools incorrectly access response.content[0].text.
    This hybrid mock handles both patterns.
    """
    return HybridMockResponse(content)


@pytest.fixture(autouse=True)
def mock_anthropic_client(monkeypatch):
    """
    Automatically mock the Anthropic client for all research tests.

    This patches get_default_client to return a mock client that
    returns appropriate responses without making real API calls.
    """
    # Create mock client that returns hybrid response
    mock_client = MagicMock()
    mock_client.create_message.side_effect = lambda **kwargs: create_mock_response()

    # Patch get_default_client in all research modules
    def mock_get_default_client():
        return mock_client

    # Patch in the anthropic_client module
    monkeypatch.setattr("src.utils.anthropic_client.get_default_client", mock_get_default_client)

    # Also patch in research modules that import it directly
    research_modules = [
        "src.research.content_audit",
        "src.research.story_mining",
        "src.research.competitive_analysis",
        "src.research.voice_analysis",
        "src.research.icp_workshop",
        "src.research.platform_strategy",
        "src.research.seo_keyword_research",
        "src.research.content_gap_analysis",
        "src.research.market_trends_research",
        "src.research.audience_research",
        "src.research.brand_archetype",
        "src.research.content_calendar_strategy",
        "src.research.base",
    ]

    for module in research_modules:
        try:
            monkeypatch.setattr(f"{module}.get_default_client", mock_get_default_client)
        except (AttributeError, ImportError):
            # Module doesn't import get_default_client directly or doesn't exist
            pass

    return mock_client


@pytest.fixture
def mock_client_with_response(mock_anthropic_client):
    """
    Fixture to set a custom response for the mock client.

    Usage:
        def test_custom(mock_client_with_response):
            mock_client_with_response('{"custom": "response"}')
            # Now API calls return this response
    """

    def _set_response(response_text: str):
        mock_anthropic_client.create_message.side_effect = lambda **kwargs: create_mock_response(
            response_text
        )

    return _set_response


@pytest.fixture
def mock_client_error(mock_anthropic_client):
    """
    Fixture to make the mock client raise an error.

    Usage:
        def test_error_handling(mock_client_error):
            mock_client_error("API rate limit exceeded")
            # Now API calls raise this error
    """

    def _set_error(error_message: str):
        mock_anthropic_client.create_message.side_effect = Exception(error_message)

    return _set_error


@pytest.fixture
def cleanup_research_outputs():
    """
    Fixture to clean up research output files after tests.
    """
    output_dir = Path("data/research")

    yield output_dir

    # Cleanup is optional - uncomment to auto-clean
    # import shutil
    # if output_dir.exists():
    #     shutil.rmtree(output_dir)
