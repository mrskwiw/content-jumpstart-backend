"""Platform Strategy Tool - Analyze and recommend optimal platform mix

This tool analyzes the target audience and business to recommend which social media
platforms and content formats will deliver the best results.

Price: $300
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.platform_strategy_models import (
    AudienceBehavior,
    ContentDistribution,
    ContentFormat,
    PlatformFit,
    PlatformMix,
    PlatformName,
    PlatformRecommendation,
    PlatformStrategyAnalysis,
    QuickWin,
)
from ..validators.research_input_validator import ResearchInputValidator
from .base import ResearchTool
from .validation_mixin import CommonValidationMixin
from ..utils.anthropic_client import get_default_client
from ..utils.logger import logger
from ..utils.web_search import get_search_client


class PlatformStrategist(ResearchTool, CommonValidationMixin):
    """Analyze audience and recommend optimal platform mix"""

    def __init__(self, project_id: str, config: Optional[Dict[str, Any]] = None):
        """Initialize Platform Strategist with input validator"""
        super().__init__(project_id, config)
        self.validator = ResearchInputValidator(strict_mode=False)
        self.client = get_default_client()  # Needed for API calls

    @property
    def tool_name(self) -> str:
        return "platform_strategy"

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

        # SECURITY: Validate optional tone preference (auto-populated from client profile)
        if "tone_preference" in inputs and inputs["tone_preference"]:
            inputs["tone_preference"] = self.validator.validate_text(
                inputs.get("tone_preference"),
                field_name="tone_preference",
                min_length=2,
                max_length=100,
                required=False,
                sanitize=True,
            )

        # SECURITY: Validate optional brand personality traits (auto-populated from client profile)
        if "brand_personality" in inputs and inputs["brand_personality"]:
            brand_personality = inputs["brand_personality"]
            if isinstance(brand_personality, list):
                inputs["brand_personality"] = [
                    self.validator.validate_text(
                        t,
                        field_name="personality_trait",
                        min_length=2,
                        max_length=100,
                        required=False,
                        sanitize=True,
                    )
                    for t in brand_personality[:10]
                ]
            elif isinstance(brand_personality, str):
                inputs["brand_personality"] = self.validator.validate_text(
                    brand_personality,
                    field_name="brand_personality",
                    min_length=2,
                    max_length=500,
                    required=False,
                    sanitize=True,
                )

        # SECURITY: Validate optional posting frequency (auto-populated from client profile)
        if "posting_frequency" in inputs and inputs["posting_frequency"]:
            inputs["posting_frequency"] = self.validator.validate_text(
                inputs.get("posting_frequency"),
                field_name="posting_frequency",
                min_length=2,
                max_length=200,
                required=False,
                sanitize=True,
            )

        # SECURITY: Validate optional data usage preference (auto-populated from client profile)
        if "data_usage" in inputs and inputs["data_usage"]:
            inputs["data_usage"] = self.validator.validate_text(
                inputs.get("data_usage"),
                field_name="data_usage",
                min_length=2,
                max_length=50,
                required=False,
                sanitize=True,
            )

        # SECURITY: Validate optional current platforms list
        # BUG FIX #38: Add type normalization before validation
        if "current_platforms" in inputs:
            current_platforms = inputs["current_platforms"]

            # Type normalization: handle various input formats
            if isinstance(current_platforms, str):
                # Convert comma-separated string to list
                current_platforms = [p.strip() for p in current_platforms.split(",") if p.strip()]
            elif not isinstance(current_platforms, list):
                # Invalid type - default to empty list
                current_platforms = []

            # Only validate if non-empty
            if current_platforms:
                inputs["current_platforms"] = self.validator.validate_list(
                    current_platforms,
                    field_name="current_platforms",
                    max_items=10,
                    required=False,  # Make it truly optional
                    item_validator=lambda x: self.validator.validate_text(
                        x,
                        field_name="platform_name",
                        min_length=2,
                        max_length=100,
                        required=False,
                        sanitize=True,
                    ),
                )
            else:
                inputs["current_platforms"] = []

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> PlatformStrategyAnalysis:
        """Execute 5-step platform strategy analysis"""
        business_description = inputs["business_description"]
        target_audience = inputs["target_audience"]
        business_name = inputs.get("business_name", "Client")
        industry = inputs.get("industry", "Not specified")
        current_platforms = inputs.get("current_platforms", [])
        content_goals = inputs.get("content_goals", "awareness and leads")
        tone_preference = inputs.get("tone_preference", "")
        brand_personality = inputs.get("brand_personality", [])
        posting_frequency = inputs.get("posting_frequency", "")
        data_usage = inputs.get("data_usage", "")

        # Step 1: Analyze audience platform behavior
        print("[Step 1/5] Analyzing target audience platform behavior...")
        audience_behavior = self._analyze_audience_behavior(
            self.client, business_description, target_audience
        )

        # Step 2: Generate platform recommendations (with optional live demographics)
        print("[Step 2/5] Evaluating platform fit and recommendations...")
        active_platform_names = [b.platform.value for b in audience_behavior if b.audience_present]
        platform_demographics = self._research_platform_demographics(
            active_platform_names, industry
        )
        platform_recommendations = self._generate_platform_recommendations(
            self.client,
            business_description,
            target_audience,
            audience_behavior,
            content_goals,
            tone_preference=tone_preference,
            brand_personality=brand_personality,
            data_usage=data_usage,
            platform_demographics=platform_demographics,
        )

        # Step 3: Determine optimal platform mix
        print("[Step 3/5] Determining optimal platform mix...")
        platform_mix = self._determine_platform_mix(
            self.client,
            platform_recommendations,
            target_audience,
            content_goals,
            posting_frequency=posting_frequency,
        )

        # Step 4: Create content distribution strategy
        print("[Step 4/5] Creating content distribution strategy...")
        content_distribution = self._create_distribution_strategy(
            self.client, platform_mix, business_description, target_audience
        )

        # Step 5: Generate quick wins
        print("[Step 5/5] Identifying quick wins...")
        quick_wins = self._generate_quick_wins(self.client, platform_mix, platform_recommendations)

        # Analyze current state if provided
        current_strengths: list[str] = []
        current_gaps: list[str] = []
        if current_platforms:
            print("[Analysis] Analyzing current platform strategy...")
            current_strengths, current_gaps = self._analyze_current_state(
                self.client, current_platforms, platform_recommendations, platform_mix
            )

        # Generate strategic insights
        print("[Strategy] Generating strategic insights...")
        key_insights, mistakes_to_avoid = self._generate_strategic_insights(
            self.client,
            business_description,
            target_audience,
            platform_mix,
            platform_recommendations,
        )

        # Create implementation plans
        print("[Planning] Creating implementation plans...")
        thirty_day_plan, ninety_day_plan = self._create_implementation_plans(
            self.client, platform_mix, platform_recommendations, quick_wins
        )

        # Generate executive summary
        print("[Summary] Generating executive summary...")
        executive_summary = self._generate_executive_summary(
            self.client, business_name, target_audience, platform_mix, platform_recommendations
        )

        # Build complete analysis
        analysis = PlatformStrategyAnalysis(
            business_name=business_name,
            industry=industry,
            target_audience=target_audience,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            executive_summary=executive_summary,
            recommended_platform_mix=platform_mix,
            audience_behavior=audience_behavior,
            platform_recommendations=platform_recommendations,
            content_distribution=content_distribution,
            current_platforms=current_platforms,
            current_strengths=current_strengths,
            current_gaps=current_gaps,
            quick_wins=quick_wins,
            thirty_day_plan=thirty_day_plan,
            ninety_day_plan=ninety_day_plan,
            key_insights=key_insights,
            common_mistakes_to_avoid=mistakes_to_avoid,
        )

        return analysis

    def _analyze_audience_behavior(
        self, client: Any, business_description: str, target_audience: str
    ) -> List[AudienceBehavior]:
        """Analyze where target audience is active"""
        prompt = f"""CRITICAL: Analyze ALL major platforms. Fill EVERY field for EACH platform.

