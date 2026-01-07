"""Audience Research Tool - Researches target audience demographics and psychographics

This tool analyzes business and industry data to create comprehensive audience profiles
including demographics, psychographics, behaviors, pain points, and segments.

Price: $500
Automation Level: 95%
Time: 3-4 minutes automated
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..models.audience_research_models import (
    AgeRange,
    AudienceResearch,
    AudienceSegment,
    BehavioralProfile,
    Demographics,
    EducationLevel,
    IncomeLevel,
    Psychographics,
)
from ..utils.anthropic_client import get_default_client
from ..utils.logger import logger
from ..validators.research_input_validator import ResearchInputValidator
from .base import ResearchTool


class AudienceResearcher(ResearchTool):
    """Analyzes target audience demographics, psychographics, and behaviors

    Creates comprehensive audience profiles with segments, pain points,
    content preferences, and strategic recommendations.
    """

    def __init__(self, project_id: str, config: Dict[str, Any] = None):
        """Initialize audience researcher with input validator"""
        super().__init__(project_id, config)
        self.validator = ResearchInputValidator(strict_mode=False)

    @property
    def tool_name(self) -> str:
        return "audience_research"

    @property
    def price(self) -> int:
        return 500

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """
        Validate required inputs with comprehensive security checks (TR-019)

        Security Features:
        - Max length checks (prevent DOS attacks)
        - Prompt injection sanitization
        - Type validation
        - Field presence validation
        """
        # SECURITY: Validate business description with sanitization
        inputs["business_description"] = self.validator.validate_text(
            inputs.get("business_description"),
            field_name="business_description",
            min_length=50,
            max_length=5000,
            required=True,
            sanitize=True,
        )

        # SECURITY: Validate target audience description
        inputs["target_audience"] = self.validator.validate_text(
            inputs.get("target_audience"),
            field_name="target_audience",
            min_length=20,
            max_length=2000,
            required=True,
            sanitize=True,
        )

        # SECURITY: Validate optional business name
        if "business_name" in inputs and inputs["business_name"]:
            inputs["business_name"] = self.validator.validate_text(
                inputs["business_name"],
                field_name="business_name",
                min_length=2,
                max_length=200,
                required=False,
                sanitize=True,
            )

        # SECURITY: Validate optional industry
        if "industry" in inputs and inputs["industry"]:
            inputs["industry"] = self.validator.validate_text(
                inputs["industry"],
                field_name="industry",
                min_length=2,
                max_length=200,
                required=False,
                sanitize=True,
            )

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> AudienceResearch:
        """Execute audience research analysis"""
        logger.info("Running audience_research analysis")

        business_desc = inputs["business_description"]
        target_audience = inputs["target_audience"]
        business_name = inputs.get("business_name", "Client Business")
        industry = inputs.get("industry", "General")

        # Multi-step analysis
        print("[Step 1/4] Analyzing demographics and psychographics...")
        demographics_psycho = self._analyze_demographics_psychographics(
            business_desc, target_audience, industry
        )

        print("[Step 2/4] Analyzing behaviors and pain points...")
        behaviors_pain = self._analyze_behaviors_pain_points(
            business_desc, target_audience, industry
        )

        print("[Step 3/4] Identifying audience segments...")
        segments = self._identify_segments(
            business_desc, target_audience, industry, demographics_psycho, behaviors_pain
        )

        print("[Step 4/4] Generating strategic recommendations...")
        strategy = self._generate_strategy(
            business_desc, target_audience, industry, demographics_psycho, behaviors_pain, segments
        )

        # Compile complete research
        return self._compile_research(
            business_name=business_name,
            industry=industry,
            target_description=target_audience,
            demographics_psycho=demographics_psycho,
            behaviors_pain=behaviors_pain,
            segments=segments,
            strategy=strategy,
        )

    def _analyze_demographics_psychographics(
        self, business_desc: str, target_audience: str, industry: str
    ) -> Dict[str, Any]:
        """Step 1: Analyze demographics and psychographics"""
        client = get_default_client()

        prompt = f"""Analyze the target audience for this business and provide demographics and psychographics.

BUSINESS: {business_desc}

TARGET AUDIENCE: {target_audience}

INDUSTRY: {industry}

Provide a detailed JSON analysis with:

1. DEMOGRAPHICS:
   - primary_age_ranges: List of 1-3 age ranges
   - gender_distribution: Description of gender breakdown
   - locations: Geographic locations (5-10 items)
   - income_levels: Income categories
   - education_levels: Education categories
   - job_titles: Common job titles (5-10 items)
   - company_sizes: Company size preferences (3-5 items)

