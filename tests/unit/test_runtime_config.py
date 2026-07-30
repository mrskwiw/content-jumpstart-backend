"""S-01.4e — runtime instance-config resolvers (settings-with-env fallback)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.services.runtime_config import (
    resolved_cors_origins,
    resolved_oauth_redirect_base,
)
from backend.services.settings_service import set_instance_config


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


ENV_ORIGINS = ["https://slot-1.app.content-jumpstart.com", "http://localhost:5173"]


def test_cors_env_only_when_no_instance_config(db):
    assert resolved_cors_origins(db, ENV_ORIGINS) == ENV_ORIGINS


def test_cors_unions_instance_config(db):
    set_instance_config(db, "cors_origins", "https://acme.com, https://www.acme.com")
    result = resolved_cors_origins(db, ENV_ORIGINS)
    assert result == ENV_ORIGINS + ["https://acme.com", "https://www.acme.com"]


def test_cors_dedupes(db):
    set_instance_config(db, "cors_origins", "http://localhost:5173, https://acme.com")
    result = resolved_cors_origins(db, ENV_ORIGINS)
    # localhost already present in env — not duplicated
    assert result == ENV_ORIGINS + ["https://acme.com"]


def test_cors_env_always_kept(db):
    # the baked-in wildcard subdomain is never dropped when a custom domain is added
    set_instance_config(db, "cors_origins", "https://acme.com")
    result = resolved_cors_origins(db, ENV_ORIGINS)
    assert "https://slot-1.app.content-jumpstart.com" in result


def test_oauth_base_env_fallback(db, monkeypatch):
    monkeypatch.setenv("OAUTH_REDIRECT_BASE_URL", "https://env.example.com/")
    assert resolved_oauth_redirect_base(db) == "https://env.example.com"  # trailing slash stripped


def test_oauth_base_instance_config_overrides_env(db, monkeypatch):
    monkeypatch.setenv("OAUTH_REDIRECT_BASE_URL", "https://env.example.com")
    set_instance_config(db, "oauth_redirect_base", "https://acme.com/")
    assert resolved_oauth_redirect_base(db) == "https://acme.com"


def test_oauth_base_empty_when_unset(db, monkeypatch):
    monkeypatch.delenv("OAUTH_REDIRECT_BASE_URL", raising=False)
    assert resolved_oauth_redirect_base(db) == ""
