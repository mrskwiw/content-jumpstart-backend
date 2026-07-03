"""Unit tests for backend.services.audit_service."""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models.audit_log import AuditLog
from backend.services.audit_service import get_client_ip, log_action


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


class TestGetClientIp:
    def _req(self, forwarded_for=None, host="1.2.3.4"):
        req = MagicMock()
        req.headers = {}
        if forwarded_for:
            req.headers["X-Forwarded-For"] = forwarded_for
        req.client = MagicMock()
        req.client.host = host
        return req

    def test_uses_x_forwarded_for(self):
        req = self._req(forwarded_for="10.0.0.1, 10.0.0.2")
        assert get_client_ip(req) == "10.0.0.1"

    def test_strips_whitespace_from_forwarded_for(self):
        req = self._req(forwarded_for="  10.0.0.5 , 10.0.0.6")
        assert get_client_ip(req) == "10.0.0.5"

    def test_falls_back_to_request_client(self):
        req = self._req(host="5.6.7.8")
        assert get_client_ip(req) == "5.6.7.8"

    def test_returns_empty_when_no_client(self):
        req = MagicMock()
        req.headers = {}
        req.client = None
        assert get_client_ip(req) == ""


class TestLogAction:
    def test_creates_audit_entry(self, db):
        log_action(
            db,
            user_id="user-1",
            user_email="user@example.com",
            action="Created client",
            action_type="create",
            resource_type="client",
        )
        entry = db.query(AuditLog).first()
        assert entry is not None
        assert entry.action == "Created client"
        assert entry.user_id == "user-1"

    def test_audit_id_has_al_prefix(self, db):
        log_action(db, action="Test", action_type="create", resource_type="project")
        entry = db.query(AuditLog).first()
        assert entry.id.startswith("al-")

    def test_stores_all_fields(self, db):
        log_action(
            db,
            user_id="u1",
            user_email="u@test.com",
            user_name="Test User",
            action="Updated client",
            action_type="update",
            resource_type="client",
            resource_id="client-123",
            resource_name="Test Client",
            details="Changed name field",
            ip_address="192.168.1.1",
            status="success",
            metadata={"old": "A", "new": "B"},
        )
        entry = db.query(AuditLog).first()
        assert entry.resource_id == "client-123"
        assert entry.ip_address == "192.168.1.1"
        assert entry.status == "success"

    def test_does_not_raise_on_db_failure(self):
        bad_db = MagicMock()
        bad_db.add.side_effect = Exception("DB is down")
        # Should NOT raise — audit failures are suppressed
        log_action(bad_db, action="Test", action_type="create", resource_type="client")

    def test_rolls_back_on_db_failure(self):
        bad_db = MagicMock()
        bad_db.commit.side_effect = Exception("commit failed")
        log_action(bad_db, action="Test", action_type="create", resource_type="client")
        bad_db.rollback.assert_called()

    def test_default_status_is_success(self, db):
        log_action(db, action="Test", action_type="create", resource_type="client")
        entry = db.query(AuditLog).first()
        assert entry.status == "success"
