"""Unit tests for secrets_manager module.

Tests cover:
- SecretNotFoundError exception
- EnvironmentSecretsProvider
- DotEnvSecretsProvider
- SecretsManager facade
- Global singleton functions
"""

import os
import pytest
from unittest.mock import MagicMock

from src.config.secrets_manager import (
    SecretNotFoundError,
    SecretsProvider,
    EnvironmentSecretsProvider,
    DotEnvSecretsProvider,
    SecretsManager,
    get_secrets_manager,
    get_secret,
)


class TestSecretNotFoundError:
    """Tests for SecretNotFoundError exception."""

    def test_raise_exception(self):
        """Test that SecretNotFoundError can be raised."""
        with pytest.raises(SecretNotFoundError):
            raise SecretNotFoundError("Test secret not found")

    def test_exception_message(self):
        """Test that exception preserves error message."""
        message = "SECRET_KEY not found"
        try:
            raise SecretNotFoundError(message)
        except SecretNotFoundError as e:
            assert str(e) == message

    def test_exception_inheritance(self):
        """Test that SecretNotFoundError is an Exception."""
        assert issubclass(SecretNotFoundError, Exception)


class TestEnvironmentSecretsProvider:
    """Tests for EnvironmentSecretsProvider."""

    @pytest.fixture
    def provider(self):
        """Create a fresh EnvironmentSecretsProvider instance."""
        return EnvironmentSecretsProvider()

    @pytest.fixture(autouse=True)
    def clean_env(self):
        """Clean up test environment variables after each test."""
        test_keys = ["TEST_SECRET", "TEST_KEY", "TEST_TOKEN", "EMPTY_SECRET"]
        yield
        for key in test_keys:
            if key in os.environ:
                del os.environ[key]

    def test_get_secret_from_environment(self, provider):
        """Test getting a secret from environment variable."""
        os.environ["TEST_SECRET"] = "secret_value_123"  # pragma: allowlist secret
        result = provider.get_secret("TEST_SECRET")
        assert result == "secret_value_123"

    def test_get_secret_with_default(self, provider):
        """Test getting a secret with default value when not found."""
        result = provider.get_secret("NONEXISTENT_SECRET", "default_value")
        assert result == "default_value"

    def test_get_secret_not_found_raises(self, provider):
        """Test that missing secret without default raises SecretNotFoundError."""
        with pytest.raises(SecretNotFoundError) as exc_info:
            provider.get_secret("NONEXISTENT_SECRET")
        assert "NONEXISTENT_SECRET" in str(exc_info.value)

    def test_get_secret_empty_raises(self, provider):
        """Test that empty secret raises SecretNotFoundError."""
        os.environ["EMPTY_SECRET"] = "   "
        with pytest.raises(SecretNotFoundError) as exc_info:
            provider.get_secret("EMPTY_SECRET")
        assert "empty" in str(exc_info.value).lower()

    def test_set_secret(self, provider):
        """Test setting a secret in environment."""
        provider.set_secret("TEST_KEY", "test_value")
        assert os.environ.get("TEST_KEY") == "test_value"

    def test_delete_secret(self, provider):
        """Test deleting a secret from environment."""
        os.environ["TEST_SECRET"] = "to_delete"  # pragma: allowlist secret
        provider.delete_secret("TEST_SECRET")
        assert "TEST_SECRET" not in os.environ

    def test_delete_nonexistent_secret(self, provider):
        """Test deleting a nonexistent secret doesn't raise."""
        # Should not raise
        provider.delete_secret("NONEXISTENT_SECRET")

    def test_list_secret_keys(self, provider):
        """Test listing secret keys filters by pattern."""
        os.environ["API_KEY"] = "value"  # pragma: allowlist secret
        os.environ["SECRET_TOKEN"] = "value"  # pragma: allowlist secret
        os.environ["REGULAR_VAR"] = "value"

        keys = provider.list_secret_keys()

        assert "API_KEY" in keys
        assert "SECRET_TOKEN" in keys
        # REGULAR_VAR doesn't match secret patterns
        assert "REGULAR_VAR" not in keys

    def test_list_secret_keys_patterns(self, provider):
        """Test that list_secret_keys matches expected patterns."""
        test_vars = {  # pragma: allowlist secret
            "MY_SECRET": "val",
            "API_KEY": "val",
            "AUTH_TOKEN": "val",
            "DATABASE_PASSWORD": "val",
            "AWS_CREDENTIALS": "val",
            "NORMAL_VALUE": "val",  # Should NOT match
        }
        for key, value in test_vars.items():
            os.environ[key] = value

        keys = provider.list_secret_keys()

        # These should match patterns
        assert "MY_SECRET" in keys
        assert "API_KEY" in keys
        assert "AUTH_TOKEN" in keys
        assert "DATABASE_PASSWORD" in keys
        assert "AWS_CREDENTIALS" in keys

        # Cleanup
        for key in test_vars:
            if key in os.environ:
                del os.environ[key]