Business: {business_description}
Target Audience: {target_audience}

EXAMPLE OUTPUT:
[
  {{
    "platform": "LinkedIn",
    "activity_level": "high",
    "audience_present": true,
    "consumption_patterns": "Professional content, industry news, thought leadership during business hours",
    "engagement_style": "Comments on posts, shares within network, values expertise",
    "decision_makers_present": true,
    "fit_score": 95
  }},
  {{
    "platform": "Twitter",
    "activity_level": "medium",
    "audience_present": true,
    "consumption_patterns": "Real-time updates, quick tips, industry conversations",
    "engagement_style": "Retweets, quick replies, follows thought leaders",
    "decision_makers_present": false,
    "fit_score": 60
  }}
]

For each major platform (LinkedIn, Twitter, Facebook, Instagram, YouTube, Blog, Email, Podcast), analyze:
1. Is the target audience present and active?
2. Activity level (High/Medium/Low)
3. Content consumption patterns (be specific)
4. Engagement style (how they interact)
5. Are decision-makers present?

FIELD-BY-FIELD REQUIREMENTS:
- "platform": Platform name (LinkedIn, Twitter, Facebook, Instagram, YouTube, Blog, Email, Podcast)
- "activity_level": "high", "medium", or "low"
- "audience_present": true/false
- "consumption_patterns": Specific description of what content they consume and when
- "engagement_style": How this audience engages (comments, shares, likes, etc.)
- "decision_makers_present": true/false - Are C-level/decision makers active here?
- "fit_score": 0-100 score for platform fit

