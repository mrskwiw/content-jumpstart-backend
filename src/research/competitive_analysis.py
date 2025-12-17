"""Competitive Analysis Tool - $500 Add-On

Analyzes competitors' content strategies and identifies differentiation opportunities.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..models.competitive_analysis_models import (
    CompetitiveAnalysis,
    CompetitorProfile,
    CompetitorStrength,
    ContentGap,
    ContentType,
    DifferentiationStrategy,
    MarketPosition,
)
from ..utils.anthropic_client import get_default_client
from ..utils.logger import logger
from .base import ResearchTool


class CompetitiveAnalyzer(ResearchTool):
    """Automated competitive analysis and strategy development"""

    def __init__(self, project_id: str):
        super().__init__(project_id=project_id)
        self.client = get_default_client()

    @property
    def tool_name(self) -> str:
        return "competitive_analysis"

    @property
    def price(self) -> int:
        return 500

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate required inputs"""
        required = ["business_description", "target_audience", "competitors"]

        missing = [field for field in required if field not in inputs]
        if missing:
            raise ValueError(f"Missing required inputs: {', '.join(missing)}")

        # Validate business description length
        if len(inputs["business_description"]) < 50:
            raise ValueError("Business description too short (min 50 characters)")

        # Validate competitors list
        if not isinstance(inputs["competitors"], list) or len(inputs["competitors"]) < 1:
            raise ValueError("Must provide at least 1 competitor")

        if len(inputs["competitors"]) > 5:
            raise ValueError("Maximum 5 competitors allowed (keeps analysis focused)")

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> CompetitiveAnalysis:
        """Execute competitive analysis"""
        business_desc = inputs["business_description"]
        target_audience = inputs["target_audience"]
        competitors = inputs["competitors"]
        industry = inputs.get("industry", "Not specified")
        business_name = inputs.get("business_name", "Client")

        logger.info(f"Analyzing {len(competitors)} competitors")

        # Step 1: Analyze each competitor
        competitor_profiles = self._analyze_competitors(
            competitors, business_desc, target_audience, industry
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
            competitor_profiles, business_desc, content_gaps, diff_strategies
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
    ) -> List[CompetitorProfile]:
        """Analyze each competitor's strategy"""
        profiles = []

        for competitor in competitors[:5]:  # Max 5
            prompt = f"""Analyze this competitor in detail.

Competitor: {competitor}

Our Business: {business_desc}

Our Target Audience: {target_audience}

Industry: {industry}

Provide a comprehensive competitor profile including:
1. Their positioning (how they position themselves in market)
2. Their target audience
3. Content types they produce (blog, social, video, etc.)
4. Content frequency (e.g., "3-4x per week")
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
estimated_reach, engagement_level"""

            try:
                response = self.client.create_message(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    temperature=0.4,
                )

                data = json.loads(response)

                # Parse content types
                content_types = []
                for ct in data.get("content_types", []):
                    try:
                        content_types.append(ContentType(ct.lower().replace(" ", "_")))
                    except ValueError:
                        pass  # Skip invalid content types

                profile = CompetitorProfile(
                    name=competitor,
                    positioning=data.get("positioning", "Unknown"),
                    target_audience=data.get("target_audience", "Unknown"),
                    content_types=content_types,
                    content_frequency=data.get("content_frequency", "Unknown"),
                    content_topics=data.get("content_topics", [])[:7],
                    brand_voice=data.get("brand_voice", "Unknown"),
                    tone_descriptors=data.get("tone_descriptors", [])[:5],
                    strengths=data.get("strengths", [])[:5],
                    weaknesses=data.get("weaknesses", [])[:5],
                    estimated_reach=data.get("estimated_reach", "Unknown"),
                    engagement_level=CompetitorStrength(data.get("engagement_level", "moderate")),
                )
                profiles.append(profile)

            except Exception as e:
                logger.warning(f"Failed to analyze competitor {competitor}: {e}")
                # Create minimal profile
                profile = CompetitorProfile(
                    name=competitor,
                    positioning="Analysis unavailable",
                    target_audience="Unknown",
                    content_frequency="Unknown",
                    brand_voice="Unknown",
                    estimated_reach="Unknown",
                    engagement_level=CompetitorStrength.MODERATE,
                )
                profiles.append(profile)

        logger.info(f"Analyzed {len(profiles)} competitors")
        return profiles

    def _identify_content_gaps(
        self,
        competitors: List[CompetitorProfile],
        business_desc: str,
        target_audience: str,
    ) -> List[ContentGap]:
        """Identify content gaps and opportunities"""
        # Collect all topics competitors cover
        competitor_topics = set()
        for comp in competitors:
            competitor_topics.update(comp.content_topics)

        competitor_list = "\n".join(
            [f"- {c.name}: {', '.join(c.content_topics)}" for c in competitors]
        )

        prompt = f"""Identify 5-7 content gap opportunities based on this competitive analysis.

Our Business: {business_desc}

Target Audience: {target_audience}

Competitors and their topics:
{competitor_list}

For each gap, provide:
1. Topic/area with gap
2. Description of the opportunity
3. Opportunity score (1-10, how valuable this gap is)
4. Which competitors are missing this (names)
5. 3 suggested content ideas to fill the gap

Focus on gaps where:
- Multiple competitors are weak or missing content
- The topic is highly relevant to target audience
- We could establish thought leadership

Return as JSON array with keys:
topic, description, opportunity_score, competitors_missing (array), suggested_content (array)"""

        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.5,
            )

            gaps_data = json.loads(response)
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
        competitor_summary = "\n".join(
            [
                f"- {c.name}: Strengths: {', '.join(c.strengths[:3])}, Weaknesses: {', '.join(c.weaknesses[:3])}"
                for c in competitors
            ]
        )

        gap_summary = "\n".join([f"- {g.topic}: {g.description}" for g in content_gaps[:5]])

        prompt = f"""Generate 5 differentiation strategies to stand out from competitors.

Our Business: {business_desc}

Competitors:
{competitor_summary}

Content Gaps:
{gap_summary}

For each strategy:
1. Strategy name (clear, concise)
2. Description (how to implement)
3. Difficulty (Low/Medium/High)
4. Potential impact (Low/Medium/High)
5. 2-3 specific examples

Focus on strategies that:
- Leverage our unique strengths
- Exploit competitor weaknesses
- Are feasible to implement
- Have high impact potential

Return as JSON array with keys:
strategy_name, description, difficulty, potential_impact, examples (array)"""

        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.6,
            )

            strategies_data = json.loads(response)
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
    ) -> MarketPosition:
        """Develop recommended market positioning"""
        comp_summary = "\n".join([f"- {c.name}: {c.positioning}" for c in competitors])
        gap_summary = "\n".join([f"- {g.topic}" for g in content_gaps[:5]])
        strat_summary = "\n".join([f"- {s.strategy_name}" for s in strategies[:3]])

        prompt = f"""Develop a market positioning recommendation.

Our Business: {business_desc}

Competitor Positioning:
{comp_summary}

Key Content Gaps:
{gap_summary}

Differentiation Strategies:
{strat_summary}

Provide:
1. Positioning statement (1-2 sentences, clear and memorable)
2. 3-5 unique angles to emphasize
3. 3-5 competitive advantages we have
4. 3-5 areas we need to improve

Return as JSON with keys:
positioning_statement, unique_angles (array), competitive_advantages (array), areas_to_improve (array)"""

        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.5,
            )

            data = json.loads(response)

            position = MarketPosition(
                positioning_statement=data["positioning_statement"],
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
        moderate_count = sum(
            1 for c in competitors if c.engagement_level == CompetitorStrength.MODERATE
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

*Report generated by Competitive Analysis Tool ($500)*
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
