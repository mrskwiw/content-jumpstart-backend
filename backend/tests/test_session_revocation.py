"""GAP-AUTH-03 — session/token revocation store (service-level unit tests)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.models  # noqa: F401 — register all tables on Base.metadata
from backend.database import Base
from backend.models.revoked_token import RevokedToken
from backend.services import session_revocation_service as svc

_T = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with factory() as session:
        yield session


# ── per-token (jti) ─────────────────────────────────────────────────────────────


def test_revoke_jti_makes_token_revoked(db):
    assert svc.is_token_revoked(db, {"jti": "j1", "sub": "u1"}) is False
    svc.revoke_jti(db, "j1", user_id="u1", token_type="access")
    assert svc.is_token_revoked(db, {"jti": "j1", "sub": "u1"}) is True
    # A different token for the same user is unaffected (targeted, not whole-user).
    assert svc.is_token_revoked(db, {"jti": "j2", "sub": "u1"}) is False


def test_revoke_jti_is_idempotent(db):
    svc.revoke_jti(db, "j1")
    svc.revoke_jti(db, "j1")
    assert db.query(RevokedToken).filter_by(kind="jti", subject="j1").count() == 1


# ── per-user cutoff ─────────────────────────────────────────────────────────────


def test_user_cutoff_revokes_tokens_issued_before(db):
    svc.revoke_user_sessions(db, "u1", cutoff=_T)
    before = {"sub": "u1", "iat": (_T - timedelta(seconds=10)).timestamp()}
    after = {"sub": "u1", "iat": (_T + timedelta(seconds=10)).timestamp()}
    assert svc.is_token_revoked(db, before) is True  # pre-cutoff → dead
    assert svc.is_token_revoked(db, after) is False  # post-cutoff (re-login) → alive
    # Other users untouched.
    assert svc.is_token_revoked(db, {"sub": "u2", "iat": 0}) is False


def test_user_cutoff_missing_iat_is_failsafe(db):
    svc.revoke_user_sessions(db, "u1", cutoff=_T)
    # A legacy token without iat can't prove it postdates the cutoff → revoked.
    assert svc.is_token_revoked(db, {"sub": "u1"}) is True


def test_user_cutoff_only_advances(db):
    svc.revoke_user_sessions(db, "u1", cutoff=_T)
    # A later call with an EARLIER cutoff must not weaken the revocation.
    svc.revoke_user_sessions(db, "u1", cutoff=_T - timedelta(days=1))
    row = db.query(RevokedToken).filter_by(kind="user", subject="u1").one()
    assert svc._as_utc(row.revoked_at) == _T
    # And there is still exactly one cutoff row (upsert, not duplicate).
    assert db.query(RevokedToken).filter_by(kind="user", subject="u1").count() == 1


def test_user_cutoff_advances_forward(db):
    svc.revoke_user_sessions(db, "u1", cutoff=_T)
    later = _T + timedelta(hours=1)
    svc.revoke_user_sessions(db, "u1", cutoff=later)
    row = db.query(RevokedToken).filter_by(kind="user", subject="u1").one()
    assert svc._as_utc(row.revoked_at) == later


def test_no_revocation_returns_false(db):
    assert svc.is_token_revoked(db, {"sub": "u1", "jti": "j1", "iat": _T.timestamp()}) is False


def test_is_token_revoked_no_sub(db):
    assert svc.is_token_revoked(db, {"iat": 123}) is False


# ── purge ───────────────────────────────────────────────────────────────────────


def test_purge_expired_removes_only_past_rows(db):
    svc.revoke_jti(db, "old", expires_at=_T - timedelta(days=1))
    svc.revoke_jti(db, "future", expires_at=_T + timedelta(days=1))
    removed = svc.purge_expired(db, now=_T)
    assert removed == 1
    assert svc.is_token_revoked(db, {"jti": "old", "sub": "u"}) is False
    assert svc.is_token_revoked(db, {"jti": "future", "sub": "u"}) is True
