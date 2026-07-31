"""GAP-AUTH-02 — email verification HTTP flow (register email, verify, resend, gate)."""

from backend.config import settings
from backend.models import User
from backend.utils.auth import (
    create_access_token,
    create_email_verification_token,
    get_password_hash,
)

_PW = "StrongPassw0rd!"


def _mk_user(db_session, *, uid, email, verified=False, active=True):
    user = User(
        id=uid,
        email=email,
        hashed_password=get_password_hash(_PW),
        full_name=email,
        is_active=active,
        is_superuser=False,
        email_verified=verified,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_register_starts_unverified(db_session, client):
    # A new account is created unverified and the response reflects it (camelCase alias).
    # (The verification-email enqueue is asserted at handler level in
    # backend/tests/test_email_verification.py.)
    r = client.post(
        "/api/auth/register",
        json={"email": "newbie@example.com", "password": _PW, "full_name": "New Bie"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["user"]["emailVerified"] is False
    created = db_session.query(User).filter(User.email == "newbie@example.com").one()
    assert created.email_verified is False


def test_verify_email_marks_verified(db_session, client):
    user = _mk_user(db_session, uid="user-ev1", email="ev1@example.com")
    token = create_email_verification_token({"sub": user.id})
    r = client.post("/api/auth/verify-email", json={"token": token})
    assert r.status_code == 200, r.text
    db_session.refresh(user)
    assert user.email_verified is True
    assert user.email_verified_at is not None


def test_verify_email_is_idempotent(db_session, client):
    user = _mk_user(db_session, uid="user-ev2", email="ev2@example.com", verified=True)
    token = create_email_verification_token({"sub": user.id})
    # Verifying an already-verified account still succeeds.
    assert client.post("/api/auth/verify-email", json={"token": token}).status_code == 200


def test_verify_email_rejects_wrong_token_type(db_session, client):
    user = _mk_user(db_session, uid="user-ev3", email="ev3@example.com")
    # An access token is not a verification token → 400.
    access = create_access_token(data={"sub": user.id})
    r = client.post("/api/auth/verify-email", json={"token": access})
    assert r.status_code == 400
    db_session.refresh(user)
    assert user.email_verified is False


def test_verify_email_rejects_malformed_token(db_session, client):
    assert client.post("/api/auth/verify-email", json={"token": "not-a-jwt"}).status_code == 400


def test_resend_verification_generic_response(db_session, client):
    # Same generic 200 whether the email is unverified, already-verified, or unknown
    # (no user enumeration). Which cases actually enqueue an email is asserted at the
    # handler level in backend/tests/test_email_verification.py.
    _mk_user(db_session, uid="user-ev5", email="ev5@example.com", verified=True)
    for email in ("ev5@example.com", "nobody@example.com"):
        assert (
            client.post("/api/auth/resend-verification", json={"email": email}).status_code == 200
        )


def test_login_gate_off_by_default_allows_unverified(db_session, client):
    _mk_user(db_session, uid="user-ev6", email="ev6@example.com", verified=False)
    # Default REQUIRE_EMAIL_VERIFICATION is False → unverified user can still log in.
    r = client.post("/api/auth/login", json={"email": "ev6@example.com", "password": _PW})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["emailVerified"] is False


def test_login_gate_blocks_unverified_when_enabled(db_session, client, monkeypatch):
    monkeypatch.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
    _mk_user(db_session, uid="user-ev7", email="ev7@example.com", verified=False)
    r = client.post("/api/auth/login", json={"email": "ev7@example.com", "password": _PW})
    assert r.status_code == 403
    # A verified user is allowed through even with the gate on.
    _mk_user(db_session, uid="user-ev8", email="ev8@example.com", verified=True)
    ok = client.post("/api/auth/login", json={"email": "ev8@example.com", "password": _PW})
    assert ok.status_code == 200, ok.text
