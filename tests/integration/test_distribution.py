"""
Integration tests for Phase 10 — Multi-Platform Distribution.

Exercises the full schedule → publish → track loop via the stub publisher, the
cron `process-due` worker, per-user ownership, and the fail-closed behaviour for
a not-yet-implemented platform.
"""

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
