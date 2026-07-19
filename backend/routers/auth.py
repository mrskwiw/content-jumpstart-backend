"""
Authentication router - login, refresh token, user creation.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from backend.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    TokenResponse,
    UserCreate,
)
from backend.services import crud
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.models import User
from backend.utils.password_policy import password_policy
from backend.utils.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    password_fingerprint,
    verify_password,
    verify_token_type,
)
from backend.utils.http_rate_limiter import strict_limiter, standard_limiter
from backend.config import settings

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
@strict_limiter.limit("10/hour")  # TR-004: Prevent brute force attacks
async def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.
    Returns access and refresh tokens.

    Rate limit: 10/hour per IP (prevents brute force password attacks)
    """
    # Get user by email
    user = crud.get_user_by_email(db, login_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # MFA disabled by operator decision — password-only login for all accounts.
    # Re-enable by restoring should_enforce_mfa() and the TOTP block. See BUGS.md #172.

    # Create tokens (bind to current password version for session revocation)
    token_data = {"sub": user.id, "pv": password_fingerprint(user.hashed_password)}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    # Import UserResponse
    from backend.schemas.auth import UserResponse

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )


@router.post("/change-password", status_code=status.HTTP_200_OK)
@standard_limiter.limit("20/hour")  # TR-004: limit self-service password churn
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Change the authenticated user's own password (self-service).

    Requires the current password for re-authentication, enforces the strong
    password policy, and rejects reusing the current password.

    Rate limit: 20/hour per IP+user.
    """
    # Re-authenticate with the current password.
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Reject a no-op change so "new password" is genuinely new.
    if verify_password(body.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )

    # Enforce the full strong-password policy (TR-013).
    is_valid, password_errors = password_policy.validate_password(body.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "WEAK_PASSWORD",
                "message": "Password does not meet security requirements",
                "requirements": password_errors,
            },
        )

    current_user.hashed_password = get_password_hash(body.new_password)
    db.add(current_user)
    db.commit()

    from backend.utils.logger import logger

    logger.info(f"Password changed for user {current_user.email} (id={current_user.id})")
    return {"status": "success", "message": "Password updated successfully"}


@router.post("/refresh", response_model=RefreshTokenResponse)
@standard_limiter.limit("100/hour")  # TR-004: Normal operation, moderate limit
async def refresh_token(
    request: Request, refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    Returns new access and refresh tokens (without user data).

    Rate limit: 100/hour per IP+user (normal operation)
    """
    # Verify refresh token
    if not verify_token_type(refresh_data.refresh_token, "refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Decode token
    payload = decode_token(refresh_data.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Verify user exists and is active
    user = crud.get_user(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Reject a refresh token issued before the current password (session revocation).
    # Legacy tokens without "pv" are allowed.
    token_pv = payload.get("pv")
    if token_pv is not None and token_pv != password_fingerprint(user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
        )

    # Create new tokens (re-bind to current password version)
    token_data = {"sub": user.id, "pv": password_fingerprint(user.hashed_password)}
    access_token = create_access_token(data=token_data)
    new_refresh_token = create_refresh_token(data=token_data)

    return RefreshTokenResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@strict_limiter.limit("3/hour")  # TR-023: Prevent spam account creation
async def register_user(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user and return authentication tokens.

    SECURITY (TR-023): Admin-only registration recommended for internal tools.
    To enable admin-only mode, uncomment the admin authentication check below.

    Current mode: Self-registration with strict rate limiting (3/hour per IP)

    Protection layers:
    - Rate limiting: 3/hour per IP address
    - Email validation: Pydantic EmailStr
    - Password strength: Min 8 chars, uppercase, lowercase, digit
    - Mass assignment protection: extra='forbid' in schema
    - Duplicate prevention: Email uniqueness check
    - New users inactive by default: Requires admin activation
    """

    # TR-013: Enforce strong password policy
    is_valid, password_errors = password_policy.validate_password(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "WEAK_PASSWORD",
                "message": "Password does not meet security requirements",
                "requirements": password_errors,
            },
        )
    # ============================================================
    # TR-023: OPTIONAL ADMIN-ONLY REGISTRATION
    # ============================================================
    # Uncomment this block to require admin authentication:
    #
    # from backend.middleware.auth_dependency import get_current_user
    # from backend.models import User as AuthUser
    # current_admin: AuthUser = Depends(get_current_user)
    #
    # if not current_admin.is_superuser:
    #     from backend.utils.logger import logger
    #     logger.warning(
    #         f"Registration denied: Non-admin {current_admin.email} "
    #         f"attempted to create user {user_data.email}"
    #     )
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Admin privileges required to create new users"
    #     )
    # ============================================================

    from backend.utils.logger import logger

    # Log registration attempt
    logger.info(
        f"Registration attempt for email: {user_data.email} "
        f"from IP: {request.client.host if request.client else 'unknown'}"
    )

    # Check if user already exists
    existing_user = crud.get_user_by_email(db, user_data.email)
    if existing_user:
        logger.warning(f"Registration rejected: Email already registered: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password
    hashed_password = get_password_hash(user_data.password)

    # TR-023: In production, users start INACTIVE (requires admin activation).
    # In DEBUG_MODE, activate immediately and grant extra credits for testing.
    starting_credits = settings.DEBUG_CREDITS if settings.DEBUG_MODE else settings.STARTING_CREDITS
    user = crud.create_user(
        db,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=settings.DEBUG_MODE,  # Active immediately in debug, inactive in prod
        credit_balance=starting_credits,
    )

    logger.info(
        f"User created successfully: {user.email} (id={user.id}, is_active=False). "
        f"Admin activation required."
    )

    # TR-023: Return tokens but user cannot use them until activated
    # This allows immediate testing in dev, but requires activation in production
    token_data = {"sub": user.id, "pv": password_fingerprint(user.hashed_password)}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    # Import UserResponse
    from backend.schemas.auth import UserResponse

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )
