"""
Template Prerequisites System

Validates that templates have required data before generation.
"""

from typing import Dict, List
from enum import Enum


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


TEMPLATE_IDS = {
    1: "problem_recognition",
    2: "statistic_insight",
    3: "contrarian_take",
    4: "whats_changed",
    5: "question_post",
    6: "personal_story",
    7: "myth_busting",
    8: "things_i_got_wrong",
    9: "how_to",
    10: "comparison",
    11: "what_i_learned",
    12: "inside_look",
    13: "future_thinking",
    14: "reader_question",
    15: "milestone",
}


TEMPLATE_PREREQUISITES = {
    "personal_story": {
        "required_client_fields": ["business_description"],
        "recommended_research_tools": ["story_mining"],
        "risk_level": RiskLevel.CRITICAL,
        "block_generation": True,
        "error_message": "Personal Story posts require authentic stories. Run Story Mining first.",
    },
    "things_i_got_wrong": {
        "required_client_fields": ["business_description"],
        "recommended_research_tools": ["story_mining"],
        "risk_level": RiskLevel.CRITICAL,
        "block_generation": True,
        "error_message": "This template requires authentic learning stories. Run Story Mining first.",
    },
    "inside_look": {
        "required_client_fields": ["business_description"],
        "recommended_research_tools": ["story_mining"],
        "risk_level": RiskLevel.CRITICAL,
        "block_generation": True,
        "error_message": "Inside Look requires real internal processes. Run Story Mining first.",
    },
    "milestone": {
        "required_client_fields": ["business_description"],
        "risk_level": RiskLevel.CRITICAL,
        "block_generation": True,
        "error_message": "Milestone posts require real achievements.",
    },
    # HIGH RISK - Warn but allow generation
    "statistic_insight": {
        "required_client_fields": ["industry", "business_description"],
        "recommended_research_tools": ["market_trends_research"],
        "risk_level": RiskLevel.HIGH,
        "block_generation": False,
        "warning_message": "This template works best with current industry statistics. Consider running Market Trends Research first.",
    },
    "what_i_learned": {
        "required_client_fields": ["business_description"],
        "recommended_research_tools": ["story_mining"],
        "risk_level": RiskLevel.HIGH,
        "block_generation": False,
        "warning_message": "Learning posts are more authentic with real client experiences. Generic lessons may reduce engagement.",
    },
    "future_thinking": {
        "required_client_fields": ["industry", "business_description"],
        "recommended_research_tools": ["market_trends_research"],
        "risk_level": RiskLevel.HIGH,
        "block_generation": False,
        "warning_message": "Future predictions need industry context. Consider running Market Trends Research for credible insights.",
    },
    # LOW RISK - Can generate with minimal data
    "problem_recognition": {
        "required_client_fields": ["customer_pain_points", "ideal_customer"],
        "recommended_client_fields": ["industry"],
        "risk_level": RiskLevel.LOW,
        "block_generation": False,
    },
    "contrarian_take": {
        "required_client_fields": ["industry"],
        "recommended_client_fields": ["business_description"],
        "risk_level": RiskLevel.LOW,
        "block_generation": False,
    },
    "whats_changed": {
        "required_client_fields": ["industry"],
        "recommended_research_tools": ["market_trends_research"],
        "risk_level": RiskLevel.LOW,
        "block_generation": False,
    },
    "question_post": {
        "required_client_fields": ["ideal_customer"],
        "recommended_client_fields": ["customer_pain_points"],
        "risk_level": RiskLevel.LOW,
        "block_generation": False,
    },
    "myth_busting": {
        "required_client_fields": ["industry"],
        "recommended_client_fields": ["business_description"],
        "risk_level": RiskLevel.LOW,
        "block_generation": False,
    },
    "how_to": {
        "required_client_fields": ["business_description", "main_problem_solved"],
        "recommended_client_fields": ["customer_pain_points"],
        "risk_level": RiskLevel.LOW,
        "block_generation": False,
    },
    "comparison": {
        "required_client_fields": ["industry"],
        "recommended_research_tools": ["competitive_analysis"],
        "risk_level": RiskLevel.LOW,
        "block_generation": False,
    },
    "reader_question": {
        "required_client_fields": ["customer_questions"],
        "recommended_client_fields": ["business_description"],
        "risk_level": RiskLevel.LOW,
        "block_generation": False,
    },
}


def check_client_field(client_data: Dict, field_name: str) -> bool:
    value = client_data.get(field_name)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    elif isinstance(value, list):
        return len(value) > 0
    return bool(value)


def check_template_prerequisites(
    template_id: str, client_data: Dict, completed_research_tools: List[str] = []
) -> Dict:
    """
    Check if template prerequisites are met.

    Args:
        template_id: Template name key (e.g. "personal_story")
        client_data: Dict of client fields
        completed_research_tools: List of tool names that have been run for this project

    Returns:
        dict with keys:
        - can_generate (bool): Whether generation should proceed
        - should_block (bool): Whether generation should be blocked
        - risk_level (str): CRITICAL, HIGH, MEDIUM, or LOW
        - missing_required_fields (list): Required client fields that are missing
        - missing_recommended_fields (list): Recommended client fields that are missing
        - missing_required_tools (list): Required research tools not yet run
        - missing_research_tools (list): Recommended research tools not yet run
        - error_message (str): Error message if blocked
        - warning_message (str): Warning message if not blocked but data incomplete
    """
    prereqs = TEMPLATE_PREREQUISITES.get(template_id, {})

    if not prereqs:
        return {
            "can_generate": True,
            "should_block": False,
            "risk_level": RiskLevel.LOW,
            "missing_required_fields": [],
            "missing_recommended_fields": [],
            "missing_required_tools": [],
            "missing_research_tools": [],
        }

    # Check required client fields
    required_fields: list = prereqs.get("required_client_fields", [])  # type: ignore[assignment]
    missing_required = [f for f in required_fields if not check_client_field(client_data, f)]

    # Check recommended client fields
    recommended_fields: list = prereqs.get("recommended_client_fields", [])  # type: ignore[assignment]
    missing_recommended = [f for f in recommended_fields if not check_client_field(client_data, f)]

    # Check required research tools (block if missing)
    required_tools: list = prereqs.get("required_research_tools", [])  # type: ignore[assignment]
    missing_required_tools = [t for t in required_tools if t not in completed_research_tools]

    # Determine if generation should be blocked
    block = prereqs.get("block_generation", False)
    should_block = block and (len(missing_required) > 0 or len(missing_required_tools) > 0)

    result = {
        "can_generate": not should_block,
        "should_block": should_block,
        "risk_level": prereqs.get("risk_level", RiskLevel.LOW),
        "missing_required_fields": missing_required,
        "missing_recommended_fields": missing_recommended,
        "missing_required_tools": missing_required_tools,
        "missing_research_tools": prereqs.get("recommended_research_tools", []),
    }

    # Add error or warning message
    if should_block:
        result["error_message"] = prereqs.get("error_message", "Required data missing")
    elif prereqs.get("warning_message"):
        result["warning_message"] = prereqs.get("warning_message")

    return result
