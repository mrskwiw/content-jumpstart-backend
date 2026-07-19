"""
Integration tests for GDPR self-service (GAP-AUTH-04):
- POST /api/auth/change-password  (operator self-service password change)
- GET  /api/privacy/instance/export  (superuser-only full-instance export)
- GET  /api/privacy/clients/{id}/export  (enhanced per-client export)

Password policy (backend/utils/password_policy.py) requires 12+ chars with
upper/lower/digit/special, no sequential runs (123/abc), no >3 repeats — the
test passwords below are crafted to satisfy it.
"""

from backend.models import User, Client, Project
from backend.utils.auth import (
    get_password_hash,
    create_access_token,
    verify_password,
    password_fingerprint,
)

# Policy-compliant strong passwords (no sequential runs, has a special char).
OLD_PASSWORD = "Zx9!qWmp7Kt#"  # pragma: allowlist secret
NEW_PASSWORD = "Qp2@vNbz8Lr$"  # pragma: allowlist secret
WRONG_PASSWORD = "Wrong!Pass99xZ"  # pragma: allowlist secret
WEAK_PASSWORD = "short"  # pragma: allowlist secret
SEQUENTIAL_PASSWORD = "Abcdefg9!xQ"  # sequential run → fails policy  # pragma: allowlist secret


def _make_user(db, email, password, is_superuser=False, uid=None):
    user = User(
        id=uid or f"user-{email.split('@')[0]}",
        email=email,
        hashed_password=get_password_hash(password),
        full_name="Test Operator",
        is_active=True,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': user.id})}"}


# ── Change password ───────────────────────────────────────────────────────────


def test_change_password_success(client, db_session):
    user = _make_user(db_session, "cp-ok@example.com", OLD_PASSWORD)
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": OLD_PASSWORD, "new_password": NEW_PASSWORD},
        headers=_headers(user),
    )
    assert resp.status_code == 200, resp.text
    db_session.refresh(user)
    assert verify_password(NEW_PASSWORD, user.hashed_password)
    assert not verify_password(OLD_PASSWORD, user.hashed_password)


def test_change_password_wrong_current(client, db_session):
    user = _make_user(db_session, "cp-wrong@example.com", OLD_PASSWORD)
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": WRONG_PASSWORD, "new_password": NEW_PASSWORD},
        headers=_headers(user),
    )
    assert resp.status_code == 401
    db_session.refresh(user)
    assert verify_password(OLD_PASSWORD, user.hashed_password)  # unchanged


def test_change_password_reuse_rejected(client, db_session):
    user = _make_user(db_session, "cp-reuse@example.com", OLD_PASSWORD)
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": OLD_PASSWORD, "new_password": OLD_PASSWORD},
        headers=_headers(user),
    )
    assert resp.status_code == 400


def test_change_password_weak_new_rejected_by_schema(client, db_session):
    user = _make_user(db_session, "cp-weak@example.com", OLD_PASSWORD)
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": OLD_PASSWORD, "new_password": WEAK_PASSWORD},
        headers=_headers(user),
    )
    assert resp.status_code == 422  # fails Pydantic schema validation


def test_change_password_policy_violation_rejected(client, db_session):
    # Passes the schema (upper/lower/digit) but fails the policy (sequential "abc"/"def").
    user = _make_user(db_session, "cp-policy@example.com", OLD_PASSWORD)
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": OLD_PASSWORD, "new_password": SEQUENTIAL_PASSWORD},
        headers=_headers(user),
    )
    assert resp.status_code == 400


def test_change_password_requires_auth(client, db_session):
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": OLD_PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 401


def test_password_change_revokes_existing_sessions(client, db_session):
    """A token bound to the old password (pv claim) is rejected after a change."""
    user = _make_user(db_session, "cp-revoke@example.com", OLD_PASSWORD)
    old_token = create_access_token(
        data={"sub": user.id, "pv": password_fingerprint(user.hashed_password)}
    )
    hdr = {"Authorization": f"Bearer {old_token}"}

    # The still-valid token can perform the change.
    r1 = client.post(
        "/api/auth/change-password",
        json={"current_password": OLD_PASSWORD, "new_password": NEW_PASSWORD},
        headers=hdr,
    )
    assert r1.status_code == 200, r1.text

    # The same token (old pv) is now rejected on any authenticated call.
    r2 = client.post(
        "/api/auth/change-password",
        json={"current_password": NEW_PASSWORD, "new_password": OLD_PASSWORD},
        headers=hdr,
    )
    assert r2.status_code == 401


