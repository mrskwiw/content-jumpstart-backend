"""GAP-AUTH-03 — session revocation HTTP flow (logout, logout-all, admin revoke)."""

from jose import jwt

from backend.config import settings
from backend.models import User
from backend.utils.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
)


def _headers(user_id: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': user_id})}"}


def _legacy_access_token(user_id: str) -> str:
    """A pre-GAP-AUTH-03 access token: no jti, no iat (only sub/type/exp)."""
    from datetime import datetime, timedelta

    payload = {
        "sub": user_id,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _mk_user(db_session, *, uid: str, email: str, superuser: bool = False) -> User:
    user = User(
        id=uid,
        email=email,
        hashed_password=get_password_hash("testpass123"),
        full_name=email,
        is_active=True,
        is_superuser=superuser,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_logout_revokes_current_token(db_session, client, test_user):
    headers = _headers(test_user.id)
    # First logout succeeds (token still valid at entry)…
    r1 = client.post("/api/auth/logout", json={}, headers=headers)
    assert r1.status_code == 200, r1.text
    # …and the very same token is now dead on the next authenticated call.
    r2 = client.post("/api/auth/logout", json={}, headers=headers)
    assert r2.status_code == 401
    assert "revoked" in r2.json()["detail"].lower()


def test_logout_without_refresh_fails_closed(db_session, client, test_user):
    # No refresh token supplied → we can't guarantee the refresh credential is dead,
    # so logout must fail closed (session-wide cutoff), not just kill the access token.
    other_session = _headers(test_user.id)  # a second, still-valid session
    r = client.post("/api/auth/logout", json={}, headers=_headers(test_user.id))
    assert r.status_code == 200, r.text
    # The other session for the same user is also dead (cutoff), not just the caller's.
    assert client.post("/api/auth/logout", json={}, headers=other_session).status_code == 401


def test_logout_with_refresh_is_single_device(db_session, client, test_user):
    # Precise single-device logout: supply the refresh token; only that device's
    # tokens die (no session-wide cutoff), so another device keeps working.
    device1_access = create_access_token(data={"sub": test_user.id})
    device1_refresh = create_refresh_token(data={"sub": test_user.id})
    device2 = _headers(test_user.id)

    r = client.post(
        "/api/auth/logout",
        json={"refresh_token": device1_refresh},
        headers={"Authorization": f"Bearer {device1_access}"},
    )
    assert r.status_code == 200, r.text
    # Device 1's access token is dead…
    dead = {"Authorization": f"Bearer {device1_access}"}
    assert client.post("/api/auth/logout", json={}, headers=dead).status_code == 401
    # …but device 2 still authenticates (no cutoff was applied to the user).
    assert client.post("/api/auth/logout", json={}, headers=device2).status_code == 200


def test_logout_with_refresh_kills_the_refresh_token(db_session, client, test_user):
    # The supplied refresh token must not be able to mint new tokens after logout.
    access = create_access_token(data={"sub": test_user.id})
    refresh = create_refresh_token(data={"sub": test_user.id})
    r = client.post(
        "/api/auth/logout",
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 200, r.text
    # Using the revoked refresh token to refresh is rejected.
    rr = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert rr.status_code == 401


def test_logout_legacy_token_fails_closed(db_session, client, test_user):
    # A legacy access token (no jti) can't be targeted → logout must fail closed and
    # the same bearer must not still authenticate afterwards.
    legacy = _legacy_access_token(test_user.id)
    hdr = {"Authorization": f"Bearer {legacy}"}
    assert client.post("/api/auth/logout", json={}, headers=hdr).status_code == 200
    # The legacy token is now rejected (session-wide cutoff; no iat → fail-safe).
    assert client.post("/api/auth/logout", json={}, headers=hdr).status_code == 401


def test_logout_all_revokes_prior_sessions(db_session, client, test_user):
    # Validates the HTTP wiring of logout-all: it 200s and kills the caller's
    # existing session. The precise iat-vs-cutoff temporal boundary (prior tokens
    # die, later re-logins survive) is unit-tested in test_session_revocation.py
    # without depending on sub-second wall-clock timing.
    old = _headers(test_user.id)
    r = client.post("/api/auth/logout-all", json={}, headers=old)
    assert r.status_code == 200, r.text
    assert client.post("/api/auth/logout", json={}, headers=old).status_code == 401


def test_admin_revoke_sessions_kills_target(db_session, client):
    admin = _mk_user(db_session, uid="user-admin1", email="admin@example.com", superuser=True)
    target = _mk_user(db_session, uid="user-target1", email="target@example.com")
    target_headers = _headers(target.id)

    r = client.post(
        f"/api/admin/users/{target.id}/revoke-sessions",
        headers=_headers(admin.id),
    )
    assert r.status_code == 200, r.text
    # Target's pre-existing session is now dead; the admin's own is unaffected.
    assert client.post("/api/auth/logout", json={}, headers=target_headers).status_code == 401
    assert client.post("/api/auth/logout", json={}, headers=_headers(admin.id)).status_code == 200


def test_admin_revoke_token_by_jti(db_session, client):
    admin = _mk_user(db_session, uid="user-admin2", email="admin2@example.com", superuser=True)
    victim = _mk_user(db_session, uid="user-victim2", email="victim2@example.com")

    victim_token = create_access_token(data={"sub": victim.id})
    jti = decode_token(victim_token)["jti"]

    r = client.post("/api/admin/revoke-token", json={"jti": jti}, headers=_headers(admin.id))
    assert r.status_code == 200, r.text

    # That specific token is dead; a different token for the same user still works.
    dead = {"Authorization": f"Bearer {victim_token}"}
    assert client.post("/api/auth/logout", json={}, headers=dead).status_code == 401
    assert client.post("/api/auth/logout", json={}, headers=_headers(victim.id)).status_code == 200


def test_admin_revoke_requires_admin(db_session, client, test_user):
    # A non-admin cannot revoke anyone's sessions.
    r = client.post(
        f"/api/admin/users/{test_user.id}/revoke-sessions",
        headers=_headers(test_user.id),
    )
    assert r.status_code == 403


def test_admin_revoke_sessions_unknown_user_404(db_session, client):
    admin = _mk_user(db_session, uid="user-admin3", email="admin3@example.com", superuser=True)
    r = client.post("/api/admin/users/nope/revoke-sessions", headers=_headers(admin.id))
    assert r.status_code == 404
