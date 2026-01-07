"""Content Calendar Strategy research tool

Creates a strategic 90-day content calendar with weekly planning,
content pillars, themes, and platform-specific schedules.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from src.models.content_calendar_models import (
    CalendarStrategy,
    CalendarWeek,
    ContentGoal,
    ContentPillar,
    ContentTheme,
    PlatformCalendar,
    PostingFrequency,
)
from src.research.base import ResearchTool
from src.research.validation_mixin import CommonValidationMixin
from src.validators.research_input_validator import ResearchInputValidator


class ContentCalendarStrategist(ResearchTool, CommonValidationMixin):
    """Generate strategic 90-day content calendar"""

    def __init__(self, project_id: str, config: Dict[str, Any] = None):
        """Initialize Content Calendar Strategist with input validator"""
        super().__init__(project_id, config)
        self.validator = ResearchInputValidator(strict_mode=False)

    @property
    def tool_name(self) -> str:
        return "content_calendar_strategy"

    @property
    def price(self) -> int:
        return 300

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """
        Validate required inputs with comprehensive security checks

        Security improvements:
        - Max length validation (prevent DOS)
        - Prompt injection sanitization
        - Type validation
        - Field presence checks
        """
        # SECURITY: Validate business description with sanitization
        inputs["business_description"] = self.validate_business_description(inputs)

        # SECURITY: Validate target audience with sanitization
        inputs["target_audience"] = self.validate_target_audience(inputs, min_length=20)

        # SECURITY: Validate optional business name
        if "business_name" in inputs and inputs["business_name"]:
            inputs["business_name"] = self.validator.validate_text(
                inputs.get("business_name"),
                field_name="business_name",
                min_length=2,
                max_length=200,
                required=False,
                sanitize=True,
            )

        # SECURITY: Validate optional industry
        if "industry" in inputs and inputs["industry"]:
            inputs["industry"] = self.validator.validate_text(
                inputs.get("industry"),
                field_name="industry",
                min_length=2,
                max_length=200,
                required=False,
                sanitize=True,
            )

        # SECURITY: Validate optional content goals
        if "content_goals" in inputs and inputs["content_goals"]:
            inputs["content_goals"] = self.validator.validate_text(
                inputs.get("content_goals"),
                field_name="content_goals",
                min_length=10,
                max_length=1000,
                required=False,
                sanitize=True,
            )

        # SECURITY: Validate optional primary platforms list
        if "primary_platforms" in inputs and inputs["primary_platforms"]:
            inputs["primary_platforms"] = self.validator.validate_list(
                inputs.get("primary_platforms"),
                field_name="primary_platforms",
                max_items=10,
                item_validator=lambda x: self.validator.validate_text(
                    x,
                    field_name="platform_name",
                    min_length=2,
                    max_length=100,
                    required=False,
                    sanitize=True,
                ),
            )

        # SECURITY: Validate optional start date
        if "start_date" in inputs and inputs["start_date"]:
            inputs["start_date"] = self.validator.validate_text(
                inputs.get("start_date"),
                field_name="start_date",
                min_length=8,
                max_length=20,
                required=False,
                sanitize=True,
            )

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> CalendarStrategy:
        """Execute content calendar strategy analysis

        Args:
            inputs: Dictionary containing:
                - business_description: str (required)
                - target_audience: str (required)
                - business_name: str (optional)
                - industry: str (optional)
                - primary_platforms: List[str] (optional)
                - content_goals: str (optional)
                - start_date: str (optional, YYYY-MM-DD format)

        Returns:
            CalendarStrategy object with complete 90-day plan
        """
        # Extract inputs
        business_description = inputs["business_description"]
        target_audience = inputs["target_audience"]
        business_name = inputs.get("business_name", "Client Business")
        industry = inputs.get("industry", "Not specified")
        platforms = inputs.get("primary_platforms", ["LinkedIn"])
        content_goals = inputs.get("content_goals", "Brand awareness and engagement")
        start_date_str = inputs.get("start_date", self._get_next_monday().strftime("%Y-%m-%d"))

        # Get Anthropic client
        print("[Step 1/6] Analyzing business and audience for calendar planning...")
        # Step 1: Determine content pillars
        pillars = self._determine_content_pillars(
            client, business_description, target_audience, content_goals
        )

        print("[Step 2/6] Creating quarterly content themes...")
        # Step 2: Create quarterly themes
        themes = self._create_quarterly_themes(
            client, pillars, business_description, target_audience, content_goals
        )

        print("[Step 3/6] Building 13-week detailed calendar...")
        # Step 3: Generate weekly calendar
        weekly_calendar = self._generate_weekly_calendar(
            client, start_date_str, themes, pillars, business_description, target_audience
        )

        print("[Step 4/6] Determining platform-specific schedules...")
        # Step 4: Create platform calendars
        platform_calendars = self._create_platform_calendars(
            client, platforms, business_description, target_audience
        )

        print("[Step 5/6] Generating implementation guidance...")
        # Step 5: Generate implementation guidance
        implementation = self._generate_implementation_guidance(
            client, business_description, target_audience, weekly_calendar
        )

        print("[Step 6/6] Compiling final calendar strategy...")
        # Step 6: Compile final strategy
        calendar_strategy = self._compile_calendar_strategy(
            business_name=business_name,
            industry=industry,
            target_audience=target_audience,
            start_date=start_date_str,
            pillars=pillars,
            themes=themes,
            weekly_calendar=weekly_calendar,
            platform_calendars=platform_calendars,
            implementation=implementation,
            content_goals=content_goals,
        )

        return calendar_strategy

    def _get_next_monday(self) -> datetime:
        """Get the next Monday from today"""
        today = datetime.now()
        days_ahead = 0 - today.weekday()  # Monday is 0
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return today + timedelta(days=days_ahead)

    def _determine_content_pillars(
        self, client: Any, business_description: str, target_audience: str, content_goals: str
    ) -> List[Dict[str, Any]]:
        """Determine 4-6 content pillars"""
        prompt = f"""Based on this business and audience, determine 4-6 core content pillars.

