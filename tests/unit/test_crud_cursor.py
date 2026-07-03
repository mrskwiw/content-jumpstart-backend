"""Unit tests for cursor pagination helpers in backend.services.crud."""

import base64
import json
import pytest
from datetime import datetime

from backend.services.crud import encode_cursor, decode_cursor


class TestEncodeCursor:
    def test_returns_string(self):
        ts = datetime(2025, 1, 15, 10, 30, 0)
        result = encode_cursor(ts, "proj-abc")
        assert isinstance(result, str)

    def test_is_base64_decodable(self):
        ts = datetime(2025, 1, 15, 10, 30, 0)
        cursor = encode_cursor(ts, "proj-abc")
        # Should decode without error
        decoded = base64.b64decode(cursor.encode("utf-8"))
        data = json.loads(decoded.decode("utf-8"))
        assert "created_at" in data
        assert "id" in data

    def test_encodes_id(self):
        ts = datetime(2025, 1, 15)
        cursor = encode_cursor(ts, "my-custom-id")
        _, decoded_id = decode_cursor(cursor)
        assert decoded_id == "my-custom-id"

    def test_different_timestamps_produce_different_cursors(self):
        ts1 = datetime(2025, 1, 1)
        ts2 = datetime(2025, 1, 2)
        c1 = encode_cursor(ts1, "same-id")
        c2 = encode_cursor(ts2, "same-id")
        assert c1 != c2

    def test_different_ids_produce_different_cursors(self):
        ts = datetime(2025, 1, 1)
        c1 = encode_cursor(ts, "id-1")
        c2 = encode_cursor(ts, "id-2")
        assert c1 != c2


class TestDecodeCursor:
    def test_decodes_timestamp(self):
        ts = datetime(2025, 6, 15, 12, 0, 0)
        cursor = encode_cursor(ts, "test-id")
        decoded_ts, _ = decode_cursor(cursor)
        assert decoded_ts == ts

    def test_decodes_id(self):
        ts = datetime(2025, 1, 1)
        cursor = encode_cursor(ts, "proj-12345")
        _, decoded_id = decode_cursor(cursor)
        assert decoded_id == "proj-12345"

    def test_roundtrip_is_lossless(self):
        ts = datetime(2025, 3, 25, 14, 30, 59)
        original_id = "client-xyz-789"
        cursor = encode_cursor(ts, original_id)
        decoded_ts, decoded_id = decode_cursor(cursor)
        assert decoded_ts == ts
        assert decoded_id == original_id

    def test_microseconds_preserved(self):
        ts = datetime(2025, 1, 1, 0, 0, 0, 123456)
        cursor = encode_cursor(ts, "id")
        decoded_ts, _ = decode_cursor(cursor)
        assert decoded_ts == ts
