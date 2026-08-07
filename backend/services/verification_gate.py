"""GAP-AUTH-02 — the effective email-verification gate.

`settings.REQUIRE_EMAIL_VERIFICATION` is the operator's intent; this module resolves it
into what the instance may actually enforce. Enforcement blocks *every* authenticated
request, so demanding a verification email on an instance with no outbound transport
would lock out every unverified account with no recovery short of database access —
across a fleet of per-customer instances that is a bricking hazard, not an edge case.
"""

from functools import lru_cache

from backend.config import settings
from backend.utils.logger import logger


@lru_cache(maxsize=1)
def email_delivery_available() -> bool:
    """Whether this instance has a real outbound email transport (Resend or SMTP).

    Transport selection is environment-driven and therefore constant for the process
    lifetime, so the answer is cached — which also keeps the warning below to one line
    per boot instead of one per request. Call `email_delivery_available.cache_clear()`
    after changing the transport environment (tests do).
    """
    try:
        from agent.email_system import EmailSystem

        available = EmailSystem().can_deliver()
    except Exception:  # pragma: no cover - defensive; never fail a request on this
        logger.exception("Could not resolve the email transport; treating it as unavailable")
        return False

    if not available:
        logger.warning(
            "EMAIL: no outbound transport configured (RESEND_API_KEY / SMTP_USER+SMTP_PASSWORD "
            "unset, or EMAIL_PROVIDER=log) — verification emails are log-only."
        )
    return available


# Set once the "configured but unenforceable" warning has been emitted; the gate is
# consulted on every authenticated request and this must not become per-request spam.
_warned_unenforceable = False


def email_verification_enforced() -> bool:
    """True when unverified accounts should be refused (403).

    Fail-safe by design: an instance that cannot send a verification email does not get
    to require one. Configure a transport to turn the gate on.
    """
    global _warned_unenforceable

    if not settings.REQUIRE_EMAIL_VERIFICATION:
        return False
    if not email_delivery_available():
        if _warned_unenforceable:
            return False
        _warned_unenforceable = True
        logger.warning(
            "AUTH: REQUIRE_EMAIL_VERIFICATION is set but this instance cannot send email — "
            "the verification gate is NOT being enforced. Configure RESEND_API_KEY or "
            "SMTP_USER/SMTP_PASSWORD to enforce it."
        )
        return False
    return True
