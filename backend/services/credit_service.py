"""
Credit service for managing user credits, transactions, and packages.

Handles:
- Credit deductions (post generation, research tools)
- Credit purchases (packages)
- Credit refunds (failed operations)
- Transaction history
- Package pricing
- Admin adjustments
"""

import uuid
from typing import Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.models import CreditLot, CreditPackage, CreditTransaction, User
from backend.services import credit_lots


class InsufficientCreditsError(Exception):
    """Raised when user doesn't have enough credits for an operation."""

    pass


# ── Credit lots (S-01.4b-ii) ──────────────────────────────────────────────────
# Credits are held as FEFO lots (backend/services/credit_lots.py): subscription
# allowance rolls over 30 days then expires; top-ups never expire. `credit_balance`
# on User is kept as a CACHED SUM of live lot remaining so the ~30 existing readers
# and the API contract are unchanged. All mutators below run under the User row
# FOR UPDATE lock (the invariant consume_fefo requires — Decision #201).


def _has_lots(db: Session, user_id: str) -> bool:
    return db.query(CreditLot.id).filter(CreditLot.user_id == user_id).first() is not None


def _ensure_lots_backfilled(db: Session, user: User) -> None:
    """Lazily migrate a legacy flat balance into a single non-expiring lot.

    Existing users have a ``credit_balance`` but no lots. On the first mutation we
    seed one ``migration`` lot equal to that balance, so nothing is lost and there
    is no separate migration run to coordinate. Idempotent: only fires when the
    user has a positive balance and zero lots.
    """
    if user.credit_balance and user.credit_balance > 0 and not _has_lots(db, user.id):
        credit_lots.grant(db, user.id, user.credit_balance, source="migration", expires_at=None)


def _sync_cached_balance(db: Session, user: User) -> None:
    """Refresh the cached ``credit_balance`` field to the live lot sum."""
    user.credit_balance = credit_lots.available_balance(db, user.id)


def live_balance(db: Session, user_id: str) -> int:
    """Accurate spendable balance from live lots.

    Reads must NOT trust the cached ``credit_balance`` column alone: it is only
    refreshed on writes + the scheduled expire sweep, so an idle user whose
    allowance lot expired would otherwise report an overstated, unspendable
    balance. Once lots exist, the live lot sum is truth (expired excluded);
    legacy users with a flat balance but no lots yet fall back to the column
    until their first mutation migrates it.
    """
    if not _has_lots(db, user_id):
        user = db.query(User).filter(User.id == user_id).first()
        return user.credit_balance if user else 0
    return credit_lots.available_balance(db, user_id)


