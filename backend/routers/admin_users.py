"""
Admin-only user management endpoints (TR-023).

Provides admin capabilities for:
- User activation/deactivation
- Promoting users to admin
- Listing all users
- User management operations

All endpoints require admin (is_superuser=True) authentication.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.config import settings
from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.models import User
from backend.schemas.auth import (
    AdminUserCreate,
    PasswordResetRequest,
    UserResponse,
    UserStatsResponse,
)
from backend.schemas.credit_schemas import GrantCreditsRequest, GrantCreditsResponse
from backend.services import credit_service, crud
from backend.utils.auth import get_password_hash
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


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to verify user is a super admin (original system administrator).

    Super admins are defined in SUPER_ADMIN_EMAILS environment variable.
    Only these users can perform privileged operations like granting free credits.

    Raises:
        HTTPException 403: User is not a super admin

    Returns:
        User instance if super admin
    """
    if not current_user.is_superuser:
        logger.warning(f"Super admin access denied: User {current_user.email} " f"is not an admin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required",
        )

    # Check if user email is in super admin list
    super_admin_emails = settings.super_admin_emails_list
    if current_user.email.lower() not in super_admin_emails:
        logger.warning(
            f"Super admin access denied: User {current_user.email} "
            f"is admin but not in SUPER_ADMIN_EMAILS list"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required. Only original system administrators can perform this action.",
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
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


@router.post("/users/{user_id}/reset-password", response_model=UserResponse)
def reset_user_password(
    user_id: str,
    request: "PasswordResetRequest",
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Admin endpoint to reset a user's password (TR-023).

    Allows administrators to reset any user's password. The new password
    must meet the same strength requirements as during registration.

    Args:
        user_id: ID of the user whose password will be reset
        request: PasswordResetRequest containing new_password
        admin: Current admin user (verified by require_admin dependency)

    Returns:
        UserResponse: Updated user information

    Raises:
        HTTPException 404: User not found
        HTTPException 400: Password validation failed
    """
    # Find the user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User not found: {user_id}"
        )

    # Hash and update the password; stamp the change so the target user's existing
    # sessions are revoked (incl. legacy tokens without a "pv" claim) — same
    # session-revocation guarantee as self-service change-password.
    from datetime import datetime, timezone

    user.hashed_password = get_password_hash(request.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    logger.info(f"Admin {admin.email} reset password for user {user.email}")

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

    users = db.query(User).filter(User.is_active.is_(False)).offset(skip).limit(limit).all()

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


@router.get("/users/stats", response_model=UserStatsResponse)
async def get_user_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Admin endpoint to get user statistics.

    Returns counts for total, active, inactive, and admin users.

    Args:
        admin: Current admin user (verified by require_admin dependency)

    Returns:
        User statistics

    Raises:
        403: Not an admin
    """
    logger.debug(f"Admin {admin.email} fetching user stats")

    total = db.query(User).count()
    active = db.query(User).filter(User.is_active.is_(True)).count()
    inactive = db.query(User).filter(User.is_active.is_(False)).count()
    admins = db.query(User).filter(User.is_superuser.is_(True)).count()

    return UserStatsResponse(
        total=total,
        active=active,
        inactive=inactive,
        admins=admins,
    )


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    user_data: AdminUserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Admin endpoint to create a new user.

    Creates a user with the specified email, password, name, and optionally
    grants admin privileges.

    Args:
        user_data: User creation data (email, password, full_name, is_superuser)
        admin: Current admin user (verified by require_admin dependency)

    Returns:
        Created user data

    Raises:
        403: Not an admin
        400: Email already registered
    """
    logger.info(f"Admin {admin.email} creating new user: {user_data.email}")

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        logger.warning(f"User creation failed: Email {user_data.email} already registered")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    new_user = User(
        id=f"user-{uuid.uuid4().hex[:12]}",
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
        is_superuser=user_data.is_superuser,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(
        f"User {new_user.email} created by admin {admin.email} "
        f"(superuser={new_user.is_superuser})"
    )

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        is_active=new_user.is_active,
        is_superuser=new_user.is_superuser,
        created_at=new_user.created_at,
        updated_at=new_user.updated_at,
    )


@router.post("/credits/grant", response_model=GrantCreditsResponse)
async def grant_credits(
    request: GrantCreditsRequest,
    db: Session = Depends(get_db),
    super_admin: User = Depends(require_super_admin),
):
    """
    Super admin endpoint to grant free credits to a user (Task #51).

    Only original system administrators (defined in SUPER_ADMIN_EMAILS env var)
    can grant free credits. This prevents abuse and ensures accountability.

    Use cases:
    - Reward beta testers or early adopters
    - Compensate users for service issues
    - Promotional campaigns
    - Customer support resolutions

    Args:
        request: Grant credits request (user_id, credits, reason)
        super_admin: Current super admin user (verified by require_super_admin dependency)

    Returns:
        Grant credits response with updated balance

    Raises:
        403: Not a super admin
        404: User not found
        400: Invalid credit amount
    """
    logger.info(
        f"Super admin {super_admin.email} granting {request.credits} credits "
        f"to user {request.user_id}. Reason: {request.reason}"
    )

    # Find the target user
    user = crud.get_user(db, request.user_id)
    if not user:
        logger.warning(f"Grant credits failed: User {request.user_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {request.user_id}",
        )

    # Grant via the lot-aware service (a direct `credit_balance +=` would create
    # no lot and be silently overwritten by the next _sync — S-01.4b-ii review).
    old_balance = credit_service.live_balance(db, user.id)
    credit_service.admin_adjust_credits(
        db,
        user.id,
        request.credits,
        description=request.reason or "Admin credit grant",
        admin_user_id=super_admin.id,
    )
    db.refresh(user)
    new_balance = credit_service.live_balance(db, user.id)

    logger.info(
        f"Granted {request.credits} credits to {user.email} "
        f"(balance: {old_balance} → {new_balance}). "
        f"Granted by: {super_admin.email}"
    )

    return GrantCreditsResponse(
        user_email=user.email,
        credits_granted=request.credits,
        new_balance=new_balance,
        reason=request.reason,
        granted_by=super_admin.email,
    )
