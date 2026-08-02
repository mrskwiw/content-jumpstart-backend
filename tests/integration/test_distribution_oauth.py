"""
Integration tests for Phase 10 OAuth connect flow + token refresh (foundation).

Covers the env-gated provider config, the authorize-URL start endpoint, and
`ensure_fresh_token` refreshing + persisting an expiring credential.
"""

from datetime import datetime, timedelta, timezone

import pytest

from backend.models import User
from backend.models.distribution import PlatformCredential
from backend.services.distribution import oauth, orchestrator
from backend.services.settings_service import decrypt_value
from backend.utils.auth import create_access_token, get_password_hash

PW = "Zx9!qWmp7Kt#"  # pragma: allowlist secret


def _make_user(db, email, uid):
    u = User(
        id=uid,
        email=email,
        hashed_password=get_password_hash(PW),
        full_name="Op",
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _hdr(user):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': user.id})}"}


def test_oauth_status_reflects_configured_platforms(client, monkeypatch):
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "li-id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "li-secret")
    monkeypatch.delenv("TIKTOK_CLIENT_KEY", raising=False)
    r = client.get("/api/distribution/oauth/status")
    assert r.status_code == 200
    body = r.json()
    assert "linkedin" in body["configured"]
    assert "tiktok" not in body["configured"]
    assert "stub" not in body["all"]


def test_oauth_start_unconfigured_platform_400(client, db_session, monkeypatch):
    u = _make_user(db_session, "oauth-unconf@example.com", "user-oauthunconf")
    monkeypatch.delenv("TIKTOK_CLIENT_KEY", raising=False)
    monkeypatch.delenv("TIKTOK_CLIENT_SECRET", raising=False)
    r = client.get("/api/distribution/oauth/tiktok/start", headers=_hdr(u))
    assert r.status_code == 400
    assert "not configured" in r.json()["detail"].lower()


def test_oauth_start_returns_authorize_url(client, db_session, monkeypatch):
    u = _make_user(db_session, "oauth-start@example.com", "user-oauthstart")
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "li-id-xyz")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "li-secret")
    monkeypatch.setenv("OAUTH_REDIRECT_BASE_URL", "https://app.example.com")
    r = client.get("/api/distribution/oauth/linkedin/start", headers=_hdr(u))
    assert r.status_code == 200, r.text
    url = r.json()["authorize_url"]
    assert url.startswith("https://www.linkedin.com/oauth/v2/authorization?")
    assert "client_id=li-id-xyz" in url
    assert "callback" in url  # redirect_uri present (url-encoded)


def test_pkce_pair_is_valid_s256():
    pair = oauth.make_pkce_pair()
    assert len(pair["verifier"]) >= 43
    assert "=" not in pair["challenge"]  # base64url, no padding


def test_ensure_fresh_token_refreshes_and_persists(db_session, monkeypatch):
    u = _make_user(db_session, "oauth-refresh@example.com", "user-oauthrefresh")
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "li-id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "li-secret")

    # A credential whose access token expired 1 minute ago but has a refresh token.
    cred = orchestrator.save_credential(
        db_session,
        u.id,
        "linkedin",
        "OLD-ACCESS",
        refresh_token="REFRESH-1",
        token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    calls = {}

    def fake_refresh(platform, refresh_token):
        calls["platform"] = platform
        calls["refresh_token"] = refresh_token
        return {
            "access_token": "NEW-ACCESS",
            "refresh_token": "REFRESH-2",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        }

    monkeypatch.setattr(oauth, "refresh_access_token", fake_refresh)

    token = oauth.ensure_fresh_token(db_session, cred)
    assert token == "NEW-ACCESS"
    assert calls == {"platform": "linkedin", "refresh_token": "REFRESH-1"}

    # Persisted (encrypted) and decryptable to the new values.
    reloaded = db_session.query(PlatformCredential).filter_by(id=cred.id).first()
    assert decrypt_value(reloaded.access_token) == "NEW-ACCESS"
    assert decrypt_value(reloaded.refresh_token) == "REFRESH-2"


def test_linkedin_person_publish_uses_oidc_userinfo(monkeypatch):
    """Regression: a personal LinkedIn publish (no account_ref) must resolve the
    author URN via the OIDC /userinfo endpoint (sub), matching the requested
    scopes — not the legacy /v2/me, which would 403."""
    import requests

    from backend.services.distribution.publishers import LinkedInPublisher

    calls = {}

    class _Resp:
        def __init__(self, status, payload=None, headers=None):
            self.status_code = status
            self._payload = payload or {}
            self.headers = headers or {}

        def json(self):
            return self._payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(self.status_code)

    def fake_get(url, **kw):
        calls["get_url"] = url
        return _Resp(200, {"sub": "MEMBER-123"})

    def fake_post(url, **kw):
        calls["post_url"] = url
        calls["author"] = kw["json"]["author"]
        return _Resp(201, {}, {"X-RestLi-Id": "urn:li:share:987"})

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)

    result = LinkedInPublisher(access_token="tok", account_ref=None).publish("hello")
    assert result.success, result.error
    assert calls["get_url"].endswith("/userinfo")  # not /me
    assert calls["author"] == "urn:li:person:MEMBER-123"


