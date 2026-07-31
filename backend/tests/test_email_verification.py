"""GAP-AUTH-02 email verification — handler-level unit tests.

The endpoints are exercised through their undecorated handlers (``__wrapped__``) so
the slowapi rate-limit wrapper doesn't need a live Request/app state. Background-task
*enqueuing* is asserted via ``len(bg.tasks)`` (the repo pattern from
``test_password_reset.py``) — reliable regardless of whether the test transport runs
the task. Token minting/decoding is real (no mock), so the ``email_verify`` token type
is genuinely verified.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException

from backend.models import User
from backend.routers.auth import register_user, resend_verification, verify_email
from backend.schemas.auth import (
    ResendVerificationRequest,
    UserCreate,
    VerifyEmailRequest,
)
from backend.utils.auth import (
    create_access_token,
    create_email_verification_token,
    get_password_hash,
)

_register = getattr(register_user, "__wrapped__", register_user)
_resend = getattr(resend_verification, "__wrapped__", resend_verification)
_verify = getattr(verify_email, "__wrapped__", verify_email)

# Satisfies the full password policy (12+ chars, upper/lower/digit, special, no runs).
STRONG = "Zephyr!K4mtby"  # pragma: allowlist secret  # noqa: S105 - test value


def _user(verified: bool = False) -> User:
    return User(
        id="u1",
        email="user@example.com",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        hashed_password=get_password_hash(STRONG),
        email_verified=verified,
        created_at=datetime.now(timezone.utc),
    )


# ── registration enqueues a verification email ──────────────────────────────────


@pytest.mark.asyncio
async def test_register_schedules_verification_email():
    bg = BackgroundTasks()
    with (
        patch("backend.routers.auth.crud.get_user_by_email", return_value=None),
        patch("backend.routers.auth.crud.create_user", return_value=_user()),
    ):
        resp = await _register(
            MagicMock(),
            UserCreate(email="user@example.com", password=STRONG, full_name="Test User"),
            bg,
            MagicMock(),
        )
    assert len(bg.tasks) == 1  # verification email enqueued
    assert resp.user.email_verified is False


# ── resend ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resend_schedules_for_unverified():
    bg = BackgroundTasks()
    with patch("backend.routers.auth.crud.get_user_by_email", return_value=_user(verified=False)):
        resp = await _resend(
            MagicMock(), ResendVerificationRequest(email="user@example.com"), bg, MagicMock()
        )
    assert resp["status"] == "success"
    assert len(bg.tasks) == 1


@pytest.mark.asyncio
async def test_resend_no_email_for_already_verified():
    bg = BackgroundTasks()
    with patch("backend.routers.auth.crud.get_user_by_email", return_value=_user(verified=True)):
        await _resend(
            MagicMock(), ResendVerificationRequest(email="user@example.com"), bg, MagicMock()
        )
    assert len(bg.tasks) == 0  # nothing to verify → no send


@pytest.mark.asyncio
async def test_resend_no_email_for_unknown():
    bg = BackgroundTasks()
    with patch("backend.routers.auth.crud.get_user_by_email", return_value=None):
        resp = await _resend(
            MagicMock(), ResendVerificationRequest(email="nobody@example.com"), bg, MagicMock()
        )
    assert resp["status"] == "success"  # generic (no enumeration)
    assert len(bg.tasks) == 0


# ── verify-email ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_email_sets_verified_and_commits():
    user = _user(verified=False)
    db = MagicMock()
    token = create_email_verification_token({"sub": user.id})
    with patch("backend.routers.auth.crud.get_user", return_value=user):
        resp = await _verify(MagicMock(), VerifyEmailRequest(token=token), db)
    assert user.email_verified is True
    assert user.email_verified_at is not None
    assert resp["status"] == "success"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_verify_email_idempotent_no_write_when_already_verified():
    user = _user(verified=True)
    db = MagicMock()
    token = create_email_verification_token({"sub": user.id})
    with patch("backend.routers.auth.crud.get_user", return_value=user):
        resp = await _verify(MagicMock(), VerifyEmailRequest(token=token), db)
    assert resp["status"] == "success"
    db.commit.assert_not_called()  # already verified → no redundant write


@pytest.mark.asyncio
async def test_verify_email_rejects_access_token():
    # An access token is not an email_verify token.
    token = create_access_token(data={"sub": "u1"})
    with pytest.raises(HTTPException) as exc:
        await _verify(MagicMock(), VerifyEmailRequest(token=token), MagicMock())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_verify_email_rejects_malformed_token():
    with pytest.raises(HTTPException) as exc:
        await _verify(MagicMock(), VerifyEmailRequest(token="not-a-jwt"), MagicMock())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_verify_email_rejects_unknown_user():
    token = create_email_verification_token({"sub": "ghost"})
    with patch("backend.routers.auth.crud.get_user", return_value=None):
        with pytest.raises(HTTPException) as exc:
            await _verify(MagicMock(), VerifyEmailRequest(token=token), MagicMock())
    assert exc.value.status_code == 400
