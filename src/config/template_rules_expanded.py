"""Template selection rules by client type - EXPANDED VERSION

This file contains the expanded client classification system based on 2025 market research.
Includes 10 client types vs original 4.

To activate: Rename this file to template_rules.py and backup the original.
"""

from enum import Enum
from typing import Dict, List

from ..models.template import TemplateType


class ClientType(Enum):
    """Client business type classification - Expanded"""

    # Original 4 types
    B2B_SAAS = "b2b_saas"
    AGENCY = "agency"
    COACH_CONSULTANT = "coach_consultant"
    CREATOR_FOUNDER = "creator_founder"

    # New types (Phase 1 - High Priority)
    REAL_ESTATE = "real_estate"
    RESTAURANT_HOSPITALITY = "restaurant_hospitality"
    ECOMMERCE_RETAIL = "ecommerce_retail"

    # New types (Phase 2 - Medium Priority)
    HEALTHCARE = "healthcare"
    NONPROFIT = "nonprofit"
    LEGAL = "legal"

    # New types (Phase 3 - Lower Priority)
    FINANCIAL_SERVICES = "financial_services"
    HOME_SERVICES = "home_services"
    EDUCATION = "education"

    # Fallback
    UNKNOWN = "unknown"


# Template selection matrix
TEMPLATE_PREFERENCES: Dict[ClientType, Dict[str, List[TemplateType]]] = {
    # ===== ORIGINAL CLIENT TYPES =====
    ClientType.B2B_SAAS: {
        "preferred": [
            TemplateType.PROBLEM_RECOGNITION,
            TemplateType.STATISTIC,
            TemplateType.CONTRARIAN,
            TemplateType.HOW_TO,
            TemplateType.COMPARISON,
        ],
        "avoid": [
            TemplateType.STORY,  # Too vulnerable for B2B
        ],
    },
    ClientType.AGENCY: {
        "preferred": [
            TemplateType.EVOLUTION,  # What Changed
            TemplateType.COMPARISON,
            TemplateType.Q_AND_A,
            TemplateType.MILESTONE,
            TemplateType.BEHIND_SCENES,  # Inside Look
        ],
        "avoid": [
            TemplateType.FUTURE,  # Too speculative
        ],
    },
    ClientType.COACH_CONSULTANT: {
        "preferred": [
            TemplateType.STORY,  # Personal Story
            TemplateType.MYTH_BUSTING,
            TemplateType.FUTURE,
            TemplateType.Q_AND_A,
            TemplateType.LEARNING,  # What I Learned
        ],
        "avoid": [
            TemplateType.STATISTIC,  # Too data-heavy
        ],
    },
    ClientType.CREATOR_FOUNDER: {
        "preferred": [
            TemplateType.STORY,
            TemplateType.Q_AND_A,
            TemplateType.BEHIND_SCENES,  # Inside Look
            TemplateType.CONTRARIAN,
            TemplateType.MILESTONE,
        ],
        "avoid": [
            TemplateType.STATISTIC,  # Not relevant
        ],
    },
    # ===== NEW CLIENT TYPES - PHASE 1 =====
    ClientType.REAL_ESTATE: {
        "preferred": [
            TemplateType.BEHIND_SCENES,  # Property tours, staging
            TemplateType.STORY,  # Client success stories
            TemplateType.MILESTONE,  # Sales achievements
            TemplateType.HOW_TO,  # Buying/selling tips
            TemplateType.Q_AND_A,  # Buyer/seller questions
        ],
        "avoid": [
            TemplateType.MYTH_BUSTING,  # Can be legally risky
            TemplateType.CONTRARIAN,  # Market predictions can backfire
        ],
    },
    ClientType.RESTAURANT_HOSPITALITY: {
        "preferred": [
            TemplateType.BEHIND_SCENES,  # Kitchen, chef stories
            TemplateType.STORY,  # Founding story, customer stories
            TemplateType.QUESTION,  # Engagement posts
            TemplateType.MILESTONE,  # Anniversaries, awards
            TemplateType.EVOLUTION,  # Menu evolution, seasonal changes
        ],
        "avoid": [
            TemplateType.STATISTIC,  # Not relevant unless unique data
            TemplateType.CONTRARIAN,  # Food opinions can alienate
        ],
    },
    ClientType.ECOMMERCE_RETAIL: {
        "preferred": [
            TemplateType.BEHIND_SCENES,  # Product creation, sourcing
            TemplateType.STORY,  # Brand story, customer stories
            TemplateType.QUESTION,  # Engagement posts
            TemplateType.COMPARISON,  # Product comparisons
            TemplateType.HOW_TO,  # Product usage, styling tips
        ],
        "avoid": [
            TemplateType.MYTH_BUSTING,  # Unless industry-specific
        ],
    },
    # ===== NEW CLIENT TYPES - PHASE 2 =====
    ClientType.HEALTHCARE: {
        "preferred": [
            TemplateType.MYTH_BUSTING,  # Health misconceptions
            TemplateType.HOW_TO,  # Wellness tips, preventive care
            TemplateType.Q_AND_A,  # Patient questions
            TemplateType.STATISTIC,  # Health data, outcomes
            TemplateType.EVOLUTION,  # Treatment advancements
        ],
        "avoid": [
            TemplateType.STORY,  # HIPAA concerns
            TemplateType.BEHIND_SCENES,  # Privacy issues
        ],
    },
    ClientType.NONPROFIT: {
        "preferred": [
            TemplateType.STORY,  # Impact stories, beneficiary testimonials
            TemplateType.MILESTONE,  # Fundraising goals, impact metrics
            TemplateType.STATISTIC,  # Impact data
            TemplateType.Q_AND_A,  # Donor/volunteer questions
            TemplateType.BEHIND_SCENES,  # Operations transparency
        ],
        "avoid": [
            TemplateType.COMPARISON,  # Can seem competitive
            TemplateType.CONTRARIAN,  # Can dilute mission focus
        ],
    },
    ClientType.LEGAL: {
        "preferred": [
            TemplateType.MYTH_BUSTING,  # Legal misconceptions
            TemplateType.Q_AND_A,  # Common legal questions
            TemplateType.STATISTIC,  # Case data, legal trends
            TemplateType.HOW_TO,  # Legal process education
            TemplateType.CONTRARIAN,  # Thought leadership
        ],
        "avoid": [
            TemplateType.STORY,  # Client confidentiality
            TemplateType.BEHIND_SCENES,  # Ethics concerns
        ],
    },
    # ===== NEW CLIENT TYPES - PHASE 3 =====
    ClientType.FINANCIAL_SERVICES: {
        "preferred": [
            TemplateType.MYTH_BUSTING,  # Financial misconceptions
            TemplateType.HOW_TO,  # Planning strategies
            TemplateType.STATISTIC,  # Market data
            TemplateType.Q_AND_A,  # Common financial questions
            TemplateType.EVOLUTION,  # Market trends
        ],
        "avoid": [
            TemplateType.STORY,  # Regulatory concerns
            TemplateType.BEHIND_SCENES,  # Privacy/compliance
        ],
    },
    ClientType.HOME_SERVICES: {
        "preferred": [
            TemplateType.BEHIND_SCENES,  # Project process
            TemplateType.HOW_TO,  # DIY tips, maintenance
            TemplateType.STORY,  # Project transformations
            TemplateType.MILESTONE,  # Project completions
            TemplateType.Q_AND_A,  # Homeowner questions
        ],
        "avoid": [
            TemplateType.STATISTIC,  # Not relevant
            TemplateType.FUTURE,  # Not thought leadership focused
        ],
    },
    ClientType.EDUCATION: {
        "preferred": [
            TemplateType.STATISTIC,  # Education data, outcomes
            TemplateType.MILESTONE,  # Student/alumni success
            TemplateType.HOW_TO,  # Educational tips
            TemplateType.Q_AND_A,  # Student/parent questions
            TemplateType.STORY,  # Success stories
        ],
        "avoid": [
            TemplateType.CONTRARIAN,  # Can undermine credibility
        ],
    },
    # ===== FALLBACK =====
    ClientType.UNKNOWN: {
        "preferred": [
            # Default safe set
            TemplateType.PROBLEM_RECOGNITION,
            TemplateType.STATISTIC,
            TemplateType.CONTRARIAN,
            TemplateType.EVOLUTION,
            TemplateType.QUESTION,
            TemplateType.HOW_TO,
            TemplateType.COMPARISON,
        ],
        "avoid": [],
    },
}


