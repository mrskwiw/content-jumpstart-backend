"""Tests for backend/observability.py — Sentry error reporting (GAP-BE-02).

Sentry is opt-in per instance via SENTRY_DSN: with no DSN nothing is initialised and
nothing leaves the process. Request bodies on this app carry users' emails and client
briefs, so PII collection stays off.
"""

from unittest.mock import patch

import pytest

from backend import observability

_SENTRY_VARS = (
    "SENTRY_DSN",
    "SENTRY_ENVIRONMENT",
    "SENTRY_RELEASE",
    "SENTRY_TRACES_SAMPLE_RATE",
    "ENVIRONMENT",
    "RENDER_GIT_COMMIT",
    "RENDER_SERVICE_NAME",
)
_DSN = "https://public@o0.ingest.sentry.io/0"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in _SENTRY_VARS:
        monkeypatch.delenv(var, raising=False)


def test_no_dsn_means_no_init():
    with patch.object(observability.sentry_sdk, "init") as init:
        assert observability.init_sentry() is False
    init.assert_not_called()


def test_blank_dsn_means_no_init(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "   ")
    with patch.object(observability.sentry_sdk, "init") as init:
        assert observability.init_sentry() is False
    init.assert_not_called()


def test_dsn_initialises_with_pii_off_and_tracing_off_by_default(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", _DSN)
    with patch.object(observability.sentry_sdk, "init") as init:
        assert observability.init_sentry() is True
    kwargs = init.call_args.kwargs
    assert kwargs["dsn"] == _DSN
    assert kwargs["send_default_pii"] is False
    assert kwargs["traces_sample_rate"] == 0.0
    assert kwargs["environment"] == "production"


def test_release_environment_and_instance_come_from_render(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", _DSN)
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc123")
    monkeypatch.setenv("RENDER_SERVICE_NAME", "cj-acme")
    with patch.object(observability.sentry_sdk, "init") as init:
        observability.init_sentry()
    kwargs = init.call_args.kwargs
    assert kwargs["environment"] == "staging"
    assert kwargs["release"] == "abc123"
    # One Render service per customer: the instance tag says whose instance failed.
    assert kwargs["server_name"] == "cj-acme"


def test_explicit_sentry_settings_win(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", _DSN)
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "prod-eu")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc123")
    monkeypatch.setenv("SENTRY_RELEASE", "cj@1.2.3")
    with patch.object(observability.sentry_sdk, "init") as init:
        observability.init_sentry()
    kwargs = init.call_args.kwargs
    assert kwargs["environment"] == "prod-eu"
    assert kwargs["release"] == "cj@1.2.3"


def test_valid_trace_sample_rate_is_used(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", _DSN)
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.25")
    with patch.object(observability.sentry_sdk, "init") as init:
        observability.init_sentry()
    assert init.call_args.kwargs["traces_sample_rate"] == 0.25


@pytest.mark.parametrize("bad", ["lots", "-0.1", "1.5", "nan"])
def test_invalid_trace_sample_rate_falls_back_to_zero(monkeypatch, bad):
    monkeypatch.setenv("SENTRY_DSN", _DSN)
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", bad)
    with patch.object(observability.sentry_sdk, "init") as init:
        observability.init_sentry()
    assert init.call_args.kwargs["traces_sample_rate"] == 0.0


def test_init_failure_does_not_break_startup(monkeypatch):
    # A malformed DSN makes sentry_sdk.init raise; observability must never take
    # the app down with it.
    monkeypatch.setenv("SENTRY_DSN", "not-a-dsn")
    with patch.object(observability.sentry_sdk, "init", side_effect=ValueError("bad dsn")):
        assert observability.init_sentry() is False
