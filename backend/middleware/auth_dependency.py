"""
Authentication dependency for protected routes.
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from backend.services import crud
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.services.session_revocation_service import is_token_revoked
from backend.services.verification_gate import email_verification_enforced
from backend.utils.auth import decode_token, password_fingerprint


class HTTPBearerWith401(HTTPBearer):
    """Custom HTTPBearer that returns 401 instead of 403 for missing credentials"""

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        try:
            result = await super().__call__(request)
        except HTTPException as e:
            # Convert 403 to 401 for missing/invalid credentials
            if e.status_code == status.HTTP_403_FORBIDDEN:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=e.detail,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise
        if result is None:
            # auto_error=True (default) always raises before returning None,
            # but the parent's return type is Optional — guard for mypy.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return result


security = HTTPBearerWith401()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to get current authenticated user from JWT token.

    Usage:
        @app.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.email}
    """
    import logging

    logger = logging.getLogger(__name__)

    token = credentials.credentials
    logger.debug(f"AUTH: Received token (first 20 chars): {token[:20]}...")

    payload = decode_token(token)

    if not payload:
        logger.warning("AUTH: Invalid token - decode_token returned None")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"AUTH: Token payload: type={payload.get('type')}, sub={payload.get('sub')}")

    # Check token type
    if payload.get("type") != "access":
        logger.warning(f"AUTH: Invalid token type: {payload.get('type')}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user_id = payload.get("sub")
    if not user_id:
        logger.warning("AUTH: Token payload missing 'sub' field")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = crud.get_user(db, user_id)
    if not user:
        logger.warning(f"AUTH: User not found in database: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"AUTH: Found user: {user.email}, is_active={user.is_active}")

    if not user.is_active:
        logger.warning(f"AUTH: User is inactive: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Session revocation on password change:
    #  - tokens with a "pv" claim must match the current password hash (race-free)
    #  - legacy tokens with no "pv" are rejected once the password has EVER changed,
    #    since any legitimately-current token would carry a matching "pv".
    token_pv = payload.get("pv")
    if token_pv is not None:
        if token_pv != password_fingerprint(user.hashed_password):
            logger.warning(f"AUTH: Stale token (password changed) for {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    elif user.password_changed_at is not None:
        logger.warning(f"AUTH: Legacy token rejected after password change: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Explicit revocation (GAP-AUTH-03): this token's jti was blacklisted, or all of
    # the user's sessions were revoked on demand (independent of password change).
    if is_token_revoked(db, payload):
        logger.warning(f"AUTH: Revoked token rejected for {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session revoked. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # GAP-AUTH-02: when email verification is enforced, gate EVERY authenticated
    # request (not just /login) so a registration-issued token can't bypass it.
    # The verify/resend endpoints are unauthenticated, so they stay reachable.
    if email_verification_enforced() and not user.email_verified:
        logger.warning(f"AUTH: Unverified email blocked for {user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address to continue.",
        )

    logger.debug(f"AUTH: Successfully authenticated user: {user.email}")
    return user


async def require_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that requires the authenticated user to be a superuser.

    Use for instance-wide/admin operations (e.g. full-database export).
    Returns 403 for non-superusers.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


async def get_current_user_for_mfa_setup(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency for the MFA enrollment endpoint only.

    Accepts EITHER a normal "access" token OR a limited "mfa_setup" token so
    that policy-required accounts (superuser / mfa_enforced) can call /mfa/enroll
    immediately after receiving the setup token at login — before they have a full
    access token.  All other endpoints use get_current_user, which rejects
    "mfa_setup" tokens.
    """
    import logging as _logging

    _logger = _logging.getLogger(__name__)

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_type = payload.get("type")
    if token_type not in ("access", "mfa_setup"):
        _logger.warning(f"MFA-enroll auth: unexpected token type {token_type!r}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = crud.get_user(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Honour explicit revocation on the MFA-enrollment path too (GAP-AUTH-03).
    if is_token_revoked(db, payload):
        _logger.warning(f"MFA-enroll auth: revoked token rejected for {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session revoked. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # GAP-AUTH-02: this dependency is an alternate front door, so it carries the same
    # verification gate as get_current_user — "every authenticated request" has to mean
    # every one, or an unverified account could still mutate its MFA state.
    if email_verification_enforced() and not user.email_verified:
        _logger.warning(f"MFA-enroll auth: unverified email blocked for {user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address to continue.",
        )

    return user
