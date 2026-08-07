"""GAP-AUTH-02 — the email-verification gate.

`settings.REQUIRE_EMAIL_VERIFICATION` is authoritative: if it is on, unverified accounts
are refused, full stop. An earlier revision also stood the gate down on instances with no
outbound email transport, to avoid bricking a fleet instance that couldn't send the link.
That was wrong — it let the most likely rollout misconfiguration silently disable an auth
control. The lockout hazard is handled where it actually lives instead: accounts that
predate the feature were grandfathered verified, and operator-provisioned accounts
(admin-seed, admin-created) are stamped verified at creation, so only self-registered
addresses are ever gated. The remaining risk — enforcing verification on an instance that
can't send the link — is caught by `check_startup_configuration()`, which refuses to boot
rather than letting either failure mode happen quietly (BUGS.md Decision #236).
"""

from backend.config import settings
from backend.utils.logger import logger


def email_delivery_available() -> bool:
    """Whether this instance has a real outbound email transport (Resend or SMTP).

    Configuration only — `EmailSystem` resolves its transport from the environment, so
    this makes no network call and says nothing about provider health.
    """
    try:
        from agent.email_system import EmailSystem

        return EmailSystem().can_deliver()
    except Exception:  # pragma: no cover - defensive; a broken import is not a verdict
        logger.exception("Could not resolve the email transport")
        return False


def email_verification_enforced() -> bool:
    """True when unverified accounts should be refused (403)."""
    return bool(settings.REQUIRE_EMAIL_VERIFICATION)


_MISCONFIGURED = (
    "AUTH: REQUIRE_EMAIL_VERIFICATION is on but this instance has NO outbound email "
    "transport (RESEND_API_KEY / SMTP_USER+SMTP_PASSWORD unset, or EMAIL_PROVIDER=log). "
    "Verification links cannot be delivered, so accounts that need to verify could never "
    "sign in. Configure a transport, or set REQUIRE_EMAIL_VERIFICATION=false."
)


def check_startup_configuration(debug_mode: bool = False) -> bool:
    """Refuse to serve a deployment that requires verification it cannot deliver.

    Two adversarial reviews argued opposite sides of this: deriving enforcement from
    transport health fails OPEN (a missing key silently disables an auth control), and
    enforcing regardless fails CLOSED (a missing key silently strands unverified users).
    Both are real, and both recommendations converge here — make the misconfiguration
    undeployable instead of choosing which way it breaks. The pairing is invalid, so it
    raises at boot; on Render a failed boot keeps the previous deploy serving, which makes
    this the loudest and least destructive of the three. Recorded as BUGS.md Decision #236.

    Returns True when the invalid pairing was detected and tolerated (DEBUG_MODE only,
    where refusing to start would just block local work).
    """
    if not email_verification_enforced() or email_delivery_available():
        return False

    if debug_mode:
        logger.error(f"{_MISCONFIGURED} (DEBUG_MODE: starting anyway)")
        return True

    raise RuntimeError(_MISCONFIGURED)