class TestDotEnvSecretsProvider:
    """Tests for DotEnvSecretsProvider."""

    @pytest.fixture
    def temp_env_file(self, tmp_path):
        """Create a temporary .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# Test environment file\n"
            "TEST_API_KEY=sk-test-12345\n"
            "TEST_SECRET=my_secret_value\n"
            'QUOTED_VALUE="double quoted"\n'
            "SINGLE_QUOTED='single quoted'\n"
            "\n"
            "# Another comment\n"
            "EMPTY_LINE_ABOVE=value\n"
        )
        return env_file

    @pytest.fixture
    def provider(self, temp_env_file):
        """Create provider with temp env file."""
        return DotEnvSecretsProvider(temp_env_file)

    @pytest.fixture(autouse=True)
    def clean_env(self, temp_env_file):
        """Clean up test environment variables after each test."""
        yield
        for key in [
            "TEST_API_KEY",
            "TEST_SECRET",
            "QUOTED_VALUE",
            "SINGLE_QUOTED",
            "EMPTY_LINE_ABOVE",
            "NEW_SECRET",
        ]:
            if key in os.environ:
                del os.environ[key]

    def test_load_env_file(self, provider):
        """Test that .env file is loaded correctly."""
        assert provider.get_secret("TEST_API_KEY") == "sk-test-12345"
        assert provider.get_secret("TEST_SECRET") == "my_secret_value"

    def test_load_quoted_values(self, provider):
        """Test that quoted values are unquoted."""
        assert provider.get_secret("QUOTED_VALUE") == "double quoted"
        assert provider.get_secret("SINGLE_QUOTED") == "single quoted"

    def test_skip_comments(self, provider):
        """Test that comments are skipped."""
        # Should not have comment keys
        with pytest.raises(SecretNotFoundError):
            provider.get_secret("# Test environment file")

    def test_get_secret_not_found(self, provider):
        """Test getting nonexistent secret raises error."""
        with pytest.raises(SecretNotFoundError) as exc_info:
            provider.get_secret("NONEXISTENT")
        assert "NONEXISTENT" in str(exc_info.value)

    def test_get_secret_with_default(self, provider):
        """Test getting secret with default value."""
        result = provider.get_secret("NONEXISTENT", "fallback")
        assert result == "fallback"

    def test_set_secret(self, provider):
        """Test setting a secret (memory only)."""
        provider.set_secret("NEW_SECRET", "new_value")
        assert provider.get_secret("NEW_SECRET") == "new_value"
        # Also sets in os.environ for compatibility
        assert os.environ.get("NEW_SECRET") == "new_value"

    def test_delete_secret(self, provider):
        """Test deleting a secret."""
        provider.delete_secret("TEST_API_KEY")
        with pytest.raises(SecretNotFoundError):
            provider.get_secret("TEST_API_KEY")

    def test_list_secret_keys(self, provider):
        """Test listing all secret keys."""
        keys = provider.list_secret_keys()
        assert "TEST_API_KEY" in keys
        assert "TEST_SECRET" in keys

    def test_nonexistent_env_file(self, tmp_path):
        """Test handling of nonexistent .env file."""
        # Should not raise, just log warning
        provider = DotEnvSecretsProvider(tmp_path / "nonexistent.env")
        # Provider initializes but has no secrets
        assert provider.list_secret_keys() == []

    def test_env_file_parse_error(self, tmp_path):
        """Test handling of malformed .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("VALID_KEY=value\n")

        provider = DotEnvSecretsProvider(env_file)
        assert provider.get_secret("VALID_KEY") == "value"

    def test_sets_environment_variables(self, provider):
        """Test that loading .env also sets os.environ."""
        # Should be set in os.environ for compatibility
        assert os.environ.get("TEST_API_KEY") == "sk-test-12345"


