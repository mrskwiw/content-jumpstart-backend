"""P0 Security Tests — JWT Token Security

Tests for backend/utils/auth.py

Verifies that:
- Valid tokens are accepted
- Expired tokens are rejected (return None)
- Tampered tokens are rejected
- Wrong-algorithm tokens are rejected
- Token type enforcement prevents refresh tokens being used as access tokens
- Password hashing round-trips correctly
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from jose import jwt

from backend.utils.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
    verify_token_type,
)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = get_password_hash("secret123")
        assert hashed != "secret123"
        assert len(hashed) > 20

    def test_correct_password_verifies(self):
        hashed = get_password_hash("correct_horse_battery_staple")
        assert verify_password("correct_horse_battery_staple", hashed) is True

    def test_wrong_password_rejected(self):
        hashed = get_password_hash("correct_horse_battery_staple")
        assert verify_password("wrong_password", hashed) is False

    def test_empty_password_verifies_own_hash(self):
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True

    def test_different_hashes_for_same_password(self):
        """bcrypt salts must produce unique hashes each time."""
        h1 = get_password_hash("same_password")
        h2 = get_password_hash("same_password")
        assert h1 != h2


# ---------------------------------------------------------------------------
# Access token creation and decoding
# ---------------------------------------------------------------------------


class TestAccessToken:
    def test_created_token_decodes_successfully(self):
        token = create_access_token({"sub": "user@example.com"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user@example.com"

    def test_created_token_has_access_type(self):
        token = create_access_token({"sub": "user@example.com"})
        payload = decode_token(token)
        assert payload["type"] == "access"

    def test_created_token_has_expiry(self):
        token = create_access_token({"sub": "user@example.com"})
        payload = decode_token(token)
        assert "exp" in payload

    def test_custom_expiry_respected(self):
        """Token with 1-second TTL should still be decodable immediately."""
        token = create_access_token({"sub": "u"}, expires_delta=timedelta(seconds=1))
        payload = decode_token(token)
        assert payload is not None

    def test_expired_token_returns_none(self):
        """Token with negative TTL is already expired."""
        token = create_access_token({"sub": "u"}, expires_delta=timedelta(seconds=-1))
        payload = decode_token(token)
        assert payload is None

    def test_tampered_token_rejected(self):
        token = create_access_token({"sub": "user@example.com"})
        # Flip a character in the payload segment
        parts = token.split(".")
        payload_b64 = parts[1]
        tampered = payload_b64[:-1] + ("A" if payload_b64[-1] != "A" else "B")
        tampered_token = ".".join([parts[0], tampered, parts[2]])
        assert decode_token(tampered_token) is None

    def test_wrong_secret_rejected(self):
        from backend.config import settings

        wrong_secret_token = jwt.encode(
            {"sub": "u", "type": "access"}, "wrong_secret", algorithm=settings.ALGORITHM
        )
        assert decode_token(wrong_secret_token) is None

    def test_wrong_algorithm_rejected(self):
        """Token signed with a different algorithm must not decode."""
        # HS512 vs the default HS256 (or whatever settings.ALGORITHM is)
        from backend.config import settings

        alt_alg = "HS512" if settings.ALGORITHM == "HS256" else "HS256"
        from datetime import datetime

        from jose import jwt as _jwt

        # Get the primary secret to sign with correct secret but wrong alg
        from backend.utils.auth import get_secret_manager

        secret_manager = get_secret_manager()
        secret = secret_manager.get_primary_secret() or settings.SECRET_KEY
        wrong_alg_token = _jwt.encode({"sub": "u", "type": "access"}, secret, algorithm=alt_alg)
        assert decode_token(wrong_alg_token) is None


# ---------------------------------------------------------------------------
# Refresh token creation and decoding
# ---------------------------------------------------------------------------


class TestRefreshToken:
    def test_created_refresh_token_decodes(self):
        token = create_refresh_token({"sub": "user@example.com"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user@example.com"

    def test_created_refresh_token_has_refresh_type(self):
        token = create_refresh_token({"sub": "u"})
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_refresh_token_has_longer_expiry_than_access(self):
        """Refresh token exp should be greater than access token exp."""
        access = create_access_token({"sub": "u"})
        refresh = create_refresh_token({"sub": "u"})
        access_exp = decode_token(access)["exp"]
        refresh_exp = decode_token(refresh)["exp"]
        assert refresh_exp > access_exp


# ---------------------------------------------------------------------------
# Token type enforcement
# ---------------------------------------------------------------------------


class TestVerifyTokenType:
    def test_access_token_validates_as_access(self):
        token = create_access_token({"sub": "u"})
        assert verify_token_type(token, "access") is True

    def test_access_token_rejected_as_refresh(self):
        """Access token must NOT be accepted where refresh token is required."""
        token = create_access_token({"sub": "u"})
        assert verify_token_type(token, "refresh") is False

    def test_refresh_token_validates_as_refresh(self):
        token = create_refresh_token({"sub": "u"})
        assert verify_token_type(token, "refresh") is True

    def test_refresh_token_rejected_as_access(self):
        """Refresh token must NOT be accepted where access token is required."""
        token = create_refresh_token({"sub": "u"})
        assert verify_token_type(token, "access") is False

    def test_invalid_token_returns_false(self):
        assert verify_token_type("not.a.token", "access") is False

    def test_expired_token_returns_false(self):
        token = create_access_token({"sub": "u"}, expires_delta=timedelta(seconds=-1))
        assert verify_token_type(token, "access") is False


# ---------------------------------------------------------------------------
# decode_token edge cases
# ---------------------------------------------------------------------------


class TestDecodeTokenEdgeCases:
    def test_empty_string_returns_none(self):
        assert decode_token("") is None

    def test_garbage_returns_none(self):
        assert decode_token("garbage.garbage.garbage") is None

    def test_unsigned_token_rejected(self):
        """alg=none (unsigned) must be rejected."""
        import base64
        import json

        header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
        payload = (
            base64.urlsafe_b64encode(b'{"sub":"attacker","type":"access"}').rstrip(b"=").decode()
        )
        unsigned_token = f"{header}.{payload}."
        assert decode_token(unsigned_token) is None