2. PSYCHOGRAPHICS:
   - values: Core values (5-7 items)
   - interests: Hobbies and interests (5-10 items)
   - lifestyle: Lifestyle description
   - personality_traits: Common traits (5-7 items)
   - motivations: Key motivations (5-7 items)

3. SUMMARY:
   - executive_summary: High-level insights (2-3 paragraphs)
   - audience_size_estimate: Total addressable market estimate

IMPORTANT - Use ONLY these exact values for enums:
- age_ranges: "18-24", "25-34", "35-44", "45-54", "55-64", "65+"
- income_levels: "low", "middle", "upper_middle", "high"
- education_levels: "high_school", "some_college", "bachelors", "masters", "doctorate"

Return ONLY valid JSON:
{{
  "demographics": {{...}},
  "psychographics": {{...}},
  "executive_summary": "...",
  "audience_size_estimate": "..."
}}"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=4000
        )

        return self._extract_json_from_response(response)

    def _analyze_behaviors_pain_points(
        self, business_desc: str, target_audience: str, industry: str
    ) -> Dict[str, Any]:
        """Step 2: Analyze behaviors and pain points"""
        client = get_default_client()

        prompt = f"""Analyze the behavioral patterns and pain points for this audience.

BUSINESS: {business_desc}

TARGET AUDIENCE: {target_audience}

INDUSTRY: {industry}

Provide a detailed JSON analysis with:

1. BEHAVIORAL PROFILE:
   - content_consumption: STRING describing how they consume content
   - preferred_platforms: ARRAY of social media and content platforms (5-10 items)
   - online_behavior: STRING describing online behavior patterns
   - purchase_behavior: STRING describing buying behavior and decision process
   - engagement_patterns: STRING describing how they engage with brands

2. PAIN POINTS: ARRAY of top challenges (7-10 items)

3. GOALS: ARRAY of goals and aspirations (7-10 items)

4. DECISION FACTORS: ARRAY of key decision-making factors (5-7 items)

5. INFORMATION SOURCES: ARRAY of where they get info (5-10 sources)

6. INFLUENCERS: ARRAY of influencers and brands they follow (7-10 items)

IMPORTANT - Format requirements:
- All STRING fields must be simple text descriptions, NOT nested objects
- All ARRAY fields must be flat lists of strings
- Do NOT create nested objects for any field

Return ONLY valid JSON:
{{
  "behavioral_profile": {{
    "content_consumption": "text description here",
    "preferred_platforms": ["platform1", "platform2", ...],
    "online_behavior": "text description here",
    "purchase_behavior": "text description here",
    "engagement_patterns": "text description here"
  }},
  "pain_points": ["challenge1", "challenge2", ...],
  "goals_aspirations": ["goal1", "goal2", ...],
  "decision_factors": ["factor1", "factor2", ...],
  "information_sources": ["source1", "source2", ...],
  "influencers_brands": ["influencer1", "influencer2", ...]
}}"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=3500
        )

        return self._extract_json_from_response(response)

    def _identify_segments(
        self,
        business_desc: str,
        target_audience: str,
        industry: str,
        demographics_psycho: Dict[str, Any],
        behaviors_pain: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Step 3: Identify 3-5 distinct audience segments"""
        client = get_default_client()

        prompt = f"""Identify 3-5 distinct audience segments for this business.

BUSINESS: {business_desc}

TARGET AUDIENCE: {target_audience}

INDUSTRY: {industry}

Based on the demographic and behavioral data, identify 3-5 distinct segments.

For each segment provide:
- segment_name: Descriptive name
- segment_size: Estimated % of total audience
- description: 2-3 sentence description
- key_characteristics: Defining traits (3-5 items)
- content_preferences: Content preferences (3-5 items)
- messaging_recommendations: How to message this segment

Return ONLY valid JSON array:
[
  {{
    "segment_name": "...",
    "segment_size": "...",
    "description": "...",
    "key_characteristics": [...],
    "content_preferences": [...],
    "messaging_recommendations": "..."
  }},
  ...
]"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=3000
        )

        return self._extract_json_from_response(response)

    def _generate_strategy(
        self,
        business_desc: str,
        target_audience: str,
        industry: str,
        demographics_psycho: Dict[str, Any],
        behaviors_pain: Dict[str, Any],
        segments: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Step 4: Generate strategic recommendations"""
        client = get_default_client()

        prompt = f"""Generate strategic recommendations for reaching this audience.

BUSINESS: {business_desc}

TARGET AUDIENCE: {target_audience}

INDUSTRY: {industry}

Provide strategic recommendations:

1. CONTENT PREFERENCES: Format and topic preferences (7-10 items)

2. MESSAGING FRAMEWORK: Overall messaging framework and tone

3. CONTENT STRATEGY: Strategic content recommendations (5-7 items)

4. ENGAGEMENT TACTICS: Tactics to engage (5-7 items)

5. KEY INSIGHTS: Key strategic insights (5-7 items)

6. WHAT TO AVOID: What to avoid (3-5 items)

Return ONLY valid JSON:
{{
  "content_preferences": [...],
  "messaging_framework": "...",
  "content_strategy_recommendations": [...],
  "engagement_tactics": [...],
  "key_insights": [...],
  "what_to_avoid": [...]
}}"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=3000
        )

        return self._extract_json_from_response(response)

    def _compile_research(
        self,
        business_name: str,
        industry: str,
        target_description: str,
        demographics_psycho: Dict[str, Any],
        behaviors_pain: Dict[str, Any],
        segments: List[Dict[str, Any]],
        strategy: Dict[str, Any],
    ) -> AudienceResearch:
        """Compile all components into final research"""
        # Parse demographics
        demo_data = demographics_psycho.get("demographics", {})
        demographics = Demographics(
            primary_age_ranges=[AgeRange(age) for age in demo_data.get("primary_age_ranges", [])],
            gender_distribution=demo_data.get("gender_distribution", "Mixed distribution"),
            locations=demo_data.get("locations", []),
            income_levels=[IncomeLevel(inc) for inc in demo_data.get("income_levels", [])],
            education_levels=[EducationLevel(edu) for edu in demo_data.get("education_levels", [])],
            job_titles=demo_data.get("job_titles", []),
            company_sizes=demo_data.get("company_sizes", []),
        )

        # Parse psychographics
        psycho_data = demographics_psycho.get("psychographics", {})
        psychographics = Psychographics(
            values=psycho_data.get("values", []),
            interests=psycho_data.get("interests", []),
            lifestyle=psycho_data.get("lifestyle", "Varied lifestyle patterns"),
            personality_traits=psycho_data.get("personality_traits", []),
            motivations=psycho_data.get("motivations", []),
        )

        # Parse behavioral profile
        behavior_data = behaviors_pain.get("behavioral_profile", {})
        behavioral_profile = BehavioralProfile(
            content_consumption=behavior_data.get(
                "content_consumption", "Mixed consumption patterns"
            ),
            preferred_platforms=behavior_data.get("preferred_platforms", []),
            online_behavior=behavior_data.get("online_behavior", "Active online presence"),
            purchase_behavior=behavior_data.get("purchase_behavior", "Research-driven purchases"),
            engagement_patterns=behavior_data.get("engagement_patterns", "Selective engagement"),
        )

        # Parse segments
        audience_segments = [AudienceSegment(**seg) for seg in segments]

        return AudienceResearch(
            business_name=business_name,
            industry=industry,
            target_description=target_description,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            executive_summary=demographics_psycho.get("executive_summary", ""),
            audience_size_estimate=demographics_psycho.get("audience_size_estimate", ""),
            demographics=demographics,
            psychographics=psychographics,
            behavioral_profile=behavioral_profile,
            pain_points=behaviors_pain.get("pain_points", []),
            goals_aspirations=behaviors_pain.get("goals_aspirations", []),
            content_preferences=strategy.get("content_preferences", []),
            decision_factors=behaviors_pain.get("decision_factors", []),
            information_sources=behaviors_pain.get("information_sources", []),
            influencers_brands=behaviors_pain.get("influencers_brands", []),
            audience_segments=audience_segments,
            messaging_framework=strategy.get("messaging_framework", ""),
            content_strategy_recommendations=strategy.get("content_strategy_recommendations", []),
            engagement_tactics=strategy.get("engagement_tactics", []),
            key_insights=strategy.get("key_insights", []),
            what_to_avoid=strategy.get("what_to_avoid", []),
        )

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

    def generate_reports(self, analysis: AudienceResearch) -> Dict[str, Path]:
        """Generate audience research reports in multiple formats"""
        # Get output directory (property already creates it)
        output_dir = self.output_dir

        outputs = {}

        # 1. Save JSON
        json_path = output_dir / "audience_research.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(analysis.model_dump(), f, indent=2, default=str)
        outputs["json"] = json_path

        # 2. Generate Markdown Report
        markdown_path = output_dir / "audience_research_report.md"
        markdown_content = self._generate_markdown_report(analysis)
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        outputs["markdown"] = markdown_path

        # 3. Generate Text Summary
        text_path = output_dir / "audience_research_summary.txt"
        text_content = self._generate_text_summary(analysis)
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        outputs["text"] = text_path

        return outputs

    def _generate_markdown_report(self, research: AudienceResearch) -> str:
        """Generate comprehensive markdown report"""
        md = f"""# Audience Research Report: {research.business_name}

