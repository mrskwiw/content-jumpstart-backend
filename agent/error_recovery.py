"""
Error recovery system with exponential backoff and intelligent retry logic
"""

import asyncio
import time
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorSeverity(str, Enum):
    """Error severity levels"""

    FATAL = "fatal"  # Cannot recover, stop workflow
    CRITICAL = "critical"  # Serious but may recover with retry
    WARNING = "warning"  # Non-critical, can continue
    RECOVERABLE = "recoverable"  # Expected errors that can be handled


class ErrorCategory(str, Enum):
    """Categories of errors"""

    API_ERROR = "api_error"  # Anthropic API errors
    NETWORK_ERROR = "network_error"  # Connection issues
    TIMEOUT_ERROR = "timeout_error"  # Operation timeout
    VALIDATION_ERROR = "validation_error"  # Data validation failures
    SYSTEM_ERROR = "system_error"  # System/OS errors
    UNKNOWN_ERROR = "unknown_error"  # Uncategorized


class RecoveryStrategy(str, Enum):
    """Recovery strategies"""

    RETRY = "retry"  # Retry with backoff
    SKIP = "skip"  # Skip and continue
    SUBSTITUTE = "substitute"  # Use alternative approach
    USER_INPUT = "user_input"  # Ask user for guidance
    ABORT = "abort"  # Stop workflow


class ErrorRecord(BaseModel):
    """Record of an error occurrence"""

    error_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)
    attempted_recoveries: List[RecoveryStrategy] = Field(default_factory=list)
    recovered: bool = False


class RetryConfig(BaseModel):
    """Configuration for retry behavior"""

    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd


