"""
Authentication API endpoints.

Provides user registration, login, and token refresh functionality.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from ..core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from ..db.database import get_db
from ..models.user import User
from ..schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Creates a new user with hashed password and returns access/refresh tokens.

    Args:
        user_data: User registration data (email, password, name)
        db: Database session

    Returns:
        TokenResponse with access token, refresh token, and user info

    Raises:
        HTTPException 400: If email is already registered
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create new user with hashed password
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        company_name=user_data.company_name,
        role="client",  # Default role for new registrations
        is_active=True,
        email_verified=False,  # TODO: Implement email verification
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate JWT tokens
    access_token = create_access_token(data={"sub": new_user.user_id})
    refresh_token = create_refresh_token(data={"sub": new_user.user_id})

    # Convert SQLAlchemy model to Pydantic schema
    user_response = UserResponse.model_validate(new_user)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user_response,
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password.

    Validates credentials and returns access/refresh tokens.

    Args:
        credentials: User login credentials (email, password)
        db: Database session

    Returns:
        TokenResponse with access token, refresh token, and user info

    Raises:
        HTTPException 401: If credentials are invalid or account is inactive
    """
    # Retrieve user by email
    user = db.query(User).filter(User.email == credentials.email).first()

    # Verify password
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive. Contact support."
        )

    # Update last login timestamp
    user.last_login = datetime.utcnow()
    db.commit()

    # Generate JWT tokens
    access_token = create_access_token(data={"sub": user.user_id})
    refresh_token = create_refresh_token(data={"sub": user.user_id})

    # Convert SQLAlchemy model to Pydantic schema
    user_response = UserResponse.model_validate(user)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user_response,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    """
    Get a new access token using a refresh token.

    Args:
        refresh_token: Valid JWT refresh token
        db: Database session

    Returns:
        TokenResponse with new access token and same refresh token

    Raises:
        HTTPException 401: If refresh token is invalid or user not found
    """
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token type
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Expected refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from token
    user_id = payload.get("sub")
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate new access token (keep same refresh token)
    new_access_token = create_access_token(data={"sub": user.user_id})

    # Convert SQLAlchemy model to Pydantic schema
    user_response = UserResponse.model_validate(user)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=refresh_token,  # Return same refresh token
        token_type="bearer",
        user=user_response,
    )