def test_ensure_fresh_token_refreshes_only_once_when_repeated(db_session, monkeypatch):
    """Regression: after one refresh advances the expiry, an immediately repeated
    call must NOT refresh again (the basis of the concurrency re-check)."""
    u = _make_user(db_session, "oauth-once@example.com", "user-oauthonce")
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "li-id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "li-secret")
    cred = orchestrator.save_credential(
        db_session,
        u.id,
        "linkedin",
        "OLD",
        refresh_token="R1",
        token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    count = {"n": 0}

    def fake_refresh(platform, refresh_token):
        count["n"] += 1
        return {
            "access_token": f"NEW-{count['n']}",
            "refresh_token": "R2",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        }

    monkeypatch.setattr(oauth, "refresh_access_token", fake_refresh)
    first = oauth.ensure_fresh_token(db_session, cred)
    second = oauth.ensure_fresh_token(db_session, cred)
    assert first == "NEW-1"
    assert second == "NEW-1"  # not refreshed again
    assert count["n"] == 1


def test_ensure_fresh_token_fails_closed_when_deactivated(db_session, monkeypatch):
    """A credential deactivated/deleted after load must not be refreshed or used —
    ensure_fresh_token returns '' (fail closed) rather than a token."""
    u = _make_user(db_session, "oauth-revoked@example.com", "user-oauthrevoked")
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "li-id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "li-secret")
    cred = orchestrator.save_credential(
        db_session,
        u.id,
        "linkedin",
        "OLD",
        refresh_token="R1",
        token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    cred.is_active = False
    db_session.commit()

    def boom(*a, **k):
        raise AssertionError("must not refresh a revoked credential")

    monkeypatch.setattr(oauth, "refresh_access_token", boom)
    assert oauth.ensure_fresh_token(db_session, cred) == ""


class _J:
    """Minimal requests-style response for the Threads token endpoints."""

    def __init__(self, status, payload=None, text=""):
        self.status_code = status
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def test_threads_exchange_upgrades_to_long_lived(monkeypatch):
    """The code exchange must upgrade the short-lived Threads token to a long-lived one and
    store the access token as its own refresh credential (Threads self-refreshes)."""
    import requests

    monkeypatch.setenv("THREADS_APP_ID", "th-id")
    monkeypatch.setenv("THREADS_APP_SECRET", "th-secret")

    def fake_post(url, **kw):  # token endpoint → short-lived
        return _J(200, {"access_token": "SHORT", "token_type": "bearer"})

    seen = {}

    def fake_get(url, **kw):  # th_exchange_token → long-lived
        seen["params"] = kw.get("params")
        return _J(200, {"access_token": "LONG", "token_type": "bearer", "expires_in": 5184000})

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "get", fake_get)

    token = oauth.exchange_code("threads", "code-1", redirect_uri="https://app.example.com/cb")
    assert token["access_token"] == "LONG"
    assert token["refresh_token"] == "LONG"  # self-refresh credential
    assert "expires_at" in token
    assert seen["params"]["grant_type"] == "th_exchange_token"
    assert seen["params"]["access_token"] == "SHORT"


def test_threads_exchange_connection_error_retries_then_succeeds(monkeypatch):
    """A connection error (request provably didn't reach Threads) is safe to replay — the
    retry absorbs it and the connect completes with a long-lived token."""
    import time

    import requests

    monkeypatch.setenv("THREADS_APP_ID", "th-id")
    monkeypatch.setenv("THREADS_APP_SECRET", "th-secret")
    monkeypatch.setattr(time, "sleep", lambda _s: None)
    calls = {"n": 0}

    def fake_get(url, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise requests.ConnectionError("connection refused")
        return _J(200, {"access_token": "LONG", "expires_in": 5184000})

    monkeypatch.setattr(requests, "post", lambda url, **kw: _J(200, {"access_token": "SHORT"}))
    monkeypatch.setattr(requests, "get", fake_get)
    token = oauth.exchange_code("threads", "code-1", redirect_uri="https://app.example.com/cb")
    assert token["access_token"] == "LONG"
    assert token["refresh_token"] == "LONG"
    assert calls["n"] == 2  # retried once after the connection error


def test_threads_exchange_persistent_connection_error_fails_closed(monkeypatch):
    """A persistent connection error retries the bounded number of times, then FAILS CLOSED."""
    import time

    import requests

    monkeypatch.setenv("THREADS_APP_ID", "th-id")
    monkeypatch.setenv("THREADS_APP_SECRET", "th-secret")
    monkeypatch.setattr(time, "sleep", lambda _s: None)
    calls = {"n": 0}

    def fake_get(url, **kw):
        calls["n"] += 1
        raise requests.ConnectionError("still down")

    monkeypatch.setattr(requests, "post", lambda url, **kw: _J(200, {"access_token": "SHORT"}))
    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(oauth.OAuthError):
        oauth.exchange_code("threads", "code-1", redirect_uri="https://app.example.com/cb")
    assert calls["n"] == oauth._THREADS_EXCHANGE_ATTEMPTS


def test_threads_exchange_5xx_fails_closed_without_replay(monkeypatch):
    """A 5xx reached Threads (it may have acted on the grant) → AMBIGUOUS, must NOT be replayed;
    fail closed after a single attempt rather than risk minting a second credential."""
    import requests

    monkeypatch.setenv("THREADS_APP_ID", "th-id")
    monkeypatch.setenv("THREADS_APP_SECRET", "th-secret")
    calls = {"n": 0}

    def fake_get(url, **kw):
        calls["n"] += 1
        return _J(503, text="threads down")

    monkeypatch.setattr(requests, "post", lambda url, **kw: _J(200, {"access_token": "SHORT"}))
    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(oauth.OAuthError):
        oauth.exchange_code("threads", "code-1", redirect_uri="https://app.example.com/cb")
    assert calls["n"] == 1  # server-side error is ambiguous → no replay


def test_threads_exchange_definitive_4xx_fails_immediately(monkeypatch):
    """A definitive 4xx (bad token/request) reached Threads and won't be helped by a replay."""
    import requests

    monkeypatch.setenv("THREADS_APP_ID", "th-id")
    monkeypatch.setenv("THREADS_APP_SECRET", "th-secret")
    calls = {"n": 0}

    def fake_get(url, **kw):
        calls["n"] += 1
        return _J(400, text="bad token")

    monkeypatch.setattr(requests, "post", lambda url, **kw: _J(200, {"access_token": "SHORT"}))
    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(oauth.OAuthError):
        oauth.exchange_code("threads", "code-1", redirect_uri="https://app.example.com/cb")
    assert calls["n"] == 1  # no retry on a definitive client error


def test_threads_refresh_uses_th_refresh_token(monkeypatch):
    import requests

    seen = {}

    def fake_get(url, **kw):
        seen["url"] = url
        seen["params"] = kw.get("params")
        return _J(200, {"access_token": "REFRESHED", "expires_in": 5184000})

    monkeypatch.setattr(requests, "get", fake_get)
    out = oauth.refresh_access_token("threads", "CURRENT-LONG")
    assert out["access_token"] == "REFRESHED"
    assert out["refresh_token"] == "REFRESHED"  # rotated to the new access token
    assert seen["url"].endswith("/refresh_access_token")
    assert seen["params"]["grant_type"] == "th_refresh_token"
    assert seen["params"]["access_token"] == "CURRENT-LONG"


def test_threads_ensure_fresh_token_self_refreshes_and_persists(db_session, monkeypatch):
    """End-to-end: an expiring Threads credential is refreshed via the self-refresh path and
    both the access token AND its refresh credential are rotated + persisted."""
    import requests

    u = _make_user(db_session, "threads-refresh@example.com", "user-threadsrefresh")
    monkeypatch.setenv("THREADS_APP_ID", "th-id")
    monkeypatch.setenv("THREADS_APP_SECRET", "th-secret")
    cred = orchestrator.save_credential(
        db_session,
        u.id,
        "threads",
        "OLD-LONG",
        refresh_token="OLD-LONG",  # Threads' refresh credential IS the access token
        account_ref="17841400000",
        token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    def fake_get(url, **kw):
        return _J(200, {"access_token": "NEW-LONG", "expires_in": 5184000})

    monkeypatch.setattr(requests, "get", fake_get)
    token = oauth.ensure_fresh_token(db_session, cred)
    assert token == "NEW-LONG"

    reloaded = db_session.query(PlatformCredential).filter_by(id=cred.id).first()
    assert decrypt_value(reloaded.access_token) == "NEW-LONG"
    assert decrypt_value(reloaded.refresh_token) == "NEW-LONG"  # rotated


def test_threads_ensure_fresh_token_recovers_without_stored_refresh(db_session, monkeypatch):
    """A Threads credential with NO stored refresh token still self-refreshes using its access
    token (th_refresh_token), so a fallback/manual-API credential isn't stranded."""
    import requests

    u = _make_user(db_session, "threads-noref@example.com", "user-threadsnoref")
    monkeypatch.setenv("THREADS_APP_ID", "th-id")
    monkeypatch.setenv("THREADS_APP_SECRET", "th-secret")
    cred = orchestrator.save_credential(
        db_session,
        u.id,
        "threads",
        "OLD-LONG",
        account_ref="tid",  # no refresh_token passed → stored as None
        token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    assert cred.refresh_token is None

    def fake_get(url, **kw):
        # Refresh must use the access token itself as the th_refresh_token credential.
        assert kw["params"]["access_token"] == "OLD-LONG"
        return _J(200, {"access_token": "NEW-LONG", "expires_in": 5184000})

    monkeypatch.setattr(requests, "get", fake_get)
    token = oauth.ensure_fresh_token(db_session, cred)
    assert token == "NEW-LONG"
    reloaded = db_session.query(PlatformCredential).filter_by(id=cred.id).first()
    assert decrypt_value(reloaded.access_token) == "NEW-LONG"
    assert decrypt_value(reloaded.refresh_token) == "NEW-LONG"  # now populated for next time


def test_ensure_fresh_token_noop_when_not_expiring(db_session, monkeypatch):
    u = _make_user(db_session, "oauth-valid@example.com", "user-oauthvalid")
    cred = orchestrator.save_credential(
        db_session,
        u.id,
        "linkedin",
        "STILL-GOOD",
        refresh_token="REFRESH-1",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
    )

    def boom(*a, **k):  # must not be called
        raise AssertionError("refresh should not run for a fresh token")

    monkeypatch.setattr(oauth, "refresh_access_token", boom)
    assert oauth.ensure_fresh_token(db_session, cred) == "STILL-GOOD"
