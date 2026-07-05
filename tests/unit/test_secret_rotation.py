"""Unit tests for backend.utils.secret_rotation."""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from backend.utils.secret_rotation import Secret, SecretManager


@pytest.fixture
def mgr(tmp_path):
    """SecretManager with a temp config path (no .env side effects)."""
    config = tmp_path / "secrets.json"
    m = SecretManager(config_path=config)
    return m


class TestSecret:
    def test_is_active_true_for_new_secret(self):
        s = Secret(
            id="abc",
            value="val",
            created_at=datetime.now().isoformat(),
            status="active",
        )
        assert s.is_active() is True

    def test_is_active_false_when_revoked(self):
        s = Secret(
            id="abc",
            value="val",
            created_at=datetime.now().isoformat(),
            status="revoked",
        )
        assert s.is_active() is False

    def test_is_expired_false_when_no_expiry(self):
        s = Secret(
            id="abc",
            value="val",
            created_at=datetime.now().isoformat(),
        )
        assert s.is_expired() is False

    def test_is_expired_true_when_past_expiry(self):
        past = (datetime.now() - timedelta(days=1)).isoformat()
        s = Secret(
            id="abc",
            value="val",
            created_at=datetime.now().isoformat(),
            expires_at=past,
        )
        assert s.is_expired() is True

    def test_is_active_false_when_expired(self):
        past = (datetime.now() - timedelta(days=1)).isoformat()
        s = Secret(
            id="abc",
            value="val",
            created_at=datetime.now().isoformat(),
            expires_at=past,
            status="active",
        )
        assert s.is_active() is False


class TestSecretManager:
    def test_generates_secret(self, mgr):
        secret = mgr.generate_secret()
        assert isinstance(secret, str)
        assert len(secret) > 0

    def test_generates_unique_secrets(self, mgr):
        s1 = mgr.generate_secret()
        s2 = mgr.generate_secret()
        assert s1 != s2

    def test_hash_secret_consistent(self, mgr):
        val = "my-secret-value"
        assert mgr.hash_secret(val) == mgr.hash_secret(val)

    def test_add_secret(self, mgr):
        s = mgr.add_secret("my-secret-value")
        assert s.value == "my-secret-value"
        assert s.status == "active"

    def test_add_same_secret_twice_returns_same(self, mgr):
        s1 = mgr.add_secret("same-value")
        s2 = mgr.add_secret("same-value")
        assert s1.id == s2.id

    def test_add_with_expiry(self, mgr):
        s = mgr.add_secret("expiring-secret", expires_in_days=7)
        assert s.expires_at is not None

    def test_get_active_secrets(self, mgr):
        initial = len(mgr.get_active_secrets())
        mgr.add_secret("active-unique-111")
        mgr.add_secret("active-unique-222")
        active = mgr.get_active_secrets()
        assert len(active) == initial + 2

    def test_get_primary_secret(self, mgr):
        mgr.add_secret("primary")
        assert mgr.get_primary_secret() == "primary"

    def test_get_primary_returns_none_when_empty(self, tmp_path):
        # Fresh manager with no env var
        import os

        saved = os.environ.pop("SECRET_KEY", None)
        try:
            m = SecretManager(config_path=tmp_path / "empty.json")
            assert m.get_primary_secret() is None
        finally:
            if saved:
                os.environ["SECRET_KEY"] = saved

    def test_revoke_secret(self, mgr):
        s = mgr.add_secret("to-revoke")
        mgr.revoke_secret(s.id)
        assert mgr.secrets[s.id].status == "revoked"
        assert s.value not in mgr.get_active_secrets()

    def test_cleanup_expired(self, mgr):
        from unittest.mock import patch

        past = (datetime.now() - timedelta(days=1)).isoformat()
        s = mgr.add_secret("expired-secret")
        mgr.secrets[s.id].expires_at = past
        with patch("builtins.print"):  # suppress emoji that fails on Windows console
            mgr.cleanup_expired()
        assert s.id not in mgr.secrets

    def test_cleanup_keeps_active(self, mgr):
        s = mgr.add_secret("active-secret")
        mgr.cleanup_expired()
        assert s.id in mgr.secrets

    def test_rotate_secret(self, mgr):
        old = mgr.add_secret("old-secret")
        new = mgr.rotate_secret(grace_period_days=7, deprecation_period_days=7)
        assert new.id != old.id
        assert new.is_active() is True
        # Old secret should now have an expiry set
        assert mgr.secrets[old.id].expires_at is not None

    def test_get_status(self, mgr):
        mgr.add_secret("s1")
        status = mgr.get_status()
        assert status["total"] >= 1
        assert "active" in status
        assert "secrets" in status

    def test_save_and_reload(self, tmp_path):
        config = tmp_path / "secrets.json"
        m1 = SecretManager(config_path=config)
        m1.add_secret("persist-this")

        # Load fresh from same file
        m2 = SecretManager(config_path=config)
        assert "persist-this" in m2.get_active_secrets()