# Classification keywords for automatic client type detection
CLIENT_TYPE_KEYWORDS: Dict[ClientType, Dict[str, List[str]]] = {
    # ===== ORIGINAL CLIENT TYPES =====
    ClientType.B2B_SAAS: {
        "business_description": [
            "saas",
            "software",
            "platform",
            "api",
            "b2b",
            "enterprise",
            "tool",
            "solution",
            "technology",
        ],
        "ideal_customer": [
            "companies",
            "businesses",
            "teams",
            "organizations",
            "cto",
            "ceo",
            "vp",
            "director",
        ],
    },
    ClientType.AGENCY: {
        "business_description": [
            "agency",
            "marketing",
            "consulting",
            "services",
            "clients",
            "campaigns",
            "creative",
            "strategy",
        ],
        "ideal_customer": [
            "clients",
            "brands",
            "companies",
            "businesses",
            "cmo",
            "marketing director",
        ],
    },
    ClientType.COACH_CONSULTANT: {
        "business_description": [
            "coach",
            "coaching",
            "consultant",
            "consulting",
            "training",
            "mentoring",
            "advisor",
            "guide",
            "transform",
        ],
        "ideal_customer": [
            "professionals",
            "individuals",
            "leaders",
            "executives",
            "entrepreneurs",
            "people who",
        ],
    },
    ClientType.CREATOR_FOUNDER: {
        "business_description": [
            "creator",
            "founder",
            "building",
            "startup",
            "launched",
            "solopreneur",
            "indie hacker",
            "bootstrapped",
        ],
        "ideal_customer": [
            "followers",
            "audience",
            "community",
            "subscribers",
            "fans",
            "readers",
        ],
    },
    # ===== NEW CLIENT TYPES - PHASE 1 =====
    ClientType.REAL_ESTATE: {
        "business_description": [
            "real estate",
            "realtor",
            "broker",
            "properties",
            "homes",
            "listings",
            "agent",
            "residential",
            "commercial",
            "investment properties",
        ],
        "ideal_customer": [
            "buyers",
            "sellers",
            "homeowners",
            "investors",
            "first-time buyers",
            "luxury buyers",
            "families",
            "relocating",
        ],
    },
    ClientType.RESTAURANT_HOSPITALITY: {
        "business_description": [
            "restaurant",
            "café",
            "bistro",
            "dining",
            "food",
            "cuisine",
            "hospitality",
            "hotel",
            "catering",
            "bar",
            "eatery",
        ],
        "ideal_customer": [
            "diners",
            "guests",
            "food lovers",
            "locals",
            "tourists",
            "families",
            "couples",
            "groups",
        ],
    },
    ClientType.ECOMMERCE_RETAIL: {
        "business_description": [
            "e-commerce",
            "ecommerce",
            "online store",
            "retail",
            "shop",
            "boutique",
            "fashion",
            "clothing",
            "accessories",
            "products",
        ],
        "ideal_customer": [
            "shoppers",
            "customers",
            "fashion lovers",
            "online shoppers",
            "consumers",
            "buyers",
        ],
    },
    # ===== NEW CLIENT TYPES - PHASE 2 =====
    ClientType.HEALTHCARE: {
        "business_description": [
            "healthcare",
            "medical",
            "clinic",
            "practice",
            "doctor",
            "dentist",
            "therapy",
            "wellness",
            "patient care",
            "health services",
        ],
        "ideal_customer": [
            "patients",
            "families",
            "individuals",
            "seniors",
            "children",
            "community members",
            "health-conscious",
        ],
    },
    ClientType.NONPROFIT: {
        "business_description": [
            "nonprofit",
            "charity",
            "foundation",
            "mission",
            "cause",
            "advocacy",
            "community",
            "social impact",
            "organization",
            "501c3",
        ],
        "ideal_customer": [
            "donors",
            "volunteers",
            "community members",
            "supporters",
            "advocates",
            "philanthropists",
            "activists",
        ],
    },
    ClientType.LEGAL: {
        "business_description": [
            "law",
            "legal",
            "attorney",
            "lawyer",
            "firm",
            "practice",
            "litigation",
            "counsel",
            "advocacy",
        ],
        "ideal_customer": [
            "clients",
            "businesses",
            "individuals",
            "families",
            "companies",
            "defendants",
            "plaintiffs",
        ],
    },
    # ===== NEW CLIENT TYPES - PHASE 3 =====
    ClientType.FINANCIAL_SERVICES: {
        "business_description": [
            "financial",
            "advisor",
            "planner",
            "wealth",
            "investment",
            "retirement",
            "tax",
            "accounting",
            "cpa",
            "bookkeeping",
        ],
        "ideal_customer": [
            "investors",
            "retirees",
            "business owners",
            "families",
            "high-net-worth",
            "entrepreneurs",
            "savers",
        ],
    },
    ClientType.HOME_SERVICES: {
        "business_description": [
            "contractor",
            "plumber",
            "electrician",
            "hvac",
            "landscaping",
            "home improvement",
            "construction",
            "renovation",
            "remodeling",
        ],
        "ideal_customer": [
            "homeowners",
            "property owners",
            "families",
            "landlords",
            "real estate investors",
        ],
    },
    ClientType.EDUCATION: {
        "business_description": [
            "education",
            "school",
            "university",
            "college",
            "training",
            "learning",
            "academy",
            "institute",
            "online course",
        ],
        "ideal_customer": [
            "students",
            "parents",
            "learners",
            "professionals",
            "educators",
            "career changers",
        ],
    },
}


