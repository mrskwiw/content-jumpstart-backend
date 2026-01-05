"""ICP Workshop Tool - Interactive Ideal Customer Profile Development

Conversational tool that guides users through building a comprehensive
Ideal Customer Profile through guided questions and Claude-powered analysis.

Price: $600
"""

import json
from pathlib import Path
from typing import Any, Dict

from ..models.icp_workshop_models import (
    Behavioral,
    Demographics,
    ICPWorkshopAnalysis,
    IdealCustomerProfile,
    Psychographics,
    Situational,
    SuccessCriteria,
)
from ..utils.anthropic_client import get_default_client
from .base import ResearchTool


class ICPWorkshopFacilitator(ResearchTool):
    """Interactive ICP development workshop"""

    @property
    def tool_name(self) -> str:
        return "icp_workshop"

    @property
    def price(self) -> int:
        return 600

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate required inputs"""
        required = ["business_description"]

        for field in required:
            if field not in inputs:
                raise ValueError(f"Missing required input: {field}")

        # Validate description length
        if len(inputs["business_description"]) < 50:
            raise ValueError("business_description too short (minimum 50 characters)")

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> ICPWorkshopAnalysis:
        """Execute interactive ICP workshop"""
        business_description = inputs["business_description"]
        business_name = inputs.get("business_name", "Client")
        target_audience = inputs.get("target_audience", "")
        existing_customer_data = inputs.get("existing_customer_data", "")

        client = get_default_client()

        print("[ICP Workshop] Starting interactive profile development...")
        print("[1/6] Analyzing business context...")

        # Step 1: Demographics/Firmographics
        demographics = self._gather_demographics(
            client, business_description, target_audience, existing_customer_data
        )

        print("[2/6] Building psychographic profile...")

        # Step 2: Psychographics
        psychographics = self._gather_psychographics(
            client, business_description, demographics, existing_customer_data
        )

        print("[3/6] Analyzing behavioral patterns...")

        # Step 3: Behavioral
        behavioral = self._gather_behavioral(
            client, business_description, demographics, psychographics
        )

        print("[4/6] Identifying situational factors...")

        # Step 4: Situational
        situational = self._gather_situational(
            client, business_description, demographics, psychographics
        )

        print("[5/6] Defining success criteria...")

        # Step 5: Success Criteria
        success_criteria = self._gather_success_criteria(
            client, business_description, demographics, psychographics
        )

        print("[6/6] Synthesizing insights and recommendations...")

        # Step 6: Synthesis
        (
            one_sentence_summary,
            key_insights,
            messaging_recommendations,
            content_topics,
        ) = self._synthesize_profile(
            client,
            business_name,
            demographics,
            psychographics,
            behavioral,
            situational,
            success_criteria,
        )

        # Build complete profile
        profile = IdealCustomerProfile(
            profile_name=f"{business_name} Ideal Customer",
            business_name=business_name,
            demographics=demographics,
            psychographics=psychographics,
            behavioral=behavioral,
            situational=situational,
            success_criteria=success_criteria,
            one_sentence_summary=one_sentence_summary,
            key_insights=key_insights,
            messaging_recommendations=messaging_recommendations,
            content_topics=content_topics,
        )

        # Generate next steps
        next_steps = self._generate_next_steps(client, profile)

        # Create workshop analysis
        analysis = ICPWorkshopAnalysis(
            profile=profile,
            workshop_notes=f"ICP developed for {business_name}",
            conversation_summary=f"Comprehensive ICP covering demographics, psychographics, behavioral patterns, situational factors, and success criteria.",
            next_steps=next_steps,
        )

        return analysis

    def _gather_demographics(
        self,
        client: Any,
        business_description: str,
        target_audience: str,
        existing_data: str,
    ) -> Demographics:
        """Gather demographic/firmographic data"""
        prompt = f"""You are facilitating an ICP (Ideal Customer Profile) workshop. Based on this business information, determine the demographic/firmographic profile of their ideal customer.

Business: {business_description}
{f'Target Audience: {target_audience}' if target_audience else ''}
{f'Existing Customer Data: {existing_data}' if existing_data else ''}

For the IDEAL customer (not average, but the BEST-FIT customer), provide:

1. Company size (e.g., "10-50 employees", "500-1000 employees", "Enterprise")
2. Industry (specific industry vertical)
3. Revenue range (if applicable for B2B)
4. Location (geographic focus)
5. Team structure (e.g., "Marketing team of 5-10", "Solo founder with contractors")
6. Technologies used (tools/platforms they use)
7. Decision-maker job titles (who makes buying decisions)

