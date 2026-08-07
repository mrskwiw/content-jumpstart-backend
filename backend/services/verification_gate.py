"""GAP-AUTH-02 — the email-verification gate.

`settings.REQUIRE_EMAIL_VERIFICATION` is authoritative: if it is on, unverified accounts
are refused, full stop. An earlier revision also stood the gate down on instances with no
outbound email transport, to avoid bricking a fleet instance that couldn't send the link.
That was wrong — it let the most likely rollout misconfiguration silently disable an auth
control. The lockout hazard is handled where it actually lives instead: accounts that
predate the feature were grandfathered verified, and operator-provisioned accounts
(admin-seed, admin-created) are stamped verified at creation, so only self-registered
addresses are ever gated. What remains is `warn_if_unenforceable()`, a loud boot-time
check so an operator who enables the gate without a transport hears about it.
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


def warn_if_unenforceable() -> bool:
    """Boot-time check: the gate is on but this instance cannot send the link.

    Called once from the app lifespan. Returns True when it warned, so the caller (and
    tests) can assert on it. It never changes enforcement — an operator who genuinely
    can't send email opts out explicitly with REQUIRE_EMAIL_VERIFICATION=false.
    """
    if not email_verification_enforced() or email_delivery_available():
        return False

    logger.error(
        "AUTH: REQUIRE_EMAIL_VERIFICATION is on but this instance has NO outbound email "
        "transport (RESEND_API_KEY / SMTP_USER+SMTP_PASSWORD unset, or EMAIL_PROVIDER=log). "
        "Verification links cannot be delivered, so self-registered accounts will be unable "
        "to sign in. Configure a transport, or set REQUIRE_EMAIL_VERIFICATION=false."
    )
    return True
