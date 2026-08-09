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

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.models import User
from backend.services.settings_service import get_instance_config

logger = logging.getLogger(__name__)

# States in which credit spending is blocked. Everything else (active, trial, or
# unset → default active) is spendable.
BLOCKED_STATES = frozenset({"past_due", "suspended"})

_ACCOUNT_STATE_KEY = "account_state"
_DEFAULT_STATE = "active"


# States that mean "no live subscription". NOTE this is NOT sufficient on its own
# to close the account — see :func:`is_gated`. Credits already bought are the
# customer's property and remain spendable after a subscription ends.
EXPIRED_STATES = frozenset({"expired"})

_TRIAL_STATE = "trial"
_TRIAL_ENDS_KEY = "trial_ends_at"  # ISO-8601, written by the control plane at claim
_TRIAL_DAYS = 30

# Paths that stay reachable on a gated account, as (prefix, allowed_methods).
# ``None`` means every method. Without these the gate would be a trap: the customer
# could neither subscribe, sign out, nor retrieve their own data.
#   auth    — /me, logout, refresh, password change
#   mfa     — an MFA-enforced account must still finish authenticating
#   account — the subscribe page's own data (gating it would be circular)
#   stripe  — the checkout that resolves the situation
#   privacy — GDPR export AND deletion. Deliberate on both counts: withholding
#             someone's data because they stopped paying is hostile and a
#             portability problem, and blocking erasure would make a billing
#             state override a statutory right. Expiry withdraws the service,
#             never the data rights.
#   settings — READ-ONLY. The page renders so the account stays legible (what
#             plan, what's connected), but operational config cannot be changed
#             while there is no entitlement to operate.
#   credits — balance, packages, and PURCHASE. Non-negotiable: the commonest way
#             to become gated is running out of credits, so gating the endpoint
#             that sells credits would make the lockout unescapable. See the deny
#             list below for the one credits path that stays shut.
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_EXPIRED_ALLOWED: tuple[tuple[str, frozenset[str] | None], ...] = (
    ("/api/auth/", None),
    ("/api/mfa/", None),
    ("/api/account/", None),
    ("/api/stripe/", None),
    ("/api/privacy", None),
    ("/api/credits", frozenset({"GET", "HEAD", "OPTIONS", "POST"})),
    ("/api/settings", _SAFE_METHODS),
)

# Checked BEFORE the allowlist, so a broad prefix cannot accidentally open a
# narrow hole. ``/api/credits/admin/adjust`` mints credits directly: reachable
# from a gated account it would let an admin grant themselves back in, which is
# the gate defeating itself.
_EXPIRED_DENIED_PREFIXES = ("/api/credits/admin",)


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


def trial_ends_at(db: Session) -> datetime | None:
    """When this instance's trial lapses, or None if not recorded.

    Written by the control plane at claim time. Absent on legacy instances, which
    is treated as "unknown" — see :func:`trial_elapsed`.
    """
    raw = get_instance_config(db, _TRIAL_ENDS_KEY, default=None)
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        logger.warning("account: unparseable %s=%r — treating as unset", _TRIAL_ENDS_KEY, raw)
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def trial_elapsed(db: Session) -> bool:
    """Whether the trial window has run out.

    **Fails open when the end date is missing.** A trial with no recorded end date
    is our provisioning bug, not the customer's, and the cost of the two errors is
    asymmetric: failing closed locks a paying-intent customer out of a product they
    were invited to try, while failing open gives away some extra days. Logged so
    the misconfiguration is visible rather than silent.
    """
    ends = trial_ends_at(db)
    if ends is None:
        logger.warning(
            "account: trial state with no %s recorded — not gating (see provisioning)",
            _TRIAL_ENDS_KEY,
        )
        return False
    return datetime.now(UTC) >= ends


def account_credits(db: Session) -> int:
    """Spendable credits across the whole instance (expired lots excluded).

    Instance-wide rather than per-user: the *account* is what holds entitlement, so
    one teammate's empty balance must not lock out an account that still has credit.
    """
    from backend.services.credit_service import live_balance

    return sum(live_balance(db, user_id) for (user_id,) in db.query(User.id).all())


def is_gated(db: Session) -> bool:
    """Whether the account has no remaining right to use the product.

    Two independent triggers, matching how the two products actually end:

    * **Trial** — bounded by TIME. At day 30 it is over, whatever credits remain;
      the grant was to evaluate the product, not a balance to draw down forever.
    * **Subscription** — bounded by CREDITS. When a subscription lapses the customer
      keeps whatever they already paid for and may spend it down; only when the
      balance reaches zero with no live subscription is there nothing left to use.
      Cutting them off at lapse would be confiscating purchased credit.

    ``past_due``/``suspended`` are NOT gated here — they are billing problems on a
    live subscription, where spending is blocked at the credit chokepoint but access
    is deliberately preserved (S-01.4d).
    """
    state = account_state(db)
    if state == _TRIAL_STATE:
        return trial_elapsed(db)
    if state in EXPIRED_STATES:
        return account_credits(db) <= 0
    return False


def is_expired(db: Session) -> bool:
    """Backwards-compatible alias for :func:`is_gated`."""
    return is_gated(db)


def path_allowed_while_expired(path: str, method: str = "GET") -> bool:
    """Whether ``path``/``method`` stays reachable on a gated account.

    Deny rules are evaluated first so a broad allow-prefix cannot re-open a path
    that was deliberately shut.
    """
    if any(path.startswith(prefix) for prefix in _EXPIRED_DENIED_PREFIXES):
        return False
    upper = method.upper()
    for prefix, methods in _EXPIRED_ALLOWED:
        if path.startswith(prefix):
            return methods is None or upper in methods
    return False


def require_access(db: Session, path: str, method: str = "GET") -> None:
    """Raise :class:`AccountExpiredError` unless the request may proceed.

    Applied to EVERY authenticated request rather than per-router, so a new endpoint
    is gated by default instead of being quietly exempt — the failure mode of an
    opt-in gate is an unpaid account that still works through whatever route nobody
    remembered to annotate.
    """
    if path_allowed_while_expired(path, method):
        return
    if is_gated(db):
        raise AccountExpiredError(account_state(db))
