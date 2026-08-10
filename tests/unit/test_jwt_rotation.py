"""
Tests for JWT secret rotation integration with auth.py.
"""

import pytest
from datetime import timedelta
from pathlib import Path
import tempfile

from backend.utils.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.utils.secret_rotation import SecretManager


@pytest.fixture
def temp_secrets_file():
    """Create temporary secrets file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        # Write empty but valid JSON
        f.write('{"secrets": [], "last_updated": "2026-01-08T00:00:00"}')
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def secret_manager(temp_secrets_file, monkeypatch):
    """Create SecretManager with temporary file."""
    # Reset global singleton
    import backend.utils.auth as auth_module

    auth_module._secret_manager = None

    # Mock the config path
    manager = SecretManager(config_path=temp_secrets_file)

    # Inject into auth module
    auth_module._secret_manager = manager

    yield manager

    # Cleanup: Reset singleton after test
    auth_module._secret_manager = None


def test_create_token_with_primary_secret(secret_manager):
    """Test that tokens are created with the primary secret."""
    # Add initial secret
    secret_manager.add_secret("test-secret-123")

    # Create access token
    token = create_access_token({"sub": "user@example.com"})
    assert token is not None
    assert isinstance(token, str)

    # Decode should work
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user@example.com"
    assert payload["type"] == "access"


def test_create_refresh_token_with_primary_secret(secret_manager):
    """Test that refresh tokens are created with the primary secret."""
    # Add initial secret
    secret_manager.add_secret("test-secret-456")

    # Create refresh token
    token = create_refresh_token({"sub": "user@example.com"})
    assert token is not None
    assert isinstance(token, str)

    # Decode should work
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user@example.com"
    assert payload["type"] == "refresh"


def test_decode_with_multiple_active_secrets(secret_manager):
    """Test that tokens can be decoded with any active secret during grace period."""
    # Add first secret and create token
    secret_manager.add_secret("old-secret-789")
    token_old = create_access_token({"sub": "old-user@example.com"})

    # Rotate secret (creates new primary, keeps old active)
    secret_manager.rotate_secret(grace_period_days=7)

    # Create new token with new primary
    token_new = create_access_token({"sub": "new-user@example.com"})

    # Both tokens should decode successfully
    payload_old = decode_token(token_old)
    assert payload_old is not None
    assert payload_old["sub"] == "old-user@example.com"

    payload_new = decode_token(token_new)
    assert payload_new is not None
    assert payload_new["sub"] == "new-user@example.com"


def test_decode_fails_with_invalid_token(secret_manager):
    """Test that invalid tokens are rejected."""
    secret_manager.add_secret("test-secret-999")

    # Try to decode invalid token
    payload = decode_token("invalid.token.here")
    assert payload is None


def test_fallback_to_settings_secret_key(monkeypatch):
    """Test fallback to settings.SECRET_KEY when no secrets configured."""
    # Create a new temp file for this test
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"secrets": [], "last_updated": "2026-01-08T00:00:00"}')
        temp_path = Path(f.name)

    try:
        # Reset global singleton
        import backend.utils.auth as auth_module

        auth_module._secret_manager = None

        # Create empty SecretManager
        empty_manager = SecretManager(config_path=temp_path)
        empty_manager.secrets = {}  # Clear all secrets
        empty_manager.save_secrets()

        # Mock settings.SECRET_KEY
        from backend.config import settings

        monkeypatch.setattr(settings, "SECRET_KEY", "fallback-secret-key")

        # Inject empty manager
        auth_module._secret_manager = empty_manager

        # Create token should use fallback
        token = create_access_token({"sub": "fallback-user@example.com"})
        assert token is not None

        # Decode should work with fallback
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "fallback-user@example.com"

    finally:
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()
        # Reset singleton
        auth_module._secret_manager = None


def test_token_expiry_respected(secret_manager):
    """Test that expired tokens are rejected."""
    secret_manager.add_secret("test-secret-expiry")

    # Create token with very short expiry
    token = create_access_token(
        {"sub": "expiry-test@example.com"}, expires_delta=timedelta(seconds=-1)  # Already expired
    )

    # Should fail to decode due to expiry
    payload = decode_token(token)
    assert payload is None  # Expired token rejected


def test_deprecated_secret_warning(secret_manager):
    """A token verified by a rotated-out secret must warn, naming the deprecated index.

    BUGS #240: this was flaky — it passed alone and across `tests/unit`, but failed
    intermittently in the full run. The old version depended on THREE pieces of
    global logging state it did not control: the logger's ``propagate`` flag, the
    root handlers ``caplog`` installs onto, and the module-wide ``logging.disable``
    threshold. Any test anywhere in the session could disturb one of them, and the
    failure surfaced here rather than at the cause.

    Root cause was never pinned down (see BUGS #240). Rather than keep hunting, the
    test now captures from its OWN handler attached directly to the logger under
    test, so none of that global state can reach it — which also protects against
    whichever future test would have broken it next.
    """
    import logging

    class _Capture(logging.Handler):
        def __init__(self) -> None:
            super().__init__(level=logging.WARNING)
            self.messages: list[str] = []

        def emit(self, record: logging.LogRecord) -> None:
            # getMessage(), not `.message` — the latter only exists once a Formatter
            # has run, which is itself a piece of state this test should not rely on.
            self.messages.append(record.getMessage())

    auth_logger = logging.getLogger("backend.utils.auth")
    handler = _Capture()

    original_level = auth_logger.level
    original_disabled = auth_logger.disabled
    # Module-wide suppression set by any other test would silence the logger no
    # matter what we configure on it, so neutralise it too. Read via the public
    # getter rather than logging.root.manager.disable, which is an internal.
    original_manager_disable = logging.getLogger().manager.disable

    auth_logger.addHandler(handler)
    auth_logger.setLevel(logging.WARNING)
    auth_logger.disabled = False
    logging.disable(logging.NOTSET)
    try:
        secret_manager.add_secret("deprecated-secret")
        token_old = create_access_token({"sub": "deprecated-user@example.com"})

        secret_manager.rotate_secret(grace_period_days=7)

        payload = decode_token(token_old)
        assert payload is not None, "token signed with the deprecated secret should still verify"

        logged = " | ".join(handler.messages)
        assert (
            "deprecated secret" in logged.lower()
        ), f"no deprecation warning; got: {handler.messages}"
        assert "index 1" in logged, f"warning did not name the index; got: {handler.messages}"
    finally:
        auth_logger.removeHandler(handler)
        auth_logger.setLevel(original_level)
        auth_logger.disabled = original_disabled
        logging.disable(original_manager_disable)


def test_rotation_workflow_end_to_end(secret_manager):
    """Test complete rotation workflow."""
    # 1. Initial state: Add first secret
    secret_manager.add_secret("initial-secret")
    token1 = create_access_token({"sub": "user1@example.com"})

    # Verify token1 works
    payload1 = decode_token(token1)
    assert payload1["sub"] == "user1@example.com"

    # 2. Rotate: New secret becomes primary, old stays active
    secret_manager.rotate_secret(grace_period_days=7)
    token2 = create_access_token({"sub": "user2@example.com"})

    # Both tokens should work during grace period
    assert decode_token(token1)["sub"] == "user1@example.com"
    assert decode_token(token2)["sub"] == "user2@example.com"

    # 3. After grace period, old secret would be deprecated
    # (Not testing actual time passage, just verifying the mechanism)

    # Verify we have 2 active secrets
    active_secrets = secret_manager.get_active_secrets()
    assert len(active_secrets) == 2

    # Verify primary is the newest
    primary = secret_manager.get_primary_secret()
    assert primary == active_secrets[0]
