"""
Pricing API endpoints.

Provides pricing configuration, preset packages, and price calculations
for the operator dashboard and external integrations.
"""

import sys
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Query, HTTPException, Request, status
from pydantic import BaseModel

# Add project root to path to import from src
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config.pricing import (  # noqa: E402
    PRESET_PACKAGES,
    calculate_price,
    calculate_price_from_quantities,
    PricingConfig,
    PresetPackage,
    PackageTier,
    get_preset_package,
)
from backend.utils.http_rate_limiter import lenient_limiter  # noqa: E402


router = APIRouter()


class PricingConfigResponse(BaseModel):
    """Response model for pricing configuration"""

    pricePerPost: float
    researchPricePerPost: float
    minPosts: int
    maxPosts: int
    unlimitedRevisions: bool


class CalculatePriceResponse(BaseModel):
    """Response model for price calculation"""

    numPosts: int
    researchIncluded: bool
    pricePerPost: float
    researchPricePerPost: float
    totalPrice: float


@router.get("/config", response_model=PricingConfigResponse)
@lenient_limiter.limit("1000/hour")  # TR-004: Cheap read operation
async def get_pricing_config(request: Request) -> PricingConfigResponse:
    """
    Get current pricing configuration.

    Rate limit: 1000/hour (cheap read operation)

    Returns global pricing constants like price per post,
    research pricing, and revision policy.

    Example response:
    ```json
    {
        "pricePerPost": 40.0,
        "researchPricePerPost": 15.0,
        "minPosts": 1,
        "maxPosts": 100,
        "unlimitedRevisions": true
    }
    ```
    """
    config = PricingConfig()
    return PricingConfigResponse(
        pricePerPost=config.PRICE_PER_POST,
        researchPricePerPost=config.RESEARCH_PRICE_PER_POST,
        minPosts=config.MIN_POSTS,
        maxPosts=config.MAX_POSTS,
        unlimitedRevisions=config.UNLIMITED_REVISIONS,
    )


@router.get("/packages", response_model=List[PresetPackage])
@lenient_limiter.limit("1000/hour")  # TR-004: Cheap read operation
async def get_preset_packages(request: Request) -> List[PresetPackage]:
    """
    Get all preset packages.

    Rate limit: 1000/hour (cheap read operation)

    Returns a list of preset packages with their template quantities,
    descriptions, and pricing.

    Example response:
    ```json
    [
        {
            "tier": "starter",
            "name": "Quick Start (15 Posts)",
            "description": "Fast templates for high engagement",
            "templateQuantities": {"1": 2, "2": 2, "5": 2, ...},
            "researchIncluded": false,
            "price": 600.0
        },
        ...
    ]
    ```
    """
    return PRESET_PACKAGES


@router.get("/packages/{tier}", response_model=PresetPackage)
@lenient_limiter.limit("1000/hour")  # TR-004: Cheap read operation
async def get_package_by_tier(request: Request, tier: PackageTier) -> PresetPackage:
    """
    Get a specific preset package by tier.

    Rate limit: 1000/hour (cheap read operation)

    Args:
        tier: Package tier (starter, professional, premium)

    Returns:
        Preset package details

    Raises:
        404: Package tier not found
    """
    package = get_preset_package(tier)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Package tier '{tier}' not found"
        )
    return package


@router.get("/calculate", response_model=CalculatePriceResponse)
@lenient_limiter.limit("1000/hour")  # TR-004: Cheap operation (calculation only)
async def calculate_custom_price(
    request: Request,
    num_posts: int = Query(..., ge=1, description="Number of posts to generate"),
    research: bool = Query(False, description="Include research add-on"),
) -> CalculatePriceResponse:
    """
    Calculate price for custom configuration.

    Rate limit: 1000/hour (cheap calculation operation)

    Args:
        num_posts: Number of posts (must be >= 1)
        research: Whether to include research add-on

    Returns:
        Price calculation breakdown

    Example response:
    ```json
    {
        "numPosts": 30,
        "researchIncluded": true,
        "pricePerPost": 40.0,
        "researchPricePerPost": 15.0,
        "totalPrice": 1650.0
    }
    ```
    """
    config = PricingConfig()
    price = calculate_price(
        num_posts=num_posts,
        research_per_post=research,
        price_per_post=config.PRICE_PER_POST,
        research_price=config.RESEARCH_PRICE_PER_POST,
    )

    return CalculatePriceResponse(
        numPosts=num_posts,
        researchIncluded=research,
        pricePerPost=config.PRICE_PER_POST,
        researchPricePerPost=config.RESEARCH_PRICE_PER_POST if research else 0.0,
        totalPrice=price,
    )


@router.post("/calculate-from-quantities", response_model=CalculatePriceResponse)
@lenient_limiter.limit("1000/hour")  # TR-004: Cheap operation (calculation only)
async def calculate_price_from_template_quantities(
    request: Request,
    template_quantities: Dict[str, int],
    research: bool = False,
) -> CalculatePriceResponse:
    """
    Calculate price from template quantities.

    Rate limit: 1000/hour (cheap calculation operation)

    Useful for custom template selections where the user specifies
    exact quantities for each template.

    Args:
        template_quantities: Dict mapping template_id (as string) -> quantity
        research: Whether to include research add-on

    Returns:
        Price calculation breakdown

    Example request body:
    ```json
    {
        "template_quantities": {"1": 3, "2": 5, "9": 2},
        "research": false
    }
    ```

    Example response:
    ```json
    {
        "numPosts": 10,
        "researchIncluded": false,
        "pricePerPost": 40.0,
        "researchPricePerPost": 0.0,
        "totalPrice": 400.0
    }
    ```
    """
    # Convert string keys to integers
    quantities_int = {int(k): v for k, v in template_quantities.items()}

    config = PricingConfig()
    price = calculate_price_from_quantities(
        template_quantities=quantities_int,
        research_per_post=research,
        price_per_post=config.PRICE_PER_POST,
        research_price=config.RESEARCH_PRICE_PER_POST,
    )

    total_posts = sum(quantities_int.values())

    return CalculatePriceResponse(
        numPosts=total_posts,
        researchIncluded=research,
        pricePerPost=config.PRICE_PER_POST,
        researchPricePerPost=config.RESEARCH_PRICE_PER_POST if research else 0.0,
        totalPrice=price,
    )