def get_balance(db: Session, user_id: str) -> int:
    """
    Get user's current credit balance.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Current credit balance

    Raises:
        ValueError: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User not found: {user_id}")

    # Derive from live lots so expired credits are never reported as spendable
    # (the cached column can be stale for an idle user — S-01.4b-ii review).
    return live_balance(db, user_id)


def deduct_credits(
    db: Session,
    user_id: str,
    amount: int,
    description: str,
    reference_id: Optional[str] = None,
    reference_type: Optional[str] = None,
) -> CreditTransaction:
    """
    Deduct credits from user's balance (atomic operation).

    Args:
        db: Database session
        user_id: User ID
        amount: Number of credits to deduct (positive number)
        description: Human-readable description
        reference_id: Optional reference to post_id, research_result_id, etc.
        reference_type: Optional type (post_generation, research_tool)

    Returns:
        Created transaction record

    Raises:
        InsufficientCreditsError: If user doesn't have enough credits
        ValueError: If user not found or amount invalid
    """
    if amount <= 0:
        raise ValueError("Deduction amount must be positive")

    # Get user with row-level lock — serializes all credit ops for this user, so
    # consume_fefo runs safely without its own lot lock (Decision #201).
    user = db.query(User).filter(User.id == user_id).with_for_update().first()
    if not user:
        raise ValueError(f"User not found: {user_id}")

    _ensure_lots_backfilled(db, user)

    # Spend from lots, FEFO. consume_fefo raises before mutating on insufficient,
    # so no partial spend; translate to this module's error for caller contract.
    try:
        credit_lots.consume_fefo(db, user_id, amount)
    except credit_lots.InsufficientCreditsError:
        raise InsufficientCreditsError(
            f"Insufficient credits. Required: {amount}, "
            f"Available: {credit_lots.available_balance(db, user_id)}"
        )

    _sync_cached_balance(db, user)
    user.total_credits_used += amount

    # Create transaction record (negative amount for deduction)
    transaction = CreditTransaction(
        id=str(uuid.uuid4()),
        user_id=user_id,
        amount=-amount,  # Negative for deduction
        transaction_type="deduction",
        description=description,
        reference_id=reference_id,
        reference_type=reference_type,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction


def purchase_credits(
    db: Session,
    user_id: str,
    package_id: str,
    payment_reference: Optional[str] = None,
    commit: bool = True,
) -> CreditTransaction:
    """
    Purchase credits from a package.

    Args:
        db: Database session
        user_id: User ID
        package_id: Credit package ID
        payment_reference: Optional payment/invoice reference
        commit: When True (default) the credit grant is committed here. Pass False
            when the caller needs the grant to be part of a larger atomic
            transaction — e.g. the Stripe webhook, which must flip
            ``StripePayment.status`` to "completed" in the SAME commit while
            holding a ``FOR UPDATE`` lock, so a concurrent duplicate delivery
            cannot commit early, release the lock, and double-grant (Bug #177).
            With ``commit=False`` the rows are flushed but not committed, so the
            caller is responsible for committing (or rolling back).

    Returns:
        Created transaction record

    Raises:
        ValueError: If user or package not found, or package inactive
    """
    # Get user
    user = db.query(User).filter(User.id == user_id).with_for_update().first()
    if not user:
        raise ValueError(f"User not found: {user_id}")

    # Get package
    package = db.query(CreditPackage).filter(CreditPackage.id == package_id).first()
    if not package:
        raise ValueError(f"Package not found: {package_id}")

    if not package.is_active:
        raise ValueError(f"Package is inactive: {package.name}")

    # Add credits as a non-expiring top-up lot; balance = live lot sum.
    _ensure_lots_backfilled(db, user)
    credit_lots.grant(db, user_id, package.credits, source="topup", expires_at=None)
    _sync_cached_balance(db, user)
    user.total_credits_purchased += package.credits

    # Create transaction record (positive amount for purchase)
    description = f"Purchased {package.name} ({package.credits} credits)"
    if payment_reference:
        description += f" - Payment: {payment_reference}"

    transaction = CreditTransaction(
        id=str(uuid.uuid4()),
        user_id=user_id,
        amount=package.credits,  # Positive for purchase
        transaction_type="purchase",
        description=description,
        reference_id=package_id,
        reference_type="purchase",
    )

    db.add(transaction)
    if commit:
        db.commit()
        db.refresh(transaction)
    else:
        # Persist within the caller's transaction (surfaces integrity errors now)
        # without ending it, so the caller can commit atomically with its own work.
        db.flush()

    return transaction


def refund_credits(
    db: Session,
    user_id: str,
    amount: int,
    description: str,
    reference_id: Optional[str] = None,
    reference_type: Optional[str] = None,
) -> CreditTransaction:
    """
    Refund credits to user (e.g., for failed operations).

    Args:
        db: Database session
        user_id: User ID
        amount: Number of credits to refund (positive number)
        description: Human-readable description
        reference_id: Optional reference to failed operation
        reference_type: Optional type (post_generation, research_tool)

    Returns:
        Created transaction record

    Raises:
        ValueError: If user not found or amount invalid
    """
    if amount <= 0:
        raise ValueError("Refund amount must be positive")

    # Get user
    user = db.query(User).filter(User.id == user_id).with_for_update().first()
    if not user:
        raise ValueError(f"User not found: {user_id}")

    # Add credits back as a non-expiring refund lot; balance = live lot sum.
    _ensure_lots_backfilled(db, user)
    credit_lots.grant(db, user_id, amount, source="refund", expires_at=None)
    _sync_cached_balance(db, user)
    user.total_credits_used -= amount  # Reverse the usage

    # Create transaction record (positive amount for refund)
    transaction = CreditTransaction(
        id=str(uuid.uuid4()),
        user_id=user_id,
        amount=amount,  # Positive for refund
        transaction_type="refund",
        description=description,
        reference_id=reference_id,
        reference_type=reference_type,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction


def admin_adjust_credits(
    db: Session,
    user_id: str,
    amount: int,
    description: str,
    admin_user_id: str,
) -> CreditTransaction:
    """
    Admin-only credit adjustment (positive or negative).

    Args:
        db: Database session
        user_id: Target user ID
        amount: Credits to add (positive) or remove (negative)
        description: Human-readable reason
        admin_user_id: Admin user making the adjustment

    Returns:
        Created transaction record

    Raises:
        ValueError: If user not found or insufficient credits for negative adjustment
    """
    if amount == 0:
        raise ValueError("Adjustment amount cannot be zero")

    # Get user with row-level lock
    user = db.query(User).filter(User.id == user_id).with_for_update().first()
    if not user:
        raise ValueError(f"User not found: {user_id}")

    # Positive → grant an admin lot (non-expiring); negative → spend FEFO.
    _ensure_lots_backfilled(db, user)
    if amount > 0:
        credit_lots.grant(db, user_id, amount, source="admin", expires_at=None)
    else:
        try:
            credit_lots.consume_fefo(db, user_id, abs(amount))
        except credit_lots.InsufficientCreditsError:
            raise ValueError(
                f"Cannot adjust by {amount}. User balance: "
                f"{credit_lots.available_balance(db, user_id)}"
            )
        user.total_credits_used += abs(amount)

    _sync_cached_balance(db, user)

    # Create transaction record
    full_description = f"Admin adjustment by {admin_user_id}: {description}"

    transaction = CreditTransaction(
        id=str(uuid.uuid4()),
        user_id=user_id,
        amount=amount,
        transaction_type="admin_adjustment",
        description=full_description,
        reference_id=admin_user_id,
        reference_type="admin_adjustment",
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction


def get_transactions(
    db: Session,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    transaction_type: Optional[str] = None,
) -> List[CreditTransaction]:
    """
    Get user's transaction history.

    Args:
        db: Database session
        user_id: User ID
        limit: Maximum number of transactions to return
        offset: Pagination offset
        transaction_type: Optional filter (purchase, deduction, refund, admin_adjustment)

    Returns:
        List of transactions, newest first
    """
    query = db.query(CreditTransaction).filter(CreditTransaction.user_id == user_id)

    if transaction_type:
        query = query.filter(CreditTransaction.transaction_type == transaction_type)

    transactions = (
        query.order_by(desc(CreditTransaction.created_at)).limit(limit).offset(offset).all()
    )

    return transactions


def get_package_pricing(db: Session, package_type: Optional[str] = None) -> List[CreditPackage]:
    """
    Get available credit packages.

    Args:
        db: Database session
        package_type: Optional filter ('package' or 'additional')

    Returns:
        List of active packages, sorted by credits ascending
    """
    query = db.query(CreditPackage).filter(CreditPackage.is_active.is_(True))

    if package_type:
        query = query.filter(CreditPackage.package_type == package_type)

    packages = query.order_by(CreditPackage.credits).all()

    return packages


def get_credit_summary(db: Session, user_id: str) -> Dict:
    """
    Get comprehensive credit summary for a user.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Dictionary with balance, usage, and pricing info

    Raises:
        ValueError: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User not found: {user_id}")

    # Get transaction counts
    total_transactions = (
        db.query(CreditTransaction).filter(CreditTransaction.user_id == user_id).count()
    )

    recent_transactions = get_transactions(db, user_id, limit=10)

    # Get available packages
    standard_packages = get_package_pricing(db, package_type="package")
    additional_packages = get_package_pricing(db, package_type="additional")

    summary = {
        "balance": live_balance(db, user_id),
        "total_purchased": user.total_credits_purchased,
        "total_used": user.total_credits_used,
        "is_enterprise": user.is_enterprise,
        "custom_credit_rate": user.custom_credit_rate,
        "enterprise_notes": user.enterprise_notes,
        "total_transactions": total_transactions,
        "recent_transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "type": t.transaction_type,
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in recent_transactions
        ],
        "available_packages": {
            "standard": [
                {
                    "id": p.id,
                    "name": p.name,
                    "credits": p.credits,
                    "price_usd": p.price_usd,
                    "rate_per_credit": p.price_usd / p.credits,
                    "description": p.description,
                }
                for p in standard_packages
            ],
            "additional": [
                {
                    "id": p.id,
                    "name": p.name,
                    "credits": p.credits,
                    "price_usd": p.price_usd,
                    "rate_per_credit": p.price_usd / p.credits,
                    "description": p.description,
                }
                for p in additional_packages
            ],
        },
    }

    return summary