class TestSecretsManager:
    """Tests for SecretsManager facade."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock SecretsProvider."""
        provider = MagicMock(spec=SecretsProvider)
        provider.get_secret.return_value = "secret_value"
        provider.list_secret_keys.return_value = ["KEY1", "KEY2"]
        return provider

    @pytest.fixture
    def manager(self, mock_provider):
        """Create SecretsManager with mock provider."""
        return SecretsManager(provider=mock_provider)

    def test_init_with_custom_provider(self, mock_provider):
        """Test initialization with custom provider."""
        manager = SecretsManager(provider=mock_provider)
        assert manager.provider == mock_provider

    def test_get_secret(self, manager, mock_provider):
        """Test getting a secret through manager."""
        result = manager.get("TEST_KEY")
        assert result == "secret_value"
        mock_provider.get_secret.assert_called_once_with("TEST_KEY", None)

    def test_get_secret_with_default(self, manager, mock_provider):
        """Test getting secret with default."""
        manager.get("TEST_KEY", default="default")
        mock_provider.get_secret.assert_called_with("TEST_KEY", "default")

    def test_get_secret_not_required(self, manager, mock_provider):
        """Test getting optional secret that doesn't exist."""
        mock_provider.get_secret.side_effect = SecretNotFoundError("Not found")
        result = manager.get("MISSING_KEY", required=False, default="fallback")
        assert result == "fallback"

    def test_get_secret_required_raises(self, manager, mock_provider):
        """Test that missing required secret raises error."""
        mock_provider.get_secret.side_effect = SecretNotFoundError("Not found")
        with pytest.raises(SecretNotFoundError):
            manager.get("MISSING_KEY", required=True)

    def test_set_secret(self, manager, mock_provider):
        """Test setting a secret."""
        manager.set("NEW_KEY", "new_value")
        mock_provider.set_secret.assert_called_once_with("NEW_KEY", "new_value")

    def test_delete_secret(self, manager, mock_provider):
        """Test deleting a secret."""
        manager.delete("OLD_KEY")
        mock_provider.delete_secret.assert_called_once_with("OLD_KEY")

    def test_list_keys(self, manager, mock_provider):
        """Test listing secret keys."""
        keys = manager.list_keys()
        assert keys == ["KEY1", "KEY2"]
        mock_provider.list_secret_keys.assert_called_once()

    def test_validate_required_secrets_all_present(self, manager, mock_provider):
        """Test validation passes when all secrets present."""
        # Should not raise
        manager.validate_required_secrets(["KEY1", "KEY2"])

    def test_validate_required_secrets_missing(self, manager, mock_provider):
        """Test validation fails when secrets missing."""
        mock_provider.get_secret.side_effect = SecretNotFoundError("Not found")
        with pytest.raises(SecretNotFoundError) as exc_info:
            manager.validate_required_secrets(["MISSING1", "MISSING2"])
        assert "MISSING1" in str(exc_info.value)

    def test_access_log(self, manager, mock_provider):
        """Test that access log is maintained."""
        manager.get("KEY1")
        manager.get("KEY2")

        log = manager.get_access_log()
        assert len(log) == 2
        assert log[0]["key"] == "KEY1"
        assert log[1]["key"] == "KEY2"
        assert "timestamp" in log[0]
        assert log[0]["found"] is True

    def test_access_log_tracks_not_found(self, manager, mock_provider):
        """Test that access log tracks failed lookups."""
        mock_provider.get_secret.side_effect = SecretNotFoundError("Not found")
        manager.get("MISSING", required=False)

        log = manager.get_access_log()
        assert len(log) == 1
        assert log[0]["key"] == "MISSING"
        assert log[0]["found"] is False

    def test_check_rotation_needed(self, manager):
        """Test rotation check (placeholder implementation)."""
        # Current implementation always returns False
        result = manager.check_rotation_needed("ANY_KEY")
        assert result is False


