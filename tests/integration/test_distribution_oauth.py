"""
Integration tests for Phase 10 OAuth connect flow + token refresh (foundation).

Covers the env-gated provider config, the authorize-URL start endpoint, and
`ensure_fresh_token` refreshing + persisting an expiring credential.
"""

from datetime import datetime, timedelta, timezone

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
