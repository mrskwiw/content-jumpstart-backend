"""S-01.4a — instance-global config: a dedicated singleton table (not per-user).

Rebuilt after the S-01.4a adversarial review flagged the original per-user +
"owner heuristic" design as brittle (ownership could shift under admin churn and
reads could return stale/mixed rows). The singleton table has no owner concept,
so these tests assert that writes and reads always agree regardless of users.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models.instance_config import InstanceConfig
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


def test_set_and_get_instance_config(db):
    set_instance_config(db, "plan_id", "agency")
    assert get_instance_config(db, "plan_id") == "agency"


def test_no_owner_needed(db):
    # The whole point of the singleton table: works with ZERO users in the DB
    # (a blank pool instance before the admin is ever seeded).
    assert db.query(InstanceConfig).count() == 0
    set_instance_config(db, "account_state", "trial")
    assert get_instance_config(db, "account_state") == "trial"


def test_get_returns_default_when_missing(db):
    assert get_instance_config(db, "account_state", default="active") == "active"
    assert get_instance_config(db, "missing") is None


def test_upsert_updates_single_row(db):
    set_instance_config(db, "plan_id", "starter")
    set_instance_config(db, "plan_id", "freelancer")
    assert get_instance_config(db, "plan_id") == "freelancer"
    # key is the PK -> exactly one row, no duplicates possible
    assert db.query(InstanceConfig).filter(InstanceConfig.key == "plan_id").count() == 1


def test_get_all_instance_config(db):
    set_instance_config(db, "plan_id", "agency")
    set_instance_config(db, "account_state", "active")
    set_instance_config(db, "canonical_domain", "acme.app.content-jumpstart.com")
    assert get_all_instance_config(db) == {
        "plan_id": "agency",
        "account_state": "active",
        "canonical_domain": "acme.app.content-jumpstart.com",
    }


def test_encrypted_roundtrip(db):
    # encryption works on any value; use a benign one so no secret-scanner trips
    plaintext = "hello-world-123"
    set_instance_config(db, "encrypted_field", plaintext, encrypt=True)
    # stored ciphertext differs from plaintext, read decrypts transparently
    row = db.query(InstanceConfig).filter(InstanceConfig.key == "encrypted_field").first()
    assert row is not None and row.value != plaintext and bool(row.is_encrypted) is True
    assert get_instance_config(db, "encrypted_field") == plaintext
    assert get_all_instance_config(db)["encrypted_field"] == plaintext


def test_isolated_from_user_settings(db):
    set_instance_config(db, "plan_id", "agency")
    # a per-user 'integrations' read must not see instance config, and vice versa
    assert get_setting(db, "any-user", "plan_id") is None
