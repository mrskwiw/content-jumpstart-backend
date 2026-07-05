"""
Unit tests for JWT auth utilities and auth dependency handling.
"""

from types import SimpleNamespace

import pytest
from jose import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from backend.config import settings
from backend.middleware.auth_dependency import HTTPBearerWith401, get_current_user
from backend.utils import auth as auth_utils


class FakeSecretManager:
    def __init__(self, primary_secret: str, active_secrets: list[str] | None = None):
        self.primary_secret = primary_secret
        self.active_secrets = active_secrets or [primary_secret]

    def get_primary_secret(self):
        return self.primary_secret

    def get_active_secrets(self):
        return list(self.active_secrets)


class TestAuthUtilities:
    def test_password_hash_round_trip(self):
        hashed = auth_utils.get_password_hash("s3cret-password")

        assert hashed != "s3cret-password"
        assert auth_utils.verify_password("s3cret-password", hashed) is True
        assert auth_utils.verify_password("wrong-password", hashed) is False

    def test_create_and_decode_access_token(self, monkeypatch):
        fake_manager = FakeSecretManager(primary_secret="a" * 32)
        monkeypatch.setattr(auth_utils, "get_secret_manager", lambda: fake_manager)

        token = auth_utils.create_access_token({"sub": "user-1"})
        payload = auth_utils.decode_token(token)

        assert payload["sub"] == "user-1"
        assert payload["type"] == "access"

    def test_create_refresh_token_uses_primary_secret(self, monkeypatch):
        fake_manager = FakeSecretManager(primary_secret="b" * 32)
        monkeypatch.setattr(auth_utils, "get_secret_manager", lambda: fake_manager)

        token = auth_utils.create_refresh_token({"sub": "user-2"})
        payload = jwt.decode(token, "b" * 32, algorithms=[settings.ALGORITHM])

        assert payload["sub"] == "user-2"
        assert payload["type"] == "refresh"

    def test_decode_token_falls_back_to_secondary_secret(self, monkeypatch):
        fake_manager = FakeSecretManager(
            primary_secret="p" * 32,
            active_secrets=["p" * 32, "s" * 32],
        )
        monkeypatch.setattr(auth_utils, "get_secret_manager", lambda: fake_manager)

        token = jwt.encode(
            {"sub": "user-3", "type": "access"},
            "s" * 32,
            algorithm=settings.ALGORITHM,
        )

        payload = auth_utils.decode_token(token)
        assert payload["sub"] == "user-3"

    def test_verify_token_type(self, monkeypatch):
        fake_manager = FakeSecretManager(primary_secret="c" * 32)
        monkeypatch.setattr(auth_utils, "get_secret_manager", lambda: fake_manager)

        token = auth_utils.create_access_token({"sub": "user-4"})

        assert auth_utils.verify_token_type(token, "access") is True
        assert auth_utils.verify_token_type(token, "refresh") is False

    def test_decode_token_returns_none_for_invalid_signature(self, monkeypatch):
        fake_manager = FakeSecretManager(primary_secret="d" * 32)
        monkeypatch.setattr(auth_utils, "get_secret_manager", lambda: fake_manager)

        token = jwt.encode(
            {"sub": "user-5", "type": "access"}, "o" * 32, algorithm=settings.ALGORITHM
        )

        assert auth_utils.decode_token(token) is None


class TestAuthDependency:
    @pytest.mark.asyncio
    async def test_http_bearer_missing_credentials_returns_401(self):
        bearer = HTTPBearerWith401()
        request = Request({"type": "http", "headers": []})

        with pytest.raises(HTTPException) as exc:
            await bearer(request)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, monkeypatch):
        user = SimpleNamespace(email="user@example.com", is_active=True)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        db = SimpleNamespace()

        monkeypatch.setattr(
            "backend.middleware.auth_dependency.decode_token",
            lambda token: {"sub": "user-1", "type": "access"},
        )
        monkeypatch.setattr(
            "backend.middleware.auth_dependency.crud.get_user", lambda db_obj, user_id: user
        )

        result = await get_current_user(credentials=credentials, db=db)

        assert result is user

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, monkeypatch):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        db = SimpleNamespace()

        monkeypatch.setattr("backend.middleware.auth_dependency.decode_token", lambda token: None)

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials, db=db)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.value.detail == "Invalid authentication credentials"

    @pytest.mark.asyncio
    async def test_get_current_user_rejects_refresh_token(self, monkeypatch):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        db = SimpleNamespace()

        monkeypatch.setattr(
            "backend.middleware.auth_dependency.decode_token",
            lambda token: {"sub": "user-1", "type": "refresh"},
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials, db=db)

        assert exc.value.detail == "Invalid token type"

    @pytest.mark.asyncio
    async def test_get_current_user_requires_user(self, monkeypatch):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        db = SimpleNamespace()

        monkeypatch.setattr(
            "backend.middleware.auth_dependency.decode_token", lambda token: {"type": "access"}
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials, db=db)

        assert exc.value.detail == "Invalid token payload"

    @pytest.mark.asyncio
    async def test_get_current_user_rejects_missing_user(self, monkeypatch):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        db = SimpleNamespace()

        monkeypatch.setattr(
            "backend.middleware.auth_dependency.decode_token",
            lambda token: {"sub": "user-1", "type": "access"},
        )
        monkeypatch.setattr(
            "backend.middleware.auth_dependency.crud.get_user", lambda db_obj, user_id: None
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials, db=db)

        assert exc.value.detail == "User not found"

    @pytest.mark.asyncio
    async def test_get_current_user_rejects_inactive_user(self, monkeypatch):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        db = SimpleNamespace()
        user = SimpleNamespace(email="user@example.com", is_active=False)

        monkeypatch.setattr(
            "backend.middleware.auth_dependency.decode_token",
            lambda token: {"sub": "user-1", "type": "access"},
        )
        monkeypatch.setattr(
            "backend.middleware.auth_dependency.crud.get_user", lambda db_obj, user_id: user
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials, db=db)

        assert exc.value.detail == "Inactive user"
