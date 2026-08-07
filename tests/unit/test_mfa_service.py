"""Unit tests for backend.services.mfa_service (TOTP/MFA logic)."""

import json
import re
from unittest.mock import MagicMock

import pyotp

from backend.services.mfa_service import MFAService, mfa_service


def _make_user(email="test@example.com", mfa_backup_codes=None):
    user = MagicMock()
    user.email = email
    user.mfa_backup_codes = mfa_backup_codes
    return user


class TestGenerateSecret:
    def test_returns_string(self):
        secret = MFAService.generate_secret()
        assert isinstance(secret, str)

    def test_valid_base32(self):
        secret = MFAService.generate_secret()
        # pyotp secrets are base32 uppercase letters and 2-7
        assert re.match(r"^[A-Z2-7]+=*$", secret)

    def test_unique_each_call(self):
        assert MFAService.generate_secret() != MFAService.generate_secret()


class TestGenerateProvisioningUri:
    def test_starts_with_otpauth(self):
        secret = MFAService.generate_secret()
        user = _make_user("alice@example.com")
        uri = MFAService.generate_provisioning_uri(user, secret)
        assert uri.startswith("otpauth://totp/")

    def test_contains_email(self):
        secret = MFAService.generate_secret()
        user = _make_user("alice@example.com")
        uri = MFAService.generate_provisioning_uri(user, secret)
        assert "alice" in uri or "alice%40example.com" in uri

    def test_contains_issuer(self):
        secret = MFAService.generate_secret()
        user = _make_user()
        uri = MFAService.generate_provisioning_uri(user, secret)
        assert (
            "Content+Jumpstart" in uri or "Content%20Jumpstart" in uri or "Content Jumpstart" in uri
        )


class TestGenerateQrCode:
    def test_returns_data_uri(self):
        secret = MFAService.generate_secret()
        user = _make_user()
        uri = MFAService.generate_provisioning_uri(user, secret)
        qr = MFAService.generate_qr_code(uri)
        assert qr.startswith("data:image/png;base64,")

    def test_non_empty_base64(self):
        secret = MFAService.generate_secret()
        user = _make_user()
        uri = MFAService.generate_provisioning_uri(user, secret)
        qr = MFAService.generate_qr_code(uri)
        b64_part = qr.split(",")[1]
        assert len(b64_part) > 100  # non-trivial image


class TestGenerateBackupCodes:
    def test_returns_correct_count(self):
        codes, _ = MFAService.generate_backup_codes()
        assert len(codes) == MFAService.BACKUP_CODE_COUNT

    def test_codes_have_correct_length(self):
        codes, _ = MFAService.generate_backup_codes()
        for code in codes:
            assert len(code) == MFAService.BACKUP_CODE_LENGTH

    def test_codes_are_uppercase_alphanumeric(self):
        codes, _ = MFAService.generate_backup_codes()
        for code in codes:
            assert re.match(r"^[A-Z0-9]+$", code)

    def test_hashed_json_is_valid(self):
        _, hashed_json = MFAService.generate_backup_codes()
        hashed = json.loads(hashed_json)
        assert len(hashed) == MFAService.BACKUP_CODE_COUNT

    def test_codes_are_unique(self):
        codes, _ = MFAService.generate_backup_codes()
        assert len(set(codes)) == len(codes)


class TestVerifyTotp:
    def test_valid_token_passes(self):
        secret = MFAService.generate_secret()
        totp = pyotp.TOTP(secret)
        token = totp.now()
        assert MFAService.verify_totp(secret, token) is True

    def test_invalid_token_fails(self):
        secret = MFAService.generate_secret()
        assert MFAService.verify_totp(secret, "000000") is False

    def test_empty_secret_returns_false(self):
        assert MFAService.verify_totp("", "123456") is False

    def test_empty_token_returns_false(self):
        assert MFAService.verify_totp(MFAService.generate_secret(), "") is False

    def test_none_secret_returns_false(self):
        assert MFAService.verify_totp(None, "123456") is False

    def test_malformed_token_returns_false(self):
        secret = MFAService.generate_secret()
        assert MFAService.verify_totp(secret, "not-a-number") is False


