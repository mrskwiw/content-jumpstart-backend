"""Account entitlement status — the data the subscribe page renders.

Deliberately on the expired-account allowlist (`account_state._EXPIRED_ALLOWED_PREFIXES`):
this is what an expired customer's client calls to find out *why* it was locked out
and what to do about it. Gating it behind the same gate it explains would be a loop.

Read-only. Nothing here spends credits or mutates state.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.models import User
from backend.services.account_state import (
    BLOCKED_STATES,
    account_credits,
    account_state,
    is_gated,
    trial_ends_at,
)
from backend.services.settings_service import get_instance_config

router = APIRouter(prefix="/api/account", tags=["Account"])


class PlanOption(BaseModel):
    id: str
    name: str
    price_usd_month: int
    monthly_credits: int
    annual_price_usd: int


class AccountStatus(BaseModel):
    state: str
    # True when the entitlement gate is closed. NOT the same as state == "expired":
    # a lapsed subscription with credits left is still usable.
    gated: bool
    # Why it closed, so the page can say something true rather than guessing:
    # "trial_ended" | "credits_exhausted" | None.
    gate_reason: str | None
    # past_due / suspended: a billing problem on a LIVE subscription. Reads still
    # work; spending is blocked. Distinct from gated, which closes everything.
    spend_blocked: bool
    credits_remaining: int
    trial_ends_at: str | None
    plan_id: str | None
    plans: list[PlanOption]


# Mirrors the locked pricing (2026-07-30): 2 credits per $1, annual = 10x monthly.
# Kept here so the subscribe page renders without a control-plane round trip; the
# control plane remains authoritative at checkout.
_PLANS = [
    PlanOption(
        id="starter",
        name="Starter",
        price_usd_month=500,
        monthly_credits=1_000,
        annual_price_usd=5_000,
    ),
    PlanOption(
        id="freelancer",
        name="Freelancer",
        price_usd_month=1_500,
        monthly_credits=3_000,
        annual_price_usd=15_000,
    ),
    PlanOption(
        id="agency",
        name="Agency",
        price_usd_month=3_000,
        monthly_credits=6_000,
        annual_price_usd=30_000,
    ),
]


@router.get("/status", response_model=AccountStatus)
def get_account_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountStatus:
    """Current entitlement state + the plans available to restore access."""
    state = account_state(db)
    credits = account_credits(db)
    gated = is_gated(db)
    # The two triggers end for different reasons, and the page should say which —
    # "your trial has ended" and "you've used your remaining credits" call for
    # different next steps.
    reason: str | None = None
    if gated:
        reason = "trial_ended" if state == "trial" else "credits_exhausted"
    ends = trial_ends_at(db)
    return AccountStatus(
        state=state,
        gated=gated,
        gate_reason=reason,
        spend_blocked=state in BLOCKED_STATES,
        credits_remaining=credits,
        trial_ends_at=ends.isoformat() if ends else None,
        plan_id=get_instance_config(db, "plan_id", default=None),
        plans=_PLANS,
    )