Return a JSON array with objects containing:
- platform: platform name (lowercase)
- audience_present: boolean
- activity_level: string
- content_consumption_pattern: string
- engagement_style: string
- decision_maker_presence: string

Focus on platforms where the audience is ACTUALLY active, not theoretical presence."""

        # Call Claude API with automatic JSON extraction (Phase 3 deduplication)
        data = self._call_claude_api(
            prompt, max_tokens=4000, temperature=0.4, extract_json=True, fallback_on_error={}
        )

        behaviors = []
        for b in data:
            try:
                # Map platform name to enum
                platform_str = b.get("platform", "").lower()
                platform = self._map_platform_name(platform_str)

                behaviors.append(
                    AudienceBehavior(
                        platform=platform,
                        audience_present=b.get("audience_present", False),
                        activity_level=b.get("activity_level", "Low"),
                        content_consumption_pattern=b.get("content_consumption_pattern", ""),
                        engagement_style=b.get("engagement_style", ""),
                        decision_maker_presence=b.get("decision_maker_presence", ""),
                    )
                )
            except Exception as e:
                print(f"Warning: Skipping invalid audience behavior: {e}")
                continue

        return behaviors

    def _research_platform_demographics(self, platforms: List[str], industry: str) -> str:
        """Fetch current audience demographics for each platform via web search.

        Searches for live demographic data to ground platform recommendations in
        current real-world usage patterns rather than baked-in assumptions.

        Args:
            platforms: List of platform names to research (max 3 queried).
            industry: Industry context for targeted search results.

        Returns:
            Formatted string of demographics data, or empty string if unavailable.
        """
        try:
            search_client = get_search_client()
            if search_client is None:
                return ""

            results_lines: List[str] = []
            for platform in platforms[:3]:
                query = f"{platform} audience demographics {industry} 2026"
                logger.info(f"platform_strategy: searching demographics — {query}")
                response = search_client.search(query, max_results=3)
                if not response.results:
                    continue
                results_lines.append(f"{platform} demographics (from web):")
                for result in response.results:
                    results_lines.append(f"- [{result.title}] {result.snippet}")
                results_lines.append("")

            return "\n".join(results_lines).strip()

        except Exception as exc:
            logger.warning(f"platform_strategy: web search for demographics failed — {exc}")
            return ""

    def _generate_platform_recommendations(
        self,
        client: Any,
        business_description: str,
        target_audience: str,
        audience_behavior: List[AudienceBehavior],
        content_goals: str,
        tone_preference: str = "",
        brand_personality: "list | str" = "",
        data_usage: str = "",
        platform_demographics: str = "",
    ) -> List[PlatformRecommendation]:
        """Generate detailed recommendations for all relevant platforms in a single API call"""
        # Filter to platforms where audience is present
        active_platforms = [b for b in audience_behavior if b.audience_present]

        if not active_platforms:
            return []

        # Build a summary of audience behaviors for all platforms
        behaviors_summary = []
        for b in active_platforms:
            behaviors_summary.append(
                f"""Platform: {b.platform.value}
