"""Self-service password reset — /auth/forgot-password + /auth/reset-password (GAP-AUTH-01).

Covers the security-critical guarantees:
- no user enumeration (generic response either way)
- reset is single-use and self-revoking via the token's "pv" claim
- a wrong-type / malformed / expired token is rejected
- the strong-password policy and session-revocation stamp are applied

The endpoints are unit-tested through their undecorated handlers (``__wrapped__``)
so the slowapi rate-limit wrapper — which needs a real Request + app state —
doesn't interfere. Token minting/decoding is exercised for real (no mock) so the
single-use ``pv`` mechanism is genuinely verified.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException

from backend.routers.auth import forgot_password, reset_password
from backend.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest
from backend.utils.auth import (
    create_access_token,
    create_password_reset_token,
    get_password_hash,
    password_fingerprint,
    verify_password,
)

_forgot = getattr(forgot_password, "__wrapped__", forgot_password)
_reset = getattr(reset_password, "__wrapped__", reset_password)

OLD_PASSWORD = "OldPass123"  # pragma: allowlist secret  # noqa: S105 - test value
# Must satisfy the full password_policy (12+ chars, upper/lower/digit, a special
# char, no sequential runs), which is stricter than the request schema.
NEW_PASSWORD = "Zephyr!K4mtby"  # pragma: allowlist secret  # noqa: S105 - test value


def _user(active: bool = True):
    """A MagicMock user with a real bcrypt hash of OLD_PASSWORD."""
    return MagicMock(
        id="u1",
        email="user@example.com",
        full_name="Test User",
        is_active=active,
        hashed_password=get_password_hash(OLD_PASSWORD),
        password_changed_at=None,
    )


def _valid_token(user) -> str:
    return create_password_reset_token(
        {"sub": user.id, "pv": password_fingerprint(user.hashed_password)}
    )


# --------------------------------------------------------------------------- #
# forgot-password
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_forgot_password_active_user_schedules_email():
    user = _user()
    bg = BackgroundTasks()
    with patch("backend.routers.auth.crud.get_user_by_email", return_value=user):
        resp = await _forgot(MagicMock(), ForgotPasswordRequest(email=user.email), bg, MagicMock())

    assert resp["status"] == "success"
    assert len(bg.tasks) == 1  # reset email enqueued


@pytest.mark.asyncio
async def test_forgot_password_unknown_email_is_indistinguishable():
    bg = BackgroundTasks()
    with patch("backend.routers.auth.crud.get_user_by_email", return_value=None):
        resp = await _forgot(
            MagicMock(),
            ForgotPasswordRequest(email="nobody@example.com"),
            bg,
            MagicMock(),
        )

    # Same response as the found case, and NO email scheduled — no enumeration.
    assert resp["status"] == "success"
    assert len(bg.tasks) == 0


@pytest.mark.asyncio
async def test_forgot_password_inactive_user_sends_nothing():
    bg = BackgroundTasks()
    with patch("backend.routers.auth.crud.get_user_by_email", return_value=_user(active=False)):
        resp = await _forgot(
            MagicMock(),
            ForgotPasswordRequest(email="user@example.com"),
            bg,
            MagicMock(),
        )

    assert resp["status"] == "success"
    assert len(bg.tasks) == 0


# --------------------------------------------------------------------------- #
# reset-password
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_reset_password_happy_path():
    user = _user()
    token = _valid_token(user)
    db = MagicMock()
    with patch("backend.routers.auth.crud.get_user", return_value=user):
        resp = await _reset(
            MagicMock(),
            ResetPasswordRequest(token=token, new_password=NEW_PASSWORD),
            db,
        )

    assert resp["status"] == "success"
    assert verify_password(NEW_PASSWORD, user.hashed_password)  # password changed
    assert user.password_changed_at is not None  # sessions revoked
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_reset_password_is_single_use():
    """After a successful reset the same link must not work again (pv mismatch)."""
    user = _user()
    token = _valid_token(user)
    db = MagicMock()
    with patch("backend.routers.auth.crud.get_user", return_value=user):
        await _reset(
            MagicMock(),
            ResetPasswordRequest(token=token, new_password=NEW_PASSWORD),
            db,
        )

        # Replay the identical token — hash (and thus pv) has now changed.
        with pytest.raises(HTTPException) as ei:
            await _reset(
                MagicMock(),
                ResetPasswordRequest(
                    token=token, new_password="ThirdPass789"  # pragma: allowlist secret
                ),
                db,
            )
    assert ei.value.status_code == 400
    assert "already been used" in str(ei.value.detail)


@pytest.mark.asyncio
async def test_reset_password_rejects_malformed_token():
    db = MagicMock()
    with patch("backend.routers.auth.crud.get_user", return_value=_user()):
        with pytest.raises(HTTPException) as ei:
            await _reset(
                MagicMock(),
                ResetPasswordRequest(token="not-a-jwt", new_password=NEW_PASSWORD),
                db,
            )
    assert ei.value.status_code == 400
    assert "Invalid or expired" in str(ei.value.detail)


@pytest.mark.asyncio
async def test_reset_password_rejects_wrong_token_type():
    """An access token must not be accepted by the reset endpoint."""
    user = _user()
    access = create_access_token({"sub": user.id, "pv": password_fingerprint(user.hashed_password)})
    db = MagicMock()
    with patch("backend.routers.auth.crud.get_user", return_value=user):
        with pytest.raises(HTTPException) as ei:
            await _reset(
                MagicMock(),
                ResetPasswordRequest(token=access, new_password=NEW_PASSWORD),
                db,
            )
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_rejects_inactive_user():
    user = _user(active=False)
    token = _valid_token(user)
    db = MagicMock()
    with patch("backend.routers.auth.crud.get_user", return_value=user):
        with pytest.raises(HTTPException) as ei:
            await _reset(
                MagicMock(),
                ResetPasswordRequest(token=token, new_password=NEW_PASSWORD),
                db,
            )
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_rejects_reuse_of_current_password():
    user = _user()
    token = _valid_token(user)
    db = MagicMock()
    with patch("backend.routers.auth.crud.get_user", return_value=user):
        with pytest.raises(HTTPException) as ei:
            await _reset(
                MagicMock(),
                ResetPasswordRequest(token=token, new_password=OLD_PASSWORD),
                db,
            )
    assert ei.value.status_code == 400
    assert "different" in str(ei.value.detail)


@pytest.mark.asyncio
async def test_reset_password_enforces_password_policy():
    """A token-valid, non-reused password that fails the policy is rejected."""
    user = _user()
    token = _valid_token(user)
    db = MagicMock()
    with (
        patch("backend.routers.auth.crud.get_user", return_value=user),
        patch(
            "backend.routers.auth.password_policy.validate_password",
            return_value=(False, ["Password is too common"]),
        ),
    ):
        with pytest.raises(HTTPException) as ei:
            await _reset(
                MagicMock(),
                ResetPasswordRequest(token=token, new_password=NEW_PASSWORD),
                db,
            )
    assert ei.value.status_code == 400
    assert ei.value.detail["error"] == "WEAK_PASSWORD"
