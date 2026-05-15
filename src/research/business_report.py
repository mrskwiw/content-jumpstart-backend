"""Business Report Tool - Research Add-On

Analyzes company perception, strengths, pain points, and value proposition
using web searches and Google Maps reviews with AI-powered synthesis.

Price: 50 credits (~$100-125, replaces 3-4 hours of market research)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.business_report_models import (
    BusinessReportOutput,
    get_analysis_date,
)
from ..utils.logger import logger
from ..utils.web_search import get_search_client
from ..utils.google_maps_search import get_google_maps_client
from .base import ResearchTool
from .validation_mixin import CommonValidationMixin


class BusinessReportTool(ResearchTool, CommonValidationMixin):
    """Business report generator for company analysis

    This tool:
    1. Searches the web for company information, reviews, and mentions
    2. Pulls Google Maps reviews (if business has a listing)
    3. Uses AI to synthesize findings into actionable insights:
       - How the company is perceived
       - Strengths to advertise
       - Customer pain points
       - Problems the company solves
    """

    @property
    def tool_name(self) -> str:
        return "business_report"

    @property
    def price(self) -> int:
        """Price in credits (50 credits ~ $100-125)"""
        return 50

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate required inputs

        Required:
        - company_name: Name of the company
        - location: Location of the company

        Optional:
        - max_web_results: Maximum web search results (default: 10)
        - max_reviews: Maximum Google Maps reviews (default: 50)

        Security:
        - Max length checks (prevent DOS)
        - Prompt injection sanitization
        - Type validation
        """
        # Required: company_name
        company_name = inputs.get("company_name")
        if not company_name:
            raise ValueError("company_name is required")

        if not isinstance(company_name, str):
            raise ValueError("company_name must be a string")

        company_name = company_name.strip()
        if not company_name:
            raise ValueError("company_name cannot be empty")

        if len(company_name) < 2:
            raise ValueError("company_name is too short (minimum 2 characters)")

        if len(company_name) > 200:
            raise ValueError("company_name too long (max 200 characters)")

        inputs["company_name"] = company_name

        # Required: location
        location = inputs.get("location")
        if not location:
            raise ValueError("location is required")

        if not isinstance(location, str):
            raise ValueError("location must be a string")

        location = location.strip()
        if not location:
            raise ValueError("location cannot be empty")

        if len(location) < 2:
            raise ValueError("location is too short (minimum 2 characters)")

        if len(location) > 200:
            raise ValueError("location too long (max 200 characters)")

        inputs["location"] = location

        # Optional: max_web_results
        max_web_results = inputs.get("max_web_results", 10)
        if not isinstance(max_web_results, int):
            try:
                max_web_results = int(max_web_results)
            except (ValueError, TypeError):
                raise ValueError("max_web_results must be an integer")

        if not 1 <= max_web_results <= 50:
            raise ValueError("max_web_results must be between 1 and 50")

        inputs["max_web_results"] = max_web_results

        # Optional: max_reviews
        max_reviews = inputs.get("max_reviews", 50)
        if not isinstance(max_reviews, int):
            try:
                max_reviews = int(max_reviews)
            except (ValueError, TypeError):
                raise ValueError("max_reviews must be an integer")

        if not 1 <= max_reviews <= 200:
            raise ValueError("max_reviews must be between 1 and 200")

        inputs["max_reviews"] = max_reviews

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> BusinessReportOutput:
        """Execute business report analysis

        Steps:
        1. Web search for company information
        2. Google Maps search for reviews
        3. AI synthesis into structured insights
        """
        company_name = inputs["company_name"]
        location = inputs["location"]
        max_web_results = inputs.get("max_web_results", 10)
        max_reviews = inputs.get("max_reviews", 50)

        logger.info(f"Generating business report for {company_name} in {location}")

        # Step 1: Web search for company information
        web_results = self._search_web(company_name, location, max_web_results)

        # Bug #148: warn when zero location-specific results were found — this
        # usually means the client's location is missing and all results may describe
        # a different business sharing the same name.
        if not web_results:
            logger.warning(
                f"Business Report: no location-matched web results for '{company_name}' in "
                f"'{location}'. Report may reflect a similarly-named business. Ensure the "
                f"client's location is set correctly in their profile."
            )

        # Bug #148: inject known staff names from client brief so Claude can cross-check.
        # The business_description and founder_name fields are injected by research_service
        # via the standard inputs dict — pass them to the synthesis step as context.
        known_staff_hint = inputs.get("founder_name") or ""
        if not known_staff_hint:
            # Try to extract from business_description ("Dr. Kim", "Dr. Smith", etc.)
            import re as _re

            desc = inputs.get("business_description", "")
            names = _re.findall(r"\bDr\.?\s+[A-Z][a-z]+\b", desc)
            known_staff_hint = ", ".join(dict.fromkeys(names))  # unique, ordered

        # Step 2: Google Maps search for reviews
        maps_data = self._search_google_maps(company_name, location, max_reviews)

        # Step 3: AI synthesis — pass known staff names so Claude can flag mismatches
        report = self._synthesize_report(
            company_name,
            location,
            web_results,
            maps_data,
            known_staff_hint=known_staff_hint,
        )

        logger.info(f"Business report generated for {company_name}")
        return report

    def _search_web(
        self,
        company_name: str,
        location: str,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Search the web for company information

        Args:
            company_name: Name of company
            location: Location of company
            max_results: Maximum results to return

        Returns:
            List of search results with title, snippet, url
        """
        try:
            logger.info(f"Searching web for {company_name} in {location}")

            search_client = get_search_client()

            # Bug #148: include authoritative review sites and location in query so results
            # are specific to this client's location, not other businesses sharing the name.
            query = (
                f'"{company_name}" {location} reviews'
                f" site:google.com OR site:yelp.com OR site:healthgrades.com"
                f" OR site:zocdoc.com OR site:facebook.com"
            )

            response = search_client.search(query, max_results=max_results)

            # Bug #148: Filter results to those that reference the client's location.
            # This prevents data from a similarly-named business in another city from
            # contaminating the report (e.g., multiple "Cascade Family Dentistry" chains).
            location_tokens = {
                tok.lower() for tok in location.replace(",", " ").split() if len(tok) > 2
            }
            results: List[Dict[str, Any]] = []
            for result in response.results:
                combined = (result.title + " " + result.snippet).lower()
                # Keep result if any location token appears in title+snippet, or if we have < 3 results
                if any(tok in combined for tok in location_tokens) or len(results) < 3:
                    results.append(
                        {
                            "title": result.title,
                            "snippet": result.snippet,
                            "url": result.url,
                        }
                    )

            if len(results) < len(response.results):
                logger.info(
                    f"Business Report: filtered {len(response.results) - len(results)} results "
                    f"not matching location '{location}' (prevents data from similarly-named businesses)"
                )

            logger.info(f"Found {len(results)} web results")
            return results

        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return []

    def _search_google_maps(
        self,
        company_name: str,
        location: str,
        max_reviews: int,
    ) -> Dict[str, Any]:
        """Search Google Maps for business and reviews

        Args:
            company_name: Name of company
            location: Location of company
            max_reviews: Maximum reviews to fetch

        Returns:
            Dictionary with:
            - place_id: Google Maps place ID (if found)
            - rating: Average rating
            - total_reviews: Total review count
            - reviews: List of reviews with text, rating, date
        """
        try:
            logger.info(f"Searching Google Maps for {company_name} in {location}")

            maps_client = get_google_maps_client()

            # Search for the business
            query = f"{company_name} {location}"
            places = maps_client.search_local_businesses(query, location, max_results=1)

            if not places:
                logger.warning("No Google Maps listing found")
                return {
                    "place_id": None,
                    "rating": None,
                    "total_reviews": None,
                    "reviews": [],
                }

            # Get the first (best match) place
            place = places[0]
            place_id = place.place_id

            if not place_id:
                logger.warning("No place_id in Google Maps result")
                return {
                    "place_id": None,
                    "rating": place.rating,
                    "total_reviews": place.reviews_count,
                    "reviews": [],
                }

            # Fetch reviews for the place
            reviews_data = maps_client.get_place_reviews(place_id, max_reviews=max_reviews)

            reviews = []
            for review in reviews_data.reviews:
                reviews.append(
                    {
                        "text": review.text,
                        "rating": review.rating,
                        "date": review.date or "",
                        "author": review.author,
                    }
                )

            result = {
                "place_id": place_id,
                "rating": place.rating,
                "total_reviews": place.reviews_count,
                "reviews": reviews,
            }

            logger.info(f"Found {len(reviews)} Google Maps reviews")
            return result

        except Exception as e:
            logger.warning(f"Google Maps search failed: {e}")
            return {
                "place_id": None,
                "rating": None,
                "total_reviews": None,
                "reviews": [],
            }

    def _synthesize_report(
        self,
        company_name: str,
        location: str,
        web_results: List[Dict[str, Any]],
        maps_data: Dict[str, Any],
        known_staff_hint: str = "",
    ) -> BusinessReportOutput:
        """Synthesize web and maps data into structured business report

        Uses Claude AI to analyze all data and extract:
        - Overall perception
        - Perception score (0-100)
        - Perception insights
        - Top strengths to advertise
        - Customer pain points
        - Problems solved

        Args:
            company_name: Name of company
            location: Location of company
            web_results: List of web search results
            maps_data: Google Maps data with reviews

        Returns:
            BusinessReportOutput with structured analysis
        """
        logger.info("Synthesizing business report with AI")

        # Prepare data for AI analysis
        web_summary = self._format_web_results(web_results)
        reviews_summary = self._format_reviews(maps_data.get("reviews", []))

        # Build analysis prompt — include known staff hint for entity verification (Bug #148)
        prompt = self._build_analysis_prompt(
            company_name,
            location,
            web_summary,
            reviews_summary,
            maps_data.get("rating"),
            maps_data.get("total_reviews"),
            known_staff_hint=known_staff_hint,
        )

        # Call Claude API with JSON extraction
        try:
            analysis_json = self._call_claude_api(
                prompt=prompt,
                max_tokens=4000,
                temperature=0.4,
                extract_json=True,
            )

            # Add metadata fields
            analysis_json["company_name"] = company_name
            analysis_json["location"] = location
            analysis_json["web_sources_analyzed"] = len(web_results)
            analysis_json["reviews_analyzed"] = len(maps_data.get("reviews", []))
            analysis_json["average_rating"] = maps_data.get("rating")
            analysis_json["total_reviews"] = maps_data.get("total_reviews")
            analysis_json["analysis_date"] = get_analysis_date()

            # Parse into Pydantic model
            report = BusinessReportOutput(**analysis_json)

            logger.info("Business report synthesis complete")
            return report

        except Exception as e:
            logger.error(f"AI synthesis failed: {e}")

            # Return minimal report on failure
            return BusinessReportOutput(
                company_name=company_name,
                location=location,
                overall_perception="Analysis failed - insufficient data available",
                perception_score=0,
                perception_insights=[],
                top_strengths=[],
                customer_pain_points=[],
                problems_solved=[],
                web_sources_analyzed=len(web_results),
                reviews_analyzed=len(maps_data.get("reviews", [])),
                average_rating=maps_data.get("rating"),
                total_reviews=maps_data.get("total_reviews"),
                analysis_date=get_analysis_date(),
                confidence_level="Low",
            )

    def _format_web_results(self, results: List[Dict[str, Any]]) -> str:
        """Format web search results for AI prompt"""
        if not results:
            return "No web results available."

        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(
                f"{i}. {result.get('title', 'No title')}\n"
                f"   {result.get('snippet', 'No description')}\n"
                f"   URL: {result.get('url', 'N/A')}"
            )

        return "\n\n".join(formatted)

    def _format_reviews(self, reviews: List[Dict[str, Any]]) -> str:
        """Format Google Maps reviews for AI prompt"""
        if not reviews:
            return "No reviews available."

        formatted = []
        for i, review in enumerate(reviews, 1):
            rating_stars = "⭐" * review.get("rating", 0)
            formatted.append(
                f"{i}. {rating_stars} ({review.get('rating', 'N/A')}/5) - {review.get('author', 'Anonymous')}\n"
                f"   \"{review.get('text', 'No review text')}\""
            )

        return "\n\n".join(formatted)

    def _build_analysis_prompt(
        self,
        company_name: str,
        location: str,
        web_summary: str,
        reviews_summary: str,
        avg_rating: Optional[float],
        total_reviews: Optional[int],
        known_staff_hint: str = "",
    ) -> str:
        """Build AI analysis prompt for business report synthesis"""

        # Get JSON schema for validation
        schema = BusinessReportOutput.model_json_schema()

        # Remove metadata fields that we'll add manually
        schema_str = json.dumps(schema, indent=2)

        # Bug #148: warn Claude about entity disambiguation when a known staff name exists
        entity_guard = ""
        if known_staff_hint:
            entity_guard = (
                f"\nIMPORTANT — ENTITY VERIFICATION: The client's known staff include: {known_staff_hint}. "
                f"If the web results or reviews mention different staff names (e.g. dentists, doctors) "
                f"not matching these, those results likely describe a DIFFERENT business sharing the "
                f"same name. Exclude quotes, reviews, or data that reference unrecognised staff names "
                f"— only synthesise information that plausibly describes THIS specific practice.\n"
            )

        prompt = f"""You are a business analyst specializing in market perception and competitive positioning.

Analyze the following data about {company_name} in {location} and provide a comprehensive business report.
{entity_guard}
WEB SEARCH RESULTS ({len(web_summary.split('URL:'))} sources):
{web_summary}

GOOGLE MAPS REVIEWS (Average: {avg_rating or 'N/A'}/5, Total Reviews: {total_reviews or 'N/A'}):
{reviews_summary}

Provide a comprehensive business report analysis with these sections:

1. PERCEPTION ANALYSIS
   - overall_perception: 2-3 sentence summary of how the company is viewed
   - perception_score: 0-100 score (100 = excellent reputation)
   - perception_insights: 3-5 specific insights categorized as positive/negative/neutral
     Each insight should include:
     * category: "positive", "negative", or "neutral"
     * insight: The specific perception point
     * source_count: Approximate number of sources mentioning this (estimate from reviews/web)
     * confidence: "High", "Medium", or "Low"

2. STRENGTHS TO ADVERTISE
   - Identify 3-5 core strengths this company should promote
   - For each strength provide:
     * strength: The strength or differentiator
     * evidence: List of 2-4 supporting evidence points from sources
     * recommended_messaging: How to message this in marketing (1-2 sentences)
     * target_audience: Who this resonates with

3. CUSTOMER PAIN POINTS
   - Identify 3-5 key pain points from customer feedback
   - For each pain point:
     * pain_point: Description of the pain point
     * frequency: "High", "Medium", or "Low" (how often mentioned)
     * severity: "High", "Medium", or "Low" (impact level)
     * customer_quotes: List of 1-3 direct quotes mentioning this (if available)

4. PROBLEMS SOLVED
   - Identify 3-5 problems the company solves for customers
   - For each problem:
     * problem: The problem description
     * solution_approach: How the company solves it
     * value_proposition: The value delivered
     * differentiation: How this differs from competitors

5. CONFIDENCE LEVEL
   - confidence_level: "High", "Medium", or "Low" based on data quality and quantity

IMPORTANT INSTRUCTIONS:
- ONLY use information from the provided sources above
- Do NOT invent or hallucinate insights not supported by the data
- If data is limited, reflect that in lower confidence levels and fewer insights
- Extract direct quotes from reviews when available for customer_quotes
- Be specific and actionable in recommendations
- Return ONLY valid JSON matching this schema (no markdown, no explanatory text):

{schema_str}

Return your analysis as valid JSON only:"""

        return prompt

    def generate_reports(self, analysis: BusinessReportOutput) -> Dict[str, Path]:
        """Generate output files

        Creates:
        - JSON: Machine-readable structured data
        - Markdown: Human-readable formatted report
        - TXT: Plain text summary

        Args:
            analysis: BusinessReportOutput from run_analysis()

        Returns:
            Dictionary mapping format to file path
        """
        logger.info("Generating business report output files")

        outputs = {}

        # JSON output (full structured data)
        json_path = self._save_json(
            analysis.model_dump(),
            f"business_report_{analysis.company_name.lower().replace(' ', '_')}.json",
        )
        outputs["json"] = json_path

        # Markdown output (formatted report)
        markdown_content = self._format_markdown_report(analysis)
        markdown_path = self._save_markdown(
            markdown_content,
            f"business_report_{analysis.company_name.lower().replace(' ', '_')}.md",
        )
        outputs["markdown"] = markdown_path

        # Text output (plain text summary)
        text_content = self._format_text_report(analysis)
        text_path = self._save_text(
            text_content,
            f"business_report_{analysis.company_name.lower().replace(' ', '_')}.txt",
        )
        outputs["txt"] = text_path

        logger.info(f"Generated {len(outputs)} output files")
        return outputs

    def _format_markdown_report(self, report: BusinessReportOutput) -> str:
        """Format business report as Markdown"""

        sections = []

        # Header
        sections.append(
            self._create_markdown_header(f"Business Report: {report.company_name}", level=1)
        )
        sections.append(f"**Location:** {report.location}\n")
        sections.append(f"**Analysis Date:** {report.analysis_date}\n")
        sections.append(f"**Confidence Level:** {report.confidence_level}\n\n")

        # Data sources
        sections.append(self._create_markdown_header("Data Sources", level=2))
        sections.append(f"- Web sources analyzed: {report.web_sources_analyzed}\n")
        sections.append(f"- Reviews analyzed: {report.reviews_analyzed}\n")
        if report.average_rating:
            sections.append(f"- Average rating: {report.average_rating:.1f}/5.0\n")
        if report.total_reviews:
            sections.append(f"- Total reviews: {report.total_reviews}\n")
        sections.append("\n")

        # Executive Summary
        sections.append(self._create_markdown_header("Executive Summary", level=2))
        sections.append(f"**Perception Score:** {report.perception_score}/100\n\n")
        sections.append(f"{report.overall_perception}\n\n")

        # Perception Insights
        sections.append(self._create_markdown_header("Perception Analysis", level=2))
        for insight in report.perception_insights:
            emoji = (
                "✅"
                if insight.category == "positive"
                else "⚠️" if insight.category == "negative" else "ℹ️"
            )
            sections.append(
                f"{emoji} **{insight.category.title()}** (Confidence: {insight.confidence})\n"
            )
            sections.append(f"- {insight.insight}\n")
            sections.append(f"- Mentioned by {insight.source_count} sources\n\n")

        # Strengths to Advertise
        sections.append(self._create_markdown_header("Strengths to Advertise", level=2))
        for i, strength in enumerate(report.top_strengths, 1):
            sections.append(self._create_markdown_header(f"{i}. {strength.strength}", level=3))
            sections.append(f"**Target Audience:** {strength.target_audience}\n\n")
            sections.append(f"**Recommended Messaging:**\n{strength.recommended_messaging}\n\n")
            sections.append("**Evidence:**\n")
            sections.append(self._format_markdown_list(strength.evidence))
            sections.append("\n")

        # Customer Pain Points
        sections.append(self._create_markdown_header("Customer Pain Points", level=2))
        for i, pain in enumerate(report.customer_pain_points, 1):
            sections.append(self._create_markdown_header(f"{i}. {pain.pain_point}", level=3))
            sections.append(f"**Frequency:** {pain.frequency} | **Severity:** {pain.severity}\n\n")
            if pain.customer_quotes:
                sections.append("**Customer Quotes:**\n")
                for quote in pain.customer_quotes:
                    sections.append(f'> "{quote}"\n\n')

        # Problems Solved
        sections.append(self._create_markdown_header("Problems Solved", level=2))
        for i, problem in enumerate(report.problems_solved, 1):
            sections.append(self._create_markdown_header(f"{i}. {problem.problem}", level=3))
            sections.append(f"**Solution Approach:** {problem.solution_approach}\n\n")
            sections.append(f"**Value Proposition:** {problem.value_proposition}\n\n")
            sections.append(f"**Differentiation:** {problem.differentiation}\n\n")

        return "".join(sections)

    def _format_text_report(self, report: BusinessReportOutput) -> str:
        """Format business report as plain text"""

        lines = []

        # Header
        lines.append("=" * 80)
        lines.append(f"BUSINESS REPORT: {report.company_name.upper()}")
        lines.append("=" * 80)
        lines.append(f"Location: {report.location}")
        lines.append(f"Analysis Date: {report.analysis_date}")
        lines.append(f"Confidence Level: {report.confidence_level}")
        lines.append(f"Perception Score: {report.perception_score}/100")
        lines.append("")

        # Executive Summary
        lines.append("-" * 80)
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        lines.append(report.overall_perception)
        lines.append("")

        # Strengths
        lines.append("-" * 80)
        lines.append("TOP STRENGTHS TO ADVERTISE")
        lines.append("-" * 80)
        for i, strength in enumerate(report.top_strengths, 1):
            lines.append(f"\n{i}. {strength.strength}")
            lines.append(f"   Target Audience: {strength.target_audience}")
            lines.append(f"   Messaging: {strength.recommended_messaging}")
        lines.append("")

        # Pain Points
        lines.append("-" * 80)
        lines.append("CUSTOMER PAIN POINTS")
        lines.append("-" * 80)
        for i, pain in enumerate(report.customer_pain_points, 1):
            lines.append(f"\n{i}. {pain.pain_point}")
            lines.append(f"   Frequency: {pain.frequency} | Severity: {pain.severity}")
        lines.append("")

        # Problems Solved
        lines.append("-" * 80)
        lines.append("PROBLEMS SOLVED")
        lines.append("-" * 80)
        for i, problem in enumerate(report.problems_solved, 1):
            lines.append(f"\n{i}. {problem.problem}")
            lines.append(f"   Value: {problem.value_proposition}")
        lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)
