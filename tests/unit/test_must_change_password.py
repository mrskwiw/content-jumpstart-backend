"""S-01.4f — must_change_password: default, exposure, and camelCase serialization."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models.user import User
from backend.schemas.auth import UserResponse


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


def test_model_defaults_false(db):
    # Existing / self-registered users are never forced to reset.
    u = User(id="u1", email="u1@x.com", hashed_password="x")
    db.add(u)
    db.commit()
    assert u.must_change_password is False


def test_model_accepts_true(db):
    u = User(id="u2", email="u2@x.com", hashed_password="x", must_change_password=True)
    db.add(u)
    db.commit()
    assert u.must_change_password is True


def _ns(**over):
    base = dict(
        id="u1",
        email="e@x.com",
        full_name="n",
        is_active=True,
        is_superuser=False,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        must_change_password=False,
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_userresponse_exposes_flag():
    r = UserResponse.model_validate(_ns(must_change_password=True))
    assert r.must_change_password is True


def test_userresponse_serializes_camelcase_for_frontend():
    r = UserResponse.model_validate(_ns(must_change_password=True))
    dumped = r.model_dump(by_alias=True)
    assert dumped["mustChangePassword"] is True


def test_userresponse_defaults_false_when_absent():
    # a source object without the attribute → schema default (backward compatible)
    ns = SimpleNamespace(
        id="u1",
        email="e@x.com",
        full_name="n",
        is_active=True,
        is_superuser=False,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )
    r = UserResponse.model_validate(ns)
    assert r.must_change_password is False
