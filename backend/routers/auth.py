"""
Authentication router - login, refresh token, user creation.
"""

import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from backend.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    ResetPasswordRequest,
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
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    password_fingerprint,
    verify_password,
    verify_token_type,
)
from backend.utils.http_rate_limiter import strict_limiter, standard_limiter
from backend.config import settings
from backend.utils.logger import logger

router = APIRouter()


def _send_password_reset_email(recipient_name: str, recipient_email: str, reset_link: str) -> None:
    """Deliver a password-reset email as a background task.

    Runs off the request path so /forgot-password responds in constant time
    regardless of whether an account exists (avoids a timing side-channel) and
    isn't blocked by SMTP latency. Failures are logged, never surfaced — the
    caller has already returned a generic response.
    """
    try:
        from agent.email_system import EmailSystem

        EmailSystem().send_password_reset(
            client_name=recipient_name,
            client_email=recipient_email,
            reset_link=reset_link,
            expiry_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
        )
    except Exception:  # pragma: no cover - defensive; email is best-effort
        logger.exception("Failed to send password-reset email")


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

    from datetime import datetime, timezone

    current_user.hashed_password = get_password_hash(body.new_password)
    # Stamp the change so pre-change sessions (incl. legacy tokens without a "pv"
    # claim) are revoked in get_current_user / refresh.
    current_user.password_changed_at = datetime.now(timezone.utc)
    db.add(current_user)
    db.commit()

    from backend.utils.logger import logger

    logger.info(f"Password changed for user {current_user.email} (id={current_user.id})")
    return {"status": "success", "message": "Password updated successfully"}


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@strict_limiter.limit("5/hour")  # TR-004: throttle reset-link requests / abuse
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Request a self-service password-reset link (GAP-AUTH-01).

    Always returns the same generic response so an attacker cannot use this
    endpoint to discover which emails have accounts (no user enumeration). When
    the email maps to an *active* account, a single-use reset link is emailed in
    the background; otherwise nothing is sent. The email send is a background
    task so response time is constant regardless of account existence.

    Rate limit: 5/hour per IP.
    """
    generic_response = {
        "status": "success",
        "message": ("If an account exists for that email, a password reset link has been sent."),
    }

    user = crud.get_user_by_email(db, body.email)
    if user and user.is_active:
        # Bind the token to the current password fingerprint so it is single-use:
        # completing the reset changes the hash, invalidating this (and any older) link.
        reset_token = create_password_reset_token(
            {"sub": user.id, "pv": password_fingerprint(user.hashed_password)}
        )
        base = os.getenv("APP_BASE_URL", "https://content-jumpstart.com").rstrip("/")
        reset_link = f"{base}/reset-password?token={reset_token}"
        background_tasks.add_task(
            _send_password_reset_email,
            user.full_name or user.email,
            user.email,
            reset_link,
        )
        logger.info(f"Password-reset link issued for user {user.email} (id={user.id})")
    else:
        # Log for monitoring, but reveal nothing to the caller.
        logger.info(f"Password-reset requested for unknown/inactive email: {body.email}")

    return generic_response


@router.post("/reset-password", status_code=status.HTTP_200_OK)
@standard_limiter.limit("20/hour")  # TR-004: limit brute force against the token
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Complete a self-service password reset using an emailed token (GAP-AUTH-01).

    Validates the single-use "password_reset" token, enforces the strong
    password policy, sets the new password, and stamps ``password_changed_at``
    so all pre-reset sessions are revoked. The token's ``pv`` claim must still
    match the user's current password hash — this guarantees a link is usable
    exactly once and cannot be replayed after the password changes.

    Rate limit: 20/hour per IP.
    """
    invalid_link = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired reset link. Please request a new one.",
    )

    payload = decode_token(body.token)
    if not payload or payload.get("type") != "password_reset":
        raise invalid_link

    user_id = payload.get("sub")
    user = crud.get_user(db, user_id) if user_id else None
    if not user or not user.is_active:
        raise invalid_link

    # Single-use / already-consumed guard: the token's password fingerprint must
    # still match the current hash. A None "pv" (malformed/legacy token) fails
    # this check too — fail closed.
    if payload.get("pv") != password_fingerprint(user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This reset link has already been used or is no longer valid. "
                "Please request a new one."
            ),
        )

    # Reject a no-op so the "new" password is genuinely new.
    if verify_password(body.new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from your current password",
        )

    # Enforce the full strong-password policy (TR-013), mirroring change-password.
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

    from datetime import datetime, timezone

    user.hashed_password = get_password_hash(body.new_password)
    # Revoke pre-reset sessions (incl. legacy tokens without a "pv" claim).
    user.password_changed_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()

    logger.info(f"Password reset completed for user {user.email} (id={user.id})")
    return {
        "status": "success",
        "message": "Password updated successfully. You can now sign in.",
    }


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

    # Reject a refresh token issued before the current password (session revocation):
    #  - "pv" present → must match current hash; legacy (no "pv") → rejected once the
    #    password has ever changed.
    token_pv = payload.get("pv")
    if token_pv is not None:
        if token_pv != password_fingerprint(user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please sign in again.",
            )
    elif user.password_changed_at is not None:
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
