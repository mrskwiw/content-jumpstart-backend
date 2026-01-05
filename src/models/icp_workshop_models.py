"""ICP Workshop Data Models

Structured models for Ideal Customer Profile development through
guided conversational workshop.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Demographics(BaseModel):
    """Demographic/firmographic profile"""

    company_size: Optional[str] = Field(None, description="Company size (e.g., '10-50 employees')")
    industry: Optional[str] = Field(None, description="Primary industry")
    revenue_range: Optional[str] = Field(None, description="Annual revenue range")
    location: Optional[str] = Field(None, description="Geographic location")
    team_structure: Optional[str] = Field(None, description="Team organization")
    technologies_used: List[str] = Field(
        default_factory=list, description="Technologies/tools they use"
    )
    job_titles: List[str] = Field(
        default_factory=list, description="Decision-maker job titles"
    )


class Psychographics(BaseModel):
    """Psychological and behavioral characteristics"""

    goals: List[str] = Field(default_factory=list, description="Primary goals and objectives")
    challenges: List[str] = Field(
        default_factory=list, description="Challenges and frustrations"
    )
    values: List[str] = Field(default_factory=list, description="Core values and priorities")
    decision_factors: List[str] = Field(
        default_factory=list, description="Factors influencing decisions"
    )
    aspirations: Optional[str] = Field(None, description="What they aspire to become")


class Behavioral(BaseModel):
    """Behavioral patterns and habits"""

    buying_process: Optional[str] = Field(None, description="How they make buying decisions")
    content_consumption: List[str] = Field(
        default_factory=list, description="Content types they consume"
    )
    research_habits: Optional[str] = Field(None, description="How they research solutions")
    influencers: List[str] = Field(
        default_factory=list, description="Influencers or sources they trust"
    )
    platforms_active_on: List[str] = Field(
        default_factory=list, description="Platforms where they're active"
    )


class Situational(BaseModel):
    """Situational and contextual factors"""

    pain_triggers: List[str] = Field(
        default_factory=list, description="Events that trigger pain points"
    )
    timing_seasonality: Optional[str] = Field(
        None, description="Timing and seasonal factors"
    )
    budget_constraints: Optional[str] = Field(None, description="Budget limitations")
    competitive_pressures: List[str] = Field(
        default_factory=list, description="Competitive pressures they face"
    )
    current_solutions: Optional[str] = Field(
        None, description="Solutions they currently use"
    )


class SuccessCriteria(BaseModel):
    """How the ideal customer defines and measures success"""

    definition_of_success: Optional[str] = Field(
        None, description="How they define success"
    )
    kpis_tracked: List[str] = Field(default_factory=list, description="KPIs they track")
    roi_expectations: Optional[str] = Field(None, description="ROI expectations")
    implementation_timeline: Optional[str] = Field(
        None, description="Expected implementation timeline"
    )
    success_indicators: List[str] = Field(
        default_factory=list, description="Indicators of successful outcome"
    )


class IdealCustomerProfile(BaseModel):
    """Complete Ideal Customer Profile"""

    # Meta
    profile_name: str = Field(..., description="Name/label for this ICP")
    created_date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d"),
        description="Creation date",
    )
    business_name: Optional[str] = Field(None, description="Business this ICP is for")

    # Core Profile Sections
    demographics: Demographics = Field(
        default_factory=Demographics, description="Demographic/firmographic data"
    )
    psychographics: Psychographics = Field(
        default_factory=Psychographics, description="Psychological characteristics"
    )
    behavioral: Behavioral = Field(
        default_factory=Behavioral, description="Behavioral patterns"
    )
    situational: Situational = Field(
        default_factory=Situational, description="Situational factors"
    )
    success_criteria: SuccessCriteria = Field(
        default_factory=SuccessCriteria, description="Success definition"
    )

    # Synthesis
    one_sentence_summary: Optional[str] = Field(
        None, description="One-sentence ICP summary"
    )
    key_insights: List[str] = Field(
        default_factory=list, description="Key insights from the profile"
    )
    messaging_recommendations: List[str] = Field(
        default_factory=list, description="Recommended messaging angles"
    )
    content_topics: List[str] = Field(
        default_factory=list, description="Recommended content topics"
    )


class ICPWorkshopAnalysis(BaseModel):
    """Complete ICP Workshop output"""

    profile: IdealCustomerProfile = Field(..., description="The completed ICP")
    workshop_notes: Optional[str] = Field(None, description="Notes from workshop session")
    conversation_summary: Optional[str] = Field(
        None, description="Summary of conversation"
    )
    next_steps: List[str] = Field(
        default_factory=list, description="Recommended next steps"
    )
