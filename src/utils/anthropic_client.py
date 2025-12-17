"""Wrapper for Anthropic API calls with error handling and retry logic"""

import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from anthropic import Anthropic, APIConnectionError, APIError, AsyncAnthropic, RateLimitError

from ..config.constants import (
    BRIEF_PARSING_TEMPERATURE,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    POST_GENERATION_TEMPERATURE,
)
from ..config.prompts import SystemPrompts
from ..config.settings import settings
from .cost_tracker import get_default_tracker
from .logger import log_api_call, log_error, logger
from .response_cache import ResponseCache


class AnthropicClient:
    """Wrapper for Anthropic API with retry logic and error handling"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        enable_response_cache: Optional[bool] = None,
    ):
        """
        Initialize Anthropic client

        Args:
            api_key: Anthropic API key (defaults to settings)
            model: Model to use (defaults to settings)
            max_retries: Maximum number of retries on failure
            retry_delay: Initial delay between retries (exponential backoff)
            enable_response_cache: Enable disk-based response caching
        """
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self.max_retries = max_retries or DEFAULT_MAX_RETRIES
        self.retry_delay = retry_delay or DEFAULT_RETRY_DELAY

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables or settings")

        self.client = Anthropic(api_key=self.api_key)
        self.async_client = AsyncAnthropic(api_key=self.api_key)

        # Initialize response cache if enabled
        if enable_response_cache is None:
            enable_response_cache = settings.ENABLE_RESPONSE_CACHE

        self.response_cache = (
            ResponseCache(
                cache_dir=Path(settings.RESPONSE_CACHE_DIR),
                ttl_seconds=settings.RESPONSE_CACHE_TTL,
                enabled=enable_response_cache,
            )
            if enable_response_cache
            else None
        )

        # Initialize cost tracker
        self.cost_tracker = get_default_tracker()

    def create_message(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_cache: bool = True,
        enable_prompt_caching: Optional[bool] = None,
        project_id: Optional[str] = None,
        operation: str = "api_call",
        **kwargs,
    ) -> str:
        """
        Create a message using the Anthropic API with retry logic and caching

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system: Optional system prompt
            max_tokens: Maximum tokens to generate (defaults to settings)
            temperature: Sampling temperature (defaults to settings)
            use_cache: Whether to use response cache (default: True)
            enable_prompt_caching: Use Anthropic prompt caching (default: from settings)
            project_id: Optional project ID for cost tracking
            operation: Operation name for cost tracking (default: "api_call")
            **kwargs: Additional arguments to pass to API

        Returns:
            Generated text content

        Raises:
            APIError: If API call fails after all retries
        """
        max_tokens = max_tokens or settings.MAX_TOKENS
        temperature = temperature or settings.TEMPERATURE

        if enable_prompt_caching is None:
            enable_prompt_caching = settings.ENABLE_PROMPT_CACHING

        # Try response cache first
        if use_cache and self.response_cache:
            cached_response = self.response_cache.get(messages, system or "", temperature)
            if cached_response:
                return cached_response

        # Estimate tokens for logging (rough approximation)
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        if system:
            total_chars += len(system)
        estimated_tokens = total_chars // 4  # Rough estimate: 4 chars per token

        log_api_call(self.model, estimated_tokens)

        # Prepare system prompt with optional caching
        system_messages = (
            self._prepare_system_with_caching(system, enable_prompt_caching) if system else None
        )

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                # Build API call parameters
                api_params = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": messages,
                    **kwargs,
                }

                # Only include system if it's not None
                if system_messages:
                    api_params["system"] = system_messages
                elif system:
                    api_params["system"] = system

                response = self.client.messages.create(**api_params)

                # Extract text from response
                if response.content and len(response.content) > 0:
                    response_text = response.content[0].text

                    # Track cost if project_id provided
                    if project_id and hasattr(response, "usage"):
                        try:
                            self.cost_tracker.track_api_call(
                                project_id=project_id,
                                operation=operation,
                                model=self.model,
                                input_tokens=response.usage.input_tokens,
                                output_tokens=response.usage.output_tokens,
                                cache_creation_tokens=getattr(
                                    response.usage, "cache_creation_input_tokens", 0
                                ),
                                cache_read_tokens=getattr(
                                    response.usage, "cache_read_input_tokens", 0
                                ),
                            )
                        except Exception as e:
                            logger.warning(f"Failed to track API cost: {e}")

                    # Cache the response
                    if use_cache and self.response_cache:
                        self.response_cache.put(messages, system or "", temperature, response_text)

                    return response_text
                else:
                    raise APIError("Empty response from API")

            except RateLimitError as e:
                last_exception = e
                wait_time = self.retry_delay * (2**attempt)  # Exponential backoff
                logger.warning(
                    f"Rate limit hit (attempt {attempt + 1}/{self.max_retries}), "
                    f"waiting {wait_time}s before retry"
                )
                time.sleep(wait_time)

            except APIConnectionError as e:
                last_exception = e
                wait_time = self.retry_delay * (2**attempt)
                logger.warning(
                    f"Connection error (attempt {attempt + 1}/{self.max_retries}), "
                    f"waiting {wait_time}s before retry"
                )
                time.sleep(wait_time)

            except APIError as e:
                last_exception = e
                # Don't retry on non-retryable errors
                log_error(f"API error: {str(e)}", exc_info=True)
                raise

        # If we get here, all retries failed
        log_error(f"All {self.max_retries} retries failed", exc_info=True)
        raise last_exception

    async def create_message_async(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_cache: bool = True,
        enable_prompt_caching: Optional[bool] = None,
        project_id: Optional[str] = None,
        operation: str = "api_call",
        **kwargs,
    ) -> str:
        """
        Async version of create_message for parallel execution

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system: Optional system prompt
            max_tokens: Maximum tokens to generate (defaults to settings)
            temperature: Sampling temperature (defaults to settings)
            use_cache: Whether to use response cache (default: True)
            enable_prompt_caching: Use Anthropic prompt caching (default: from settings)
            project_id: Optional project ID for cost tracking
            operation: Operation name for cost tracking (default: "api_call")
            **kwargs: Additional arguments to pass to API

        Returns:
            Generated text content

        Raises:
            APIError: If API call fails after all retries
        """
        max_tokens = max_tokens or settings.MAX_TOKENS
        temperature = temperature or settings.TEMPERATURE

        if enable_prompt_caching is None:
            enable_prompt_caching = settings.ENABLE_PROMPT_CACHING

        # Try response cache first
        if use_cache and self.response_cache:
            cached_response = self.response_cache.get(messages, system or "", temperature)
            if cached_response:
                return cached_response

        # Estimate tokens for logging (rough approximation)
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        if system:
            total_chars += len(system)
        estimated_tokens = total_chars // 4  # Rough estimate: 4 chars per token

        log_api_call(self.model, estimated_tokens)

        # Prepare system prompt with optional caching
        system_messages = (
            self._prepare_system_with_caching(system, enable_prompt_caching) if system else None
        )

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                # Build API call parameters
                api_params = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": messages,
                    **kwargs,
                }

                # Only include system if it's not None
                if system_messages:
                    api_params["system"] = system_messages
                elif system:
                    api_params["system"] = system

                response = await self.async_client.messages.create(**api_params)

                # Extract text from response
                if response.content and len(response.content) > 0:
                    response_text = response.content[0].text

                    # Track cost if project_id provided
                    if project_id and hasattr(response, "usage"):
                        try:
                            self.cost_tracker.track_api_call(
                                project_id=project_id,
                                operation=operation,
                                model=self.model,
                                input_tokens=response.usage.input_tokens,
                                output_tokens=response.usage.output_tokens,
                                cache_creation_tokens=getattr(
                                    response.usage, "cache_creation_input_tokens", 0
                                ),
                                cache_read_tokens=getattr(
                                    response.usage, "cache_read_input_tokens", 0
                                ),
                            )
                        except Exception as e:
                            logger.warning(f"Failed to track API cost: {e}")

                    # Cache the response
                    if use_cache and self.response_cache:
                        self.response_cache.put(messages, system or "", temperature, response_text)

                    return response_text
                else:
                    raise APIError("Empty response from API")

            except RateLimitError as e:
                last_exception = e
                wait_time = self.retry_delay * (2**attempt)  # Exponential backoff
                logger.warning(
                    f"Rate limit hit (attempt {attempt + 1}/{self.max_retries}), "
                    f"waiting {wait_time}s before retry"
                )
                await asyncio.sleep(wait_time)

            except APIConnectionError as e:
                last_exception = e
                wait_time = self.retry_delay * (2**attempt)
                logger.warning(
                    f"Connection error (attempt {attempt + 1}/{self.max_retries}), "
                    f"waiting {wait_time}s before retry"
                )
                await asyncio.sleep(wait_time)

            except APIError as e:
                last_exception = e
                # Don't retry on non-retryable errors
                log_error(f"API error: {str(e)}", exc_info=True)
                raise

        # If we get here, all retries failed
        log_error(f"All {self.max_retries} retries failed", exc_info=True)
        raise last_exception

    def create_brief_analysis(self, brief_content: str, system_prompt: Optional[str] = None) -> str:
        """
        Analyze a client brief and extract structured information

        Args:
            brief_content: Raw client brief text
            system_prompt: Optional custom system prompt

        Returns:
            Analysis result as string
        """
        if not system_prompt:
            system_prompt = SystemPrompts.BRIEF_ANALYSIS

        messages = [{"role": "user", "content": brief_content}]

        return self.create_message(
            messages=messages, system=system_prompt, temperature=BRIEF_PARSING_TEMPERATURE
        )

    def generate_post_content(
        self,
        template_structure: str,
        context: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = POST_GENERATION_TEMPERATURE,
    ) -> str:
        """
        Generate post content from a template and context

        Args:
            template_structure: Template structure with placeholders
            context: Dictionary of context values for filling template
            system_prompt: Optional custom system prompt
            temperature: Sampling temperature for generation

        Returns:
            Generated post content
        """
        if not system_prompt:
            system_prompt = SystemPrompts.CONTENT_GENERATOR

        # Format context for the prompt with smart filtering
        context_str = self._format_context_optimized(context)

        user_message = f"""Template Structure:
{template_structure}

