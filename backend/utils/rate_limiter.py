"""
Rate limiting tracker to stay at 70% of Anthropic API limits.

Anthropic Limits (Claude 3.5 Sonnet):
- 4,000 requests per minute
- 400,000 tokens per minute

Our Target (70%):
- 2,800 requests per minute
- 280,000 tokens per minute
"""
import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from backend.config import settings


@dataclass
class QueuedRequest:
    """Represents a request in the queue"""

    id: str
    estimated_tokens: int
    timestamp: datetime
    priority: int = 0  # Higher priority = processed first


class RateLimitTracker:
    """
    In-memory rate limit tracker for Anthropic API calls.

    Keeps track of:
    - Requests per minute
    - Tokens per minute
    - Queue for requests when at capacity
    """

    def __init__(self):
        # Sliding window tracking (last 60 seconds)
        self.requests_log: deque = deque()  # [(timestamp, tokens_used), ...]
        self.request_limit = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        self.token_limit = settings.RATE_LIMIT_TOKENS_PER_MINUTE

        # Queue for pending requests
        self.queue: List[QueuedRequest] = []
        self._lock = asyncio.Lock()

    def _cleanup_old_entries(self):
        """Remove entries older than 1 minute"""
        cutoff_time = datetime.now() - timedelta(minutes=1)
        while self.requests_log and self.requests_log[0][0] < cutoff_time:
            self.requests_log.popleft()

    def _get_current_usage(self) -> Dict[str, int]:
        """Get current requests and tokens in the last minute"""
        self._cleanup_old_entries()
        requests_count = len(self.requests_log)
        tokens_count = sum(tokens for _, tokens in self.requests_log)
        return {
            "requests": requests_count,
            "tokens": tokens_count,
            "requests_limit": self.request_limit,
            "tokens_limit": self.token_limit,
            "requests_available": max(0, self.request_limit - requests_count),
            "tokens_available": max(0, self.token_limit - tokens_count),
        }

    async def can_make_request(self, estimated_tokens: int) -> bool:
        """
        Check if request can be made without exceeding limits.

        Args:
            estimated_tokens: Estimated tokens for this request

        Returns:
            True if request can be made, False otherwise
        """
        async with self._lock:
            usage = self._get_current_usage()

            # Check if adding this request would exceed limits
            if usage["requests"] >= self.request_limit:
                return False
            if usage["tokens"] + estimated_tokens >= self.token_limit:
                return False

            return True

    async def record_request(self, tokens_used: int):
        """
        Record a completed request.

        Args:
            tokens_used: Actual tokens used by the request
        """
        async with self._lock:
            timestamp = datetime.now()
            self.requests_log.append((timestamp, tokens_used))

    async def add_to_queue(self, request_id: str, estimated_tokens: int, priority: int = 0):
        """
        Add request to queue when at capacity.

        Args:
            request_id: Unique identifier for the request
            estimated_tokens: Estimated tokens for this request
            priority: Higher priority = processed first (default: 0)
        """
        async with self._lock:
            queued_request = QueuedRequest(
                id=request_id,
                estimated_tokens=estimated_tokens,
                timestamp=datetime.now(),
                priority=priority,
            )
            self.queue.append(queued_request)
            # Sort by priority (descending) then timestamp (ascending)
            self.queue.sort(key=lambda r: (-r.priority, r.timestamp))

    async def remove_from_queue(self, request_id: str):
        """Remove request from queue"""
        async with self._lock:
            self.queue = [r for r in self.queue if r.id != request_id]

    async def get_queue_position(self, request_id: str) -> int:
        """
        Get position in queue (0-indexed).

        Returns:
            Queue position, or -1 if not in queue
        """
        async with self._lock:
            for i, request in enumerate(self.queue):
                if request.id == request_id:
                    return i
            return -1

    async def get_estimated_wait_time(self, request_id: str) -> Optional[int]:
        """
        Estimate wait time in seconds for a queued request.

        Args:
            request_id: Request ID to check

        Returns:
            Estimated wait time in seconds, or None if not in queue
        """
        position = await self.get_queue_position(request_id)
        if position == -1:
            return None

        self._get_current_usage()

        # Estimate based on how fast the rate limit window is moving
        # Assume requests clear at a steady rate
        requests_per_second = self.request_limit / 60  # Convert to per-second

        # Calculate wait time based on queue position
        estimated_seconds = position / requests_per_second

        return int(estimated_seconds)

    def get_usage_stats(self) -> Dict[str, any]:
        """Get current usage statistics"""
        usage = self._get_current_usage()
        return {
            **usage,
            "queue_length": len(self.queue),
            "requests_utilization": round(usage["requests"] / self.request_limit * 100, 1),
            "tokens_utilization": round(usage["tokens"] / self.token_limit * 100, 1),
        }


# Global rate limiter instance
rate_limiter = RateLimitTracker()
