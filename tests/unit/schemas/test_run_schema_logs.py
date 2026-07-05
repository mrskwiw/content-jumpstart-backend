"""
Unit tests for Run schema logs validator - Tests for MyPy fix
"""

from datetime import datetime

import pytest

from backend.schemas.run import LogEntry, RunResponse


class TestLogEntrySchema:
    """Tests for LogEntry schema"""

    def test_log_entry_valid(self):
        """Test creating valid LogEntry"""
        entry = LogEntry(timestamp="2026-02-28T10:00:00", message="Test log")

        assert entry.timestamp == "2026-02-28T10:00:00"
        assert entry.message == "Test log"

    def test_log_entry_with_empty_message(self):
        """Test LogEntry with empty message"""
        entry = LogEntry(timestamp="2026-02-28T10:00:00", message="")

        assert entry.message == ""

    def test_log_entry_with_unicode(self):
        """Test LogEntry with Unicode characters"""
        entry = LogEntry(timestamp="2026-02-28T10:00:00", message="Test émoji 🎉")

        assert "émoji" in entry.message
        assert "🎉" in entry.message


class TestRunResponseLogsValidator:
    """Tests for RunResponse.convert_logs validator"""

    def test_convert_logs_none(self):
        """Test logs validator with None value"""
        run = RunResponse(
            id="run-123",
            project_id="proj-123",
            status="completed",
            is_batch=False,
            started_at=datetime.now(),
            logs=None,
        )

        assert run.logs is None

    def test_convert_logs_empty_list(self):
        """Test logs validator with empty list"""
        run = RunResponse(
            id="run-123",
            project_id="proj-123",
            status="completed",
            is_batch=False,
            started_at=datetime.now(),
            logs=[],
        )

        assert run.logs == []

    def test_convert_logs_plain_strings(self):
        """Test logs validator converts plain strings to LogEntry objects"""
        run = RunResponse(
            id="run-123",
            project_id="proj-123",
            status="completed",
            is_batch=False,
            started_at=datetime.now(),
            logs=["Log message 1", "Log message 2", "Log message 3"],
        )

        assert len(run.logs) == 3
        assert all(isinstance(log, LogEntry) for log in run.logs)
        assert run.logs[0].message == "Log message 1"
        assert run.logs[1].message == "Log message 2"
        assert run.logs[2].message == "Log message 3"

        # Each log should have a timestamp
        assert all(log.timestamp for log in run.logs)

    def test_convert_logs_dict_format(self):
        """Test logs validator converts dict objects to LogEntry"""
        run = RunResponse(
            id="run-123",
            project_id="proj-123",
            status="completed",
            is_batch=False,
            started_at=datetime.now(),
            logs=[
                {"timestamp": "2026-02-28T10:00:00", "message": "Log 1"},
                {"timestamp": "2026-02-28T10:01:00", "message": "Log 2"},
            ],
        )

        assert len(run.logs) == 2
        assert all(isinstance(log, LogEntry) for log in run.logs)
        assert run.logs[0].message == "Log 1"
        assert run.logs[0].timestamp == "2026-02-28T10:00:00"
        assert run.logs[1].message == "Log 2"
        assert run.logs[1].timestamp == "2026-02-28T10:01:00"

    def test_convert_logs_already_log_entries(self):
        """Test logs validator with existing LogEntry objects"""
        existing_logs = [
            LogEntry(timestamp="2026-02-28T10:00:00", message="Log 1"),
            LogEntry(timestamp="2026-02-28T10:01:00", message="Log 2"),
        ]

        run = RunResponse(
            id="run-123",
            project_id="proj-123",
            status="completed",
            is_batch=False,
            started_at=datetime.now(),
            logs=existing_logs,
        )

        assert len(run.logs) == 2
        assert run.logs[0].message == "Log 1"
        assert run.logs[1].message == "Log 2"

    def test_convert_logs_mixed_formats(self):
        """Test logs validator with mixed formats"""
        run = RunResponse(
            id="run-123",
            project_id="proj-123",
            status="completed",
            is_batch=False,
            started_at=datetime.now(),
            logs=[
                "Plain string log",
                {"timestamp": "2026-02-28T10:00:00", "message": "Dict log"},
                LogEntry(timestamp="2026-02-28T10:01:00", message="LogEntry object"),
            ],
        )

        assert len(run.logs) == 3
        assert all(isinstance(log, LogEntry) for log in run.logs)
        assert run.logs[0].message == "Plain string log"
        assert run.logs[1].message == "Dict log"
        assert run.logs[2].message == "LogEntry object"

    def test_convert_logs_unexpected_type_returns_empty_list(self):
        """Test logs validator with unexpected type (MyPy fix test)"""
        # This tests the fix we made for MyPy - returning empty list instead of Any
        run = RunResponse(
            id="run-123",
            project_id="proj-123",
            status="completed",
            is_batch=False,
            started_at=datetime.now(),
            logs=123,  # Invalid type - not a list
        )

        # Should return empty list and log warning (tested behavior from fix)
        assert run.logs == []

    def test_convert_logs_with_unicode_strings(self):
        """Test logs validator with Unicode content"""
        run = RunResponse(
            id="run-123",
            project_id="proj-123",
            status="completed",
            is_batch=False,
            started_at=datetime.now(),
            logs=["Log with émoji 🎉", "Café ☕", "日本語"],
        )

        assert len(run.logs) == 3
        assert "émoji" in run.logs[0].message
        assert "🎉" in run.logs[0].message
        assert "Café" in run.logs[1].message
        assert "日本語" in run.logs[2].message

    def test_convert_logs_preserves_order(self):
        """Test logs validator preserves log order"""
        messages = [f"Log {i}" for i in range(10)]
        run = RunResponse(
            id="run-123",
            project_id="proj-123",
            status="completed",
            is_batch=False,
            started_at=datetime.now(),
            logs=messages,
        )

        for i, log in enumerate(run.logs):
            assert log.message == f"Log {i}"

    def test_convert_logs_with_long_messages(self):
        """Test logs validator with very long log messages"""
        long_message = "X" * 10000  # 10KB message
        run = RunResponse(
            id="run-123",
            project_id="proj-123",
            status="completed",
            is_batch=False,
            started_at=datetime.now(),
            logs=[long_message],
        )

        assert len(run.logs) == 1
        assert len(run.logs[0].message) == 10000

    def test_convert_logs_empty_string(self):
        """Test logs validator with empty string logs"""
        run = RunResponse(
            id="run-123",
            project_id="proj-123",
            status="completed",
            is_batch=False,
            started_at=datetime.now(),
            logs=["", "Non-empty", ""],
        )

        assert len(run.logs) == 3
        assert run.logs[0].message == ""
        assert run.logs[1].message == "Non-empty"
        assert run.logs[2].message == ""


