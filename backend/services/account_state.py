"""Account-state suspension gate (S-01.4d).

A single guard for the spend paths: when the control plane marks an instance
``past_due`` or ``suspended`` (written to the instance-config namespace, S-01.4a),
credit-spending actions are blocked with a clear "billing" signal, while READS —
listing/viewing/exporting content, login, billing links — stay available (the
customer's content is theirs; suspension gates *creation*, not *access*).

The gate lives in ``credit_service.deduct_credits`` (the universal spend
chokepoint), so every user-initiated spend is covered without per-router wiring.
A ``trial`` account is fully spendable (it holds the trial credit grant).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.services.settings_service import get_instance_config

# States in which credit spending is blocked. Everything else (active, trial, or
# unset → default active) is spendable.
BLOCKED_STATES = frozenset({"past_due", "suspended"})

_ACCOUNT_STATE_KEY = "account_state"
_DEFAULT_STATE = "active"


# States in which the whole application is closed, not just spending. An EXPIRED
# account has no live entitlement at all: a trial that ran out, or a subscription
# that lapsed. Distinct from past_due/suspended, which are *billing* problems on a
# live subscription and deliberately keep reads working.
EXPIRED_STATES = frozenset({"expired"})

# Authenticated paths that stay reachable while expired. Without these the gate
# would be a trap: the customer could neither subscribe nor sign out.
#   auth  — /me, logout, refresh, password change
#   mfa   — an MFA-enforced account must still finish authenticating
#   account — the subscribe page's own data (state, plans)
#   stripe  — the checkout the subscribe page sends them to
#   privacy — data export. Deliberate: locking someone out of their own data
#             because they stopped paying is both hostile and a GDPR portability
#             problem. Expiry withdraws the service, not their content.
_EXPIRED_ALLOWED_PREFIXES = (
    "/api/auth/",
    "/api/mfa/",
    "/api/account/",
    "/api/stripe/",
    "/api/privacy",
)


class AccountSuspendedError(Exception):
    """Raised when a spend is attempted on a past-due / suspended account."""

    def __init__(self, state: str) -> None:
        super().__init__(f"account is {state}; spending is blocked until billing is resolved")
        self.state = state


class AccountExpiredError(Exception):
    """Raised on any gated request while the account has no live entitlement."""

    def __init__(self, state: str) -> None:
        super().__init__(f"account is {state}; subscribe to restore access")
        self.state = state


def account_state(db: Session) -> str:
    """Current instance account state (defaults to ``active`` when unset)."""
    return get_instance_config(db, _ACCOUNT_STATE_KEY, default=_DEFAULT_STATE) or _DEFAULT_STATE


def is_spendable(db: Session) -> bool:
    return account_state(db) not in BLOCKED_STATES


def require_spendable(db: Session) -> None:
    """Raise :class:`AccountSuspendedError` if the account may not spend."""
    state = account_state(db)
    if state in BLOCKED_STATES:
        raise AccountSuspendedError(state)


def is_expired(db: Session) -> bool:
    """True when the account has no live entitlement (trial ended / sub lapsed)."""
    return account_state(db) in EXPIRED_STATES


def path_allowed_while_expired(path: str) -> bool:
    """Whether ``path`` stays reachable on an expired account (see the allowlist)."""
    return any(path.startswith(prefix) for prefix in _EXPIRED_ALLOWED_PREFIXES)


def require_access(db: Session, path: str) -> None:
    """Raise :class:`AccountExpiredError` unless the request may proceed.

    Applied to EVERY authenticated request rather than per-router, so a new endpoint
    is gated by default instead of being quietly exempt — the failure mode of an
    opt-in gate is an unpaid account that still works through whatever route nobody
    remembered to annotate.
    """
    if path_allowed_while_expired(path):
        return
    state = account_state(db)
    if state in EXPIRED_STATES:
        raise AccountExpiredError(state)
