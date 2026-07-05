"""Unit tests for backend.utils.password_policy (security-critical)."""

import pytest
from backend.utils.password_policy import PasswordPolicy, password_policy, COMMON_PASSWORDS


VALID_PASSWORD = "Secure!Pass@97X"  # meets all requirements (no sequential chars)


class TestValidatePassword:
    def test_valid_password_passes(self):
        is_valid, errors = PasswordPolicy.validate_password(VALID_PASSWORD)
        assert is_valid
        assert errors == []

    def test_too_short_fails(self):
        is_valid, errors = PasswordPolicy.validate_password("Short@1")
        assert not is_valid
        assert any("12 characters" in e for e in errors)

    def test_missing_uppercase_fails(self):
        is_valid, errors = PasswordPolicy.validate_password("alllowercase@123")
        assert not is_valid
        assert any("uppercase" in e for e in errors)

    def test_missing_lowercase_fails(self):
        is_valid, errors = PasswordPolicy.validate_password("ALLUPPERCASE@123")
        assert not is_valid
        assert any("lowercase" in e for e in errors)

    def test_missing_digit_fails(self):
        is_valid, errors = PasswordPolicy.validate_password("NoDigitsHere@abc")
        assert not is_valid
        assert any("number" in e for e in errors)

    def test_missing_special_fails(self):
        is_valid, errors = PasswordPolicy.validate_password("NoSpecialChars123")
        assert not is_valid
        assert any("special" in e for e in errors)

    def test_common_password_fails(self):
        is_valid, errors = PasswordPolicy.validate_password("password123")
        assert not is_valid
        assert any("common" in e for e in errors)

    def test_sequential_digits_fails(self):
        is_valid, errors = PasswordPolicy.validate_password("SecurePass@A123")
        assert not is_valid
        assert any("sequential" in e for e in errors)

    def test_sequential_letters_fails(self):
        is_valid, errors = PasswordPolicy.validate_password("SecurePass@abcD1")
        assert not is_valid
        assert any("sequential" in e for e in errors)

    def test_repeated_chars_fails(self):
        is_valid, errors = PasswordPolicy.validate_password("SecurePassaaaa@1")
        assert not is_valid
        assert any("repeated" in e for e in errors)

    def test_multiple_violations(self):
        _, errors = PasswordPolicy.validate_password("weak")
        assert len(errors) > 2


class TestHasSequentialChars:
    def test_ascending_digits_detected(self):
        assert PasswordPolicy._has_sequential_chars("abc123def") is True

    def test_descending_digits_detected(self):
        assert PasswordPolicy._has_sequential_chars("abc321def") is True

    def test_ascending_letters_detected(self):
        assert PasswordPolicy._has_sequential_chars("xabc1") is True

    def test_descending_letters_detected(self):
        assert PasswordPolicy._has_sequential_chars("xcba1") is True

    def test_non_sequential_not_detected(self):
        assert PasswordPolicy._has_sequential_chars("aXm1Z!") is False

    def test_two_chars_not_sequential(self):
        assert PasswordPolicy._has_sequential_chars("ab") is False


class TestHasRepeatedChars:
    def test_four_same_chars_detected(self):
        assert PasswordPolicy._has_repeated_chars("aaaaa", max_repeat=3) is True

    def test_three_same_chars_not_detected(self):
        assert PasswordPolicy._has_repeated_chars("aaa", max_repeat=3) is False

    def test_no_repeat_not_detected(self):
        assert PasswordPolicy._has_repeated_chars("abcdef") is False

    def test_repeat_not_consecutive_not_detected(self):
        assert PasswordPolicy._has_repeated_chars("ababab", max_repeat=3) is False


class TestGetPasswordStrength:
    def test_strong_password_score(self):
        result = PasswordPolicy.get_password_strength(VALID_PASSWORD)
        assert result["score"] >= 60
        assert result["strength"] in ("strong", "medium")

    def test_weak_password_score(self):
        result = PasswordPolicy.get_password_strength("password")
        assert result["strength"] == "weak"
        assert result["score"] < 60

    def test_long_password_higher_score(self):
        long_pw = "SecureVeryLongPassword@1234!!"
        short_pw = "SecPass@12!"
        long_score = PasswordPolicy.get_password_strength(long_pw)["score"]
        short_score = PasswordPolicy.get_password_strength(short_pw)["score"]
        assert long_score >= short_score

    def test_common_password_low_score(self):
        result = PasswordPolicy.get_password_strength("password123")
        assert result["score"] < 60

    def test_returns_feedback_list(self):
        result = PasswordPolicy.get_password_strength("weak")
        assert isinstance(result["feedback"], list)
        assert len(result["feedback"]) > 0

    def test_score_between_0_and_100(self):
        for pw in ["short", VALID_PASSWORD, "AaAaAaAaAaAa!1"]:
            result = PasswordPolicy.get_password_strength(pw)
            assert 0 <= result["score"] <= 100

    def test_strength_levels(self):
        strong = PasswordPolicy.get_password_strength("VerySecure!Pass@2024#XYZ")
        assert strong["strength"] in ("strong", "medium")
        weak = PasswordPolicy.get_password_strength("pass")
        assert weak["strength"] == "weak"


def test_singleton_import():
    assert isinstance(password_policy, PasswordPolicy)


def test_common_passwords_not_empty():
    assert len(COMMON_PASSWORDS) > 0
    assert "password" in COMMON_PASSWORDS
