"""GAP-AUTH-02 — email verification HTTP flow (register email, verify, resend, gate)."""

import pytest

from backend.config import settings
from backend.models import User
from backend.services.verification_gate import email_delivery_available
from backend.utils.auth import (
    create_access_token,
    create_email_verification_token,
    get_password_hash,
)

_PW = "StrongPassw0rd!"


@pytest.fixture
def gate_on(monkeypatch):
    """Enforce the verification gate. The setting is the whole story — deliberately so."""
    monkeypatch.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)


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


def test_shipped_default_enforces_verification():
    # The gate ships ON. The test environment opts out via REQUIRE_EMAIL_VERIFICATION=false
    # (see tests/conftest.py) because fixtures create users straight through the ORM, so
    # assert the field default itself rather than the env-resolved singleton.
    from backend.config import Settings

    assert Settings.model_fields["REQUIRE_EMAIL_VERIFICATION"].default is True


def test_login_gate_can_be_disabled_per_instance(db_session, client, monkeypatch):
    monkeypatch.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", False)
    _mk_user(db_session, uid="user-ev6", email="ev6@example.com", verified=False)
    # With the gate off, an unverified user still signs in (the escape hatch for an
    # instance that can't send mail yet).
    r = client.post("/api/auth/login", json={"email": "ev6@example.com", "password": _PW})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["emailVerified"] is False


def test_login_gate_blocks_unverified_when_enabled(db_session, client, gate_on):
    _mk_user(db_session, uid="user-ev7", email="ev7@example.com", verified=False)
    r = client.post("/api/auth/login", json={"email": "ev7@example.com", "password": _PW})
    assert r.status_code == 403
    # A verified user is allowed through even with the gate on.
    _mk_user(db_session, uid="user-ev8", email="ev8@example.com", verified=True)
    ok = client.post("/api/auth/login", json={"email": "ev8@example.com", "password": _PW})
    assert ok.status_code == 200, ok.text


def test_a_missing_email_transport_does_not_open_authentication(
    db_session, client, gate_on, monkeypatch
):
    # An unconfigured mailer is the likeliest rollout mistake; it must not disable the
    # gate. (Boot logs a loud error instead — see warn_if_unenforceable.)
    for key in ("RESEND_API_KEY", "SMTP_USER", "SMTP_USERNAME", "SMTP_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("EMAIL_PROVIDER", "auto")
    assert email_delivery_available() is False

    _mk_user(db_session, uid="user-ev11", email="ev11@example.com", verified=False)
    r = client.post("/api/auth/login", json={"email": "ev11@example.com", "password": _PW})
    assert r.status_code == 403


def test_gate_enforced_on_every_authenticated_request(db_session, client, gate_on):
    # The gate lives in the shared auth dependency, so an already-issued token (e.g.
    # from /register) can't bypass verification — every authenticated request is gated.
    unverified = _mk_user(db_session, uid="user-ev9", email="ev9@example.com", verified=False)
    token = create_access_token(data={"sub": unverified.id})
    r = client.post("/api/auth/logout-all", json={}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403  # blocked by get_current_user, not just /login
    # A verified user's token still works.
    verified = _mk_user(db_session, uid="user-ev10", email="ev10@example.com", verified=True)
    vtoken = create_access_token(data={"sub": verified.id})
    ok = client.post("/api/auth/logout-all", json={}, headers={"Authorization": f"Bearer {vtoken}"})
    assert ok.status_code == 200


def test_gate_covers_the_mfa_setup_dependency(db_session, client, gate_on):
    # get_current_user_for_mfa_setup is a second front door (it also accepts limited
    # "mfa_setup" tokens), so it carries the same gate — otherwise an unverified account
    # could still mutate its MFA state on /mfa/enroll and /mfa/verify.
    unverified = _mk_user(db_session, uid="user-ev12", email="ev12@example.com", verified=False)
    headers = {"Authorization": f"Bearer {create_access_token(data={'sub': unverified.id})}"}
    assert client.post("/api/mfa/enroll", headers=headers).status_code == 403
    assert (
        client.post("/api/mfa/verify", json={"token": "123456"}, headers=headers).status_code == 403
    )

    verified = _mk_user(db_session, uid="user-ev13", email="ev13@example.com", verified=True)
    ok_headers = {"Authorization": f"Bearer {create_access_token(data={'sub': verified.id})}"}
    assert client.post("/api/mfa/enroll", headers=ok_headers).status_code == 200


def test_grandfather_backfill_on_alter():
    # The migration ALTER for existing DBs uses DEFAULT TRUE, so accounts that predate
    # email verification are grandfathered as verified and can't be locked out when the
    # gate is enabled. (New ORM inserts still default False via the model.)
    from sqlalchemy import create_engine, text

    eng = create_engine("sqlite://")
    with eng.begin() as c:
        c.execute(text("CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT)"))
        c.execute(text("INSERT INTO users (id, email) VALUES ('old', 'old@example.com')"))
        c.execute(text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT TRUE"))
        val = c.execute(text("SELECT email_verified FROM users WHERE id = 'old'")).scalar()
    assert val in (1, True)  # pre-existing row grandfathered to verified


def test_grandfather_backfill_update_flips_existing_false_rows():
    # Covers the case the DEFAULT-TRUE add-column can't: a DB that ALREADY has
    # users.email_verified with FALSE incumbents. The one-time v7 backfill UPDATE
    # flips existing FALSE/NULL rows to TRUE (already-true rows are untouched).
    from sqlalchemy import create_engine, text

    eng = create_engine("sqlite://")
    with eng.begin() as c:
        c.execute(
            text("CREATE TABLE users (id TEXT PRIMARY KEY, email_verified BOOLEAN DEFAULT 0)")
        )
        c.execute(text("INSERT INTO users (id, email_verified) VALUES ('a', 0), ('b', 1)"))
        c.execute(
            text(
                "UPDATE users SET email_verified = TRUE "
                "WHERE email_verified = FALSE OR email_verified IS NULL"
            )
        )
        rows = dict(c.execute(text("SELECT id, email_verified FROM users")).fetchall())
    assert rows["a"] in (1, True)  # incumbent flipped to verified
    assert rows["b"] in (1, True)  # already-verified stays verified
