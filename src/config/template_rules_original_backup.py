"""Template selection rules by client type"""

from enum import Enum
from typing import Dict, List

from ..models.template import TemplateType


class ClientType(Enum):
    """Client business type classification"""

    B2B_SAAS = "b2b_saas"
    AGENCY = "agency"
    COACH_CONSULTANT = "coach_consultant"
    CREATOR_FOUNDER = "creator_founder"
    UNKNOWN = "unknown"


# Template selection matrix from CLAUDE.md:241-248
TEMPLATE_PREFERENCES: Dict[ClientType, Dict[str, List[TemplateType]]] = {
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
    ClientType.UNKNOWN: {
        "preferred": [
            # Default safe set from CLAUDE.md:250
            # Templates 1, 2, 3, 4, 5, 9, 10
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
}
