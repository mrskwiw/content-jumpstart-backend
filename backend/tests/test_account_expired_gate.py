"""Expired-account entitlement gate.

The gate closes the whole app to an account with no live entitlement, so the risk
is not "does it block" but "does it block the wrong things" — an expired customer
who cannot sign out, export their data, or subscribe is trapped, and a gate that
fails open on some route defeats the point. Both directions are asserted here.
"""

from __future__ import annotations

import pytest

from backend.services.account_state import (
    EXPIRED_STATES,
    AccountExpiredError,
    path_allowed_while_expired,
    require_access,
)


class _FakeDb:
    """Stands in for the session; only the instance-config read matters."""


@pytest.fixture
def expired(monkeypatch):
    monkeypatch.setattr("backend.services.account_state.account_state", lambda db: "expired")
    return _FakeDb()


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setattr("backend.services.account_state.account_state", lambda db: "active")
    return _FakeDb()


# ── the gate closes ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "path",
    [
        "/api/clients",
        "/api/projects/1",
        "/api/posts",
        "/api/generator/run",
        "/api/research/audience",
        "/api/media/generate",
        "/api/distribution/queue",
        "/api/teams/me",
        "/api/admin/users",  # even admin: the account itself has no entitlement
    ],
)
def test_expired_account_is_blocked_everywhere(expired, path):
    with pytest.raises(AccountExpiredError):
        require_access(expired, path)


def test_an_unknown_future_endpoint_is_blocked_by_default(expired):
    # The whole reason the gate is central: a new router must be gated without
    # anyone remembering to annotate it.
    with pytest.raises(AccountExpiredError):
        require_access(expired, "/api/some-feature-invented-next-quarter")


# ── the gate must NOT trap the customer ──────────────────────────────────────


@pytest.mark.parametrize(
    "path",
    [
        "/api/auth/me",
        "/api/auth/logout",
        "/api/auth/refresh",
        "/api/auth/change-password",
        "/api/mfa/verify",  # an MFA-enforced account must still finish auth
        "/api/account/status",  # the subscribe page's own data
        "/api/stripe/checkout",  # the way out
        "/api/privacy/export",  # their content is theirs; expiry withdraws service
    ],
)
def test_escape_hatches_stay_open_while_expired(expired, path):
    require_access(expired, path)  # must not raise


def test_allowlist_predicate_matches_the_gate():
    assert path_allowed_while_expired("/api/auth/me")
    assert path_allowed_while_expired("/api/account/status")
    assert not path_allowed_while_expired("/api/clients")
    # Prefix matching must not be fooled by a path that merely contains an allowed one.
    assert not path_allowed_while_expired("/api/clients/api/auth/")


# ── live accounts are unaffected ─────────────────────────────────────────────


@pytest.mark.parametrize("path", ["/api/clients", "/api/generator/run", "/api/posts"])
def test_live_account_passes(live, path):
    require_access(live, path)


@pytest.mark.parametrize("state", ["active", "trial", "past_due", "suspended"])
def test_only_expired_closes_access(monkeypatch, state):
    # past_due/suspended are BILLING problems on a live subscription: spending is
    # blocked elsewhere (require_spendable), but access is deliberately preserved.
    monkeypatch.setattr("backend.services.account_state.account_state", lambda db: state)
    require_access(_FakeDb(), "/api/clients")
    assert state not in EXPIRED_STATES
