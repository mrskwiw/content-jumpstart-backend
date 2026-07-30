"""Instance-global configuration — a singleton key/value store (NOT per-user).

Holds values that describe the *instance as a whole* — plan tier, account state,
CORS origins, canonical domain — written at runtime by the control plane so they
take effect without a redeploy (S-01.4).

Deliberately **not tied to any user row.** Instance config must survive normal
admin churn (create / promote / demote / soft-delete), so keying it to a mutable
"owner" superuser would make it brittle: ownership could shift and reads could
return stale/mixed values (the flaw the S-01.4a adversarial review caught). A
single-row-per-key table has no owner concept, so writes and reads always agree.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text

from ..database import Base


class InstanceConfig(Base):
    """One row per instance-global config key (singleton table)."""

    __tablename__ = "instance_config"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)  # encrypted iff is_encrypted
    is_encrypted = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<InstanceConfig(key='{self.key}')>"
