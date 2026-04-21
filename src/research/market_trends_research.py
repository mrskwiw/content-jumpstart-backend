"""Market Trends Research Tool - $400 Add-On

Identifies trending topics and emerging conversations in the client's industry.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.market_trends_models import (
    EmergingConversation,
    SeasonalTrend,
    Trend,
    TrendCategory,
    TrendMomentum,
    TrendRelevance,
    TrendReport,
)
from ..utils.logger import logger
from ..validators.research_input_validator import ResearchInputValidator
from ..utils.anthropic_client import get_default_client
from ..utils.google_maps_search import get_google_maps_client
from ..utils.web_search import get_search_client
from .base import ResearchTool
from .validation_mixin import CommonValidationMixin


class MarketTrendsResearcher(ResearchTool, CommonValidationMixin):
    """Automated market trends research and analysis"""

    def __init__(self, project_id: str, config: Optional[Dict[str, Any]] = None):
        """Initialize Market Trends Researcher with input validator"""
        super().__init__(project_id, config)
        self.validator = ResearchInputValidator(strict_mode=False)
        self.client = get_default_client()

    @staticmethod
    def _safe_join(items: List[Any], separator: str = ", ") -> str:
        """
        Safely join a list of items (strings or dicts) into a comma-separated string.

        Handles both string items and dict items (extracts 'name' or 'title' field).
        This fixes Bug #37 - handles dicts passed instead of strings.

        Args:
            items: List of strings or dicts
            separator: String to use between items

        Returns:
            Comma-separated string
        """
        if not items:
            return ""

        str_items = []
        for item in items:
            if isinstance(item, dict):
                # Extract name/title from dict, or convert to string
                str_items.append(item.get("name") or item.get("title") or str(item))
            else:
                str_items.append(str(item))

        return separator.join(str_items)

    @property
    def tool_name(self) -> str:
        return "market_trends_research"

    @property
    def price(self) -> int:
        return 400

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """
        Validate required inputs with comprehensive security checks

        Security improvements:
        - Max length validation (prevent DOS)
        - Prompt injection sanitization
        - Type validation
        - Field presence checks

        NEW: Auto-generates focus_areas from SEO keywords if available
        NEW: Industry is now optional - pulls from database if not provided
        """
        # SECURITY: Validate business description with sanitization
        inputs["business_description"] = self.validate_business_description(inputs)

        # SECURITY: Validate industry with sanitization (NOW OPTIONAL - auto from DB)
        if "industry" in inputs and inputs["industry"]:
            inputs["industry"] = self.validator.validate_text(
                inputs.get("industry"),
                field_name="industry",
                min_length=2,
                max_length=200,
                required=False,  # Changed to optional - will pull from DB
                sanitize=True,
            )
        else:
            # Will be set from database in run_analysis
            inputs["industry"] = None

        # SECURITY: Validate target audience with sanitization
        inputs["target_audience"] = self.validate_target_audience(inputs)

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

        # SECURITY: Validate optional focus areas list (NOW AUTO-GENERATED)
        if "focus_areas" in inputs and inputs["focus_areas"]:
            inputs["focus_areas"] = self.validator.validate_list(
                inputs.get("focus_areas"),
                field_name="focus_areas",
                max_items=10,
                item_validator=lambda x: self.validator.validate_text(
                    x,
                    field_name="focus_area",
                    min_length=2,
                    max_length=200,
                    required=False,
                    sanitize=True,
                ),
            )
        else:
            # Will auto-generate from SEO keywords if available
            inputs["focus_areas"] = None

        # Optional: location (for Google Maps industry review analysis)
        location = inputs.get("location")
        if location:
            inputs["location"] = self.validator.validate_text(
                location,
                field_name="location",
                min_length=2,
                max_length=200,
                required=False,
                sanitize=True,
            )
        else:
            inputs["location"] = None

        # Optional client intelligence fields
        if "customer_pain_points" in inputs and inputs["customer_pain_points"]:
            inputs["customer_pain_points"] = self.validator.validate_text(
                inputs.get("customer_pain_points"),
                field_name="customer_pain_points",
                min_length=2,
                max_length=2000,
                required=False,
                sanitize=True,
            )
        if "misconceptions" in inputs and inputs["misconceptions"]:
            inputs["misconceptions"] = self.validator.validate_text(
                inputs.get("misconceptions"),
                field_name="misconceptions",
                min_length=2,
                max_length=2000,
                required=False,
                sanitize=True,
            )

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> TrendReport:
        """Execute market trends research"""
        business_desc = inputs["business_description"]
        industry = inputs.get("industry")
        target_audience = inputs["target_audience"]
        business_name = inputs.get("business_name", "Client")
        focus_areas = inputs.get("focus_areas")
        customer_pain_points = inputs.get("customer_pain_points", "")
        misconceptions = inputs.get("misconceptions", "")

        # Auto-populate industry if not provided (should come from DB)
        if not industry:
            industry = inputs.get("industry_from_db") or "General business"
            logger.info(f"Using industry from database: {industry}")

        # Auto-generate focus areas from SEO keywords if available and not provided
        if not focus_areas:
            focus_areas = self._auto_generate_focus_areas(
                business_desc, industry, inputs.get("seo_keywords", [])
            )
            logger.info(f"Auto-generated {len(focus_areas)} focus areas: {focus_areas}")

        logger.info(f"Researching market trends for {industry} with {len(focus_areas)} focus areas")

        # Step 0: Extract industry customer insights from Google Maps reviews (if location provided)
        location = inputs.get("location")
        industry_insights = ""
        if location:
            logger.info(f"Extracting industry insights from Google Maps reviews in {location}")
            industry_insights = self._extract_industry_insights_from_reviews(
                industry, location, focus_areas
            )

        # Fetch current web trends data
        search_client = get_search_client()
        web_trends_data = []
        if search_client:
            logger.info(f"Fetching current web trends for {industry}")
            web_trends_data = self._fetch_web_trends(
                search_client, industry, focus_areas, business_desc
            )
            logger.info(f"Fetched {len(web_trends_data)} web trend results")
        else:
            logger.warning(
                "Web search client not available - proceeding without current trend data"
            )

        # Step 1: Identify trending topics by category
        trend_categories = self._research_trending_topics(
            business_desc,
            industry,
            target_audience,
            focus_areas,
            industry_insights,
            web_trends_data,
            customer_pain_points=customer_pain_points,
            misconceptions=misconceptions,
        )

        # Step 2: Identify emerging conversations
        emerging_conversations = self._identify_emerging_conversations(
            business_desc, industry, target_audience
        )

        # Step 3: Identify seasonal trends
        seasonal_trends = self._identify_seasonal_trends(industry, business_desc)

        # Step 4: Extract top trends
        top_rising = self._extract_top_rising_trends(trend_categories)
        top_relevant = self._extract_top_relevant_trends(trend_categories)

        # Step 5: Generate content recommendations
        immediate_opps = self._generate_immediate_opportunities(
            top_rising, top_relevant, emerging_conversations
        )
        upcoming_opps = self._generate_upcoming_opportunities(trend_categories, seasonal_trends)

        # Step 6: Identify declining topics
        declining = self._identify_declining_topics(trend_categories)

        # Step 7: Extract key themes
        key_themes = self._extract_key_themes(trend_categories, emerging_conversations)

        # Step 8: Generate market summary
        market_summary = self._generate_market_summary(trend_categories, top_rising, key_themes)

        # Build complete report
        report = TrendReport(
            business_name=business_name,
            industry=industry,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            trend_categories=trend_categories,
            top_rising_trends=top_rising,
            top_relevant_trends=top_relevant,
            emerging_conversations=emerging_conversations,
            seasonal_trends=seasonal_trends,
            immediate_opportunities=immediate_opps,
            upcoming_opportunities=upcoming_opps,
            market_summary=market_summary,
            key_themes=key_themes,
            declining_topics=declining,
        )

        return report

    def _auto_generate_focus_areas(
        self,
        business_description: str,
        industry: str,
        seo_keywords: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Auto-generate 3-5 focus areas for trend research.

        Uses SEO keywords if available, otherwise extracts from business description.

        Args:
            business_description: Business description from database
            industry: Industry from database
            seo_keywords: Optional list of SEO keywords from SEO research tool

        Returns:
            List of 3-5 focus area strings
        """
        logger.info("Auto-generating focus areas for market trends")

        # Build prompt based on available data
        if seo_keywords and len(seo_keywords) > 0:
            # Use SEO keywords to generate more targeted focus areas (Bug #37 fix)
            keywords_text = self._safe_join(seo_keywords[:10])  # Use up to 10 keywords
            prompt = f"""Based on this business context and SEO keywords, identify 3-5 specific focus areas for market trend research.

Industry: {industry}

Business: {business_description}

SEO Keywords: {keywords_text}

Focus areas should be:
- Specific topics or themes (2-5 words each)
- Relevant to the business and target audience
- Suitable for trend research (not too broad, not too narrow)
- Aligned with the SEO keywords when possible

IMPORTANT:
- Return ONLY the focus areas, one per line
- Each focus area should be 2-5 words
- NO numbering, bullets, or extra formatting

Example output format:
AI automation tools
content marketing strategies
remote work productivity

Your focus areas:"""
        else:
            # Fall back to extracting from business description only
            prompt = f"""Based on this business context, identify 3-5 specific focus areas for market trend research.

Industry: {industry}

Business: {business_description}

Focus areas should be:
- Specific topics or themes (2-5 words each)
- Relevant to the business and target audience
- Suitable for trend research (not too broad, not too narrow)

IMPORTANT:
- Return ONLY the focus areas, one per line
- Each focus area should be 2-5 words
- NO numbering, bullets, or extra formatting

Example output format:
cloud infrastructure
developer tools
API integrations

Your focus areas:"""

        try:
            focus_areas_text = self._call_claude_api(
                prompt, max_tokens=300, temperature=0.3, extract_json=False, fallback_on_error=""
            )
            focus_areas_text = str(focus_areas_text).strip()
            focus_areas = [
                area.strip()
                for area in focus_areas_text.split("\n")
                if area.strip() and len(area.strip()) > 3
            ]

            # Limit to 5 focus areas
            focus_areas = focus_areas[:5]

            # Ensure we have at least 3 focus areas
            if len(focus_areas) < 3:
                logger.warning(f"AI generated only {len(focus_areas)} focus areas, using fallback")
                focus_areas = self._fallback_focus_area_extraction(
                    business_description, industry, seo_keywords
                )

            logger.info(f"Auto-generated {len(focus_areas)} focus areas: {focus_areas}")
            return focus_areas

        except Exception as e:
            logger.error(f"Error auto-generating focus areas: {e}")
            # Fallback to simple extraction
            return self._fallback_focus_area_extraction(
                business_description, industry, seo_keywords
            )

    def _fallback_focus_area_extraction(
        self,
        business_description: str,
        industry: str,
        seo_keywords: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Fallback method to extract focus areas if AI generation fails.

        Uses simple keyword extraction from SEO keywords and business description.

        Args:
            business_description: Business description from database
            industry: Industry from database
            seo_keywords: Optional list of SEO keywords

        Returns:
            List of 3-5 focus area strings
        """
        focus_areas = []

        # Start with industry as a focus area
        if industry:
            focus_areas.append(industry)

        # Add SEO keywords if available (limit to 3)
        if seo_keywords and len(seo_keywords) > 0:
            for keyword in seo_keywords[:3]:
                if keyword not in focus_areas:
                    focus_areas.append(keyword)

        # If still need more, extract from business description
        if len(focus_areas) < 3:
            # Common business keywords to look for
            common_keywords = [
                "AI",
                "automation",
                "content",
                "marketing",
                "sales",
                "analytics",
                "cloud",
                "SaaS",
                "platform",
                "tools",
                "software",
                "technology",
                "data",
                "security",
                "workflow",
                "productivity",
                "collaboration",
                "customer",
                "enterprise",
                "business",
                "solutions",
                "services",
            ]

            description_lower = business_description.lower()
            for keyword in common_keywords:
                if keyword.lower() in description_lower and len(focus_areas) < 5:
                    focus_areas.append(keyword)

        # Ensure we have at least 3 focus areas (pad with generic ones if needed)
        if len(focus_areas) < 3:
            focus_areas.extend(["market trends", "industry innovations", "customer needs"])

        # Return first 5 unique focus areas
        unique_areas = []
        for area in focus_areas:
            if area not in unique_areas:
                unique_areas.append(area)

        return unique_areas[:5]

    def _fetch_web_trends(
        self, search_client, industry: str, focus_areas: List[str], business_description: str
    ) -> List[Dict[str, str]]:
        """
        Fetch current web trends for industry and focus areas.

        Uses web search to find recent articles, trends, and discussions
        about the industry and specific focus areas. This provides CURRENT
        data that AI cannot know from training data.

        Args:
            search_client: Web search client
            industry: Industry to research
            focus_areas: List of focus areas to search
            business_description: Business description for context

        Returns:
            List of search results with titles, URLs, and snippets
        """
        web_results = []

        try:
            # Search 1: General industry trends
            industry_query = f"{industry} trends 2026"
            logger.info(f"Searching: {industry_query}")
            industry_results = search_client.search(industry_query, max_results=5)
            for result in industry_results.results:
                web_results.append(
                    {
                        "category": "Industry Trends",
                        "title": result.title,
                        "url": result.url,
                        "snippet": result.snippet,
                        "source": result.source or "Web",
                    }
                )

            # Search 2-4: Focus area specific trends
            for focus_area in focus_areas[:3]:  # Limit to top 3 focus areas
                focus_query = f"{focus_area} {industry} trends"
                logger.info(f"Searching: {focus_query}")
                focus_results = search_client.search(focus_query, max_results=3)
                for result in focus_results.results:
                    web_results.append(
                        {
                            "category": f"Focus: {focus_area}",
                            "title": result.title,
                            "url": result.url,
                            "snippet": result.snippet,
                            "source": result.source or "Web",
                        }
                    )

            logger.info(f"Fetched {len(web_results)} web trend results")

        except Exception as e:
            logger.error(f"Web search failed: {str(e)}")
            logger.warning("Continuing with AI-only trend analysis (may be less current)")
            # Return empty list - analysis will continue with AI-only data

        return web_results

    def _extract_industry_insights_from_reviews(
        self,
        industry: str,
        location: str,
        focus_areas: List[str],
    ) -> str:
        """Extract customer insights from Google Maps reviews of industry businesses.

        Searches for businesses in the industry at the given location,
        extracts their reviews, and identifies common themes, pain points,
        and emerging customer demands.

        Args:
            industry: Industry to research
            location: Geographic location for search
            focus_areas: Focus areas to guide analysis

        Returns:
            Formatted string with industry insights from customer reviews
        """
        try:
            maps_client = get_google_maps_client()

            # Search for top businesses in this industry
            search_query = f"{industry} businesses"
            logger.info(f"Searching for {industry} businesses in {location}")

            businesses = maps_client.search_local_businesses(
                query=search_query,
                location=location,
                max_results=5,  # Get top 5 businesses
            )

            if not businesses:
                logger.warning("No businesses found for industry review analysis")
                return ""

            logger.info(f"Found {len(businesses)} businesses, extracting reviews...")

            # Collect reviews from multiple businesses
            all_reviews = []
            business_names = []

            for business in businesses[:3]:  # Top 3 to avoid too much data
                if not business.place_id:
                    continue

                business_names.append(business.name)
                logger.info(f"Fetching reviews for {business.name}")

                place_reviews = maps_client.get_place_reviews(
                    place_id=business.place_id,
                    max_reviews=10,  # 10 reviews per business
                )

                if place_reviews.reviews:
                    all_reviews.extend(place_reviews.reviews)

            if not all_reviews:
                logger.warning("No reviews found for industry analysis")
                return ""

            logger.info(
                f"Collected {len(all_reviews)} reviews from {len(business_names)} businesses"
            )

            # Format reviews for analysis
            review_text = self._format_industry_reviews(all_reviews, business_names)

            return review_text

        except Exception as e:
            logger.error(f"Failed to extract industry insights from reviews: {e}")
            return ""

    def _format_industry_reviews(self, reviews, business_names: List[str]) -> str:
        """Format industry reviews for trend analysis prompt."""
        if not reviews:
            return ""

        lines = []
        lines.append(f"**INDUSTRY CUSTOMER FEEDBACK** (from {len(business_names)} businesses):")
        lines.append(f"Businesses analyzed: {', '.join(business_names)}")
        lines.append("")

        # Calculate sentiment
        positive = sum(1 for r in reviews if r.rating >= 4)
        negative = sum(1 for r in reviews if r.rating <= 2)
        lines.append(
            f"Sentiment: {positive} positive, {negative} negative (from {len(reviews)} reviews)"
        )
        lines.append("")

        # Show mix of positive and negative for balanced insights
        positive_reviews = [r for r in reviews if r.rating >= 4][:8]
        negative_reviews = [r for r in reviews if r.rating <= 2][:8]

        if positive_reviews:
            lines.append("**What Customers Love:**")
            for i, review in enumerate(positive_reviews, 1):
                stars = "⭐" * review.rating
                text = review.text[:150] + "..." if len(review.text) > 150 else review.text
                lines.append(f'{i}. {stars} - "{text}"')
            lines.append("")

        if negative_reviews:
            lines.append("**Common Complaints/Unmet Needs:**")
            for i, review in enumerate(negative_reviews, 1):
                stars = "⭐" * review.rating
                text = review.text[:150] + "..." if len(review.text) > 150 else review.text
                lines.append(f'{i}. {stars} - "{text}"')
            lines.append("")

        return "\n".join(lines)

    def _research_trending_topics(
        self,
        business_desc: str,
        industry: str,
        target_audience: str,
        focus_areas: List[str],
        industry_insights: str = "",
        web_trends_data: List[Dict[str, str]] = None,
        customer_pain_points: str = "",
        misconceptions: str = "",
    ) -> List[TrendCategory]:
        """Research trending topics organized by category"""
        # Bug #37 fix - handle dicts in focus_areas
        focus_context = (
            f"Focus particularly on: {self._safe_join(focus_areas, ', ')}" if focus_areas else ""
        )

        # Build client intelligence section
        client_intel_lines = []
        if customer_pain_points:
            client_intel_lines.append(
                f"Known Customer Pain Points (confirmed — trends addressing these have guaranteed demand):\n{customer_pain_points}"
            )
        if misconceptions:
            client_intel_lines.append(
                f"Industry Misconceptions to Correct (trend opportunity — debunking content outperforms):\n{misconceptions}"
            )
        client_intel_section = (
            "\n\nCLIENT INTELLIGENCE (use to validate trend relevance):\n"
            + "\n\n".join(client_intel_lines)
            if client_intel_lines
            else ""
        )

        # Add customer insights section if available
        insights_section = ""
        if industry_insights:
            insights_section = f"""

{industry_insights}

Use these customer insights to:
- Validate trending topics (what customers actually care about)
- Identify emerging needs (complaints = opportunities)
- Ground trends in real customer feedback
- Spot gaps between what customers want vs. what's available
"""

        # Add web trends section if available (BUG #46 FIX)
        web_trends_section = ""
        if web_trends_data:
            # Format web search results
            trend_items = []
            for result in web_trends_data:
                cat = result.get("category", "")
                title = result.get("title", "")
                source = result.get("source", "")
                snippet = result.get("snippet", "")
                trend_items.append(f"- [{cat}] {title} ({source})")
                trend_items.append(f"  {snippet}")

            trends_text = chr(92) + "n".join(trend_items)

            web_trends_section = (
                f"{chr(92)}n{chr(92)}nCURRENT WEB TRENDS DATA (March 2026):{chr(92)}n"
                + f"{trends_text}{chr(92)}n{chr(92)}n"
                + "Use these CURRENT web search results to:"
                + chr(92)
                + "n"
                + "- Identify what's trending RIGHT NOW (live search results)"
                + chr(92)
                + "n"
                + "- Validate trend momentum with recent articles"
                + chr(92)
                + "n"
                + "- Ground analysis in current market reality"
                + chr(92)
                + "n"
                + "- Cite specific sources from search results"
            )

        prompt = f"""Research current market trends and organize them into 4-5 categories.

Industry: {industry}

Business: {business_desc}

Target Audience: {target_audience}

{focus_context}{client_intel_section}{insights_section}{web_trends_section}

For each category:
1. Category name and description
2. 3-5 trends within that category
3. Overall category momentum (rising/emerging/stable/declining/seasonal)

For each trend provide:
- Topic (short, clear)
- Description (what it's about)
- Momentum (rising/emerging/stable/declining/seasonal)
- Relevance to this business (high/medium/low)
- Popularity score (1-10)
- Growth rate estimate (e.g., "+50% YoY", "Stable")
- Key drivers (2-3 factors driving this trend)
- Target audience segments (who cares about this)
- Related keywords (3-5 search terms)
- Content angles (2-3 ways to create content)
- Urgency (High/Medium/Low - how time-sensitive)

Focus on trends that are:
- Currently active (not speculative future predictions)
- Relevant to the target audience
- Actionable for content creation

Return ONLY a valid JSON array of category objects. Each object has: category_name, description, category_momentum, trends (array). No markdown. No explanation."""

        try:
            categories_data = self._call_claude_api(
                prompt, max_tokens=3000, temperature=0.5, extract_json=True, fallback_on_error=[]
            )
            categories = []

            for cat_data in categories_data[:5]:  # Max 5 categories
                trends = []

                for trend_data in cat_data.get("trends", [])[:5]:  # Max 5 trends per category
                    trend = Trend(
                        topic=trend_data["topic"],
                        description=trend_data["description"],
                        momentum=TrendMomentum(trend_data["momentum"]),
                        relevance=TrendRelevance(trend_data["relevance"]),
                        popularity_score=float(trend_data["popularity_score"]),
                        growth_rate=trend_data["growth_rate"],
                        key_drivers=trend_data.get("key_drivers", [])[:3],
                        target_audience=trend_data.get("target_audience", [])[:3],
                        related_keywords=trend_data.get("related_keywords", [])[:5],
                        content_angles=trend_data.get("content_angles", [])[:3],
                        urgency=trend_data["urgency"],
                    )
                    trends.append(trend)

                category = TrendCategory(
                    category_name=cat_data["category_name"],
                    description=cat_data["description"],
                    trends=trends,
                    category_momentum=TrendMomentum(cat_data["category_momentum"]),
                )
                categories.append(category)

            logger.info(
                f"Identified {len(categories)} trend categories with {sum(len(c.trends) for c in categories)} trends"
            )
            return categories

        except Exception as e:
            logger.error(f"Failed to research trending topics: {e}")
            return []

    def _identify_emerging_conversations(
        self, business_desc: str, industry: str, target_audience: str
    ) -> List[EmergingConversation]:
        """Identify new conversations and debates emerging"""
        prompt = f"""Identify 3-5 emerging conversations or debates in this industry.

Industry: {industry}

Business: {business_desc}

Target Audience: {target_audience}

For each conversation:
1. Topic (what's being discussed)
2. Description (what the conversation is about)
3. Key perspectives (2-4 different viewpoints)
4. Thought leaders (2-3 people/companies leading discussion)
5. Content opportunity (how to contribute)

Focus on:
- New or evolving discussions (not long-established debates)
- Conversations relevant to target audience
- Areas where original perspective could add value

Return ONLY a valid JSON array. Each object has: topic, description, key_perspectives (array), thought_leaders (array), content_opportunity. No markdown."""

        try:
            conversations_data = self._call_claude_api(
                prompt, max_tokens=2000, temperature=0.6, extract_json=True, fallback_on_error=[]
            )
            conversations = []

            for conv_data in conversations_data[:5]:  # Max 5 conversations
                conversation = EmergingConversation(
                    topic=conv_data["topic"],
                    description=conv_data["description"],
                    key_perspectives=conv_data.get("key_perspectives", [])[:4],
                    thought_leaders=conv_data.get("thought_leaders", [])[:3],
                    content_opportunity=conv_data["content_opportunity"],
                )
                conversations.append(conversation)

            logger.info(f"Identified {len(conversations)} emerging conversations")
            return conversations

        except Exception as e:
            logger.error(f"Failed to identify emerging conversations: {e}")
            return []

    def _identify_seasonal_trends(self, industry: str, business_desc: str) -> List[SeasonalTrend]:
        """Identify recurring seasonal trends"""
        prompt = f"""Identify 3-5 seasonal trends or cyclical patterns in this industry.

Industry: {industry}

Business: {business_desc}

For each seasonal trend:
1. Topic (what peaks seasonally)
2. Timing (when it peaks - quarter, months, etc.)
3. Description (what happens during this season)
4. Preparation timeline (when to start creating content)

Examples:
- Budget planning season (Q4/Q1)
- Conference season
- Holiday/end-of-year patterns
- Industry-specific cycles

Return ONLY a valid JSON array. Each object has: topic, timing, description, preparation_timeline. No markdown."""

        try:
            seasonal_data = self._call_claude_api(
                prompt, max_tokens=1500, temperature=0.4, extract_json=True, fallback_on_error=[]
            )
            seasonal_trends = []

            for trend_data in seasonal_data[:5]:  # Max 5 seasonal trends
                trend = SeasonalTrend(
                    topic=trend_data["topic"],
                    timing=trend_data["timing"],
                    description=trend_data["description"],
                    preparation_timeline=trend_data["preparation_timeline"],
                )
                seasonal_trends.append(trend)

            logger.info(f"Identified {len(seasonal_trends)} seasonal trends")
            return seasonal_trends

        except Exception as e:
            logger.error(f"Failed to identify seasonal trends: {e}")
            return []

    def _extract_top_rising_trends(self, categories: List[TrendCategory]) -> List[Trend]:
        """Extract top rising/emerging trends"""
        rising_trends = []

        for category in categories:
            for trend in category.trends:
                if trend.momentum in [TrendMomentum.RISING, TrendMomentum.EMERGING]:
                    rising_trends.append(trend)

        # Sort by popularity score
        rising_trends.sort(key=lambda t: t.popularity_score, reverse=True)

        return rising_trends[:7]  # Top 7

    def _extract_top_relevant_trends(self, categories: List[TrendCategory]) -> List[Trend]:
        """Extract most relevant trends regardless of momentum"""
        relevant_trends = []

        for category in categories:
            for trend in category.trends:
                if trend.relevance == TrendRelevance.HIGH:
                    relevant_trends.append(trend)

        # Sort by popularity score
        relevant_trends.sort(key=lambda t: t.popularity_score, reverse=True)

        return relevant_trends[:7]  # Top 7

    def _generate_immediate_opportunities(
        self,
        top_rising: List[Trend],
        top_relevant: List[Trend],
        conversations: List[EmergingConversation],
    ) -> List[str]:
        """Generate immediate content opportunities"""
        opportunities = []

        # High urgency, rising trends
        for trend in top_rising[:3]:
            if trend.urgency.lower() == "high":
                opportunities.append(
                    f"Create content on '{trend.topic}' (rising trend, {trend.urgency.lower()} urgency)"
                )

        # High relevance trends
        for trend in top_relevant[:2]:
            if trend.relevance == TrendRelevance.HIGH and trend not in top_rising[:3]:
                opportunities.append(f"Address '{trend.topic}' (high relevance to audience)")

        # Emerging conversations
        if conversations:
            opportunities.append(
                f"Join conversation: {conversations[0].topic} - {conversations[0].content_opportunity}"
            )

        return opportunities[:5]  # Max 5

    def _generate_upcoming_opportunities(
        self, categories: List[TrendCategory], seasonal: List[SeasonalTrend]
    ) -> List[str]:
        """Generate opportunities to prepare for"""
        opportunities = []

        # Emerging trends
        emerging = []
        for category in categories:
            for trend in category.trends:
                if trend.momentum == TrendMomentum.EMERGING:
                    emerging.append(trend)

        for trend in emerging[:2]:
            opportunities.append(
                f"Prepare for '{trend.topic}' (emerging trend, score: {trend.popularity_score}/10)"
            )

        # Seasonal trends
        seasonal_trend: SeasonalTrend
        for seasonal_trend in seasonal[:3]:
            opportunities.append(
                f"Plan for {seasonal_trend.topic} ({seasonal_trend.timing}) - start {seasonal_trend.preparation_timeline}"
            )

        return opportunities[:5]  # Max 5

    def _identify_declining_topics(self, categories: List[TrendCategory]) -> List[str]:
        """Identify topics losing relevance"""
        declining = []

        for category in categories:
            for trend in category.trends:
                if trend.momentum == TrendMomentum.DECLINING:
                    declining.append(f"{trend.topic} - {trend.description}")

        return declining[:5]  # Max 5

    def _extract_key_themes(
        self,
        categories: List[TrendCategory],
        conversations: List[EmergingConversation],
    ) -> List[str]:
        """Extract overarching themes"""
        themes = set()

        # From category names
        for category in categories:
            themes.add(category.category_name)

        # From high-level drivers
        for category in categories:
            for trend in category.trends[:2]:  # Top 2 per category
                for driver in trend.key_drivers[:1]:  # Top driver
                    # Coerce to str — API may return dicts instead of strings
                    driver_str = driver if isinstance(driver, str) else str(driver)
                    if len(driver_str) > 10:  # Skip short/generic drivers
                        themes.add(driver_str)

        # From conversations
        for conv in conversations[:2]:
            themes.add(conv.topic)

        return list(themes)[:7]  # Max 7 themes

    def _generate_market_summary(
        self,
        categories: List[TrendCategory],
        top_rising: List[Trend],
        key_themes: List[str],
    ) -> str:
        """Generate market trends summary"""
        # Count momentum types
        rising_count = sum(
            1 for cat in categories for t in cat.trends if t.momentum == TrendMomentum.RISING
        )
        emerging_count = sum(
            1 for cat in categories for t in cat.trends if t.momentum == TrendMomentum.EMERGING
        )

        # Average popularity of top trends
        avg_popularity = (
            sum(t.popularity_score for t in top_rising[:5]) / len(top_rising[:5])
            if top_rising
            else 0
        )

        summary = f"""Market analysis identified {len(categories)} major trend categories with {sum(len(c.trends) for c in categories)} distinct trends. """

        if rising_count > 0:
            summary += f"{rising_count} trends show strong upward momentum, indicating an active and evolving market landscape. "

        if emerging_count > 0:
            summary += (
                f"{emerging_count} emerging trends suggest new opportunities for early movers. "
            )

        summary += f"Top trends average {avg_popularity:.1f}/10 in popularity, indicating {'strong' if avg_popularity >= 7 else 'moderate'} market interest. "

        if key_themes:
            # Bug #37 fix - handle dicts in key_themes
            summary += f"Key themes include: {self._safe_join(key_themes[:3], ', ')}. "

        summary += (
            "Strategic content aligned with these trends will maximize relevance and engagement."
        )

        return summary

    def generate_reports(self, report: TrendReport) -> Dict[str, Path]:
        """Generate market trends reports in multiple formats"""
        output_dir = self.base_output_dir / self.tool_name / self.project_id
        output_dir.mkdir(parents=True, exist_ok=True)

        reports = {}

        # JSON report
        json_path = output_dir / "market_trends.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2, default=str)
        reports["json"] = json_path

        # Markdown report
        markdown_path = output_dir / "market_trends_report.md"
        markdown_content = self._format_markdown_report(report)
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        reports["markdown"] = markdown_path

        # Text report (quick reference)
        text_path = output_dir / "trends_summary.txt"
        text_content = self._format_text_report(report)
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        reports["text"] = text_path

        logger.info(f"Generated {len(reports)} report formats")
        return reports

    def _format_markdown_report(self, report: TrendReport) -> str:
        """Format report as markdown"""
        md = f"""# Market Trends Research Report

**Business:** {report.business_name}
**Industry:** {report.industry}
**Analysis Date:** {report.analysis_date}

---

## Executive Summary

{report.market_summary}

**Key Themes:** {self._safe_join(report.key_themes)}

---

## Top Rising Trends

"""

        for i, trend in enumerate(report.top_rising_trends, 1):
            md += f"""
### {i}. {trend.topic} [{trend.momentum.value.upper()}]

{trend.description}

- **Popularity:** {trend.popularity_score}/10
- **Growth:** {trend.growth_rate}
- **Relevance:** {trend.relevance.value.upper()}
- **Urgency:** {trend.urgency}

**Key Drivers:** {self._safe_join(trend.key_drivers)}

**Content Angles:**
"""
            for angle in trend.content_angles:
                md += f"- {angle}\n"

        md += """
---

## Trends by Category

"""

        for category in report.trend_categories:
            md += f"""
### {category.category_name} [{category.category_momentum.value.upper()}]

{category.description}

"""
            for trend in category.trends:
                md += f"""
#### {trend.topic}

{trend.description}

- Momentum: {trend.momentum.value.title()}
- Popularity: {trend.popularity_score}/10
- Relevance: {trend.relevance.value.title()}
- Related: {self._safe_join(trend.related_keywords[:3])}

"""

        if report.emerging_conversations:
            md += """
---

## Emerging Conversations

"""
            for conv in report.emerging_conversations:
                md += f"""
### {conv.topic}

{conv.description}

**Perspectives:**
"""
                for perspective in conv.key_perspectives:
                    md += f"- {perspective}\n"

                md += f"""
**Thought Leaders:** {self._safe_join(conv.thought_leaders)}

**Content Opportunity:** {conv.content_opportunity}

"""

        if report.seasonal_trends:
            md += """
---

## Seasonal Trends

"""
            for seasonal in report.seasonal_trends:
                md += f"""
### {seasonal.topic}

**Timing:** {seasonal.timing}

{seasonal.description}

**Preparation:** {seasonal.preparation_timeline}

"""

        md += """
---

## Content Opportunities

### Immediate Opportunities

"""
        for opp in report.immediate_opportunities:
            md += f"- {opp}\n"

        md += "\n### Upcoming Opportunities\n\n"
        for opp in report.upcoming_opportunities:
            md += f"- {opp}\n"

        if report.declining_topics:
            md += "\n---\n\n## Declining Topics (Avoid)\n\n"
            for topic in report.declining_topics:
                md += f"- {topic}\n"

        md += """
---

*Report generated by Market Trends Research Tool*
"""

        return md

    def _format_text_report(self, report: TrendReport) -> str:
        """Format report as simple text"""
        text = f"""MARKET TRENDS REPORT - {report.business_name}
{"=" * 60}

MARKET SUMMARY:
{report.market_summary}

KEY THEMES:
"""

        for theme in report.key_themes:
            text += f"- {theme}\n"

        text += f"\n\nTOP RISING TRENDS ({len(report.top_rising_trends)}):\n"

        for i, trend in enumerate(report.top_rising_trends, 1):
            text += f"\n{i}. {trend.topic} ({trend.popularity_score}/10, {trend.growth_rate})\n"
            text += f"   {trend.description}\n"

        text += "\n\nIMMEDIATE OPPORTUNITIES:\n"
        for opp in report.immediate_opportunities:
            text += f"- {opp}\n"

        text += "\n\nUPCOMING OPPORTUNITIES:\n"
        for opp in report.upcoming_opportunities:
            text += f"- {opp}\n"

        return text