- Activity Level: {b.activity_level}
- Consumption: {b.content_consumption_pattern}
- Engagement: {b.engagement_style}
- Decision Makers: {b.decision_maker_presence}"""
            )

        behaviors_text = "\n\n".join(behaviors_summary)
        platform_names = ", ".join(b.platform.value for b in active_platforms)

        # Build brand voice context if available
        voice_lines = []
        if tone_preference:
            voice_lines.append(f"Tone Preference: {tone_preference}")
        if brand_personality:
            traits = (
                ", ".join(brand_personality)
                if isinstance(brand_personality, list)
                else brand_personality
            )
            voice_lines.append(f"Brand Personality Traits: {traits}")
        if data_usage:
            voice_lines.append(
                f"Data/Statistics Usage: {data_usage} (affects content format fit — heavy data favors LinkedIn/blog over Twitter/Instagram)"
            )
        voice_context = ("\nBrand Voice Context:\n" + "\n".join(voice_lines)) if voice_lines else ""

        demographics_context = (
            f"\n\nCurrent Platform Demographics (live web data):\n{platform_demographics}"
            if platform_demographics
            else ""
        )

        prompt = f"""Create detailed platform recommendations for ALL of these platforms: {platform_names}

Business: {business_description}
Target Audience: {target_audience}
Content Goals: {content_goals}{voice_context}

Audience Behavior Data:
{behaviors_text}{demographics_context}

For EACH platform, provide a recommendation with:
1. Fit level (essential/recommended/optional/not_recommended)
2. Priority (High/Medium/Low)
3. Why use (3-5 reasons)
4. Why not use / concerns (2-3 items)
5. Best content formats (short_form/long_form/video/audio/visual/carousel/live)
6. Posting frequency
7. Content approach
8. Primary goal (awareness/leads/community/etc)
9. Success metrics (3-5)
10. Estimated effort (Small/Medium/Large)
11. Expected ROI (High/Medium/Low)

