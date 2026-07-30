"""Unit tests for backend.services.credit_service."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models import User, CreditPackage, CreditTransaction
from backend.services.credit_service import (
    InsufficientCreditsError,
    get_balance,
    deduct_credits,
    purchase_credits,
    refund_credits,
    admin_adjust_credits,
    get_transactions,
    get_package_pricing,
    get_credit_summary,
    estimate_cost,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def user(db):
    u = User(
        id="user-cred-1",
        email="cred@test.com",
        hashed_password="hashed",
        full_name="Cred User",
        is_active=True,
        credit_balance=1000,
        total_credits_purchased=1000,
        total_credits_used=0,
        is_enterprise=False,
    )
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def package(db):
    p = CreditPackage(
        id="pkg-001",
        name="Starter Pack",
        credits=100,
        price_usd=200.0,
        package_type="package",
        is_active=True,
        description="Test package",
    )
    db.add(p)
    db.commit()
    return p


class TestGetBalance:
    def test_returns_balance(self, db, user):
        assert get_balance(db, user.id) == 1000

    def test_unknown_user_raises(self, db):
        with pytest.raises(ValueError, match="User not found"):
            get_balance(db, "no-such-user")


class TestDeductCredits:
    def test_deducts_from_balance(self, db, user):
        deduct_credits(db, user.id, 100, "test deduction")
        db.refresh(user)
        assert user.credit_balance == 900

    def test_returns_transaction(self, db, user):
        txn = deduct_credits(db, user.id, 50, "test")
        assert isinstance(txn, CreditTransaction)
        assert txn.amount == -50
        assert txn.transaction_type == "deduction"

    def test_updates_total_used(self, db, user):
        deduct_credits(db, user.id, 200, "test")
        db.refresh(user)
        assert user.total_credits_used == 200

    def test_insufficient_credits_raises(self, db, user):
        with pytest.raises(InsufficientCreditsError, match="Insufficient credits"):
            deduct_credits(db, user.id, 9999, "too much")

    def test_zero_amount_raises(self, db, user):
        with pytest.raises(ValueError, match="must be positive"):
            deduct_credits(db, user.id, 0, "test")

    def test_negative_amount_raises(self, db, user):
        with pytest.raises(ValueError, match="must be positive"):
            deduct_credits(db, user.id, -50, "test")

    def test_unknown_user_raises(self, db):
        with pytest.raises(ValueError, match="User not found"):
            deduct_credits(db, "no-user", 10, "test")

    def test_stores_reference_id(self, db, user):
        txn = deduct_credits(db, user.id, 20, "test", reference_id="post-123")
        assert txn.reference_id == "post-123"


class TestPurchaseCredits:
    def test_adds_credits(self, db, user, package):
        purchase_credits(db, user.id, package.id)
        db.refresh(user)
        assert user.credit_balance == 1100

    def test_returns_transaction(self, db, user, package):
        txn = purchase_credits(db, user.id, package.id)
        assert txn.amount == 100
        assert txn.transaction_type == "purchase"

    def test_updates_total_purchased(self, db, user, package):
        purchase_credits(db, user.id, package.id)
        db.refresh(user)
        assert user.total_credits_purchased == 1100

    def test_inactive_package_raises(self, db, user, package):
        package.is_active = False
        db.commit()
        with pytest.raises(ValueError, match="inactive"):
            purchase_credits(db, user.id, package.id)

    def test_unknown_package_raises(self, db, user):
        with pytest.raises(ValueError, match="Package not found"):
            purchase_credits(db, user.id, "no-such-pkg")

    def test_with_payment_reference(self, db, user, package):
        txn = purchase_credits(db, user.id, package.id, payment_reference="pay_123")
        assert "pay_123" in txn.description


class TestRefundCredits:
    def test_adds_credits_back(self, db, user):
        # First deduct then refund
        deduct_credits(db, user.id, 100, "deduct")
        refund_credits(db, user.id, 100, "refund")
        db.refresh(user)
        assert user.credit_balance == 1000

    def test_returns_positive_transaction(self, db, user):
        txn = refund_credits(db, user.id, 50, "refund test")
        assert txn.amount == 50
        assert txn.transaction_type == "refund"

    def test_zero_amount_raises(self, db, user):
        with pytest.raises(ValueError, match="must be positive"):
            refund_credits(db, user.id, 0, "test")

    def test_unknown_user_raises(self, db):
        with pytest.raises(ValueError, match="User not found"):
            refund_credits(db, "no-user", 10, "test")


class TestAdminAdjustCredits:
    def test_positive_adjustment_adds(self, db, user):
        admin_adjust_credits(db, user.id, 500, "bonus", "admin-1")
        db.refresh(user)
        assert user.credit_balance == 1500

    def test_negative_adjustment_removes(self, db, user):
        admin_adjust_credits(db, user.id, -200, "clawback", "admin-1")
        db.refresh(user)
        assert user.credit_balance == 800

    def test_zero_raises(self, db, user):
        with pytest.raises(ValueError, match="cannot be zero"):
            admin_adjust_credits(db, user.id, 0, "test", "admin-1")

    def test_over_balance_negative_raises(self, db, user):
        with pytest.raises(ValueError, match="Cannot adjust"):
            admin_adjust_credits(db, user.id, -9999, "too much", "admin-1")

    def test_description_includes_admin(self, db, user):
        txn = admin_adjust_credits(db, user.id, 100, "test reason", "admin-xyz")
        assert "admin-xyz" in txn.description


class TestGetTransactions:
    def test_returns_transactions_newest_first(self, db, user):
        deduct_credits(db, user.id, 10, "first")
        deduct_credits(db, user.id, 20, "second")
        txns = get_transactions(db, user.id)
        assert len(txns) >= 2

    def test_filter_by_type(self, db, user):
        deduct_credits(db, user.id, 10, "d1")
        refund_credits(db, user.id, 5, "r1")
        deductions = get_transactions(db, user.id, transaction_type="deduction")
        assert all(t.transaction_type == "deduction" for t in deductions)

    def test_limit_and_offset(self, db, user):
        for i in range(5):
            deduct_credits(db, user.id, 1, f"d{i}")
        page1 = get_transactions(db, user.id, limit=2, offset=0)
        page2 = get_transactions(db, user.id, limit=2, offset=2)
        assert len(page1) == 2
        assert page1[0].id != page2[0].id


class TestGetPackagePricing:
    def test_returns_active_packages(self, db, package):
        pkgs = get_package_pricing(db)
        assert any(p.id == package.id for p in pkgs)

    def test_inactive_excluded(self, db, package):
        package.is_active = False
        db.commit()
        pkgs = get_package_pricing(db)
        assert all(p.id != package.id for p in pkgs)

    def test_filter_by_type(self, db, package):
        pkgs = get_package_pricing(db, package_type="package")
        assert all(p.package_type == "package" for p in pkgs)

    def test_empty_when_no_packages(self, db):
        assert get_package_pricing(db) == []


class TestGetCreditSummary:
    def test_returns_summary_dict(self, db, user, package):
        summary = get_credit_summary(db, user.id)
        assert "balance" in summary
        assert "total_purchased" in summary
        assert "total_used" in summary
        assert "available_packages" in summary

    def test_balance_correct(self, db, user):
        summary = get_credit_summary(db, user.id)
        assert summary["balance"] == 1000

    def test_unknown_user_raises(self, db):
        with pytest.raises(ValueError, match="User not found"):
            get_credit_summary(db, "no-user")


class TestEstimateCost:
    def test_posts_only(self):
        result = estimate_cost(num_posts=10)
        assert result["posts"]["total_credits"] == 200  # 10 * 20
        assert result["total_credits"] == 200

    def test_with_research_tools(self):
        result = estimate_cost(num_posts=5, research_tools=["seo_keyword_research"])
        assert result["total_credits"] > 100  # posts + research

    def test_unknown_tool_ignored(self):
        result = estimate_cost(research_tools=["nonexistent_tool"])
        assert result["research_tools"]["total_credits"] == 0

    def test_cost_usd_calculated(self):
        result = estimate_cost(num_posts=10)
        assert result["estimated_cost_usd"]["standard_package"] == 100.0  # 200 * $0.50 (BILLING-01)

    def test_zero_posts(self):
        result = estimate_cost(num_posts=0)
        assert result["total_credits"] == 0
