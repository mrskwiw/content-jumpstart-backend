"""FEFO credit-lot engine (S-01.4b-i).

Pure lot mechanics — grant, balance, first-expiring-first-out consumption, and an
expiry sweep — with no coupling to the existing credit_service mutators yet
(that integration is S-01.4b-ii). Kept standalone so the tricky ordering/expiry
logic is unit-tested in isolation before it touches the live money path.

Consumption order: soonest ``expires_at`` first, nulls (never-expire top-ups)
last, ties broken by ``created_at`` — so rolling-over allowance is spent before it
lapses and permanent credits are preserved. Expired lots are never spent.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import case
from sqlalchemy.orm import Session

from ..models.credit_lot import CreditLot


class InsufficientCreditsError(Exception):
    """Raised when live lots can't cover a requested consumption."""


def _now(now: datetime | None) -> datetime:
    return now if now is not None else datetime.utcnow()


def _is_live(lot: CreditLot, now: datetime) -> bool:
    return lot.remaining > 0 and (lot.expires_at is None or lot.expires_at > now)


def grant(
    db: Session,
    user_id: str,
    amount: int,
    source: str,
    expires_at: datetime | None = None,
) -> CreditLot:
    """Create a new credit lot. ``expires_at=None`` means never expires."""
    if amount <= 0:
        raise ValueError("grant amount must be positive")
    lot = CreditLot(
        id=str(uuid.uuid4()),
        user_id=user_id,
        source=source,
        amount=amount,
        remaining=amount,
        expires_at=expires_at,
    )
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return lot


def available_balance(db: Session, user_id: str, now: datetime | None = None) -> int:
    """Sum of ``remaining`` across live (non-expired) lots."""
    at = _now(now)
    lots = db.query(CreditLot).filter(CreditLot.user_id == user_id).all()
    return sum(lot.remaining for lot in lots if _is_live(lot, at))


def _fefo_lots(db: Session, user_id: str) -> list[CreditLot]:
    """Live-first ordering: soonest expiry first, nulls last, then oldest first.

    ``expires_at IS NULL`` sorts 0/1 so non-null (real expiries) come first and
    never-expire lots come last — portable across SQLite and Postgres (avoids
    relying on NULLS LAST).
    """
    null_last = case((CreditLot.expires_at.is_(None), 1), else_=0)
    return (
        db.query(CreditLot)
        .filter(CreditLot.user_id == user_id)
        .with_for_update()
        .order_by(null_last, CreditLot.expires_at, CreditLot.created_at)
        .all()
    )


def consume_fefo(db: Session, user_id: str, amount: int, now: datetime | None = None) -> None:
    """Draw ``amount`` credits from live lots, soonest-expiring first.

    Raises :class:`InsufficientCreditsError` (without mutating) if live lots
    can't cover it.
    """
    if amount <= 0:
        raise ValueError("consume amount must be positive")
    at = _now(now)
    lots = [lot for lot in _fefo_lots(db, user_id) if _is_live(lot, at)]

    if sum(lot.remaining for lot in lots) < amount:
        db.rollback()  # release the FOR UPDATE lock; no partial spend
        raise InsufficientCreditsError(
            f"insufficient credits: need {amount}, have {sum(lot.remaining for lot in lots)}"
        )

    outstanding = amount
    for lot in lots:
        if outstanding <= 0:
            break
        take = min(lot.remaining, outstanding)
        lot.remaining -= take
        outstanding -= take
    db.commit()


def expire_lots(db: Session, now: datetime | None = None) -> int:
    """Zero out ``remaining`` on lapsed lots so cached balances stay honest.

    Returns the number of lots swept. (FEFO already refuses to spend expired
    lots; this makes the persisted state match by reclaiming stranded remainders.)
    """
    at = _now(now)
    swept = 0
    lapsed = (
        db.query(CreditLot)
        .filter(
            CreditLot.expires_at.isnot(None),
            CreditLot.expires_at <= at,
            CreditLot.remaining > 0,
        )
        .with_for_update()
        .all()
    )
    for lot in lapsed:
        lot.remaining = 0
        swept += 1
    if swept:
        db.commit()
    return swept