class TestSecretsManagerAutoSelect:
    """Tests for SecretsManager auto provider selection."""

    @pytest.fixture(autouse=True)
    def clean_env(self):
        """Clean up environment after each test."""
        original_provider = os.environ.get("SECRETS_PROVIDER")
        yield
        if original_provider is not None:
            os.environ["SECRETS_PROVIDER"] = original_provider
        elif "SECRETS_PROVIDER" in os.environ:
            del os.environ["SECRETS_PROVIDER"]

    def test_auto_select_environment_provider(self, tmp_path, monkeypatch):
        """Test auto-selection of EnvironmentSecretsProvider."""
        monkeypatch.chdir(tmp_path)  # No .env file exists
        os.environ["SECRETS_PROVIDER"] = "environment"  # pragma: allowlist secret

        manager = SecretsManager()
        assert isinstance(manager.provider, EnvironmentSecretsProvider)

    def test_auto_select_dotenv_provider(self, tmp_path, monkeypatch):
        """Test auto-selection of DotEnvSecretsProvider."""
        monkeypatch.chdir(tmp_path)
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_KEY=value\n")
        os.environ["SECRETS_PROVIDER"] = "dotenv"  # pragma: allowlist secret

        manager = SecretsManager()
        assert isinstance(manager.provider, DotEnvSecretsProvider)

    def test_auto_detect_env_file(self, tmp_path, monkeypatch):
        """Test auto-detection of .env file."""
        monkeypatch.chdir(tmp_path)
        # Remove SECRETS_PROVIDER to trigger auto-detect
        if "SECRETS_PROVIDER" in os.environ:
            del os.environ["SECRETS_PROVIDER"]

        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("AUTO_KEY=auto_value\n")

        manager = SecretsManager()
        assert isinstance(manager.provider, DotEnvSecretsProvider)

    def test_auto_detect_no_env_file(self, tmp_path, monkeypatch):
        """Test auto-detection without .env file."""
        monkeypatch.chdir(tmp_path)
        # Remove SECRETS_PROVIDER to trigger auto-detect
        if "SECRETS_PROVIDER" in os.environ:
            del os.environ["SECRETS_PROVIDER"]

        # No .env file - should use EnvironmentSecretsProvider
        manager = SecretsManager()
        assert isinstance(manager.provider, EnvironmentSecretsProvider)


class TestGlobalFunctions:
    """Tests for global singleton functions."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset the global singleton before each test."""
        import src.config.secrets_manager as sm

        sm._secrets_manager = None
        yield
        sm._secrets_manager = None

    def test_get_secrets_manager_singleton(self, tmp_path, monkeypatch):
        """Test that get_secrets_manager returns singleton."""
        monkeypatch.chdir(tmp_path)
        if "SECRETS_PROVIDER" in os.environ:
            del os.environ["SECRETS_PROVIDER"]

        manager1 = get_secrets_manager()
        manager2 = get_secrets_manager()

        assert manager1 is manager2

    def test_get_secret_convenience_function(self, tmp_path, monkeypatch):
        """Test get_secret convenience function."""
        monkeypatch.chdir(tmp_path)
        os.environ["CONVENIENCE_TEST"] = "convenience_value"
        os.environ["SECRETS_PROVIDER"] = "environment"  # pragma: allowlist secret

        result = get_secret("CONVENIENCE_TEST")
        assert result == "convenience_value"

        # Cleanup
        del os.environ["CONVENIENCE_TEST"]

    def test_get_secret_with_default(self, tmp_path, monkeypatch):
        """Test get_secret with default value."""
        monkeypatch.chdir(tmp_path)
        os.environ["SECRETS_PROVIDER"] = "environment"

        result = get_secret(
            "NONEXISTENT_KEY", default="default", required=False
        )  # pragma: allowlist secret
        assert result == "default"

    def test_get_secret_required_raises(self, tmp_path, monkeypatch):
        """Test get_secret raises for missing required secret."""
        monkeypatch.chdir(tmp_path)
        os.environ["SECRETS_PROVIDER"] = "environment"

        with pytest.raises(SecretNotFoundError):
            get_secret("DEFINITELY_NOT_EXISTING", required=True)


# ---------------------------------------------------------------------------
# Additional coverage tests — appended to reach full branch coverage
# ---------------------------------------------------------------------------


