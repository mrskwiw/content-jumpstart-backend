"""
Stripe payment router.

Endpoints:
  POST   /api/stripe/checkout              — create checkout session
  GET    /api/stripe/payment-status/{id}   — poll payment status
  POST   /api/stripe/webhook               — Stripe webhook (no auth, sig verified)
"""

import json
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.models import User
from backend.models.stripe_payment import StripePayment
from backend.schemas.stripe_schemas import (
    BillingPortalRequest,
    BillingPortalResponse,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    PaymentHistoryItem,
    PaymentStatusResponse,
)
from backend.services import stripe_service
from backend.utils.http_rate_limiter import standard_limiter

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/checkout", response_model=CheckoutSessionResponse)
@standard_limiter.limit("20/hour")
async def create_checkout_session(
    request: Request,
    body: CheckoutSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout Session for a credit package."""
    from backend.models.credit import CreditPackage
    from backend.services import audit_service

    # Refund/Terms consent is enforced HERE (not just via the client checkbox,
    # which is trivially bypassable) so no purchase can proceed without it.
    if not body.accepted_terms:
        raise HTTPException(
            status_code=400,
            detail="You must accept the Terms of Service and Refund Policy to purchase.",
        )

    package = (
        db.query(CreditPackage)
        .filter(
            CreditPackage.id == body.package_id,
            CreditPackage.is_active.is_(True),
        )
        .first()
    )
    if not package:
        raise HTTPException(status_code=404, detail="Credit package not found")

    # Persist the accepted-terms consent (immutable audit trail) BEFORE creating
    # the session, so acceptance is provable independent of the client. This is
    # FAIL-CLOSED (raise_on_error): if we cannot record consent, the purchase does
    # not proceed — otherwise the audit trail could silently disappear.
    try:
        audit_service.log_action(
            db,
            user_id=current_user.id,
            user_email=getattr(current_user, "email", None),
            action="Accepted Terms & Refund Policy at checkout",
            action_type="system",
            resource_type="payment",
            resource_id=body.package_id,
            details=f"Consent version: {body.consent_version or 'unspecified'}",
            ip_address=audit_service.get_client_ip(request),
            metadata={
                "accepted_terms": True,
                "consent_version": body.consent_version,
                "package_id": body.package_id,
            },
            raise_on_error=True,
        )
    except Exception as e:
        logger.error(f"Failed to record checkout consent: {e}")
        raise HTTPException(
            status_code=503,
            detail="Could not record your consent; purchase not started. Please try again.",
        )

    try:
        result = stripe_service.create_checkout_session(
            db=db,
            user=current_user,
            package=package,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            project_id=body.project_id,
        )
        return CheckoutSessionResponse(**result)
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise HTTPException(status_code=502, detail="Payment service unavailable")


@router.get("/payment-status/{session_id}", response_model=PaymentStatusResponse)
@standard_limiter.limit("60/hour")
async def get_payment_status(
    request: Request,
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Poll payment status for a checkout session. Used by success page."""
    payment = (
        db.query(StripePayment)
        .filter(
            StripePayment.stripe_session_id == session_id,
            StripePayment.user_id == current_user.id,  # IDOR protection
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment session not found")

    project_id = None
    if payment.metadata_json:
        try:
            project_id = json.loads(payment.metadata_json).get("project_id")
        except Exception:
            pass

    return PaymentStatusResponse(
        session_id=session_id,
        status=payment.status,
        credits=payment.credits,
        project_id=project_id,
    )


@router.post("/webhook", status_code=200)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe webhook endpoint. Verifies signature and processes events.
    IMPORTANT: Must receive raw bytes — do NOT use a Pydantic body parameter.
    """
    body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("STRIPE_WEBHOOK_SECRET not configured — skipping signature verification")
        try:
            event = json.loads(body)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload")
    else:
        try:
            event = stripe.Webhook.construct_event(body, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        except stripe.error.SignatureVerificationError:
            logger.warning("Stripe webhook signature verification failed")
            raise HTTPException(status_code=400, detail="Invalid signature")
        except Exception as e:
            logger.error(f"Webhook payload error: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event.get("type", "")
    event_data = event.get("data", {}).get("object", {})

    logger.info(f"Stripe webhook received: {event_type}")

    if event_type == "checkout.session.completed":
        session_id = event_data.get("id")
        if session_id:
            try:
                stripe_service.fulfill_payment(db, session_id)
            except Exception as e:
                logger.error(f"Failed to fulfill payment for session {session_id}: {e}")
                raise HTTPException(status_code=500, detail="Fulfillment failed")

    elif event_type == "checkout.session.expired":
        session_id = event_data.get("id")
        if session_id:
            stripe_service.expire_payment(db, session_id)

    elif event_type == "payment_intent.payment_failed":
        pi_id = event_data.get("id")
        if pi_id:
            stripe_service.fail_payment(db, pi_id)

    return {"received": True}


@router.get("/payments", response_model=list[PaymentHistoryItem])
async def list_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return Stripe payment history for the current user."""
    payments = (
        db.query(StripePayment)
        .filter(StripePayment.user_id == current_user.id)
        .order_by(StripePayment.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        PaymentHistoryItem(
            id=p.id,
            session_id=p.stripe_session_id,
            amount_usd=p.amount_usd,
            credits=p.credits,
            status=p.status,
            package_id=p.package_id,
            created_at=p.created_at,
        )
        for p in payments
    ]


@router.post("/portal", response_model=BillingPortalResponse)
@standard_limiter.limit("10/hour")
async def create_billing_portal(
    request: Request,
    body: BillingPortalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Customer Portal session and return the URL."""
    try:
        portal_url = stripe_service.create_billing_portal_session(
            db=db,
            user=current_user,
            return_url=body.return_url,
        )
        return BillingPortalResponse(portal_url=portal_url)
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating billing portal: {e}")
        raise HTTPException(status_code=502, detail="Payment service unavailable")
