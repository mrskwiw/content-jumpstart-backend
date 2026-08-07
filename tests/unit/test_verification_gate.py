"""GAP-AUTH-02 — the resolved email-verification gate (services/verification_gate.py).

The gate is fail-safe: operator intent alone does not enforce it, because an instance
that cannot send a verification email would lock out every unverified account with no
recovery short of database access.
"""

import pytest

from backend.config import settings
from backend.services.verification_gate import (
    email_delivery_available,
    email_verification_enforced,
)

_TRANSPORT_ENV = ("RESEND_API_KEY", "SMTP_USER", "SMTP_USERNAME", "SMTP_PASSWORD")


@pytest.fixture
def clean_transport(monkeypatch):
    """Start from 'no transport configured', with the process cache cleared."""
    for key in _TRANSPORT_ENV:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("EMAIL_PROVIDER", "auto")
    email_delivery_available.cache_clear()
    yield monkeypatch
    email_delivery_available.cache_clear()


def test_intent_off_is_never_enforced(clean_transport):
    clean_transport.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", False)
    clean_transport.setenv("RESEND_API_KEY", "key")
    email_delivery_available.cache_clear()
    assert email_verification_enforced() is False


def test_intent_on_without_a_transport_stands_down(clean_transport):
    clean_transport.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
    assert email_delivery_available() is False
    assert email_verification_enforced() is False


def test_intent_on_with_resend_enforces(clean_transport):
    clean_transport.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
    clean_transport.setenv("RESEND_API_KEY", "key")
    email_delivery_available.cache_clear()
    assert email_verification_enforced() is True


def test_intent_on_with_smtp_credentials_enforces(clean_transport):
    clean_transport.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
    clean_transport.setenv("SMTP_USER", "mailer@example.com")
    clean_transport.setenv("SMTP_PASSWORD", "secret")  # pragma: allowlist secret
    email_delivery_available.cache_clear()
    assert email_verification_enforced() is True


def test_explicit_log_only_provider_stands_down(clean_transport):
    # EMAIL_PROVIDER=log means "never actually send", even with a key present.
    clean_transport.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
    clean_transport.setenv("RESEND_API_KEY", "key")
    clean_transport.setenv("EMAIL_PROVIDER", "log")
    email_delivery_available.cache_clear()
    assert email_verification_enforced() is False


def test_partial_smtp_credentials_are_not_a_transport(clean_transport):
    # A username with no password can't authenticate — EmailSystem falls back to log.
    clean_transport.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
    clean_transport.setenv("SMTP_USER", "mailer@example.com")
    email_delivery_available.cache_clear()
    assert email_verification_enforced() is False
