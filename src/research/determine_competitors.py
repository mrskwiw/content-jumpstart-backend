"""
AI-powered competitor discovery and market positioning analysis.

This tool automatically identifies 3-5 key market competitors based on
a client's business description and industry, providing zero-input
competitor intelligence for strategic positioning.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.determine_competitors_models import (
    DiscoveredCompetitor,
    DetermineCompetitorsReport,
)
from ..utils.anthropic_client import get_default_client
from ..utils.logger import logger
from ..utils.web_search import get_search_client, SearchResponse
from ..utils.google_maps_search import get_google_maps_client, GoogleMapsPlace
from ..validators.research_input_validator import ResearchInputValidator
from .base import ResearchTool
from .validation_mixin import CommonValidationMixin


class CompetitorDeterminer(ResearchTool, CommonValidationMixin):
    """AI-powered competitor discovery and analysis"""

    def __init__(self, project_id: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(project_id, config)
        self.validator = ResearchInputValidator(strict_mode=False)
        self.client = get_default_client()

    @property
    def tool_name(self) -> str:
        return "determine_competitors"

    @property
    def price(self) -> int:
        return 400

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate inputs with security checks (TR-019)"""
        # Required: business_description (min 70 chars)
        inputs["business_description"] = self.validate_business_description(inputs, min_length=70)

        # Optional: industry (auto-populated from client.industry)
        inputs["industry"] = self.validate_optional_industry(inputs)

        # Optional: location (no strict validation needed)
        location = inputs.get("location")
        if location:
            inputs["location"] = location.strip()

        # Optional: business_name
        inputs["business_name"] = self.validate_optional_business_name(inputs)

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> DetermineCompetitorsReport:
        """Execute competitor discovery using Claude AI"""

        business_desc = inputs["business_description"]
        industry = inputs.get("industry") or "General business"
        business_name = inputs.get("business_name") or "Client"
        location = inputs.get("location")

        logger.info(f"Determining competitors for {business_name} in {industry}")

        # Step 1: Discover competitors using Claude AI
        discovered = self._discover_competitors_with_ai(
            business_desc, industry, business_name, location
        )

        # Step 2: Analyze competitive landscape
        landscape_summary = self._analyze_competitive_landscape(discovered, industry)

        # Step 3: Identify market gaps
        market_gaps = self._identify_market_gaps(discovered, business_desc)

        # Step 4: Generate positioning recommendation
        positioning = self._generate_positioning_recommendation(
            discovered, market_gaps, business_desc
        )

        # Build report
        report = DetermineCompetitorsReport(
            business_name=business_name,
            industry=industry,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            primary_competitors=discovered.get("primary", []),
            emerging_competitors=discovered.get("emerging", []),
            competitive_landscape_summary=landscape_summary,
            market_gaps=market_gaps,
            recommended_positioning=positioning,
        )

        return report

    def _discover_competitors_with_ai(
        self,
        business_description: str,
        industry: str,
        business_name: str,
        location: Optional[str] = None,
    ) -> Dict[str, List[DiscoveredCompetitor]]:
        """Use web search + Google Maps + Claude to identify competitors based on real-time data"""

        # Step 1: Search the web for competitors
        logger.info("Searching web for competitors...")
        search_client = get_search_client()

        # Build optimized search query
        search_query = f"{industry} companies competitors"
        if location:
            search_query += f" {location}"

        search_results = search_client.search(search_query, max_results=15)

        # Format search results for prompt
        search_data = self._format_search_results(search_results)

        # Step 2: If location provided, also search Google Maps for local competitors
        maps_data = ""
        if location:
            logger.info(f"Searching Google Maps for local competitors in {location}...")
            maps_client = get_google_maps_client()
            maps_query = f"{industry} {location}"
            local_businesses = maps_client.search_local_businesses(
                query=maps_query, location=location, max_results=10
            )

            if local_businesses:
                maps_data = self._format_google_maps_results(local_businesses)
                logger.info(f"Found {len(local_businesses)} local competitors on Google Maps")

        location_context = f"\n**Geographic Market:** {location}" if location else ""

        # Build prompt with both web search and Google Maps data
        maps_section = ""
        if maps_data:
            maps_section = f"""

**GOOGLE MAPS LOCAL COMPETITORS:**
{maps_data}
"""

        prompt = f"""Based on the web search results and local business data below, analyze this business and identify its top 3-5 market competitors.

**Business:** {business_name}
**Industry:** {industry}{location_context}
**Description:** {business_description}

**WEB SEARCH RESULTS:**
{search_data}{maps_section}

CRITICAL INSTRUCTIONS:
- Use ONLY the companies/information found in the search results above
- Prioritize LOCAL competitors from Google Maps when available (they have verified reviews/ratings)
- Identify 3-5 PRIMARY competitors (direct and adjacent) — maximum 5
- Identify 0-2 EMERGING competitors if found in search results
- Do NOT invent or hallucinate companies not in the search results
- Include Google Maps rating and review count in your analysis when available

For each competitor found in search results, provide:
- Name (exact company/brand name from search results)
- Market position (based on search result descriptions)
- Threat level (high/medium/low based on competitive overlap)
- Strength areas (2-3 specific areas where they excel, from search data)
- Differentiation opportunity (how to differentiate from them)
- Reasoning (why you identified them as a competitor, citing search results)

Return ONLY valid JSON (no markdown, no code blocks):

{{
  "primary": [
    {{
      "name": "Competitor Name",
      "market_position": "Description of positioning",
      "threat_level": "high|medium|low",
      "strength_areas": ["Area 1", "Area 2", "Area 3"],
      "differentiation_opportunity": "How to differentiate",
      "reasoning": "Why identified as competitor (cite search result)"
    }}
  ],
  "emerging": [
    // 0-2 emerging competitors from search results
  ]
}}

Your analysis:"""

        try:
            # Call Claude API with JSON extraction (increased tokens for more competitors)
            result = self._call_claude_api(
                prompt=prompt,
                max_tokens=4000,  # Increased for 5-7 competitors
                temperature=0.3,  # Lower temp for factual extraction
                extract_json=True,
                fallback_on_error={"primary": [], "emerging": []},
            )

            # Parse and validate (expecting 5-7 primary)
            primary = [
                DiscoveredCompetitor(**comp) for comp in result.get("primary", [])[:7]  # Max 7
            ]
            emerging = [
                DiscoveredCompetitor(**comp) for comp in result.get("emerging", [])[:2]  # Max 2
            ]

            logger.info(
                f"Discovered {len(primary)} primary and {len(emerging)} emerging competitors from web search"
            )

            return {"primary": primary, "emerging": emerging}

        except Exception as e:
            logger.error(f"AI competitor discovery failed: {e}", exc_info=True)
            # Fallback: Return empty lists
            return {"primary": [], "emerging": []}

    def _format_search_results(self, search_response: SearchResponse) -> str:
        """Format web search results for Claude prompt"""
        lines = []

        for i, result in enumerate(search_response.results[:15], 1):
            lines.append(f"{i}. **{result.title}**")
            lines.append(f"   URL: {result.url}")
            lines.append(f"   Description: {result.snippet}")
            if result.published_date:
                lines.append(f"   Published: {result.published_date}")
            lines.append("")

        if not lines:
            return "No search results found. Please analyze based on general market knowledge."

        return "\n".join(lines)

    def _format_google_maps_results(self, places: List[GoogleMapsPlace]) -> str:
        """Format Google Maps results for Claude prompt"""
        lines = []

        for i, place in enumerate(places, 1):
            lines.append(f"{i}. **{place.name}** ({place.category or 'Business'})")
            lines.append(f"   Address: {place.address}")

            if place.rating:
                stars = "⭐" * int(place.rating)
                lines.append(
                    f"   Rating: {place.rating}/5.0 {stars} ({place.reviews_count or 0} reviews)"
                )

            if place.website:
                lines.append(f"   Website: {place.website}")

            if place.phone:
                lines.append(f"   Phone: {place.phone}")

            lines.append("")

        if not lines:
            return "No local competitors found on Google Maps."

        return "\n".join(lines)

    def _analyze_competitive_landscape(
        self, discovered: Dict[str, List[DiscoveredCompetitor]], industry: str
    ) -> str:
        """Generate DETAILED competitive landscape analysis with ALL competitor data"""

        primary = discovered.get("primary", [])
        emerging = discovered.get("emerging", [])

        if not primary:
            return f"The {industry} market is highly fragmented with no clear dominant competitors identified."

        # Pass ALL competitor data for comprehensive analysis
        prompt = f"""Analyze the competitive landscape for the {industry} industry based on these {len(primary)} competitors.

**ALL PRIMARY COMPETITORS:**
{self._format_competitors_for_prompt(primary)}

**EMERGING COMPETITORS:**
{self._format_competitors_for_prompt(emerging) if emerging else "None identified"}

Provide a comprehensive competitive landscape analysis (4-6 paragraphs) covering:

1. **Market Structure:** How is the market organized? (fragmented vs consolidated, # of major players, market share distribution)

2. **Competitive Dynamics:** What are the key competitive factors? (price, features, brand, service, innovation)

3. **Positioning Patterns:** What common positioning strategies do competitors use? (enterprise vs SMB, vertical focus, geography)

4. **Competitive Intensity:** How intense is competition? (barriers to entry, switching costs, customer acquisition difficulty)

5. **Market Trends:** What trends are shaping competition? (consolidation, new entrants, technology shifts)

6. **Strategic Implications:** What does this mean for a new/existing player? (opportunities, threats, strategic considerations)

Be specific and cite competitor examples throughout. Make this analysis ROBUST and actionable.

Your detailed analysis:"""

        try:
            summary = self._call_claude_api(
                prompt=prompt,
                max_tokens=2000,  # Much longer for detailed analysis
                temperature=0.4,
                extract_json=False,
            )

            return str(summary).strip()

        except Exception as e:
            logger.error(f"Landscape analysis failed: {e}")
            competitor_names = [comp.name for comp in primary[:3]]
            return f"The {industry} market features established competitors including {', '.join(competitor_names)}."

    def _identify_market_gaps(
        self, discovered: Dict[str, List[DiscoveredCompetitor]], business_desc: str
    ) -> List[str]:
        """Identify market gaps and positioning opportunities"""

        primary = discovered.get("primary", [])

        if not primary:
            return [
                "First-mover advantage in underserved market",
                "Opportunity to define category positioning",
                "Potential to establish thought leadership",
            ]

        prompt = f"""Based on these competitors and the business description, identify 3-5 unmet market needs or positioning opportunities.

**Business Description:** {business_desc}

**Competitors:**
{self._format_competitors_for_prompt(primary)}

Identify gaps like:
- Underserved customer segments
- Unmet needs or pain points
- Differentiation opportunities
- Positioning white space

Return ONLY a JSON array of 3-5 gap descriptions:
["Gap 1", "Gap 2", "Gap 3", "Gap 4", "Gap 5"]

Your analysis:"""

        try:
            result = self._call_claude_api(
                prompt=prompt,
                max_tokens=800,
                temperature=0.4,
                extract_json=True,
                fallback_on_error=[],
            )

            # Handle both array and dict responses
            if isinstance(result, list):
                gaps = result[:5]
            elif isinstance(result, dict) and "gaps" in result:
                gaps = result["gaps"][:5]
            else:
                gaps = []

            return gaps if gaps else ["Market positioning opportunity identified"]

        except Exception as e:
            logger.error(f"Gap analysis failed: {e}")
            return ["Market positioning opportunity identified"]

    def _generate_positioning_recommendation(
        self,
        discovered: Dict[str, List[DiscoveredCompetitor]],
        market_gaps: List[str],
        business_desc: str,
    ) -> str:
        """Generate positioning recommendation based on competitive gaps"""

        primary = discovered.get("primary", [])

        if not primary:
            return "Position as a category leader in this emerging market, focusing on unique value proposition and target audience needs."

        prompt = f"""Based on the competitive analysis and market gaps, write a competitive positioning recommendation.

**Business Description:** {business_desc}

**Market Gaps:**
{chr(10).join(f'- {gap}' for gap in market_gaps[:3])}

**Key Competitors:**
{self._format_competitors_for_prompt(primary[:3])}

Write a positioning recommendation that:
- Identifies the 2-3 most important market gaps
- States how to differentiate from each named competitor
- Provides a clear positioning statement

Format as plain prose paragraphs. Do NOT use Markdown headers (##, ###), bullet lists, or code blocks.
Write 3-5 complete paragraphs and end with a clear, complete sentence."""

        try:
            recommendation = self._call_claude_api(
                prompt=prompt, max_tokens=2000, temperature=0.4, extract_json=False
            )

            return str(recommendation).strip()

        except Exception as e:
            logger.error(f"Positioning recommendation failed: {e}")
            return "Differentiate by focusing on underserved market segments and unique value proposition."

    def _format_competitors_for_prompt(self, competitors: List[DiscoveredCompetitor]) -> str:
        """Format competitors for Claude prompts"""
        lines = []
        for comp in competitors:
            lines.append(f"- **{comp.name}**: {comp.market_position}")
            lines.append(f"  Strengths: {', '.join(comp.strength_areas)}")
        return "\n".join(lines)

    def generate_reports(self, analysis: DetermineCompetitorsReport) -> Dict[str, Path]:
        """Generate output files (JSON, Markdown, Text)"""

        # JSON: Full structured data
        json_path = self._save_json(analysis.model_dump(), "competitors.json")

        # Markdown: Formatted report
        markdown_content = self._format_markdown_report(analysis)
        markdown_path = self._save_markdown(markdown_content, "competitors_report.md")

        # Text: Executive summary
        text_content = self._format_executive_summary(analysis)
        text_path = self._save_text(text_content, "competitors_summary.txt")

        return {"json": json_path, "markdown": markdown_path, "text": text_path}

    def _format_markdown_report(self, analysis: DetermineCompetitorsReport) -> str:
        """Generate detailed markdown report"""

        lines = []

        # Header
        lines.append(
            self._create_markdown_header(
                f"Competitor Discovery Report: {analysis.business_name}", level=1
            )
        )
        lines.append(f"**Industry:** {analysis.industry}\n")
        lines.append(f"**Analysis Date:** {analysis.analysis_date}\n")

        # Landscape Summary
        lines.append(self._create_markdown_header("Competitive Landscape", level=2))
        lines.append(f"{analysis.competitive_landscape_summary}\n")

        # Primary Competitors
        if analysis.primary_competitors:
            lines.append(self._create_markdown_header("Primary Competitors", level=2))
            for comp in analysis.primary_competitors:
                lines.append(
                    self._create_markdown_header(
                        f"{comp.name} ({comp.threat_level.upper()} Threat)", level=3
                    )
                )
                lines.append(f"**Market Position:** {comp.market_position}\n")
                lines.append(f"**Strengths:** {', '.join(comp.strength_areas[:3])}\n")
                lines.append(
                    f"**Differentiation Opportunity:** {comp.differentiation_opportunity}\n"
                )
                lines.append(f"**Analysis:** {comp.reasoning}\n")

        # Emerging Competitors
        if analysis.emerging_competitors:
            lines.append(self._create_markdown_header("Emerging Competitors to Watch", level=2))
            for comp in analysis.emerging_competitors:
                lines.append(f"- **{comp.name}**: {comp.market_position}\n")

        # Market Gaps
        if analysis.market_gaps:
            lines.append(self._create_markdown_header("Market Gaps & Opportunities", level=2))
            lines.append(self._format_markdown_list(analysis.market_gaps))

        # Positioning Recommendation
        lines.append(self._create_markdown_header("Recommended Positioning", level=2))
        lines.append(f"{analysis.recommended_positioning}\n")

        return "".join(lines)

    def _format_executive_summary(self, analysis: DetermineCompetitorsReport) -> str:
        """Generate concise executive summary"""

        lines = []

        lines.append(f"COMPETITOR DISCOVERY REPORT: {analysis.business_name}\n")
        lines.append(f"Industry: {analysis.industry}\n")
        lines.append(f"Analysis Date: {analysis.analysis_date}\n")
        lines.append("=" * 60 + "\n\n")

        # Competitive Landscape
        lines.append("COMPETITIVE LANDSCAPE\n")
        lines.append(f"{analysis.competitive_landscape_summary}\n\n")

        # Primary Competitors
        if analysis.primary_competitors:
            lines.append(f"PRIMARY COMPETITORS ({len(analysis.primary_competitors)})\n")
            for i, comp in enumerate(analysis.primary_competitors, 1):
                lines.append(f"{i}. {comp.name} ({comp.threat_level.upper()} threat)\n")
                lines.append(f"   {comp.market_position}\n")
                lines.append(f"   Differentiate by: {comp.differentiation_opportunity}\n\n")

        # Positioning
        lines.append("RECOMMENDED POSITIONING\n")
        lines.append(f"{analysis.recommended_positioning}\n")

        return "".join(lines)
