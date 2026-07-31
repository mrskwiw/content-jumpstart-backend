"""Session/token revocation store (GAP-AUTH-03).

A single table backs two revocation mechanisms, distinguished by ``kind``:

* ``kind="jti"``  — ``subject`` is a token's ``jti``; that one access/refresh token
  is dead. Used for admin "kill this compromised token" and self-service logout.
* ``kind="user"`` — ``subject`` is a ``user_id`` and ``revoked_at`` is a cutoff; every
  token for that user issued (``iat``) before the cutoff is dead. Used for logout-all
  and admin "kill all of this user's sessions" — decoupled from password change.

``(kind, subject)`` is unique so the per-user cutoff row is upserted (advanced, not
duplicated). ``expires_at`` lets a sweeper purge rows once no unexpired token could
still match them.
"""

import uuid

from sqlalchemy import Column, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from backend.database import Base


class RevokedToken(Base):
    """One revocation record — either a single ``jti`` or a per-user cutoff."""

    __tablename__ = "revoked_tokens"

    id = Column(String, primary_key=True, default=lambda: f"rt-{uuid.uuid4().hex[:12]}")
    # "jti" (single token) | "user" (per-user cutoff over iat)
    kind = Column(String, nullable=False)
    # jti value (kind="jti") or user_id (kind="user")
    subject = Column(String, nullable=False, index=True)
    # Owning user — for audit/filtering; equals subject when kind="user".
    user_id = Column(String, nullable=True, index=True)
    # "access" | "refresh" | None — informational for kind="jti".
    token_type = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    # For kind="user" this is the cutoff compared against a token's iat.
    revoked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # When this row can be purged (no unexpired token could match after this).
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("kind", "subject", name="uq_revoked_tokens_kind_subject"),
        Index("idx_revoked_tokens_kind_subject", "kind", "subject"),
    )
