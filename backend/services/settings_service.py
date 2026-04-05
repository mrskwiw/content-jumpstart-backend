"""Service for managing user settings and encrypted API keys"""

import os
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from dotenv import set_key as dotenv_set_key

from ..models.setting import Setting

# Resolve backend/.env path relative to this file (backend/services/settings_service.py → backend/.env)
_ENV_FILE = Path(__file__).parent.parent / ".env"


def _persist_to_env(env_key: str, value: str) -> None:
    """Write a key/value to os.environ and to backend/.env for DB-restore resilience.

    Plaintext only — never write encrypted ciphertext here.
    If the .env file does not exist, only os.environ is updated.
    """
    os.environ[env_key] = value
    if _ENV_FILE.exists():
        try:
            dotenv_set_key(str(_ENV_FILE), env_key, value, quote_mode="never")
        except Exception:
            pass  # env persistence is best-effort; DB is the primary store


# Get encryption key from environment or generate one
# In production, this should be stored securely (e.g., AWS Secrets Manager)
ENCRYPTION_KEY = os.getenv("SETTINGS_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # Generate a key for development (WARNING: This will change on restart!)
    ENCRYPTION_KEY = Fernet.generate_key().decode()

cipher_suite = Fernet(
    ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
)


def encrypt_value(value: str) -> str:
    """Encrypt a sensitive value"""
    if not value:
        return value
    return cipher_suite.encrypt(value.encode()).decode()


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a sensitive value"""
    if not encrypted_value:
        return encrypted_value
    try:
        return cipher_suite.decrypt(encrypted_value.encode()).decode()
    except Exception:
        # If decryption fails, return empty string
        return ""


def get_setting(
    db: Session, user_id: int, key: str, category: str = "integrations", decrypt: bool = True
) -> Optional[str]:
    """
    Get a setting value for a user.

    Args:
        db: Database session
        user_id: User ID
        key: Setting key (e.g., "brave_api_key")
        category: Setting category (e.g., "integrations")
        decrypt: Whether to decrypt the value if encrypted

    Returns:
        Setting value or None if not found
    """
    setting = (
        db.query(Setting)
        .filter(Setting.user_id == user_id, Setting.key == key, Setting.category == category)
        .first()
    )

    if not setting:
        return None

    if setting.is_encrypted and decrypt:
        return decrypt_value(setting.value)

    return setting.value


def set_setting(
    db: Session,
    user_id: int,
    key: str,
    value: Optional[str],
    category: str = "integrations",
    encrypt: bool = True,
) -> Setting:
    """
    Set a setting value for a user.

    Args:
        db: Database session
        user_id: User ID
        key: Setting key (e.g., "brave_api_key")
        value: Setting value
        category: Setting category (e.g., "integrations")
        encrypt: Whether to encrypt the value

    Returns:
        Updated or created Setting object
    """
    # Find existing setting
    setting = (
        db.query(Setting)
        .filter(Setting.user_id == user_id, Setting.key == key, Setting.category == category)
        .first()
    )

    # Encrypt value if requested
    stored_value = encrypt_value(value) if encrypt and value else value

    if setting:
        # Update existing
        setting.value = stored_value
        setting.is_encrypted = 1 if encrypt else 0
    else:
        # Create new
        setting = Setting(
            user_id=user_id,
            key=key,
            value=stored_value,
            category=category,
            is_encrypted=1 if encrypt else 0,
        )
        db.add(setting)

    db.commit()
    db.refresh(setting)
    return setting


def delete_setting(db: Session, user_id: int, key: str, category: str = "integrations") -> bool:
    """
    Delete a setting for a user.

    Args:
        db: Database session
        user_id: User ID
        key: Setting key
        category: Setting category

    Returns:
        True if deleted, False if not found
    """
    setting = (
        db.query(Setting)
        .filter(Setting.user_id == user_id, Setting.key == key, Setting.category == category)
        .first()
    )

    if setting:
        db.delete(setting)
        db.commit()
        return True

    return False


def get_web_search_config(db: Session, user_id: int) -> dict:
    """
    Get web search configuration for a user.

    Checks user settings first, then falls back to environment variables.
    This allows system-wide API keys to be configured via .env file.

    Returns:
        dict with keys: provider, brave_api_key, tavily_api_key, serpapi_api_key
    """
    # Get provider: user DB setting → env fallback (survives DB restore) → default stub
    provider = (
        get_setting(db, user_id, "web_search_provider", decrypt=False)
        or os.getenv("WEB_SEARCH_PROVIDER")
        or "stub"
    )

    # Get API keys: DB setting → env fallback (survives DB restore) → empty
    brave_key = get_setting(db, user_id, "brave_api_key") or os.getenv("BRAVE_API_KEY") or ""
    tavily_key = get_setting(db, user_id, "tavily_api_key") or os.getenv("TAVILY_API_KEY") or ""
    serpapi_key = get_setting(db, user_id, "serpapi_api_key") or os.getenv("SERPAPI_API_KEY") or ""

    # Auto-detect provider from available keys when provider is unset.
    # Handles the case where keys are in .env but WEB_SEARCH_PROVIDER was never written
    # (e.g. keys pre-date this feature, or DB was restored without the env entry).
    if provider == "stub":
        if tavily_key:
            provider = "tavily"
        elif brave_key:
            provider = "brave"
        elif serpapi_key:
            provider = "serpapi"

    return {
        "provider": provider,
        "brave_api_key": brave_key,
        "tavily_api_key": tavily_key,
        "serpapi_api_key": serpapi_key,
    }


def set_web_search_config(
    db: Session,
    user_id: int,
    provider: str,
    brave_api_key: Optional[str] = None,
    tavily_api_key: Optional[str] = None,
    serpapi_api_key: Optional[str] = None,
) -> dict:
    """
    Set web search configuration for a user.

    Args:
        db: Database session
        user_id: User ID
        provider: "brave", "tavily", "serpapi", or "stub"
        brave_api_key: Brave Search API key (optional)
        tavily_api_key: Tavily API key (optional)
        serpapi_api_key: SerpAPI key (optional)

    Returns:
        Updated configuration dict
    """
    # Set provider
    set_setting(db, user_id, "web_search_provider", provider, encrypt=False)
    _persist_to_env("WEB_SEARCH_PROVIDER", provider)

    # Set API keys if provided
    if brave_api_key is not None:
        if brave_api_key:
            set_setting(db, user_id, "brave_api_key", brave_api_key, encrypt=True)
            _persist_to_env("BRAVE_API_KEY", brave_api_key)
        else:
            delete_setting(db, user_id, "brave_api_key")
            _persist_to_env("BRAVE_API_KEY", "")

    if tavily_api_key is not None:
        if tavily_api_key:
            set_setting(db, user_id, "tavily_api_key", tavily_api_key, encrypt=True)
            _persist_to_env("TAVILY_API_KEY", tavily_api_key)
        else:
            delete_setting(db, user_id, "tavily_api_key")
            _persist_to_env("TAVILY_API_KEY", "")

    if serpapi_api_key is not None:
        if serpapi_api_key:
            set_setting(db, user_id, "serpapi_api_key", serpapi_api_key, encrypt=True)
            _persist_to_env("SERPAPI_API_KEY", serpapi_api_key)
        else:
            delete_setting(db, user_id, "serpapi_api_key")
            _persist_to_env("SERPAPI_API_KEY", "")

    return get_web_search_config(db, user_id)
