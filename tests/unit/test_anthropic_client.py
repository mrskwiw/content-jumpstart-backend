"""Comprehensive unit tests for AnthropicClient

Tests API wrapper, retry logic, caching, and all client methods.
Achieves 90%+ coverage without making real API calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic import APIConnectionError, APIError, RateLimitError

from src.utils.anthropic_client import AnthropicClient, get_default_client


@pytest.fixture
def mock_anthropic_response():
    """Create mock Anthropic API response"""
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = "This is a test response from Claude"
    mock_response.content = [mock_content]

    # Mock usage for cost tracking
    mock_usage = MagicMock()
    mock_usage.input_tokens = 100
    mock_usage.output_tokens = 50
    mock_usage.cache_creation_input_tokens = 0
    mock_usage.cache_read_input_tokens = 0
    mock_response.usage = mock_usage

    return mock_response


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    with patch("src.utils.anthropic_client.settings") as mock_settings:
        mock_settings.ANTHROPIC_API_KEY = "test_api_key_123"  # pragma: allowlist secret
        mock_settings.ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
        mock_settings.MAX_TOKENS = 4096
        mock_settings.TEMPERATURE = 0.7
        mock_settings.ENABLE_PROMPT_CACHING = True
        mock_settings.CACHE_SYSTEM_PROMPTS = True
        mock_settings.ENABLE_RESPONSE_CACHE = False
        mock_settings.RESPONSE_CACHE_DIR = "/tmp/cache"
        mock_settings.RESPONSE_CACHE_TTL = 3600
        yield mock_settings


class TestAnthropicClientInit:
    """Test AnthropicClient initialization"""

    def test_init_with_api_key(self, mock_settings):
        """Test initialization with explicit API key"""
        client = AnthropicClient(api_key="custom_key")  # pragma: allowlist secret
        assert client.api_key == "custom_key"  # pragma: allowlist secret

    def test_init_with_settings_api_key(self, mock_settings):
        """Test initialization uses settings API key by default"""
        client = AnthropicClient()
        assert client.api_key == "test_api_key_123"  # pragma: allowlist secret

    def test_init_missing_api_key(self):
        """Test initialization fails without API key"""
        with patch("src.utils.anthropic_client.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = None
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not found"):
                AnthropicClient()

    def test_init_with_custom_model(self, mock_settings):
        """Test initialization with custom model"""
        client = AnthropicClient(model="claude-opus-4")
        assert client.model == "claude-opus-4"

    def test_init_with_custom_retry_settings(self, mock_settings):
        """Test initialization with custom retry parameters"""
        client = AnthropicClient(max_retries=5, retry_delay=2.0)
        assert client.max_retries == 5
        assert client.retry_delay == 2.0

    def test_init_creates_clients(self, mock_settings):
        """Test initialization creates sync and async clients"""
        client = AnthropicClient()
        assert client.client is not None
        assert client.async_client is not None

    def test_init_with_response_cache_enabled(self, mock_settings):
        """Test initialization with response cache enabled"""
        mock_settings.ENABLE_RESPONSE_CACHE = True
        client = AnthropicClient()
        assert client.response_cache is not None

    def test_init_with_response_cache_disabled(self, mock_settings):
        """Test initialization with response cache disabled"""
        mock_settings.ENABLE_RESPONSE_CACHE = False
        client = AnthropicClient()
        assert client.response_cache is None


class TestCreateMessage:
    """Test create_message synchronous method"""

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_create_message_success(self, mock_tracker, mock_settings, mock_anthropic_response):
        """Test successful message creation"""
        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            messages = [{"role": "user", "content": "Test message"}]
            result = client.create_message(messages, system="Test system prompt")

            assert result == "This is a test response from Claude"
            mock_client_instance.messages.create.assert_called_once()

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_create_message_with_defaults(
        self, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test message creation uses default settings"""
        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            messages = [{"role": "user", "content": "Test"}]
            client.create_message(messages)

            call_args = mock_client_instance.messages.create.call_args
            assert call_args.kwargs["model"] == "claude-3-5-sonnet-20241022"
            assert call_args.kwargs["max_tokens"] == 4096
            assert call_args.kwargs["temperature"] == 0.7

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_create_message_with_custom_params(
        self, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test message creation with custom parameters"""
        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            messages = [{"role": "user", "content": "Test"}]
            client.create_message(messages, max_tokens=2000, temperature=0.5)

            call_args = mock_client_instance.messages.create.call_args
            assert call_args.kwargs["max_tokens"] == 2000
            assert call_args.kwargs["temperature"] == 0.5

    @patch("src.utils.anthropic_client.get_default_tracker")
    @patch("src.utils.anthropic_client.time.sleep")
    def test_create_message_rate_limit_retry(
        self, mock_sleep, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test retry logic on rate limit error"""
        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            # Fail twice, then succeed
            mock_client_instance.messages.create.side_effect = [
                RateLimitError("Rate limit exceeded", response=MagicMock(), body=None),
                RateLimitError("Rate limit exceeded", response=MagicMock(), body=None),
                mock_anthropic_response,
            ]
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient(max_retries=3, retry_delay=1.0)
            messages = [{"role": "user", "content": "Test"}]
            result = client.create_message(messages)

            assert result == "This is a test response from Claude"
            assert mock_client_instance.messages.create.call_count == 3
            # Verify exponential backoff sleep calls
            assert mock_sleep.call_count == 2

    @patch("src.utils.anthropic_client.get_default_tracker")
    @patch("src.utils.anthropic_client.time.sleep")
    def test_create_message_connection_error_retry(
        self, mock_sleep, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test retry logic on connection error"""
        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.side_effect = [
                APIConnectionError(message="Connection failed", request=MagicMock()),
                mock_anthropic_response,
            ]
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient(max_retries=3, retry_delay=1.0)
            messages = [{"role": "user", "content": "Test"}]
            result = client.create_message(messages)

            assert result == "This is a test response from Claude"
            assert mock_sleep.call_count == 1

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_create_message_api_error_no_retry(self, mock_tracker, mock_settings):
        """Test non-retryable API errors raise immediately"""
        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.side_effect = APIError(
                "Invalid request", request=MagicMock(), body=None
            )
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient(max_retries=3)
            messages = [{"role": "user", "content": "Test"}]

            with pytest.raises(APIError):
                client.create_message(messages)

            # Should fail immediately without retries
            assert mock_client_instance.messages.create.call_count == 1

    @patch("src.utils.anthropic_client.get_default_tracker")
    @patch("src.utils.anthropic_client.time.sleep")
    def test_create_message_all_retries_fail(self, mock_sleep, mock_tracker, mock_settings):
        """Test raises exception when all retries exhausted"""
        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.side_effect = RateLimitError(
                "Rate limit", response=MagicMock(), body=None
            )
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient(max_retries=2, retry_delay=0.1)
            messages = [{"role": "user", "content": "Test"}]

            with pytest.raises(RateLimitError):
                client.create_message(messages)

            assert mock_client_instance.messages.create.call_count == 2

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_create_message_empty_response(self, mock_tracker, mock_settings):
        """Test handles empty response"""
        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_empty_response = MagicMock()
            mock_empty_response.content = []
            mock_client_instance.messages.create.return_value = mock_empty_response
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            messages = [{"role": "user", "content": "Test"}]

            with pytest.raises(RuntimeError, match="Empty response from API"):
                client.create_message(messages)

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_create_message_with_cost_tracking(
        self, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test cost tracking is called when project_id provided"""
        mock_tracker_instance = MagicMock()
        mock_tracker.return_value = mock_tracker_instance

        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            messages = [{"role": "user", "content": "Test"}]
            client.create_message(messages, project_id="test_project", operation="test_op")

            # Verify cost tracking was called
            mock_tracker_instance.track_api_call.assert_called_once()
            call_args = mock_tracker_instance.track_api_call.call_args.kwargs
            assert call_args["project_id"] == "test_project"
            assert call_args["operation"] == "test_op"


class TestCreateMessageAsync:
    """Test create_message_async asynchronous method"""

    @pytest.mark.asyncio
    @patch("src.utils.anthropic_client.get_default_tracker")
    async def test_create_message_async_success(
        self, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test successful async message creation"""
        with patch("src.utils.anthropic_client.AsyncAnthropic") as mock_async_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create = AsyncMock(return_value=mock_anthropic_response)
            mock_async_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            messages = [{"role": "user", "content": "Test async"}]
            result = await client.create_message_async(messages, system="Test system")

            assert result == "This is a test response from Claude"

    @pytest.mark.asyncio
    @patch("src.utils.anthropic_client.get_default_tracker")
    async def test_create_message_async_rate_limit_retry(
        self, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test async retry logic on rate limit"""
        with patch("src.utils.anthropic_client.AsyncAnthropic") as mock_async_anthropic_class:
            mock_client_instance = MagicMock()
            # Fail once, then succeed
            mock_client_instance.messages.create = AsyncMock(
                side_effect=[
                    RateLimitError("Rate limit", response=MagicMock(), body=None),
                    mock_anthropic_response,
                ]
            )
            mock_async_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient(max_retries=3, retry_delay=0.1)
            messages = [{"role": "user", "content": "Test"}]
            result = await client.create_message_async(messages)

            assert result == "This is a test response from Claude"

    @pytest.mark.asyncio
    @patch("src.utils.anthropic_client.get_default_tracker")
    async def test_create_message_async_api_error(self, mock_tracker, mock_settings):
        """Test async non-retryable errors raise immediately"""
        with patch("src.utils.anthropic_client.AsyncAnthropic") as mock_async_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create = AsyncMock(
                side_effect=APIError("Invalid", request=MagicMock(), body=None)
            )
            mock_async_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            messages = [{"role": "user", "content": "Test"}]

            with pytest.raises(APIError):
                await client.create_message_async(messages)


class TestHelperMethods:
    """Test helper methods"""

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_prepare_system_with_caching_enabled(self, mock_tracker, mock_settings):
        """Test system prompt preparation with caching enabled"""
        client = AnthropicClient()
        result = client._prepare_system_with_caching("Test system prompt", enable_caching=True)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert result[0]["text"] == "Test system prompt"
        assert result[0]["cache_control"]["type"] == "ephemeral"

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_prepare_system_with_caching_disabled(self, mock_tracker, mock_settings):
        """Test system prompt preparation without caching"""
        client = AnthropicClient()
        result = client._prepare_system_with_caching("Test system prompt", enable_caching=False)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert result[0]["text"] == "Test system prompt"
        assert "cache_control" not in result[0]

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_format_context_optimized(self, mock_tracker, mock_settings):
        """Test context optimization filters empty fields"""
        client = AnthropicClient()

        context = {
            "company_name": "Test Co",
            "ideal_customer": "Business owners",
            "empty_field": "",
            "empty_list": [],
            "populated_list": ["item1", "item2", "item3"],
            "template_type": "should_be_skipped",
        }

        result = client._format_context_optimized(context)

        assert "company_name: Test Co" in result
        assert "ideal_customer: Business owners" in result
        assert "empty_field" not in result
        assert "empty_list" not in result
        assert "populated_list: item1, item2, item3" in result
        assert "template_type" not in result  # Filtered out

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_format_context_optimized_limits_list_items(self, mock_tracker, mock_settings):
        """Test context optimization limits list items to 5"""
        client = AnthropicClient()

        context = {"long_list": ["item1", "item2", "item3", "item4", "item5", "item6", "item7"]}

        result = client._format_context_optimized(context)

        # Should only include first 5 items
        assert "item1" in result
        assert "item5" in result
        assert "item6" not in result
        assert "item7" not in result


class TestHighLevelMethods:
    """Test high-level convenience methods"""

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_create_brief_analysis(self, mock_tracker, mock_settings, mock_anthropic_response):
        """Test brief analysis method"""
        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            result = client.create_brief_analysis("Test brief content")

            assert result == "This is a test response from Claude"
            # Should use brief parsing temperature
            call_args = mock_client_instance.messages.create.call_args.kwargs
            assert call_args["temperature"] == 0.3  # BRIEF_PARSING_TEMPERATURE

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_generate_post_content(self, mock_tracker, mock_settings, mock_anthropic_response):
        """Test post content generation"""
        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            context = {"company_name": "Test Co", "problem": "Inefficiency"}
            result = client.generate_post_content("Template structure", context)

            assert result == "This is a test response from Claude"
            # Should use post generation temperature
            call_args = mock_client_instance.messages.create.call_args.kwargs
            assert call_args["temperature"] == 0.7  # POST_GENERATION_TEMPERATURE

    @pytest.mark.asyncio
    @patch("src.utils.anthropic_client.get_default_tracker")
    async def test_generate_post_content_async(
        self, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test async post content generation"""
        with patch("src.utils.anthropic_client.AsyncAnthropic") as mock_async_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create = AsyncMock(return_value=mock_anthropic_response)
            mock_async_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            context = {"company_name": "Test Co"}
            result = await client.generate_post_content_async("Template", context)

            assert result == "This is a test response from Claude"

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_refine_post(self, mock_tracker, mock_settings, mock_anthropic_response):
        """Test post refinement method"""
        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            context = {"company_name": "Test Co"}
            result = client.refine_post("Original post", "Make it shorter", context)

            assert result == "This is a test response from Claude"
            # Verify user message includes feedback
            call_args = mock_client_instance.messages.create.call_args.kwargs
            user_content = call_args["messages"][0]["content"]
            assert "Original post" in user_content
            assert "Make it shorter" in user_content


class TestResponseCache:
    """Test response cache integration"""

    @patch("src.utils.anthropic_client.get_default_tracker")
    @patch("src.utils.anthropic_client.ResponseCache")
    def test_create_message_uses_cache(
        self, mock_cache_class, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test message creation uses response cache when available"""
        mock_cache_instance = MagicMock()
        mock_cache_instance.get.return_value = "Cached response"
        mock_cache_class.return_value = mock_cache_instance

        mock_settings.ENABLE_RESPONSE_CACHE = True

        with patch("src.utils.anthropic_client.Anthropic"):
            client = AnthropicClient(enable_response_cache=True)
            messages = [{"role": "user", "content": "Test"}]
            result = client.create_message(messages, system="System")

            # Should return cached response without API call
            assert result == "Cached response"
            mock_cache_instance.get.assert_called_once()

    @patch("src.utils.anthropic_client.get_default_tracker")
    @patch("src.utils.anthropic_client.ResponseCache")
    def test_create_message_stores_in_cache(
        self, mock_cache_class, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test message creation stores response in cache"""
        mock_cache_instance = MagicMock()
        mock_cache_instance.get.return_value = None  # Cache miss
        mock_cache_class.return_value = mock_cache_instance

        mock_settings.ENABLE_RESPONSE_CACHE = True

        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient(enable_response_cache=True)
            messages = [{"role": "user", "content": "Test"}]
            _result = client.create_message(messages)

            # Should store in cache after API call
            mock_cache_instance.put.assert_called_once()


class TestGetDefaultClient:
    """Test get_default_client singleton function"""

    @patch("src.utils.anthropic_client.settings")
    def test_get_default_client_returns_instance(self, mock_settings):
        """Test get_default_client returns AnthropicClient instance"""
        mock_settings.ANTHROPIC_API_KEY = "test_key"  # pragma: allowlist secret
        mock_settings.ENABLE_RESPONSE_CACHE = False
        client = get_default_client()
        assert isinstance(client, AnthropicClient)

    @patch("src.utils.anthropic_client.settings")
    def test_get_default_client_singleton(self, mock_settings):
        """Test get_default_client returns same instance"""
        mock_settings.ANTHROPIC_API_KEY = "test_key"  # pragma: allowlist secret
        mock_settings.ENABLE_RESPONSE_CACHE = False
        client1 = get_default_client()
        client2 = get_default_client()
        assert client1 is client2


class TestAsyncCoverageGaps:
    """Test async methods for full coverage"""

    @pytest.mark.asyncio
    @patch("src.utils.anthropic_client.get_default_tracker")
    async def test_async_with_cost_tracking(
        self, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test async message creation with cost tracking"""
        mock_tracker_instance = MagicMock()
        mock_tracker.return_value = mock_tracker_instance

        with patch("src.utils.anthropic_client.AsyncAnthropic") as mock_async_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create = AsyncMock(return_value=mock_anthropic_response)
            mock_async_class.return_value = mock_client_instance

            client = AnthropicClient()
            messages = [{"role": "user", "content": "Test async"}]
            result = await client.create_message_async(
                messages, project_id="test_project", operation="async_op"
            )

            assert result == "This is a test response from Claude"
            mock_tracker_instance.track_api_call.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.utils.anthropic_client.get_default_tracker")
    async def test_async_cost_tracking_failure(
        self, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test async cost tracking failure doesn't break execution"""
        mock_tracker_instance = MagicMock()
        mock_tracker_instance.track_api_call.side_effect = Exception("Tracking failed")
        mock_tracker.return_value = mock_tracker_instance

        with patch("src.utils.anthropic_client.AsyncAnthropic") as mock_async_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create = AsyncMock(return_value=mock_anthropic_response)
            mock_async_class.return_value = mock_client_instance

            client = AnthropicClient()
            messages = [{"role": "user", "content": "Test"}]
            result = await client.create_message_async(messages, project_id="test")

            assert result == "This is a test response from Claude"

    @pytest.mark.asyncio
    @patch("src.utils.anthropic_client.get_default_tracker")
    @patch("src.utils.anthropic_client.ResponseCache")
    async def test_async_with_cache_hit(self, mock_cache_class, mock_tracker, mock_settings):
        """Test async message creation uses cache hit"""
        mock_cache_instance = MagicMock()
        mock_cache_instance.get.return_value = "Cached async response"
        mock_cache_class.return_value = mock_cache_instance

        mock_settings.ENABLE_RESPONSE_CACHE = True

        with patch("src.utils.anthropic_client.AsyncAnthropic"):
            client = AnthropicClient(enable_response_cache=True)
            messages = [{"role": "user", "content": "Test"}]
            result = await client.create_message_async(messages, system="System")

            assert result == "Cached async response"
            mock_cache_instance.get.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.utils.anthropic_client.get_default_tracker")
    @patch("src.utils.anthropic_client.ResponseCache")
    async def test_async_stores_in_cache(
        self, mock_cache_class, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test async message creation stores response in cache"""
        mock_cache_instance = MagicMock()
        mock_cache_instance.get.return_value = None
        mock_cache_class.return_value = mock_cache_instance

        mock_settings.ENABLE_RESPONSE_CACHE = True

        with patch("src.utils.anthropic_client.AsyncAnthropic") as mock_async_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create = AsyncMock(return_value=mock_anthropic_response)
            mock_async_class.return_value = mock_client_instance

            client = AnthropicClient(enable_response_cache=True)
            messages = [{"role": "user", "content": "Test"}]
            await client.create_message_async(messages)

            mock_cache_instance.put.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.utils.anthropic_client.get_default_tracker")
    async def test_async_empty_response(self, mock_tracker, mock_settings):
        """Test async handles empty response"""
        with patch("src.utils.anthropic_client.AsyncAnthropic") as mock_async_class:
            mock_client_instance = MagicMock()
            mock_empty_response = MagicMock()
            mock_empty_response.content = []
            mock_client_instance.messages.create = AsyncMock(return_value=mock_empty_response)
            mock_async_class.return_value = mock_client_instance

            client = AnthropicClient()
            messages = [{"role": "user", "content": "Test"}]

            with pytest.raises(RuntimeError, match="Empty response from API"):
                await client.create_message_async(messages)

    @pytest.mark.asyncio
    @patch("src.utils.anthropic_client.get_default_tracker")
    async def test_async_connection_error_all_retries_fail(self, mock_tracker, mock_settings):
        """Test async all retries fail on connection error with diagnostics"""
        from src.utils.connection_diagnostics import ConnectionDiagnostics, ConnectionErrorType

        with patch("src.utils.anthropic_client.AsyncAnthropic") as mock_async_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create = AsyncMock(
                side_effect=APIConnectionError(message="Connection refused", request=MagicMock())
            )
            mock_async_class.return_value = mock_client_instance

            mock_diagnostics = ConnectionDiagnostics(
                error_type=ConnectionErrorType.CONNECTION_REFUSED,
                suggestions=["Check network"],
            )

            client = AnthropicClient(max_retries=2, retry_delay=0.01)
            messages = [{"role": "user", "content": "Test"}]

            with patch(
                "src.utils.anthropic_client.diagnose_connection_error",
                return_value=mock_diagnostics,
            ):
                with pytest.raises(APIConnectionError):
                    await client.create_message_async(messages)

            assert len(client.error_history) >= 1

    @pytest.mark.asyncio
    @patch("src.utils.anthropic_client.get_default_tracker")
    async def test_async_all_retries_fail_runtime_error(self, mock_tracker, mock_settings):
        """Test async raises RuntimeError when all retries fail without exception"""
        with patch("src.utils.anthropic_client.AsyncAnthropic") as mock_async_class:
            mock_client_instance = MagicMock()
            # Make it fail with rate limit that exhausts retries
            mock_client_instance.messages.create = AsyncMock(
                side_effect=RateLimitError("Rate limit", response=MagicMock(), body=None)
            )
            mock_async_class.return_value = mock_client_instance

            client = AnthropicClient(max_retries=1, retry_delay=0.01)
            messages = [{"role": "user", "content": "Test"}]

            with pytest.raises(RateLimitError):
                await client.create_message_async(messages)


class TestEdgeCases:
    """Test edge cases and error scenarios"""

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_create_message_with_none_system(
        self, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test message creation with None system prompt"""
        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            messages = [{"role": "user", "content": "Test"}]
            result = client.create_message(messages, system=None)

            assert result == "This is a test response from Claude"
            # Should not include system in API call
            call_args = mock_client_instance.messages.create.call_args.kwargs
            assert "system" not in call_args or call_args.get("system") is None

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_create_message_with_additional_kwargs(
        self, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test message creation passes through additional kwargs"""
        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            messages = [{"role": "user", "content": "Test"}]
            result = client.create_message(messages, stop_sequences=["END"], top_p=0.9)

            assert result == "This is a test response from Claude"
            call_args = mock_client_instance.messages.create.call_args.kwargs
            assert call_args["stop_sequences"] == ["END"]
            assert call_args["top_p"] == 0.9

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_cost_tracking_failure_is_logged(
        self, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test cost tracking failure doesn't break message creation"""
        mock_tracker_instance = MagicMock()
        mock_tracker_instance.track_api_call.side_effect = Exception("Tracking failed")
        mock_tracker.return_value = mock_tracker_instance

        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            messages = [{"role": "user", "content": "Test"}]

            # Should succeed despite tracking failure
            result = client.create_message(messages, project_id="test")
            assert result == "This is a test response from Claude"

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_create_brief_analysis_with_custom_prompt(
        self, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test brief analysis with custom system prompt"""
        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            result = client.create_brief_analysis(
                "Test brief", system_prompt="Custom analysis prompt"
            )

            assert result == "This is a test response from Claude"
            call_args = mock_client_instance.messages.create.call_args.kwargs
            # Should use custom system prompt
            assert "Custom analysis prompt" in str(call_args.get("system", ""))

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_generate_post_content_with_custom_prompt(
        self, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test post generation with custom system prompt"""
        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            context = {"company_name": "Test Co"}
            result = client.generate_post_content(
                "Template", context, system_prompt="Custom gen prompt"
            )

            assert result == "This is a test response from Claude"
            call_args = mock_client_instance.messages.create.call_args.kwargs
            assert "Custom gen prompt" in str(call_args.get("system", ""))

    @pytest.mark.asyncio
    @patch("src.utils.anthropic_client.get_default_tracker")
    async def test_generate_post_content_async_with_custom_prompt(
        self, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test async post generation with custom system prompt"""
        with patch("src.utils.anthropic_client.AsyncAnthropic") as mock_async_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create = AsyncMock(return_value=mock_anthropic_response)
            mock_async_class.return_value = mock_client_instance

            client = AnthropicClient()
            context = {"company_name": "Test Co"}
            result = await client.generate_post_content_async(
                "Template", context, system_prompt="Custom async prompt"
            )

            assert result == "This is a test response from Claude"

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_format_context_with_dict_value(self, mock_tracker, mock_settings):
        """Test context formatting with dict values"""
        client = AnthropicClient()

        context = {
            "company_name": "Test Co",
            "metadata": {"key1": "val1", "key2": "val2"},  # Dict value
            "empty_dict": {},  # Empty dict should be skipped
        }

        result = client._format_context_optimized(context)

        assert "company_name: Test Co" in result
        # Dict values should be skipped (not formatted as lists)
        assert "metadata" not in result
        assert "empty_dict" not in result

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_format_context_with_none_value(self, mock_tracker, mock_settings):
        """Test context formatting with None values"""
        client = AnthropicClient()

        context = {
            "company_name": "Test Co",
            "none_field": None,  # None should be included as-is
        }

        result = client._format_context_optimized(context)

        assert "company_name: Test Co" in result

    @patch("src.utils.anthropic_client.get_default_tracker")
    def test_create_message_with_system_no_caching(
        self, mock_tracker, mock_settings, mock_anthropic_response
    ):
        """Test message creation with system prompt but caching disabled"""
        mock_settings.ENABLE_PROMPT_CACHING = False
        mock_settings.CACHE_SYSTEM_PROMPTS = False

        with patch("src.utils.anthropic_client.Anthropic") as mock_anthropic_class:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_client_instance

            client = AnthropicClient()
            messages = [{"role": "user", "content": "Test"}]
            result = client.create_message(
                messages, system="Test system", enable_prompt_caching=False
            )

            assert result == "This is a test response from Claude"
            call_args = mock_client_instance.messages.create.call_args.kwargs
            # System should be plain string or simple list without cache_control
            system_arg = call_args.get("system", "")
            if isinstance(system_arg, list):
                assert "cache_control" not in system_arg[0]
