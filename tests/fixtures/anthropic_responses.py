"""
Mock Anthropic API responses for testing.
NEVER makes real API calls - all responses are mocked.

This module provides fixtures for mocking the AnthropicClient to prevent
real API calls during testing, which would incur costs and slow down tests.
"""

import json
from typing import Any, Dict, Optional
from unittest.mock import MagicMock
import pytest


# ==================== Sample Mock Responses ====================

MOCK_BRIEF_PARSING_RESPONSE = {
    "company_name": "Test Company Inc",
    "business_description": "We provide cloud-based project management software for small businesses looking to streamline their operations.",
    "ideal_customer": "Small business owners with 5-20 employees who struggle with manual workflow management.",
    "main_problem_solved": "Inefficient workflows and scattered communication across multiple tools.",
    "customer_pain_points": [
        "Wasting time on manual data entry and task tracking",
        "Poor team collaboration due to scattered communication",
        "Lack of visibility into project progress and bottlenecks",
    ],
    "customer_questions": [
        "How can we improve team productivity without adding complexity?",
        "What tools integrate with our existing software stack?",
    ],
    "unique_value_proposition": "All-in-one platform that's 10x faster to set up than competitors",
    "platform_preferences": ["linkedin", "twitter"],
    "brand_voice_notes": "Professional yet approachable, data-driven, emphasizing ROI",
    "tone_preference": "professional",
}

MOCK_POST_GENERATION_RESPONSE = """Here's a compelling LinkedIn post about productivity:

Most teams waste 30% of their time switching between apps.

We analyzed 500 small businesses and found they use an average of 12 different tools daily.
- 45 minutes lost per day to context switching
- 3 hours per week in status update meetings
- $15K annual cost per employee in lost productivity

The solution isn't adding more tools. It's consolidating them.

Our clients cut app usage by 60% and saved 10 hours/week per team member.

What's your biggest productivity killer? Drop it in the comments. 👇

[CTA: Try our free workflow assessment]"""

MOCK_VOICE_ANALYSIS_RESPONSE = {
    "formality_level": "semi-formal",
    "tone": "professional",
    "perspective": "first-person-plural",
    "sentence_variety": "varied",
    "reading_ease": 65.5,
}

MOCK_QA_VALIDATION_RESPONSE = {
    "hook_uniqueness": 0.95,
    "cta_present": True,
    "cta_type": "question",
    "length_appropriate": True,
    "word_count": 142,
    "quality_flags": [],
    "overall_quality_score": 92.0,
}


# ==================== Mock Fixtures ====================


@pytest.fixture
def mock_anthropic_client(monkeypatch):
    """
    Mock AnthropicClient to prevent real API calls.

    This fixture monkeypatches both synchronous and asynchronous message
    creation methods to return predefined responses based on the system
    prompt content.

    Usage:
        def test_something(mock_anthropic_client):
            # AnthropicClient calls will be mocked automatically
            result = some_function_that_uses_anthropic_client()
            assert result is not None
    """
    from src.utils.anthropic_client import AnthropicClient

    def mock_create_message(self, messages, **kwargs):
        """Mock synchronous message creation"""
        system = kwargs.get("system", "")

        # Detect agent type from system prompt
        if "parse the client brief" in system.lower() or "extract" in system.lower():
            return json.dumps(MOCK_BRIEF_PARSING_RESPONSE)
        elif "generate" in system.lower() and "post" in system.lower():
            return MOCK_POST_GENERATION_RESPONSE
        elif "voice" in system.lower() or "tone" in system.lower():
            return json.dumps(MOCK_VOICE_ANALYSIS_RESPONSE)
        elif "quality" in system.lower() or "validate" in system.lower():
            return json.dumps(MOCK_QA_VALIDATION_RESPONSE)
        else:
            # Default response
            return "This is a mocked Anthropic API response."

    async def mock_create_message_async(self, messages, **kwargs):
        """Mock async message creation"""
        return mock_create_message(self, messages, **kwargs)

    # Monkeypatch the methods
    monkeypatch.setattr(AnthropicClient, "create_message", mock_create_message)
    monkeypatch.setattr(AnthropicClient, "create_message_async", mock_create_message_async)

    return MagicMock(
        create_message=mock_create_message, create_message_async=mock_create_message_async
    )


@pytest.fixture
def mock_anthropic_client_with_custom_response(monkeypatch):
    """
    Factory fixture for custom Anthropic responses.

    This allows tests to specify exactly what response should be returned
    for specific scenarios.

    Usage:
        def test_custom_response(mock_anthropic_client_with_custom_response):
            mock_anthropic_client_with_custom_response({
                "custom_field": "custom_value",
                "another_field": 123
            })
            result = function_that_calls_anthropic()
            assert result["custom_field"] == "custom_value"
    """

    def _mock_with_response(custom_response: Dict[str, Any]):
        from src.utils.anthropic_client import AnthropicClient

        def mock_create(self, messages, **kwargs):
            if isinstance(custom_response, dict):
                return json.dumps(custom_response)
            return str(custom_response)

        async def mock_create_async(self, messages, **kwargs):
            if isinstance(custom_response, dict):
                return json.dumps(custom_response)
            return str(custom_response)

        monkeypatch.setattr(AnthropicClient, "create_message", mock_create)
        monkeypatch.setattr(AnthropicClient, "create_message_async", mock_create_async)

    return _mock_with_response


@pytest.fixture
def mock_anthropic_client_with_error(monkeypatch):
    """
    Mock AnthropicClient to raise an error.

    Useful for testing error handling and retry logic.

    Usage:
        def test_api_error_handling(mock_anthropic_client_with_error):
            with pytest.raises(Exception):
                function_that_calls_anthropic()
    """
    from src.utils.anthropic_client import AnthropicClient

    def mock_create_error(self, messages, **kwargs):
        raise Exception("Mocked Anthropic API error")

    async def mock_create_error_async(self, messages, **kwargs):
        raise Exception("Mocked Anthropic API error")

    monkeypatch.setattr(AnthropicClient, "create_message", mock_create_error)
    monkeypatch.setattr(AnthropicClient, "create_message_async", mock_create_error_async)


# ==================== Response Templates ====================


def get_mock_brief_response(**overrides) -> Dict[str, Any]:
    """
    Get a mock brief parsing response with optional field overrides.

    Args:
        **overrides: Fields to override in the default response

    Returns:
        Dict with brief parsing response

    Example:
        response = get_mock_brief_response(company_name="Custom Corp")
    """
    response = MOCK_BRIEF_PARSING_RESPONSE.copy()
    response.update(overrides)
    return response


def get_mock_post_response(
    word_count: int = 150, has_cta: bool = True, topic: Optional[str] = None
) -> str:
    """
    Get a mock post generation response with specified parameters.

    Args:
        word_count: Target word count (approximate)
        has_cta: Whether to include a CTA
        topic: Optional topic to mention

    Returns:
        String with mocked post content
    """
    if topic:
        base_text = f"Here's a compelling post about {topic}:\n\n"
    else:
        base_text = MOCK_POST_GENERATION_RESPONSE

    if not has_cta and "[CTA:" in base_text:
        base_text = base_text.split("[CTA:")[0].strip()

    return base_text


def get_mock_voice_response(**overrides) -> Dict[str, Any]:
    """
    Get a mock voice analysis response with optional overrides.

    Args:
        **overrides: Fields to override

    Returns:
        Dict with voice analysis response
    """
    response = MOCK_VOICE_ANALYSIS_RESPONSE.copy()
    response.update(overrides)
    return response