Business: {business_description}
Target Audience: {target_audience}
Content Goals: {content_goals}

Content pillars are the main themes that content will focus on. They should:
1. Align with business value and audience needs
2. Support the content goals
3. Provide variety and cover different aspects
4. Be specific enough to guide content creation

Available pillar types: education, thought_leadership, case_studies, product, community, industry_news, entertainment

Return JSON array with 4-6 pillars:
[
  {{
    "pillar": "education",
    "description": "How the pillar supports goals",
    "topics": ["topic 1", "topic 2", "topic 3"],
    "percentage": 30
  }},
  ...
]

Percentages should add up to 100."""

        # Call Claude API with automatic JSON extraction (Phase 3 deduplication)
        data = self._call_claude_api(
            prompt, max_tokens=2000, temperature=0.4, extract_json=True, fallback_on_error={}
        )

        return data

    def _create_quarterly_themes(
        self,
        client: Any,
        pillars: List[Dict[str, Any]],
        business_description: str,
        target_audience: str,
        content_goals: str,
    ) -> List[ContentTheme]:
        """Create 3 monthly themes for 90 days"""
        pillars_str = json.dumps(pillars, indent=2)

        prompt = f"""Create 3 monthly content themes for a 90-day calendar (Month 1, Month 2, Month 3).

Business: {business_description}
Target Audience: {target_audience}
Content Goals: {content_goals}

Content Pillars:
{pillars_str}

Each theme should:
1. Cover approximately 4 weeks
2. Use 2-3 of the content pillars
3. Have a clear goal and narrative arc
4. Build on the previous theme

IMPORTANT - Use ONLY these exact values:
- "pillars" must contain values from: education, thought_leadership, case_studies, product, community, industry_news, entertainment
- "goal" must be one of: awareness, engagement, leads, education, retention, thought_leadership

