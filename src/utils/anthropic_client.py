"""Wrapper for Anthropic API calls with error handling and retry logic.

Provides comprehensive error detection, diagnostics, and reporting for
connection issues with the Anthropic API.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
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
from .connection_diagnostics import (
    ConnectionDiagnostics,
    check_anthropic_connectivity,
    diagnose_connection_error,
)
from .cost_tracker import get_default_tracker
from .logger import log_api_call, log_error, logger
from .response_cache import ResponseCache


@dataclass
class APIErrorReport:
    """Structured error report for API failures."""

    timestamp: datetime = field(default_factory=datetime.now)
    operation: str = ""
    model: str = ""
    attempt: int = 1
    max_attempts: int = 3
    error_type: str = ""
    error_message: str = ""
    diagnostics: Optional[ConnectionDiagnostics] = None
    recovery_action: str = ""

    def to_log_message(self) -> str:
        """Generate log message for this error."""
        lines = [
            f"API Error Report [{self.timestamp.strftime('%H:%M:%S')}]",
            f"  Operation: {self.operation}",
            f"  Model: {self.model}",
            f"  Attempt: {self.attempt}/{self.max_attempts}",
            f"  Error Type: {self.error_type}",
            f"  Message: {self.error_message[:200]}",
        ]
        if self.recovery_action:
            lines.append(f"  Recovery: {self.recovery_action}")
        return "\n".join(lines)


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

        # Error tracking for diagnostics
        self.error_history: List[APIErrorReport] = []
        self.consecutive_failures: int = 0
        self.last_successful_call: Optional[datetime] = None
        self.connection_verified: bool = False

    def check_connection_health(self) -> ConnectionDiagnostics:
        """Check connectivity to Anthropic API.

        Runs comprehensive diagnostics including DNS resolution,
        port connectivity, and SSL certificate validation.

        Returns:
            ConnectionDiagnostics with current health status.
        """
        logger.info("Running Anthropic API connection health check...")
        diagnostics = check_anthropic_connectivity()

        # Log results
        if diagnostics.dns_resolved and diagnostics.port_open and diagnostics.ssl_valid:
            logger.info(
                f"Connection health check PASSED - "
                f"DNS: {diagnostics.dns_resolution_time_ms:.1f}ms, "
                f"Connection: {diagnostics.connection_time_ms:.1f}ms, "
                f"SSL: {diagnostics.ssl_handshake_time_ms:.1f}ms"
            )
            self.connection_verified = True
        else:
            logger.warning(
                f"Connection health check FAILED - "
                f"DNS: {'OK' if diagnostics.dns_resolved else 'FAILED'}, "
                f"Port: {'OK' if diagnostics.port_open else 'FAILED'}, "
                f"SSL: {'OK' if diagnostics.ssl_valid else 'FAILED'}"
            )
            # Log detailed report
            logger.warning(diagnostics.to_report())
            self.connection_verified = False

        return diagnostics

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent API errors.

        Returns:
            Dictionary with error statistics and recent failures.
        """
        if not self.error_history:
            return {
                "total_errors": 0,
                "consecutive_failures": self.consecutive_failures,
                "last_successful_call": (
                    self.last_successful_call.isoformat() if self.last_successful_call else None
                ),
                "connection_verified": self.connection_verified,
                "error_types": {},
                "recent_errors": [],
            }

        # Count error types
        error_types: Dict[str, int] = {}
        for error in self.error_history:
            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1

        # Get last 5 errors
        recent = self.error_history[-5:]

        return {
            "total_errors": len(self.error_history),
            "consecutive_failures": self.consecutive_failures,
            "last_successful_call": (
                self.last_successful_call.isoformat() if self.last_successful_call else None
            ),
            "connection_verified": self.connection_verified,
            "error_types": error_types,
            "recent_errors": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "operation": e.operation,
                    "error_type": e.error_type,
                    "message": e.error_message[:100],
                }
                for e in recent
            ],
        }

    def _record_error(
        self,
        exception: Exception,
        operation: str,
        attempt: int,
        max_attempts: int,
        run_diagnostics: bool = True,
    ) -> APIErrorReport:
        """Record an API error with diagnostics.

        Args:
            exception: The exception that occurred.
            operation: Name of the operation that failed.
            attempt: Current attempt number.
            max_attempts: Maximum retry attempts.
            run_diagnostics: Whether to run full connection diagnostics.

        Returns:
            APIErrorReport with error details.
        """
        # Determine error type and recovery action
        error_type = type(exception).__name__
        recovery_action = ""

        if isinstance(exception, RateLimitError):
            error_type = "RateLimitError"
            recovery_action = "Waiting with exponential backoff"
        elif isinstance(exception, APIConnectionError):
            error_type = "APIConnectionError"
            recovery_action = "Retrying connection"
        elif isinstance(exception, APIError):
            error_type = f"APIError ({getattr(exception, 'status_code', 'unknown')})"
            recovery_action = "No retry - non-retryable error"

        # Run diagnostics for connection errors
        diagnostics = None
        if run_diagnostics and isinstance(exception, APIConnectionError):
            wait_time = self.retry_delay * (2 ** (attempt - 1))
            diagnostics = diagnose_connection_error(
                exception=exception,
                endpoint="https://api.anthropic.com",
                attempt=attempt,
                max_attempts=max_attempts,
                retry_delay=wait_time,
            )
            # Log detailed diagnostic report
            logger.error(diagnostics.to_report())

        report = APIErrorReport(
            operation=operation,
            model=self.model,
            attempt=attempt,
            max_attempts=max_attempts,
            error_type=error_type,
            error_message=str(exception),
            diagnostics=diagnostics,
            recovery_action=recovery_action,
        )

        # Track error
        self.error_history.append(report)
        self.consecutive_failures += 1

        # Keep only last 50 errors
        if len(self.error_history) > 50:
            self.error_history = self.error_history[-50:]

        # Log structured error
        logger.error(report.to_log_message())

        return report

    def _record_success(self) -> None:
        """Record a successful API call."""
        self.consecutive_failures = 0
        self.last_successful_call = datetime.now()

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

        last_exception: Optional[Exception] = None

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
                    response_text: str = response.content[0].text

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

                    # Record success
                    self._record_success()

                    return response_text
                else:
                    raise RuntimeError("Empty response from API")

            except RateLimitError as e:
                last_exception = e
                wait_time = self.retry_delay * (2**attempt)  # Exponential backoff

                # Record error with context (no full diagnostics for rate limits)
                self._record_error(
                    exception=e,
                    operation=operation,
                    attempt=attempt + 1,
                    max_attempts=self.max_retries,
                    run_diagnostics=False,  # Rate limits aren't connection issues
                )

                logger.warning(
                    f"Rate limit hit (attempt {attempt + 1}/{self.max_retries}), "
                    f"waiting {wait_time}s before retry. "
                    f"Consecutive failures: {self.consecutive_failures}"
                )
                time.sleep(wait_time)

            except APIConnectionError as e:
                last_exception = e
                wait_time = self.retry_delay * (2**attempt)

                # Record error with full connection diagnostics
                error_report = self._record_error(
                    exception=e,
                    operation=operation,
                    attempt=attempt + 1,
                    max_attempts=self.max_retries,
                    run_diagnostics=True,  # Run full diagnostics for connection errors
                )

                # Log additional context
                logger.warning(
                    f"Connection error (attempt {attempt + 1}/{self.max_retries}), "
                    f"waiting {wait_time}s before retry. "
                    f"Error type: {error_report.diagnostics.error_type.value if error_report.diagnostics else 'unknown'}"
                )

                # Log suggestions if available
                if error_report.diagnostics and error_report.diagnostics.suggestions:
                    logger.info("Troubleshooting suggestions:")
                    for suggestion in error_report.diagnostics.suggestions[:3]:
                        logger.info(f"  - {suggestion}")

                time.sleep(wait_time)

            except APIError as e:
                last_exception = e

                # Record error (no diagnostics for API errors)
                self._record_error(
                    exception=e,
                    operation=operation,
                    attempt=attempt + 1,
                    max_attempts=self.max_retries,
                    run_diagnostics=False,
                )

                # Don't retry on non-retryable errors
                log_error(f"API error: {str(e)}", exc_info=True)
                raise

        # If we get here, all retries failed - generate final diagnostic report
        log_error(f"All {self.max_retries} retries failed", exc_info=True)

        # Run final diagnostics
        if isinstance(last_exception, APIConnectionError):
            logger.error("=" * 60)
            logger.error("FINAL CONNECTION FAILURE - DETAILED DIAGNOSTICS")
            logger.error("=" * 60)
            final_diagnostics = diagnose_connection_error(
                exception=last_exception,
                endpoint="https://api.anthropic.com",
                attempt=self.max_retries,
                max_attempts=self.max_retries,
                retry_delay=0,
            )
            logger.error(final_diagnostics.to_report())
            logger.error("=" * 60)

        if last_exception is not None:
            raise last_exception
        else:
            raise RuntimeError(f"All {self.max_retries} retries failed")

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

        last_exception: Optional[Exception] = None

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
                    response_text: str = response.content[0].text

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

                    # Record success
                    self._record_success()

                    return response_text
                else:
                    raise RuntimeError("Empty response from API")

            except RateLimitError as e:
                last_exception = e
                wait_time = self.retry_delay * (2**attempt)  # Exponential backoff

                # Record error with context (no full diagnostics for rate limits)
                self._record_error(
                    exception=e,
                    operation=operation,
                    attempt=attempt + 1,
                    max_attempts=self.max_retries,
                    run_diagnostics=False,
                )

                logger.warning(
                    f"Rate limit hit (attempt {attempt + 1}/{self.max_retries}), "
                    f"waiting {wait_time}s before retry. "
                    f"Consecutive failures: {self.consecutive_failures}"
                )
                await asyncio.sleep(wait_time)

            except APIConnectionError as e:
                last_exception = e
                wait_time = self.retry_delay * (2**attempt)

                # Record error with full connection diagnostics
                error_report = self._record_error(
                    exception=e,
                    operation=operation,
                    attempt=attempt + 1,
                    max_attempts=self.max_retries,
                    run_diagnostics=True,
                )

                # Log additional context
                logger.warning(
                    f"Connection error (attempt {attempt + 1}/{self.max_retries}), "
                    f"waiting {wait_time}s before retry. "
                    f"Error type: {error_report.diagnostics.error_type.value if error_report.diagnostics else 'unknown'}"
                )

                # Log suggestions if available
                if error_report.diagnostics and error_report.diagnostics.suggestions:
                    logger.info("Troubleshooting suggestions:")
                    for suggestion in error_report.diagnostics.suggestions[:3]:
                        logger.info(f"  - {suggestion}")

                await asyncio.sleep(wait_time)

            except APIError as e:
                last_exception = e

                # Record error (no diagnostics for API errors)
                self._record_error(
                    exception=e,
                    operation=operation,
                    attempt=attempt + 1,
                    max_attempts=self.max_retries,
                    run_diagnostics=False,
                )

                # Don't retry on non-retryable errors
                log_error(f"API error: {str(e)}", exc_info=True)
                raise

        # If we get here, all retries failed - generate final diagnostic report
        log_error(f"All {self.max_retries} retries failed", exc_info=True)

        # Run final diagnostics
        if isinstance(last_exception, APIConnectionError):
            logger.error("=" * 60)
            logger.error("FINAL CONNECTION FAILURE - DETAILED DIAGNOSTICS")
            logger.error("=" * 60)
            final_diagnostics = diagnose_connection_error(
                exception=last_exception,
                endpoint="https://api.anthropic.com",
                attempt=self.max_retries,
                max_attempts=self.max_retries,
                retry_delay=0,
            )
            logger.error(final_diagnostics.to_report())
            logger.error("=" * 60)

        if last_exception is not None:
            raise last_exception
        else:
            raise RuntimeError(f"All {self.max_retries} retries failed")

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
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate post content from a template and context

        Args:
            template_structure: Template structure with placeholders
            context: Dictionary of context values for filling template
            system_prompt: Optional custom system prompt
            temperature: Sampling temperature for generation
            max_tokens: Token budget for output (defaults to settings.MAX_TOKENS).
                        Pass a higher value for long-form content like blog posts.

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

        return self.create_message(
            messages=messages, system=system_prompt, temperature=temperature, max_tokens=max_tokens
        )

    async def generate_post_content_async(
        self,
        template_structure: str,
        context: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = POST_GENERATION_TEMPERATURE,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Async version of generate_post_content for parallel execution

        Args:
            template_structure: Template structure with placeholders
            context: Dictionary of context values for filling template
            system_prompt: Optional custom system prompt
            temperature: Sampling temperature for generation
            max_tokens: Token budget for output (defaults to settings.MAX_TOKENS).
                        Pass a higher value for long-form content like blog posts.

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
            messages=messages, system=system_prompt, temperature=temperature, max_tokens=max_tokens
        )

    def _format_context_optimized(self, context: Dict[str, Any]) -> str:
        """Format context, excluding empty/redundant fields to reduce token usage

        Args:
            context: Dictionary of context values

        Returns:
            Formatted context string
        """
        lines = []

        # company_name is always emitted — even if empty — so that two clients
        # with otherwise identical sparse context produce different cache keys
        # and cannot collide in the response cache.
        raw_company = context.get("company_name", "") or ""
        lines.append(f"company_name: {raw_company.strip() or '[not provided]'}")

        # Remaining priority fields (always include if present and non-empty)
        priority_fields = [
            "company_name",  # already handled above — kept here so the skip logic works
            "ideal_customer",
            "problem_solved",
            "brand_voice",
            "research_insights",
            "web_search_results",
        ]
        for field_name in priority_fields:
            if field_name == "company_name":
                continue  # emitted unconditionally above
            if field_name in context and context[field_name]:
                value = context[field_name]
                if isinstance(value, str) and value.strip():
                    # Research insights and web search results formatted as standalone blocks
                    if field_name in ("research_insights", "web_search_results"):
                        lines.append("")  # Blank line before
                        lines.append(value)  # Already formatted by context builder
                        lines.append("")  # Blank line after
                    else:
                        lines.append(f"{field_name}: {value}")

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
