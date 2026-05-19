"""
MFA (Multi-Factor Authentication) Router - TR-008

Endpoints for MFA enrollment, verification, and management.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user, get_current_user_for_mfa_setup
from backend.models import User
from backend.services.mfa_service import mfa_service
from backend.utils.logger import logger
from backend.utils.http_rate_limiter import standard_limiter

router = APIRouter()


class MFAEnrollRequest(BaseModel):
    pass


class MFAEnrollResponse(BaseModel):
    secret: str
    qr_code: str
    backup_codes: list[str]
    message: str


class MFAVerifyRequest(BaseModel):
    token: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$")


class MFAStatusResponse(BaseModel):
    mfa_enabled: bool
    mfa_enforced: bool
    remaining_backup_codes: int


@router.post("/enroll", response_model=MFAEnrollResponse)
@standard_limiter.limit("5/hour")
async def enroll_mfa(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_for_mfa_setup),
):
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled for this account",
        )

    secret = mfa_service.generate_secret()
    provisioning_uri = mfa_service.generate_provisioning_uri(current_user, secret)
    qr_code = mfa_service.generate_qr_code(provisioning_uri)
    backup_codes, hashed_backup_codes = mfa_service.generate_backup_codes()

    current_user.mfa_secret = secret
    current_user.mfa_backup_codes = hashed_backup_codes
    current_user.mfa_enabled = False

    db.commit()

    logger.info(f"MFA enrollment started for user {current_user.email}")

    return MFAEnrollResponse(
        secret=secret,
        qr_code=qr_code,
        backup_codes=backup_codes,
        message="Scan the QR code with your authenticator app",
    )


@router.post("/verify")
@standard_limiter.limit("10/hour")
async def verify_mfa_token(
    request: Request,
    body: MFAVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not set up for this account",
        )

    is_valid = mfa_service.verify_totp(current_user.mfa_secret, body.token)

    if not is_valid:
        logger.warning(f"Invalid MFA token for user {current_user.email}")
        return {"success": False, "message": "Invalid verification code"}

    if not current_user.mfa_enabled:
        current_user.mfa_enabled = True
        if current_user.is_superuser:
            current_user.mfa_enforced = True
        db.commit()
        logger.info(f"MFA enrollment completed for user {current_user.email}")
        return {"success": True, "message": "MFA successfully enabled"}

    return {"success": True, "message": "MFA verification successful"}


@router.get("/status", response_model=MFAStatusResponse)
@standard_limiter.limit("100/hour")
async def get_mfa_status(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    return MFAStatusResponse(
        mfa_enabled=current_user.mfa_enabled or False,
        mfa_enforced=mfa_service.should_enforce_mfa(current_user),
        remaining_backup_codes=mfa_service.get_remaining_backup_codes(current_user),
    )