def test_legacy_token_without_pv_revoked_after_change(client, db_session):
    """A token carrying NO pv claim is also revoked once the password changes."""
    user = _make_user(db_session, "cp-legacy@example.com", OLD_PASSWORD)
    legacy_token = create_access_token(data={"sub": user.id})  # no "pv" claim
    hdr = {"Authorization": f"Bearer {legacy_token}"}

    # Before any change (password_changed_at is NULL) the legacy token authenticates.
    r0 = client.post(
        "/api/auth/change-password",
        json={"current_password": OLD_PASSWORD, "new_password": NEW_PASSWORD},
        headers=hdr,
    )
    assert r0.status_code == 200, r0.text

    # After the change, the same legacy token is rejected (no valid pv, pca set).
    r1 = client.post(
        "/api/auth/change-password",
        json={"current_password": NEW_PASSWORD, "new_password": OLD_PASSWORD},
        headers=hdr,
    )
    assert r1.status_code == 401


def test_admin_reset_revokes_target_user_sessions(client, db_session):
    """An admin password reset revokes the target user's existing sessions."""
    admin = _make_user(
        db_session, "admin-r@example.com", OLD_PASSWORD, is_superuser=True, uid="user-adminr"
    )
    target = _make_user(db_session, "target-r@example.com", OLD_PASSWORD, uid="user-targetr")
    target_hdr = {"Authorization": f"Bearer {create_access_token(data={'sub': target.id})}"}

    # Target's token authenticates before the reset (404 = auth ok, client missing).
    pre = client.get("/api/privacy/clients/nope/export", headers=target_hdr)
    assert pre.status_code == 404

    # Admin resets the target's password.
    reset = client.post(
        f"/api/admin/users/{target.id}/reset-password",
        json={"new_password": NEW_PASSWORD},
        headers=_headers(admin),
    )
    assert reset.status_code == 200, reset.text

    # Target's pre-reset session is now revoked.
    post = client.get("/api/privacy/clients/nope/export", headers=target_hdr)
    assert post.status_code == 401


# ── Instance export (superuser only) ──────────────────────────────────────────


def test_instance_export_superuser_ok_and_redacts_secrets(client, db_session):
    admin = _make_user(db_session, "admin@example.com", OLD_PASSWORD, is_superuser=True)
    resp = client.get("/api/privacy/instance/export", headers=_headers(admin))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["export_metadata"]["scope"] == "instance"
    assert "users" in body["data"]
    # The admin's own row must be present with its password hash redacted.
    users = body["data"]["users"]
    assert any(u["email"] == "admin@example.com" for u in users)
    assert all(u["hashed_password"] == "[REDACTED]" for u in users)


def test_instance_export_forbidden_for_operator(client, db_session):
    operator = _make_user(db_session, "op@example.com", OLD_PASSWORD, is_superuser=False)
    resp = client.get("/api/privacy/instance/export", headers=_headers(operator))
    assert resp.status_code == 403


# ── Enhanced per-client export ────────────────────────────────────────────────


def test_client_export_includes_related_sections(client, db_session):
    user = _make_user(db_session, "owner@example.com", OLD_PASSWORD)
    c = Client(
        id="client-exp1",
        user_id=user.id,
        name="Acme Co",
        business_description="x" * 80,
    )
    db_session.add(c)
    db_session.commit()
    p = Project(
        id="proj-exp1",
        user_id=user.id,
        client_id=c.id,
        name="Launch",
        status="active",
    )
    db_session.add(p)
    db_session.commit()

    resp = client.get(f"/api/privacy/clients/{c.id}/export", headers=_headers(user))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["export_metadata"]["scope"] == "client"
    assert body["client"]["id"] == "client-exp1"
    assert len(body["projects"]) == 1
    # New sections the thin v1 export lacked:
    for key in ("deliverables", "research_results", "client_keywords", "communications"):
        assert key in body


def test_client_export_forbidden_for_non_owner(client, db_session):
    """IDOR guard: a non-owner operator cannot export another user's client."""
    owner = _make_user(db_session, "owner2@example.com", OLD_PASSWORD, uid="user-owner2")
    other = _make_user(db_session, "other2@example.com", OLD_PASSWORD, uid="user-other2")
    c = Client(
        id="client-idor",
        user_id=owner.id,
        name="Owned Co",
        business_description="x" * 80,
    )
    db_session.add(c)
    db_session.commit()

    # Non-owner → 403
    resp = client.get(f"/api/privacy/clients/{c.id}/export", headers=_headers(other))
    assert resp.status_code == 403

    # Owner → 200
    resp_owner = client.get(f"/api/privacy/clients/{c.id}/export", headers=_headers(owner))
    assert resp_owner.status_code == 200


def test_client_delete_forbidden_for_non_owner(client, db_session):
    owner = _make_user(db_session, "owner3@example.com", OLD_PASSWORD, uid="user-owner3")
    other = _make_user(db_session, "other3@example.com", OLD_PASSWORD, uid="user-other3")
    c = Client(
        id="client-idor2",
        user_id=owner.id,
        name="Owned Co 2",
        business_description="x" * 80,
    )
    db_session.add(c)
    db_session.commit()

    resp = client.delete(f"/api/privacy/clients/{c.id}", headers=_headers(other))
    assert resp.status_code == 403


# ── User-level (account) export + deletion ────────────────────────────────────