def estimate_cost(
    num_posts: int = 0,
    research_tools: Optional[List[str]] = None,
) -> Dict:
    """
    Estimate credit cost for a project.

    Args:
        num_posts: Number of blog posts (20 credits each)
        research_tools: List of research tool names

    Returns:
        Dictionary with breakdown and total credits

    Note:
        Research tool costs are defined in backend/pricing/credit_pricing.py
    """
    from backend.pricing.credit_pricing import RESEARCH_TOOL_COSTS

    # Blog posts: 20 credits each
    post_credits = num_posts * 20

    # Research tools
    tool_credits = 0
    tool_breakdown = []

    if research_tools:
        for tool_name in research_tools:
            cost = RESEARCH_TOOL_COSTS.get(tool_name, 0)
            if cost > 0:
                tool_credits += cost
                tool_breakdown.append({"tool": tool_name, "credits": cost})

    total_credits = post_credits + tool_credits

    return {
        "posts": {
            "count": num_posts,
            "credits_each": 20,
            "total_credits": post_credits,
        },
        "research_tools": {"tools": tool_breakdown, "total_credits": tool_credits},
        "total_credits": total_credits,
        "estimated_cost_usd": {
            "standard_package": total_credits * 2.0,  # $2/credit in packages
            "additional_credits": total_credits * 2.5,  # $2.50/credit for top-ups
        },
    }