Return JSON with these fields:
- company_size: string
- industry: string
- revenue_range: string
- location: string
- team_structure: string
- technologies_used: array of strings
- job_titles: array of strings

Focus on the IDEAL customer, not the average customer."""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=3000
        )

        data = self._extract_json_from_response(response)

        return Demographics(
            company_size=data.get("company_size"),
            industry=data.get("industry"),
            revenue_range=data.get("revenue_range"),
            location=data.get("location"),
            team_structure=data.get("team_structure"),
            technologies_used=data.get("technologies_used", []),
            job_titles=data.get("job_titles", []),
        )

    def _gather_psychographics(
        self,
        client: Any,
        business_description: str,
        demographics: Demographics,
        existing_data: str,
    ) -> Psychographics:
        """Gather psychographic data"""
        prompt = f"""Continue the ICP workshop. Based on the business and demographic profile, determine the psychographic characteristics of the ideal customer.

Business: {business_description}

Demographics:
- Industry: {demographics.industry}
- Company Size: {demographics.company_size}
- Job Titles: {', '.join(demographics.job_titles)}

Analyze the IDEAL customer's psychology:

1. Goals (3-5 primary goals they're trying to achieve)
2. Challenges (3-5 challenges/frustrations they face)
3. Values (3-5 core values and priorities)
4. Decision factors (what influences their buying decisions)
5. Aspirations (what they aspire to become/achieve)

Return JSON with:
- goals: array of strings
- challenges: array of strings
- values: array of strings
- decision_factors: array of strings
- aspirations: string

Focus on deep motivations, not surface-level wants."""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=3000
        )

        data = self._extract_json_from_response(response)

        return Psychographics(
            goals=data.get("goals", []),
            challenges=data.get("challenges", []),
            values=data.get("values", []),
            decision_factors=data.get("decision_factors", []),
            aspirations=data.get("aspirations"),
        )

    def _gather_behavioral(
        self,
        client: Any,
        business_description: str,
        demographics: Demographics,
        psychographics: Psychographics,
    ) -> Behavioral:
        """Gather behavioral patterns"""
        prompt = f"""Continue the ICP workshop. Analyze the behavioral patterns of the ideal customer.

Business: {business_description}
Industry: {demographics.industry}
Goals: {', '.join(psychographics.goals[:3])}

Determine behavioral patterns:

1. Buying process (how they make buying decisions - steps they go through)
2. Content consumption (3-5 types of content they consume)
3. Research habits (how they research solutions)
4. Influencers (3-5 influencers or sources they trust)
5. Platforms active on (where they spend time online)

Return JSON with:
- buying_process: string
- content_consumption: array of strings
- research_habits: string
- influencers: array of strings
- platforms_active_on: array of strings"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2500
        )

        data = self._extract_json_from_response(response)

        return Behavioral(
            buying_process=data.get("buying_process"),
            content_consumption=data.get("content_consumption", []),
            research_habits=data.get("research_habits"),
            influencers=data.get("influencers", []),
            platforms_active_on=data.get("platforms_active_on", []),
        )

    def _gather_situational(
        self,
        client: Any,
        business_description: str,
        demographics: Demographics,
        psychographics: Psychographics,
    ) -> Situational:
        """Gather situational factors"""
        prompt = f"""Continue the ICP workshop. Identify situational and contextual factors.

Business: {business_description}
Challenges: {', '.join(psychographics.challenges[:3])}

Determine situational factors:

1. Pain triggers (3-5 events that trigger their pain points)
2. Timing/seasonality (when they're most likely to buy)
3. Budget constraints (typical budget limitations)
4. Competitive pressures (3-5 competitive pressures they face)
5. Current solutions (what they currently use)

Return JSON with:
- pain_triggers: array of strings
- timing_seasonality: string
- budget_constraints: string
- competitive_pressures: array of strings
- current_solutions: string"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2500
        )

        data = self._extract_json_from_response(response)

        return Situational(
            pain_triggers=data.get("pain_triggers", []),
            timing_seasonality=data.get("timing_seasonality"),
            budget_constraints=data.get("budget_constraints"),
            competitive_pressures=data.get("competitive_pressures", []),
            current_solutions=data.get("current_solutions"),
        )

    def _gather_success_criteria(
        self,
        client: Any,
        business_description: str,
        demographics: Demographics,
        psychographics: Psychographics,
    ) -> SuccessCriteria:
        """Gather success criteria"""
        prompt = f"""Continue the ICP workshop. Define how the ideal customer measures success.

