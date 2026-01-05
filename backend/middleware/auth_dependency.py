"""
Authentication dependency for protected routes.
"""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from backend.services import crud
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.utils.auth import decode_token


class HTTPBearerWith401(HTTPBearer):
    """Custom HTTPBearer that returns 401 instead of 403 for missing credentials"""
    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        try:
            return await super().__call__(request)
        except HTTPException as e:
            # Convert 403 to 401 for missing/invalid credentials
            if e.status_code == status.HTTP_403_FORBIDDEN:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=e.detail,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise


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

    logger.debug(f"AUTH: Successfully authenticated user: {user.email}")
    return user
