"""Unit tests for settings module.

Tests cover:
- Settings class initialization
- ANTHROPIC_API_KEY validation (lines 29-58)
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config.settings import Settings

# Some tests assert values that come from the developer's local project/.env
# (API key present, tuned performance defaults). That file is gitignored and not
# present in CI, so guard those tests — they run locally, skip in CI.
_HAS_ENV_FILE = (Path(__file__).resolve().parents[2] / ".env").exists()
_requires_env_file = pytest.mark.skipif(
    not _HAS_ENV_FILE, reason="requires local project/.env (not present in CI)"
)


class TestSettingsAPIKeyValidation:
    """Tests for ANTHROPIC_API_KEY validation (lines 18-58)."""

    @_requires_env_file
    def test_api_key_loads_from_env_file(self, monkeypatch):
        """Test that API key loads from .env file when env var not set."""
        # Temporarily unset the environment variable
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        settings = Settings()

        # Should load from .env file if it exists
        # (pydantic-settings automatically reads .env files)
        assert settings.ANTHROPIC_API_KEY is not None
        assert len(settings.ANTHROPIC_API_KEY) > 0

    def test_api_key_placeholder_raises_error(self):
        """Test that placeholder values raise ValueError (line 39)."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(ANTHROPIC_API_KEY="your_api_key_here")  # pragma: allowlist secret

        assert "placeholder value" in str(exc_info.value).lower()

    def test_api_key_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(ANTHROPIC_API_KEY="")

        assert "placeholder" in str(exc_info.value).lower()

    def test_api_key_xxx_placeholder_raises_error(self):
        """Test that 'xxx' placeholder raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(ANTHROPIC_API_KEY="xxx")  # pragma: allowlist secret

        # Both short length and placeholder might trigger
        assert (
            "placeholder" in str(exc_info.value).lower()
            or "too short" in str(exc_info.value).lower()
        )

    def test_api_key_too_short_raises_error(self):
        """Test that short API key raises ValueError (line 46)."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(ANTHROPIC_API_KEY="sk-ant-short")  # Only 12 chars  # pragma: allowlist secret

        assert "too short" in str(exc_info.value).lower()

    def test_api_key_wrong_prefix_logs_warning(self, caplog):
        """Test that wrong prefix logs warning (line 53)."""
        import logging

        caplog.set_level(logging.WARNING)

        # Valid length but wrong prefix
        settings = Settings(ANTHROPIC_API_KEY="wrong-prefix-12345678901234567890")

        assert settings.ANTHROPIC_API_KEY is not None
        assert "does not start with expected prefix" in caplog.text

    def test_api_key_valid_format(self, caplog):
        """Test that valid API key passes validation (line 58)."""
        import logging

        caplog.set_level(logging.INFO)

        valid_key = "sk-ant-api03-" + "x" * 50  # Valid prefix and length
        settings = Settings(ANTHROPIC_API_KEY=valid_key)

        assert settings.ANTHROPIC_API_KEY == valid_key
        assert "validated" in caplog.text.lower()


class TestSettingsDefaults:
    """Tests for settings default values."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        settings = Settings()

        # Model may be overridden by environment, check it's set
        assert settings.ANTHROPIC_MODEL is not None
        assert len(settings.ANTHROPIC_MODEL) > 0
        assert settings.MAX_TOKENS == 4096
        assert settings.TEMPERATURE == 0.7
        assert settings.MAX_RETRIES == 3
        assert settings.TIMEOUT_SECONDS == 120

    def test_generation_temperatures(self):
        """Test generation-specific temperatures."""
        settings = Settings()

        assert settings.POST_GENERATION_TEMPERATURE == 0.7
        assert settings.BRIEF_PARSING_TEMPERATURE == 0.3

    def test_quality_thresholds(self):
        """Test quality threshold defaults."""
        settings = Settings()

        assert settings.MIN_POST_WORD_COUNT == 200  # LinkedIn minimum — posts under 200 fail
        assert settings.MAX_POST_WORD_COUNT == 350
        assert settings.OPTIMAL_POST_MIN_WORDS == 220  # Sweet spot minimum
        assert settings.OPTIMAL_POST_MAX_WORDS == 280  # Sweet spot maximum

    @_requires_env_file
    def test_performance_settings(self):
        """Test performance setting defaults."""
        settings = Settings()

        assert settings.PARALLEL_GENERATION is True
        assert settings.MAX_CONCURRENT_API_CALLS == 5
        assert settings.CACHE_PROMPTS is True
