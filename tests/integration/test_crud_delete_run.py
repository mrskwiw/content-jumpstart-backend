"""
Unit tests for Bug #49: crud.delete_run() function

Tests the newly added delete_run function in backend.services.crud
"""

import pytest
from backend.services import crud
from backend.models import Run, Project


class TestDeleteRun:
    """Test suite for crud.delete_run() function (Bug #49)"""

    def test_delete_run_success(self, db_session, test_project):
        """Test successful deletion of a run"""
        # Create a run
        run = crud.create_run(db_session, project_id=test_project.id, is_batch=False)
        run_id = run.id

        # Verify run exists
        assert crud.get_run(db_session, run_id) is not None

        # Delete the run
        result = crud.delete_run(db_session, run_id)

        # Assertions
        assert result is True
        assert crud.get_run(db_session, run_id) is None

    def test_delete_run_nonexistent(self, db_session):
        """Test deletion of non-existent run returns False"""
        result = crud.delete_run(db_session, "run-nonexistent123")
        assert result is False

    def test_delete_run_removes_from_database(self, db_session, test_project):
        """Test that delete_run actually removes record from database"""
        # Create run
        run = crud.create_run(db_session, project_id=test_project.id, is_batch=True)
        run_id = run.id

        # Delete
        crud.delete_run(db_session, run_id)

        # Query database directly
        db_run = db_session.query(Run).filter(Run.id == run_id).first()
        assert db_run is None

    def test_delete_run_multiple_runs(self, db_session, test_project):
        """Test deleting one run doesn't affect other runs"""
        # Create multiple runs
        run1 = crud.create_run(db_session, project_id=test_project.id)
        run2 = crud.create_run(db_session, project_id=test_project.id)
        run3 = crud.create_run(db_session, project_id=test_project.id)

        # Delete run2
        result = crud.delete_run(db_session, run2.id)

        # Assertions
        assert result is True
        assert crud.get_run(db_session, run1.id) is not None
        assert crud.get_run(db_session, run2.id) is None
        assert crud.get_run(db_session, run3.id) is not None

    def test_delete_run_idempotent(self, db_session, test_project):
        """Test that deleting same run twice returns False on second attempt"""
        run = crud.create_run(db_session, project_id=test_project.id)
        run_id = run.id

        # First deletion succeeds
        assert crud.delete_run(db_session, run_id) is True

        # Second deletion returns False (run doesn't exist)
        assert crud.delete_run(db_session, run_id) is False
