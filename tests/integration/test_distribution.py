"""
Integration tests for Phase 10 — Multi-Platform Distribution.

Exercises the full schedule → publish → track loop via the stub publisher, the
cron `process-due` worker, per-user ownership, and the fail-closed behaviour for
a not-yet-implemented platform.
"""

import pytest

from backend.models import User
from backend.utils.auth import get_password_hash, create_access_token

PW = "Zx9!qWmp7Kt#"  # pragma: allowlist secret


def _make_user(db, email, uid, is_superuser=False):
    u = User(
        id=uid,
        email=email,
        hashed_password=get_password_hash(PW),
        full_name="Op",
        is_active=True,
        is_superuser=is_superuser,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _hdr(user):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': user.id})}"}


def test_connect_list_and_delete_credential(client, db_session):
    u = _make_user(db_session, "dist-cred@example.com", "user-distcred")
    r = client.post(
        "/api/distribution/credentials",
        json={"platform": "linkedin", "access_token": "secret-token-123", "display_name": "My LI"},
        headers=_hdr(u),
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    # Token is never returned.
    assert "access_token" not in r.json()

    lst = client.get("/api/distribution/credentials", headers=_hdr(u))
    assert lst.status_code == 200
    assert any(c["id"] == cid for c in lst.json())

    d = client.delete(f"/api/distribution/credentials/{cid}", headers=_hdr(u))
    assert d.status_code == 200


class _FakeResp:
    def __init__(self, status, payload=None, text=""):
        self.status_code = status
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def test_connect_bluesky_rejects_bad_credential_before_persisting(client, db_session, monkeypatch):
    """Bluesky (app-password) is verified via a real createSession before persisting — a bad
    app password is rejected at connect time (400) and nothing is stored, rather than creating
    a false 'connected' state that only fails at publish."""
    import requests

    monkeypatch.delenv("DISTRIBUTION_DRY_RUN", raising=False)  # force the real verifier
    monkeypatch.setattr(requests, "post", lambda *a, **k: _FakeResp(401, text="bad app password"))
    u = _make_user(db_session, "bsky-bad@example.com", "user-bskybad")
    r = client.post(
        "/api/distribution/credentials",
        json={"platform": "bluesky", "access_token": "wrong", "account_ref": "me.bsky.social"},
        headers=_hdr(u),
    )
    assert r.status_code == 400, r.text
    assert "401" in r.json()["detail"]
    # Nothing persisted.
    lst = client.get("/api/distribution/credentials", headers=_hdr(u)).json()
    assert all(c["platform"] != "bluesky" for c in lst)


def test_connect_bluesky_transient_failure_is_502_not_400(client, db_session, monkeypatch):
    """A provider outage during connect verification must NOT be reported as a 400 bad-request
    (which would blame the operator's input) — it's a transient upstream failure → 502."""
    import requests

    monkeypatch.delenv("DISTRIBUTION_DRY_RUN", raising=False)
    monkeypatch.setattr(requests, "post", lambda *a, **k: _FakeResp(503, text="pds down"))
    u = _make_user(db_session, "bsky-503@example.com", "user-bsky503")
    r = client.post(
        "/api/distribution/credentials",
        json={"platform": "bluesky", "access_token": "pw", "account_ref": "me.bsky.social"},
        headers=_hdr(u),
    )
    assert r.status_code == 502, r.text
    # And nothing was persisted on a transient failure either.
    lst = client.get("/api/distribution/credentials", headers=_hdr(u)).json()
    assert all(c["platform"] != "bluesky" for c in lst)


def test_connect_bluesky_dry_run_skips_network_verify(client, db_session, monkeypatch):
    """In dry-run the connect verifier resolves to the stub (no network) and succeeds, storing
    the handle as the display name so the credential is identifiable."""
    monkeypatch.setenv("DISTRIBUTION_DRY_RUN", "true")
    u = _make_user(db_session, "bsky-dry@example.com", "user-bskydry")
    r = client.post(
        "/api/distribution/credentials",
        json={
            "platform": "bluesky",
            "access_token": "pw",
            "account_ref": "me.bsky.social",
            "display_name": "me.bsky.social",
        },
        headers=_hdr(u),
    )
    assert r.status_code == 201, r.text
    assert r.json()["display_name"] == "me.bsky.social"


def test_schedule_and_publish_now_via_stub(client, db_session):
    u = _make_user(db_session, "dist-pub@example.com", "user-distpub")
    r = client.post(
        "/api/distribution/schedule",
        json={
            "platform": "stub",
            "content": "Hello world",
            "scheduled_for": "2020-01-01T00:00:00Z",
        },
        headers=_hdr(u),
    )
    assert r.status_code == 201, r.text
    sp_id = r.json()["id"]
    assert r.json()["status"] == "pending"

    pub = client.post(f"/api/distribution/publish/{sp_id}", headers=_hdr(u))
    assert pub.status_code == 200, pub.text
    body = pub.json()
    assert body["status"] == "posted"
    assert body["platform_url"].startswith("https://stub.local/")


def test_process_due_publishes_pending(client, db_session):
    admin = _make_user(db_session, "dist-admin@example.com", "user-distadmin", is_superuser=True)
    # A past-due stub post owned by the admin.
    client.post(
        "/api/distribution/schedule",
        json={"platform": "stub", "content": "due post", "scheduled_for": "2020-01-01T00:00:00Z"},
        headers=_hdr(admin),
    )
    res = client.post("/api/distribution/process-due", headers=_hdr(admin))
    assert res.status_code == 200, res.text
    assert res.json()["published"] >= 1


def test_process_due_requires_superuser(client, db_session):
    op = _make_user(db_session, "dist-op@example.com", "user-distop")
    res = client.post("/api/distribution/process-due", headers=_hdr(op))
    assert res.status_code == 403


def test_video_platform_without_media_fails_closed(client, db_session):
    u = _make_user(db_session, "dist-ni@example.com", "user-distni")
    # TikTok is video-only; publishing text with no media_url must fail closed
    # with a clear message rather than crash or make a doomed network call.
    client.post(
        "/api/distribution/credentials",
        json={"platform": "tiktok", "access_token": "tok"},
        headers=_hdr(u),
    )
    sp = client.post(
        "/api/distribution/schedule",
        json={"platform": "tiktok", "content": "vid", "scheduled_for": "2020-01-01T00:00:00Z"},
        headers=_hdr(u),
    ).json()
    pub = client.post(f"/api/distribution/publish/{sp['id']}", headers=_hdr(u))
    assert pub.status_code == 200
    body = pub.json()
    assert body["status"] == "failed"
    assert "video" in (body["error_message"] or "").lower()


def test_no_credential_fails_closed(client, db_session):
    u = _make_user(db_session, "dist-nocred@example.com", "user-distnocred")
    # A real platform with NO connected account must fail closed (not publish).
    sp = client.post(
        "/api/distribution/schedule",
        json={"platform": "twitter", "content": "hi", "scheduled_for": "2020-01-01T00:00:00Z"},
        headers=_hdr(u),
    ).json()
    pub = client.post(f"/api/distribution/publish/{sp['id']}", headers=_hdr(u))
    assert pub.status_code == 200
    body = pub.json()
    assert body["status"] == "failed"
    assert "no active credential" in (body["error_message"] or "").lower()


def test_scheduled_post_is_active_policy():
    """The is_active predicate must match process_due's retry selection exactly (Decision #220)."""
    from datetime import datetime, timedelta, timezone

    from backend.models.distribution import ScheduledPost
    from backend.services.distribution import orchestrator as orch

    now = datetime.now(timezone.utc)

    def sp(status, retry_count=0, scheduled_for=None):
        return ScheduledPost(
            status=status, retry_count=retry_count, scheduled_for=scheduled_for or now
        )

    assert orch.scheduled_post_is_active(sp("pending")) is True
    assert orch.scheduled_post_is_active(sp("posted")) is False
    # failed + under the cap + within the 24h window → still retryable.
    assert orch.scheduled_post_is_active(sp("failed", 1, now - timedelta(hours=1))) is True
    # failed but the retry cap is hit → exhausted.
    assert orch.scheduled_post_is_active(sp("failed", orch.MAX_RETRIES, now)) is False
    # failed but past the 24h retry window → exhausted (even under the cap).
    assert orch.scheduled_post_is_active(sp("failed", 0, now - timedelta(hours=25))) is False


def test_queue_exposes_is_active_and_reflects_exhaustion(client, db_session):
    """/api/distribution/queue rows carry a server-computed is_active so the calendar can tell
    'will retry' from 'gave up' without reimplementing the retry policy."""
    from backend.models.distribution import ScheduledPost
    from backend.services.distribution import orchestrator as orch

    u = _make_user(db_session, "dist-active@example.com", "user-distactive")
    client.post(
        "/api/distribution/schedule",
        json={"platform": "stub", "content": "soon", "scheduled_for": "2020-01-01T00:00:00Z"},
        headers=_hdr(u),
    )
    q = client.get("/api/distribution/queue", headers=_hdr(u)).json()
    assert len(q) == 1
    assert q[0]["is_active"] is True  # pending → active

    # Exhaust it (failed at the retry cap) → the same row now reports inactive.
    sp = db_session.query(ScheduledPost).filter(ScheduledPost.user_id == u.id).first()
    sp.status = "failed"
    sp.retry_count = orch.MAX_RETRIES
    db_session.commit()
    q2 = client.get("/api/distribution/queue", headers=_hdr(u)).json()
    assert q2[0]["is_active"] is False


def test_queue_and_publish_scoped_to_owner(client, db_session):
    a = _make_user(db_session, "dist-a@example.com", "user-dista")
    b = _make_user(db_session, "dist-b@example.com", "user-distb")
    sp = client.post(
        "/api/distribution/schedule",
        json={"platform": "stub", "content": "a's post", "scheduled_for": "2020-01-01T00:00:00Z"},
        headers=_hdr(a),
    ).json()
    # B cannot see A's queue…
    assert client.get("/api/distribution/queue", headers=_hdr(b)).json() == []
    # …nor publish A's post.
    assert client.post(f"/api/distribution/publish/{sp['id']}", headers=_hdr(b)).status_code == 404


def test_publish_gate_rejects_oversized_content_bypassing_schedule(db_session):
    """The compliance gate lives in _publish (the single choke point), so content
    that reaches publishing WITHOUT going through schedule_post's gate — e.g. a row
    built directly, or a mutated post — is still caught before the platform API call.
    """
    from datetime import datetime, timezone

    from backend.models.distribution import ScheduledPost
    from backend.services.distribution import orchestrator

    u = _make_user(db_session, "dist-gate@example.com", "user-distgate")
    sp = ScheduledPost(
        id="sp-oversized-gate",
        user_id=u.id,
        platform="twitter",
        content="x " * 200,  # 400 chars, over X's 280 API limit
        scheduled_for=datetime(2020, 1, 1, tzinfo=timezone.utc),
        status="pending",
        retry_count=0,
    )
    db_session.add(sp)
    db_session.commit()

    result = orchestrator._publish(db_session, sp)

    assert result.status == "failed"
    assert "280" in (result.error_message or "")
    # Never posted — the gate short-circuited before any publish attempt.
    assert result.posted_at is None


def test_publish_sends_utm_tagged_content_when_enabled(db_session, monkeypatch):
    """With UTM tagging enabled, _publish sends the tagged content to the publisher
    (links attributed) and records that as the posted content."""
    from datetime import datetime, timezone

    from backend.models.distribution import ScheduledPost
    from backend.services.distribution import orchestrator
    from backend.services.distribution.publishers import PublishResult

    monkeypatch.setenv("DISTRIBUTION_UTM_TAGGING", "true")

    captured = {}

    class _Spy:
        def publish(self, content, media_url=None):
            captured["content"] = content
            return PublishResult(success=True, platform_post_id="p1", platform_url="https://x/1")

    monkeypatch.setattr(orchestrator, "get_publisher", lambda *a, **k: _Spy())

    u = _make_user(db_session, "dist-utm@example.com", "user-distutm")
    sp = ScheduledPost(
        id="sp-utm",
        user_id=u.id,
        project_id=None,
        platform="stub",
        content="Read https://acme.com/post today",
        scheduled_for=datetime(2020, 1, 1, tzinfo=timezone.utc),
        status="pending",
        retry_count=0,
    )
    db_session.add(sp)
    db_session.commit()

    result = orchestrator._publish(db_session, sp)

    assert result.status == "posted"
    assert "utm_source=stub" in captured["content"]
    assert "utm_campaign=sp-utm" in captured["content"]  # fell back to sp.id
    # The authored row is unchanged — only the sent payload is tagged.
    assert sp.content == "Read https://acme.com/post today"


def test_schedule_gates_the_tagged_payload_not_just_authored(db_session, monkeypatch):
    """With UTM tagging on, schedule_post must gate the TAGGED content, so a tweet
    that is valid untagged but exceeds 280 once tagged is rejected up front — never
    scheduled only to fail silently at publish time."""
    from datetime import datetime, timezone

    from backend.services.distribution import orchestrator

    u = _make_user(db_session, "dist-tagchar@example.com", "user-tagchar")
    # ~250 chars: under 280 authored, but UTM params push it over once tagged.
    content = "Launch is live, read the full story here: https://acme.com/blog/launch " + (
        "x" * 180
    )
    assert len(content) < 280

    monkeypatch.setenv("DISTRIBUTION_UTM_TAGGING", "true")
    with pytest.raises(ValueError):
        orchestrator.schedule_post(
            db_session, u.id, "twitter", content, datetime(2030, 1, 1, tzinfo=timezone.utc)
        )

    # With tagging OFF, the same authored content is accepted (it fits untagged).
    monkeypatch.setenv("DISTRIBUTION_UTM_TAGGING", "false")
    sp = orchestrator.schedule_post(
        db_session, u.id, "twitter", content, datetime(2030, 1, 1, tzinfo=timezone.utc)
    )
    assert sp.status == "pending"


def test_save_credential_reconnect_preserves_metadata(db_session):
    """A reconnect (OAuth refresh) rotates tokens + reactivates but preserves the
    operator-set display_name and the account_ref publishers depend on."""
    from backend.services.distribution import orchestrator

    from datetime import datetime, timedelta, timezone

    u = _make_user(db_session, "dist-reconn@example.com", "user-distreconn")
    expiry = datetime(2026, 6, 1, tzinfo=timezone.utc)
    c1 = orchestrator.save_credential(
        db_session,
        u.id,
        "facebook",
        "tok-1",
        refresh_token="refresh-1",
        account_ref="page-123",
        display_name="Acme FB Page",
        token_expires_at=expiry,
    )
    original_refresh = c1.refresh_token
    c1.is_active = False  # simulate a revoked/expired credential
    db_session.commit()

    # Reconnect exactly as the OAuth callback often does: new access token, but the
    # provider re-issues NO refresh token and carries no account_ref/display_name.
    c2 = orchestrator.save_credential(db_session, u.id, "facebook", "tok-2")

    assert c2.id == c1.id  # same row (upsert), not a duplicate
    assert c2.is_active is True  # reactivated
    assert c2.account_ref == "page-123"  # preserved — FB/IG publishing needs it
    assert c2.display_name == "Acme FB Page"  # operator name not clobbered
    assert c2.refresh_token == original_refresh  # existing refresh token preserved, not wiped
    # Reconnect omitted a new expiry → an already-due sentinel is set (<= now, not None and
    # not the stale prior deadline) so ensure_fresh_token refreshes it on next use via the
    # kept refresh token and learns the real expiry before the token is relied on.
    c2_exp = c2.token_expires_at
    assert c2_exp is not None
    if c2_exp.tzinfo is None:
        c2_exp = c2_exp.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    assert c2_exp <= now + timedelta(seconds=1)  # already due for refresh
    assert c2_exp != expiry  # not the stale prior deadline

    # …but a reconnect that DOES supply a refresh token rotates it.
    c3 = orchestrator.save_credential(
        db_session, u.id, "facebook", "tok-3", refresh_token="refresh-2"
    )
    assert c3.refresh_token != original_refresh


def test_save_credential_new_gets_default_display_name(db_session):
    from backend.services.distribution import orchestrator

    u = _make_user(db_session, "dist-defname@example.com", "user-distdefname")
    c = orchestrator.save_credential(db_session, u.id, "linkedin", "tok")
    assert c.display_name == "linkedin account"
