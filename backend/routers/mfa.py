"""
MFA (Multi-Factor Authentication) Router - TR-008

Endpoints for MFA enrollment, verification, and management.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import (
    get_current_user,
    get_current_user_for_mfa_setup,
)
from backend.models import User
from backend.services.mfa_service import mfa_service
from backend.utils.auth import verify_password
from backend.utils.logger import logger
from backend.utils.http_rate_limiter import standard_limiter, strict_limiter

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


class MFADisableRequest(BaseModel):
    password: str = Field(..., min_length=1)
    # Wider than MFAVerifyRequest: a backup code (8 chars) is accepted here too, since
    # "my authenticator is gone" is exactly when someone needs to turn MFA off.
    code: str = Field(..., min_length=6, max_length=16)


class MFABackupCodesResponse(BaseModel):
    backup_codes: list[str]


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
    current_user: User = Depends(get_current_user_for_mfa_setup),
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
        # BUGS #172: enrolling does NOT set mfa_enforced. That flag is the *policy*
        # ("this account must use MFA") and only an operator sets it — conflating the
        # two meant anyone who voluntarily enrolled could never turn MFA back off.
        db.commit()
        logger.info(f"MFA enrollment completed for user {current_user.email}")
        return {"success": True, "message": "MFA successfully enabled"}

    return {"success": True, "message": "MFA verification successful"}


@router.post("/disable")
@strict_limiter.limit("5/hour")
async def disable_mfa(
    request: Request,
    body: MFADisableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Turn MFA off for the caller's own account (BUGS #172).

    Re-authentication is deliberately double: the account password (so a hijacked
    session alone can't strip the second factor) AND a live second factor (so someone
    who only knows the password can't either). Accounts under an operator MFA policy
    (`mfa_enforced`) cannot self-disable — that is checked first, so a refused request
    never burns one of the user's backup codes.
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled for this account",
        )

    if current_user.mfa_enforced:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA is required for this account and cannot be disabled",
        )

    if not verify_password(body.password, current_user.hashed_password):
        logger.warning(f"MFA disable refused (bad password) for {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    if not mfa_service.verify_credential(current_user, body.code):
        logger.warning(f"MFA disable refused (bad code) for {current_user.email}")
        # Persist a consumed backup code even on refusal — verify_credential only
        # consumes a code that MATCHED, and a matched code is spent either way.
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code",
        )

    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    current_user.mfa_backup_codes = None
    db.commit()

    logger.info(f"MFA disabled for user {current_user.email}")
    return {"success": True, "message": "MFA disabled"}


@router.post("/backup-codes/regenerate", response_model=MFABackupCodesResponse)
@strict_limiter.limit("5/hour")
async def regenerate_backup_codes(
    request: Request,
    body: MFAVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Issue a fresh set of backup codes, invalidating the old ones (BUGS #172).

    Requires a live TOTP code: the codes are a standing bypass of the second factor,
    so minting new ones has to prove possession of the authenticator. Returns the
    plaintext codes once — only their hashes are stored.
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled for this account",
        )

    if not mfa_service.verify_totp(current_user.mfa_secret, body.token):
        logger.warning(f"Backup-code regeneration refused for {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code",
        )

    backup_codes, hashed_backup_codes = mfa_service.generate_backup_codes()
    current_user.mfa_backup_codes = hashed_backup_codes
    db.commit()

    logger.info(f"Backup codes regenerated for user {current_user.email}")
    return MFABackupCodesResponse(backup_codes=backup_codes)


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
