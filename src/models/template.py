"""Post template data models and structures"""
from enum import Enum
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field


class TemplateDifficulty(str, Enum):
    """Template difficulty/time to fill"""

    FAST = "fast"  # 3-5 min
    MEDIUM = "medium"  # 6-8 min
    SLOW = "slow"  # 9-12 min


class TemplateType(str, Enum):
    """Template category"""

    PROBLEM_RECOGNITION = "problem_recognition"
    STATISTIC = "statistic"
    CONTRARIAN = "contrarian"
    EVOLUTION = "evolution"
    QUESTION = "question"
    STORY = "story"
    MYTH_BUSTING = "myth_busting"
    VULNERABILITY = "vulnerability"
    HOW_TO = "how_to"
    COMPARISON = "comparison"
    LEARNING = "learning"
    BEHIND_SCENES = "behind_scenes"
    FUTURE = "future"
    Q_AND_A = "q_and_a"
    MILESTONE = "milestone"


class Template(BaseModel):
    """A post template from the library"""

    # Identification
    template_id: int = Field(..., description="Template number (1-15)")
    name: str = Field(..., description="Template name")
    template_type: TemplateType = Field(..., description="Template category")

    # Content
    structure: str = Field(..., description="Template structure with [BRACKETS]")
    example: Optional[str] = Field(None, description="Example post")

    # Metadata
    best_for: str = Field(..., description="What this template is best for")
    difficulty: TemplateDifficulty = Field(..., description="Time/difficulty to fill")

    # Requirements
    requires_story: bool = Field(False, description="Needs client story")
    requires_data: bool = Field(False, description="Needs statistics/data")
    requires_question: bool = Field(False, description="Needs real customer question")

    # Brackets
    placeholder_fields: List[str] = Field(
        default_factory=list, description="List of [BRACKET] fields to fill"
    )

    def get_required_context_fields(self) -> List[str]:
        """Get list of required context fields from brief"""
        required = ["company_name", "ideal_customer", "problem_solved", "brand_voice"]

        if self.requires_story:
            required.append("stories")
        if self.requires_data:
            required.append("statistics")
        if self.requires_question:
            required.append("customer_questions")

        return required

    def can_be_filled(self, client_brief) -> Tuple[bool, List[str]]:
        """Check if template can be filled with available brief data"""
        missing = []

        if self.requires_story and not client_brief.stories:
            missing.append("client stories")
        if self.requires_question and not client_brief.customer_questions:
            missing.append("customer questions")

        can_fill = len(missing) == 0
        return can_fill, missing
