"""
Stripe payment service.

Handles all Stripe SDK calls: customer management, checkout sessions,
and payment fulfillment via webhooks.
"""

import json
import logging
import time
from typing import Optional

import stripe
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.stripe_payment import StripeCustomer, StripePayment
from backend.services import credit_service

logger = logging.getLogger(__name__)


def _get_stripe():
    """Get configured Stripe client. Logs mode on first call."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    if settings.STRIPE_SECRET_KEY.startswith("sk_test_"):
        logger.info("Stripe mode: TEST")
    elif settings.STRIPE_SECRET_KEY.startswith("sk_live_"):
        logger.info("Stripe mode: LIVE")
    return stripe


def get_or_create_stripe_customer(db: Session, user) -> str:
    """
    Get existing Stripe Customer ID for user, or create a new one.
    Returns stripe_customer_id string.
    """
    existing = db.query(StripeCustomer).filter(StripeCustomer.user_id == user.id).first()
    if existing:
        return existing.stripe_customer_id

    s = _get_stripe()
    customer = s.Customer.create(
        email=user.email,
        name=getattr(user, "full_name", None),
        metadata={"user_id": user.id},
    )

    sc = StripeCustomer(user_id=user.id, stripe_customer_id=customer.id)
    db.add(sc)
    db.commit()
    return customer.id


def create_checkout_session(
    db: Session,
    user,
    package,
    success_url: str,
    cancel_url: str,
    project_id: Optional[str] = None,
) -> dict:
    """
    Create a Stripe Checkout Session for a credit package purchase.
    Returns dict with checkout_url and session_id.
    """
    s = _get_stripe()
    stripe_customer_id = get_or_create_stripe_customer(db, user)

    amount_cents = int(float(package.price_usd) * 100)
    metadata = {"user_id": user.id, "package_id": package.id}
    if project_id:
        metadata["project_id"] = project_id

    session = s.checkout.Session.create(
        customer=stripe_customer_id,
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": package.name},
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=user.id,
        metadata=metadata,
        idempotency_key=f"checkout_{user.id}_{package.id}_{int(time.time() // 300)}",
    )

    payment = StripePayment(
        user_id=user.id,
        stripe_session_id=session.id,
        package_id=package.id,
        amount_usd=float(package.price_usd),
        credits=package.credits,
        status="pending",
        metadata_json=json.dumps(metadata),
    )
    db.add(payment)
    db.commit()

    return {"checkout_url": session.url, "session_id": session.id}


def fulfill_payment(db: Session, session_id: str) -> bool:
    """
    Idempotent payment fulfillment. Called by webhook on checkout.session.completed.
    Returns True if credits were added, False if already fulfilled.

    Bug #177: Stripe retries webhooks, and two duplicate deliveries can arrive
    concurrently. A plain status check is not atomic — both could read
    ``status == "pending"`` before either commits and double-grant credits. We
    take a row-level lock (``SELECT ... FOR UPDATE``) on the payment so duplicate
    deliveries serialize: the second one blocks until the first commits, then
    reads ``status == "completed"`` and short-circuits. On PostgreSQL (prod) this
    is real row locking; SQLite serializes writers regardless.
    """
    payment = (
        db.query(StripePayment)
        .filter(StripePayment.stripe_session_id == session_id)
        .with_for_update()
        .first()
    )

    if not payment:
        logger.warning(f"Webhook: StripePayment not found for session {session_id}")
        return False

    if payment.status == "completed":
        logger.info(f"Webhook: Payment {session_id} already completed (idempotency guard)")
        return False

    try:
        tx = credit_service.purchase_credits(
            db=db,
            user_id=payment.user_id,
            package_id=payment.package_id,
            payment_reference=session_id,
        )
        payment.status = "completed"
        payment.credit_transaction_id = str(tx.id) if tx else None
        db.commit()
        logger.info(f"Webhook: Fulfilled payment {session_id}, added {payment.credits} credits")
        return True
    except Exception as e:
        logger.error(f"Webhook: Failed to fulfill payment {session_id}: {e}")
        db.rollback()
        raise


def expire_payment(db: Session, session_id: str) -> None:
    """Mark a payment as expired (checkout.session.expired webhook)."""
    payment = db.query(StripePayment).filter(StripePayment.stripe_session_id == session_id).first()
    if payment and payment.status == "pending":
        payment.status = "expired"
        db.commit()


def create_billing_portal_session(db: Session, user, return_url: str) -> str:
    """
    Create a Stripe Customer Portal session for managing billing.
    Returns the portal URL to redirect the user to.
    """
    s = _get_stripe()
    stripe_customer_id = get_or_create_stripe_customer(db, user)
    session = s.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=return_url,
    )
    return session.url


def fail_payment(db: Session, payment_intent_id: str) -> None:
    """Mark a payment as failed (payment_intent.payment_failed webhook)."""
    payment = (
        db.query(StripePayment)
        .filter(StripePayment.stripe_payment_intent == payment_intent_id)
        .first()
    )
    if payment and payment.status == "pending":
        payment.status = "failed"
        db.commit()
