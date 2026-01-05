"""Story Mining Data Models

Structured models for extracting customer success stories and
case study material through guided interview process.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CustomerBackground(BaseModel):
    """Customer background and context"""

    customer_name: Optional[str] = Field(None, description="Customer/company name")
    industry: Optional[str] = Field(None, description="Industry vertical")
    company_size: Optional[str] = Field(None, description="Company size")
    role_title: Optional[str] = Field(None, description="Customer's role/title")
    starting_situation: Optional[str] = Field(
        None, description="Situation before using the solution"
    )
    key_responsibilities: List[str] = Field(
        default_factory=list, description="Key responsibilities"
    )


class Challenge(BaseModel):
    """Problem and pain points"""

    problem_description: str = Field(..., description="Main problem description")
    impact_on_business: Optional[str] = Field(
        None, description="How problem impacted business"
    )
    urgency_level: Optional[str] = Field(None, description="Why urgent")
    failed_attempts: List[str] = Field(
        default_factory=list, description="Previous failed attempts"
    )
    pain_points: List[str] = Field(default_factory=list, description="Specific pain points")
    cost_of_inaction: Optional[str] = Field(
        None, description="What would happen if problem not solved"
    )


class DecisionProcess(BaseModel):
    """How they decided on this solution"""

    why_chose_solution: str = Field(..., description="Why chose this solution")
    alternatives_considered: List[str] = Field(
        default_factory=list, description="Other options considered"
    )
    key_decision_factors: List[str] = Field(
        default_factory=list, description="Key factors in decision"
    )
    decision_timeline: Optional[str] = Field(None, description="How long to decide")
    stakeholders_involved: List[str] = Field(
        default_factory=list, description="Who was involved in decision"
    )
    concerns_overcome: List[str] = Field(
        default_factory=list, description="Concerns that had to be overcome"
    )


class Implementation(BaseModel):
    """Implementation journey"""

    getting_started: Optional[str] = Field(None, description="How they got started")
    implementation_timeline: Optional[str] = Field(
        None, description="Timeline from start to results"
    )
    key_milestones: List[str] = Field(default_factory=list, description="Key milestones")
    obstacles_overcome: List[str] = Field(
        default_factory=list, description="Obstacles and how overcome"
    )
    surprises_discoveries: List[str] = Field(
        default_factory=list, description="Unexpected discoveries"
    )
    support_needed: Optional[str] = Field(None, description="Support they needed")


class Results(BaseModel):
    """Outcomes and achievements"""

    quantitative_results: List[str] = Field(
        default_factory=list, description="Measurable outcomes (with numbers)"
    )
    qualitative_improvements: List[str] = Field(
        default_factory=list, description="Qualitative improvements"
    )
    roi_metrics: Optional[str] = Field(None, description="ROI or cost savings")
    time_savings: Optional[str] = Field(None, description="Time saved")
    before_after_comparison: Optional[str] = Field(
        None, description="Before vs after comparison"
    )
    unexpected_benefits: List[str] = Field(
        default_factory=list, description="Unexpected positive outcomes"
    )


class Testimonials(BaseModel):
    """Customer quotes and testimonials"""

    headline_quote: Optional[str] = Field(
        None, description="Main pull quote for case study"
    )
    detailed_quotes: List[str] = Field(
        default_factory=list, description="Detailed customer quotes"
    )
    specific_wins: List[str] = Field(
        default_factory=list, description="Specific wins in customer's words"
    )
    would_recommend: Optional[str] = Field(
        None, description="Would they recommend? Why?"
    )
    advice_for_others: Optional[str] = Field(
        None, description="Advice for others considering"
    )


class FuturePlans(BaseModel):
    """Future plans and ongoing success"""

    ongoing_success: Optional[str] = Field(
        None, description="How success continues"
    )
    next_goals: List[str] = Field(default_factory=list, description="Next goals")
    long_term_vision: Optional[str] = Field(None, description="Long-term plans")
    expansion_plans: Optional[str] = Field(
        None, description="Plans to expand usage"
    )


class SuccessStory(BaseModel):
    """Complete customer success story"""

    # Meta
    story_title: str = Field(..., description="Story title")
    created_date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d"),
        description="Creation date",
    )
    business_name: Optional[str] = Field(None, description="Business this story is for")

    # Story Sections
    customer_background: CustomerBackground = Field(
        default_factory=CustomerBackground, description="Customer background"
    )
    challenge: Challenge = Field(..., description="Challenge faced")
    decision_process: DecisionProcess = Field(..., description="Decision process")
    implementation: Implementation = Field(
        default_factory=Implementation, description="Implementation journey"
    )
    results: Results = Field(default_factory=Results, description="Results achieved")
    testimonials: Testimonials = Field(
        default_factory=Testimonials, description="Customer testimonials"
    )
    future_plans: FuturePlans = Field(
        default_factory=FuturePlans, description="Future plans"
    )

    # Synthesis
    one_sentence_summary: Optional[str] = Field(
        None, description="One-sentence story summary"
    )
    key_takeaways: List[str] = Field(
        default_factory=list, description="Key takeaways from story"
    )
    use_cases: List[str] = Field(
        default_factory=list, description="Use cases this story demonstrates"
    )


class StoryMiningAnalysis(BaseModel):
    """Complete story mining output"""

    story: SuccessStory = Field(..., description="The complete success story")
    interview_notes: Optional[str] = Field(None, description="Notes from interview")
    content_recommendations: List[str] = Field(
        default_factory=list, description="Recommended content to create from this story"
    )
    social_proof_snippets: List[str] = Field(
        default_factory=list, description="Short snippets for social proof"
    )
    case_study_outline: Optional[str] = Field(
        None, description="Case study structure outline"
    )
