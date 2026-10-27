"""Error reporting to Sentry (GAP-BE-02).

Opt-in per instance: nothing is initialised, and nothing leaves the process, unless
``SENTRY_DSN`` is set. Every customer runs as its own Render service, so events are
tagged with the instance (``server_name``) and the deployed commit (``release``) —
both taken from variables Render sets automatically.

PII collection stays off (``send_default_pii=False``): requests on this app carry
users' emails and client briefs, and with it off the SDK's AI integrations don't
attach prompts either.

Environment:
    SENTRY_DSN                 enables reporting (unset or blank → disabled)
    SENTRY_ENVIRONMENT         defaults to ENVIRONMENT, then "production"
    SENTRY_RELEASE             defaults to RENDER_GIT_COMMIT
    SENTRY_TRACES_SAMPLE_RATE  0.0–1.0, default 0.0 (errors only, no tracing)
"""

import math
import os
from typing import Optional

import sentry_sdk

from backend.utils.logger import logger


def _traces_sample_rate() -> float:
    """Parse SENTRY_TRACES_SAMPLE_RATE; anything invalid or out of range means 0.0."""
    raw = os.getenv("SENTRY_TRACES_SAMPLE_RATE", "").strip()
    if not raw:
        return 0.0
    try:
        rate = float(raw)
    except ValueError:
        rate = math.nan
    if math.isnan(rate) or not 0.0 <= rate <= 1.0:
        logger.warning(
            f"SENTRY_TRACES_SAMPLE_RATE={raw!r} is not a number in [0, 1]; tracing disabled."
        )
        return 0.0
    return rate


def init_sentry() -> bool:
    """Initialise Sentry if ``SENTRY_DSN`` is set.

    Never raises: a bad configuration is logged and reporting stays off, so
    observability can't take the app down at startup.

    Returns:
        True if Sentry was initialised, False if it is disabled or failed to start.
    """
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return False

    release: Optional[str] = os.getenv("SENTRY_RELEASE") or os.getenv("RENDER_GIT_COMMIT")
    environment = os.getenv("SENTRY_ENVIRONMENT") or os.getenv("ENVIRONMENT") or "production"
    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            server_name=os.getenv("RENDER_SERVICE_NAME") or None,
            send_default_pii=False,
            traces_sample_rate=_traces_sample_rate(),
        )
    except Exception as exc:  # noqa: BLE001 - startup must survive a bad DSN
        logger.error(f"Sentry initialisation failed; error reporting disabled: {exc}")
        return False

    logger.info(f"Sentry error reporting enabled (environment={environment}).")
    return True
