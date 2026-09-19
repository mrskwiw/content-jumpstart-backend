"""
Credit system models.

Includes:
- CreditTransaction: Records all credit movements (purchases, deductions, refunds)
- CreditPackage: Defines available credit packages and pricing
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    Integer,
    Float,
    Boolean,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class CreditTransaction(Base):
    """Credit transaction record"""

    __tablename__ = "credit_transactions"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # Positive = credit, Negative = debit
    transaction_type = Column(
        String, nullable=False
    )  # purchase, deduction, refund, admin_adjustment
    description = Column(Text)
    reference_id = Column(String, index=True)  # Reference to post_id, research_result_id, etc.
    reference_type = Column(String)  # post_generation, research_tool, purchase, refund
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("backend.models.user.User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<CreditTransaction {self.id} user={self.user_id} amount={self.amount}>"


class CreditPackage(Base):
    """Available credit packages"""

    __tablename__ = "credit_packages"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    credits = Column(Integer, nullable=False)
    price_usd = Column(Float, nullable=False)
    package_type = Column(
        String, default="package"
    )  # 'package' ($0.50/credit, subscription) or 'additional' ($1.00/credit, non-expiring top-up) — BILLING-01 locked rate
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<CreditPackage {self.name} {self.credits} credits ${self.price_usd}>"
