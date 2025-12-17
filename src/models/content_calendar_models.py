"""Data models for content calendar strategy"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ContentPillar(str, Enum):
    """Core content themes"""

    EDUCATION = "education"  # How-to, tutorials, guides
    THOUGHT_LEADERSHIP = "thought_leadership"  # Industry insights, opinions
    CASE_STUDIES = "case_studies"  # Success stories, testimonials
    PRODUCT = "product"  # Features, updates, demos
    COMMUNITY = "community"  # User-generated, behind-scenes
    INDUSTRY_NEWS = "industry_news"  # Trends, news commentary
    ENTERTAINMENT = "entertainment"  # Engaging, shareable content


class PostingFrequency(str, Enum):
    """How often to post"""

    DAILY = "daily"
    THREE_PER_WEEK = "3x_per_week"
    TWICE_WEEKLY = "2x_per_week"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"


class ContentGoal(str, Enum):
    """Primary goals for content"""

    AWARENESS = "awareness"  # Reach new audience
    ENGAGEMENT = "engagement"  # Build community
    LEADS = "leads"  # Generate leads
    EDUCATION = "education"  # Teach audience
    RETENTION = "retention"  # Keep customers engaged
    THOUGHT_LEADERSHIP = "thought_leadership"  # Build authority


class CalendarWeek(BaseModel):
    """One week in the content calendar"""

    week_number: int = Field(..., description="Week number (1-13 for 90 days)")
    start_date: str = Field(..., description="Week start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Week end date (YYYY-MM-DD)")

    # Content plan
    theme: str = Field(..., description="Weekly theme or focus")
    pillar: ContentPillar = Field(..., description="Primary content pillar")
    post_count: int = Field(..., description="Number of posts this week")

    # Post ideas
    post_ideas: List[str] = Field(
        default_factory=list, description="Specific post ideas for this week (3-5 items)"
    )

    # Strategic notes
    goal: ContentGoal = Field(..., description="Primary goal for this week")
    key_message: str = Field(..., description="Core message to communicate")
    cta_focus: str = Field(..., description="Call-to-action focus")

    # Special considerations
    holidays_events: List[str] = Field(
        default_factory=list, description="Holidays or events this week to leverage"
    )
    notes: Optional[str] = Field(None, description="Additional notes or considerations")


class ContentTheme(BaseModel):
    """Monthly or quarterly content theme"""

    name: str = Field(..., description="Theme name")
    description: str = Field(..., description="Theme description")
    pillars: List[ContentPillar] = Field(
        default_factory=list, description="Content pillars used in this theme"
    )
    weeks: List[int] = Field(default_factory=list, description="Week numbers covered by this theme")
    goal: ContentGoal = Field(..., description="Primary goal for this theme")


class PlatformCalendar(BaseModel):
    """Platform-specific calendar details"""

    platform: str = Field(..., description="Platform name (LinkedIn, Twitter, etc.)")
    frequency: PostingFrequency = Field(..., description="Posting frequency")
    best_days: List[str] = Field(
        default_factory=list,
        description="Best days to post (e.g., ['Monday', 'Wednesday', 'Friday'])",
    )
    best_times: List[str] = Field(
        default_factory=list, description="Best times to post (e.g., ['9:00 AM', '3:00 PM'])"
    )
    content_mix: str = Field(..., description="Recommended content mix for this platform")


class CalendarStrategy(BaseModel):
    """Complete 90-day content calendar strategy"""

    business_name: str = Field(..., description="Client business name")
    industry: str = Field(..., description="Industry/vertical")
    target_audience: str = Field(..., description="Primary audience")
    strategy_start_date: str = Field(..., description="Calendar start date (YYYY-MM-DD)")
    analysis_date: str = Field(..., description="Date of analysis")

    # Executive summary
    executive_summary: str = Field(..., description="High-level calendar strategy")
    primary_goals: List[ContentGoal] = Field(
        default_factory=list, description="Top 3 content goals for 90 days"
    )

    # Content structure
    content_pillars: List[ContentPillar] = Field(
        default_factory=list, description="4-6 content pillars to rotate through"
    )
    pillar_rationale: str = Field(..., description="Why these pillars were chosen")

    # Themes
    themes: List[ContentTheme] = Field(
        default_factory=list, description="3 monthly or quarterly themes"
    )

    # Weekly calendar
    weekly_calendar: List[CalendarWeek] = Field(
        default_factory=list, description="13 weeks of detailed content planning"
    )

    # Platform recommendations
    platform_calendars: List[PlatformCalendar] = Field(
        default_factory=list, description="Platform-specific posting schedules"
    )

    # Posting strategy
    recommended_frequency: PostingFrequency = Field(..., description="Overall posting frequency")
    total_posts_90_days: int = Field(..., description="Total posts planned for 90 days")
    content_mix: str = Field(
        ...,
        description="Overall content mix (e.g., '40% education, 30% thought leadership, 20% case studies, 10% product')",
    )

    # Seasonal opportunities
    seasonal_opportunities: List[str] = Field(
        default_factory=list, description="Holidays, events, seasons to leverage (5-10 items)"
    )

    # Implementation guidance
    quick_start_actions: List[str] = Field(
        default_factory=list, description="First 5 actions to implement calendar (Week 1)"
    )

    content_creation_workflow: str = Field(
        ..., description="Recommended workflow for creating content"
    )

    batch_creation_tips: List[str] = Field(
        default_factory=list, description="Tips for batching content creation (3-5 items)"
    )

    # Success metrics
    success_metrics: List[str] = Field(
        default_factory=list, description="KPIs to track (5-7 metrics)"
    )

    review_schedule: str = Field(..., description="When and how to review calendar performance")

    # Strategic insights
    key_insights: List[str] = Field(
        default_factory=list, description="Strategic insights about content planning (3-5 items)"
    )

    common_pitfalls: List[str] = Field(
        default_factory=list, description="Calendar mistakes to avoid (3-5 items)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "business_name": "Acme Corp",
                "industry": "B2B SaaS",
                "target_audience": "Marketing managers",
                "strategy_start_date": "2025-01-01",
                "primary_goals": ["awareness", "leads", "thought_leadership"],
                "content_pillars": ["education", "thought_leadership", "case_studies"],
                "recommended_frequency": "3x_per_week",
                "total_posts_90_days": 39,
            }
        }