Business: {business_description}
Goals: {', '.join(psychographics.goals[:3])}

Determine success criteria:

1. Definition of success (how they define a successful outcome)
2. KPIs tracked (3-5 KPIs they track)
3. ROI expectations (what ROI they expect)
4. Implementation timeline (expected timeline)
5. Success indicators (3-5 indicators of successful outcome)

Return JSON with:
- definition_of_success: string
- kpis_tracked: array of strings
- roi_expectations: string
- implementation_timeline: string
- success_indicators: array of strings"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2500
        )

        data = self._extract_json_from_response(response)

        return SuccessCriteria(
            definition_of_success=data.get("definition_of_success"),
            kpis_tracked=data.get("kpis_tracked", []),
            roi_expectations=data.get("roi_expectations"),
            implementation_timeline=data.get("implementation_timeline"),
            success_indicators=data.get("success_indicators", []),
        )

    def _synthesize_profile(
        self,
        client: Any,
        business_name: str,
        demographics: Demographics,
        psychographics: Psychographics,
        behavioral: Behavioral,
        situational: Situational,
        success_criteria: SuccessCriteria,
    ) -> tuple[str, list[str], list[str], list[str]]:
        """Synthesize insights from complete profile"""
        prompt = f"""Synthesize this complete ICP into actionable insights.

Business: {business_name}

DEMOGRAPHICS:
- Industry: {demographics.industry}
- Size: {demographics.company_size}
- Roles: {', '.join(demographics.job_titles[:3])}

PSYCHOGRAPHICS:
- Goals: {', '.join(psychographics.goals[:3])}
- Challenges: {', '.join(psychographics.challenges[:3])}
- Values: {', '.join(psychographics.values[:3])}

BEHAVIORAL:
- Content: {', '.join(behavioral.content_consumption[:3])}
- Platforms: {', '.join(behavioral.platforms_active_on[:3])}

Provide:
1. One-sentence ICP summary (concise description of the ideal customer)
2. Key insights (3-5 critical insights about this ICP)
3. Messaging recommendations (3-5 messaging angles that will resonate)
4. Content topics (5-7 content topics to create)

Return JSON with:
- one_sentence_summary: string
- key_insights: array of strings
- messaging_recommendations: array of strings
- content_topics: array of strings"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=3000
        )

        data = self._extract_json_from_response(response)

        return (
            data.get("one_sentence_summary", ""),
            data.get("key_insights", []),
            data.get("messaging_recommendations", []),
            data.get("content_topics", []),
        )

    def _generate_next_steps(
        self, client: Any, profile: IdealCustomerProfile
    ) -> list[str]:
        """Generate recommended next steps"""
        prompt = f"""Based on this ICP, recommend 5-7 immediate next steps.

ICP Summary: {profile.one_sentence_summary}
Key Insights: {', '.join(profile.key_insights[:3])}
Platforms: {', '.join(profile.behavioral.platforms_active_on[:3])}

Provide actionable next steps like:
- Specific content to create
- Platforms to focus on
- Messaging to test
- Research to conduct
- Tools to implement

Return JSON array of strings."""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=1500
        )

        return self._extract_json_from_response(response)

    def generate_reports(self, analysis: ICPWorkshopAnalysis) -> Dict[str, Path]:
        """Generate output files"""
        outputs = {}

        # JSON format
        json_path = self.output_dir / "icp_profile.json"
        json_path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
        outputs["json"] = json_path

        # Markdown format
        markdown_path = self.output_dir / "icp_profile.md"
        markdown_content = self.format_output_markdown(analysis)
        markdown_path.write_text(markdown_content, encoding="utf-8")
        outputs["markdown"] = markdown_path

        # Text format (summary)
        text_path = self.output_dir / "icp_summary.txt"
        text_content = self.format_output_text(analysis)
        text_path.write_text(text_content, encoding="utf-8")
        outputs["text"] = text_path

        return outputs

    def format_output_markdown(self, analysis: ICPWorkshopAnalysis) -> str:
        """Format as markdown report"""
        profile = analysis.profile

        md = f"""# Ideal Customer Profile: {profile.profile_name}

**Created:** {profile.created_date}
{f'**Business:** {profile.business_name}' if profile.business_name else ''}

---

## Executive Summary

{profile.one_sentence_summary}

---

## Demographics / Firmographics

