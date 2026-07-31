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


def _alive(client, user_id: str) -> int:
    """Probe whether a fresh token for the user still authenticates.

    Returns the status of a valid single-device logout (200 when the user has no
    session-wide cutoff). Used to assert one user's revocation didn't affect another.
    """
    access = create_access_token(data={"sub": user_id})
    refresh = create_refresh_token(data={"sub": user_id})
    return client.post(
        "/api/auth/logout",
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {access}"},
    ).status_code


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


def test_logout_requires_refresh_token(db_session, client, test_user):
    # A logout without a refresh token is rejected (400) rather than silently
    # escalating to a session-wide wipe — the revoke-all path is /logout-all.
    r = client.post("/api/auth/logout", json={}, headers=_headers(test_user.id))
    assert r.status_code == 400
    assert "refresh_token" in r.json()["detail"]


def test_logout_with_refresh_is_single_device(db_session, client, test_user):
    # Precise single-device logout: supply the refresh token; only that device's
    # tokens die (no session-wide cutoff), so another device keeps working.
    device1_access = create_access_token(data={"sub": test_user.id})
    device1_refresh = create_refresh_token(data={"sub": test_user.id})
    device2_access = create_access_token(data={"sub": test_user.id})
    device2_refresh = create_refresh_token(data={"sub": test_user.id})

    r = client.post(
        "/api/auth/logout",
        json={"refresh_token": device1_refresh},
        headers={"Authorization": f"Bearer {device1_access}"},
    )
    assert r.status_code == 200, r.text
    # Device 1's access token is dead…
    dead = {"Authorization": f"Bearer {device1_access}"}
    assert (
        client.post("/api/auth/logout", json={"refresh_token": "x"}, headers=dead).status_code
        == 401
    )
    # …but device 2 still authenticates + logs out cleanly (no user-wide cutoff).
    r2 = client.post(
        "/api/auth/logout",
        json={"refresh_token": device2_refresh},
        headers={"Authorization": f"Bearer {device2_access}"},
    )
    assert r2.status_code == 200


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


def test_logout_legacy_token_directs_to_logout_all(db_session, client, test_user):
    # A legacy access token (no jti) can't be logged out individually and must NOT be
    # able to trigger an account-wide cutoff via /logout — it's 409'd toward /logout-all.
    legacy_hdr = {"Authorization": f"Bearer {_legacy_access_token(test_user.id)}"}
    # A pre-existing modern session for the same user, minted before the logout attempt.
    other_access = create_access_token(data={"sub": test_user.id})
    other_refresh = create_refresh_token(data={"sub": test_user.id})

    r = client.post("/api/auth/logout", json={}, headers=legacy_hdr)
    assert r.status_code == 409

    # No account-wide cutoff happened: the pre-existing session still authenticates
    # (if a cutoff had run, this token — minted before it — would be 401).
    still_alive = client.post(
        "/api/auth/logout",
        json={"refresh_token": other_refresh},
        headers={"Authorization": f"Bearer {other_access}"},
    )
    assert still_alive.status_code == 200
    # The explicit account-wide path is still available to the legacy bearer.
    assert client.post("/api/auth/logout-all", json={}, headers=legacy_hdr).status_code == 200


def test_logout_rejects_access_token_as_refresh(db_session, client, test_user):
    # Passing the ACCESS token in the refresh_token field must be rejected (type check),
    # else logout would revoke the access token twice and leave the real refresh path
    # alive — a logout bypass.
    access = create_access_token(data={"sub": test_user.id})
    r = client.post(
        "/api/auth/logout",
        json={"refresh_token": access},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 400
    # The access token itself was NOT revoked by that rejected call: a proper logout
    # (with a real refresh token) still succeeds afterwards.
    good = client.post(
        "/api/auth/logout",
        json={"refresh_token": create_refresh_token(data={"sub": test_user.id})},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert good.status_code == 200


def test_logout_rejects_foreign_refresh_token(db_session, client):
    # /logout must not revoke a refresh token that belongs to a different user.
    a = _mk_user(db_session, uid="user-fa1", email="fa1@example.com")
    b = _mk_user(db_session, uid="user-fb1", email="fb1@example.com")
    r = client.post(
        "/api/auth/logout",
        json={"refresh_token": create_refresh_token(data={"sub": b.id})},
        headers={"Authorization": f"Bearer {create_access_token(data={'sub': a.id})}"},
    )
    assert r.status_code == 400


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
    assert _alive(client, admin.id) == 200


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
    assert _alive(client, victim.id) == 200


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
