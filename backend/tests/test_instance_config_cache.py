"""Instance-config read cache (AUDIT-01 / P1).

The entitlement gate reads `account_state` on every authenticated request, so this
cache sits in front of ~200 endpoints. The risk is not "is it fast" but "is it
correct": a stale account_state keeps a suspended account working, and a cache that
misses an invalidation is worse than no cache.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.services import settings_service as svc


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False, future=True)
    svc.invalidate_instance_config_cache()
    with factory() as s:
        yield s
    svc.invalidate_instance_config_cache()


class _CountingSession:
    """Wraps a session and counts .query() calls, to prove the cache is doing work."""

    def __init__(self, inner):
        self._inner = inner
        self.queries = 0

    def query(self, *a, **kw):
        self.queries += 1
        return self._inner.query(*a, **kw)

    def __getattr__(self, name):
        return getattr(self._inner, name)


def test_repeat_reads_hit_the_cache(db):
    svc.set_instance_config(db, "account_state", "active")
    counting = _CountingSession(db)

    assert svc.get_instance_config(counting, "account_state") == "active"
    for _ in range(20):
        svc.get_instance_config(counting, "account_state")

    assert counting.queries == 1, "the per-request DB read is back"


def test_write_invalidates_immediately(db):
    # A suspension must take effect on the next request, not after the TTL.
    svc.set_instance_config(db, "account_state", "active")
    assert svc.get_instance_config(db, "account_state") == "active"

    svc.set_instance_config(db, "account_state", "suspended")

    assert svc.get_instance_config(db, "account_state") == "suspended"


def test_ttl_expiry_refetches(db, monkeypatch):
    svc.set_instance_config(db, "account_state", "active")
    counting = _CountingSession(db)
    svc.get_instance_config(counting, "account_state")
    assert counting.queries == 1

    # Jump past the TTL without sleeping.
    import time as _time

    base = _time.monotonic()
    monkeypatch.setattr(
        _time, "monotonic", lambda: base + svc._CONFIG_TTL_SECONDS + 1, raising=True
    )

    svc.get_instance_config(counting, "account_state")
    assert counting.queries == 2, "TTL did not expire"


def test_unset_key_is_cached_but_default_is_per_caller(db):
    # The cache stores the resolved value (None), NOT the default — otherwise the
    # first caller's default would leak to every later caller.
    counting = _CountingSession(db)

    assert svc.get_instance_config(counting, "missing", default="a") == "a"
    assert svc.get_instance_config(counting, "missing", default="b") == "b"
    assert counting.queries == 1, "a missing key should still be cached"


def test_keys_are_isolated(db):
    svc.set_instance_config(db, "account_state", "trial")
    svc.set_instance_config(db, "plan_id", "starter")

    assert svc.get_instance_config(db, "account_state") == "trial"
    assert svc.get_instance_config(db, "plan_id") == "starter"

    svc.set_instance_config(db, "plan_id", "agency")

    assert svc.get_instance_config(db, "plan_id") == "agency"
    assert svc.get_instance_config(db, "account_state") == "trial", "invalidation was too broad"


def test_encrypted_values_round_trip_through_the_cache(db):
    svc.set_instance_config(db, "control_plane_token", "secret-tok", encrypt=True)

    assert svc.get_instance_config(db, "control_plane_token") == "secret-tok"
    # Cached value must be the DECRYPTED one, not ciphertext.
    assert svc.get_instance_config(db, "control_plane_token") == "secret-tok"
