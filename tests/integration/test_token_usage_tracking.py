"""Test token usage tracking in Run model (Task #32)"""

import pytest
from unittest.mock import Mock, patch
from backend.models import Run
from backend.services import crud
from src.utils.cost_tracker import CostTracker, ProjectCost
from datetime import datetime


@pytest.fixture
def mock_project_cost():
    """Mock ProjectCost from CostTracker"""
    return ProjectCost(
        project_id="test_project_123",
        total_calls=5,
        total_input_tokens=45234,
        total_output_tokens=67890,
        total_cache_creation_tokens=5000,
        total_cache_read_tokens=2000,
        total_cost=1.23,
        first_call=datetime.now(),
        last_call=datetime.now(),
    )


def test_run_model_has_token_fields(db_session):
    """Test that Run model has all token usage fields"""
    # Create a run with token fields
    run = Run(
        id="test_run_123",
        project_id="test_project_123",
        is_batch=True,
        status="succeeded",
        total_input_tokens=45234,
        total_output_tokens=67890,
        total_cache_creation_tokens=5000,
        total_cache_read_tokens=2000,
        total_cost_usd=1.23,
    )

    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    # Verify all fields are stored correctly
    assert run.total_input_tokens == 45234
    assert run.total_output_tokens == 67890
    assert run.total_cache_creation_tokens == 5000
    assert run.total_cache_read_tokens == 2000
    assert run.total_cost_usd == 1.23


def test_crud_update_run_with_token_usage(db_session, test_project):
    """Test that crud.update_run accepts and stores token usage"""
    # Create a run
    run = crud.create_run(db_session, test_project.id, is_batch=True)

    # Update with token usage
    updated_run = crud.update_run(
        db_session,
        run.id,
        status="succeeded",
        total_input_tokens=12345,
        total_output_tokens=67890,
        total_cache_creation_tokens=1000,
        total_cache_read_tokens=500,
        total_cost_usd=0.85,
    )

    # Verify update
    assert updated_run.status == "succeeded"
    assert updated_run.total_input_tokens == 12345
    assert updated_run.total_output_tokens == 67890
    assert updated_run.total_cache_creation_tokens == 1000
    assert updated_run.total_cache_read_tokens == 500
    assert updated_run.total_cost_usd == 0.85


def test_run_response_includes_token_fields(db_session, test_project):
    """Test that RunResponse schema includes token usage fields"""
    from backend.schemas.run import RunResponse

    # Create run with token data
    run = crud.create_run(db_session, test_project.id, is_batch=True)
    run.status = "succeeded"
    run.total_input_tokens = 10000
    run.total_output_tokens = 20000
    run.total_cache_creation_tokens = 500
    run.total_cache_read_tokens = 300
    run.total_cost_usd = 0.55

    db_session.commit()
    db_session.refresh(run)

    # Convert to response schema
    response = RunResponse.model_validate(run)

    # Verify all token fields are included
    assert response.total_input_tokens == 10000
    assert response.total_output_tokens == 20000
    assert response.total_cache_creation_tokens == 500
    assert response.total_cache_read_tokens == 300
    assert response.total_cost_usd == 0.55


@patch("src.utils.cost_tracker.get_default_tracker")
def test_token_usage_capture_flow(mock_get_tracker, db_session, test_project, mock_project_cost):
    """Test complete flow of capturing token usage from CostTracker"""
    # Mock CostTracker
    mock_tracker = Mock(spec=CostTracker)
    mock_tracker.get_project_cost.return_value = mock_project_cost
    mock_get_tracker.return_value = mock_tracker

    # Simulate what generator.py does
    from src.utils.cost_tracker import get_default_tracker

    cost_tracker = get_default_tracker()
    project_cost = cost_tracker.get_project_cost(test_project.id)

    # Create run
    run = crud.create_run(db_session, test_project.id, is_batch=True)

    # Update run with token usage (like generator.py does)
    updated_run = crud.update_run(
        db_session,
        run.id,
        status="succeeded",
        total_input_tokens=project_cost.total_input_tokens,
        total_output_tokens=project_cost.total_output_tokens,
        total_cache_creation_tokens=project_cost.total_cache_creation_tokens,
        total_cache_read_tokens=project_cost.total_cache_read_tokens,
        total_cost_usd=project_cost.total_cost,
    )

    # Verify data was captured correctly
    assert updated_run.total_input_tokens == 45234
    assert updated_run.total_output_tokens == 67890
    assert updated_run.total_cache_creation_tokens == 5000
    assert updated_run.total_cache_read_tokens == 2000
    assert updated_run.total_cost_usd == 1.23

    # Verify CostTracker was called with correct project_id
    mock_tracker.get_project_cost.assert_called_once_with(test_project.id)


def test_run_with_no_token_usage(db_session, test_project):
    """Test that runs without token usage still work (nullable fields)"""
    # Create run without token data
    run = crud.create_run(db_session, test_project.id, is_batch=True)
    run.status = "succeeded"
    # Don't set any token fields

    db_session.commit()
    db_session.refresh(run)

    # Verify nullable fields are None
    assert run.total_input_tokens is None
    assert run.total_output_tokens is None
    assert run.total_cache_creation_tokens is None
    assert run.total_cache_read_tokens is None
    assert run.total_cost_usd is None


def test_token_usage_in_logs(db_session, test_project):
    """Test that token usage appears in run logs"""
    from backend.schemas.run import LogEntry

    # Create run
    run = crud.create_run(db_session, test_project.id, is_batch=True)

    # Add log entry with token usage (like generator.py does)
    logs = [
        LogEntry(
            timestamp=datetime.now().isoformat(),
            message="Token usage: 45,234 input, 67,890 output ($1.23)",
        )
    ]

    updated_run = crud.update_run(
        db_session,
        run.id,
        status="succeeded",
        logs=[log.model_dump() for log in logs],
        total_input_tokens=45234,
        total_output_tokens=67890,
        total_cost_usd=1.23,
    )

    # Verify log entry exists
    assert updated_run.logs is not None
    assert len(updated_run.logs) > 0

    # Find the token usage log
    token_log = next(
        (log for log in updated_run.logs if "Token usage" in log.get("message", "")), None
    )
    assert token_log is not None
    assert "45,234 input" in token_log["message"]
    assert "$1.23" in token_log["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