class TestEnvironmentSecretsProviderExtended:
    """Extended tests for EnvironmentSecretsProvider filling coverage gaps."""

    @pytest.fixture
    def provider(self):
        """Create a fresh EnvironmentSecretsProvider instance."""
        return EnvironmentSecretsProvider()

    def test_get_secret_key_exists_returns_value(self, provider, monkeypatch):
        """Key present in environment → exact value is returned."""
        monkeypatch.setenv("MY_TEST_KEY", "hello_world")
        result = provider.get_secret("MY_TEST_KEY")
        assert result == "hello_world"

    def test_get_secret_missing_no_default_raises(self, provider, monkeypatch):
        """Key absent + default=None (omitted) → SecretNotFoundError raised."""
        monkeypatch.delenv("DEFINITELY_ABSENT_XYZ", raising=False)
        with pytest.raises(SecretNotFoundError) as exc_info:
            provider.get_secret("DEFINITELY_ABSENT_XYZ")
        assert "DEFINITELY_ABSENT_XYZ" in str(exc_info.value)

    def test_get_secret_missing_with_default_returns_default(self, provider, monkeypatch):
        """Key absent + explicit default → default value returned (not an error)."""
        monkeypatch.delenv("DEFINITELY_ABSENT_XYZ", raising=False)
        result = provider.get_secret("DEFINITELY_ABSENT_XYZ", default="my_default")
        assert result == "my_default"

    def test_get_secret_whitespace_only_raises(self, provider, monkeypatch):
        """Key present but value is whitespace-only → SecretNotFoundError raised."""
        monkeypatch.setenv("WHITESPACE_SECRET", "   \t  ")  # pragma: allowlist secret
        with pytest.raises(SecretNotFoundError) as exc_info:
            provider.get_secret("WHITESPACE_SECRET")
        assert "empty" in str(exc_info.value).lower()

    def test_set_secret_writes_to_environ(self, provider, monkeypatch):
        """set_secret places the value into os.environ under the given key."""
        monkeypatch.delenv("SET_TEST_TOKEN", raising=False)
        provider.set_secret("SET_TEST_TOKEN", "tok_abc")
        assert os.environ.get("SET_TEST_TOKEN") == "tok_abc"

    def test_delete_secret_removes_existing_key(self, provider, monkeypatch):
        """delete_secret removes a key that is present in os.environ."""
        monkeypatch.setenv("DEL_MY_PASSWORD", "to_remove")  # pragma: allowlist secret
        provider.delete_secret("DEL_MY_PASSWORD")
        assert "DEL_MY_PASSWORD" not in os.environ

    def test_delete_secret_no_op_when_absent(self, provider, monkeypatch):
        """delete_secret does not raise when key is not in os.environ."""
        monkeypatch.delenv("ABSENT_KEY_XYZ", raising=False)
        # Must not raise
        provider.delete_secret("ABSENT_KEY_XYZ")

    def test_list_secret_keys_returns_only_secret_patterns(self, provider, monkeypatch):
        """list_secret_keys only returns keys containing KEY, SECRET, TOKEN, PASSWORD, CREDENTIALS."""
        monkeypatch.setenv("CONTAINS_KEY_HERE", "v1")  # pragma: allowlist secret
        monkeypatch.setenv("CONTAINS_SECRET_HERE", "v2")  # pragma: allowlist secret
        monkeypatch.setenv("CONTAINS_TOKEN_HERE", "v3")  # pragma: allowlist secret
        monkeypatch.setenv("CONTAINS_PASSWORD_HERE", "v4")  # pragma: allowlist secret
        monkeypatch.setenv("CONTAINS_CREDENTIALS_HERE", "v5")  # pragma: allowlist secret
        monkeypatch.setenv("PLAIN_VAR_NO_MATCH", "v6")
        monkeypatch.setenv("ANOTHER_PLAIN_ONE", "v7")

        keys = provider.list_secret_keys()

        assert "CONTAINS_KEY_HERE" in keys
        assert "CONTAINS_SECRET_HERE" in keys
        assert "CONTAINS_TOKEN_HERE" in keys
        assert "CONTAINS_PASSWORD_HERE" in keys
        assert "CONTAINS_CREDENTIALS_HERE" in keys
        assert "PLAIN_VAR_NO_MATCH" not in keys
        assert "ANOTHER_PLAIN_ONE" not in keys


