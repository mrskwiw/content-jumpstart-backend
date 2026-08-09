"""Entitlement gate — when the subscribe notice appears, and what stays reachable.

Two independent triggers, because the two products end differently:
  * trial        → bounded by TIME (30 days), whatever credits remain
  * subscription → bounded by CREDITS (already-purchased credit is the customer's
                   property and stays spendable after the subscription lapses)

The risk is not "does it block" but "does it block the wrong things": an account
that cannot subscribe, sign out, or export its data is trapped, and a gate that
misses a route defeats the point. Both directions are asserted.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.services import account_state as acct
from backend.services.account_state import (
    AccountExpiredError,
    path_allowed_while_expired,
    require_access,
)


class _FakeDb:
    """Stands in for the session; every read the gate makes is monkeypatched."""


@pytest.fixture
def db():
    return _FakeDb()


def _state(monkeypatch, state):
    monkeypatch.setattr(acct, "account_state", lambda db: state)


def _credits(monkeypatch, amount):
    monkeypatch.setattr(acct, "account_credits", lambda db: amount)


def _trial_ends(monkeypatch, delta_days):
    when = datetime.now(UTC) + timedelta(days=delta_days)
    monkeypatch.setattr(acct, "trial_ends_at", lambda db: when)


# ── trigger 1: a trial ends on TIME, regardless of leftover credits ──────────


def test_trial_inside_the_window_is_not_gated(monkeypatch, db):
    _state(monkeypatch, "trial")
    _trial_ends(monkeypatch, +5)
    require_access(db, "/api/clients")


def test_trial_past_the_window_is_gated_even_with_credits_left(monkeypatch, db):
    # The grant was to evaluate the product for 30 days, not a balance to draw
    # down forever. Time wins over balance here.
    _state(monkeypatch, "trial")
    _trial_ends(monkeypatch, -1)
    _credits(monkeypatch, 2_500)
    with pytest.raises(AccountExpiredError):
        require_access(db, "/api/clients")


def test_trial_with_no_recorded_end_date_fails_OPEN_and_warns(monkeypatch, db, caplog):
    # A trial with no end date is OUR provisioning bug. Locking out a customer we
    # invited to try the product is the worse of the two errors — but it must be
    # loud, not silent, or an unbounded free trial goes unnoticed.
    import logging

    _state(monkeypatch, "trial")
    monkeypatch.setattr(acct, "trial_ends_at", lambda db: None)

    with caplog.at_level(logging.WARNING, logger=acct.logger.name):
        require_access(db, "/api/clients")  # must not raise

    assert any(
        "trial_ends_at" in r.getMessage() for r in caplog.records
    ), "the misconfiguration must be logged, not swallowed"


# ── trigger 2: a lapsed subscription ends on CREDITS ─────────────────────────


def test_expired_with_credits_remaining_is_NOT_gated(monkeypatch, db):
    # Credits already paid for are the customer's property. Cutting them off at
    # subscription lapse would be confiscating purchased credit.
    _state(monkeypatch, "expired")
    _credits(monkeypatch, 400)
    require_access(db, "/api/clients")
    require_access(db, "/api/generator/run")  # including spend paths


def test_expired_with_zero_credits_is_gated(monkeypatch, db):
    _state(monkeypatch, "expired")
    _credits(monkeypatch, 0)
    with pytest.raises(AccountExpiredError):
        require_access(db, "/api/clients")


def test_expired_with_negative_balance_is_gated(monkeypatch, db):
    _state(monkeypatch, "expired")
    _credits(monkeypatch, -10)
    with pytest.raises(AccountExpiredError):
        require_access(db, "/api/clients")


# ── states that must NOT be gated here ───────────────────────────────────────


@pytest.mark.parametrize("state", ["active", "past_due", "suspended"])
def test_live_subscription_states_are_never_gated(monkeypatch, db, state):
    # past_due/suspended are billing problems on a LIVE subscription: spending is
    # blocked at the credit chokepoint (S-01.4d), access is deliberately preserved.
    _state(monkeypatch, state)
    _credits(monkeypatch, 0)
    require_access(db, "/api/clients")


# ── what the gate closes ─────────────────────────────────────────────────────


@pytest.fixture
def gated(monkeypatch):
    _state(monkeypatch, "expired")
    _credits(monkeypatch, 0)
    return _FakeDb()


@pytest.mark.parametrize(
    "path",
    [
        "/api/clients",
        "/api/projects/1",
        "/api/generator/run",
        "/api/research/audience",
        "/api/media/generate",
        "/api/distribution/queue",
        "/api/admin/users",  # even admin: the ACCOUNT has no entitlement
    ],
)
def test_gated_account_is_blocked(gated, path):
    with pytest.raises(AccountExpiredError):
        require_access(gated, path)


def test_a_future_endpoint_is_blocked_by_default(gated):
    with pytest.raises(AccountExpiredError):
        require_access(gated, "/api/some-feature-invented-next-quarter")


# ── what must stay reachable ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "path",
    [
        "/api/auth/me",
        "/api/auth/logout",
        "/api/auth/refresh",
        "/api/mfa/verify",
        "/api/account/status",
        "/api/stripe/checkout",
    ],
)
def test_escape_hatches_stay_open(gated, path):
    require_access(gated, path)


def test_gdpr_export_and_erasure_stay_open(gated):
    # Withholding data because someone stopped paying is hostile; blocking erasure
    # would let a billing state override a statutory right.
    require_access(gated, "/api/privacy/account/export", "GET")
    require_access(gated, "/api/privacy/instance/export", "GET")
    require_access(gated, "/api/privacy/account", "DELETE")


def test_buying_credits_stays_open(gated):
    # THE trap this gate could most easily become: the commonest way to get gated
    # is running out of credits, so gating the endpoint that SELLS credits would
    # make the lockout unescapable.
    require_access(gated, "/api/credits/purchase", "POST")
    require_access(gated, "/api/credits/balance", "GET")
    require_access(gated, "/api/credits/packages", "GET")
    require_access(gated, "/api/credits/summary", "GET")
    require_access(gated, "/api/credits/estimate", "POST")


def test_subscription_checkout_stays_open(gated):
    require_access(gated, "/api/stripe/checkout", "POST")
    require_access(gated, "/api/stripe/portal", "POST")
    require_access(gated, "/api/stripe/payment-status/sess_123", "GET")


def test_admin_credit_minting_stays_SHUT(gated):
    # Otherwise an admin on a gated account grants themselves credits and walks
    # straight back in — the gate defeating itself. Deny beats the broad allow.
    with pytest.raises(AccountExpiredError):
        require_access(gated, "/api/credits/admin/adjust", "POST")


def test_deny_rules_beat_allow_prefixes():
    assert path_allowed_while_expired("/api/credits/purchase", "POST")
    assert not path_allowed_while_expired("/api/credits/admin/adjust", "POST")


def test_settings_are_readable_but_not_writable(gated):
    # The page renders so the account stays legible; operational config cannot be
    # changed while there is no entitlement to operate.
    require_access(gated, "/api/settings/integrations/status", "GET")
    require_access(gated, "/api/settings/web-search", "GET")
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        with pytest.raises(AccountExpiredError):
            require_access(gated, "/api/settings/web-search", method)


# ── allowlist mechanics ──────────────────────────────────────────────────────


def test_method_awareness():
    assert path_allowed_while_expired("/api/settings/web-search", "GET")
    assert not path_allowed_while_expired("/api/settings/web-search", "POST")
    assert path_allowed_while_expired("/api/auth/logout", "POST")  # any method
    assert path_allowed_while_expired("/api/settings", "get")  # case-insensitive


def test_prefix_matching_is_not_fooled_by_a_containing_path():
    assert not path_allowed_while_expired("/api/clients/api/auth/", "GET")
    assert not path_allowed_while_expired("/api/clients", "GET")
