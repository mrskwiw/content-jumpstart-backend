"""
Regression tests for Bug #177: Stripe webhook fulfillment must not double-grant
credits when the same `checkout.session.completed` event is delivered more than
once (Stripe retries on network failure / manual redelivery).

`fulfill_payment` guards on `payment.status == "completed"` and now takes a
row-level lock (`SELECT ... FOR UPDATE`) so concurrent duplicate deliveries
serialize on the payment row instead of both passing the pending check.
"""

import pytest

from backend.services import stripe_service
from backend.models import User
from backend.models.credit import CreditPackage
from backend.models.stripe_payment import StripePayment


@pytest.fixture
def buyer(db_session):
    user = User(
        id="user-stripe-177",
        email="buyer177@example.com",
        hashed_password="x",
        full_name="Buyer",
        is_active=True,
        is_superuser=False,
        credit_balance=0,
        total_credits_purchased=0,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def package(db_session):
    pkg = CreditPackage(
        id="pkg-100",
        name="Starter 100",
        credits=100,
        price_usd=200.0,
        is_active=True,
    )
    db_session.add(pkg)
    db_session.commit()
    return pkg


@pytest.fixture
def pending_payment(db_session, buyer, package):
    payment = StripePayment(
        id="spay-177",
        user_id=buyer.id,
        stripe_session_id="cs_test_177",
        package_id=package.id,
        amount_usd=200.0,
        credits=100,
        status="pending",
    )
    db_session.add(payment)
    db_session.commit()
    return payment


class TestFulfillPaymentIdempotency:
    def test_first_fulfillment_grants_credits(self, db_session, buyer, pending_payment):
        granted = stripe_service.fulfill_payment(db_session, "cs_test_177")

        assert granted is True
        db_session.refresh(buyer)
        assert buyer.credit_balance == 100
        db_session.refresh(pending_payment)
        assert pending_payment.status == "completed"

    def test_duplicate_delivery_does_not_double_grant(self, db_session, buyer, pending_payment):
        # First delivery fulfills.
        assert stripe_service.fulfill_payment(db_session, "cs_test_177") is True
        # Simulate Stripe re-delivering the same event.
        second = stripe_service.fulfill_payment(db_session, "cs_test_177")

        assert second is False
        db_session.refresh(buyer)
        assert buyer.credit_balance == 100  # not 200

    def test_unknown_session_returns_false(self, db_session):
        assert stripe_service.fulfill_payment(db_session, "cs_does_not_exist") is False

    def test_credit_grant_and_status_flip_are_atomic(self, db_session, buyer, pending_payment):
        """The grant and the status flip must land in one transaction. If the
        commit never happens (simulated by a rollback), NEITHER the credits nor
        the completed status may persist — otherwise the FOR UPDATE lock could be
        released with credits granted but status still pending (Bug #177)."""
        from backend.services import credit_service

        # Mirror fulfill_payment's inner steps but roll back instead of commit.
        tx = credit_service.purchase_credits(
            db_session,
            user_id=buyer.id,
            package_id=pending_payment.package_id,
            payment_reference="cs_test_177",
            commit=False,
        )
        assert tx is not None
        pending_payment.status = "completed"

        db_session.rollback()

        db_session.refresh(buyer)
        db_session.refresh(pending_payment)
        assert buyer.credit_balance == 0  # grant did not leak out
        assert pending_payment.status == "pending"  # status did not leak out