Return JSON array with 3 themes:
[
  {{
    "name": "Theme name",
    "description": "What this theme covers and why",
    "pillars": ["education", "thought_leadership"],
    "weeks": [1, 2, 3, 4],
    "goal": "awareness"
  }},
  ...
]"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2000
        )

        themes_data = self._extract_json_from_response(response)

        return [
            ContentTheme(
                name=theme["name"],
                description=theme["description"],
                pillars=[
                    ContentPillar(self._normalize_pillar(p)) for p in theme.get("pillars", [])
                ],
                weeks=theme.get("weeks", []),
                goal=ContentGoal(self._normalize_goal(theme.get("goal", "awareness"))),
            )
            for theme in themes_data
        ]

    def _normalize_goal(self, goal_value: str) -> str:
        """Normalize goal values to valid ContentGoal enum values

        Handles composite goals (e.g., 'education_+_credibility'), variations,
        and special characters.
        """
        # Clean the input
        goal_lower = goal_value.lower().strip()

        # Remove special characters and split on common separators
        # Handle cases like "education_+_credibility" or "awareness & leads"
        for separator in ["+", "&", "/", "|", ",", "_and_"]:
            if separator in goal_lower:
                # Take the first goal from composite
                goal_lower = goal_lower.split(separator)[0].strip()
                break

        # Remove remaining special characters and normalize spaces to underscores
        goal_lower = goal_lower.replace(" ", "_")
        goal_lower = "".join(c for c in goal_lower if c.isalnum() or c == "_")

        # Map common variations to valid enum values
        goal_mappings = {
            "authority_building": "thought_leadership",
            "authority": "thought_leadership",
            "credibility": "thought_leadership",
            "brand_awareness": "awareness",
            "build_awareness": "awareness",  # e.g., "build_awareness_and_..."
            "problem_awareness": "awareness",  # e.g., "problem_awareness"
            "consideration": "engagement",  # Marketing funnel stage
            "community_building": "engagement",
            "lead_generation": "leads",
            "lead_gen": "leads",
            "customer_retention": "retention",
            "learning": "education",
            "teaching": "education",
        }

        # Try to map, otherwise try last word, otherwise default to awareness
        mapped = goal_mappings.get(goal_lower)
        if mapped:
            return mapped

        # If no mapping found, check if it's a valid goal already
        valid_goals = {
            "awareness",
            "engagement",
            "leads",
            "education",
            "retention",
            "thought_leadership",
        }
        if goal_lower in valid_goals:
            return goal_lower

        # Last resort: take the last word and see if it matches
        last_word = goal_lower.split("_")[-1] if "_" in goal_lower else goal_lower
        if last_word in valid_goals:
            return last_word

        # Final fallback: default to awareness
        return "awareness"

    def _normalize_pillar(self, pillar_value: str) -> str:
        """Normalize pillar values to valid ContentPillar enum values

        Handles variations and special characters.
        """
        # Clean the input
        pillar_lower = pillar_value.lower().strip()

        # Remove special characters and split on common separators
        for separator in ["+", "&", "/", "|", ","]:
            if separator in pillar_lower:
                # Take the first pillar from composite
                pillar_lower = pillar_lower.split(separator)[0].strip()
                break

        # Remove remaining special characters and normalize spaces to underscores
        pillar_lower = pillar_lower.replace(" ", "_")
        pillar_lower = "".join(c for c in pillar_lower if c.isalnum() or c == "_")

        # Map common variations to valid enum values
        pillar_mappings = {
            "tactical": "education",  # tactical content → education
            "how_to": "education",
            "tutorial": "education",
            "tips": "education",
            "thought_leader": "thought_leadership",
            "opinion": "thought_leadership",
            "insights": "thought_leadership",
            "case_study": "case_studies",
            "success_stories": "case_studies",
            "testimonials": "case_studies",
            "features": "product",
            "updates": "product",
            "news": "industry_news",
            "trends": "industry_news",
            "fun": "entertainment",
            "engaging": "entertainment",
        }

        # Try to map, otherwise return cleaned value
        return pillar_mappings.get(pillar_lower, pillar_lower)

    def _generate_weekly_calendar(
        self,
        client: Any,
        start_date_str: str,
        themes: List[ContentTheme],
        pillars: List[Dict[str, Any]],
        business_description: str,
        target_audience: str,
    ) -> List[CalendarWeek]:
        """Generate 13 weeks of detailed content calendar"""
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        weekly_calendar = []

        # Generate calendar in batches (4-5 weeks at a time to fit in context)
        for batch_start in range(0, 13, 4):
            batch_end = min(batch_start + 4, 13)
            weeks_in_batch = list(range(batch_start + 1, batch_end + 1))

            # Find which theme covers these weeks
            theme_context = []
            for theme in themes:
                for week_num in weeks_in_batch:
                    if week_num in theme.weeks:
                        theme_context.append(f"Week {week_num}: {theme.name} - {theme.description}")
                        break

            theme_context_str = (
                "\n".join(theme_context) if theme_context else "General content planning"
            )

            prompt = f"""Create detailed weekly content plans for weeks {weeks_in_batch[0]}-{weeks_in_batch[-1]} of a 90-day calendar.

Business: {business_description}
Target Audience: {target_audience}

Theme Context:
{theme_context_str}

For each week, provide:
1. Weekly theme/focus (specific topic within the monthly theme)
2. Primary content pillar to use
3. Number of posts (3-5 posts per week)
4. 3-5 specific post ideas
5. Primary goal for the week
6. Key message to communicate
7. CTA focus (what action to drive)
8. Any holidays or events to leverage

IMPORTANT - Use ONLY these exact values:
- "pillar" must be one of: education, thought_leadership, case_studies, product, community, industry_news, entertainment
- "goal" must be one of: awareness, engagement, leads, education, retention, thought_leadership

Return JSON array for weeks {weeks_in_batch}:
[
  {{
    "week_number": 1,
    "theme": "Week-specific theme",
    "pillar": "education",
    "post_count": 4,
    "post_ideas": ["Idea 1", "Idea 2", "Idea 3", "Idea 4"],
    "goal": "awareness",
    "key_message": "Core message",
    "cta_focus": "What to ask audience to do",
    "holidays_events": ["Event if applicable"],
    "notes": "Optional notes"
  }},
  ...
]"""

            response = client.create_message(
                messages=[{"role": "user", "content": prompt}], max_tokens=3000
            )

            weeks_data = self._extract_json_from_response(response)

            # Convert to CalendarWeek objects
            for week_data in weeks_data:
                week_num = week_data["week_number"]
                week_start = start_date + timedelta(weeks=week_num - 1)
                week_end = week_start + timedelta(days=6)

                # Normalize goal and pillar values before creating enums
                goal_value = self._normalize_goal(week_data.get("goal", "awareness"))
                pillar_value = self._normalize_pillar(week_data.get("pillar", "education"))

                calendar_week = CalendarWeek(
                    week_number=week_num,
                    start_date=week_start.strftime("%Y-%m-%d"),
                    end_date=week_end.strftime("%Y-%m-%d"),
                    theme=week_data.get("theme", ""),
                    pillar=ContentPillar(pillar_value),
                    post_count=week_data.get("post_count", 3),
                    post_ideas=week_data.get("post_ideas", []),
                    goal=ContentGoal(goal_value),
                    key_message=week_data.get("key_message", ""),
                    cta_focus=week_data.get("cta_focus", ""),
                    holidays_events=week_data.get("holidays_events", []),
                    notes=week_data.get("notes"),
                )
                weekly_calendar.append(calendar_week)

        return sorted(weekly_calendar, key=lambda w: w.week_number)

    def _create_platform_calendars(
        self, client: Any, platforms: List[str], business_description: str, target_audience: str
    ) -> List[PlatformCalendar]:
        """Create platform-specific schedules"""
        platforms_str = ", ".join(platforms)

        prompt = f"""Create platform-specific posting schedules for: {platforms_str}

Business: {business_description}
Target Audience: {target_audience}

For each platform, determine:
1. Optimal posting frequency
2. Best days of the week to post
3. Best times to post
4. Recommended content mix

Return JSON array:
[
  {{
    "platform": "LinkedIn",
    "frequency": "3x_per_week",
    "best_days": ["Tuesday", "Wednesday", "Thursday"],
    "best_times": ["9:00 AM", "12:00 PM", "4:00 PM"],
    "content_mix": "40% education, 30% thought leadership, 20% case studies, 10% product"
  }},
  ...
]

Frequency options: daily, 3x_per_week, 2x_per_week, weekly, biweekly"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2000
        )

        calendars_data = self._extract_json_from_response(response)

        return [
            PlatformCalendar(
                platform=cal["platform"],
                frequency=PostingFrequency(cal.get("frequency", "3x_per_week")),
                best_days=cal.get("best_days", []),
                best_times=cal.get("best_times", []),
                content_mix=cal.get("content_mix", ""),
            )
            for cal in calendars_data
        ]

    def _generate_implementation_guidance(
        self,
        client: Any,
        business_description: str,
        target_audience: str,
        weekly_calendar: List[CalendarWeek],
    ) -> Dict[str, Any]:
        """Generate implementation guidance and metrics"""
        total_posts = sum(week.post_count for week in weekly_calendar)

        prompt = f"""Create implementation guidance for a 90-day content calendar.