Return a JSON array with one object per platform:
[
  {{
    "platform": "platform_name",
    "fit_level": "essential|recommended|optional|not_recommended",
    "priority": "High|Medium|Low",
    "why_use": ["reason1", "reason2"],
    "why_not_use": ["concern1", "concern2"],
    "recommended_formats": ["short_form", "video"],
    "posting_frequency": "3x per week",
    "content_approach": "description",
    "primary_goal": "awareness",
    "success_metrics": ["metric1", "metric2"],
    "estimated_effort": "Medium",
    "expected_roi": "High"
  }}
]"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=6000
        )

        # Parse response — expect an array
        recs_data = self._extract_json_from_response(response)
        if isinstance(recs_data, dict):
            # Some models wrap array in a key
            recs_data = recs_data.get("recommendations", recs_data.get("platforms", [recs_data]))

        # Build a map from platform name to behavior for lookup
        behavior_map = {b.platform.value.lower(): b for b in active_platforms}

        recommendations = []
        for rec_data in recs_data:
            try:
                platform_str = rec_data.get("platform", "").lower()
                # Look up the behavior to get the PlatformName enum
                behavior = behavior_map.get(platform_str)
                if behavior is None:
                    # Try mapping the string to a platform name
                    try:
                        platform = self._map_platform_name(platform_str)
                    except Exception:  # nosec B112
                        continue
                else:
                    platform = behavior.platform

                # Map formats
                formats = []
                for fmt in rec_data.get("recommended_formats", []):
                    try:
                        formats.append(self._map_content_format(fmt))
                    except (KeyError, ValueError, AttributeError):
                        pass

                recommendation = PlatformRecommendation(
                    platform=platform,
                    fit_level=self._map_platform_fit(rec_data.get("fit_level", "optional")),
                    priority=rec_data.get("priority", "Medium"),
                    why_use=rec_data.get("why_use", []),
                    why_not_use=rec_data.get("why_not_use", []),
                    recommended_formats=formats,
                    posting_frequency=rec_data.get("posting_frequency", ""),
                    content_approach=rec_data.get("content_approach", ""),
                    primary_goal=rec_data.get("primary_goal", ""),
                    success_metrics=rec_data.get("success_metrics", []),
                    estimated_effort=rec_data.get("estimated_effort", "Medium"),
                    expected_roi=rec_data.get("expected_roi", "Medium"),
                )

                recommendations.append(recommendation)

            except Exception as e:
                print(f"Warning: Failed to create recommendation: {e}")
                continue

        # Deduplicate by platform value (case-insensitive); keep first occurrence
        seen_platforms: set = set()
        deduped: list = []
        for rec in recommendations:
            key = rec.platform.value.lower()
            if key not in seen_platforms:
                seen_platforms.add(key)
                deduped.append(rec)
        return deduped

    def _determine_platform_mix(
        self,
        client: Any,
        recommendations: List[PlatformRecommendation],
        target_audience: str,
        content_goals: str,
        posting_frequency: str = "",
    ) -> PlatformMix:
        """Determine optimal portfolio of platforms"""
        # Build context
        recs_summary = []
        for rec in recommendations:
            recs_summary.append(
                {
                    "platform": rec.platform.value,
                    "fit_level": rec.fit_level.value,
                    "priority": rec.priority,
                    "effort": rec.estimated_effort,
                    "roi": rec.expected_roi,
                }
            )

        frequency_context = (
            f"\nClient's Posting Frequency: {posting_frequency} (factor this into how many primary platforms are realistic)"
            if posting_frequency
            else ""
        )
        prompt = f"""Based on these platform recommendations, determine the optimal platform mix.

Target Audience: {target_audience}
Content Goals: {content_goals}{frequency_context}

Platform Recommendations:
{json.dumps(recs_summary, indent=2)}

Create a platform portfolio using the 70-25-5 rule:
- Primary platforms (1-2): Focus 70% of effort - essential platforms with highest ROI
- Secondary platforms (1-2): 25% of effort - supporting platforms
- Experimental platforms (0-1): 5% of effort - testing new channels
- Avoid platforms: Not worth time right now

Return JSON with:
- primary_platforms: array of platform names
- secondary_platforms: array of platform names
- experimental_platforms: array of platform names
- avoid_platforms: array of platform names
- rationale: explanation of this mix"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2000
        )

        # Parse response
        mix_data = self._extract_json_from_response(response)

        # Handle rationale - could be string or dict
        rationale = mix_data.get("rationale", "")
        if isinstance(rationale, dict):
            # If dict, convert to string (join values)
            rationale = " ".join(str(v) for v in rationale.values() if v)

        return PlatformMix(
            primary_platforms=[
                self._map_platform_name(p) for p in mix_data.get("primary_platforms", [])
            ],
            secondary_platforms=[
                self._map_platform_name(p) for p in mix_data.get("secondary_platforms", [])
            ],
            experimental_platforms=[
                self._map_platform_name(p) for p in mix_data.get("experimental_platforms", [])
            ],
            avoid_platforms=[
                self._map_platform_name(p) for p in mix_data.get("avoid_platforms", [])
            ],
            rationale=rationale,
        )

    def _create_distribution_strategy(
        self,
        client: Any,
        platform_mix: PlatformMix,
        business_description: str,
        target_audience: str,
    ) -> ContentDistribution:
        """Create content distribution and repurposing strategy"""
        all_platforms = (
            platform_mix.primary_platforms
            + platform_mix.secondary_platforms
            + platform_mix.experimental_platforms
        )

        platforms_str = ", ".join([p.value for p in all_platforms])

        prompt = f"""Create a content distribution strategy for these platforms: {platforms_str}

Business: {business_description}
Target Audience: {target_audience}

Design an efficient content creation and distribution system:
1. Where should content originate? (source platform)
2. How should content flow across platforms?
3. What's the repurposing strategy?
4. What time savings does this create?

