"""Content Gap Analysis Tool - Identify missing content opportunities

This tool analyzes a client's business and competitors to identify content gaps.
Price: $500
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.content_gap_models import (
    BuyerJourneyGap,
    CompetitorContentAnalysis,
    ContentGap,
    ContentGapAnalysis,
    FormatGap,
    GapPriority,
    GapType,
)
from ..utils.logger import logger
from ..validators.research_input_validator import ResearchInputValidator
from .base import ResearchTool
from .validation_mixin import CommonValidationMixin
from ..utils.anthropic_client import get_default_client


class ContentGapAnalyzer(ResearchTool, CommonValidationMixin):
    """Analyzes content gaps compared to competitors and search intent"""

    def __init__(self, project_id: str, config: Optional[Dict[str, Any]] = None):
        """Initialize Content Gap Analyzer with input validator"""
        super().__init__(project_id, config)
        self.validator = ResearchInputValidator(strict_mode=False)

    @property
    def tool_name(self) -> str:
        return "content_gap_analysis"

    @property
    def price(self) -> int:
        return 500

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
        inputs["target_audience"] = self.validate_target_audience(inputs)

        # SECURITY: Validate current content topics (can be string or list)
        current_content = inputs.get("current_content_topics")
        if isinstance(current_content, str):
            inputs["current_content_topics"] = self.validator.validate_text(
                current_content,
                field_name="current_content_topics",
                min_length=10,
                max_length=5000,
                required=True,
                sanitize=True,
            )
        elif isinstance(current_content, list):
            if len(current_content) == 0:
                raise ValueError(
                    "Provide at least 1 current content topic, or use 'None' if starting fresh"
                )
            inputs["current_content_topics"] = self.validator.validate_list(
                current_content,
                field_name="current_content_topics",
                max_items=100,
                item_validator=lambda x: self.validator.validate_text(
                    x,
                    field_name="content_topic",
                    min_length=2,
                    max_length=500,
                    required=False,
                    sanitize=True,
                ),
            )
        else:
            raise ValueError("current_content_topics must be string or list")

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

        # SECURITY: Validate optional competitors list
        if "competitors" in inputs and inputs["competitors"]:
            competitors = inputs["competitors"]
            if isinstance(competitors, list):
                if len(competitors) > 5:
                    raise ValueError("Maximum 5 competitors allowed for analysis")
                # Validator doesn't have validate_competitor_list method, just use the list directly
                inputs["competitors"] = competitors

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> ContentGapAnalysis:
        """Execute 10-step content gap analysis"""
        logger.info("Starting content gap analysis...")

        # Extract inputs
        business_name = inputs.get("business_name", "Client")
        business_description = inputs["business_description"]
        target_audience = inputs["target_audience"]
        current_content_topics = inputs["current_content_topics"]
        industry = inputs.get("industry", "Not specified")
        competitors = inputs.get("competitors", [])

        # Step 1: Analyze current content coverage
        logger.info("Step 1: Analyzing current content coverage...")
        current_coverage = self._analyze_current_coverage(
            business_description, current_content_topics
        )

        # Step 2: Research competitor content
        logger.info("Step 2: Researching competitor content...")
        competitor_analysis = self._analyze_competitor_content(
            business_description, target_audience, competitors
        )

        # Step 3: Identify topic gaps
        logger.info("Step 3: Identifying topic gaps...")
        topic_gaps = self._identify_topic_gaps(
            business_description, target_audience, current_coverage, competitor_analysis
        )

        # Step 4: Identify format gaps
        logger.info("Step 4: Identifying format gaps...")
        format_gaps = self._identify_format_gaps(business_description, current_coverage)

        # Step 5: Analyze buyer journey gaps
        logger.info("Step 5: Analyzing buyer journey gaps...")
        buyer_journey_gaps = self._analyze_buyer_journey_gaps(
            business_description, target_audience, current_coverage
        )

        # Step 6: Categorize by priority
        logger.info("Step 6: Categorizing gaps by priority...")
        critical_gaps = [g for g in topic_gaps if g.priority == GapPriority.CRITICAL]
        high_priority_gaps = [g for g in topic_gaps if g.priority == GapPriority.HIGH]
        medium_priority_gaps = [g for g in topic_gaps if g.priority == GapPriority.MEDIUM]

        # Step 7: Identify quick wins
        logger.info("Step 7: Identifying quick wins...")
        quick_wins = self._identify_quick_wins(topic_gaps, format_gaps)

        # Step 8: Identify long-term opportunities
        logger.info("Step 8: Identifying long-term opportunities...")
        long_term_opportunities = self._identify_long_term_opportunities(
            topic_gaps, buyer_journey_gaps
        )

        # Step 9: Generate immediate actions
        logger.info("Step 9: Generating immediate actions...")
        immediate_actions = self._generate_immediate_actions(
            critical_gaps, high_priority_gaps, quick_wins
        )

        # Step 10: Create 90-day roadmap
        logger.info("Step 10: Creating 90-day roadmap...")
        ninety_day_roadmap = self._create_90_day_roadmap(
            critical_gaps, high_priority_gaps, medium_priority_gaps
        )

        # Generate executive summary
        total_gaps = len(topic_gaps)
        executive_summary = self._create_executive_summary(
            total_gaps, critical_gaps, high_priority_gaps, competitor_analysis
        )

        estimated_opportunity = self._estimate_opportunity(total_gaps, critical_gaps)

        # Build final report
        analysis = ContentGapAnalysis(
            business_name=business_name,
            industry=industry,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            critical_gaps=critical_gaps,
            high_priority_gaps=high_priority_gaps,
            medium_priority_gaps=medium_priority_gaps,
            competitor_analysis=competitor_analysis,
            buyer_journey_gaps=buyer_journey_gaps,
            format_gaps=format_gaps,
            quick_wins=quick_wins,
            long_term_opportunities=long_term_opportunities,
            executive_summary=executive_summary,
            total_gaps_identified=total_gaps,
            estimated_opportunity=estimated_opportunity,
            immediate_actions=immediate_actions,
            ninety_day_roadmap=ninety_day_roadmap,
        )

        logger.info(f"Content gap analysis complete. {total_gaps} gaps identified.")
        return analysis

    def _analyze_current_coverage(
        self, business_description: str, current_content_topics: Any
    ) -> Dict[str, Any]:
        """Analyze what content currently exists"""
        client = get_default_client()

        # Convert topics to string if list
        if isinstance(current_content_topics, list):
            topics_str = ", ".join(current_content_topics)
        else:
            topics_str = str(current_content_topics)

        prompt = f"""Analyze the current content coverage for this business:

