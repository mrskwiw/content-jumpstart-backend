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


# Get encryption key from environment or generate one.
# This key encrypts every at-rest secret the app stores: user API keys (Settings)
# AND OAuth platform tokens (Phase 10 platform_credentials). It MUST be stable
# across restarts — a per-process key silently orphans every previously-encrypted
# value (decrypt_value then returns "" and downstream publishing/lookups fail).
# In production, store it in the platform secret store (Render env var / AWS
# Secrets Manager). Generate one with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY = os.getenv("SETTINGS_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # DEBUG_MODE is the app's prod/dev switch (see backend/config.py). Outside
    # dev, refuse to boot without a stable key rather than silently rotate it and
    # lose access to every stored credential on the next restart.
    _is_debug = os.getenv("DEBUG_MODE", "true").strip().lower() in ("1", "true", "yes")
    if not _is_debug:
        raise RuntimeError(
            "SETTINGS_ENCRYPTION_KEY is not set. Refusing to start: a per-process "
            "encryption key would orphan all stored API keys and OAuth tokens on "
            "the next restart. Set SETTINGS_ENCRYPTION_KEY to a stable Fernet key "
            '(python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())").'
        )
    # Dev-only fallback: generate an ephemeral key so local runs work, but warn
    # loudly because anything encrypted this process will be unreadable next boot.
    import logging as _logging

    _logging.getLogger(__name__).warning(
        "SETTINGS_ENCRYPTION_KEY not set - generated an EPHEMERAL dev key. "
        "Stored API keys and OAuth tokens will NOT survive a restart. Set "
        "SETTINGS_ENCRYPTION_KEY for any persistent environment."
    )
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


# ── Instance-global config (S-01.4a) ──────────────────────────────────────────
# Instance-global values (plan tier, account state, CORS origins, canonical
# domain) live in a dedicated SINGLETON table (backend/models/instance_config.py),
# NOT the per-user `settings` table. The control plane writes these at runtime
# (S-01.4) so plan/domain changes take effect WITHOUT a redeploy.
#
# Why a dedicated table (not a `settings` category): instance config must survive
# admin churn (create/promote/demote/soft-delete). Deriving an "owner" user to
# hold it is brittle — ownership can shift and reads can return stale/mixed rows
# (the flaw the S-01.4a adversarial review caught). One row per key has no owner
# concept, so writes and reads always agree.


# ── instance-config read cache ────────────────────────────────────────────────
# The entitlement gate reads `account_state` on EVERY authenticated request, so an
# uncached lookup put one SELECT in front of ~200 endpoints to fetch a value that
# changes perhaps monthly. Instance config is instance-GLOBAL (one row per key, no
# owner) and near-static, which is what makes a plain process-local cache safe.
#
# Writes go through set_instance_config, which invalidates — so the TTL only bounds
# staleness from a write by ANOTHER process (a control-plane suspension, or a second
# web worker). 30s is the deliberate ceiling on "how long can a suspended account
# keep working": short enough to be immaterial, long enough to erase the per-request
# query. Deliberately NOT Redis — this must stay correct while Redis is unavailable
# in production (see the startup log), and per-process is sufficient for a value
# that is global and rarely written.
_CONFIG_TTL_SECONDS = 30.0
_config_cache: dict[str, tuple[Optional[str], float]] = {}


def invalidate_instance_config_cache(key: Optional[str] = None) -> None:
    """Drop one key (or the whole cache) — called on write, and by tests."""
    if key is None:
        _config_cache.clear()
    else:
        _config_cache.pop(key, None)


def get_instance_config(db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
    """Read an instance-global config value; returns ``default`` when unset.

    Cached for ``_CONFIG_TTL_SECONDS``. Note the cache stores the resolved value
    only — ``default`` is applied per call, so two callers passing different
    defaults for an unset key still each get their own.
    """
    import time

    from ..models.instance_config import InstanceConfig

    hit = _config_cache.get(key)
    if hit is not None and hit[1] > time.monotonic():
        return hit[0] if hit[0] is not None else default

    row = db.query(InstanceConfig).filter(InstanceConfig.key == key).first()
    value = (
        None
        if (row is None or row.value is None)
        else (decrypt_value(row.value) if row.is_encrypted else row.value)
    )
    _config_cache[key] = (value, time.monotonic() + _CONFIG_TTL_SECONDS)
    return value if value is not None else default


def set_instance_config(db: Session, key: str, value: Optional[str], encrypt: bool = False):
    """Upsert an instance-global config value (one row per key)."""
    from ..models.instance_config import InstanceConfig

    stored_value = encrypt_value(value) if (encrypt and value) else value
    row = db.query(InstanceConfig).filter(InstanceConfig.key == key).first()
    if row:
        row.value = stored_value
        row.is_encrypted = bool(encrypt)
    else:
        row = InstanceConfig(key=key, value=stored_value, is_encrypted=bool(encrypt))
        db.add(row)
    db.commit()
    db.refresh(row)
    # After the commit, so a failed write cannot evict a still-correct cached value.
    invalidate_instance_config_cache(key)
    return row


def get_all_instance_config(db: Session) -> dict:
    """All instance-global config as a ``{key: value}`` dict (bulk read / caching)."""
    from ..models.instance_config import InstanceConfig

    out: dict = {}
    for row in db.query(InstanceConfig).all():
        if row.value is None:
            continue
        out[row.key] = decrypt_value(row.value) if row.is_encrypted else row.value
    return out


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
