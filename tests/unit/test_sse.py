"""Unit tests for backend.utils.sse (Server-Sent Events utilities)."""

import json
import pytest

from backend.utils.sse import SSEMessage, create_sse_response


class TestSSEMessage:
    def test_format_basic(self):
        msg = SSEMessage.format({"status": "ok"})
        assert msg.startswith("event: message\n")
        assert '"status": "ok"' in msg
        assert msg.endswith("\n\n")

    def test_format_custom_event(self):
        msg = SSEMessage.format({"status": "done"}, event="progress")
        assert "event: progress\n" in msg

    def test_format_data_is_valid_json(self):
        data = {"id": "123", "value": 42, "list": [1, 2, 3]}
        msg = SSEMessage.format(data)
        # Extract JSON from the data: line
        data_line = [line for line in msg.split("\n") if line.startswith("data:")][0]
        parsed = json.loads(data_line[len("data: ") :])
        assert parsed == data

    def test_ping_format(self):
        ping = SSEMessage.ping()
        assert ping == ": ping\n\n"

    def test_format_empty_data(self):
        msg = SSEMessage.format({})
        assert "data: {}" in msg


class TestCreateSSEResponse:
    @pytest.mark.asyncio
    async def test_returns_streaming_response(self):
        from fastapi.responses import StreamingResponse

        async def gen():
            yield {"step": 1}
            yield {"step": 2}

        resp = await create_sse_response(gen())
        assert isinstance(resp, StreamingResponse)

    @pytest.mark.asyncio
    async def test_correct_media_type(self):
        async def gen():
            yield {"x": 1}

        resp = await create_sse_response(gen())
        assert resp.media_type == "text/event-stream"

    @pytest.mark.asyncio
    async def test_cache_control_header(self):
        async def gen():
            yield {}

        resp = await create_sse_response(gen())
        assert resp.headers.get("Cache-Control") == "no-cache"

    @pytest.mark.asyncio
    async def test_event_generator_streams_messages(self):
        events = []

        async def gen():
            for i in range(3):
                yield {"n": i}

        resp = await create_sse_response(gen())
        # Collect all chunks from the streaming body
        async for chunk in resp.body_iterator:
            events.append(chunk)

        combined = "".join(e if isinstance(e, str) else e.decode() for e in events)
        assert '"n": 0' in combined
        assert '"n": 2' in combined

    @pytest.mark.asyncio
    async def test_error_in_generator_sends_error_event(self):
        async def bad_gen():
            yield {"ok": True}
            raise RuntimeError("generator blew up")

        resp = await create_sse_response(bad_gen())
        chunks = []
        async for chunk in resp.body_iterator:
            chunks.append(chunk if isinstance(chunk, str) else chunk.decode())

        combined = "".join(chunks)
        assert "error" in combined
        # Security (py/stack-trace-exposure): the raw exception text must NOT be
        # sent to the client — only a generic message.
        assert "generator blew up" not in combined
        assert "An internal error occurred" in combined
