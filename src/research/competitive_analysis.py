"""Competitive Analysis Tool - $500 Add-On

Analyzes competitors' content strategies and identifies differentiation opportunities.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.competitive_analysis_models import (
    CompetitiveAnalysis,
    CompetitorProfile,
    CompetitorStrength,
    ContentGap,
    ContentType,
    DifferentiationStrategy,
    MarketPosition,
)
from ..utils.logger import logger
from ..validators.research_input_validator import (
    ResearchInputValidator,
    validate_competitor_list,
)
from ..utils.anthropic_client import get_default_client
from ..utils.web_search import get_search_client, SearchResponse
from ..utils.google_maps_search import get_google_maps_client
from .base import ResearchTool
from .validation_mixin import CommonValidationMixin
import re


def extract_json_from_response(response_text: str) -> str:
    """
    Extract JSON from Claude response, handling markdown code blocks.

    Claude often wraps JSON in ```json ... ``` blocks. This function
    extracts the JSON content, falling back to the raw response if no
    code blocks are found.

    Args:
        response_text: Raw response from Claude API

    Returns:
        Extracted JSON string
    """
    if not response_text or not response_text.strip():
        logger.warning("Empty response received, returning empty object")
        return "{}"

    # Try to extract JSON from markdown code blocks
    json_match = re.search(r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```", response_text, re.DOTALL)
    if json_match:
        return json_match.group(1)

    # Try to find JSON array or object without code blocks
    json_match = re.search(r"(\[.*\]|\{.*\})", response_text, re.DOTALL)
    if json_match:
        return json_match.group(1)

    # If no JSON found, return empty object
    logger.warning(
        f"No JSON found in response, returning empty object. Response preview: {response_text[:200]}"
    )
    return "{}"


class CompetitiveAnalyzer(ResearchTool, CommonValidationMixin):
    """Automated competitive analysis and strategy development"""

    def __init__(self, project_id: str, config: Optional[Dict[str, Any]] = None):
        """Initialize competitive analyzer with input validator"""
        super().__init__(project_id=project_id, config=config)
        self.validator = ResearchInputValidator(strict_mode=False)
        self.client = get_default_client()

    @property
    def tool_name(self) -> str:
        return "competitive_analysis"

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
        inputs["business_description"] = self.validate_business_description(inputs)

        # SECURITY: Validate target audience description
        inputs["target_audience"] = self.validate_target_audience(inputs)

        # SECURITY: Validate competitors list (1-5 competitors)
        inputs["competitors"] = validate_competitor_list(
            inputs.get("competitors"),
            validator=self.validator,
        )

        # Enforce max 5 competitors for focused analysis
        if len(inputs["competitors"]) > 5:
            raise ValueError(
                f"Maximum 5 competitors allowed (keeps analysis focused), got {len(inputs['competitors'])}"
            )

        # SECURITY: Validate optional industry
        inputs["industry"] = self.validate_optional_industry(inputs)

        # Optional: location hint improves Google Maps matching accuracy
        location = inputs.get("location")
        if location:
            inputs["location"] = location.strip()

        # Optional client brand context fields
        if "tone_to_avoid" in inputs and inputs["tone_to_avoid"]:
            inputs["tone_to_avoid"] = self.validator.validate_text(
                inputs.get("tone_to_avoid"),
                field_name="tone_to_avoid",
                min_length=2,
                max_length=500,
                required=False,
                sanitize=True,
            )
        if "measurable_results" in inputs and inputs["measurable_results"]:
            inputs["measurable_results"] = self.validator.validate_text(
                inputs.get("measurable_results"),
                field_name="measurable_results",
                min_length=2,
                max_length=1000,
                required=False,
                sanitize=True,
            )
        if "brand_personality" in inputs and inputs["brand_personality"]:
            bp = inputs["brand_personality"]
            if isinstance(bp, list):
                inputs["brand_personality"] = [
                    self.validator.validate_text(
                        t,
                        field_name="brand_personality_item",
                        min_length=1,
                        max_length=100,
                        required=False,
                        sanitize=True,
                    )
                    for t in bp
                    if t
                ]
            else:
                inputs["brand_personality"] = self.validator.validate_text(
                    bp,
                    field_name="brand_personality",
                    min_length=2,
                    max_length=500,
                    required=False,
                    sanitize=True,
                )

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> CompetitiveAnalysis:
        """Execute competitive analysis"""
        business_desc = inputs["business_description"]
        target_audience = inputs["target_audience"]
        competitors = inputs["competitors"]
        industry = inputs.get("industry", "Not specified")
        business_name = inputs.get("business_name", "Client")
        location = inputs.get("location")  # Optional location for Google Maps reviews
        tone_to_avoid = inputs.get("tone_to_avoid", "")
        measurable_results = inputs.get("measurable_results", "")
        brand_personality = inputs.get("brand_personality", "")

        logger.info(f"Analyzing {len(competitors)} competitors")

        # Step 1: Analyze each competitor
        competitor_profiles = self._analyze_competitors(
            competitors, business_desc, target_audience, industry, location
        )

        # Step 2: Identify content gaps
        content_gaps = self._identify_content_gaps(
            competitor_profiles, business_desc, target_audience
        )

        # Step 3: Generate differentiation strategies
        diff_strategies = self._generate_differentiation_strategies(
            competitor_profiles, business_desc, content_gaps
        )

        # Step 4: Develop positioning recommendation
        positioning = self._develop_positioning(
            competitor_profiles,
            business_desc,
            content_gaps,
            diff_strategies,
            tone_to_avoid=tone_to_avoid,
            measurable_results=measurable_results,
            brand_personality=brand_personality,
        )

        # Step 5: Identify quick wins
        quick_wins = self._identify_quick_wins(content_gaps, diff_strategies)

        # Step 6: Identify threats
        threats = self._identify_threats(competitor_profiles)

        # Step 7: Generate priority actions
        priority_actions = self._generate_priority_actions(
            content_gaps, diff_strategies, positioning
        )

        # Step 8: Create market summary
        market_summary = self._create_market_summary(
            competitor_profiles, content_gaps, len(competitors)
        )

        # Step 9: Assess market saturation
        market_saturation = self._assess_market_saturation(competitor_profiles)

        # Build complete analysis
        analysis = CompetitiveAnalysis(
            business_name=business_name,
            industry=industry,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            competitors=competitor_profiles,
            market_summary=market_summary,
            market_saturation=market_saturation,
            content_gaps=content_gaps,
            quick_wins=quick_wins,
            differentiation_strategies=diff_strategies,
            recommended_position=positioning,
            priority_actions=priority_actions,
            competitive_threats=threats,
        )

        return analysis

    def _analyze_competitors(
        self,
        competitors: List[str],
        business_desc: str,
        target_audience: str,
        industry: str,
        location: Optional[str] = None,
    ) -> List[CompetitorProfile]:
        """Analyze each competitor's strategy using web search + Google Maps reviews"""
        profiles = []
        search_client = get_search_client()
        maps_client = get_google_maps_client()

        for competitor in competitors[:5]:  # Max 5
            # STEP 1: Search the web for competitor information
            logger.info(f"Searching web for competitor: {competitor}")
            search_query = f"{competitor} {industry} content strategy blog social media"
            search_results = search_client.search(search_query, max_results=10)

            # STEP 1b: Targeted search for posting frequency signals
            logger.info(f"Searching posting cadence data for competitor: {competitor}")
            cadence_query = (
                f"{competitor} posting frequency content cadence how often posts per week"
            )
            cadence_results = search_client.search(cadence_query, max_results=5)

            # Format search results for prompt
            search_data = self._format_competitor_search_results(search_results, competitor)
            cadence_data = self._format_competitor_search_results(cadence_results, competitor)

            # STEP 2: Find competitor on Google Maps and get reviews.
            # Location is optional — if not provided, Maps searches by name globally.
            review_data = ""
            if maps_client:
                loc_label = f" in {location}" if location else ""
                logger.info(f"Searching Google Maps for {competitor} reviews{loc_label}")
                local_results = maps_client.search_local_businesses(
                    query=f"{competitor} {industry}",
                    location=location or "",
                    max_results=3,
                )

                # If we find a match, get reviews
                if local_results:
                    # Take the first result (best match)
                    place = local_results[0]
                    logger.info(
                        f"Found Google Maps listing: {place.name} ({place.reviews_count} reviews)"
                    )

                    if place.place_id and place.reviews_count and place.reviews_count > 0:
                        place_reviews = maps_client.get_place_reviews(
                            place_id=place.place_id, max_reviews=40
                        )

                        if place_reviews.reviews:
                            review_data = self._format_google_reviews(place_reviews)
                            logger.info(
                                f"Fetched {len(place_reviews.reviews)} reviews for analysis"
                            )

            # Add review section if available
            review_section = ""
            if review_data:
                review_section = f"""

**GOOGLE MAPS REVIEWS (Customer Feedback):**
{review_data}

Use the reviews to understand:
- Customer sentiment and satisfaction
- Common complaints or weaknesses
- Praised strengths and features
- Service quality perception
"""

            cadence_section = ""
            if cadence_results.results:
                cadence_section = f"""

**POSTING CADENCE SEARCH RESULTS (Use to estimate content_frequency):**
{cadence_data}
"""

            prompt = f"""Analyze this competitor based on the web search results and customer reviews below.

**COMPETITOR:** {competitor}

**OUR BUSINESS:** {business_desc}

**OUR TARGET AUDIENCE:** {target_audience}

**INDUSTRY:** {industry}

**WEB SEARCH RESULTS (Use ONLY these for analysis):**
{search_data}{review_section}{cadence_section}

**CRITICAL INSTRUCTIONS:**
- You MUST use ONLY the information found in the search results and reviews above
- Base your analysis on FACTUAL data from the search results, not assumptions
- When reviews are available, incorporate customer feedback into strengths/weaknesses
- For content_frequency: look for explicit statements like "posts 3x per week" OR estimate from published dates in the search results (e.g., if articles are published 2-3 days apart → "2-3x per week"; if weeks apart → "1-2x per week"; if months apart → "Monthly"). State your method: e.g., "~3x per week (estimated from article publish dates)".
- If content_frequency cannot be estimated from any signal in the results, use "Not determinable from available data" — never return just "Unknown"
- Do NOT invent or hallucinate information not present in the search results

Provide a comprehensive competitor profile including:
1. Their positioning (how they position themselves in market)
2. Their target audience
3. Content types they produce (blog, social, video, etc.)
4. Content frequency (e.g., "3-4x per week" or "~2x per week (estimated from article dates)")
5. Main content topics (5-7 topics)
6. Brand voice description
7. Tone descriptors (3-5 adjectives)
8. Strengths (3-5 things they do well)
9. Weaknesses (3-5 areas where they fall short)
10. Estimated reach (audience size)
11. Engagement level (strong/moderate/weak)

Return as JSON with keys:
positioning, target_audience, content_types (array), content_frequency, content_topics (array),
brand_voice, tone_descriptors (array), strengths (array), weaknesses (array),
estimated_reach, engagement_level

Example when data is missing:
{{
  "positioning": "Premium B2B software for enterprise teams",
  "target_audience": "Enterprise IT directors",
  "content_types": ["blog", "case studies"],
  "content_frequency": "~2x per week (estimated from article publish dates)",
  "content_topics": ["security", "compliance", "integration"],
  "brand_voice": "Professional and authoritative",
  "tone_descriptors": ["technical", "formal", "credible"],
  "strengths": ["Strong case study library", "Clear enterprise focus"],
  "weaknesses": ["Limited social media presence"],
  "estimated_reach": "Not determinable from available data",
  "engagement_level": "weak"
}}

Use "Not determinable from available data" for string fields with no data. Use [] for array fields with no data."""

            try:
                response = self.client.create_message(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2500,  # Increased from 2000 for detailed analysis
                    temperature=0.3,  # Lowered from 0.4 for factual extraction
                )

                # Parse JSON response (extract from markdown if needed)
                json_str = extract_json_from_response(response)
                data = json.loads(json_str)

                # Parse content types
                content_types = []
                for ct in data.get("content_types", []):
                    try:
                        content_types.append(ContentType(ct.lower().replace(" ", "_")))
                    except ValueError:
                        pass  # Skip invalid content types

                profile = CompetitorProfile(
                    name=competitor,
                    positioning=data.get("positioning", "Not determinable from available data"),
                    target_audience=data.get(
                        "target_audience", "Not determinable from available data"
                    ),
                    content_types=content_types,
                    content_frequency=data.get(
                        "content_frequency", "Not determinable from available data"
                    ),
                    content_topics=data.get("content_topics", [])[:7],
                    brand_voice=data.get("brand_voice", "Not determinable from available data"),
                    tone_descriptors=data.get("tone_descriptors", [])[:5],
                    strengths=data.get("strengths", [])[:5],
                    weaknesses=data.get("weaknesses", [])[:5],
                    estimated_reach=data.get(
                        "estimated_reach", "Not determinable from available data"
                    ),
                    engagement_level=CompetitorStrength(
                        data.get("engagement_level", "moderate").lower()
                        if data.get("engagement_level", "").lower()
                        in {v.value for v in CompetitorStrength}
                        else "moderate"
                    ),
                )
                profiles.append(profile)

            except Exception as e:
                logger.warning(f"Failed to analyze competitor {competitor}: {e}")
                # Create minimal profile
                profile = CompetitorProfile(
                    name=competitor,
                    positioning="Analysis unavailable",
                    target_audience="Not determinable from available data",
                    content_frequency="Not determinable from available data",
                    brand_voice="Not determinable from available data",
                    estimated_reach="Not determinable from available data",
                    engagement_level=CompetitorStrength.MODERATE,
                )
                profiles.append(profile)

        logger.info(f"Analyzed {len(profiles)} competitors")
        return profiles

    def _format_competitor_search_results(
        self, search_response: SearchResponse, competitor_name: str
    ) -> str:
        """Format search results for competitor analysis prompt"""
        if not search_response.results:
            return f"No search results found for {competitor_name}. Analysis will be limited."

        lines = []
        lines.append(
            f"Found {len(search_response.results)} search results for {competitor_name}:\n"
        )

        for i, result in enumerate(search_response.results[:10], 1):
            lines.append(f"{i}. **{result.title}**")
            lines.append(f"   URL: {result.url}")
            lines.append(f"   Description: {result.snippet}")
            if result.published_date:
                lines.append(f"   Published: {result.published_date}")
            lines.append("")

        return "\n".join(lines)

    def _format_google_reviews(self, place_reviews) -> str:
        """Format Google Maps reviews for competitor analysis"""

        if not place_reviews.reviews:
            return "No customer reviews available."

        lines = []
        place = place_reviews.place
        reviews = place_reviews.reviews

        # Summary
        lines.append(f"**{place.name}**")
        if place.rating:
            stars = "⭐" * int(place.rating)
            lines.append(
                f"Overall Rating: {place.rating}/5.0 {stars} ({place_reviews.total_reviews} total reviews)"
            )
        lines.append("")

        # Calculate review sentiment
        positive = sum(1 for r in reviews if r.rating >= 4)
        negative = sum(1 for r in reviews if r.rating <= 2)
        lines.append(
            f"Review Sentiment: {positive} positive, {negative} negative (from {len(reviews)} sampled)"
        )
        lines.append("")

        # Top reviews (mix of positive and negative for balanced view)
        positive_reviews = [r for r in reviews if r.rating >= 4][:10]
        negative_reviews = [r for r in reviews if r.rating <= 2][:10]

        if positive_reviews:
            lines.append("**Top Positive Reviews:**")
            for i, review in enumerate(positive_reviews, 1):
                stars = "⭐" * review.rating
                lines.append(f"{i}. {stars} - {review.author}")
                lines.append(f"   \"{review.text[:200]}{'...' if len(review.text) > 200 else ''}\"")
                lines.append("")

        if negative_reviews:
            lines.append("**Top Negative Reviews:**")
            for i, review in enumerate(negative_reviews, 1):
                stars = "⭐" * review.rating
                lines.append(f"{i}. {stars} - {review.author}")
                lines.append(f"   \"{review.text[:200]}{'...' if len(review.text) > 200 else ''}\"")
                lines.append("")

        return "\n".join(lines)

    def _format_trend_search_results(self, search_response: SearchResponse) -> str:
        """Format trend search results for content gap analysis"""
        if not search_response.results:
            return "No trend data found. Analysis will focus on competitor gaps only."

        lines = []
        lines.append(f"Found {len(search_response.results)} results on current market trends:\n")

        for i, result in enumerate(search_response.results[:10], 1):
            lines.append(f"{i}. {result.title}")
            lines.append(f"   {result.snippet}")
            lines.append("")

        return "\n".join(lines)

    def _identify_content_gaps(
        self,
        competitors: List[CompetitorProfile],
        business_desc: str,
        target_audience: str,
    ) -> List[ContentGap]:
        """Identify content gaps and opportunities using web search for market trends"""
        # Collect all topics competitors cover
        competitor_topics = set()
        for comp in competitors:
            competitor_topics.update(comp.content_topics)

        # STEP 1: Search for trending topics in the industry
        search_client = get_search_client()
        industry = competitors[0].positioning.split()[0] if competitors else "business"
        trend_query = f"{industry} content marketing trends topics 2026"
        logger.info(f"Searching for content trends: {trend_query}")
        trend_results = search_client.search(trend_query, max_results=10)

        # Format trend search results
        trend_data = self._format_trend_search_results(trend_results)

        competitor_detail = "\n".join(
            [
                f"- {c.name}:\n"
                f"    Topics: {', '.join(c.content_topics) or 'Unknown'}\n"
                f"    Weaknesses: {', '.join(c.weaknesses) or 'Unknown'}\n"
                f"    Brand voice: {c.brand_voice}"
                for c in competitors
            ]
        )

        prompt = f"""Identify 5-7 content gap opportunities based on the competitor analysis below and current market trends.

**CURRENT MARKET TRENDS (from web search):**
{trend_data}

Our Business: {business_desc}

Target Audience: {target_audience}

Competitor analysis (use this as the primary source):
{competitor_detail}

For each gap:
1. topic — specific topic area that is missing or underserved
2. description — MUST name the specific competitor(s) whose weaknesses or missing topics reveal this gap. Reference the competitor data above directly.
3. opportunity_score — 1-10, how valuable this gap is
4. competitors_missing — array of competitor names from the list above who don't cover this
5. suggested_content — 3 specific, publish-ready content titles (not categories)

Focus on gaps where competitors are explicitly weak or missing coverage per the data above.

Return ONLY a valid JSON array. No markdown. No explanation.

If competitor data is too sparse, return one item with opportunity_score 0 and description explaining what data was missing."""

        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2500,
                temperature=0.3,
            )

            gaps_data = json.loads(extract_json_from_response(response))
            gaps = []

            for gap_data in gaps_data[:7]:  # Max 7 gaps
                gap = ContentGap(
                    topic=gap_data["topic"],
                    description=gap_data["description"],
                    opportunity_score=float(gap_data["opportunity_score"]),
                    competitors_missing=gap_data.get("competitors_missing", []),
                    suggested_content=gap_data.get("suggested_content", [])[:3],
                )
                gaps.append(gap)

            logger.info(f"Identified {len(gaps)} content gaps")
            return gaps

        except Exception as e:
            logger.error(f"Failed to identify content gaps: {e}")
            return []

    def _generate_differentiation_strategies(
        self,
        competitors: List[CompetitorProfile],
        business_desc: str,
        content_gaps: List[ContentGap],
    ) -> List[DifferentiationStrategy]:
        """Generate ways to differentiate from competitors"""
        competitor_detail = "\n".join(
            [
                f"- {c.name}:\n"
                f"    Positioning: {c.positioning}\n"
                f"    Brand voice: {c.brand_voice}\n"
                f"    Strengths: {', '.join(c.strengths[:3]) or 'Unknown'}\n"
                f"    Weaknesses: {', '.join(c.weaknesses[:3]) or 'Unknown'}\n"
                f"    Content topics: {', '.join(c.content_topics[:5]) or 'Unknown'}"
                for c in competitors
            ]
        )

        gap_summary = (
            "\n".join(
                [
                    f"- {g.topic} (missing from: {', '.join(g.competitors_missing)}): {g.description}"
                    for g in content_gaps[:5]
                ]
            )
            or "No gaps identified"
        )

        prompt = f"""Generate 5 differentiation strategies based on the specific competitor data below.

Our Business: {business_desc}

Competitor profiles:
{competitor_detail}

Content gaps already identified:
{gap_summary}

For each strategy:
1. strategy_name — clear, concise name
2. description — MUST cite a specific named competitor from the profiles above and the exact weakness or gap being exploited. Reference the competitor's actual positioning, brand voice, or content topics. BAD: "post more consistently". GOOD: "CompanyX uses a formal/technical voice with no personality — own the approachable expert angle they've left open."
3. difficulty — Low / Medium / High
4. potential_impact — Low / Medium / High
5. examples — 2-3 specific, actionable content ideas executable in the next 30 days, each tied to the named competitor or gap

Rules:
- Every strategy MUST reference a specific named competitor from the data above
- Every example MUST be a concrete content title or campaign idea, not a category
- No generic best-practice advice

Return ONLY a valid JSON array with keys: strategy_name, description, difficulty, potential_impact, examples (array). No markdown."""

        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.6,
            )

            strategies_data = json.loads(extract_json_from_response(response))
            strategies = []

            for strat_data in strategies_data[:5]:  # Max 5 strategies
                strategy = DifferentiationStrategy(
                    strategy_name=strat_data["strategy_name"],
                    description=strat_data["description"],
                    difficulty=strat_data["difficulty"],
                    potential_impact=strat_data["potential_impact"],
                    examples=strat_data.get("examples", [])[:3],
                )
                strategies.append(strategy)

            logger.info(f"Generated {len(strategies)} differentiation strategies")
            return strategies

        except Exception as e:
            logger.error(f"Failed to generate differentiation strategies: {e}")
            return []

    def _develop_positioning(
        self,
        competitors: List[CompetitorProfile],
        business_desc: str,
        content_gaps: List[ContentGap],
        strategies: List[DifferentiationStrategy],
        tone_to_avoid: str = "",
        measurable_results: str = "",
        brand_personality: Any = "",
    ) -> MarketPosition:
        """Develop recommended market positioning"""
        comp_summary = "\n".join([f"- {c.name}: {c.positioning}" for c in competitors])
        gap_summary = "\n".join([f"- {g.topic}" for g in content_gaps[:5]])
        strat_summary = "\n".join([f"- {s.strategy_name}" for s in strategies[:3]])

        brand_lines = []
        if brand_personality:
            traits = (
                ", ".join(brand_personality)
                if isinstance(brand_personality, list)
                else brand_personality
            )
            brand_lines.append(f"Brand Personality: {traits}")
        if tone_to_avoid:
            brand_lines.append(f"Tone to Avoid: {tone_to_avoid}")
        if measurable_results:
            brand_lines.append(
                f"Proven Results: {measurable_results} — use as differentiator evidence"
            )
        brand_context = (
            "\n\nClient Brand Context (anchor positioning to these):\n" + "\n".join(brand_lines)
            if brand_lines
            else ""
        )

        prompt = f"""Develop a market positioning recommendation.

Our Business: {business_desc}{brand_context}

Competitor Positioning:
{comp_summary}

Key Content Gaps:
{gap_summary}

Differentiation Strategies:
{strat_summary}

Provide:
1. Positioning statement (1-2 sentences, clear and memorable — must contrast with at least one named competitor)
2. 3-5 unique angles to emphasize — each must name the competitor(s) that lack this angle (e.g. "Deep implementation case studies — Competitor X and Y only publish high-level thought leadership")
3. 3-5 competitive advantages — each must cite which specific competitor(s) do NOT have this advantage
4. 3-5 areas to improve — each must name the competitor that already does this well (e.g. "Video content — Competitor Z publishes 2 videos/week")

Rules:
- Every bullet in unique_angles, competitive_advantages, and areas_to_improve MUST include a named competitor as supporting evidence
- No generic observations (e.g. "be more consistent" without a named comparison)

Return as JSON with keys:
positioning_statement, unique_angles (array), competitive_advantages (array), areas_to_improve (array)"""

        try:
            data = self._call_claude_api(
                prompt,
                max_tokens=1500,
                temperature=0.5,
                extract_json=True,
                fallback_on_error={},
            )

            position = MarketPosition(
                positioning_statement=data.get("positioning_statement", ""),
                unique_angles=data.get("unique_angles", [])[:5],
                competitive_advantages=data.get("competitive_advantages", [])[:5],
                areas_to_improve=data.get("areas_to_improve", [])[:5],
            )

            return position

        except Exception as e:
            logger.error(f"Failed to develop positioning: {e}")
            # Return fallback positioning
            return MarketPosition(
                positioning_statement=f"The differentiated solution for {business_desc}",
                unique_angles=["Data-driven approach", "Customer-focused", "Innovative"],
                competitive_advantages=["Better service", "Modern technology"],
                areas_to_improve=["Brand awareness", "Content volume"],
            )

    def _identify_quick_wins(
        self, content_gaps: List[ContentGap], strategies: List[DifferentiationStrategy]
    ) -> List[str]:
        """Identify immediate opportunities"""
        quick_wins = []

        # High-scoring gaps
        for gap in content_gaps:
            if gap.opportunity_score >= 7.5:
                quick_wins.append(
                    f"Create content on '{gap.topic}' (opportunity score: {gap.opportunity_score}/10)"
                )

        # Low-difficulty, high-impact strategies
        for strategy in strategies:
            if strategy.difficulty.lower() == "low" and strategy.potential_impact.lower() in [
                "high",
                "medium",
            ]:
                quick_wins.append(
                    f"Implement: {strategy.strategy_name} ({strategy.potential_impact} impact, {strategy.difficulty} difficulty)"
                )

        return quick_wins[:7]  # Max 7 quick wins

    def _identify_threats(self, competitors: List[CompetitorProfile]) -> List[str]:
        """Identify competitive threats"""
        threats = []

        # Strong competitors with high engagement
        strong_competitors = [
            c for c in competitors if c.engagement_level == CompetitorStrength.STRONG
        ]
        if strong_competitors:
            threats.append(
                f"Strong competitors with high engagement: {', '.join([c.name for c in strong_competitors])}"
            )

        # Competitors covering many topics
        comprehensive_competitors = [c for c in competitors if len(c.content_topics) >= 6]
        if comprehensive_competitors:
            threats.append(
                f"Competitors with comprehensive content coverage: {', '.join([c.name for c in comprehensive_competitors])}"
            )

        # Competitors with high frequency
        frequent_competitors = [
            c
            for c in competitors
            if "daily" in c.content_frequency.lower() or "5" in c.content_frequency
        ]
        if frequent_competitors:
            threats.append(
                f"High-frequency content producers: {', '.join([c.name for c in frequent_competitors])}"
            )

        return threats[:5]  # Max 5 threats

    def _generate_priority_actions(
        self,
        content_gaps: List[ContentGap],
        strategies: List[DifferentiationStrategy],
        positioning: MarketPosition,
    ) -> List[str]:
        """Generate top 5 priority actions"""
        actions = []

        # Action 1: Positioning
        actions.append(f"Clarify positioning: {positioning.positioning_statement}")

        # Action 2: Top content gap
        if content_gaps:
            top_gap = max(content_gaps, key=lambda g: g.opportunity_score)
            actions.append(
                f"Fill content gap: {top_gap.topic} - {top_gap.suggested_content[0] if top_gap.suggested_content else 'Create educational content'}"
            )

        # Action 3: Top differentiation strategy
        if strategies:
            high_impact = [s for s in strategies if s.potential_impact.lower() == "high"]
            if high_impact:
                actions.append(f"Differentiate via: {high_impact[0].strategy_name}")

        # Action 4: Unique angle
        if positioning.unique_angles:
            actions.append(f"Emphasize unique angle: {positioning.unique_angles[0]}")

        # Action 5: Improvement area
        if positioning.areas_to_improve:
            actions.append(f"Improve: {positioning.areas_to_improve[0]}")

        return actions[:5]

    def _create_market_summary(
        self,
        competitors: List[CompetitorProfile],
        content_gaps: List[ContentGap],
        num_competitors: int,
    ) -> str:
        """Create market landscape summary"""
        # Analyze competitor strengths
        strong_count = sum(
            1 for c in competitors if c.engagement_level == CompetitorStrength.STRONG
        )

        # Analyze content coverage
        all_topics = set()
        for c in competitors:
            all_topics.update(c.content_topics)

        avg_opportunity = (
            sum(g.opportunity_score for g in content_gaps) / len(content_gaps)
            if content_gaps
            else 0
        )

        summary = f"""The competitive landscape includes {num_competitors} analyzed competitors. """

        if strong_count > 0:
            summary += f"{strong_count} competitors demonstrate strong market presence with high engagement levels. "

        summary += f"Competitors collectively cover {len(all_topics)} distinct content topics, indicating {'high' if len(all_topics) > 20 else 'moderate'} market maturity. "

        if content_gaps:
            summary += f"Analysis identified {len(content_gaps)} content gap opportunities with an average opportunity score of {avg_opportunity:.1f}/10, suggesting {'significant' if avg_opportunity >= 7 else 'moderate'} room for differentiation. "

        summary += "Strategic positioning focusing on underserved topics and unique value propositions will be critical for market penetration."

        return summary

    def _assess_market_saturation(self, competitors: List[CompetitorProfile]) -> str:
        """Assess how crowded the market is"""
        # Count total content types across competitors
        all_content_types = set()
        for c in competitors:
            all_content_types.update(c.content_types)

        # Count total topics
        all_topics = set()
        for c in competitors:
            all_topics.update(c.content_topics)

        # Assess saturation
        if len(all_topics) > 30 or len(all_content_types) >= 6:
            return (
                "High - Market is crowded with extensive content coverage across multiple formats"
            )
        elif len(all_topics) > 15 or len(all_content_types) >= 4:
            return "Moderate - Competitive market with established content strategies but room for differentiation"
        else:
            return "Low - Emerging market with opportunities for thought leadership and category definition"

    def generate_reports(self, analysis: CompetitiveAnalysis) -> Dict[str, Path]:
        """Generate competitive analysis reports in multiple formats"""
        output_dir = self.base_output_dir / self.tool_name / self.project_id
        output_dir.mkdir(parents=True, exist_ok=True)

        reports = {}

        # JSON report
        json_path = output_dir / "competitive_analysis.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(analysis.model_dump(), f, indent=2, default=str)
        reports["json"] = json_path

        # Markdown report
        markdown_path = output_dir / "competitive_analysis_report.md"
        markdown_content = self._format_markdown_report(analysis)
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        reports["markdown"] = markdown_path

        # Text report (executive summary)
        text_path = output_dir / "executive_summary.txt"
        text_content = self._format_text_report(analysis)
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        reports["text"] = text_path

        logger.info(f"Generated {len(reports)} report formats")
        return reports

    def _format_markdown_report(self, analysis: CompetitiveAnalysis) -> str:
        """Format analysis as markdown report"""
        md = f"""# Competitive Analysis Report

**Business:** {analysis.business_name}
**Industry:** {analysis.industry}
**Analysis Date:** {analysis.analysis_date}

---

## Executive Summary

{analysis.market_summary}

**Market Saturation:** {analysis.market_saturation}

---

## Competitor Profiles ({len(analysis.competitors)})

"""

        for i, comp in enumerate(analysis.competitors, 1):
            md += f"""
### {i}. {comp.name}

**Positioning:** {comp.positioning}

**Target Audience:** {comp.target_audience}

**Content Strategy:**
- Frequency: {comp.content_frequency}
- Types: {", ".join([ct.value for ct in comp.content_types])}
- Topics: {", ".join(comp.content_topics[:5])}

**Brand Voice:** {comp.brand_voice}

**Tone:** {", ".join(comp.tone_descriptors)}

**Engagement:** {comp.engagement_level.value.title()} ({comp.estimated_reach} reach)

**Strengths:**
"""
            for strength in comp.strengths:
                md += f"- {strength}\n"

            md += "\n**Weaknesses:**\n"
            for weakness in comp.weaknesses:
                md += f"- {weakness}\n"

        md += """
---

## Content Gap Opportunities

"""

        for i, gap in enumerate(
            sorted(analysis.content_gaps, key=lambda g: g.opportunity_score, reverse=True), 1
        ):
            md += f"""
### {i}. {gap.topic} (Score: {gap.opportunity_score}/10)

{gap.description}

**Competitors Missing:** {", ".join(gap.competitors_missing)}

**Suggested Content:**
"""
            for content in gap.suggested_content:
                md += f"- {content}\n"

        md += """
---

## Differentiation Strategies

"""

        for i, strategy in enumerate(analysis.differentiation_strategies, 1):
            md += f"""
### {i}. {strategy.strategy_name}

{strategy.description}

- **Difficulty:** {strategy.difficulty}
- **Impact:** {strategy.potential_impact}

**Examples:**
"""
            for example in strategy.examples:
                md += f"- {example}\n"

        md += f"""
---

## Recommended Market Positioning

### Positioning Statement

{analysis.recommended_position.positioning_statement}

### Unique Angles to Emphasize

"""
        for angle in analysis.recommended_position.unique_angles:
            md += f"- {angle}\n"

        md += "\n### Competitive Advantages\n\n"
        for adv in analysis.recommended_position.competitive_advantages:
            md += f"- {adv}\n"

        md += "\n### Areas to Improve\n\n"
        for area in analysis.recommended_position.areas_to_improve:
            md += f"- {area}\n"

        if analysis.quick_wins:
            md += "\n---\n\n## Quick Wins\n\n"
            for win in analysis.quick_wins:
                md += f"- {win}\n"

        if analysis.competitive_threats:
            md += "\n---\n\n## Competitive Threats\n\n"
            for threat in analysis.competitive_threats:
                md += f"- {threat}\n"

        md += """
---

## Priority Actions (Top 5)

"""
        for i, action in enumerate(analysis.priority_actions, 1):
            md += f"{i}. {action}\n"

        md += """
---

*Report generated by Competitive Analysis Tool*
"""

        return md

    def _format_text_report(self, analysis: CompetitiveAnalysis) -> str:
        """Format analysis as simple text executive summary"""
        text = f"""COMPETITIVE ANALYSIS - {analysis.business_name}
{"=" * 60}

MARKET LANDSCAPE:
{analysis.market_summary}

Market Saturation: {analysis.market_saturation}

COMPETITORS ANALYZED ({len(analysis.competitors)}):
"""

        for comp in analysis.competitors:
            text += f"- {comp.name}: {comp.positioning}\n"

        text += f"\n\nCONTENT GAPS ({len(analysis.content_gaps)}):\n"

        for gap in sorted(analysis.content_gaps, key=lambda g: g.opportunity_score, reverse=True)[
            :5
        ]:
            text += f"- {gap.topic} (Score: {gap.opportunity_score}/10)\n"

        text += "\n\nRECOMMENDED POSITIONING:\n"
        text += f"{analysis.recommended_position.positioning_statement}\n"

        text += "\n\nPRIORITY ACTIONS:\n"
        for i, action in enumerate(analysis.priority_actions, 1):
            text += f"{i}. {action}\n"

        return text
