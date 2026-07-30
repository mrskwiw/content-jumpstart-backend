"""S-01.4b-i — FEFO credit-lot engine (standalone, no credit_service coupling)."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models.credit_lot import CreditLot
from backend.services.credit_lots import (
    InsufficientCreditsError,
    available_balance,
    consume_fefo,
    expire_lots,
    grant,
)

USER = "user-1"
NOW = datetime(2026, 7, 30, 12, 0, 0)


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


def test_grant_creates_lot(db):
    lot = grant(db, USER, 1000, "allowance", expires_at=NOW + timedelta(days=30))
    assert lot.remaining == 1000 and lot.amount == 1000
    assert available_balance(db, USER, now=NOW) == 1000


def test_grant_rejects_nonpositive(db):
    with pytest.raises(ValueError):
        grant(db, USER, 0, "allowance")


def test_available_balance_excludes_expired(db):
    grant(db, USER, 500, "allowance", expires_at=NOW - timedelta(days=1))  # expired
    grant(db, USER, 300, "topup", expires_at=None)  # never
    assert available_balance(db, USER, now=NOW) == 300


def test_consume_fefo_soonest_expiry_first(db):
    # top-up (never) + two allowances expiring at different times
    grant(db, USER, 100, "topup", expires_at=None)
    grant(db, USER, 100, "allowance", expires_at=NOW + timedelta(days=30))  # later
    grant(db, USER, 100, "allowance", expires_at=NOW + timedelta(days=5))  # soonest
    consume_fefo(db, USER, 120, now=NOW)
    # soonest (5d) fully drained, then the 30d one takes the remainder, top-up untouched
    lots = {_days(lot, NOW): lot.remaining for lot in db.query(CreditLot).all()}
    assert lots[5] == 0
    assert lots[30] == 80
    assert lots[None] == 100  # never-expire preserved last
    assert available_balance(db, USER, now=NOW) == 180


def test_consume_skips_expired_lots(db):
    grant(db, USER, 100, "allowance", expires_at=NOW - timedelta(days=1))  # expired
    grant(db, USER, 100, "topup", expires_at=None)
    consume_fefo(db, USER, 50, now=NOW)
    # spend came from the live top-up, not the expired lot
    assert available_balance(db, USER, now=NOW) == 50


def test_consume_insufficient_raises_and_no_partial_spend(db):
    grant(db, USER, 30, "topup")
    with pytest.raises(InsufficientCreditsError):
        consume_fefo(db, USER, 100, now=NOW)
    # nothing was drawn down
    assert available_balance(db, USER, now=NOW) == 30


def test_consume_rejects_nonpositive(db):
    with pytest.raises(ValueError):
        consume_fefo(db, USER, 0)


def test_session_usable_after_insufficient_error(db):
    # Decision #201: consume_fefo does not commit/rollback and does not self-lock,
    # so an insufficient-credits error leaves the caller's session fully usable
    # (no wiped work, no held locks) — the caller owns the transaction.
    grant(db, USER, 30, "topup")
    with pytest.raises(InsufficientCreditsError):
        consume_fefo(db, USER, 100, now=NOW)
    # the session still works: prior grant intact + a new grant + a valid consume
    grant(db, USER, 100, "topup")
    consume_fefo(db, USER, 50, now=NOW)
    assert available_balance(db, USER, now=NOW) == 80  # 30 + 100 - 50


def test_expire_lots_sweeps_lapsed(db):
    grant(db, USER, 100, "allowance", expires_at=NOW - timedelta(days=1))  # lapsed w/ remainder
    grant(db, USER, 50, "topup", expires_at=None)
    swept = expire_lots(db, now=NOW)
    assert swept == 1
    lapsed = db.query(CreditLot).filter(CreditLot.source == "allowance").first()
    assert lapsed.remaining == 0
    assert available_balance(db, USER, now=NOW) == 50


def test_expire_lots_noop_when_nothing_lapsed(db):
    grant(db, USER, 100, "topup", expires_at=None)
    assert expire_lots(db, now=NOW) == 0


def test_spend_and_sweep_operate_on_disjoint_lots(db):
    # Decision #201: consume touches only LIVE lots, sweep only EXPIRED-with-
    # remaining — disjoint sets, so interleaving them can't corrupt balances.
    grant(db, USER, 100, "allowance", expires_at=NOW - timedelta(days=1))  # expired
    grant(db, USER, 200, "topup", expires_at=None)  # live
    consume_fefo(db, USER, 150, now=NOW)  # spends only from the live top-up
    swept = expire_lots(db, now=NOW)  # zeroes only the expired allowance
    assert swept == 1
    # live top-up: 200 - 150 = 50; expired allowance: reclaimed to 0
    assert available_balance(db, USER, now=NOW) == 50
    live = db.query(CreditLot).filter(CreditLot.source == "topup").first()
    dead = db.query(CreditLot).filter(CreditLot.source == "allowance").first()
    assert live.remaining == 50 and dead.remaining == 0


def _days(lot: CreditLot, now: datetime):
    """Helper: how many days out a lot expires (None if never), for assertions."""
    if lot.expires_at is None:
        return None
    return (lot.expires_at - now).days
