"""
Credit system API routes.

Endpoints:
- GET /credits/balance - Get current credit balance
- GET /credits/transactions - Get transaction history
- POST /credits/purchase - Purchase credits
- GET /credits/packages - Get available packages
- GET /credits/summary - Get comprehensive credit summary
- POST /credits/estimate - Estimate project cost
- POST /credits/admin/adjust - Admin credit adjustment
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.models import User
from backend.schemas.credit_schemas import (
    AdminCreditAdjustmentRequest,
    AdminCreditAdjustmentResponse,
    CostEstimationRequest,
    CostEstimateResponse,
    CreditBalanceResponse,
    CreditPackageResponse,
    CreditPurchaseRequest,
    CreditPurchaseResponse,
    CreditSummaryResponse,
    CreditTransactionResponse,
)
from backend.services import credit_service

router = APIRouter(prefix="/credits", tags=["credits"])

logger = logging.getLogger(__name__)


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to verify user is an admin (superuser).

    Raises:
        HTTPException 403: User is not an admin

    Returns:
        User instance if admin
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


@router.get("/balance", response_model=CreditBalanceResponse)
def get_credit_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's credit balance."""
    try:
        return CreditBalanceResponse(
            # Live lot sum, not the cached column — excludes expired credits even
            # for an idle user with no intervening mutation (S-01.4b-ii review).
            balance=credit_service.live_balance(db, current_user.id),
            total_purchased=current_user.total_credits_purchased,
            total_used=current_user.total_credits_used,
            is_enterprise=current_user.is_enterprise,
            custom_credit_rate=current_user.custom_credit_rate,
        )
    except Exception as e:
        logger.error(f"Error fetching credit balance for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve credit balance")


@router.get("/transactions", response_model=List[CreditTransactionResponse])
def get_transactions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    transaction_type: str = Query(
        default=None, pattern="^(purchase|deduction|refund|admin_adjustment)$"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user's transaction history."""
    try:
        return credit_service.get_transactions(
            db=db,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
            transaction_type=transaction_type,
        )
    except Exception as e:
        logger.error(f"Error fetching transactions for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve transactions")


@router.post(
    "/purchase", response_model=CreditPurchaseResponse, status_code=status.HTTP_201_CREATED
)
def purchase_credits(
    request: CreditPurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Purchase credits from a package.

    Note: In production, this should be called AFTER successful payment processing.
    The payment_reference should contain the payment/invoice ID.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Direct credit purchase requires admin. Use /api/stripe/checkout instead.",
        )
    try:
        transaction = credit_service.purchase_credits(
            db=db,
            user_id=current_user.id,
            package_id=request.package_id,
            payment_reference=request.payment_reference,
        )

        # Get updated balance
        db.refresh(current_user)

        # Get package info
        from backend.models import CreditPackage

        package = db.query(CreditPackage).filter(CreditPackage.id == request.package_id).first()

        package_info = CreditPackageResponse(
            id=package.id,
            name=package.name,
            credits=package.credits,
            price_usd=package.price_usd,
            package_type=package.package_type,
            description=package.description,
            is_active=package.is_active,
            rate_per_credit=package.price_usd / package.credits,
        )

        return CreditPurchaseResponse(
            transaction=transaction,
            new_balance=current_user.credit_balance,
            package_info=package_info,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/packages", response_model=List[CreditPackageResponse])
def get_credit_packages(
    package_type: str = Query(default=None, pattern="^(package|additional)$"),
    db: Session = Depends(get_db),
):
    """Get available credit packages."""
    packages = credit_service.get_package_pricing(db=db, package_type=package_type)

    return [
        CreditPackageResponse(
            id=p.id,
            name=p.name,
            credits=p.credits,
            price_usd=p.price_usd,
            package_type=p.package_type,
            description=p.description,
            is_active=p.is_active,
            rate_per_credit=p.price_usd / p.credits,
        )
        for p in packages
    ]


@router.get("/summary", response_model=CreditSummaryResponse)
def get_credit_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get comprehensive credit summary for current user."""
    try:
        summary = credit_service.get_credit_summary(db=db, user_id=current_user.id)
        return summary

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/estimate", response_model=CostEstimateResponse)
def estimate_project_cost(request: CostEstimationRequest):
    """
    Estimate credit cost for a project.

    No authentication required - can be used for pre-signup cost calculation.
    """
    estimate = credit_service.estimate_cost(
        num_posts=request.num_posts,
        research_tools=request.research_tools,
    )

    return estimate


# Admin-only routes
@router.post(
    "/admin/adjust",
    response_model=AdminCreditAdjustmentResponse,
)
def admin_adjust_credits(
    request: AdminCreditAdjustmentRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Admin-only endpoint to adjust user credits.

    Positive amount adds credits, negative removes credits.
    """
    try:
        transaction = credit_service.admin_adjust_credits(
            db=db,
            user_id=request.user_id,
            amount=request.amount,
            description=request.description,
            admin_user_id=current_user.id,
        )

        # Get updated user balance
        from backend.models import User as UserModel

        user = db.query(UserModel).filter(UserModel.id == request.user_id).first()

        return AdminCreditAdjustmentResponse(
            transaction=transaction,
            new_balance=user.credit_balance,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
