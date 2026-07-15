"""
Server-Sent Events (SSE) utilities for streaming responses.

Provides async generator support for real-time progress updates during
long-running operations like content generation and research execution.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Any, Dict
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


class SSEMessage:
    """Server-Sent Event message formatter"""

    @staticmethod
    def format(data: Dict[str, Any], event: str = "message") -> str:
        """
        Format data as an SSE message.

        Args:
            data: Dictionary to send as JSON
            event: Event type name

        Returns:
            Formatted SSE message string
        """
        msg = f"event: {event}\n"
        msg += f"data: {json.dumps(data)}\n\n"
        return msg

    @staticmethod
    def ping() -> str:
        """Create a ping message to keep connection alive"""
        return ": ping\n\n"


async def create_sse_response(
    generator: AsyncGenerator[Dict[str, Any], None],
    event_type: str = "message",
) -> StreamingResponse:
    """
    Create a StreamingResponse for Server-Sent Events.

    Args:
        generator: Async generator yielding data dictionaries
        event_type: Default event type for messages

    Returns:
        StreamingResponse configured for SSE
    """

    async def event_generator():
        """Wrap the data generator with SSE formatting"""
        try:
            async for data in generator:
                yield SSEMessage.format(data, event=event_type)
                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            # Client disconnected
            pass
        except Exception:
            # Log the detail server-side; send the client a generic error rather
            # than the raw exception text (py/stack-trace-exposure).
            logger.exception("SSE stream error")
            yield SSEMessage.format(
                {"error": "An internal error occurred", "type": "error"}, event="error"
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
