"""BUGS #172 — MFA end to end: enroll, sign in with a second factor, manage, disable."""

import json

import pyotp
import pytest

from backend.models import User
from backend.services.mfa_service import MFAService
from backend.utils.auth import create_access_token, get_password_hash

_PW = "StrongPassw0rd!"  # pragma: allowlist secret


def _mk_user(db_session, *, uid, email, superuser=False):
    user = User(
        id=uid,
        email=email,
        hashed_password=get_password_hash(_PW),
        full_name=email,
        is_active=True,
        is_superuser=superuser,
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _auth(user):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': user.id})}"}


def _enrolled(db_session, user):
    """Put a user in the post-enrollment state and return (secret, plaintext codes)."""
    secret = MFAService.generate_secret()
    codes, hashed = MFAService.generate_backup_codes()
    user.mfa_secret = secret
    user.mfa_backup_codes = hashed
    user.mfa_enabled = True
    db_session.commit()
    return secret, codes


def _login(client, email, code=None):
    body = {"email": email, "password": _PW}
    if code is not None:
        body["totp_code"] = code
    return client.post("/api/auth/login", json=body)


# ---------------------------------------------------------------- enrollment


def test_enroll_then_verify_activates_mfa(db_session, client):
    user = _mk_user(db_session, uid="mfa-1", email="mfa1@example.com")

    enroll = client.post("/api/mfa/enroll", headers=_auth(user))
    assert enroll.status_code == 200, enroll.text
    payload = enroll.json()
    assert payload["qr_code"].startswith("data:image/png;base64,")
    assert len(payload["backup_codes"]) == MFAService.BACKUP_CODE_COUNT

    # Enrollment is not complete until a code from the authenticator is confirmed.
    db_session.refresh(user)
    assert user.mfa_enabled is False

    code = pyotp.TOTP(payload["secret"]).now()
    verify = client.post("/api/mfa/verify", json={"token": code}, headers=_auth(user))
    assert verify.status_code == 200, verify.text
    assert verify.json()["success"] is True

    db_session.refresh(user)
    assert user.mfa_enabled is True


def test_enrolling_a_superuser_does_not_lock_them_into_mfa(db_session, client):
    # mfa_enforced is an operator policy flag; enrolling voluntarily must not set it,
    # or the user could never turn MFA back off.
    user = _mk_user(db_session, uid="mfa-2", email="mfa2@example.com", superuser=True)
    enroll = client.post("/api/mfa/enroll", headers=_auth(user)).json()
    client.post(
        "/api/mfa/verify",
        json={"token": pyotp.TOTP(enroll["secret"]).now()},
        headers=_auth(user),
    )
    db_session.refresh(user)
    assert user.mfa_enabled is True
    assert user.mfa_enforced is False


def test_enroll_rejected_when_already_enabled(db_session, client):
    user = _mk_user(db_session, uid="mfa-3", email="mfa3@example.com")
    _enrolled(db_session, user)
    assert client.post("/api/mfa/enroll", headers=_auth(user)).status_code == 400


# ---------------------------------------------------------------- login


def test_login_requires_a_code_once_enrolled(db_session, client):
    user = _mk_user(db_session, uid="mfa-4", email="mfa4@example.com")
    secret, _ = _enrolled(db_session, user)

    missing = _login(client, "mfa4@example.com")
    assert missing.status_code == 401
    # The exact phrase the login form switches on to render the code step.
    assert missing.json()["detail"] == "MFA code required"

    assert _login(client, "mfa4@example.com", "000000").status_code == 401

    ok = _login(client, "mfa4@example.com", pyotp.TOTP(secret).now())
    assert ok.status_code == 200, ok.text
    assert ok.json()["access_token"]


def test_login_accepts_a_backup_code_exactly_once(db_session, client):
    user = _mk_user(db_session, uid="mfa-5", email="mfa5@example.com")
    _, codes = _enrolled(db_session, user)

    first = _login(client, "mfa5@example.com", codes[0])
    assert first.status_code == 200, first.text

    # Consumption is committed, so a replay of the same code is refused.
    replay = _login(client, "mfa5@example.com", codes[0])
    assert replay.status_code == 401

    db_session.refresh(user)
    assert len(json.loads(user.mfa_backup_codes)) == MFAService.BACKUP_CODE_COUNT - 1


def test_login_is_unaffected_for_accounts_without_mfa(db_session, client):
    _mk_user(db_session, uid="mfa-6", email="mfa6@example.com")
    assert _login(client, "mfa6@example.com").status_code == 200


# ---------------------------------------------------------------- management


def test_status_reports_enrollment_and_remaining_codes(db_session, client):
    user = _mk_user(db_session, uid="mfa-7", email="mfa7@example.com")
    before = client.get("/api/mfa/status", headers=_auth(user)).json()
    assert before["mfa_enabled"] is False
    assert before["remaining_backup_codes"] == 0

    _enrolled(db_session, user)
    after = client.get("/api/mfa/status", headers=_auth(user)).json()
    assert after["mfa_enabled"] is True
    assert after["remaining_backup_codes"] == MFAService.BACKUP_CODE_COUNT


def test_regenerate_backup_codes_invalidates_the_old_set(db_session, client):
    user = _mk_user(db_session, uid="mfa-8", email="mfa8@example.com")
    secret, old_codes = _enrolled(db_session, user)

    bad = client.post(
        "/api/mfa/backup-codes/regenerate", json={"token": "000000"}, headers=_auth(user)
    )
    assert bad.status_code == 401

    fresh = client.post(
        "/api/mfa/backup-codes/regenerate",
        json={"token": pyotp.TOTP(secret).now()},
        headers=_auth(user),
    )
    assert fresh.status_code == 200, fresh.text
    new_codes = fresh.json()["backup_codes"]
    assert len(new_codes) == MFAService.BACKUP_CODE_COUNT
    assert not set(new_codes) & set(old_codes)

    # An old code is dead; a new one authenticates.
    assert _login(client, "mfa8@example.com", old_codes[0]).status_code == 401
    assert _login(client, "mfa8@example.com", new_codes[0]).status_code == 200


def test_disable_requires_password_and_a_live_second_factor(db_session, client):
    user = _mk_user(db_session, uid="mfa-9", email="mfa9@example.com")
    secret, _ = _enrolled(db_session, user)

    wrong_pw = client.post(
        "/api/mfa/disable",
        json={"password": "NotThePassword1!", "code": pyotp.TOTP(secret).now()},
        headers=_auth(user),
    )
    assert wrong_pw.status_code == 401

    wrong_code = client.post(
        "/api/mfa/disable",
        json={"password": _PW, "code": "000000"},
        headers=_auth(user),
    )
    assert wrong_code.status_code == 401

    db_session.refresh(user)
    assert user.mfa_enabled is True

    ok = client.post(
        "/api/mfa/disable",
        json={"password": _PW, "code": pyotp.TOTP(secret).now()},
        headers=_auth(user),
    )
    assert ok.status_code == 200, ok.text

    db_session.refresh(user)
    assert user.mfa_enabled is False
    assert user.mfa_secret is None
    assert user.mfa_backup_codes is None
    # ...and sign-in no longer challenges for a code.
    assert _login(client, "mfa9@example.com").status_code == 200


def test_disable_is_refused_under_an_operator_policy(db_session, client):
    user = _mk_user(db_session, uid="mfa-10", email="mfa10@example.com")
    secret, _ = _enrolled(db_session, user)
    user.mfa_enforced = True
    db_session.commit()

    refused = client.post(
        "/api/mfa/disable",
        json={"password": _PW, "code": pyotp.TOTP(secret).now()},
        headers=_auth(user),
    )
    assert refused.status_code == 403

    db_session.refresh(user)
    assert user.mfa_enabled is True


def test_disable_rejected_when_mfa_is_not_enabled(db_session, client):
    user = _mk_user(db_session, uid="mfa-11", email="mfa11@example.com")
    resp = client.post(
        "/api/mfa/disable",
        json={"password": _PW, "code": "000000"},
        headers=_auth(user),
    )
    assert resp.status_code == 400


@pytest.mark.parametrize("path", ["/api/mfa/status", "/api/mfa/enroll"])
def test_mfa_endpoints_require_authentication(client, path):
    method = client.get if path.endswith("status") else client.post
    assert method(path).status_code in (401, 403)