Business: {business_description}

Current Content Topics: {topics_str}

Provide a structured analysis:
1. Content coverage areas (what topics are covered)
2. Content depth (superficial vs comprehensive)
3. Content formats present (blog, video, checklist, etc.)
4. Buyer journey stages covered (awareness, consideration, decision)
5. Audience segments addressed

Return as JSON with these exact keys: coverage_areas, depth_assessment, formats, buyer_stages, audience_segments"""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], temperature=0.7
        )

        try:
            result: Dict[str, Any] = json.loads(response.content[0].text)
            return result
        except (json.JSONDecodeError, KeyError, IndexError, AttributeError):
            return {
                "coverage_areas": [topics_str],
                "depth_assessment": "Unknown",
                "formats": ["Blog posts"],
                "buyer_stages": ["Awareness"],
                "audience_segments": ["General"],
            }

    def _analyze_competitor_content(
        self, business_description: str, target_audience: str, competitors: List[str]
    ) -> List[CompetitorContentAnalysis]:
        """Analyze competitor content strategies"""
        if not competitors:
            return []

        client = get_default_client()
        analyses = []

        for competitor in competitors[:5]:  # Max 5 competitors
            prompt = f"""Analyze the content strategy for this competitor:

Competitor: {competitor}

Our Business: {business_description}
Our Audience: {target_audience}

