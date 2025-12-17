"""Unit tests for cost tracking system"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.utils.cost_tracker import APICall, CostTracker


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = Path(f.name)

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def tracker(temp_db):
    """Create cost tracker with temporary database"""
    return CostTracker(db_path=temp_db)


def test_tracker_initialization(tracker):
    """Test tracker initializes database correctly"""
    assert tracker.db_path.exists()

    # Check tables exist
    conn = sqlite3.connect(tracker.db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    assert "api_calls" in tables
    assert "budget_alerts" in tables

    conn.close()


def test_calculate_cost(tracker):
    """Test cost calculation for different models"""
    model = "claude-3-5-sonnet-20241022"

    # Test basic input/output cost
    cost = tracker.calculate_cost(model=model, input_tokens=1000, output_tokens=500)

    expected_cost = (1000 / 1_000_000 * 0.003) + (500 / 1_000_000 * 0.015)
    assert cost == pytest.approx(expected_cost, rel=1e-6)


def test_calculate_cost_with_cache(tracker):
    """Test cost calculation with cache tokens"""
    model = "claude-3-5-sonnet-20241022"

    cost = tracker.calculate_cost(
        model=model,
        input_tokens=1000,
        output_tokens=500,
        cache_creation_tokens=2000,
        cache_read_tokens=5000,
    )

    expected_cost = (
        (1000 / 1_000_000 * 0.003)
        + (500 / 1_000_000 * 0.015)  # Input
        + (2000 / 1_000_000 * 0.00375)  # Output
        + (5000 / 1_000_000 * 0.0003)  # Cache write  # Cache read
    )

    assert cost == pytest.approx(expected_cost, rel=1e-6)


def test_track_api_call(tracker):
    """Test tracking an API call"""
    project_id = "TestProject_20250101_120000"

    cost = tracker.track_api_call(
        project_id=project_id,
        operation="test_generation",
        model="claude-3-5-sonnet-20241022",
        input_tokens=1000,
        output_tokens=500,
    )

    assert cost > 0

    # Verify stored in database
    project_cost = tracker.get_project_cost(project_id)
    assert project_cost.total_calls == 1
    assert project_cost.total_input_tokens == 1000
    assert project_cost.total_output_tokens == 500
    assert project_cost.total_cost == pytest.approx(cost, rel=1e-6)


def test_get_project_cost(tracker):
    """Test getting project cost summary"""
    project_id = "TestProject_20250101_120000"

    # Track multiple calls
    tracker.track_api_call(
        project_id=project_id,
        operation="call1",
        model="claude-3-5-sonnet-20241022",
        input_tokens=1000,
        output_tokens=500,
    )

    tracker.track_api_call(
        project_id=project_id,
        operation="call2",
        model="claude-3-5-sonnet-20241022",
        input_tokens=2000,
        output_tokens=1000,
    )

    project_cost = tracker.get_project_cost(project_id)

    assert project_cost.total_calls == 2
    assert project_cost.total_input_tokens == 3000
    assert project_cost.total_output_tokens == 1500
    assert project_cost.total_cost > 0


def test_get_project_cost_nonexistent(tracker):
    """Test getting cost for nonexistent project"""
    project_cost = tracker.get_project_cost("NonexistentProject")

    assert project_cost.total_calls == 0
    assert project_cost.total_cost == 0.0


def test_get_project_calls(tracker):
    """Test getting individual API calls"""
    project_id = "TestProject_20250101_120000"

    tracker.track_api_call(
        project_id=project_id,
        operation="call1",
        model="claude-3-5-sonnet-20241022",
        input_tokens=1000,
        output_tokens=500,
    )

    tracker.track_api_call(
        project_id=project_id,
        operation="call2",
        model="claude-3-5-sonnet-20241022",
        input_tokens=2000,
        output_tokens=1000,
    )

    calls = tracker.get_project_calls(project_id)

    assert len(calls) == 2
    assert all(isinstance(call, APICall) for call in calls)

    # Should be ordered by timestamp DESC (most recent first)
    assert calls[0].operation == "call2"
    assert calls[1].operation == "call1"


def test_get_all_projects(tracker):
    """Test getting list of all projects"""
    # Track calls for multiple projects
    tracker.track_api_call(
        project_id="Project1",
        operation="call1",
        model="claude-3-5-sonnet-20241022",
        input_tokens=1000,
        output_tokens=500,
    )

    tracker.track_api_call(
        project_id="Project2",
        operation="call2",
        model="claude-3-5-sonnet-20241022",
        input_tokens=1000,
        output_tokens=500,
    )

    projects = tracker.get_all_projects()

    assert len(projects) == 2
    assert "Project1" in projects
    assert "Project2" in projects


def test_get_total_costs(tracker):
    """Test getting total costs across all projects"""
    # Track calls for multiple projects
    tracker.track_api_call(
        project_id="Project1",
        operation="call",
        model="claude-3-5-sonnet-20241022",
        input_tokens=1000,
        output_tokens=500,
    )

    tracker.track_api_call(
        project_id="Project2",
        operation="call",
        model="claude-3-5-sonnet-20241022",
        input_tokens=2000,
        output_tokens=1000,
    )

    totals = tracker.get_total_costs()

    assert totals["total_projects"] == 2
    assert totals["total_calls"] == 2
    assert totals["total_input_tokens"] == 3000
    assert totals["total_output_tokens"] == 1500
    assert totals["total_cost"] > 0
    assert totals["avg_cost_per_project"] > 0


def test_set_budget_alert(tracker):
    """Test setting budget alert"""
    project_id = "TestProject"

    tracker.set_budget_alert(project_id=project_id, budget_limit=5.0, alert_threshold=0.8)

    # Verify stored in database
    conn = sqlite3.connect(tracker.db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT budget_limit, alert_threshold FROM budget_alerts WHERE project_id = ?",
        (project_id,),
    )
    row = cursor.fetchone()

    assert row is not None
    assert row[0] == 5.0
    assert row[1] == 0.8

    conn.close()


def test_budget_alert_warning(tracker, caplog):
    """Test budget alert triggers warning"""
    import logging

    project_id = "TestProject"

    # Set budget alert
    tracker.set_budget_alert(
        project_id=project_id, budget_limit=0.01, alert_threshold=0.5  # Very low limit
    )

    # Track API call that exceeds threshold
    with caplog.at_level(logging.WARNING):
        tracker.track_api_call(
            project_id=project_id,
            operation="call",
            model="claude-3-5-sonnet-20241022",
            input_tokens=5000,
            output_tokens=2500,
        )

    # Check warning was logged
    assert any("BUDGET ALERT" in record.message for record in caplog.records)


def test_export_to_json(tracker, temp_db):
    """Test exporting cost data to JSON"""
    import json

    project_id = "TestProject"

    tracker.track_api_call(
        project_id=project_id,
        operation="call",
        model="claude-3-5-sonnet-20241022",
        input_tokens=1000,
        output_tokens=500,
    )

    # Export to JSON
    output_path = temp_db.parent / "export.json"
    tracker.export_to_json(output_path, project_id=project_id)

    # Verify JSON file
    assert output_path.exists()

    with open(output_path) as f:
        data = json.load(f)

    assert data["project_id"] == project_id
    assert "summary" in data
    assert "calls" in data
    assert len(data["calls"]) == 1

    # Cleanup
    output_path.unlink()


def test_unknown_model_uses_default(tracker):
    """Test unknown model falls back to Sonnet pricing"""
    cost = tracker.calculate_cost(model="unknown-model", input_tokens=1000, output_tokens=500)

    # Should use Sonnet pricing
    expected_cost = (1000 / 1_000_000 * 0.003) + (500 / 1_000_000 * 0.015)
    assert cost == pytest.approx(expected_cost, rel=1e-6)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
