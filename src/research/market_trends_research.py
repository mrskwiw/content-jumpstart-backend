"""Market Trends Research Tool - $400 Add-On

Identifies trending topics and emerging conversations in the client's industry.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

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
from .base import ResearchTool
from .validation_mixin import CommonValidationMixin
from ..utils.anthropic_client import get_default_client


class MarketTrendsResearcher(ResearchTool, CommonValidationMixin):
    """Automated market trends research and analysis"""

    def __init__(self, project_id: str, config: Dict[str, Any] = None):
        """Initialize Market Trends Researcher with input validator"""
        super().__init__(project_id, config)
        self.validator = ResearchInputValidator(strict_mode=False)
        self.client = get_default_client()  # Still needed for unmigrated API calls

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
        """
        # SECURITY: Validate business description with sanitization
        inputs["business_description"] = self.validate_business_description(inputs)

        # SECURITY: Validate industry with sanitization
        inputs["industry"] = self.validator.validate_text(
            inputs.get("industry"),
            field_name="industry",
            min_length=2,
            max_length=200,
            required=True,
            sanitize=True,
        )

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

        # SECURITY: Validate optional focus areas list
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

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> TrendReport:
        """Execute market trends research"""
        business_desc = inputs["business_description"]
        industry = inputs["industry"]
        target_audience = inputs["target_audience"]
        business_name = inputs.get("business_name", "Client")
        focus_areas = inputs.get("focus_areas", [])

        logger.info(f"Researching market trends for {industry}")

        # Step 1: Identify trending topics by category
        trend_categories = self._research_trending_topics(
            business_desc, industry, target_audience, focus_areas
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

    def _research_trending_topics(
        self,
        business_desc: str,
        industry: str,
        target_audience: str,
        focus_areas: List[str],
    ) -> List[TrendCategory]:
        """Research trending topics organized by category"""
        focus_context = f"Focus particularly on: {', '.join(focus_areas)}" if focus_areas else ""

        prompt = f"""Research current market trends and organize them into 4-5 categories.

Industry: {industry}

Business: {business_desc}

Target Audience: {target_audience}

{focus_context}

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

Return as JSON array of categories with keys:
category_name, description, category_momentum, trends (array with all trend fields)"""

        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
                temperature=0.5,
            )

            categories_data = json.loads(response)
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

Return as JSON array with keys:
topic, description, key_perspectives (array), thought_leaders (array), content_opportunity"""

        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.6,
            )

            conversations_data = json.loads(response)
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

Return as JSON array with keys:
topic, timing, description, preparation_timeline"""

        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.4,
            )

            seasonal_data = json.loads(response)
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
        for trend in seasonal[:3]:
            opportunities.append(
                f"Plan for {trend.topic} ({trend.timing}) - start {trend.preparation_timeline}"
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
                    if len(driver) > 10:  # Skip short/generic drivers
                        themes.add(driver)

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
            summary += f"Key themes include: {', '.join(key_themes[:3])}. "

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

**Key Themes:** {", ".join(report.key_themes)}

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

**Key Drivers:** {", ".join(trend.key_drivers)}

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
- Related: {", ".join(trend.related_keywords[:3])}

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
**Thought Leaders:** {", ".join(conv.thought_leaders)}

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

*Report generated by Market Trends Research Tool ($400)*
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
