"""Stripe payment models."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


class StripeCustomer(Base):
    __tablename__ = "stripe_customers"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True, default=lambda: f"scus-{uuid.uuid4().hex[:12]}")
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    stripe_customer_id = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("backend.models.user.User", foreign_keys=[user_id])


class StripePayment(Base):
    __tablename__ = "stripe_payments"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True, default=lambda: f"spay-{uuid.uuid4().hex[:12]}")
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    stripe_session_id = Column(String, nullable=False, unique=True, index=True)
    stripe_payment_intent = Column(String, nullable=True, index=True)
    package_id = Column(String, ForeignKey("credit_packages.id"), nullable=True, index=True)
    amount_usd = Column(Float, nullable=True)
    credits = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending|completed|failed|expired
    credit_transaction_id = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON string for project_id etc
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("backend.models.user.User", foreign_keys=[user_id])