class TestDotEnvSecretsProviderExtended:
    """Extended tests for DotEnvSecretsProvider filling coverage gaps."""

    @pytest.fixture(autouse=True)
    def _cleanup_env(self):
        """Remove any keys injected into os.environ by DotEnvSecretsProvider during tests."""
        keys_before = set(os.environ.keys())
        yield
        for key in list(os.environ.keys()):
            if key not in keys_before:
                del os.environ[key]

    def _make_provider(self, tmp_path, content: str) -> "DotEnvSecretsProvider":
        env_file = tmp_path / ".env"
        env_file.write_text(content, encoding="utf-8")
        return DotEnvSecretsProvider(env_file)

    def test_init_nonexistent_file_does_not_crash(self, tmp_path):
        """__init__ with a path that does not exist → no exception, _secrets is empty."""
        provider = DotEnvSecretsProvider(tmp_path / "no_such_file.env")
        assert provider._secrets == {}

    def test_load_env_file_skips_comments(self, tmp_path):
        """Lines starting with # are ignored and do not appear as keys."""
        provider = self._make_provider(tmp_path, "# this is a comment\nREAL_KEY=real\n")
        assert "# this is a comment" not in provider._secrets
        assert provider.get_secret("REAL_KEY") == "real"

    def test_load_env_file_skips_blank_lines(self, tmp_path):
        """Blank lines in the file are silently skipped."""
        provider = self._make_provider(tmp_path, "\n\nBLANK_KEY=value\n\n")
        assert provider.get_secret("BLANK_KEY") == "value"

    def test_load_env_file_parses_plain_key_value(self, tmp_path):
        """KEY=VALUE (no quotes) is parsed correctly."""
        provider = self._make_provider(tmp_path, "PLAIN=hello123\n")
        assert provider.get_secret("PLAIN") == "hello123"

    def test_load_env_file_parses_double_quoted_value(self, tmp_path):
        """KEY=\"VALUE\" strips surrounding double quotes."""
        provider = self._make_provider(tmp_path, 'DQUOTED="double quoted value"\n')
        assert provider.get_secret("DQUOTED") == "double quoted value"

    def test_load_env_file_parses_single_quoted_value(self, tmp_path):
        """KEY='VALUE' strips surrounding single quotes."""
        provider = self._make_provider(tmp_path, "SQUOTED='single quoted value'\n")
        assert provider.get_secret("SQUOTED") == "single quoted value"

    def test_get_secret_found_returns_value(self, tmp_path):
        """Key present in loaded file → value is returned."""
        provider = self._make_provider(tmp_path, "MY_TOKEN=abc123\n")  # pragma: allowlist secret
        assert provider.get_secret("MY_TOKEN") == "abc123"

    def test_get_secret_missing_no_default_raises(self, tmp_path):
        """Key absent + no default → SecretNotFoundError."""
        provider = self._make_provider(tmp_path, "OTHER_KEY=other\n")
        with pytest.raises(SecretNotFoundError) as exc_info:
            provider.get_secret("ABSENT_KEY")
        assert "ABSENT_KEY" in str(exc_info.value)

    def test_get_secret_missing_with_default_returns_default(self, tmp_path):
        """Key absent + default provided → default is returned."""
        provider = self._make_provider(tmp_path, "OTHER_KEY=other\n")
        result = provider.get_secret("ABSENT_KEY", default="fallback_val")
        assert result == "fallback_val"

    def test_get_secret_empty_value_raises(self, tmp_path):
        """Key present with empty value → SecretNotFoundError (empty after strip)."""
        provider = self._make_provider(tmp_path, "EMPTY_SECRET=   \n")  # pragma: allowlist secret
        with pytest.raises(SecretNotFoundError) as exc_info:
            provider.get_secret("EMPTY_SECRET")
        assert "empty" in str(exc_info.value).lower()

    def test_set_secret_updates_secrets_dict(self, tmp_path):
        """set_secret updates _secrets in memory (does NOT write to file)."""
        provider = self._make_provider(tmp_path, "EXISTING=old\n")
        provider.set_secret("NEW_API_KEY", "new_value")  # pragma: allowlist secret
        assert provider._secrets["NEW_API_KEY"] == "new_value"

    def test_set_secret_also_updates_environ(self, tmp_path):
        """set_secret sets the key in os.environ for cross-compatibility."""
        provider = self._make_provider(tmp_path, "EXISTING=old\n")
        provider.set_secret("ENV_COMPAT_KEY", "compat_val")  # pragma: allowlist secret
        assert os.environ.get("ENV_COMPAT_KEY") == "compat_val"

    def test_set_secret_does_not_persist_to_file(self, tmp_path):
        """set_secret is memory-only — the .env file on disk is not modified."""
        env_file = tmp_path / ".env"
        env_file.write_text("EXISTING=old\n", encoding="utf-8")
        provider = DotEnvSecretsProvider(env_file)
        provider.set_secret("RUNTIME_ONLY_KEY", "runtime_val")  # pragma: allowlist secret
        file_content = env_file.read_text(encoding="utf-8")
        assert "RUNTIME_ONLY_KEY" not in file_content

    def test_delete_secret_removes_from_secrets_and_environ(self, tmp_path):
        """delete_secret removes key from both _secrets dict and os.environ."""
        provider = self._make_provider(tmp_path, "DEL_TOKEN=gone\n")  # pragma: allowlist secret
        assert "DEL_TOKEN" in provider._secrets
        assert os.environ.get("DEL_TOKEN") == "gone"
        provider.delete_secret("DEL_TOKEN")
        assert "DEL_TOKEN" not in provider._secrets
        assert "DEL_TOKEN" not in os.environ

    def test_delete_secret_absent_is_no_op(self, tmp_path):
        """delete_secret for a key that does not exist must not raise."""
        provider = self._make_provider(tmp_path, "OTHER=val\n")
        provider.delete_secret("NOT_THERE_AT_ALL")  # must not raise

    def test_list_secret_keys_returns_all_file_keys(self, tmp_path):
        """list_secret_keys returns every key loaded from the .env file."""
        provider = self._make_provider(
            tmp_path, "ALPHA_KEY=1\nBETA_SECRET=2\nGAMMA_TOKEN=3\n"  # pragma: allowlist secret
        )
        keys = provider.list_secret_keys()
        assert set(keys) == {"ALPHA_KEY", "BETA_SECRET", "GAMMA_TOKEN"}


