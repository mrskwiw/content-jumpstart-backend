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


class AccountSuspendedError(Exception):
    """Raised when a spend is attempted on a past-due / suspended account."""

    def __init__(self, state: str) -> None:
        super().__init__(f"account is {state}; spending is blocked until billing is resolved")
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
