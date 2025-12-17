"""Payment model for Stripe integration."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import relationship

from ..db.database import Base


def generate_uuid():
    """Generate a lowercase hex UUID."""
    return uuid.uuid4().hex


class Payment(Base):
    """
    Payment model for tracking Stripe payments.

    Attributes:
        payment_id: Unique payment identifier
        user_id: Foreign key to user
        project_id: Foreign key to project (NULL for recurring)
        stripe_payment_intent_id: Stripe PaymentIntent ID
        stripe_customer_id: Stripe Customer ID
        stripe_subscription_id: Stripe Subscription ID (for recurring)
        amount: Payment amount
        currency: Currency code (usd)
        status: Payment status (pending, succeeded, failed, refunded)
        package_tier: Package purchased
        is_recurring: Whether this is a subscription payment
        invoice_url: Stripe invoice URL
        invoice_pdf_path: Path to saved invoice PDF
        created_at: Payment creation timestamp
        paid_at: When payment succeeded
    """

    __tablename__ = "payments"

    payment_id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    project_id = Column(String, ForeignKey("projects.project_id"), nullable=True)

    # Stripe data
    stripe_payment_intent_id = Column(String, unique=True, nullable=True, index=True)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)

    # Payment details
    amount = Column(Float, nullable=False)
    currency = Column(String, default="usd")
    status = Column(String, default="pending")  # pending, succeeded, failed, refunded

    # Package info
    package_tier = Column(String, nullable=True)
    is_recurring = Column(Boolean, default=False)

    # Invoice
    invoice_url = Column(String, nullable=True)
    invoice_pdf_path = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="payments")
    project = relationship("Project", back_populates="payments")

    def __repr__(self):
        return (
            f"<Payment(payment_id={self.payment_id}, amount={self.amount}, status={self.status})>"
        )
