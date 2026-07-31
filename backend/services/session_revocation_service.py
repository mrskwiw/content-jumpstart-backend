"""Session/token revocation store operations (GAP-AUTH-03).

Thin, transaction-agnostic helpers over the ``revoked_tokens`` table (see
``backend/models/revoked_token.py``). Two mechanisms:

* per-token: :func:`revoke_jti` blacklists one ``jti``.
* per-user:  :func:`revoke_user_sessions` writes/advances a cutoff so every token
  the user holds that was issued before the cutoff is rejected.

:func:`is_token_revoked` is the read side used by the auth dependency + ``/refresh``.
It is deliberately fail-safe: a token that cannot prove it postdates a user cutoff
(no ``iat``) is treated as revoked.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from sqlalchemy import delete
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.revoked_token import RevokedToken

KIND_JTI = "jti"
KIND_USER = "user"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _max_token_lifetime() -> timedelta:
    """Longest a token can live — used to set purge horizons for cutoff rows."""
    return timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


def revoke_jti(
    db: Session,
    jti: str,
    *,
    user_id: Optional[str] = None,
    token_type: Optional[str] = None,
    expires_at: Optional[datetime] = None,
    reason: Optional[str] = None,
    commit: bool = True,
) -> None:
    """Blacklist a single token by its ``jti`` (idempotent).

    ``expires_at`` should be the token's own expiry so the row can be purged once the
    token would have expired anyway; it defaults to one max token lifetime out.
    """
    existing = (
        db.query(RevokedToken)
        .filter(RevokedToken.kind == KIND_JTI, RevokedToken.subject == jti)
        .first()
    )
    if existing is not None:
        return  # already revoked — nothing to do
    row = RevokedToken(
        kind=KIND_JTI,
        subject=jti,
        user_id=user_id,
        token_type=token_type,
        reason=reason,
        revoked_at=_now(),
        expires_at=expires_at or (_now() + _max_token_lifetime()),
    )
    db.add(row)
    if commit:
        db.commit()


def revoke_user_sessions(
    db: Session,
    user_id: str,
    *,
    reason: Optional[str] = None,
    cutoff: Optional[datetime] = None,
    commit: bool = True,
) -> None:
    """Revoke all of a user's sessions issued before ``cutoff`` (default now).

    Upserts the single per-user cutoff row and only ever advances it forward, so a
    later revoke never weakens an earlier one.
    """
    cutoff = cutoff or _now()
    row = (
        db.query(RevokedToken)
        .filter(RevokedToken.kind == KIND_USER, RevokedToken.subject == user_id)
        .first()
    )
    horizon = cutoff + _max_token_lifetime()
    if row is None:
        db.add(
            RevokedToken(
                kind=KIND_USER,
                subject=user_id,
                user_id=user_id,
                reason=reason,
                revoked_at=cutoff,
                expires_at=horizon,
            )
        )
    else:
        # Only advance the cutoff — never move it backwards.
        if _as_utc(row.revoked_at) < cutoff:
            row.revoked_at = cutoff
            row.expires_at = horizon
            row.reason = reason
    if commit:
        db.commit()


def _as_utc(value: datetime) -> datetime:
    """Normalize a possibly-naive DB datetime to timezone-aware UTC for comparison."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def is_token_revoked(db: Session, payload: Mapping[str, Any]) -> bool:
    """Whether a decoded token payload has been revoked.

    True if the token's ``jti`` is blacklisted, OR a per-user cutoff exists for the
    token's ``sub`` and the token was issued before it (or carries no ``iat`` — a
    legacy token can't prove it postdates the cutoff, so it is rejected fail-safe).
    """
    jti = payload.get("jti")
    if jti and _jti_revoked(db, jti):
        return True

    sub = payload.get("sub")
    if not sub:
        return False
    cutoff_row = (
        db.query(RevokedToken)
        .filter(RevokedToken.kind == KIND_USER, RevokedToken.subject == sub)
        .first()
    )
    if cutoff_row is None:
        return False
    iat = payload.get("iat")
    if iat is None:
        return True  # fail-safe: cannot prove the token postdates the cutoff
    # JWT ``iat`` has whole-second granularity, so compare on floored seconds. Use
    # ``<=`` so EVERY token already issued at cutoff time dies (a "revoke all" must
    # leave nothing behind); a re-login lands in a later second and survives.
    return int(iat) <= int(_as_utc(cutoff_row.revoked_at).timestamp())


def _jti_revoked(db: Session, jti: str) -> bool:
    return (
        db.query(RevokedToken)
        .filter(RevokedToken.kind == KIND_JTI, RevokedToken.subject == jti)
        .first()
        is not None
    )


def purge_expired(db: Session, *, now: Optional[datetime] = None, commit: bool = True) -> int:
    """Delete revocation rows whose ``expires_at`` has passed; return the row count."""
    now = now or _now()
    result = db.execute(
        delete(RevokedToken).where(
            RevokedToken.expires_at.is_not(None), RevokedToken.expires_at < now
        )
    )
    if commit:
        db.commit()
    return int(result.rowcount or 0)