Business: {business_description}
Target Audience: {target_audience}
Total Posts Planned: {total_posts}

Provide:
1. Quick start actions (5 specific actions for Week 1)
2. Content creation workflow (step-by-step process)
3. Batch creation tips (3-5 tips for efficiency)
4. Success metrics (5-7 KPIs to track)
5. Review schedule (when and how to review performance)
6. Key insights (3-5 strategic insights about content planning)
7. Common pitfalls (3-5 mistakes to avoid)

Return JSON:
{{
  "quick_start_actions": ["Action 1", "Action 2", ...],
  "content_creation_workflow": "Step-by-step workflow description",
  "batch_creation_tips": ["Tip 1", "Tip 2", ...],
  "success_metrics": ["Metric 1", "Metric 2", ...],
  "review_schedule": "When and how to review",
  "key_insights": ["Insight 1", "Insight 2", ...],
  "common_pitfalls": ["Pitfall 1", "Pitfall 2", ...]
}}"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,  # Increased for implementation guidance
        )

        return data

    def _compile_calendar_strategy(
        self,
        business_name: str,
        industry: str,
        target_audience: str,
        start_date: str,
        pillars: List[Dict[str, Any]],
        themes: List[ContentTheme],
        weekly_calendar: List[CalendarWeek],
        platform_calendars: List[PlatformCalendar],
        implementation: Dict[str, Any],
        content_goals: str,
    ) -> CalendarStrategy:
        """Compile all components into final strategy"""
        # Extract primary goals from content_goals string
        goal_keywords = {
            "awareness": ContentGoal.AWARENESS,
            "engagement": ContentGoal.ENGAGEMENT,
            "lead": ContentGoal.LEADS,
            "education": ContentGoal.EDUCATION,
            "retention": ContentGoal.RETENTION,
            "thought leadership": ContentGoal.THOUGHT_LEADERSHIP,
        }

        primary_goals = []
        goals_lower = content_goals.lower()
        for keyword, goal in goal_keywords.items():
            if keyword in goals_lower and len(primary_goals) < 3:
                primary_goals.append(goal)

        if not primary_goals:
            primary_goals = [ContentGoal.AWARENESS, ContentGoal.ENGAGEMENT]

        # Extract content pillars with normalization
        content_pillars_enum = [ContentPillar(self._normalize_pillar(p["pillar"])) for p in pillars]

        # Calculate total posts
        total_posts = sum(week.post_count for week in weekly_calendar)

        # Determine recommended frequency
        avg_posts_per_week = total_posts / len(weekly_calendar)
        if avg_posts_per_week >= 5:
            frequency = PostingFrequency.DAILY
        elif avg_posts_per_week >= 3:
            frequency = PostingFrequency.THREE_PER_WEEK
        elif avg_posts_per_week >= 2:
            frequency = PostingFrequency.TWICE_WEEKLY
        else:
            frequency = PostingFrequency.WEEKLY

        # Build content mix string
        content_mix_parts = [f"{p['percentage']}% {p['pillar']}" for p in pillars]
        content_mix = ", ".join(content_mix_parts)

        # Extract pillar rationale
        pillar_rationale = (
            "Selected pillars align with business goals and audience interests. "
            + " ".join(
                [
                    f"{p['pillar'].replace('_', ' ').title()}: {p['description']}"
                    for p in pillars[:2]
                ]
            )
        )

        # Generate executive summary
        executive_summary = f"""This 90-day content calendar provides a strategic roadmap for {business_name}'s content marketing from {start_date} onwards.
The calendar focuses on {', '.join([g.value for g in primary_goals[:2]])} through {len(content_pillars_enum)} core content pillars.
With {total_posts} posts planned across {len(weekly_calendar)} weeks, the strategy balances consistency with quality,
using a {frequency.value.replace('_', ' ')} posting rhythm."""

        # Collect seasonal opportunities from weekly calendar
        seasonal_opportunities = []
        for week in weekly_calendar:
            seasonal_opportunities.extend(week.holidays_events)
        seasonal_opportunities = list(set(seasonal_opportunities))[:10]  # Unique, max 10

        return CalendarStrategy(
            business_name=business_name,
            industry=industry,
            target_audience=target_audience,
            strategy_start_date=start_date,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            executive_summary=executive_summary,
            primary_goals=primary_goals,
            content_pillars=content_pillars_enum,
            pillar_rationale=pillar_rationale,
            themes=themes,
            weekly_calendar=weekly_calendar,
            platform_calendars=platform_calendars,
            recommended_frequency=frequency,
            total_posts_90_days=total_posts,
            content_mix=content_mix,
            seasonal_opportunities=seasonal_opportunities,
            quick_start_actions=implementation.get("quick_start_actions", []),
            content_creation_workflow=implementation.get("content_creation_workflow", ""),
            batch_creation_tips=implementation.get("batch_creation_tips", []),
            success_metrics=implementation.get("success_metrics", []),
            review_schedule=implementation.get("review_schedule", ""),
            key_insights=implementation.get("key_insights", []),
            common_pitfalls=implementation.get("common_pitfalls", []),
        )

    def generate_reports(self, analysis: CalendarStrategy) -> Dict[str, Path]:
        """Generate calendar strategy reports in multiple formats"""
        calendar_strategy = analysis  # Rename for internal use
        # Get output directory (property already creates it)
        output_dir = self.output_dir

        outputs = {}

        # 1. Save JSON
        json_path = output_dir / "content_calendar_strategy.json"
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(calendar_strategy.model_dump_json(indent=2))
        outputs["json"] = json_path

        # 2. Save Markdown report
        markdown_path = output_dir / "content_calendar_report.md"
        markdown_content = self._generate_markdown_report(calendar_strategy)
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        outputs["markdown"] = markdown_path

        # 3. Save text summary
        text_path = output_dir / "content_calendar_summary.txt"
        text_content = self._generate_text_summary(calendar_strategy)
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        outputs["text"] = text_path

        return outputs

    def _generate_markdown_report(self, strategy: CalendarStrategy) -> str:
        """Generate detailed markdown report"""
        md = f"""# 90-Day Content Calendar Strategy
## {strategy.business_name}

**Industry:** {strategy.industry}
**Target Audience:** {strategy.target_audience}
**Calendar Start Date:** {strategy.strategy_start_date}
**Analysis Date:** {strategy.analysis_date}

---

## Executive Summary

{strategy.executive_summary}

**Primary Goals:** {', '.join([g.value.replace('_', ' ').title() for g in strategy.primary_goals])}

**Total Posts Planned:** {strategy.total_posts_90_days} posts over {len(strategy.weekly_calendar)} weeks

**Recommended Frequency:** {strategy.recommended_frequency.value.replace('_', ' ').title()}

---

## Content Pillars

{strategy.pillar_rationale}

**Content Mix:** {strategy.content_mix}

"""
        for i, pillar in enumerate(strategy.content_pillars, 1):
            md += f"{i}. **{pillar.value.replace('_', ' ').title()}**\n"

        md += "\n---\n\n## Quarterly Themes\n\n"
        for i, theme in enumerate(strategy.themes, 1):
            md += f"### Theme {i}: {theme.name}\n\n"
            md += f"{theme.description}\n\n"
            md += f"- **Pillars:** {', '.join([p.value for p in theme.pillars])}\n"
            md += f"- **Weeks:** {', '.join(map(str, theme.weeks))}\n"
            md += f"- **Goal:** {theme.goal.value.replace('_', ' ').title()}\n\n"

        md += "---\n\n## Weekly Calendar\n\n"
        for week in strategy.weekly_calendar:
            md += f"### Week {week.week_number}: {week.theme}\n"
            md += f"**Dates:** {week.start_date} to {week.end_date}  \n"
            md += f"**Pillar:** {week.pillar.value.replace('_', ' ').title()}  \n"
            md += f"**Posts:** {week.post_count}  \n"
            md += f"**Goal:** {week.goal.value.replace('_', ' ').title()}  \n\n"
            md += f"**Key Message:** {week.key_message}\n\n"
            md += "**Post Ideas:**\n"
            for idea in week.post_ideas:
                md += f"- {idea}\n"
            md += f"\n**CTA Focus:** {week.cta_focus}\n\n"
            if week.holidays_events:
                md += f"**Events/Holidays:** {', '.join(week.holidays_events)}\n\n"
            if week.notes:
                md += f"**Notes:** {week.notes}\n\n"
            md += "---\n\n"

        md += "## Platform-Specific Schedules\n\n"
        for platform in strategy.platform_calendars:
            md += f"### {platform.platform}\n\n"
            md += f"- **Frequency:** {platform.frequency.value.replace('_', ' ').title()}\n"
            md += f"- **Best Days:** {', '.join(platform.best_days)}\n"
            md += f"- **Best Times:** {', '.join(platform.best_times)}\n"
            md += f"- **Content Mix:** {platform.content_mix}\n\n"

        md += "---\n\n## Implementation Guide\n\n"
        md += "### Quick Start Actions (Week 1)\n\n"
        for i, action in enumerate(strategy.quick_start_actions, 1):
            md += f"{i}. {action}\n"

        md += "\n### Content Creation Workflow\n\n"
        md += f"{strategy.content_creation_workflow}\n\n"

        md += "### Batch Creation Tips\n\n"
        for tip in strategy.batch_creation_tips:
            md += f"- {tip}\n"

        md += "\n---\n\n## Success Metrics\n\n"
        md += "Track these KPIs to measure calendar effectiveness:\n\n"
        for metric in strategy.success_metrics:
            md += f"- {metric}\n"

        md += f"\n**Review Schedule:** {strategy.review_schedule}\n\n"

        if strategy.seasonal_opportunities:
            md += "---\n\n## Seasonal Opportunities\n\n"
            md += "Leverage these holidays and events:\n\n"
            for opp in strategy.seasonal_opportunities:
                md += f"- {opp}\n"
            md += "\n"

        md += "---\n\n## Strategic Insights\n\n"
        for insight in strategy.key_insights:
            md += f"- {insight}\n"

        md += "\n## Common Pitfalls to Avoid\n\n"
        for pitfall in strategy.common_pitfalls:
            md += f"- {pitfall}\n"

        md += "\n---\n\n*Calendar generated by Content Calendar Strategy tool ($300)*\n"

        return md

    def _generate_text_summary(self, strategy: CalendarStrategy) -> str:
        """Generate concise text summary"""
        summary = f"""90-DAY CONTENT CALENDAR STRATEGY
{strategy.business_name}
{'=' * 60}

OVERVIEW
--------
Industry: {strategy.industry}
Target Audience: {strategy.target_audience}
Start Date: {strategy.strategy_start_date}
Total Posts: {strategy.total_posts_90_days}
Posting Frequency: {strategy.recommended_frequency.value.replace('_', ' ').title()}

PRIMARY GOALS
-------------
{chr(10).join(['- ' + g.value.replace('_', ' ').title() for g in strategy.primary_goals])}

CONTENT PILLARS
---------------
{chr(10).join(['- ' + p.value.replace('_', ' ').title() for p in strategy.content_pillars])}

Content Mix: {strategy.content_mix}

QUARTERLY THEMES
----------------
"""
        for i, theme in enumerate(strategy.themes, 1):
            summary += f"{i}. {theme.name} (Weeks {', '.join(map(str, theme.weeks))})\n"
            summary += f"   {theme.description}\n\n"

        summary += "\nWEEKLY BREAKDOWN\n"
        summary += "-" * 60 + "\n"
        for week in strategy.weekly_calendar[:4]:  # First 4 weeks as preview
            summary += f"\nWeek {week.week_number}: {week.theme}\n"
            summary += f"  Posts: {week.post_count} | Goal: {week.goal.value}\n"
            summary += f"  Top Ideas: {', '.join(week.post_ideas[:2])}\n"

        summary += f"\n... and {len(strategy.weekly_calendar) - 4} more weeks\n"

        summary += "\nQUICK START ACTIONS\n"
        summary += "-" * 60 + "\n"
        for i, action in enumerate(strategy.quick_start_actions, 1):
            summary += f"{i}. {action}\n"

        summary += "\nSUCCESS METRICS\n"
        summary += "-" * 60 + "\n"
        for metric in strategy.success_metrics:
            summary += f"- {metric}\n"

        return summary

    def _extract_json_from_response(self, text: str) -> Any:
        """Extract JSON from Claude response"""
        import json
        import re

        # Try to parse entire response as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Look for JSON in code blocks first
        json_match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to extract JSON using Python's json decoder (handles nested structures)
        # Find the start of a JSON object or array
        json_start = -1
        for i, char in enumerate(text):
            if char in "{[":
                json_start = i
                break

        if json_start >= 0:
            # Try to parse from this position, the decoder will stop at the end of valid JSON
            try:
                decoder = json.JSONDecoder()
                obj, end_idx = decoder.raw_decode(text, json_start)
                return obj
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not extract JSON from response: {text[:200]}")
