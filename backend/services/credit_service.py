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

from backend.models import CreditPackage, CreditTransaction, User


class InsufficientCreditsError(Exception):
    """Raised when user doesn't have enough credits for an operation."""

    pass


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

    return user.credit_balance


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

    # Get user with row-level lock for atomic update
    user = db.query(User).filter(User.id == user_id).with_for_update().first()
    if not user:
        raise ValueError(f"User not found: {user_id}")

    # Check balance
    if user.credit_balance < amount:
        raise InsufficientCreditsError(
            f"Insufficient credits. Required: {amount}, Available: {user.credit_balance}"
        )

    # Deduct credits
    user.credit_balance -= amount
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

    # Add credits
    user.credit_balance += package.credits
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

    # Add credits
    user.credit_balance += amount
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

    # Check balance if negative adjustment
    if amount < 0 and user.credit_balance < abs(amount):
        raise ValueError(f"Cannot adjust by {amount}. User balance: {user.credit_balance}")

    # Adjust balance
    user.credit_balance += amount

    # Adjust usage tracking (only for negative adjustments)
    if amount < 0:
        user.total_credits_used += abs(amount)

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
    query = db.query(CreditPackage).filter(CreditPackage.is_active == True)  # noqa: E712

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
        "balance": user.credit_balance,
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
        "posts": {"count": num_posts, "credits_each": 20, "total_credits": post_credits},
        "research_tools": {"tools": tool_breakdown, "total_credits": tool_credits},
        "total_credits": total_credits,
        "estimated_cost_usd": {
            "standard_package": total_credits * 2.0,  # $2/credit in packages
            "additional_credits": total_credits * 2.5,  # $2.50/credit for top-ups
        },
    }
