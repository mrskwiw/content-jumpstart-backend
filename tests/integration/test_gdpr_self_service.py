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