class TestSecretsManagerExtended:
    """Extended tests for SecretsManager to fill coverage gaps."""

    @pytest.fixture
    def mock_provider(self):
        """Return a mock provider that returns a value by default."""
        provider = MagicMock(spec=SecretsProvider)
        provider.get_secret.return_value = "test_value"
        provider.list_secret_keys.return_value = ["KEY_A", "KEY_B"]
        return provider

    @pytest.fixture
    def manager(self, mock_provider):
        return SecretsManager(provider=mock_provider)

    # --- get() ---

    def test_get_found_logs_access_with_found_true(self, manager):
        """get() records an access-log entry with found=True when the secret exists."""
        manager.get("FOUND_KEY")
        log = manager.get_access_log()
        assert len(log) == 1
        entry = log[0]
        assert entry["key"] == "FOUND_KEY"
        assert entry["found"] is True
        assert "timestamp" in entry

    def test_get_not_found_required_false_returns_default(self, manager, mock_provider):
        """get() with required=False returns the default when provider raises."""
        mock_provider.get_secret.side_effect = SecretNotFoundError("missing")
        result = manager.get("MISSING_KEY", default="fallback", required=False)
        assert result == "fallback"

    def test_get_not_found_required_false_logs_found_false(self, manager, mock_provider):
        """get() with required=False logs found=False in the access log."""
        mock_provider.get_secret.side_effect = SecretNotFoundError("missing")
        manager.get("OPT_KEY", required=False)
        log = manager.get_access_log()
        assert log[0]["found"] is False
        assert log[0]["key"] == "OPT_KEY"

    def test_get_not_found_required_true_raises(self, manager, mock_provider):
        """get() with required=True raises SecretNotFoundError for missing key."""
        mock_provider.get_secret.side_effect = SecretNotFoundError("missing")
        with pytest.raises(SecretNotFoundError):
            manager.get("REQUIRED_MISSING", required=True)

    # --- set() / delete() / list_keys() ---

    def test_set_delegates_to_provider(self, manager, mock_provider):
        """set() calls provider.set_secret with the exact key and value."""
        manager.set("DELEGATE_KEY", "delegate_val")
        mock_provider.set_secret.assert_called_once_with("DELEGATE_KEY", "delegate_val")

    def test_delete_delegates_to_provider(self, manager, mock_provider):
        """delete() calls provider.delete_secret with the exact key."""
        manager.delete("DEL_KEY")
        mock_provider.delete_secret.assert_called_once_with("DEL_KEY")

    def test_list_keys_returns_provider_keys(self, manager, mock_provider):
        """list_keys() delegates to provider and returns its result."""
        result = manager.list_keys()
        assert result == ["KEY_A", "KEY_B"]
        mock_provider.list_secret_keys.assert_called_once()

    # --- validate_required_secrets() ---

    def test_validate_all_present_does_not_raise(self, manager):
        """validate_required_secrets raises nothing when all keys are found."""
        manager.validate_required_secrets(["KEY_A", "KEY_B"])  # provider returns value

    def test_validate_missing_raises_with_all_missing_listed(self, manager, mock_provider):
        """validate_required_secrets raises with ALL missing keys in the message."""
        mock_provider.get_secret.side_effect = SecretNotFoundError("missing")
        with pytest.raises(SecretNotFoundError) as exc_info:
            manager.validate_required_secrets(["MISS_ONE", "MISS_TWO", "MISS_THREE"])
        error_msg = str(exc_info.value)
        assert "MISS_ONE" in error_msg
        assert "MISS_TWO" in error_msg
        assert "MISS_THREE" in error_msg

    # --- get_access_log() ---

    def test_get_access_log_returns_copy(self, manager):
        """get_access_log() returns a copy — mutating it does not affect the internal log."""
        manager.get("SOME_KEY")
        log_copy = manager.get_access_log()
        log_copy.clear()
        # Internal log must still have the entry
        assert len(manager.get_access_log()) == 1

    def test_get_access_log_multiple_entries(self, manager):
        """get_access_log() accumulates one entry per get() call."""
        manager.get("FIRST_KEY")
        manager.get("SECOND_KEY")
        manager.get("THIRD_KEY")
        log = manager.get_access_log()
        assert len(log) == 3
        assert [e["key"] for e in log] == ["FIRST_KEY", "SECOND_KEY", "THIRD_KEY"]

    # --- check_rotation_needed() ---

    def test_check_rotation_needed_always_false(self, manager):
        """check_rotation_needed() is a stub and always returns False."""
        assert manager.check_rotation_needed("ANY_KEY") is False
        assert manager.check_rotation_needed("OTHER_KEY", max_age_days=30) is False


