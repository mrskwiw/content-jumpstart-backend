"""S-01.4a — instance-global config namespace on settings_service."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models.setting import Setting
from backend.models.user import User
from backend.services.settings_service import (
    get_all_instance_config,
    get_instance_config,
    get_setting,
    set_instance_config,
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


def _make_owner(db, user_id="owner-1"):
    owner = User(
        id=user_id,
        email=f"{user_id}@x.com",
        hashed_password="x",
        is_active=True,
        is_superuser=True,
    )
    db.add(owner)
    db.commit()
    return owner


def test_set_and_get_instance_config(db):
    _make_owner(db)
    set_instance_config(db, "plan_id", "agency")
    assert get_instance_config(db, "plan_id") == "agency"


def test_get_returns_default_when_missing(db):
    _make_owner(db)
    assert get_instance_config(db, "account_state", default="active") == "active"
    assert get_instance_config(db, "missing") is None


def test_upsert_updates_value(db):
    _make_owner(db)
    set_instance_config(db, "plan_id", "starter")
    set_instance_config(db, "plan_id", "freelancer")
    assert get_instance_config(db, "plan_id") == "freelancer"
    # exactly one row (upsert, not insert)
    rows = db.query(Setting).filter(Setting.key == "plan_id").all()
    assert len(rows) == 1


def test_get_all_instance_config(db):
    _make_owner(db)
    set_instance_config(db, "plan_id", "agency")
    set_instance_config(db, "account_state", "active")
    set_instance_config(db, "canonical_domain", "acme.app.content-jumpstart.com")
    cfg = get_all_instance_config(db)
    assert cfg == {
        "plan_id": "agency",
        "account_state": "active",
        "canonical_domain": "acme.app.content-jumpstart.com",
    }


def test_set_requires_owner(db):
    # no superuser exists yet (pre-claim pool instance)
    with pytest.raises(RuntimeError):
        set_instance_config(db, "plan_id", "agency")


def test_instance_config_isolated_from_user_settings(db):
    owner = _make_owner(db)
    set_instance_config(db, "plan_id", "agency")
    # a normal per-user 'integrations' read must not see instance config
    assert get_setting(db, owner.id, "plan_id") is None
    # and instance config is stored unencrypted
    row = db.query(Setting).filter(Setting.key == "plan_id").first()
    assert row is not None
    assert bool(row.is_encrypted) is False
    assert row.value == "agency"


def test_owner_is_earliest_superuser(db):
    _make_owner(db, "owner-1")
    _make_owner(db, "owner-2")
    set_instance_config(db, "plan_id", "agency")
    # stored under the earliest superuser
    row = db.query(Setting).filter(Setting.key == "plan_id").first()
    assert row is not None
    assert row.user_id == "owner-1"
