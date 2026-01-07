"""
Authentication router - login, refresh token, user creation.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from backend.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    TokenResponse,
    UserCreate,
)
from backend.services import crud
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.utils.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
    verify_token_type,
)
from backend.utils.http_rate_limiter import strict_limiter, standard_limiter

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

    # Create tokens
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    # Import UserResponse
    from backend.schemas.auth import UserResponse

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id, email=user.email, full_name=user.full_name, is_active=user.is_active
        ),
    )


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

    # Create new tokens
    access_token = create_access_token(data={"sub": user.id})
    new_refresh_token = create_refresh_token(data={"sub": user.id})

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

    # TR-023: Create user in INACTIVE state (requires admin activation)
    user = crud.create_user(
        db,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=False,  # TR-023: New users inactive by default
    )

    logger.info(
        f"User created successfully: {user.email} (id={user.id}, is_active=False). "
        f"Admin activation required."
    )

    # TR-023: Return tokens but user cannot use them until activated
    # This allows immediate testing in dev, but requires activation in production
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

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