class TestSecretsManagerAutoSelectExtended:
    """Extended auto-provider-selection tests for SecretsManager."""

    @pytest.fixture(autouse=True)
    def _clean_provider_env(self, monkeypatch):
        """Ensure SECRETS_PROVIDER does not bleed between tests."""
        monkeypatch.delenv("SECRETS_PROVIDER", raising=False)

    def test_explicit_environment_provider(self, tmp_path, monkeypatch):
        """SECRETS_PROVIDER='environment' → EnvironmentSecretsProvider selected."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SECRETS_PROVIDER", "environment")
        manager = SecretsManager()
        assert isinstance(manager.provider, EnvironmentSecretsProvider)

    def test_explicit_dotenv_provider_with_existing_file(self, tmp_path, monkeypatch):
        """SECRETS_PROVIDER='dotenv' → DotEnvSecretsProvider selected (default .env path)."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("DOTENV_KEY=val\n", encoding="utf-8")
        monkeypatch.setenv("SECRETS_PROVIDER", "dotenv")
        manager = SecretsManager()
        assert isinstance(manager.provider, DotEnvSecretsProvider)

    def test_auto_with_env_file_selects_dotenv(self, tmp_path, monkeypatch):
        """'auto' mode + .env present → DotEnvSecretsProvider selected."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("AUTO_KEY=auto_val\n", encoding="utf-8")
        # SECRETS_PROVIDER not set → defaults to 'auto'
        manager = SecretsManager()
        assert isinstance(manager.provider, DotEnvSecretsProvider)

    def test_auto_without_env_file_selects_environment(self, tmp_path, monkeypatch):
        """'auto' mode + no .env → EnvironmentSecretsProvider selected."""
        monkeypatch.chdir(tmp_path)
        # Ensure there is no .env in the tmp directory
        env_file = tmp_path / ".env"
        if env_file.exists():
            env_file.unlink()
        manager = SecretsManager()
        assert isinstance(manager.provider, EnvironmentSecretsProvider)


class TestGlobalFunctionsExtended:
    """Extended tests for module-level singleton functions."""

    @pytest.fixture(autouse=True)
    def _reset_singleton(self):
        """Reset the global singleton before and after each test."""
        import src.config.secrets_manager as sm

        sm._secrets_manager = None
        yield
        sm._secrets_manager = None

    def test_get_secrets_manager_returns_same_instance(self, tmp_path, monkeypatch):
        """get_secrets_manager() is a true singleton — repeated calls return the same object."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("SECRETS_PROVIDER", raising=False)
        first = get_secrets_manager()
        second = get_secrets_manager()
        assert first is second

    def test_get_secrets_manager_creates_new_after_reset(self, tmp_path, monkeypatch):
        """After resetting _secrets_manager to None a new instance is created."""
        import src.config.secrets_manager as sm

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("SECRETS_PROVIDER", raising=False)
        first = get_secrets_manager()
        sm._secrets_manager = None
        second = get_secrets_manager()
        assert first is not second

    def test_get_secret_convenience_delegates_to_manager(self, tmp_path, monkeypatch):
        """get_secret() convenience function calls through to the singleton manager."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SECRETS_PROVIDER", "environment")
        monkeypatch.setenv("CONV_MY_TOKEN", "tok_xyz")  # pragma: allowlist secret
        result = get_secret("CONV_MY_TOKEN")
        assert result == "tok_xyz"

    def test_get_secret_optional_returns_default(self, tmp_path, monkeypatch):
        """get_secret() with required=False returns default for missing key."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SECRETS_PROVIDER", "environment")
        monkeypatch.delenv("TOTALLY_MISSING_KEY_XYZ", raising=False)
        result = get_secret("TOTALLY_MISSING_KEY_XYZ", default="def_val", required=False)
        assert result == "def_val"
