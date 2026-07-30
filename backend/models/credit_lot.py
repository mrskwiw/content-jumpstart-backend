"""Credit lots — per-grant credit tracking with expiry (S-01.4b).

A flat ``users.credit_balance`` integer cannot represent the locked billing rule
(BILLING-01): subscription allowance credits **roll over 30 days then expire**,
while purchased top-up credits **never expire**. Each grant is therefore its own
lot with a ``source`` and an ``expires_at`` (null = never), and spend is
**FEFO** — soonest-expiring first — so rolling-over allowance is used before it
lapses and permanent top-ups are consumed last.

``users.credit_balance`` remains as a cached sum of live (non-expired)
``remaining`` so the ~30 existing readers and the API contract are untouched
(S-01.4b-ii wires that maintenance into credit_service).
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from ..database import Base


def _uuid() -> str:
    import uuid

    return str(uuid.uuid4())


class CreditLot(Base):
    """One credit grant, drawn down over time (FEFO)."""

    __tablename__ = "credit_lots"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # allowance | topup | trial | refund | admin | migration
    source = Column(String(32), nullable=False)
    amount = Column(Integer, nullable=False)  # credits granted
    remaining = Column(Integer, nullable=False)  # credits left (>= 0)
    # null = never expires (top-ups); allowance = granted_at + 30d
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self) -> str:
        return (
            f"<CreditLot(id={self.id!r}, user_id={self.user_id!r}, "
            f"source={self.source!r}, remaining={self.remaining})>"
        )