Client Context:
{context_str}

Generate a post following this template structure, customized for this client's voice and audience."""

        messages = [{"role": "user", "content": user_message}]

        return self.create_message(messages=messages, system=system_prompt, temperature=temperature)

    async def generate_post_content_async(
        self,
        template_structure: str,
        context: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = POST_GENERATION_TEMPERATURE,
    ) -> str:
        """
        Async version of generate_post_content for parallel execution

        Args:
            template_structure: Template structure with placeholders
            context: Dictionary of context values for filling template
            system_prompt: Optional custom system prompt
            temperature: Sampling temperature for generation

        Returns:
            Generated post content
        """
        if not system_prompt:
            system_prompt = SystemPrompts.CONTENT_GENERATOR

        # Format context for the prompt with smart filtering
        context_str = self._format_context_optimized(context)

        user_message = f"""Template Structure:
{template_structure}

Client Context:
{context_str}

Generate a post following this template structure, customized for this client's voice and audience."""

        messages = [{"role": "user", "content": user_message}]

        return await self.create_message_async(
            messages=messages, system=system_prompt, temperature=temperature
        )

    def _format_context_optimized(self, context: Dict[str, Any]) -> str:
        """Format context, excluding empty/redundant fields to reduce token usage

        Args:
            context: Dictionary of context values

        Returns:
            Formatted context string
        """
        lines = []

        # Priority fields (always include if present)
        priority_fields = ["company_name", "ideal_customer", "problem_solved", "brand_voice"]
        for field in priority_fields:
            if field in context and context[field]:
                value = context[field]
                if isinstance(value, str) and value.strip():
                    lines.append(f"{field}: {value}")

        # Optional fields (only if non-empty and relevant)
        for k, v in context.items():
            if k in priority_fields:
                continue

            # Skip empty collections to save tokens
            if isinstance(v, (list, dict)):
                if not v:  # Empty list or dict
                    continue
                # Format lists compactly
                if isinstance(v, list) and all(isinstance(item, str) for item in v):
                    lines.append(f"{k}: {', '.join(v[:5])}")  # Limit to first 5 items
                continue

            # Skip redundant template metadata (already in structure)
            if k in ["template_type", "requires_story", "requires_data"]:
                continue

            # Skip empty strings
            if isinstance(v, str) and not v.strip():
                continue

            lines.append(f"{k}: {v}")

        return "\n".join(lines)

    def _prepare_system_with_caching(
        self, system: str, enable_caching: bool
    ) -> List[Dict[str, Any]]:
        """Prepare system prompt with optional Anthropic prompt caching

        Args:
            system: System prompt text
            enable_caching: Whether to enable prompt caching

        Returns:
            List of system message dictionaries with optional cache_control
        """
        if not enable_caching or not settings.CACHE_SYSTEM_PROMPTS:
            # Return as simple list without caching
            return [{"type": "text", "text": system}]

        # Use Anthropic's prompt caching for ephemeral caching
        return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

    def refine_post(self, original_post: str, feedback: str, context: Dict[str, Any]) -> str:
        """
        Refine a post based on feedback

        Args:
            original_post: Original post content
            feedback: Feedback or revision request
            context: Client context for maintaining voice

        Returns:
            Refined post content
        """
        system_prompt = SystemPrompts.POST_REFINEMENT

        context_str = self._format_context_optimized(context)

        user_message = f"""Original Post:
{original_post}

Feedback:
{feedback}

Client Context:
{context_str}

Revise the post incorporating the feedback while maintaining the brand voice."""

        messages = [{"role": "user", "content": user_message}]

        return self.create_message(messages=messages, system=system_prompt)


# Default client instance (lazy loaded)
default_client = None


def get_default_client() -> AnthropicClient:
    """Get or create default client instance"""
    global default_client
    if default_client is None:
        default_client = AnthropicClient()
    return default_client