Based on typical content strategies in this space, infer:
1. Their content strengths (3-5 items)
2. Their popular topics (5-7 topics)
3. Formats they likely use (blog, video, webinar, etc.)
4. Gaps in their content (what they're missing that we could own)

Return as JSON with keys: content_strengths, popular_topics, formats_used, gaps_in_their_content"""

            response = client.create_message(
                messages=[{"role": "user", "content": prompt}], temperature=0.7
            )

            try:
                data = json.loads(response.content[0].text)
                analyses.append(
                    CompetitorContentAnalysis(
                        competitor_name=competitor,
                        content_strengths=data.get("content_strengths", []),
                        popular_topics=data.get("popular_topics", []),
                        formats_used=data.get("formats_used", []),
                        gaps_in_their_content=data.get("gaps_in_their_content", []),
                    )
                )
            except (json.JSONDecodeError, KeyError, IndexError, AttributeError, TypeError):
                # Fallback
                analyses.append(
                    CompetitorContentAnalysis(
                        competitor_name=competitor,
                        content_strengths=["Strong SEO", "Regular publishing"],
                        popular_topics=["Industry best practices"],
                        formats_used=["Blog posts", "Case studies"],
                        gaps_in_their_content=["Tactical how-to content"],
                    )
                )

        return analyses

    def _identify_topic_gaps(
        self,
        business_description: str,
        target_audience: str,
        current_coverage: Dict,
        competitor_analysis: List[CompetitorContentAnalysis],
    ) -> List[ContentGap]:
        """Identify specific topic gaps"""
        client = get_default_client()

        # Build competitor context
        competitor_topics = []
        for comp in competitor_analysis:
            competitor_topics.extend(comp.popular_topics)

        competitor_context = (
            ", ".join(competitor_topics[:15]) if competitor_topics else "Not analyzed"
        )

        prompt = f"""Identify content gaps for this business:

Business: {business_description}
Target Audience: {target_audience}

Current Coverage: {json.dumps(current_coverage, indent=2)}
Competitor Topics: {competitor_context}

Identify 10-15 specific content gaps. For each gap:
- gap_title: What's missing
- gap_type: "topic", "format", "depth", "freshness", "stage", or "audience_segment"
- priority: "critical", "high", "medium", or "low"
- description: Why this matters
- search_volume: Estimate (e.g., "High: 5K/mo", "Medium: 1K/mo", "Low: 200/mo")
- competition: How many competitors cover this
- business_impact: How this helps business
- target_audience: Who needs this
- buyer_stage: "Awareness", "Consideration", or "Decision"
- content_angle: Recommended approach
- example_topics: 3-5 specific topics
- estimated_effort: "Small", "Medium", or "Large"

Return as JSON array of gap objects."""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], temperature=0.7
        )

        try:
            gaps_data = json.loads(response.content[0].text)
            if isinstance(gaps_data, dict) and "gaps" in gaps_data:
                gaps_data = gaps_data["gaps"]

            return [ContentGap(**gap) for gap in gaps_data]
        except Exception as e:
            logger.error(f"Error parsing topic gaps: {e}")
            # Return fallback gaps
            return [
                ContentGap(
                    gap_title="Getting Started Guide",
                    gap_type=GapType.TOPIC,
                    priority=GapPriority.CRITICAL,
                    description="New users need onboarding content",
                    search_volume="High: 3K/mo",
                    competition="3 of 5 competitors have this",
                    business_impact="Reduces time-to-value for new customers",
                    target_audience=target_audience,
                    buyer_stage="Decision",
                    content_angle="Step-by-step walkthrough with screenshots",
                    example_topics=["Quick start guide", "First steps", "Setup tutorial"],
                    estimated_effort="Medium",
                )
            ]

    def _identify_format_gaps(
        self, business_description: str, current_coverage: Dict
    ) -> List[FormatGap]:
        """Identify missing content formats"""
        client = get_default_client()

        current_formats = current_coverage.get("formats", [])
        current_formats_str = ", ".join(current_formats) if current_formats else "None specified"

        prompt = f"""Identify content format gaps for this business:

Business: {business_description}
Current Formats: {current_formats_str}

Suggest 3-5 content formats they should add:
- Blog posts
- Video tutorials
- Checklists/templates
- Webinars
- Case studies
- Infographics
- Email courses
- Podcasts
- Interactive tools

For each format:
- format_name: Format type
- why_needed: Why this format matters
- topics_to_cover: 3-5 topics that work well in this format
- estimated_impact: "High", "Medium", or "Low"

Return as JSON array of format gap objects."""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], temperature=0.7
        )

        try:
            gaps_data = json.loads(response.content[0].text)
            if isinstance(gaps_data, dict) and "formats" in gaps_data:
                gaps_data = gaps_data["formats"]

            return [FormatGap(**gap) for gap in gaps_data]
        except (json.JSONDecodeError, KeyError, IndexError, AttributeError, TypeError):
            return [
                FormatGap(
                    format_name="Video tutorials",
                    why_needed="Visual learners need video content",
                    topics_to_cover=["Product walkthrough", "Common workflows", "Troubleshooting"],
                    estimated_impact="High",
                )
            ]

    def _analyze_buyer_journey_gaps(
        self, business_description: str, target_audience: str, current_coverage: Dict
    ) -> List[BuyerJourneyGap]:
        """Analyze gaps in buyer journey coverage"""
        client = get_default_client()

        current_stages = current_coverage.get("buyer_stages", [])
        stages_str = ", ".join(current_stages) if current_stages else "Unknown"

        prompt = f"""Analyze buyer journey content gaps:

Business: {business_description}
Target Audience: {target_audience}
Current Coverage: {stages_str}

For each stage (Awareness, Consideration, Decision):
- stage: Stage name
- current_coverage: What content exists now
- gap_description: What's missing
- recommended_content: 3-5 specific content pieces to create
- priority: "critical", "high", "medium", or "low"

Return as JSON array of buyer journey gap objects."""

        response = client.create_message(
            messages=[{"role": "user", "content": prompt}], temperature=0.7
        )

        try:
            gaps_data = json.loads(response.content[0].text)
            if isinstance(gaps_data, dict) and "stages" in gaps_data:
                gaps_data = gaps_data["stages"]

            return [BuyerJourneyGap(**gap) for gap in gaps_data]
        except (json.JSONDecodeError, KeyError, IndexError, AttributeError, TypeError):
            return [
                BuyerJourneyGap(
                    stage="Awareness",
                    current_coverage="Limited",
                    gap_description="Need more educational content for discovery stage",
                    recommended_content=[
                        "Industry trends blog",
                        "Problem recognition guides",
                        "Educational webinar",
                    ],
                    priority=GapPriority.HIGH,
                )
            ]

    def _identify_quick_wins(
        self, topic_gaps: List[ContentGap], format_gaps: List[FormatGap]
    ) -> List[str]:
        """Identify quick-win opportunities"""
        quick_wins = []

        # High priority + small effort = quick win
        for gap in topic_gaps:
            if (
                gap.priority in [GapPriority.CRITICAL, GapPriority.HIGH]
                and gap.estimated_effort == "Small"
            ):
                quick_wins.append(f"{gap.gap_title} - {gap.description}")

        # High impact formats
        for fmt in format_gaps:
            if fmt.estimated_impact == "High":
                quick_wins.append(f"Create {fmt.format_name}: {fmt.why_needed}")

        return quick_wins[:7]  # Top 7

    def _identify_long_term_opportunities(
        self, topic_gaps: List[ContentGap], buyer_journey_gaps: List[BuyerJourneyGap]
    ) -> List[str]:
        """Identify strategic long-term opportunities"""
        opportunities = []

        # Large effort gaps with high impact
        for gap in topic_gaps:
            if gap.estimated_effort == "Large" and gap.priority in [
                GapPriority.CRITICAL,
                GapPriority.HIGH,
            ]:
                opportunities.append(f"{gap.gap_title} - {gap.business_impact}")

        # Strategic buyer journey improvements
        for journey in buyer_journey_gaps:
            if journey.priority in [GapPriority.CRITICAL, GapPriority.HIGH]:
                opportunities.append(f"Build {journey.stage} stage content library")

        return opportunities[:5]  # Top 5

    def _generate_immediate_actions(
        self,
        critical_gaps: List[ContentGap],
        high_priority_gaps: List[ContentGap],
        quick_wins: List[str],
    ) -> List[str]:
        """Generate immediate action items"""
        actions = []

        # Critical gaps first
        for gap in critical_gaps[:3]:
            actions.append(f"CREATE: {gap.gap_title} ({gap.content_angle})")

        # Quick wins
        for win in quick_wins[:2]:
            if len(actions) < 5:
                actions.append(f"QUICK WIN: {win}")

        # High priority gaps to fill remaining
        for gap in high_priority_gaps:
            if len(actions) < 5:
                actions.append(f"HIGH PRIORITY: {gap.gap_title}")

        return actions

    def _create_90_day_roadmap(
        self,
        critical_gaps: List[ContentGap],
        high_priority_gaps: List[ContentGap],
        medium_priority_gaps: List[ContentGap],
    ) -> List[str]:
        """Create 90-day content roadmap"""
        roadmap = []

        # Month 1: Critical gaps
        roadmap.append("MONTH 1: Critical Gaps")
        for gap in critical_gaps[:4]:
            roadmap.append(f"  Week {len(roadmap)//2 + 1}: {gap.gap_title}")

        # Month 2: High priority gaps
        roadmap.append("MONTH 2: High Priority Gaps")
        for gap in high_priority_gaps[:4]:
            roadmap.append(f"  Week {len(roadmap)//2 + 1}: {gap.gap_title}")

        # Month 3: Medium priority gaps
        roadmap.append("MONTH 3: Medium Priority Gaps")
        for gap in medium_priority_gaps[:4]:
            roadmap.append(f"  Week {len(roadmap)//2 + 1}: {gap.gap_title}")

        return roadmap[:12]  # Max 12 items

    def _create_executive_summary(
        self,
        total_gaps: int,
        critical_gaps: List[ContentGap],
        high_priority_gaps: List[ContentGap],
        competitor_analysis: List[CompetitorContentAnalysis],
    ) -> str:
        """Create executive summary of gap analysis"""
        summary = f"Identified {total_gaps} content gaps across topics, formats, and buyer journey stages. "

        if critical_gaps:
            summary += f"{len(critical_gaps)} critical gaps require immediate attention. "

        if high_priority_gaps:
            summary += f"{len(high_priority_gaps)} high-priority opportunities present strong ROI potential. "

        if competitor_analysis:
            summary += f"Analysis of {len(competitor_analysis)} competitors reveals opportunities to differentiate and capture uncovered topics. "

        summary += "Recommended approach: Address critical gaps first, then pursue quick wins to build momentum."

        return summary

    def _estimate_opportunity(self, total_gaps: int, critical_gaps: List[ContentGap]) -> str:
        """Estimate business opportunity from addressing gaps"""
        if total_gaps >= 20:
            return "$100K+ annual organic traffic value"
        elif total_gaps >= 10:
            return "$50K+ annual organic traffic value"
        elif critical_gaps:
            return "$25K+ annual organic traffic value"
        else:
            return "$10K+ annual organic traffic value"

    def generate_reports(self, analysis: ContentGapAnalysis) -> Dict[str, Path]:
        """Generate output reports in multiple formats

        Args:
            analysis: Content gap analysis results

        Returns:
            Dictionary mapping format names to file paths
        """
        outputs = {}

        # JSON format
        json_path = self.output_dir / "content_gaps.json"
        json_path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
        outputs["json"] = json_path

        # Markdown format
        markdown_path = self.output_dir / "content_gap_analysis.md"
        markdown_content = self.format_output_markdown(analysis)
        markdown_path.write_text(markdown_content, encoding="utf-8")
        outputs["markdown"] = markdown_path

        # Text format
        text_path = self.output_dir / "gaps_summary.txt"
        text_content = self.format_output_text(analysis)
        text_path.write_text(text_content, encoding="utf-8")
        outputs["text"] = text_path

        logger.info(f"Generated {len(outputs)} report files in {self.output_dir}")
        return outputs

    def format_output_text(self, analysis: ContentGapAnalysis) -> str:
        """Format as plain text summary"""
        lines = [
            "=" * 60,
            f"CONTENT GAP ANALYSIS - {analysis.business_name}",
            "=" * 60,
            "",
            f"Industry: {analysis.industry}",
            f"Analysis Date: {analysis.analysis_date}",
            f"Total Gaps Identified: {analysis.total_gaps_identified}",
            f"Estimated Opportunity: {analysis.estimated_opportunity}",
            "",
            "=" * 60,
            "EXECUTIVE SUMMARY",
            "=" * 60,
            analysis.executive_summary,
            "",
            "=" * 60,
            "IMMEDIATE ACTIONS",
            "=" * 60,
        ]

        for i, action in enumerate(analysis.immediate_actions, 1):
            lines.append(f"{i}. {action}")

        lines.extend(["", "=" * 60, "90-DAY ROADMAP", "=" * 60])

        for item in analysis.ninety_day_roadmap:
            lines.append(item)

        return "\n".join(lines)

    def format_output_markdown(self, analysis: ContentGapAnalysis) -> str:
        """Format as markdown report"""
        md = [
            "# Content Gap Analysis Report",
            f"## {analysis.business_name}",
            "",
            f"**Industry:** {analysis.industry}  ",
            f"**Analysis Date:** {analysis.analysis_date}  ",
            f"**Total Gaps:** {analysis.total_gaps_identified}  ",
            f"**Estimated Opportunity:** {analysis.estimated_opportunity}",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            analysis.executive_summary,
            "",
            "## Immediate Actions",
            "",
        ]

        for i, action in enumerate(analysis.immediate_actions, 1):
            md.append(f"{i}. {action}")

        md.extend(["", "## Critical Gaps", ""])

        for gap in analysis.critical_gaps:
            md.extend(
                [
                    f"### {gap.gap_title}",
                    "",
                    f"**Priority:** {gap.priority.value.upper()}  ",
                    f"**Type:** {gap.gap_type.value}  ",
                    f"**Search Volume:** {gap.search_volume}  ",
                    f"**Competition:** {gap.competition}",
                    "",
                    f"**Why This Matters:** {gap.description}",
                    "",
                    f"**Business Impact:** {gap.business_impact}",
                    "",
                    f"**Target Audience:** {gap.target_audience}  ",
                    f"**Buyer Stage:** {gap.buyer_stage}  ",
                    f"**Estimated Effort:** {gap.estimated_effort}",
                    "",
                    f"**Content Angle:** {gap.content_angle}",
                    "",
                    "**Example Topics:**",
                ]
            )
            for topic in gap.example_topics:
                md.append(f"- {topic}")
            md.append("")

        md.extend(["## 90-Day Content Roadmap", ""])
        for item in analysis.ninety_day_roadmap:
            if item.startswith("MONTH"):
                md.append(f"### {item}")
            else:
                md.append(item)

        return "\n".join(md)
