"""
Admin-only user management endpoints (TR-023).

Provides admin capabilities for:
- User activation/deactivation
- Promoting users to admin
- Listing all users
- User management operations

All endpoints require admin (is_superuser=True) authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.models import User
from backend.schemas.auth import UserResponse
from backend.services import crud
from backend.utils.logger import logger

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to verify user is an admin (superuser).

    Raises:
        HTTPException 403: User is not an admin

    Returns:
        User instance if admin
    """
    if not current_user.is_superuser:
        logger.warning(
            f"Admin access denied: User {current_user.email} "
            f"attempted admin operation without superuser privileges"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


@router.post("/users/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    """
    Admin endpoint to activate a user account (TR-023).

    Sets is_active=True, allowing the user to authenticate.

    Args:
        user_id: User ID to activate
        admin: Current admin user (verified by require_admin dependency)

    Returns:
        Updated user data

    Raises:
        404: User not found
        403: Not an admin
    """
    logger.info(f"Admin {admin.email} activating user {user_id}")

    user = crud.get_user(db, user_id)
    if not user:
        logger.warning(f"Activation failed: User {user_id} not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update activation status
    user.is_active = True
    db.commit()
    db.refresh(user)

    logger.info(f"User {user.email} activated by admin {admin.email}")

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/users/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    """
    Admin endpoint to deactivate a user account (TR-023).

    Sets is_active=False, preventing the user from authenticating.

    Args:
        user_id: User ID to deactivate
        admin: Current admin user (verified by require_admin dependency)

    Returns:
        Updated user data

    Raises:
        404: User not found
        403: Not an admin
        400: Cannot deactivate yourself
    """
    logger.info(f"Admin {admin.email} deactivating user {user_id}")

    # Prevent admin from deactivating themselves
    if user_id == admin.id:
        logger.warning(f"Admin {admin.email} attempted to deactivate their own account")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account"
        )

    user = crud.get_user(db, user_id)
    if not user:
        logger.warning(f"Deactivation failed: User {user_id} not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update activation status
    user.is_active = False
    db.commit()
    db.refresh(user)

    logger.info(f"User {user.email} deactivated by admin {admin.email}")

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/users/{user_id}/promote", response_model=UserResponse)
async def promote_to_admin(
    user_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    """
    Admin endpoint to promote a user to admin (superuser) status (TR-023).

    Sets is_superuser=True, granting admin privileges.

    IMPORTANT: Use this with caution. Admins have full access to all resources.

    Args:
        user_id: User ID to promote
        admin: Current admin user (verified by require_admin dependency)

    Returns:
        Updated user data

    Raises:
        404: User not found
        403: Not an admin
        400: User is already an admin
    """
    logger.info(f"Admin {admin.email} promoting user {user_id} to admin")

    user = crud.get_user(db, user_id)
    if not user:
        logger.warning(f"Promotion failed: User {user_id} not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.is_superuser:
        logger.warning(f"Promotion failed: User {user.email} is already an admin")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User is already an admin"
        )

    # Promote to admin
    user.is_superuser = True
    db.commit()
    db.refresh(user)

    logger.info(f"User {user.email} promoted to admin by {admin.email}")

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/users/{user_id}/demote", response_model=UserResponse)
async def demote_from_admin(
    user_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    """
    Admin endpoint to demote a user from admin (superuser) status (TR-023).

    Sets is_superuser=False, revoking admin privileges.

    Args:
        user_id: User ID to demote
        admin: Current admin user (verified by require_admin dependency)

    Returns:
        Updated user data

    Raises:
        404: User not found
        403: Not an admin
        400: Cannot demote yourself or user is not an admin
    """
    logger.info(f"Admin {admin.email} demoting user {user_id} from admin")

    # Prevent admin from demoting themselves
    if user_id == admin.id:
        logger.warning(f"Admin {admin.email} attempted to demote themselves")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote your own admin privileges",
        )

    user = crud.get_user(db, user_id)
    if not user:
        logger.warning(f"Demotion failed: User {user_id} not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.is_superuser:
        logger.warning(f"Demotion failed: User {user.email} is not an admin")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not an admin")

    # Demote from admin
    user.is_superuser = False
    db.commit()
    db.refresh(user)

    logger.info(f"User {user.email} demoted from admin by {admin.email}")

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("/users", response_model=List[UserResponse])
async def list_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Admin endpoint to list all users (TR-023).

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        admin: Current admin user (verified by require_admin dependency)

    Returns:
        List of all users

    Raises:
        403: Not an admin
    """
    logger.debug(f"Admin {admin.email} listing all users (skip={skip}, limit={limit})")

    users = db.query(User).offset(skip).limit(limit).all()

    return [
        UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        for user in users
    ]


@router.get("/users/inactive", response_model=List[UserResponse])
async def list_inactive_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Admin endpoint to list inactive users awaiting activation (TR-023).

    Useful for reviewing pending user registrations.

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        admin: Current admin user (verified by require_admin dependency)

    Returns:
        List of inactive users

    Raises:
        403: Not an admin
    """
    logger.debug(f"Admin {admin.email} listing inactive users (skip={skip}, limit={limit})")

    users = db.query(User).filter(not User.is_active).offset(skip).limit(limit).all()

    return [
        UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        for user in users
    ]
