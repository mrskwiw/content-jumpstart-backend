"""
Secrets Management Module

Provides secure access to sensitive configuration values with support for:
- Environment variables (production)
- .env files (development only)
- Future: HashiCorp Vault, AWS Secrets Manager

Security Features:
- No secrets in logs
- Validation on access
- Rotation tracking
- Audit trail

CRITICAL: Never log or print secret values
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SecretNotFoundError(Exception):
    """Raised when a required secret is not found"""


class SecretsProvider(ABC):
    """Abstract base class for secrets providers"""

    @abstractmethod
    def get_secret(self, key: str, default: Optional[str] = None) -> str:
        """Get a secret value by key"""

    @abstractmethod
    def set_secret(self, key: str, value: str) -> None:
        """Set a secret value (if supported)"""

    @abstractmethod
    def delete_secret(self, key: str) -> None:
        """Delete a secret (if supported)"""

    @abstractmethod
    def list_secret_keys(self) -> list[str]:
        """List all available secret keys (not values!)"""


class EnvironmentSecretsProvider(SecretsProvider):
    """
    Production-grade secrets provider using environment variables

    Best for:
    - Docker containers
    - Kubernetes secrets
    - Cloud platforms (AWS, GCP, Azure)

    Security:
    - Secrets injected at runtime
    - No disk storage
    - Process isolation
    """

    def __init__(self):
        logger.info("Initialized EnvironmentSecretsProvider (production mode)")

    def get_secret(self, key: str, default: Optional[str] = None) -> str:
        """Get secret from environment variable"""
        value = os.environ.get(key, default)

        if value is None:
            raise SecretNotFoundError(
                f"Secret '{key}' not found in environment variables. "
                f"Set it before starting the application."
            )

        # Validate non-empty
        if not value.strip():
            raise SecretNotFoundError(f"Secret '{key}' is empty")

        logger.debug(f"Retrieved secret '{key}' from environment (length: {len(value)})")
        return value

    def set_secret(self, key: str, value: str) -> None:
        """Set environment variable (not persistent)"""
        os.environ[key] = value
        logger.warning(
            f"Set secret '{key}' in environment (runtime only, not persistent). "
            f"Use external secrets manager for production."
        )

    def delete_secret(self, key: str) -> None:
        """Remove from environment"""
        if key in os.environ:
            del os.environ[key]
            logger.info(f"Deleted secret '{key}' from environment")

    def list_secret_keys(self) -> list[str]:
        """List environment variable keys (filtered for security)"""
        # Only list keys that look like secrets (contain certain patterns)
        secret_patterns = ['KEY', 'SECRET', 'TOKEN', 'PASSWORD', 'CREDENTIALS']
        return [
            key for key in os.environ.keys()
            if any(pattern in key.upper() for pattern in secret_patterns)
        ]


class DotEnvSecretsProvider(SecretsProvider):
    """
    Development-only secrets provider using .env files

    WARNING: Only use in development! Not secure for production.

    Security limitations:
    - Secrets stored on disk (plaintext)
    - Accessible to anyone with filesystem access
    - May be accidentally committed to version control
    """

    def __init__(self, env_file: Path = Path(".env")):
        self.env_file = env_file
        self._secrets: Dict[str, str] = {}
        self._load_env_file()

        logger.warning(
            f"Initialized DotEnvSecretsProvider (DEVELOPMENT ONLY) from {env_file}. "
            f"This is NOT secure for production!"
        )

    def _load_env_file(self) -> None:
        """Load secrets from .env file"""
        if not self.env_file.exists():
            logger.warning(f".env file not found at {self.env_file}")
            return

        try:
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()

                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue

                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")

                        self._secrets[key] = value
                        # Also set in environment for compatibility
                        os.environ[key] = value

            logger.info(f"Loaded {len(self._secrets)} secrets from {self.env_file}")

        except Exception as e:
            logger.error(f"Failed to load .env file: {e}")
            raise

    def get_secret(self, key: str, default: Optional[str] = None) -> str:
        """Get secret from .env file"""
        value = self._secrets.get(key, default)

        if value is None:
            raise SecretNotFoundError(
                f"Secret '{key}' not found in {self.env_file}. "
                f"Add it to the file: {key}=your_value_here"
            )

        if not value.strip():
            raise SecretNotFoundError(f"Secret '{key}' is empty in {self.env_file}")

        logger.debug(f"Retrieved secret '{key}' from .env (length: {len(value)})")
        return value

    def set_secret(self, key: str, value: str) -> None:
        """Update secret in memory (not persisted to file for security)"""
        self._secrets[key] = value
        os.environ[key] = value
        logger.warning(
            f"Set secret '{key}' in memory only. "
            f"Manually update {self.env_file} to persist."
        )

    def delete_secret(self, key: str) -> None:
        """Remove secret from memory"""
        if key in self._secrets:
            del self._secrets[key]
        if key in os.environ:
            del os.environ[key]
        logger.info(f"Deleted secret '{key}' from memory")

    def list_secret_keys(self) -> list[str]:
        """List all secret keys"""
        return list(self._secrets.keys())


class SecretsManager:
    """
    Central secrets management facade

    Usage:
        secrets = SecretsManager()
        api_key = secrets.get("ANTHROPIC_API_KEY")

    Automatic provider selection:
    - Production: EnvironmentSecretsProvider
    - Development: DotEnvSecretsProvider (if .env exists)
    """

    def __init__(self, provider: Optional[SecretsProvider] = None):
        """
        Initialize secrets manager

        Args:
            provider: Custom secrets provider (optional)
                     If None, auto-selects based on environment
        """
        if provider is None:
            provider = self._auto_select_provider()

        self.provider = provider
        self._access_log: list[Dict[str, Any]] = []

        logger.info(f"SecretsManager initialized with {provider.__class__.__name__}")

    def _auto_select_provider(self) -> SecretsProvider:
        """
        Auto-select secrets provider based on environment

        Priority:
        1. If SECRETS_PROVIDER env var is set, use it
        2. If .env file exists, use DotEnvSecretsProvider (dev)
        3. Otherwise, use EnvironmentSecretsProvider (production)
        """
        provider_type = os.environ.get('SECRETS_PROVIDER', 'auto').lower()

        if provider_type == 'environment':
            return EnvironmentSecretsProvider()

        if provider_type == 'dotenv':
            return DotEnvSecretsProvider()

        # Auto-detect
        env_file = Path('.env')
        if env_file.exists():
            logger.info("Detected .env file - using development mode")
            return DotEnvSecretsProvider(env_file)
        else:
            logger.info("No .env file - using production environment mode")
            return EnvironmentSecretsProvider()

    def get(self, key: str, default: Optional[str] = None, required: bool = True) -> Optional[str]:
        """
        Get a secret value

        Args:
            key: Secret key name (e.g., 'ANTHROPIC_API_KEY')
            default: Default value if not found
            required: If True, raises error if not found. If False, returns default.

        Returns:
            Secret value (never None if required=True)

        Raises:
            SecretNotFoundError: If required=True and secret not found
        """
        try:
            value = self.provider.get_secret(key, default)

            # Log access (but never log the value!)
            self._access_log.append({
                'key': key,
                'timestamp': datetime.now().isoformat(),
                'found': True,
            })

            return value

        except SecretNotFoundError:
            if required:
                logger.error(f"Required secret '{key}' not found")
                raise

            logger.debug(f"Optional secret '{key}' not found, using default")
            self._access_log.append({
                'key': key,
                'timestamp': datetime.now().isoformat(),
                'found': False,
            })

            return default

    def set(self, key: str, value: str) -> None:
        """
        Set a secret value (if provider supports it)

        WARNING: Most production providers don't support setting secrets
        via API. Use provider's native tools (AWS CLI, Vault CLI, etc.)
        """
        self.provider.set_secret(key, value)
        logger.info(f"Set secret '{key}'")

    def delete(self, key: str) -> None:
        """Delete a secret"""
        self.provider.delete_secret(key)
        logger.info(f"Deleted secret '{key}'")

    def list_keys(self) -> list[str]:
        """List all available secret keys (not values!)"""
        return self.provider.list_secret_keys()

    def validate_required_secrets(self, required_keys: list[str]) -> None:
        """
        Validate that all required secrets are present

        Args:
            required_keys: List of required secret keys

        Raises:
            SecretNotFoundError: If any required secret is missing
        """
        missing = []

        for key in required_keys:
            try:
                self.get(key, required=True)
            except SecretNotFoundError:
                missing.append(key)

        if missing:
            raise SecretNotFoundError(
                f"Missing required secrets: {', '.join(missing)}. "
                f"Set them before starting the application."
            )

        logger.info(f"Validated {len(required_keys)} required secrets")

    def get_access_log(self) -> list[Dict[str, Any]]:
        """
        Get audit log of secret accesses

        Returns:
            List of access events (key, timestamp, found)
            NEVER includes secret values
        """
        return self._access_log.copy()

    def check_rotation_needed(self, key: str, max_age_days: int = 90) -> bool:
        """
        Check if a secret needs rotation (placeholder)

        TODO: Implement rotation tracking with metadata storage

        Args:
            key: Secret key to check
            max_age_days: Maximum age before rotation needed

        Returns:
            True if rotation needed (currently always False)
        """
        # TODO: Store secret creation/rotation dates in metadata
        # For now, always return False
        logger.warning(f"Rotation tracking not yet implemented for '{key}'")
        return False


# Global singleton instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """
    Get global secrets manager instance (singleton)

    Usage:
        from src.config.secrets_manager import get_secrets_manager

        secrets = get_secrets_manager()
        api_key = secrets.get("ANTHROPIC_API_KEY")
    """
    global _secrets_manager

    if _secrets_manager is None:
        _secrets_manager = SecretsManager()

    return _secrets_manager


# Convenience function for quick access
def get_secret(key: str, default: Optional[str] = None, required: bool = True) -> Optional[str]:
    """
    Convenience function to get a secret

    Usage:
        from src.config.secrets_manager import get_secret

        api_key = get_secret("ANTHROPIC_API_KEY")
    """
    return get_secrets_manager().get(key, default, required)