class TestRunResponseCamelCase:
    """Tests for RunResponse camelCase serialization"""

    def test_run_response_model_dump_uses_camel_case(self):
        """Test that RunResponse serializes to camelCase"""
        run = RunResponse(
            id="run-123",
            project_id="proj-123",
            status="completed",
            is_batch=True,
            started_at=datetime(2026, 2, 28, 10, 0, 0),
            completed_at=datetime(2026, 2, 28, 10, 5, 0),
            error_message=None,
            logs=["Log 1", "Log 2"],
        )

        # Use model_dump with by_alias=True to get camelCase
        data = run.model_dump(by_alias=True)

        # Check camelCase field names
        assert "projectId" in data
        assert "isBatch" in data
        assert "startedAt" in data
        assert "completedAt" in data
        assert "errorMessage" in data

        # snake_case should not be present
        assert "project_id" not in data
        assert "is_batch" not in data
        assert "started_at" not in data

    def test_run_response_logs_serialization(self):
        """Test that logs are properly serialized"""
        run = RunResponse(
            id="run-123",
            project_id="proj-123",
            status="completed",
            is_batch=False,
            started_at=datetime.now(),
            logs=["Log 1", "Log 2"],
        )

        data = run.model_dump(by_alias=True)

        assert "logs" in data
        assert len(data["logs"]) == 2
        assert all(isinstance(log, dict) for log in data["logs"])
        assert data["logs"][0]["message"] == "Log 1"
        assert data["logs"][1]["message"] == "Log 2"
