"""GAP-AUTH-02 — the email-verification gate (services/verification_gate.py).

`REQUIRE_EMAIL_VERIFICATION` is authoritative and nothing may quietly override it: a
missing or broken email transport must never turn an auth control off by itself. The
transport is only inspected at boot, to warn a human.
"""

import pytest

from backend.config import settings
from backend.services.verification_gate import (
    check_startup_configuration,
    email_delivery_available,
    email_verification_enforced,
)

_TRANSPORT_ENV = ("RESEND_API_KEY", "SMTP_USER", "SMTP_USERNAME", "SMTP_PASSWORD")


@pytest.fixture
def clean_transport(monkeypatch):
    """Start from 'no transport configured'."""
    for key in _TRANSPORT_ENV:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("EMAIL_PROVIDER", "auto")
    return monkeypatch


class TestEnforcement:
    def test_follows_the_setting_when_on(self, clean_transport):
        clean_transport.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
        assert email_verification_enforced() is True

    def test_follows_the_setting_when_off(self, clean_transport):
        clean_transport.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", False)
        clean_transport.setenv("RESEND_API_KEY", "key")
        assert email_verification_enforced() is False

    def test_a_missing_transport_does_not_disable_it(self, clean_transport):
        # The regression that matters: an unconfigured (or misconfigured) mailer is the
        # likeliest rollout mistake, and it must not silently open authentication.
        clean_transport.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
        assert email_delivery_available() is False
        assert email_verification_enforced() is True

    def test_a_broken_email_import_does_not_disable_it(self, clean_transport, monkeypatch):
        clean_transport.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
        monkeypatch.setattr(
            "backend.services.verification_gate.email_delivery_available",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        # Enforcement doesn't consult delivery at all, so it can't be thrown off by it.
        assert email_verification_enforced() is True


class TestDeliveryAvailability:
    def test_detects_resend(self, clean_transport):
        clean_transport.setenv("RESEND_API_KEY", "key")
        assert email_delivery_available() is True

    def test_detects_smtp(self, clean_transport):
        clean_transport.setenv("SMTP_USER", "mailer@example.com")
        clean_transport.setenv("SMTP_PASSWORD", "secret")  # pragma: allowlist secret
        assert email_delivery_available() is True

    def test_partial_smtp_credentials_are_not_a_transport(self, clean_transport):
        clean_transport.setenv("SMTP_USER", "mailer@example.com")
        assert email_delivery_available() is False

    def test_explicit_log_provider_is_not_a_transport(self, clean_transport):
        clean_transport.setenv("RESEND_API_KEY", "key")
        clean_transport.setenv("EMAIL_PROVIDER", "log")
        assert email_delivery_available() is False


class TestStartupGuard:
    """Decision #236 — the enforced-but-undeliverable pairing must not deploy at all."""

    def test_refuses_to_boot_when_enforced_without_a_transport(self, clean_transport):
        clean_transport.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
        with pytest.raises(RuntimeError, match="REQUIRE_EMAIL_VERIFICATION"):
            check_startup_configuration(debug_mode=False)

    def test_debug_mode_logs_and_continues(self, clean_transport):
        # Refusing to start would just block local work; the misconfiguration is loud.
        clean_transport.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
        assert check_startup_configuration(debug_mode=True) is True

    def test_passes_when_a_transport_exists(self, clean_transport):
        clean_transport.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
        clean_transport.setenv("RESEND_API_KEY", "key")
        assert check_startup_configuration(debug_mode=False) is False

    def test_passes_when_the_gate_is_off(self, clean_transport):
        clean_transport.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", False)
        assert check_startup_configuration(debug_mode=False) is False