**Industry:** {research.industry}
**Analysis Date:** {research.analysis_date}
**Target Audience:** {research.target_description}

---

## Executive Summary

{research.executive_summary}

**Estimated Audience Size:** {research.audience_size_estimate}

---

## Demographics

### Age Ranges
{self._format_list([age.value for age in research.demographics.primary_age_ranges])}

### Gender Distribution
{research.demographics.gender_distribution}

### Geographic Locations
{self._format_list(research.demographics.locations)}

### Income Levels
{self._format_list([inc.value for inc in research.demographics.income_levels])}

### Education Levels
{self._format_list([edu.value for edu in research.demographics.education_levels])}

### Common Job Titles
{self._format_list(research.demographics.job_titles)}

### Company Sizes
{self._format_list(research.demographics.company_sizes)}

---

## Psychographics

### Core Values
{self._format_list(research.psychographics.values)}

### Interests
{self._format_list(research.psychographics.interests)}

### Lifestyle
{research.psychographics.lifestyle}

### Personality Traits
{self._format_list(research.psychographics.personality_traits)}

### Motivations
{self._format_list(research.psychographics.motivations)}

---

## Behavioral Profile

### Content Consumption
{research.behavioral_profile.content_consumption}

### Preferred Platforms
{self._format_list(research.behavioral_profile.preferred_platforms)}