**Industry:** {profile.demographics.industry or 'Not specified'}
**Company Size:** {profile.demographics.company_size or 'Not specified'}
**Revenue Range:** {profile.demographics.revenue_range or 'Not specified'}
**Location:** {profile.demographics.location or 'Not specified'}
**Team Structure:** {profile.demographics.team_structure or 'Not specified'}

**Decision-Maker Roles:**
{self._format_list(profile.demographics.job_titles)}

**Technologies Used:**
{self._format_list(profile.demographics.technologies_used)}

---

## Psychographics

### Goals & Objectives
{self._format_list(profile.psychographics.goals)}

### Challenges & Frustrations
{self._format_list(profile.psychographics.challenges)}

### Core Values & Priorities
{self._format_list(profile.psychographics.values)}

### Decision-Making Factors
{self._format_list(profile.psychographics.decision_factors)}

**Aspirations:** {profile.psychographics.aspirations or 'Not specified'}

---

## Behavioral Patterns

**Buying Process:**
{profile.behavioral.buying_process or 'Not specified'}

**Content Consumption:**
{self._format_list(profile.behavioral.content_consumption)}

**Research Habits:**
{profile.behavioral.research_habits or 'Not specified'}

**Trusted Influencers:**
{self._format_list(profile.behavioral.influencers)}

**Active Platforms:**
{self._format_list(profile.behavioral.platforms_active_on)}

---

## Situational Factors

**Pain Point Triggers:**
{self._format_list(profile.situational.pain_triggers)}

**Timing & Seasonality:**
{profile.situational.timing_seasonality or 'Not specified'}

**Budget Constraints:**
{profile.situational.budget_constraints or 'Not specified'}

**Competitive Pressures:**
{self._format_list(profile.situational.competitive_pressures)}

**Current Solutions:**
{profile.situational.current_solutions or 'Not specified'}

---

## Success Criteria

**Definition of Success:**
{profile.success_criteria.definition_of_success or 'Not specified'}

**KPIs Tracked:**
{self._format_list(profile.success_criteria.kpis_tracked)}

**ROI Expectations:**
{profile.success_criteria.roi_expectations or 'Not specified'}

**Implementation Timeline:**
{profile.success_criteria.implementation_timeline or 'Not specified'}

**Success Indicators:**
{self._format_list(profile.success_criteria.success_indicators)}

---

## Key Insights

{self._format_list(profile.key_insights)}

---

## Messaging Recommendations

{self._format_list(profile.messaging_recommendations)}

---

## Recommended Content Topics

{self._format_list(profile.content_topics)}

---

## Next Steps

{self._format_list(analysis.next_steps, numbered=True)}

---

*ICP Workshop Facilitation - ${self.price}*
"""

        return md

    def format_output_text(self, analysis: ICPWorkshopAnalysis) -> str:
        """Format as plain text summary"""
        profile = analysis.profile

        text = f"""IDEAL CUSTOMER PROFILE SUMMARY
{'=' * 60}

Profile: {profile.profile_name}
Created: {profile.created_date}

EXECUTIVE SUMMARY
{'=' * 60}

{profile.one_sentence_summary}

KEY DEMOGRAPHICS
{'=' * 60}

Industry: {profile.demographics.industry}
Company Size: {profile.demographics.company_size}
Decision Makers: {', '.join(profile.demographics.job_titles[:3])}

TOP GOALS
{'=' * 60}

"""

        for i, goal in enumerate(profile.psychographics.goals[:5], 1):
            text += f"{i}. {goal}\n"

        text += f"""
TOP CHALLENGES
{'=' * 60}

"""

        for i, challenge in enumerate(profile.psychographics.challenges[:5], 1):
            text += f"{i}. {challenge}\n"

        text += f"""
RECOMMENDED CONTENT TOPICS
{'=' * 60}

"""

        for i, topic in enumerate(profile.content_topics[:7], 1):
            text += f"{i}. {topic}\n"

        text += "\n\nSee icp_profile.md for complete details.\n"

        return text

    def _format_list(self, items: list[str], numbered: bool = False) -> str:
        """Format list for markdown"""
        if not items:
            return "None specified\n"

        if numbered:
            return "\n".join([f"{i}. {item}" for i, item in enumerate(items, 1)])
        else:
            return "\n".join([f"- {item}" for item in items])

    def _extract_json_from_response(self, text: str) -> Any:
        """Extract JSON from Claude response"""
        try:
            # Try to parse entire response as JSON
            return json.loads(text)
        except json.JSONDecodeError:
            # Look for JSON in code blocks
            import re

            json_match = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # Try to find JSON object/array
            json_match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            raise ValueError(f"Could not extract JSON from response: {text[:200]}")
