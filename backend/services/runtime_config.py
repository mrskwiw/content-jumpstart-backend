"""Runtime instance-config resolvers (S-01.4e) — settings-with-env fallback.

Building blocks for making CORS origins + the OAuth redirect base
runtime-configurable via the ``instance_config`` singleton (S-01.4a), so the
control plane's custom-domain promotion doesn't require a redeploy.

These are **pure resolvers with an env fallback**: when ``instance_config`` is
empty (every current instance, and any pre-claim pool slot) they return exactly
what the env-based code returns today, so existing behavior is unchanged.

NOTE: the OAuth-redirect-base resolver is WIRED into the OAuth legs
(``redirect_uri_for``/``build_authorize_url``/``exchange_code`` + the distribution
router, commit efcdefc) — safe because that value goes to the trusted provider and
its source is instance_config/env, never user input.

``resolved_cors_origins`` is intentionally NOT wired (BUGS.md Decision #210): CORS runs
on the env ``CORS_ORIGINS`` list, and a control-plane custom-domain promotion adds the
new origin to that env + redeploys the instance. Runtime instance_config-driven CORS
(a custom middleware) was declined as an unneeded security surface — the spec sanctions
the redeploy path. This resolver stays as a tested building block should that
enhancement ever be wanted; it is not dead by accident.
"""

from __future__ import annotations

import os
from collections.abc import Iterable

from sqlalchemy.orm import Session

from backend.services.settings_service import get_instance_config

_CORS_KEY = "cors_origins"  # CSV of extra allowed origins
_OAUTH_BASE_KEY = "oauth_redirect_base"  # canonical base URL for OAuth callbacks


def resolved_cors_origins(db: Session, env_origins: Iterable[str]) -> list[str]:
    """Env origins unioned with any ``instance_config`` ``cors_origins`` (CSV).

    Order-preserving, de-duplicated. Env origins always remain allowed; the
    control plane can ADD the custom domain at runtime without dropping the
    baked-in wildcard subdomain.
    """
    origins: list[str] = []
    for origin in env_origins:
        origin = origin.strip()
        if origin and origin not in origins:
            origins.append(origin)
    extra = get_instance_config(db, _CORS_KEY)
    if extra:
        for origin in extra.split(","):
            origin = origin.strip()
            if origin and origin not in origins:
                origins.append(origin)
    return origins


def resolved_oauth_redirect_base(db: Session) -> str:
    """Instance-config OAuth base if set, else the ``OAUTH_REDIRECT_BASE_URL`` env.

    Returns the base with any trailing slash stripped (matching the current
    env-based helper). Empty string when neither is set (callers raise, as today).
    """
    value = get_instance_config(db, _OAUTH_BASE_KEY)
    if value:
        return value.rstrip("/")
    return os.getenv("OAUTH_REDIRECT_BASE_URL", "").rstrip("/")