Return JSON with:
- source_platform: where content is created first
- distribution_flow: array of strings showing content flow
- repurposing_strategy: explanation
- time_savings: explanation"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2000
        )

        # Parse response
        dist_data = self._extract_json_from_response(response)

        # Handle repurposing_strategy - could be string or dict
        repurposing_strategy = dist_data.get("repurposing_strategy", "")
        if isinstance(repurposing_strategy, dict):
            # If dict, convert to string (join values)
            repurposing_strategy = " ".join(str(v) for v in repurposing_strategy.values() if v)

        # Handle time_savings - could be string or dict
        time_savings = dist_data.get("time_savings", "")
        if isinstance(time_savings, dict):
            # If dict, convert to string (join values)
            time_savings = " ".join(str(v) for v in time_savings.values() if v)

        return ContentDistribution(
            source_platform=self._map_platform_name(dist_data.get("source_platform", "blog")),
            distribution_flow=dist_data.get("distribution_flow", []),
            repurposing_strategy=repurposing_strategy,
            time_savings=time_savings,
        )

    def _generate_quick_wins(
        self, client: Any, platform_mix: PlatformMix, recommendations: List[PlatformRecommendation]
    ) -> List[QuickWin]:
        """Identify immediate actions to get started"""
        prompt = f"""Identify 3-5 quick wins to get started on these platforms.

Primary Platforms: {', '.join([p.value for p in platform_mix.primary_platforms])}

For each quick win, provide:
1. Specific action to take
2. Timeframe (This week, Next 2 weeks, etc)
3. Expected outcome

Return JSON array with objects containing:
- platform: platform name
- action: specific action
- timeframe: when to complete
- expected_outcome: what success looks like"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2000
        )

        # Parse response
        wins_data = self._extract_json_from_response(response)

        quick_wins = []
        for win in wins_data:
            try:
                quick_wins.append(
                    QuickWin(
                        platform=self._map_platform_name(win.get("platform", "")),
                        action=win.get("action", ""),
                        timeframe=win.get("timeframe", ""),
                        expected_outcome=win.get("expected_outcome", ""),
                    )
                )
            except Exception as e:
                print(f"Warning: Skipping invalid quick win: {e}")
                continue

        return quick_wins

    def _analyze_current_state(
        self,
        client: Any,
        current_platforms: List[str],
        recommendations: List[PlatformRecommendation],
        platform_mix: PlatformMix,
    ) -> tuple[List[str], List[str]]:
        """Analyze current platform strategy"""
        current_str = ", ".join(current_platforms)
        recommended_str = ", ".join(
            [p.value for p in platform_mix.primary_platforms + platform_mix.secondary_platforms]
        )

        prompt = f"""Analyze the current platform strategy vs recommended strategy.

Current Platforms: {current_str}
Recommended Platforms: {recommended_str}

Identify:
1. What's working (3-5 strengths)
2. What's missing or needs improvement (3-5 gaps)

Return JSON with:
- strengths: array of strings
- gaps: array of strings"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2000
        )

        # Parse response
        analysis_data = self._extract_json_from_response(response)

        return (analysis_data.get("strengths", []), analysis_data.get("gaps", []))

    def _generate_strategic_insights(
        self,
        client: Any,
        business_description: str,
        target_audience: str,
        platform_mix: PlatformMix,
        recommendations: List[PlatformRecommendation],
    ) -> tuple[List[str], List[str]]:
        """Generate strategic insights and common mistakes"""
        prompt = f"""Generate strategic insights about this platform strategy.

Business: {business_description}
Target Audience: {target_audience}

Platform Mix:
- Primary: {', '.join([p.value for p in platform_mix.primary_platforms])}
- Secondary: {', '.join([p.value for p in platform_mix.secondary_platforms])}

Provide:
1. Key strategic insights (3-5 items)
2. Common mistakes to avoid (3-5 items)

Return JSON with:
- key_insights: array of strings
- mistakes_to_avoid: array of strings"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2000
        )

        # Parse response
        insights_data = self._extract_json_from_response(response)

        return (insights_data.get("key_insights", []), insights_data.get("mistakes_to_avoid", []))

    def _create_implementation_plans(
        self,
        client: Any,
        platform_mix: PlatformMix,
        recommendations: List[PlatformRecommendation],
        quick_wins: List[QuickWin],
    ) -> tuple[List[str], List[str]]:
        """Create 30-day and 90-day implementation plans"""
        prompt = f"""Create implementation plans for this platform strategy.

Platform Mix:
- Primary: {', '.join([p.value for p in platform_mix.primary_platforms])}
- Secondary: {', '.join([p.value for p in platform_mix.secondary_platforms])}

Quick Wins Already Identified: {len(quick_wins)} actions

Create:
1. 30-day plan (5-7 specific actions)
2. 90-day plan (8-10 strategic initiatives)

