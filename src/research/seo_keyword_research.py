"""SEO Keyword Research Tool - $400 Add-On

Researches and recommends target keywords for content optimization.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..models.seo_models import (
    CompetitorKeywords,
    Keyword,
    KeywordCluster,
    KeywordDifficulty,
    KeywordStrategy,
    SearchIntent,
)
from ..utils.anthropic_client import get_default_client
from ..utils.logger import logger
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
        logger.warning("Empty response received, returning empty array")
        return "[]"

    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        return json_match.group(1)

    # Try to find JSON array or object without code blocks
    json_match = re.search(r'(\[.*\]|\{.*\})', response_text, re.DOTALL)
    if json_match:
        return json_match.group(1)

    # If no JSON found, return empty array
    logger.warning(f"No JSON found in response, returning empty array. Response preview: {response_text[:200]}")
    return "[]"
from .base import ResearchTool


class SEOKeywordResearcher(ResearchTool):
    """Automated SEO keyword research and strategy development"""

    def __init__(self, project_id: str):
        super().__init__(project_id=project_id)
        self.client = get_default_client()

    @property
    def tool_name(self) -> str:
        return "seo_keyword_research"

    @property
    def price(self) -> int:
        return 400

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate required inputs"""
        required = ["business_description", "target_audience", "main_topics"]

        missing = [field for field in required if field not in inputs]
        if missing:
            raise ValueError(f"Missing required inputs: {', '.join(missing)}")

        # Validate business description length
        if len(inputs["business_description"]) < 50:
            raise ValueError("Business description too short (min 50 characters)")

        # Validate main topics
        if not isinstance(inputs["main_topics"], list) or len(inputs["main_topics"]) < 1:
            raise ValueError("Must provide at least 1 main topic")

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> KeywordStrategy:
        """Execute keyword research analysis"""
        business_desc = inputs["business_description"]
        target_audience = inputs["target_audience"]
        main_topics = inputs["main_topics"]
        competitors = inputs.get("competitors", [])
        industry = inputs.get("industry", "Not specified")

        logger.info(f"Researching keywords for {len(main_topics)} topics")

        # Step 1: Research primary keywords (5-10)
        primary_keywords = self._research_primary_keywords(
            business_desc, target_audience, main_topics, industry
        )

        # Step 2: Research secondary/long-tail keywords (20-30)
        secondary_keywords = self._research_secondary_keywords(
            business_desc, target_audience, main_topics, primary_keywords
        )

        # Step 3: Create keyword clusters
        clusters = self._create_keyword_clusters(main_topics, primary_keywords, secondary_keywords)

        # Step 4: Identify quick wins
        quick_wins = self._identify_quick_wins(primary_keywords, secondary_keywords)

        # Step 5: Competitor analysis (if provided)
        competitor_analysis = []
        if competitors:
            competitor_analysis = self._analyze_competitors(
                competitors, business_desc, primary_keywords
            )

        # Step 6: Generate content priorities
        content_priorities = self._generate_content_priorities(
            clusters, quick_wins, competitor_analysis
        )

        # Step 7: Create strategy summary
        strategy_summary = self._create_strategy_summary(
            primary_keywords,
            secondary_keywords,
            clusters,
            quick_wins,
            competitor_analysis,
        )

        # Build complete strategy
        strategy = KeywordStrategy(
            business_name=inputs.get("business_name", "Client"),
            industry=industry,
            target_audience=target_audience,
            primary_keywords=primary_keywords,
            secondary_keywords=secondary_keywords,
            keyword_clusters=clusters,
            competitor_analysis=competitor_analysis,
            quick_win_keywords=quick_wins,
            content_priorities=content_priorities,
            strategy_summary=strategy_summary,
        )

        return strategy

    def _research_primary_keywords(
        self,
        business_desc: str,
        target_audience: str,
        main_topics: List[str],
        industry: str,
    ) -> List[Keyword]:
        """Research primary target keywords (5-10)"""
        prompt = f"""Analyze this business and recommend 5-10 PRIMARY target keywords for SEO.

Business: {business_desc}

Target Audience: {target_audience}

Industry: {industry}

Main Topics: {', '.join(main_topics)}

For each keyword, provide:
1. The keyword phrase
2. Search intent (informational/navigational/commercial/transactional)
3. Difficulty estimate (low/medium/high)
4. Monthly volume estimate (range like "1K-10K")
5. Relevance score (1-10)
6. Whether it's long-tail (3+ words)
7. Whether it's question-based
8. Related topics it supports

Focus on keywords that are:
- Highly relevant to the business (8+ relevance score)
- Mix of informational and commercial intent
- Realistic to rank for (prefer medium difficulty)
- Specific enough to attract qualified traffic

Return as JSON array of objects with keys:
keyword, search_intent, difficulty, monthly_volume_estimate, relevance_score, long_tail, question_based, related_topics"""

        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.4,
            )

            # Parse JSON response (extract from markdown if needed)
            json_str = extract_json_from_response(response)
            keywords_data = json.loads(json_str)
            keywords = []

            for kw_data in keywords_data[:10]:  # Max 10 primary
                keyword = Keyword(
                    keyword=kw_data["keyword"],
                    search_intent=SearchIntent(kw_data["search_intent"]),
                    difficulty=KeywordDifficulty(kw_data["difficulty"]),
                    monthly_volume_estimate=kw_data["monthly_volume_estimate"],
                    relevance_score=float(kw_data["relevance_score"]),
                    long_tail=kw_data.get("long_tail", False),
                    question_based=kw_data.get("question_based", False),
                    related_topics=kw_data.get("related_topics", []),
                )
                keywords.append(keyword)

            logger.info(f"Identified {len(keywords)} primary keywords")
            return keywords

        except Exception as e:
            logger.error(f"Failed to research primary keywords: {e}")
            # Return fallback keywords based on topics
            return self._generate_fallback_primary_keywords(main_topics)

    def _research_secondary_keywords(
        self,
        business_desc: str,
        target_audience: str,
        main_topics: List[str],
        primary_keywords: List[Keyword],
    ) -> List[Keyword]:
        """Research secondary/long-tail keywords (20-30)"""
        primary_kw_list = [kw.keyword for kw in primary_keywords]

        prompt = f"""Generate 20-30 SECONDARY/LONG-TAIL keywords based on these primary keywords.

Business: {business_desc}

Target Audience: {target_audience}

Primary Keywords: {', '.join(primary_kw_list)}

Main Topics: {', '.join(main_topics)}

For secondary keywords:
- Create long-tail variations (3+ words)
- Include question-based keywords (how to, what is, etc.)
- Focus on lower difficulty (low/medium)
- Mix of informational and commercial intent
- Support the primary keywords

Return as JSON array with same structure as before:
keyword, search_intent, difficulty, monthly_volume_estimate, relevance_score, long_tail, question_based, related_topics"""

        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
                temperature=0.5,
            )

            # Parse JSON response (extract from markdown if needed)
            json_str = extract_json_from_response(response)
            keywords_data = json.loads(json_str)
            keywords = []

            for kw_data in keywords_data[:30]:  # Max 30 secondary
                keyword = Keyword(
                    keyword=kw_data["keyword"],
                    search_intent=SearchIntent(kw_data["search_intent"]),
                    difficulty=KeywordDifficulty(kw_data["difficulty"]),
                    monthly_volume_estimate=kw_data["monthly_volume_estimate"],
                    relevance_score=float(kw_data["relevance_score"]),
                    long_tail=kw_data.get("long_tail", True),
                    question_based=kw_data.get("question_based", False),
                    related_topics=kw_data.get("related_topics", []),
                )
                keywords.append(keyword)

            logger.info(f"Identified {len(keywords)} secondary keywords")
            return keywords

        except Exception as e:
            logger.error(f"Failed to research secondary keywords: {e}")
            return self._generate_fallback_secondary_keywords(primary_keywords)

    def _create_keyword_clusters(
        self,
        main_topics: List[str],
        primary_keywords: List[Keyword],
        secondary_keywords: List[Keyword],
    ) -> List[KeywordCluster]:
        """Group keywords into thematic clusters"""
        clusters = []
        all_keywords = primary_keywords + secondary_keywords

        # Create one cluster per main topic
        for topic in main_topics:
            # Find keywords related to this topic
            topic_keywords = [
                kw
                for kw in all_keywords
                if topic.lower() in kw.keyword.lower()
                or any(topic.lower() in t.lower() for t in kw.related_topics)
            ]

            if not topic_keywords:
                continue

            # Pick primary keyword (highest relevance)
            primary_kw = max(topic_keywords, key=lambda k: k.relevance_score)
            secondary_kws = [kw.keyword for kw in topic_keywords if kw != primary_kw][:10]

            # Determine priority based on keyword difficulty and relevance
            avg_difficulty = sum(
                1
                if kw.difficulty == KeywordDifficulty.LOW
                else 2
                if kw.difficulty == KeywordDifficulty.MEDIUM
                else 3
                for kw in topic_keywords
            ) / len(topic_keywords)
            avg_relevance = sum(kw.relevance_score for kw in topic_keywords) / len(topic_keywords)

            if avg_relevance >= 8 and avg_difficulty <= 2:
                priority = "High"
            elif avg_relevance >= 6:
                priority = "Medium"
            else:
                priority = "Low"

            # Generate content suggestions
            content_suggestions = [
                f"Ultimate guide to {primary_kw.keyword}",
                f"How to {primary_kw.keyword} (step-by-step)",
                f"{primary_kw.keyword}: Best practices and tips",
            ]

            cluster = KeywordCluster(
                theme=topic,
                primary_keyword=primary_kw.keyword,
                secondary_keywords=secondary_kws,
                content_suggestions=content_suggestions,
                priority=priority,
            )
            clusters.append(cluster)

        logger.info(f"Created {len(clusters)} keyword clusters")
        return clusters

    def _identify_quick_wins(
        self, primary_keywords: List[Keyword], secondary_keywords: List[Keyword]
    ) -> List[str]:
        """Identify low-difficulty, high-relevance keywords"""
        all_keywords = primary_keywords + secondary_keywords

        quick_wins = [
            kw.keyword
            for kw in all_keywords
            if kw.difficulty == KeywordDifficulty.LOW and kw.relevance_score >= 7.0
        ]

        # If not enough low difficulty, include medium difficulty with high relevance
        if len(quick_wins) < 5:
            medium_wins = [
                kw.keyword
                for kw in all_keywords
                if kw.difficulty == KeywordDifficulty.MEDIUM and kw.relevance_score >= 8.5
            ]
            quick_wins.extend(medium_wins[: 5 - len(quick_wins)])

        logger.info(f"Identified {len(quick_wins)} quick-win keywords")
        return quick_wins[:10]  # Max 10

    def _analyze_competitors(
        self,
        competitors: List[str],
        business_desc: str,
        primary_keywords: List[Keyword],
    ) -> List[CompetitorKeywords]:
        """Analyze competitor keyword strategies"""
        primary_kw_list = [kw.keyword for kw in primary_keywords]

        competitor_analysis = []

        for competitor in competitors[:3]:  # Max 3 competitors
            prompt = f"""Analyze this competitor's likely keyword strategy.

Competitor: {competitor}

Our Business: {business_desc}

Our Target Keywords: {', '.join(primary_kw_list)}

Estimate:
1. What 10-15 keywords are they likely targeting?
2. What keyword gaps exist (keywords we could target that they don't)?
3. What overlaps exist (keywords both of us target)?

Return as JSON with keys:
estimated_keywords (list), gaps (list), overlaps (list)"""

            try:
                response = self.client.create_message(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1500,
                    temperature=0.4,
                )

                data = json.loads(response)
                analysis = CompetitorKeywords(
                    competitor_name=competitor,
                    estimated_keywords=data.get("estimated_keywords", [])[:15],
                    gaps=data.get("gaps", [])[:10],
                    overlaps=data.get("overlaps", [])[:10],
                )
                competitor_analysis.append(analysis)

            except Exception as e:
                logger.warning(f"Failed to analyze competitor {competitor}: {e}")
                continue

        logger.info(f"Analyzed {len(competitor_analysis)} competitors")
        return competitor_analysis

    def _generate_content_priorities(
        self,
        clusters: List[KeywordCluster],
        quick_wins: List[str],
        competitor_analysis: List[CompetitorKeywords],
    ) -> List[str]:
        """Generate top 5 content pieces to create"""
        priorities = []

        # Priority 1-2: High-priority clusters
        high_priority_clusters = [c for c in clusters if c.priority == "High"]
        for cluster in high_priority_clusters[:2]:
            priorities.append(
                f"[HIGH] {cluster.content_suggestions[0]} (targets: {cluster.primary_keyword})"
            )

        # Priority 3-4: Quick win keywords
        for kw in quick_wins[:2]:
            priorities.append(f"[QUICK WIN] How-to guide for '{kw}'")

        # Priority 5: Gap opportunity from competitors (if available)
        if competitor_analysis:
            gaps = []
            for comp in competitor_analysis:
                gaps.extend(comp.gaps)
            if gaps:
                priorities.append(f"[GAP] Compete on '{gaps[0]}' (competitor weakness)")

        # Fill to 5 with medium priority clusters
        if len(priorities) < 5:
            medium_clusters = [c for c in clusters if c.priority == "Medium"]
            for cluster in medium_clusters[: 5 - len(priorities)]:
                priorities.append(
                    f"[MEDIUM] {cluster.content_suggestions[0]} (targets: {cluster.primary_keyword})"
                )

        return priorities[:5]

    def _create_strategy_summary(
        self,
        primary_keywords: List[Keyword],
        secondary_keywords: List[Keyword],
        clusters: List[KeywordCluster],
        quick_wins: List[str],
        competitor_analysis: List[CompetitorKeywords],
    ) -> str:
        """Generate executive summary of keyword strategy"""
        # Count intent distribution
        intent_counts = {}
        for kw in primary_keywords:
            intent_counts[kw.search_intent.value] = intent_counts.get(kw.search_intent.value, 0) + 1

        # Count difficulty distribution
        difficulty_counts = {}
        for kw in primary_keywords + secondary_keywords:
            difficulty_counts[kw.difficulty.value] = (
                difficulty_counts.get(kw.difficulty.value, 0) + 1
            )

        summary = f"""This keyword strategy identifies {len(primary_keywords)} primary keywords and {len(secondary_keywords)} secondary/long-tail keywords organized into {len(clusters)} thematic clusters.

**Search Intent Focus:** {max(intent_counts, key=intent_counts.get).title()} intent dominates with {intent_counts[max(intent_counts, key=intent_counts.get)]} primary keywords, supporting {"awareness and education" if max(intent_counts, key=intent_counts.get) == "informational" else "conversion and sales"}.

**Difficulty Balance:** {difficulty_counts.get('low', 0)} low-difficulty keywords offer quick wins, {difficulty_counts.get('medium', 0)} medium-difficulty keywords provide sustainable growth, and {difficulty_counts.get('high', 0)} high-difficulty keywords represent long-term authority plays.

**Quick Wins:** {len(quick_wins)} keywords identified as immediate opportunities due to low competition and high relevance.

{"**Competitive Positioning:** " + str(len(competitor_analysis)) + " competitors analyzed, revealing " + str(sum(len(c.gaps) for c in competitor_analysis)) + " gap opportunities where we can compete effectively." if competitor_analysis else ""}

**Recommended Approach:** Start with quick-win keywords to build authority, then systematically target medium-difficulty keywords in high-priority clusters."""

        return summary

    def _generate_fallback_primary_keywords(self, main_topics: List[str]) -> List[Keyword]:
        """Generate basic keywords if API fails"""
        keywords = []
        for topic in main_topics[:5]:
            keyword = Keyword(
                keyword=topic.lower(),
                search_intent=SearchIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.MEDIUM,
                monthly_volume_estimate="Unknown",
                relevance_score=7.0,
                long_tail=False,
                question_based=False,
                related_topics=[topic],
            )
            keywords.append(keyword)
        return keywords

    def _generate_fallback_secondary_keywords(
        self, primary_keywords: List[Keyword]
    ) -> List[Keyword]:
        """Generate basic secondary keywords if API fails"""
        keywords = []
        question_words = ["how to", "what is", "why", "when to", "best"]

        for primary_kw in primary_keywords[:5]:
            for qw in question_words:
                keyword = Keyword(
                    keyword=f"{qw} {primary_kw.keyword}",
                    search_intent=SearchIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.LOW,
                    monthly_volume_estimate="Unknown",
                    relevance_score=6.0,
                    long_tail=True,
                    question_based=True,
                    related_topics=primary_kw.related_topics,
                )
                keywords.append(keyword)
                if len(keywords) >= 20:
                    break
            if len(keywords) >= 20:
                break

        return keywords

    def generate_reports(self, strategy: KeywordStrategy) -> Dict[str, Path]:
        """Generate keyword strategy reports in multiple formats"""
        output_dir = self.base_output_dir / self.project_id
        output_dir.mkdir(parents=True, exist_ok=True)

        reports = {}

        # JSON report
        json_path = output_dir / "keyword_strategy.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(strategy.model_dump(), f, indent=2)
        reports["json"] = json_path

        # Markdown report
        markdown_path = output_dir / "keyword_strategy_report.md"
        markdown_content = self._format_markdown_report(strategy)
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        reports["markdown"] = markdown_path

        # Text report (simple list)
        text_path = output_dir / "keyword_list.txt"
        text_content = self._format_text_report(strategy)
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        reports["text"] = text_path

        logger.info(f"Generated {len(reports)} report formats")
        return reports

    def _format_markdown_report(self, strategy: KeywordStrategy) -> str:
        """Format strategy as markdown report"""
        md = f"""# SEO Keyword Strategy Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

**Business:** {strategy.business_name}
**Industry:** {strategy.industry}
**Target Audience:** {strategy.target_audience}

---

## Executive Summary

{strategy.strategy_summary}

---

## Primary Keywords ({len(strategy.primary_keywords)})

"""

        for i, kw in enumerate(strategy.primary_keywords, 1):
            md += f"""
### {i}. {kw.keyword}

- **Search Intent:** {kw.search_intent.value.title()}
- **Difficulty:** {kw.difficulty.value.upper()}
- **Volume Estimate:** {kw.monthly_volume_estimate}
- **Relevance Score:** {kw.relevance_score}/10
- **Long-tail:** {"Yes" if kw.long_tail else "No"}
- **Question-based:** {"Yes" if kw.question_based else "No"}
- **Related Topics:** {", ".join(kw.related_topics)}
"""

        md += f"""
---

## Secondary Keywords ({len(strategy.secondary_keywords)})

"""

        for i, kw in enumerate(strategy.secondary_keywords[:10], 1):
            md += f"{i}. **{kw.keyword}** ({kw.difficulty.value}, {kw.search_intent.value})\n"

        if len(strategy.secondary_keywords) > 10:
            md += f"\n*... and {len(strategy.secondary_keywords) - 10} more*\n"

        md += """
---

## Keyword Clusters

"""

        for cluster in strategy.keyword_clusters:
            md += f"""
### [{cluster.priority.upper()}] {cluster.theme}

**Primary Keyword:** {cluster.primary_keyword}

**Secondary Keywords:** {", ".join(cluster.secondary_keywords[:5])}

**Content Ideas:**
"""
            for suggestion in cluster.content_suggestions:
                md += f"- {suggestion}\n"

        if strategy.quick_win_keywords:
            md += """
---

## Quick Win Keywords

Target these first for early SEO wins:

"""
            for kw in strategy.quick_win_keywords:
                md += f"- {kw}\n"

        if strategy.competitor_analysis:
            md += """
---

## Competitor Analysis

"""
            for comp in strategy.competitor_analysis:
                md += f"""
### {comp.competitor_name}

**Their Keywords:** {", ".join(comp.estimated_keywords[:5])}

**Gap Opportunities:** {", ".join(comp.gaps[:3])}

**Overlaps:** {", ".join(comp.overlaps[:3])}

"""

        md += """
---

## Content Priorities

Recommended content pieces to create (in priority order):

"""
        for i, priority in enumerate(strategy.content_priorities, 1):
            md += f"{i}. {priority}\n"

        md += """
---

*Report generated by SEO Keyword Research Tool ($400)*
"""

        return md

    def _format_text_report(self, strategy: KeywordStrategy) -> str:
        """Format strategy as simple text list"""
        text = f"""SEO KEYWORD STRATEGY - {strategy.business_name}
{"=" * 60}

PRIMARY KEYWORDS ({len(strategy.primary_keywords)}):
"""

        for i, kw in enumerate(strategy.primary_keywords, 1):
            text += f"{i}. {kw.keyword} ({kw.difficulty.value}, {kw.search_intent.value})\n"

        text += f"\n\nSECONDARY KEYWORDS ({len(strategy.secondary_keywords)}):\n"

        for i, kw in enumerate(strategy.secondary_keywords, 1):
            text += f"{i}. {kw.keyword}\n"

        if strategy.quick_win_keywords:
            text += "\n\nQUICK WINS:\n"
            for kw in strategy.quick_win_keywords:
                text += f"- {kw}\n"

        text += "\n\nCONTENT PRIORITIES:\n"
        for i, priority in enumerate(strategy.content_priorities, 1):
            text += f"{i}. {priority}\n"

        return text
