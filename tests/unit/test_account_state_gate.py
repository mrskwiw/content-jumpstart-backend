"""S-01.4d — account-state suspension gate on the spend path."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models.user import User
from backend.services import account_state, credit_service
from backend.services.account_state import AccountSuspendedError
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


def _user(db, cached=1000):
    u = User(id="u1", email="u1@x.com", hashed_password="x", is_active=True, credit_balance=cached)
    db.add(u)
    db.commit()
    return u


def test_default_state_is_active_and_spendable(db):
    assert account_state.account_state(db) == "active"
    assert account_state.is_spendable(db) is True
    account_state.require_spendable(db)  # no raise


@pytest.mark.parametrize("state", ["active", "trial"])
def test_spendable_states_allow(db, state):
    set_instance_config(db, "account_state", state)
    assert account_state.is_spendable(db) is True
    account_state.require_spendable(db)


@pytest.mark.parametrize("state", ["past_due", "suspended"])
def test_blocked_states_raise(db, state):
    set_instance_config(db, "account_state", state)
    assert account_state.is_spendable(db) is False
    with pytest.raises(AccountSuspendedError) as ei:
        account_state.require_spendable(db)
    assert ei.value.state == state


def test_deduct_blocked_when_suspended(db):
    _user(db)
    set_instance_config(db, "account_state", "suspended")
    with pytest.raises(AccountSuspendedError):
        credit_service.deduct_credits(db, "u1", 10, "should be blocked")


def test_deduct_allowed_when_active(db):
    _user(db)
    set_instance_config(db, "account_state", "active")
    credit_service.deduct_credits(db, "u1", 10, "ok")
    assert credit_service.get_balance(db, "u1") == 990


def test_refund_not_gated_by_suspension(db):
    # suspension blocks SPENDS, not refunds/credits back
    _user(db, cached=0)
    set_instance_config(db, "account_state", "suspended")
    credit_service.refund_credits(db, "u1", 25, "refund still works")
    assert credit_service.get_balance(db, "u1") == 25
