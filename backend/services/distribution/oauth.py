"""
OAuth 2.0 infrastructure for Phase 10 distribution.

One declarative `OAuthProvider` per platform, driven entirely by environment
variables so a platform "lights up" the moment its client id/secret are set — no
code change. Provides the three legs of the flow plus token refresh:

    build_authorize_url()  -> where to send the user to grant access
    exchange_code()        -> callback code  -> access/refresh tokens
    refresh_access_token() -> refresh token  -> a fresh access token
    ensure_fresh_token()   -> refresh-if-expiring, persisted, for the worker path

Platform quirks (PKCE, HTTP-Basic vs body client auth, Facebook's long-lived
token exchange, Google's offline access) are captured as config flags rather than
bespoke code paths. Endpoints reflect each platform's current public OAuth docs;
scopes are the minimum needed to publish + read insights.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import requests
from sqlalchemy.orm import Session

from backend.services.runtime_config import resolved_oauth_redirect_base

logger = logging.getLogger(__name__)

# Refresh a token this long before it actually expires, to avoid a race where a
# token validated as fresh expires mid-request.
_REFRESH_SKEW = timedelta(minutes=5)
_HTTP_TIMEOUT = 30


@dataclass(frozen=True)
class OAuthProvider:
    """Declarative OAuth config for one platform."""

    platform: str
    authorize_url: str
    token_url: str
    scopes: List[str]
    # Env var names holding the app credentials. A platform is "configured" iff
    # both resolve to non-empty values.
    client_id_env: str
    client_secret_env: str
    # "basic" -> credentials in the HTTP Basic header; "body" -> in the form body.
    client_auth: str = "body"
    # Twitter/X requires PKCE; Google/others accept it harmlessly but we only send
    # it when required to keep provider payloads minimal.
    use_pkce: bool = False
    # Extra static params merged into the authorize request (e.g. Google's
    # access_type=offline&prompt=consent to actually receive a refresh token).
    extra_authorize_params: Dict[str, str] = field(default_factory=dict)
    # Some providers (Facebook/Instagram) don't issue refresh tokens; instead an
    # access token is exchanged for a long-lived one. When False, ensure_fresh_token
    # will not attempt a refresh-token grant.
    supports_refresh: bool = True

    @property
    def client_id(self) -> Optional[str]:
        return os.getenv(self.client_id_env) or None

    @property
    def client_secret(self) -> Optional[str]:
        return os.getenv(self.client_secret_env) or None

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)


# ── Provider registry ──────────────────────────────────────────────────────────
# Facebook and Instagram share one Meta app (same id/secret), hence the shared
# FACEBOOK_APP_ID/SECRET env vars with platform-specific scopes.
PROVIDERS: Dict[str, OAuthProvider] = {
    "linkedin": OAuthProvider(  # nosec B106 - token_url is a public OAuth endpoint, not a secret
        platform="linkedin",
        authorize_url="https://www.linkedin.com/oauth/v2/authorization",
        token_url="https://www.linkedin.com/oauth/v2/accessToken",
        scopes=["openid", "profile", "w_member_social"],
        client_id_env="LINKEDIN_CLIENT_ID",
        client_secret_env="LINKEDIN_CLIENT_SECRET",  # pragma: allowlist secret
        client_auth="body",
    ),
    "twitter": OAuthProvider(  # nosec B106 - token_url is a public OAuth endpoint, not a secret
        platform="twitter",
        authorize_url="https://twitter.com/i/oauth2/authorize",
        token_url="https://api.twitter.com/2/oauth2/token",
        scopes=["tweet.read", "tweet.write", "users.read", "offline.access"],
        client_id_env="TWITTER_CLIENT_ID",
        client_secret_env="TWITTER_CLIENT_SECRET",  # pragma: allowlist secret
        client_auth="basic",
        use_pkce=True,
    ),
    "facebook": OAuthProvider(  # nosec B106 - token_url is a public OAuth endpoint, not a secret
        platform="facebook",
        authorize_url="https://www.facebook.com/v19.0/dialog/oauth",
        token_url="https://graph.facebook.com/v19.0/oauth/access_token",
        scopes=["pages_manage_posts", "pages_read_engagement", "pages_show_list"],
        client_id_env="FACEBOOK_APP_ID",
        client_secret_env="FACEBOOK_APP_SECRET",  # pragma: allowlist secret
        client_auth="body",
        supports_refresh=False,  # long-lived token exchange, not refresh grants
    ),
    "instagram": OAuthProvider(  # nosec B106 - token_url is a public OAuth endpoint, not a secret
        platform="instagram",
        authorize_url="https://www.facebook.com/v19.0/dialog/oauth",
        token_url="https://graph.facebook.com/v19.0/oauth/access_token",
        scopes=[
            "instagram_basic",
            "instagram_content_publish",
            "pages_show_list",
            "business_management",
        ],
        client_id_env="FACEBOOK_APP_ID",
        client_secret_env="FACEBOOK_APP_SECRET",  # pragma: allowlist secret
        client_auth="body",
        supports_refresh=False,
    ),
    "tiktok": OAuthProvider(  # nosec B106 - token_url is a public OAuth endpoint, not a secret
        platform="tiktok",
        authorize_url="https://www.tiktok.com/v2/auth/authorize/",
        token_url="https://open.tiktokapis.com/v2/oauth/token/",
        scopes=["user.info.basic", "video.publish", "video.upload"],
        client_id_env="TIKTOK_CLIENT_KEY",
        client_secret_env="TIKTOK_CLIENT_SECRET",  # pragma: allowlist secret
        client_auth="body",
    ),
    "youtube": OAuthProvider(  # nosec B106 - token_url is a public OAuth endpoint, not a secret
        platform="youtube",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
        client_id_env="YOUTUBE_CLIENT_ID",
        client_secret_env="YOUTUBE_CLIENT_SECRET",  # pragma: allowlist secret
        client_auth="body",
        extra_authorize_params={"access_type": "offline", "prompt": "consent"},
    ),
    "threads": OAuthProvider(  # nosec B106 - token_url is a public OAuth endpoint, not a secret
        platform="threads",
        authorize_url="https://threads.net/oauth/authorize",
        token_url="https://graph.threads.net/oauth/access_token",
        scopes=["threads_basic", "threads_content_publish"],
        client_id_env="THREADS_APP_ID",
        client_secret_env="THREADS_APP_SECRET",  # pragma: allowlist secret
        client_auth="body",
        # Threads issues short-lived tokens upgraded to long-lived (~60d) ones via a
        # th_exchange_token grant rather than a standard refresh grant — mirror Meta.
        supports_refresh=False,
    ),
    "pinterest": OAuthProvider(  # nosec B106 - token_url is a public OAuth endpoint, not a secret
        platform="pinterest",
        authorize_url="https://www.pinterest.com/oauth/",
        token_url="https://api.pinterest.com/v5/oauth/token",
        scopes=["boards:read", "pins:read", "pins:write"],
        client_id_env="PINTEREST_APP_ID",
        client_secret_env="PINTEREST_APP_SECRET",  # pragma: allowlist secret
        client_auth="basic",  # Pinterest v5 token endpoint uses HTTP Basic app auth
    ),
}


class OAuthError(RuntimeError):
    """Raised when an OAuth exchange/refresh fails or a platform is misconfigured."""


def get_provider(platform: str) -> OAuthProvider:
    provider = PROVIDERS.get(platform)
    if provider is None:
        raise OAuthError(f"No OAuth provider for platform '{platform}'")
    return provider


def configured_platforms() -> List[str]:
    """Platforms whose app credentials are present in the environment."""
    return [p for p, prov in PROVIDERS.items() if prov.is_configured]


def redirect_uri_for(platform: str, db: Session | None = None) -> str:
    """Public callback URL for a platform.

    Derived from the OAuth redirect base so a deploy only needs the base set, e.g.
    https://app.customer.com -> https://app.customer.com/api/distribution/oauth/<platform>/callback
    Per-platform override supported via <PLATFORM>_REDIRECT_URI for odd cases.

    When ``db`` is supplied, the base is resolved via ``instance_config`` (the control
    plane's custom-domain promotion, S-01.4e) with an env fallback; without ``db`` it
    is exactly the env value (unchanged behavior). Both OAuth legs (authorize +
    token-exchange) MUST pass the same ``db`` so the redirect_uri matches — the
    provider rejects a mismatch.
    """
    override = os.getenv(f"{platform.upper()}_REDIRECT_URI")
    if override:
        return override
    base = (
        resolved_oauth_redirect_base(db)
        if db is not None
        else os.getenv("OAUTH_REDIRECT_BASE_URL", "").rstrip("/")
    )
    if not base:
        raise OAuthError(
            "OAUTH_REDIRECT_BASE_URL is not set — required to build OAuth callback URLs."
        )
    return f"{base}/api/distribution/oauth/{platform}/callback"


# ── PKCE helpers ────────────────────────────────────────────────────────────────


def make_pkce_pair() -> Dict[str, str]:
    """Return {'verifier', 'challenge'} for a PKCE (S256) flow."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return {"verifier": verifier, "challenge": challenge}


# ── Flow legs ───────────────────────────────────────────────────────────────────


def build_authorize_url(
    platform: str,
    state: str,
    *,
    code_challenge: Optional[str] = None,
    db: Session | None = None,
    redirect_uri: Optional[str] = None,
) -> str:
    """Build the URL to redirect a user to for granting access.

    ``redirect_uri`` pins the exact callback URL (stored in ``state`` so the exchange
    leg reuses the identical value); when omitted it is resolved from ``db``/env.
    """
    provider = get_provider(platform)
    if not provider.is_configured:
        raise OAuthError(
            f"{platform} is not configured — set {provider.client_id_env} and "
            f"{provider.client_secret_env}."
        )
    params = {
        "response_type": "code",
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri or redirect_uri_for(platform, db),
        "scope": " ".join(provider.scopes),
        "state": state,
        **provider.extra_authorize_params,
    }
    if provider.use_pkce:
        if not code_challenge:
            raise OAuthError(f"{platform} requires PKCE but no code_challenge was provided")
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"
    query = "&".join(f"{k}={requests.utils.quote(str(v), safe='')}" for k, v in params.items())
    return f"{provider.authorize_url}?{query}"


def _post_token(provider: OAuthProvider, data: Dict[str, str]) -> Dict:
    """POST to the token endpoint applying the provider's client-auth style."""
    headers = {"Accept": "application/json"}
    auth = None
    if provider.client_auth == "basic":
        auth = (provider.client_id, provider.client_secret)
    else:
        data = {**data, "client_id": provider.client_id, "client_secret": provider.client_secret}
    try:
        resp = requests.post(
            provider.token_url, data=data, headers=headers, auth=auth, timeout=_HTTP_TIMEOUT
        )
    except requests.RequestException as e:
        raise OAuthError(f"{provider.platform} token request failed: {e}") from e
    if resp.status_code >= 400:
        raise OAuthError(
            f"{provider.platform} token endpoint {resp.status_code}: {resp.text[:300]}"
        )
    try:
        return resp.json()
    except ValueError as e:
        raise OAuthError(
            f"{provider.platform} token response was not JSON: {resp.text[:200]}"
        ) from e


def _normalize_token(payload: Dict) -> Dict:
    """Map a provider token payload to our stored shape.

    Returns {access_token, refresh_token?, expires_at?}. Facebook returns
    expires_in for long-lived tokens; others use expires_in for the access token.
    """
    access = payload.get("access_token")
    if not access:
        raise OAuthError(f"Token response missing access_token: {list(payload.keys())}")
    out: Dict[str, object] = {"access_token": access}
    if payload.get("refresh_token"):
        out["refresh_token"] = payload["refresh_token"]
    expires_in = payload.get("expires_in")
    if expires_in:
        try:
            out["expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        except (TypeError, ValueError):
            pass
    return out


def exchange_code(
    platform: str,
    code: str,
    *,
    code_verifier: Optional[str] = None,
    db: Session | None = None,
    redirect_uri: Optional[str] = None,
) -> Dict:
    """Exchange an authorization code for tokens. Returns the normalized token dict.

    ``redirect_uri`` MUST be the exact value used at authorize time (the caller pins
    it in the signed ``state`` and passes it back here) — OAuth rejects a mismatch. If
    omitted it is resolved from ``db``/env, which only matches when the base is stable.
    """
    provider = get_provider(platform)
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri or redirect_uri_for(platform, db),
    }
    if provider.use_pkce:
        if not code_verifier:
            raise OAuthError(f"{platform} requires PKCE code_verifier for exchange")
        data["code_verifier"] = code_verifier
    token = _normalize_token(_post_token(provider, data))

    # Facebook/Instagram: immediately upgrade the short-lived token to a
    # long-lived (~60 day) one, since they have no refresh grant.
    if not provider.supports_refresh and platform in ("facebook", "instagram"):
        token = _facebook_long_lived(provider, token)
    return token


def _facebook_long_lived(provider: OAuthProvider, token: Dict) -> Dict:
    """Exchange a short-lived FB token for a long-lived one (~60 days)."""
    try:
        resp = requests.get(
            provider.token_url,
            params={
                "grant_type": "fb_exchange_token",
                "client_id": provider.client_id,
                "client_secret": provider.client_secret,
                "fb_exchange_token": token["access_token"],
            },
            timeout=_HTTP_TIMEOUT,
        )
        if resp.status_code < 400:
            return _normalize_token(resp.json())
    except requests.RequestException as e:
        logger.warning("Facebook long-lived token exchange failed: %s", e)
    return token  # fall back to the short-lived token


def refresh_access_token(platform: str, refresh_token: str) -> Dict:
    """Use a refresh token to obtain a new access token. Normalized token dict."""
    provider = get_provider(platform)
    if not provider.supports_refresh:
        raise OAuthError(f"{platform} does not support refresh-token grants")
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    return _normalize_token(_post_token(provider, data))


def ensure_fresh_token(db: Session, cred) -> str:
    """Return a valid, decrypted access token for a PlatformCredential, refreshing
    and persisting it first if it is expired/expiring and a refresh path exists.

    Falls back to the current access token when refresh is impossible (no refresh
    token, provider without refresh grants, or the platform isn't OAuth-configured)
    — the publisher will then surface any auth error from the live call.
    """
    # Imported here to avoid a circular import (settings_service ← models ← db).
    from backend.services.settings_service import decrypt_value, encrypt_value

    access = decrypt_value(cred.access_token) if cred.access_token else ""
    expires_at = cred.token_expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    needs_refresh = (
        expires_at is not None and expires_at <= datetime.now(timezone.utc) + _REFRESH_SKEW
    )
    if not needs_refresh:
        return access

    provider = PROVIDERS.get(cred.platform)
    if provider is None or not provider.supports_refresh or not provider.is_configured:
        return access
    if not cred.refresh_token:
        return access

    # Serialize refresh per credential so two concurrent callers (e.g. a
    # user-triggered publish_now racing a scheduler tick) can't both refresh the
    # same token and clobber each other — critical when the provider rotates
    # refresh tokens, which would otherwise strand the account. On Postgres we
    # take a row lock and re-check under it; on SQLite (dev/tests) the single
    # writer makes locking unnecessary.
    from backend.models.distribution import PlatformCredential

    is_pg = db.bind is not None and db.bind.dialect.name == "postgresql"
    # Re-read the credential requiring is_active — so a concurrent disconnect /
    # deactivation is honoured (fail closed) instead of refreshing a revoked
    # token. On Postgres also take a row lock + populate_existing to serialize
    # concurrent refreshers and read the committed row, not stale session state.
    q = db.query(PlatformCredential).filter(
        PlatformCredential.id == cred.id, PlatformCredential.is_active.is_(True)
    )
    if is_pg:
        q = q.populate_existing().with_for_update()
    locked = q.first()
    if locked is None:
        # Deleted or deactivated (possibly concurrently) — never fall back to the
        # stale ORM object; fail closed so the publish surfaces an auth failure.
        # No row matched, so the SELECT ... FOR UPDATE locked nothing and there is
        # nothing to release — do NOT rollback (it would discard the caller's
        # unrelated pending writes in this session).
        return ""

    exp = locked.token_expires_at
    if exp is not None and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp is not None and exp > datetime.now(timezone.utc) + _REFRESH_SKEW:
        # Another worker refreshed while we waited for the lock — use theirs.
        if is_pg:
            db.commit()  # release the lock
        return decrypt_value(locked.access_token) if locked.access_token else access

    refresh = decrypt_value(locked.refresh_token) if locked.refresh_token else ""
    if not refresh:
        if is_pg:
            db.commit()  # release the lock
        return access

    try:
        token = refresh_access_token(cred.platform, refresh)
    except OAuthError as e:
        logger.warning("Token refresh failed for %s cred %s: %s", cred.platform, cred.id, e)
        if is_pg:
            db.commit()  # release the lock
        return access

    locked.access_token = encrypt_value(token["access_token"])
    if token.get("refresh_token"):
        locked.refresh_token = encrypt_value(token["refresh_token"])
    if token.get("expires_at"):
        locked.token_expires_at = token["expires_at"]
    db.commit()  # persists and releases the lock
    logger.info("Refreshed %s access token for cred %s", cred.platform, cred.id)
    return token["access_token"]