# ===== METADATA FOR NEW CLIENT TYPES =====

# Posting frequency recommendations by client type
POSTING_FREQUENCY: Dict[ClientType, str] = {
    ClientType.B2B_SAAS: "3-4x weekly",
    ClientType.AGENCY: "4-5x weekly",
    ClientType.COACH_CONSULTANT: "3-4x weekly",
    ClientType.CREATOR_FOUNDER: "5-7x weekly",
    ClientType.REAL_ESTATE: "5-7x weekly",
    ClientType.RESTAURANT_HOSPITALITY: "5-7x weekly (daily for high performers)",
    ClientType.ECOMMERCE_RETAIL: "Daily (7x weekly)",
    ClientType.HEALTHCARE: "3-4x weekly",
    ClientType.NONPROFIT: "3-4x weekly",
    ClientType.LEGAL: "2-3x weekly",
    ClientType.FINANCIAL_SERVICES: "2-4x weekly (higher in tax season)",
    ClientType.HOME_SERVICES: "3-5x weekly",
    ClientType.EDUCATION: "3-4x weekly",
    ClientType.UNKNOWN: "3-4x weekly",
}

# Primary platform recommendations by client type
PRIMARY_PLATFORMS: Dict[ClientType, List[str]] = {
    ClientType.B2B_SAAS: ["LinkedIn", "Twitter"],
    ClientType.AGENCY: ["LinkedIn", "Instagram"],
    ClientType.COACH_CONSULTANT: ["LinkedIn", "Instagram"],
    ClientType.CREATOR_FOUNDER: ["Instagram", "Twitter", "TikTok"],
    ClientType.REAL_ESTATE: ["Instagram", "Facebook", "LinkedIn"],
    ClientType.RESTAURANT_HOSPITALITY: ["Instagram", "TikTok", "Facebook"],
    ClientType.ECOMMERCE_RETAIL: ["Instagram", "TikTok", "Facebook", "Pinterest"],
    ClientType.HEALTHCARE: ["Facebook", "LinkedIn", "YouTube"],
    ClientType.NONPROFIT: ["Facebook", "LinkedIn", "Instagram"],
    ClientType.LEGAL: ["LinkedIn", "YouTube", "Twitter"],
    ClientType.FINANCIAL_SERVICES: ["LinkedIn", "Facebook", "YouTube"],
    ClientType.HOME_SERVICES: ["Facebook", "Instagram", "Nextdoor"],
    ClientType.EDUCATION: ["LinkedIn", "Facebook", "Instagram"],
    ClientType.UNKNOWN: ["LinkedIn", "Facebook"],
}