Return JSON with:
- thirty_day_plan: array of strings
- ninety_day_plan: array of strings"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=2000
        )

        # Parse response
        plans_data = self._extract_json_from_response(response)

        return (plans_data.get("thirty_day_plan", []), plans_data.get("ninety_day_plan", []))

    def _generate_executive_summary(
        self,
        client: Any,
        business_name: str,
        target_audience: str,
        platform_mix: PlatformMix,
        recommendations: List[PlatformRecommendation],
    ) -> str:
        """Generate executive summary"""
        prompt = f"""Write a concise executive summary (2-3 paragraphs) for this platform strategy.

Business: {business_name}
Target Audience: {target_audience}

Platform Recommendations:
- Primary: {', '.join([p.value for p in platform_mix.primary_platforms])}
- Secondary: {', '.join([p.value for p in platform_mix.secondary_platforms])}

Rationale: {platform_mix.rationale}

Summarize:
1. Where the audience is
2. Recommended platform focus
3. Expected outcomes"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], max_tokens=1000
        )

        return str(response.strip())

    def generate_reports(self, analysis: PlatformStrategyAnalysis) -> Dict[str, Path]:
        """Generate output files"""
        outputs = {}

        # JSON format
        json_path = self.output_dir / "platform_strategy.json"
        json_path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
        outputs["json"] = json_path

        # Markdown format
        markdown_path = self.output_dir / "platform_strategy_report.md"
        markdown_content = self.format_output_markdown(analysis)
        markdown_path.write_text(markdown_content, encoding="utf-8")
        outputs["markdown"] = markdown_path

        # Text format (summary)
        text_path = self.output_dir / "platform_strategy_summary.txt"
        text_content = self.format_output_text(analysis)
        text_path.write_text(text_content, encoding="utf-8")
        outputs["text"] = text_path

        return outputs

    def format_output_markdown(self, analysis: PlatformStrategyAnalysis) -> str:
        """Format as markdown report"""
        md = f"""# Platform Strategy Report

**Business:** {analysis.business_name}
**Industry:** {analysis.industry}
**Target Audience:** {analysis.target_audience}
**Analysis Date:** {analysis.analysis_date}

---

## Executive Summary

{analysis.executive_summary}

---

## Recommended Platform Mix

### Primary Platforms (70% effort)
{self._format_platform_list(analysis.recommended_platform_mix.primary_platforms)}

### Secondary Platforms (25% effort)
{self._format_platform_list(analysis.recommended_platform_mix.secondary_platforms)}

### Experimental Platforms (5% effort)
{self._format_platform_list(analysis.recommended_platform_mix.experimental_platforms)}

### Platforms to Avoid (For Now)
{self._format_platform_list(analysis.recommended_platform_mix.avoid_platforms)}

**Rationale:** {analysis.recommended_platform_mix.rationale}

---

## Audience Behavior Analysis

"""

        for behavior in analysis.audience_behavior:
            if behavior.audience_present:
                md += f"""
### {behavior.platform.value.title()}

- **Activity Level:** {behavior.activity_level}
- **Content Consumption:** {behavior.content_consumption_pattern}
- **Engagement Style:** {behavior.engagement_style}
- **Decision Makers:** {behavior.decision_maker_presence}
"""

        md += "\n---\n\n## Platform Recommendations\n\n"

        for rec in analysis.platform_recommendations:
            md += f"""
### {rec.platform.value.title()}

**Fit Level:** {rec.fit_level.value.replace('_', ' ').title()} | **Priority:** {rec.priority}

**Why Use This Platform:**
{self._format_list(rec.why_use)}

**Concerns/Limitations:**
{self._format_list(rec.why_not_use)}

**Recommended Formats:**
{self._format_list([f.value.replace('_', ' ').title() for f in rec.recommended_formats])}

**Posting Frequency:** {rec.posting_frequency}

**Content Approach:** {rec.content_approach}

**Primary Goal:** {rec.primary_goal}

**Success Metrics:**
{self._format_list(rec.success_metrics)}

**Effort Required:** {rec.estimated_effort} | **Expected ROI:** {rec.expected_roi}

---
"""

        md += f"""
## Content Distribution Strategy

**Source Platform:** {analysis.content_distribution.source_platform.value.title()}

**Distribution Flow:**
{self._format_list(analysis.content_distribution.distribution_flow)}

**Repurposing Strategy:**
{analysis.content_distribution.repurposing_strategy}

**Time Savings:**
{analysis.content_distribution.time_savings}

---

## Quick Wins

"""

        for i, win in enumerate(analysis.quick_wins, 1):
            md += f"""
**{i}. {win.platform.value.title()}**
- **Action:** {win.action}
- **Timeframe:** {win.timeframe}
- **Expected Outcome:** {win.expected_outcome}
"""

        if analysis.current_platforms:
            md += f"""
---

## Current State Analysis

**Current Platforms:** {', '.join(analysis.current_platforms)}

