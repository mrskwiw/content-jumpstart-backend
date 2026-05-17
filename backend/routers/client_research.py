"""Client Research API — discovers business info via web search + Claude synthesis."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.middleware.authorization import verify_client_ownership
from backend.models import User, Client
from backend.schemas.client import ClientUpdate, ClientResponse
from backend.schemas.client_research_schemas import ClientResearchRequest, ClientResearchResponse
from backend.services import crud, credit_service
from backend.services.credit_service import InsufficientCreditsError
from backend.utils.http_rate_limiter import standard_limiter
from backend.utils.logger import logger
from src.agents.client_research_agent import ClientResearchAgent

router = APIRouter()

CREDIT_COST = 200

# Fallback strings emitted by _convert_to_client_brief when a field is absent.
# These must NOT be written back to the database — they would overwrite real data.
_AGENT_FALLBACKS = frozenset({"No description provided", "Not specified"})


def _meaningful(value: object) -> bool:
    """True only for non-empty values that aren't agent placeholder fallbacks."""
    if not value:
        return False
    if isinstance(value, str) and value in _AGENT_FALLBACKS:
        return False
    return True


@router.post("/brief", response_model=ClientResearchResponse)
@standard_limiter.limit("10/hour")
async def research_client_brief(
    request: Request,
    body: ClientResearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Research a business from name + location and return a pre-populated brief draft.
    Does not save to the database — callers review and apply selected fields.
    Costs 200 credits.
    """
    user_id = str(current_user.id)
    try:
        credit_service.deduct_credits(
            db=db,
            user_id=user_id,
            amount=CREDIT_COST,
            description=f"Client brief research: {body.name}",
            reference_type="client_research",
        )
    except InsufficientCreditsError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Insufficient credits. Required: {CREDIT_COST} credits. "
                f"Your balance: {current_user.credit_balance} credits. "
                "Please purchase more credits."
            ),
        )

    try:
        agent = ClientResearchAgent()
        result = await agent.run(
            business_name=body.name,
            location=body.location,
            website=body.website,
        )
    except Exception as e:
        logger.error(f"Client research failed for '{body.name}': {e}", exc_info=True)
        try:
            credit_service.refund_credits(
                db=db,
                user_id=user_id,
                amount=CREDIT_COST,
                description=f"Refund: client research failed for {body.name}",
                reference_type="client_research_refund",
            )
        except Exception as refund_err:
            logger.error(f"Credit refund failed for user {user_id}: {refund_err}")
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")

    return ClientResearchResponse(
        brief=result.brief.model_dump(mode="json"),
        confidence=result.confidence,
        sources=result.sources,
        duration_seconds=result.duration_seconds,
        stub_mode=result.stub_mode,
        warning=result.warning,
        credit_cost=CREDIT_COST,
    )


@router.post("/clients/{client_id}/apply", response_model=ClientResponse)
@standard_limiter.limit("10/hour")
async def research_and_apply(
    request: Request,
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    client: Client = Depends(verify_client_ownership),
):
    """
    Research an existing client by name + location and patch their record with
    all discovered non-null fields. Costs 200 credits.
    """
    client_location = str(client.location) if client.location else None
    if not client_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client location is required for research. Please add a location first.",
        )

    user_id = str(current_user.id)
    try:
        credit_service.deduct_credits(
            db=db,
            user_id=user_id,
            amount=CREDIT_COST,
            description=f"Client brief research: {client.name}",
            reference_type="client_research",
        )
    except InsufficientCreditsError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Required: {CREDIT_COST} credits.",
        )

    try:
        agent = ClientResearchAgent()
        result = await agent.run(business_name=str(client.name), location=client_location)
    except Exception as e:
        logger.error(f"Client research failed for client {client_id}: {e}", exc_info=True)
        try:
            credit_service.refund_credits(
                db=db,
                user_id=user_id,
                amount=CREDIT_COST,
                description=f"Refund: research failed for client {client_id}",
                reference_type="client_research_refund",
            )
        except Exception as refund_err:
            logger.error(f"Credit refund failed for user {user_id}: {refund_err}")
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")

    brief = result.brief

    # Build update with only genuinely discovered fields (preserve existing client data).
    # _meaningful() filters out empty values AND agent fallback placeholders like
    # "No description provided" that appear when a field wasn't found in search results.
    update_data: dict = {}
    if _meaningful(brief.business_description):
        update_data["business_description"] = brief.business_description
    if _meaningful(brief.industry):
        update_data["industry"] = brief.industry
    if brief.keywords:
        update_data["keywords"] = brief.keywords
    if brief.competitors:
        update_data["competitors"] = brief.competitors
    if _meaningful(brief.ideal_customer):
        update_data["ideal_customer"] = brief.ideal_customer
    if _meaningful(brief.main_problem_solved):
        update_data["main_problem_solved"] = brief.main_problem_solved
    if brief.customer_pain_points:
        update_data["customer_pain_points"] = brief.customer_pain_points
    if brief.customer_questions:
        update_data["customer_questions"] = brief.customer_questions
    if brief.tone_preference:
        update_data["tone_preference"] = brief.tone_preference.value
    if brief.brand_personality:
        update_data["brand_personality"] = brief.brand_personality
    if brief.key_phrases:
        update_data["key_phrases"] = brief.key_phrases
    if brief.target_platforms:
        update_data["platforms"] = [p.value for p in brief.target_platforms]
    if _meaningful(brief.main_cta):
        update_data["main_cta"] = brief.main_cta
    if _meaningful(brief.measurable_results):
        update_data["measurable_results"] = brief.measurable_results
    if _meaningful(brief.founder_name):
        update_data["founder_name"] = brief.founder_name

    client_update = ClientUpdate(**update_data)
    updated = crud.update_client(db, client_id, client_update)
    if not updated:
        raise HTTPException(status_code=404, detail="Client not found")

    return ClientResponse.model_validate(updated)