# Pricing tier recommendations by client type (for business model)
PRICING_TIER_RECOMMENDATIONS: Dict[ClientType, str] = {
    ClientType.B2B_SAAS: "Professional ($1,800) or Premium ($2,500)",
    ClientType.AGENCY: "Professional ($1,800)",
    ClientType.COACH_CONSULTANT: "Professional ($1,800)",
    ClientType.CREATOR_FOUNDER: "Starter ($1,200) or Professional ($1,800)",
    ClientType.REAL_ESTATE: "Premium ($2,500) - high client value",
    ClientType.RESTAURANT_HOSPITALITY: "Professional ($1,800)",
    ClientType.ECOMMERCE_RETAIL: "Professional ($1,800)",
    ClientType.HEALTHCARE: "Premium ($2,500) - strong ROI justification",
    ClientType.NONPROFIT: "Professional ($1,800) - value-driven",
    ClientType.LEGAL: "Premium ($2,500) - high client value",
    ClientType.FINANCIAL_SERVICES: "Premium ($2,500) - high client value",
    ClientType.HOME_SERVICES: "Starter ($1,200) - cost-sensitive",
    ClientType.EDUCATION: "Starter ($1,200) or Professional ($1,800)",
    ClientType.UNKNOWN: "Professional ($1,800)",
}