### What's Working
{self._format_list(analysis.current_strengths)}

### Gaps to Address
{self._format_list(analysis.current_gaps)}
"""

        md += f"""
---

## Strategic Insights

{self._format_list(analysis.key_insights)}

---

## Common Mistakes to Avoid

{self._format_list(analysis.common_mistakes_to_avoid)}

---

## Implementation Roadmap

### 30-Day Plan

{self._format_list(analysis.thirty_day_plan, numbered=True)}

### 90-Day Plan

{self._format_list(analysis.ninety_day_plan, numbered=True)}

---

*Platform Strategy Analysis - ${self.price}*
"""

        return md

    def format_output_text(self, analysis: PlatformStrategyAnalysis) -> str:
        """Format as plain text summary"""
        text = f"""PLATFORM STRATEGY SUMMARY
{'=' * 60}

Business: {analysis.business_name}
Industry: {analysis.industry}
Target Audience: {analysis.target_audience}
Date: {analysis.analysis_date}

RECOMMENDED PLATFORM MIX
{'=' * 60}

Primary (70% effort): {', '.join([p.value for p in analysis.recommended_platform_mix.primary_platforms])}
Secondary (25% effort): {', '.join([p.value for p in analysis.recommended_platform_mix.secondary_platforms])}
Experimental (5% effort): {', '.join([p.value for p in analysis.recommended_platform_mix.experimental_platforms])}
Avoid: {', '.join([p.value for p in analysis.recommended_platform_mix.avoid_platforms])}

QUICK WINS
{'=' * 60}

"""

        for i, win in enumerate(analysis.quick_wins, 1):
            text += f"{i}. {win.platform.value.title()}: {win.action}\n"
            text += f"   Timeframe: {win.timeframe}\n\n"

        text += f"""
30-DAY PLAN
{'=' * 60}

"""

        for i, item in enumerate(analysis.thirty_day_plan, 1):
            text += f"{i}. {item}\n"

        text += "\n\nFull details in platform_strategy_report.md\n"

        return text

    def _format_platform_list(self, platforms: List[PlatformName]) -> str:
        """Format platform list for markdown"""
        if not platforms:
            return "None\n"
        return "\n".join([f"- {p.value.title()}" for p in platforms])

    def _format_list(self, items: List[str], numbered: bool = False) -> str:
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
            # Look for JSON in code blocks (use greedy matching for nested structures)
            import re

            json_match = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # Try to find JSON object/array (greedy matching)
            json_match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            raise ValueError(f"Could not extract JSON from response: {text[:200]}")

    def _map_platform_name(self, name: str) -> PlatformName:
        """Map string to PlatformName enum"""
        name_lower = name.lower().strip()
        mapping = {
            "linkedin": PlatformName.LINKEDIN,
            "twitter": PlatformName.TWITTER,
            "facebook": PlatformName.FACEBOOK,
            "youtube": PlatformName.YOUTUBE,
            "tiktok": PlatformName.TIKTOK,
            "blog": PlatformName.BLOG,
            "email": PlatformName.EMAIL,
            "podcast": PlatformName.PODCAST,
        }
        return mapping.get(name_lower, PlatformName.BLOG)

    def _map_platform_fit(self, fit: str) -> PlatformFit:
        """Map string to PlatformFit enum"""
        fit_lower = fit.lower().strip().replace(" ", "_")
        mapping = {
            "essential": PlatformFit.ESSENTIAL,
            "recommended": PlatformFit.RECOMMENDED,
            "optional": PlatformFit.OPTIONAL,
            "not_recommended": PlatformFit.NOT_RECOMMENDED,
        }
        return mapping.get(fit_lower, PlatformFit.OPTIONAL)

    def _map_content_format(self, format_str: str) -> ContentFormat:
        """Map string to ContentFormat enum"""
        format_lower = format_str.lower().strip().replace(" ", "_").replace("-", "_")
        mapping = {
            "short_form": ContentFormat.SHORT_FORM,
            "long_form": ContentFormat.LONG_FORM,
            "video": ContentFormat.VIDEO,
            "audio": ContentFormat.AUDIO,
            "visual": ContentFormat.VISUAL,
            "carousel": ContentFormat.CAROUSEL,
            "live": ContentFormat.LIVE,
        }
        return mapping.get(format_lower, ContentFormat.SHORT_FORM)
