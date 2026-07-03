"""
Unit tests for data_privacy_service - GDPR/CCPA compliance
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.services.data_privacy_service import (
    soft_delete_client,
    anonymize_client,
    export_client_data,
    restore_soft_deleted_client,
    purge_soft_deleted_records,
)


class TestSoftDeleteClient:
    def test_soft_delete_client_success(self, db_session, sample_client, sample_project):
        """Test soft deleting a client marks it as deleted"""
        result = soft_delete_client(sample_client.id, db_session, cascade=True)

        assert result["status"] == "success"
        assert result["client_id"] == sample_client.id
        assert "deleted_at" in result

        # Verify client is soft deleted
        db_session.refresh(sample_client)
        assert sample_client.is_deleted == True
        assert sample_client.deleted_at is not None

    def test_soft_delete_cascades_to_projects(self, db_session, sample_client, sample_project):
        """Test soft delete cascades to related projects"""
        result = soft_delete_client(sample_client.id, db_session, cascade=True)

        assert result["deleted_counts"]["projects"] >= 1

        # Verify project is soft deleted
        db_session.refresh(sample_project)
        assert sample_project.is_deleted == True

    def test_soft_delete_without_cascade(self, db_session, sample_client, sample_project):
        """Test soft delete without cascade only deletes client"""
        result = soft_delete_client(sample_client.id, db_session, cascade=False)

        assert result["deleted_counts"]["projects"] == 0

        # Verify project is NOT soft deleted
        db_session.refresh(sample_project)
        assert sample_project.is_deleted == False

    def test_soft_delete_nonexistent_client_raises_error(self, db_session):
        """Test soft deleting nonexistent client raises ValueError"""
        with pytest.raises(ValueError, match="not found"):
            soft_delete_client("nonexistent-id", db_session)


class TestAnonymizeClient:
    def test_anonymize_replaces_pii(self, db_session, sample_client):
        """Test anonymization replaces all PII fields"""
        original_name = sample_client.name
        original_email = sample_client.email

        result = anonymize_client(sample_client.id, db_session)

        db_session.refresh(sample_client)
        assert sample_client.name.startswith("ANONYMIZED_USER_")
        assert sample_client.email.endswith("@anonymized.local")
        assert sample_client.name != original_name
        assert sample_client.email != original_email

    def test_anonymize_preserves_analytics(self, db_session, sample_client):
        """Test anonymization preserves non-PII analytics data"""
        original_platforms = sample_client.platforms

        anonymize_client(sample_client.id, db_session)

        db_session.refresh(sample_client)
        assert sample_client.platforms == original_platforms

    def test_anonymize_marks_as_deleted(self, db_session, sample_client):
        """Test anonymization marks client as deleted"""
        anonymize_client(sample_client.id, db_session)

        db_session.refresh(sample_client)
        assert sample_client.is_deleted == True
        assert sample_client.deleted_at is not None


class TestExportClientData:
    def test_export_includes_client_data(self, db_session, sample_client):
        """Test export includes all client PII"""
        export = export_client_data(sample_client.id, db_session)

        assert "client" in export
        assert export["client"]["id"] == sample_client.id
        assert export["client"]["name"] == sample_client.name
        assert export["client"]["email"] == sample_client.email

    def test_export_includes_projects(self, db_session, sample_client, sample_project):
        """Test export includes related projects"""
        export = export_client_data(sample_client.id, db_session)

        assert "projects" in export
        assert len(export["projects"]) >= 1
        assert export["projects"][0]["id"] == sample_project.id

    def test_export_includes_metadata(self, db_session, sample_client):
        """Test export includes GDPR metadata"""
        export = export_client_data(sample_client.id, db_session)

        assert "export_metadata" in export
        assert "client_id" in export["export_metadata"]
        assert "exported_at" in export["export_metadata"]


class TestRestoreSoftDeletedClient:
    def test_restore_within_recovery_period(self, db_session, sample_client):
        """Test restoring client within 90-day recovery period"""
        # Soft delete first
        soft_delete_client(sample_client.id, db_session)
        db_session.refresh(sample_client)
        assert sample_client.is_deleted == True

        # Restore
        result = restore_soft_deleted_client(sample_client.id, db_session)

        assert result["status"] == "success"
        db_session.refresh(sample_client)
        assert sample_client.is_deleted == False
        assert sample_client.deleted_at is None

    def test_restore_outside_recovery_period_fails(self, db_session, sample_client):
        """Test restoring client after 90 days raises error"""
        # Soft delete and manually set old deletion date
        sample_client.soft_delete()
        sample_client.deleted_at = datetime.utcnow() - timedelta(days=91)
        db_session.commit()

        with pytest.raises(ValueError, match="90 days ago"):
            restore_soft_deleted_client(sample_client.id, db_session)


class TestPurgeSoftDeletedRecords:
    def test_purge_dry_run_does_not_delete(self, db_session, sample_client):
        """Test dry run mode does not actually delete"""
        # Soft delete with old date
        sample_client.soft_delete()
        sample_client.deleted_at = datetime.utcnow() - timedelta(days=91)
        db_session.commit()

        result = purge_soft_deleted_records(90, db_session, dry_run=True)

        assert result["dry_run"] == True
        # Client should still exist
        db_session.refresh(sample_client)
        assert sample_client.id is not None

    def test_purge_deletes_old_records(self, db_session, sample_client):
        """Test purge actually deletes records older than threshold"""
        client_id = sample_client.id

        # Soft delete with old date
        sample_client.soft_delete()
        sample_client.deleted_at = datetime.utcnow() - timedelta(days=91)
        db_session.commit()

        result = purge_soft_deleted_records(90, db_session, dry_run=False)

        assert result["dry_run"] == False
        assert result["deleted"]["clients"] >= 1