class ErrorRecoverySystem:
    """Intelligent error recovery with exponential backoff"""

    def __init__(self):
        self.error_history: List[ErrorRecord] = []
        self.error_id_counter = 0

    def categorize_error(self, error: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """Categorize error and assess severity"""
        error_type = type(error).__name__
        error_msg = str(error).lower()

        # API errors
        if "rate" in error_msg and "limit" in error_msg:
            return ErrorCategory.API_ERROR, ErrorSeverity.CRITICAL
        if "api" in error_msg or "anthropic" in error_msg:
            return ErrorCategory.API_ERROR, ErrorSeverity.CRITICAL

        # Network errors
        if any(word in error_msg for word in ["connection", "network", "dns", "unreachable"]):
            return ErrorCategory.NETWORK_ERROR, ErrorSeverity.CRITICAL

        # Timeout errors
        if "timeout" in error_msg or "timed out" in error_msg:
            return ErrorCategory.TIMEOUT_ERROR, ErrorSeverity.CRITICAL

        # Validation errors
        if "validation" in error_msg or error_type in ["ValidationError", "ValueError"]:
            return ErrorCategory.VALIDATION_ERROR, ErrorSeverity.WARNING

        # System errors
        if error_type in ["OSError", "IOError", "PermissionError"]:
            return ErrorCategory.SYSTEM_ERROR, ErrorSeverity.CRITICAL

        return ErrorCategory.UNKNOWN_ERROR, ErrorSeverity.WARNING

    def determine_strategy(
        self, error: Exception, attempt: int, max_retries: int
    ) -> RecoveryStrategy:
        """Determine best recovery strategy for error"""
        category, severity = self.categorize_error(error)

        # Fatal errors - abort immediately
        if severity == ErrorSeverity.FATAL:
            return RecoveryStrategy.ABORT

        # API/Network/Timeout errors - retry with backoff
        if category in [
            ErrorCategory.API_ERROR,
            ErrorCategory.NETWORK_ERROR,
            ErrorCategory.TIMEOUT_ERROR,
        ]:
            if attempt < max_retries:
                return RecoveryStrategy.RETRY
            else:
                return RecoveryStrategy.USER_INPUT  # Ask user after max retries

        # Validation errors - usually can't be fixed by retry
        if category == ErrorCategory.VALIDATION_ERROR:
            return RecoveryStrategy.USER_INPUT

        # System errors - try once, then ask
        if category == ErrorCategory.SYSTEM_ERROR:
            if attempt == 0:
                return RecoveryStrategy.RETRY
            else:
                return RecoveryStrategy.USER_INPUT

        # Unknown errors - try once
        if attempt == 0:
            return RecoveryStrategy.RETRY
        else:
            return RecoveryStrategy.SKIP

    async def execute_with_retry_async(
        self, func: Callable, config: RetryConfig = RetryConfig(), context: Dict[str, Any] = None
    ) -> tuple[bool, Any, Optional[ErrorRecord]]:
        """Execute async function with exponential backoff retry"""
        context = context or {}
        last_error = None

        for attempt in range(config.max_retries + 1):
            try:
                # Execute the function
                if asyncio.iscoroutinefunction(func):
                    result = await func()
                else:
                    result = func()

                # Success - clear error history for this operation
                if last_error:
                    last_error.recovered = True

                return True, result, last_error

            except Exception as e:
                last_error = self._record_error(e, context, attempt)
                strategy = self.determine_strategy(e, attempt, config.max_retries)

                # If we should retry and haven't hit max retries
                if strategy == RecoveryStrategy.RETRY and attempt < config.max_retries:
                    delay = self._calculate_backoff_delay(attempt, config)
                    await asyncio.sleep(delay)
                    continue

                # Otherwise, return failure
                return False, None, last_error

        # Max retries exhausted
        return False, None, last_error

    def execute_with_retry_sync(
        self, func: Callable, config: RetryConfig = RetryConfig(), context: Dict[str, Any] = None
    ) -> tuple[bool, Any, Optional[ErrorRecord]]:
        """Execute sync function with exponential backoff retry"""
        context = context or {}
        last_error = None

        for attempt in range(config.max_retries + 1):
            try:
                result = func()

                if last_error:
                    last_error.recovered = True

                return True, result, last_error

            except Exception as e:
                last_error = self._record_error(e, context, attempt)
                strategy = self.determine_strategy(e, attempt, config.max_retries)

                if strategy == RecoveryStrategy.RETRY and attempt < config.max_retries:
                    delay = self._calculate_backoff_delay(attempt, config)
                    time.sleep(delay)
                    continue

                return False, None, last_error

        return False, None, last_error

    def _record_error(self, error: Exception, context: Dict[str, Any], attempt: int) -> ErrorRecord:
        """Record error occurrence"""
        self.error_id_counter += 1
        category, severity = self.categorize_error(error)

        record = ErrorRecord(
            error_id=f"error_{self.error_id_counter}",
            category=category,
            severity=severity,
            message=str(error),
            context={**context, "attempt": attempt, "traceback": traceback.format_exc()},
        )

        self.error_history.append(record)
        return record

    def _calculate_backoff_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate exponential backoff delay with jitter"""
        delay = config.initial_delay_seconds * (config.exponential_base**attempt)
        delay = min(delay, config.max_delay_seconds)

        if config.jitter:
            import random

            jitter_factor = random.uniform(0.8, 1.2)
            delay *= jitter_factor

        return delay

    def get_error_summary(self, recent_count: int = 10) -> str:
        """Get summary of recent errors"""
        recent_errors = self.error_history[-recent_count:]

        if not recent_errors:
            return "✅ No recent errors"

        summary = f"**Recent Errors ({len(recent_errors)}):**\n\n"

        for error in recent_errors:
            emoji = "❌" if not error.recovered else "✅"
            summary += f"{emoji} **{error.category.value}** ({error.severity.value})\n"
            summary += f"   {error.message}\n"
            if error.context.get("attempt"):
                summary += f"   Attempt: {error.context['attempt']}\n"
            summary += f"   Time: {error.timestamp.strftime('%H:%M:%S')}\n\n"

        return summary

    def format_recovery_prompt(self, error_record: ErrorRecord) -> str:
        """Format a user prompt for recovery guidance"""
        category, severity = error_record.category, error_record.severity

        prompt = "⚠️ **Error Occurred**\n\n"
        prompt += f"**Type:** {category.value.replace('_', ' ').title()}\n"
        prompt += f"**Severity:** {severity.value.title()}\n"
        prompt += f"**Message:** {error_record.message}\n\n"

        prompt += "**What should I do?**\n"
        prompt += "1. Retry with exponential backoff\n"
        prompt += "2. Skip this step and continue\n"
        prompt += "3. Try alternative approach\n"
        prompt += "4. Pause and investigate\n\n"

        prompt += "Please select an option (1-4):"

        return prompt


# Global instance
error_recovery = ErrorRecoverySystem()
