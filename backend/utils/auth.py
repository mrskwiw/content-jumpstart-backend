"""
JWT authentication utilities with secret rotation support.
"""

from datetime import datetime, timedelta
from typing import Optional
import hashlib
import logging

import bcrypt
from jose import JWTError, jwt

from backend.config import settings
from backend.utils.secret_rotation import SecretManager

# Initialize logger
logger = logging.getLogger(__name__)

# Global secret manager instance (singleton pattern)
_secret_manager: Optional[SecretManager] = None
# Tracks whether the fallback warning has been emitted at startup
_fallback_warned: bool = False


def get_secret_manager() -> SecretManager:
    """
    Get or create singleton SecretManager instance.

    Emits a single startup log if no secrets are configured (i.e. fallback to
    settings.SECRET_KEY is in effect). The message is intentionally INFO, not
    WARNING, because the fallback is correct behaviour for deployments that
    don't use secret rotation.

    Returns:
        SecretManager instance
    """
    global _secret_manager, _fallback_warned
    if _secret_manager is None:
        _secret_manager = SecretManager()
        if not _secret_manager.get_active_secrets() and not _fallback_warned:
            logger.info(
                "SecretManager: no secrets configured — using settings.SECRET_KEY. "
                "Secret rotation is disabled. This is expected on deployments without a secrets store."
            )
            _fallback_warned = True
    return _secret_manager


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Hash a password"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def password_fingerprint(hashed_password: str) -> str:
    """
    Short, non-reversible fingerprint of a password hash.

    Embedded in access/refresh tokens as the ``pv`` (password version) claim.
    Because a bcrypt hash changes whenever the password changes, comparing a
    token's ``pv`` against the user's current fingerprint lets us reject tokens
    that were issued before a password change — i.e. revoke existing sessions on
    password change without a stateful blacklist. Tokens minted before this
    mechanism existed carry no ``pv`` and are treated as legacy (not rejected).
    """
    return hashlib.sha256(hashed_password.encode("utf-8")).hexdigest()[:16]


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token using primary secret from SecretManager.

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})

    # Use primary secret from SecretManager
    secret_manager = get_secret_manager()
    primary_secret = secret_manager.get_primary_secret()

    if not primary_secret:
        primary_secret = settings.SECRET_KEY

    encoded_jwt = jwt.encode(to_encode, primary_secret, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_mfa_setup_token(data: dict) -> str:
    """
    Create a short-lived, limited-scope JWT for MFA enrollment only.

    Used when a policy-required account (superuser / mfa_enforced) has not
    yet configured MFA.  The token type is "mfa_setup" — get_current_user
    rejects it, so it cannot be used to access any API endpoint except
    /mfa/enroll (which accepts both "access" and "mfa_setup").

    Expiry: 15 minutes — enough to scan the QR code.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire, "type": "mfa_setup"})

    secret_manager = get_secret_manager()
    primary_secret = secret_manager.get_primary_secret() or settings.SECRET_KEY
    return jwt.encode(to_encode, primary_secret, algorithm=settings.ALGORITHM)


def create_password_reset_token(data: dict) -> str:
    """
    Create a short-lived, single-use JWT for self-service password reset
    (GAP-AUTH-01).

    The token type is "password_reset" — get_current_user rejects it, so it
    grants no API access; only /auth/reset-password accepts it.

    Callers MUST include a "pv" claim = password_fingerprint(current hash). That
    makes the token single-use without any server-side store: the reset endpoint
    verifies "pv" still matches the user's current hash, and completing a reset
    changes the hash — so the same link (or any link minted before the change)
    can never be replayed. Expiry defaults to
    settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "password_reset"})

    secret_manager = get_secret_manager()
    primary_secret = secret_manager.get_primary_secret() or settings.SECRET_KEY
    return jwt.encode(to_encode, primary_secret, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Create JWT refresh token using primary secret from SecretManager.

    Args:
        data: Payload data to encode in the token

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})

    # Use primary secret from SecretManager
    secret_manager = get_secret_manager()
    primary_secret = secret_manager.get_primary_secret()

    if not primary_secret:
        primary_secret = settings.SECRET_KEY

    encoded_jwt = jwt.encode(to_encode, primary_secret, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and verify JWT token using all active secrets.

    Tries secrets in order (primary first). If a deprecated secret successfully
    decodes the token, a warning is logged to encourage token refresh.

    Args:
        token: JWT token to decode

    Returns:
        Decoded payload or None if invalid
    """
    secret_manager = get_secret_manager()
    active_secrets = secret_manager.get_active_secrets()

    if not active_secrets:
        active_secrets = [settings.SECRET_KEY]

    # Try each active secret in order (primary first)
    last_error = None
    for idx, secret in enumerate(active_secrets):
        try:
            payload = jwt.decode(token, secret, algorithms=[settings.ALGORITHM])

            # Log warning if using deprecated secret (not the primary)
            if idx > 0:
                logger.warning(
                    f"Token decoded with deprecated secret (index {idx}). "
                    "Client should refresh token to use latest secret."
                )

            return payload
        except JWTError as e:
            last_error = e
            continue

    # All secrets failed
    logger.debug(
        f"Token validation failed with all {len(active_secrets)} active secrets: {last_error}"
    )
    return None


def verify_token_type(token: str, expected_type: str) -> bool:
    """
    Verify token is of expected type (access or refresh).

    Args:
        token: JWT token to verify
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        True if token type matches, False otherwise
    """
    payload = decode_token(token)
    if not payload:
        return False
    return payload.get("type") == expected_type
