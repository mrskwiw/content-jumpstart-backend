"""
FastAPI dependencies for authentication and authorization.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..models.user import User
from .security import decode_token

# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.

    This dependency extracts the JWT token from the Authorization header,
    decodes it, and retrieves the user from the database.

    Args:
        credentials: HTTP Bearer credentials from request header
        db: Database session

    Returns:
        User object for the authenticated user

    Raises:
        HTTPException: If token is invalid or user not found (401 Unauthorized)
    """
    token = credentials.credentials

    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user ID from token
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Retrieve user from database
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Verify that the current user has admin privileges.

    This dependency ensures the user has either "admin" or "agency" role.

    Args:
        current_user: Authenticated user from get_current_user dependency

    Returns:
        User object if user is admin/agency

    Raises:
        HTTPException: If user doesn't have sufficient permissions (403 Forbidden)
    """
    if current_user.role not in ["admin", "agency"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin or agency role required.",
        )

    return current_user
