"""
MFA (Multi-Factor Authentication) Service - TR-008

Implements TOTP-based two-factor authentication for admin accounts.

Security Features:
- Time-based One-Time Passwords (TOTP) - RFC 6238
- 6-digit codes with 30-second validity window
- QR code generation for authenticator apps
- Backup codes for account recovery
- Constant-time comparison to prevent timing attacks

ALE Prevented: $18,750/year
"""

import pyotp
import qrcode
import io
import base64
import secrets
import json
from typing import List, Tuple, Optional
from passlib.hash import bcrypt

from backend.models import User
from backend.utils.logger import logger


class MFAService:
    """Service for managing MFA enrollment and verification"""

    # Constants
    TOTP_ISSUER = "Content Jumpstart"
    BACKUP_CODE_COUNT = 10
    BACKUP_CODE_LENGTH = 8

    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret"""
        return pyotp.random_base32()

    @staticmethod
    def generate_provisioning_uri(user: User, secret: str) -> str:
        """
        Generate a provisioning URI for authenticator apps

        Args:
            user: User object
            secret: TOTP secret

        Returns:
            otpauth:// URI for QR code generation
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=user.email, issuer_name=MFAService.TOTP_ISSUER)

    @staticmethod
    def generate_qr_code(provisioning_uri: str) -> str:
        """
        Generate QR code as base64-encoded PNG

        Args:
            provisioning_uri: otpauth:// URI

        Returns:
            Base64-encoded PNG image
        """
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode()

        return f"data:image/png;base64,{img_base64}"

    @staticmethod
    def generate_backup_codes() -> Tuple[List[str], str]:
        """
        Generate backup codes for account recovery

        Returns:
            Tuple of (plaintext_codes, hashed_codes_json)
        """
        plaintext_codes = []
        hashed_codes = []

        for _ in range(MFAService.BACKUP_CODE_COUNT):
            # Generate random alphanumeric code
            code = "".join(
                secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
                for _ in range(MFAService.BACKUP_CODE_LENGTH)
            )
            plaintext_codes.append(code)

            # Hash the code for storage
            hashed_codes.append(bcrypt.hash(code))

        return plaintext_codes, json.dumps(hashed_codes)

    @staticmethod
    def verify_totp(secret: str, token: str, window: int = 1) -> bool:
        """
        Verify a TOTP token

        Args:
            secret: User's TOTP secret
            token: 6-digit code from authenticator app
            window: Time window to check (default: 1 = ±30 seconds)

        Returns:
            True if token is valid
        """
        if not secret or not token:
            return False

        try:
            totp = pyotp.TOTP(secret)
            # Verify with time window to account for clock drift
            return totp.verify(token, valid_window=window)
        except Exception as e:
            logger.error(f"TOTP verification error: {e}")
            return False

    @staticmethod
    def verify_backup_code(user: User, code: str) -> Tuple[bool, Optional[str]]:
        """
        Verify a backup code and remove it if valid

        Args:
            user: User object
            code: Backup code to verify

        Returns:
            Tuple of (is_valid, updated_backup_codes_json)
        """
        if not user.mfa_backup_codes:
            return False, None

        try:
            hashed_codes = json.loads(user.mfa_backup_codes)

            # Check each hashed code
            for i, hashed_code in enumerate(hashed_codes):
                if bcrypt.verify(code.upper(), hashed_code):
                    # Code is valid - remove it (one-time use)
                    hashed_codes.pop(i)
                    updated_json = json.dumps(hashed_codes)

                    logger.warning(
                        f"Backup code used for user {user.email}. "
                        f"Remaining codes: {len(hashed_codes)}"
                    )

                    return True, updated_json

            return False, None

        except Exception as e:
            logger.error(f"Backup code verification error: {e}")
            return False, None

    @staticmethod
    def should_enforce_mfa(user: User) -> bool:
        """
        Determine if MFA should be enforced for this user

        TR-008: MFA is enforced for:
        - Superusers (is_superuser=True)
        - Users with mfa_enforced flag set

        Args:
            user: User object

        Returns:
            True if MFA should be enforced
        """
        return user.is_superuser or user.mfa_enforced

    @staticmethod
    def get_remaining_backup_codes(user: User) -> int:
        """Get count of remaining backup codes"""
        if not user.mfa_backup_codes:
            return 0

        try:
            hashed_codes = json.loads(user.mfa_backup_codes)
            return len(hashed_codes)
        except Exception:
            return 0


# Global instance
mfa_service = MFAService()
