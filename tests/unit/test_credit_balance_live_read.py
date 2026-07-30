"""S-01.4b-ii review fix — balance reads derive from live lots, not the cache.

Regression for the adversarial-review no-ship: an idle user whose allowance lot
expired must NOT keep reporting an overstated (unspendable) balance just because
no write refreshed the cached ``credit_balance`` column.
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models.user import User
from backend.services import credit_lots, credit_service

_PAST = datetime(2020, 1, 1)  # expired regardless of real "now"


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


def _user(db, uid="u1", cached=0):
    u = User(
        id=uid, email=f"{uid}@x.com", hashed_password="x", is_active=True, credit_balance=cached
    )
    db.add(u)
    db.commit()
    return u


def test_get_balance_excludes_expired_without_any_mutation(db):
    # Cached column deliberately stale/overstated (999); lots tell the truth.
    _user(db, cached=999)
    credit_lots.grant(db, "u1", 100, "allowance", expires_at=_PAST)  # expired
    credit_lots.grant(db, "u1", 50, "topup", expires_at=None)  # live
    db.commit()
    # No mutation happens — read must still reflect only the 50 live credits.
    assert credit_service.get_balance(db, "u1") == 50
    assert credit_service.live_balance(db, "u1") == 50
    assert credit_service.get_credit_summary(db, "u1")["balance"] == 50


def test_legacy_user_without_lots_reads_cached_balance(db):
    # Un-migrated legacy user: no lots yet, so the flat column is the source.
    _user(db, cached=1000)
    assert credit_service.get_balance(db, "u1") == 1000
    assert credit_service.live_balance(db, "u1") == 1000


def test_read_then_spend_are_consistent(db):
    _user(db, cached=999)
    credit_lots.grant(db, "u1", 100, "allowance", expires_at=_PAST)  # expired
    credit_lots.grant(db, "u1", 50, "topup", expires_at=None)  # live
    db.commit()
    # reported balance (50) matches what can actually be spent
    assert credit_service.get_balance(db, "u1") == 50
    credit_service.deduct_credits(db, "u1", 50, "spend all live")
    assert credit_service.get_balance(db, "u1") == 0
    with pytest.raises(credit_service.InsufficientCreditsError):
        credit_service.deduct_credits(db, "u1", 1, "overspend")
