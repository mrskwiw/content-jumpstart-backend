"""
Unit tests for SoftDeleteMixin
"""

import pytest
from datetime import datetime
from backend.models.client import Client


class TestSoftDeleteMixin:
    def test_soft_delete_sets_flags(self, db_session, sample_client):
        """Test soft_delete() sets is_deleted and deleted_at"""
        assert sample_client.is_deleted == False
        assert sample_client.deleted_at is None

        sample_client.soft_delete()
        db_session.commit()

        assert sample_client.is_deleted == True
        assert sample_client.deleted_at is not None
        assert isinstance(sample_client.deleted_at, datetime)

    def test_restore_clears_flags(self, db_session, sample_client):
        """Test restore() clears is_deleted and deleted_at"""
        # First soft delete
        sample_client.soft_delete()
        db_session.commit()
        assert sample_client.is_deleted == True

        # Then restore
        sample_client.restore()
        db_session.commit()

        assert sample_client.is_deleted == False
        assert sample_client.deleted_at is None

    def test_is_active_property(self, sample_client):
        """Test is_active property returns correct status"""
        assert sample_client.is_active == True

        sample_client.soft_delete()
        assert sample_client.is_active == False

        sample_client.restore()
        assert sample_client.is_active == True

    def test_soft_delete_does_not_hard_delete(self, db_session, sample_client):
        """Test soft delete does not remove record from database"""
        client_id = sample_client.id
        sample_client.soft_delete()
        db_session.commit()

        # Record should still exist in database
        deleted_client = db_session.query(Client).filter(Client.id == client_id).first()
        assert deleted_client is not None
        assert deleted_client.is_deleted == True

    def test_multiple_soft_deletes_idempotent(self, db_session, sample_client):
        """Test multiple soft deletes don't cause errors"""
        sample_client.soft_delete()
        db_session.commit()

        first_deleted_at = sample_client.deleted_at

        # Delete again
        sample_client.soft_delete()
        db_session.commit()

        # Should still be deleted with updated timestamp
        assert sample_client.is_deleted == True
        assert sample_client.deleted_at >= first_deleted_at


class TestQueryFiltering:
    def test_query_excludes_soft_deleted_by_default(self, db_session, sample_client):
        """Test queries with is_deleted filter exclude soft-deleted records"""
        # Create and soft delete a client
        sample_client.soft_delete()
        db_session.commit()

        # Query should not return soft-deleted client
        active_clients = db_session.query(Client).filter(Client.is_deleted == False).all()
        deleted_client_ids = [c.id for c in active_clients]

        assert sample_client.id not in deleted_client_ids

    def test_query_can_include_soft_deleted_explicitly(self, db_session, sample_client):
        """Test queries can explicitly include soft-deleted records"""
        sample_client.soft_delete()
        db_session.commit()

        # Query for deleted records
        deleted_clients = db_session.query(Client).filter(Client.is_deleted == True).all()
        deleted_ids = [c.id for c in deleted_clients]

        assert sample_client.id in deleted_ids