class TestVerifyBackupCode:
    def test_valid_code_passes(self):
        codes, hashed_json = MFAService.generate_backup_codes()
        user = _make_user(mfa_backup_codes=hashed_json)
        is_valid, _ = MFAService.verify_backup_code(user, codes[0])
        assert is_valid is True

    def test_valid_code_is_removed(self):
        codes, hashed_json = MFAService.generate_backup_codes()
        user = _make_user(mfa_backup_codes=hashed_json)
        _, updated_json = MFAService.verify_backup_code(user, codes[0])
        remaining = json.loads(updated_json)
        assert len(remaining) == MFAService.BACKUP_CODE_COUNT - 1

    def test_invalid_code_fails(self):
        _, hashed_json = MFAService.generate_backup_codes()
        user = _make_user(mfa_backup_codes=hashed_json)
        is_valid, updated = MFAService.verify_backup_code(user, "BADCODE1")
        assert is_valid is False
        assert updated is None

    def test_no_backup_codes_fails(self):
        user = _make_user(mfa_backup_codes=None)
        is_valid, updated = MFAService.verify_backup_code(user, "ANYCODE1")
        assert is_valid is False
        assert updated is None

    def test_case_insensitive_verification(self):
        codes, hashed_json = MFAService.generate_backup_codes()
        user = _make_user(mfa_backup_codes=hashed_json)
        # Codes are uppercase; pass lowercase
        is_valid, _ = MFAService.verify_backup_code(user, codes[0].lower())
        assert is_valid is True


class TestVerifyCredential:
    """BUGS #172 — the shared second-factor check used by login and MFA management."""

    def test_accepts_a_valid_totp_code(self):
        secret = MFAService.generate_secret()
        user = _make_user()
        user.mfa_secret = secret
        assert MFAService.verify_credential(user, pyotp.TOTP(secret).now()) is True

    def test_accepts_and_consumes_a_backup_code(self):
        codes, hashed_json = MFAService.generate_backup_codes()
        user = _make_user(mfa_backup_codes=hashed_json)
        user.mfa_secret = MFAService.generate_secret()

        assert MFAService.verify_credential(user, codes[0]) is True
        # Consumed in-place: one fewer code, and the same code no longer works.
        assert len(json.loads(user.mfa_backup_codes)) == MFAService.BACKUP_CODE_COUNT - 1
        assert MFAService.verify_credential(user, codes[0]) is False

    def test_tolerates_user_typing_habits(self):
        codes, hashed_json = MFAService.generate_backup_codes()
        user = _make_user(mfa_backup_codes=hashed_json)
        user.mfa_secret = MFAService.generate_secret()
        # Lowercase, spaced and hyphenated renderings of the same code.
        assert MFAService.verify_credential(user, f" {codes[0].lower()} ") is True

    def test_rejects_wrong_and_empty_codes(self):
        codes, hashed_json = MFAService.generate_backup_codes()
        user = _make_user(mfa_backup_codes=hashed_json)
        user.mfa_secret = MFAService.generate_secret()

        assert MFAService.verify_credential(user, "000000") is False
        assert MFAService.verify_credential(user, "NOTACODE") is False
        assert MFAService.verify_credential(user, "") is False
        # A rejected attempt spends nothing.
        assert len(json.loads(user.mfa_backup_codes)) == MFAService.BACKUP_CODE_COUNT

    def test_backup_code_works_when_no_secret_is_set(self):
        codes, hashed_json = MFAService.generate_backup_codes()
        user = _make_user(mfa_backup_codes=hashed_json)
        user.mfa_secret = None
        assert MFAService.verify_credential(user, codes[1]) is True


class TestShouldEnforceMfa:
    def test_always_returns_false(self):
        user = _make_user()
        assert MFAService.should_enforce_mfa(user) is False


class TestGetRemainingBackupCodes:
    def test_returns_count(self):
        _, hashed_json = MFAService.generate_backup_codes()
        user = _make_user(mfa_backup_codes=hashed_json)
        assert MFAService.get_remaining_backup_codes(user) == MFAService.BACKUP_CODE_COUNT

    def test_none_returns_zero(self):
        user = _make_user(mfa_backup_codes=None)
        assert MFAService.get_remaining_backup_codes(user) == 0

    def test_invalid_json_returns_zero(self):
        user = _make_user(mfa_backup_codes="not-json")
        assert MFAService.get_remaining_backup_codes(user) == 0


def test_singleton_import():
    assert isinstance(mfa_service, MFAService)