### Online Behavior
{research.behavioral_profile.online_behavior}

### Purchase Behavior
{research.behavioral_profile.purchase_behavior}

### Engagement Patterns
{research.behavioral_profile.engagement_patterns}

---

## Pain Points & Goals

### Top Pain Points
{self._format_list(research.pain_points)}

### Goals & Aspirations
{self._format_list(research.goals_aspirations)}

---

## Decision Factors & Information Sources

### Decision-Making Factors
{self._format_list(research.decision_factors)}

### Information Sources
{self._format_list(research.information_sources)}

### Influencers & Brands They Follow
{self._format_list(research.influencers_brands)}

---

## Audience Segments

"""

        for segment in research.audience_segments:
            md += f"""
### {segment.segment_name}

**Size:** {segment.segment_size}

**Description:** {segment.description}

**Key Characteristics:**
{self._format_list(segment.key_characteristics)}

**Content Preferences:**
{self._format_list(segment.content_preferences)}

**Messaging Recommendations:**
{segment.messaging_recommendations}

---
"""

        md += f"""
## Content Strategy

### Content Preferences
{self._format_list(research.content_preferences)}

### Messaging Framework
{research.messaging_framework}

### Content Strategy Recommendations
{self._format_list(research.content_strategy_recommendations)}

### Engagement Tactics
{self._format_list(research.engagement_tactics)}

---

## Key Insights & Recommendations

### Strategic Insights
{self._format_list(research.key_insights)}

### What to Avoid
{self._format_list(research.what_to_avoid)}

---

*Generated by Audience Research Tool ($500)*
"""

        return md

    def _generate_text_summary(self, research: AudienceResearch) -> str:
        """Generate concise text summary"""
        text = f"""AUDIENCE RESEARCH SUMMARY
{research.business_name} - {research.industry}
Analysis Date: {research.analysis_date}

=== OVERVIEW ===
Target: {research.target_description}
Audience Size: {research.audience_size_estimate}

{research.executive_summary}

=== TOP INSIGHTS ===
"""
        for i, insight in enumerate(research.key_insights, 1):
            text += f"{i}. {insight}\n"

        text += """
=== AUDIENCE SEGMENTS ===
"""
        for segment in research.audience_segments:
            text += f"\n{segment.segment_name} ({segment.segment_size})\n"
            text += f"{segment.description}\n"

        text += """
=== TOP PAIN POINTS ===
"""
        for i, pain in enumerate(research.pain_points[:5], 1):
            text += f"{i}. {pain}\n"

        text += f"""
=== MESSAGING FRAMEWORK ===
{research.messaging_framework}

Generated by Audience Research Tool ($500)
"""

        return text

    def _format_list(self, items: List[str]) -> str:
        """Format list as markdown bullets"""
        if not items:
            return "- (No items)"
        return "\n".join(f"- {item}" for item in items)
