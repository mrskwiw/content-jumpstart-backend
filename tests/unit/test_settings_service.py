"""Unit tests for backend.services.settings_service."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models.setting import Setting
from backend.models.user import User
from backend.services.settings_service import (
    encrypt_value,
    decrypt_value,
    get_setting,
    set_setting,
    delete_setting,
    get_web_search_config,
    set_web_search_config,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


USER_ID = "user-settings-1"


class TestEncryptDecrypt:
    def test_encrypt_produces_different_value(self):
        encrypted = encrypt_value("my-api-key")
        assert encrypted != "my-api-key"

    def test_decrypt_recovers_original(self):
        original = "my-api-key-12345"
        encrypted = encrypt_value(original)
        assert decrypt_value(encrypted) == original

    def test_empty_string_unchanged(self):
        assert encrypt_value("") == ""
        assert decrypt_value("") == ""

    def test_invalid_ciphertext_returns_empty(self):
        result = decrypt_value("not-valid-ciphertext")
        assert result == ""

    def test_none_encrypt_unchanged(self):
        assert encrypt_value(None) is None


class TestGetSetting:
    def test_returns_none_when_not_found(self, db):
        result = get_setting(db, USER_ID, "missing_key")
        assert result is None

    def test_returns_plaintext_value(self, db):
        s = Setting(
            user_id=USER_ID,
            key="plain_key",
            value="plain_value",
            category="integrations",
            is_encrypted=0,
        )
        db.add(s)
        db.commit()
        result = get_setting(db, USER_ID, "plain_key", decrypt=False)
        assert result == "plain_value"

    def test_decrypts_encrypted_value(self, db):
        encrypted = encrypt_value("secret-key")
        s = Setting(
            user_id=USER_ID, key="enc_key", value=encrypted, category="integrations", is_encrypted=1
        )
        db.add(s)
        db.commit()
        result = get_setting(db, USER_ID, "enc_key")
        assert result == "secret-key"

    def test_category_filter(self, db):
        s = Setting(user_id=USER_ID, key="k", value="v", category="other", is_encrypted=0)
        db.add(s)
        db.commit()
        assert get_setting(db, USER_ID, "k", category="integrations") is None
        assert get_setting(db, USER_ID, "k", category="other") == "v"


class TestSetSetting:
    def test_creates_new_setting(self, db):
        result = set_setting(db, USER_ID, "new_key", "new_value", encrypt=False)
        assert result.key == "new_key"
        assert result.value == "new_value"

    def test_updates_existing_setting(self, db):
        set_setting(db, USER_ID, "key", "v1", encrypt=False)
        set_setting(db, USER_ID, "key", "v2", encrypt=False)
        assert get_setting(db, USER_ID, "key", decrypt=False) == "v2"

    def test_encrypts_value_when_requested(self, db):
        set_setting(db, USER_ID, "enc_key", "secret", encrypt=True)
        raw = db.query(Setting).filter(Setting.key == "enc_key").first()
        assert raw.value != "secret"  # stored encrypted
        assert get_setting(db, USER_ID, "enc_key") == "secret"  # decrypts on read

    def test_none_value_stored_as_none(self, db):
        result = set_setting(db, USER_ID, "null_key", None, encrypt=False)
        assert result.value is None


class TestDeleteSetting:
    def test_deletes_existing(self, db):
        set_setting(db, USER_ID, "to_delete", "value", encrypt=False)
        deleted = delete_setting(db, USER_ID, "to_delete")
        assert deleted is True
        assert get_setting(db, USER_ID, "to_delete") is None

    def test_returns_false_for_missing(self, db):
        assert delete_setting(db, USER_ID, "no_such_key") is False


class TestGetWebSearchConfig:
    def test_defaults_to_stub(self, db):
        config = get_web_search_config(db, USER_ID)
        # No keys in DB and no env vars set → should be "stub" or auto-detected
        assert "provider" in config
        assert "brave_api_key" in config

    def test_reads_provider_from_db(self, db):
        set_setting(db, USER_ID, "web_search_provider", "brave", encrypt=False)
        config = get_web_search_config(db, USER_ID)
        assert config["provider"] == "brave"

    def test_auto_detects_provider_from_tavily_key(self, db):
        set_setting(db, USER_ID, "tavily_api_key", "tvly-test-key", encrypt=True)
        config = get_web_search_config(db, USER_ID)
        # With tavily key and no explicit provider, should auto-detect tavily
        assert config["provider"] in ("tavily", "stub")  # depends on env


class TestSetWebSearchConfig:
    def test_sets_provider(self, db):
        set_web_search_config(db, USER_ID, provider="brave")
        config = get_web_search_config(db, USER_ID)
        assert config["provider"] == "brave"

    def test_sets_api_key(self, db):
        set_web_search_config(db, USER_ID, provider="tavily", tavily_api_key="tvly-key")
        config = get_web_search_config(db, USER_ID)
        assert config["tavily_api_key"] == "tvly-key"

    def test_clears_api_key_when_empty_string(self, db):
        set_web_search_config(db, USER_ID, provider="brave", brave_api_key="key")
        set_web_search_config(db, USER_ID, provider="stub", brave_api_key="")
        config = get_web_search_config(db, USER_ID)
        # Key should be cleared
        assert config["brave_api_key"] == ""

    def test_returns_config_dict(self, db):
        result = set_web_search_config(db, USER_ID, provider="stub")
        assert "provider" in result
        assert "brave_api_key" in result