def test_export_my_account_returns_user_scoped_data(client, db_session):
    from backend.models import Run, Post, Conversation, Message, TrendsKeywordInsight

    user = _make_user(db_session, "acct-exp@example.com", OLD_PASSWORD, uid="user-acctexp")
    c = Client(id="client-acct", user_id=user.id, name="My Client", business_description="x" * 80)
    db_session.add(c)
    p = Project(id="proj-acct", user_id=user.id, client_id="client-acct", name="P", status="active")
    db_session.add(p)
    db_session.commit()
    # Project-scoped trends insight with NO client_id (must still be exported).
    db_session.add(TrendsKeywordInsight(id="tki-acct", project_id="proj-acct", keyword="kw"))
    db_session.commit()
    db_session.add(Run(id="run-acct", project_id="proj-acct", status="completed"))
    db_session.commit()
    db_session.add(
        Post(id="post-acct", project_id="proj-acct", run_id="run-acct", content="generated post")
    )
    db_session.add(Conversation(id="conv-acct", user_id=user.id, title="Chat"))
    db_session.commit()
    db_session.add(Message(id="msg-acct", conversation_id="conv-acct", role="user", content="hi"))
    db_session.commit()
    # Raw-SQL cost-tracking table (no ORM model) — project-scoped, must be exported.
    from sqlalchemy import text

    db_session.execute(
        text(
            "CREATE TABLE IF NOT EXISTS api_calls "
            "(call_id TEXT PRIMARY KEY, project_id TEXT, operation TEXT, cost NUMERIC)"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO api_calls (call_id, project_id, operation, cost) "
            "VALUES ('call-acct', 'proj-acct', 'gen', 0.5)"
        )
    )
    db_session.commit()

    resp = client.get("/api/privacy/account/export", headers=_headers(user))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["export_metadata"]["scope"] == "user"
    assert body["account"]["id"] == user.id
    assert body["account"]["hashed_password"] == "[REDACTED]"
    assert any(cl["id"] == "client-acct" for cl in body["clients"])
    assert any(pp["id"] == "proj-acct" for pp in body["projects"])
    # Generated content tree must be present (was materially missing before).
    assert any(po["id"] == "post-acct" for po in body["posts"])
    assert any(rr["id"] == "run-acct" for rr in body["runs"])
    # Assistant history (user-owned) must be present.
    assert any(cv["id"] == "conv-acct" for cv in body["conversations"])
    assert any(m["id"] == "msg-acct" for m in body["messages"])
    # Project-scoped trends insight (no client_id) must be captured.
    assert any(t["id"] == "tki-acct" for t in body["trends_keyword_insights"])
    # Raw-SQL cost-tracking table (no ORM model) must be captured.
    assert any(a["call_id"] == "call-acct" for a in body["api_calls"])
    assert "budget_alerts" in body and "deletion_audit_log" in body
    for key in ("settings", "credit_transactions", "audit_log", "deliverables", "client_keywords"):
        assert key in body


def test_delete_my_account_soft_deletes_and_revokes_session(client, db_session):
    user = _make_user(db_session, "acct-del@example.com", OLD_PASSWORD, uid="user-acctdel")
    # A second admin so the account isn't the last active superuser (it isn't a
    # superuser here anyway, but keeps intent explicit).
    _make_user(
        db_session, "keep-admin@example.com", OLD_PASSWORD, is_superuser=True, uid="user-keep"
    )
    hdr = _headers(user)

    resp = client.delete("/api/privacy/account", headers=hdr)
    assert resp.status_code == 200, resp.text
    db_session.refresh(user)
    assert user.is_deleted is True
    assert user.is_active is False

    # Session revoked — the same token no longer authenticates.
    after = client.get("/api/privacy/account/export", headers=hdr)
    assert after.status_code == 401


def test_delete_last_admin_blocked(client, db_session):
    admin = _make_user(
        db_session, "sole-admin@example.com", OLD_PASSWORD, is_superuser=True, uid="user-soleadmin"
    )
    resp = client.delete("/api/privacy/account", headers=_headers(admin))
    assert resp.status_code == 400
    db_session.refresh(admin)
    assert admin.is_deleted is False  # guard prevented deletion


def test_restore_user_requires_superuser(client, db_session):
    from datetime import datetime, timezone

    admin = _make_user(
        db_session, "r-admin@example.com", OLD_PASSWORD, is_superuser=True, uid="user-radmin"
    )
    victim = _make_user(db_session, "victim@example.com", OLD_PASSWORD, uid="user-victim")
    victim.is_deleted = True
    victim.is_active = False
    victim.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    other = _make_user(db_session, "nobody@example.com", OLD_PASSWORD, uid="user-nobody")
    forbidden = client.post(f"/api/privacy/users/{victim.id}/restore", headers=_headers(other))
    assert forbidden.status_code == 403

    ok = client.post(f"/api/privacy/users/{victim.id}/restore", headers=_headers(admin))
    assert ok.status_code == 200
    db_session.refresh(victim)
    assert victim.is_deleted is False
    assert victim.is_active is True
