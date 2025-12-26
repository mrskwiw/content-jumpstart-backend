"""
Centralized pricing configuration for the Content Jumpstart system.

This module provides:
- Global pricing constants ($40/post, $15 research add-on)
- Preset package definitions (Quick Start, Professional, Premium)
- Price calculation utilities
- Unlimited revision policy
"""
from typing import Dict, List, Optional
from pydantic import BaseModel
from enum import Enum


class PackageTier(str, Enum):
    """Package tier names"""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    PREMIUM = "premium"
    CUSTOM = "custom"


class PricingConfig(BaseModel):
    """Global pricing constants"""

    # Base pricing
    PRICE_PER_POST: float = 40.0
    RESEARCH_PRICE_PER_POST: float = 15.0  # Optional add-on per post

    # Minimum and maximum order sizes
    MIN_POSTS: int = 1
    MAX_POSTS: int = 100  # Soft limit for UI (can be overridden)

    # Revision policy
    UNLIMITED_REVISIONS: bool = True  # Changed from limited revisions

    # Volume discounts (future feature)
    VOLUME_DISCOUNTS: Dict[int, float] = {
        # posts_threshold: discount_percentage
        50: 0.05,   # 5% off at 50+ posts
        100: 0.10,  # 10% off at 100+ posts
    }


class PresetPackage(BaseModel):
    """Preset package definition with template quantities"""

    tier: PackageTier
    name: str
    description: str
    template_quantities: Dict[int, int]  # Preset template distribution (template_id: quantity)
    research_included: bool
    price: float  # Pre-calculated for display

    @property
    def total_posts(self) -> int:
        """Calculate total posts from template quantities"""
        return sum(self.template_quantities.values())


# Preset package definitions
# Each package is designed with specific template mixes for optimal content variety
PRESET_PACKAGES: List[PresetPackage] = [
    PresetPackage(
        tier=PackageTier.STARTER,
        name="Quick Start (15 Posts)",
        description="Fast templates for high engagement - ideal for getting started quickly",
        template_quantities={
            1: 2,   # Problem Recognition (fast)
            2: 2,   # Statistic + Insight (fast)
            5: 2,   # Question Post (fast)
            9: 3,   # How-To (fast)
            10: 3,  # Comparison (fast)
            3: 2,   # Contrarian Take (medium)
            4: 1,   # What Changed (medium)
        },
        research_included=False,
        price=600.0  # 15 posts * $40
    ),
    PresetPackage(
        tier=PackageTier.PROFESSIONAL,
        name="Professional (30 Posts)",
        description="Balanced variety with proven templates - our most popular package",
        template_quantities={
            1: 2,   # Problem Recognition
            2: 2,   # Statistic + Insight
            3: 2,   # Contrarian Take
            4: 2,   # What Changed
            5: 2,   # Question Post
            7: 2,   # Myth Busting
            9: 3,   # How-To
            10: 3,  # Comparison
            11: 2,  # What I Learned From
            13: 2,  # Future Thinking
            14: 2,  # Reader Q Response
            6: 2,   # Personal Story
            8: 1,   # Things I Got Wrong
            12: 1,  # Inside Look
            15: 2,  # Milestone
        },
        research_included=False,
        price=1200.0  # 30 posts * $40
    ),
    PresetPackage(
        tier=PackageTier.PREMIUM,
        name="Premium (50 Posts)",
        description="Full variety + research included - comprehensive content ecosystem",
        template_quantities={
            1: 4,   # Problem Recognition
            2: 4,   # Statistic + Insight
            3: 3,   # Contrarian Take
            4: 3,   # What Changed
            5: 4,   # Question Post
            6: 3,   # Personal Story
            7: 3,   # Myth Busting
            8: 2,   # Things I Got Wrong
            9: 5,   # How-To
            10: 4,  # Comparison
            11: 3,  # What I Learned From
            12: 2,  # Inside Look
            13: 3,  # Future Thinking
            14: 4,  # Reader Q Response (increased from 3 to 4)
            15: 3,  # Milestone (increased from 2 to 3)
        },
        research_included=True,  # +$15/post included
        price=2750.0  # 50 * ($40 + $15)
    ),
]


def calculate_price(
    num_posts: int,
    research_per_post: bool = False,
    price_per_post: float = 40.0,
    research_price: float = 15.0
) -> float:
    """
    Calculate total price with optional research add-on.

    Args:
        num_posts: Number of posts to generate
        research_per_post: Whether to include research add-on
        price_per_post: Base price per post (default: $40)
        research_price: Research price per post (default: $15)

    Returns:
        Total price as float

    Examples:
        >>> calculate_price(30, research_per_post=False)
        1200.0
        >>> calculate_price(30, research_per_post=True)
        1650.0
        >>> calculate_price(50, research_per_post=True)
        2750.0
    """
    base = num_posts * price_per_post
    research = num_posts * research_price if research_per_post else 0.0
    return base + research


def get_preset_package(tier: PackageTier) -> Optional[PresetPackage]:
    """
    Get preset package by tier.

    Args:
        tier: Package tier (starter, professional, premium)

    Returns:
        PresetPackage if found, None otherwise

    Example:
        >>> pkg = get_preset_package(PackageTier.PROFESSIONAL)
        >>> pkg.total_posts
        30
        >>> pkg.price
        1200.0
    """
    for pkg in PRESET_PACKAGES:
        if pkg.tier == tier:
            return pkg
    return None


def calculate_price_from_quantities(
    template_quantities: Dict[int, int],
    research_per_post: bool = False,
    price_per_post: float = 40.0,
    research_price: float = 15.0
) -> float:
    """
    Calculate price from template quantities.

    Args:
        template_quantities: Dict mapping template_id -> quantity
        research_per_post: Whether to include research add-on
        price_per_post: Base price per post (default: $40)
        research_price: Research price per post (default: $15)

    Returns:
        Total price as float

    Example:
        >>> calculate_price_from_quantities({"1": 3, "2": 5, "9": 2}, research_per_post=False)
        400.0  # 10 posts * $40
    """
    total_posts = sum(template_quantities.values())
    return calculate_price(total_posts, research_per_post, price_per_post, research_price)
