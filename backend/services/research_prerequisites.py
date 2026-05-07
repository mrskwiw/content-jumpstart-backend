"""Research Tool Prerequisites System

Manages dependencies between research tools to ensure:
1. Critical prerequisites run before dependent tools
2. Tools are blocked if prerequisites haven't been completed
3. Batch runs execute in correct dependency order
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from ..utils.logger import logger


class PrerequisiteType(str, Enum):
    """Prerequisite requirement types"""

    REQUIRED = "required"  # Must run before dependent tool
    RECOMMENDED = "recommended"  # Should run before, but not blocking
    OPTIONAL = "optional"  # Enhances results if available


@dataclass
class ToolPrerequisite:
    """Prerequisite definition for a research tool"""

    tool_id: str
    type: PrerequisiteType
    reason: str  # Why this prerequisite is needed


@dataclass
class ToolDependencies:
    """Complete dependency information for a tool"""

    tool_id: str
    tier: int  # Execution tier (1-4)
    prerequisites: List[ToolPrerequisite]
    used_by: List[str]  # Tools that depend on this one
    description: str


# Complete dependency registry based on research-tool-dependencies.md
TOOL_DEPENDENCIES: Dict[str, ToolDependencies] = {
    # Tier 1: Foundation Tools (No Dependencies)
    "voice_analysis": ToolDependencies(
        tool_id="voice_analysis",
        tier=1,
        prerequisites=[],
        used_by=["story_mining", "content_calendar"],
        description="Brand voice patterns, tone guidelines, writing style",
    ),
    "brand_archetype": ToolDependencies(
        tool_id="brand_archetype",
        tier=1,
        prerequisites=[],
        used_by=["story_mining", "platform_strategy"],
        description="Brand archetype and personality traits",
    ),
    "seo_keyword_research": ToolDependencies(
        tool_id="seo_keyword_research",
        tier=1,
        prerequisites=[],
        used_by=["market_trends_research", "content_gap_analysis", "content_calendar"],
        description="Primary keywords, secondary keywords, keyword clusters",
    ),
    # NOTE (Bug #47 - Partially Complete): audience_research requires:
    # 1. Web search integration (Brave/Tavily/SerpAPI) - IMPLEMENTED ✓
    # 2. Census API integration - PENDING (Task #46 in TODO.md)
    # Web search provides current audience behavior data
    # Census API will add official demographic data (income, education, population)
    "audience_research": ToolDependencies(
        tool_id="audience_research",
        tier=1,
        prerequisites=[],
        used_by=["icp_workshop", "platform_strategy"],
        description="Detailed personas, pain points, motivations",
    ),
    "determine_competitors": ToolDependencies(
        tool_id="determine_competitors",
        tier=1,  # Foundation tool, no prerequisites
        prerequisites=[],
        used_by=["competitive_analysis"],
        description="Automated competitor discovery and positioning analysis",
    ),
    "competitive_analysis": ToolDependencies(
        tool_id="competitive_analysis",
        tier=2,  # Promoted: requires determine_competitors to run first
        prerequisites=[
            ToolPrerequisite(
                tool_id="determine_competitors",
                type=PrerequisiteType.REQUIRED,
                reason="Competitor names must be known before analysing their strategy",
            ),
        ],
        used_by=["content_gap_analysis", "market_trends_research"],
        description="Competitor strengths, gaps, differentiators",
    ),
    # Tier 2: Analysis Tools (Enhanced by Tier 1)
    "content_gap_analysis": ToolDependencies(
        tool_id="content_gap_analysis",
        tier=2,
        prerequisites=[
            ToolPrerequisite(
                tool_id="competitive_analysis",
                type=PrerequisiteType.REQUIRED,
                reason="Required for accurate content gap identification",
            ),
            ToolPrerequisite(
                tool_id="seo_keyword_research",
                type=PrerequisiteType.RECOMMENDED,
                reason="Identifies keyword opportunities",
            ),
        ],
        used_by=["platform_strategy", "content_calendar"],
        description="Missing content opportunities, topic gaps",
    ),
    # NOTE (Bug #46): market_trends_research REQUIRES web search integration (Brave/Tavily/SerpAPI)
    # Web search is not a research TOOL but an infrastructure requirement
    # Users must configure web search in settings for current trend data
    "market_trends_research": ToolDependencies(
        tool_id="market_trends_research",
        tier=2,
        prerequisites=[
            ToolPrerequisite(
                tool_id="seo_keyword_research",
                type=PrerequisiteType.RECOMMENDED,
                reason="Generates targeted focus areas from SEO keywords",
            ),
        ],
        used_by=["platform_strategy", "content_calendar"],
        description="Industry trends, emerging topics, seasonal patterns",
    ),
    "icp_workshop": ToolDependencies(
        tool_id="icp_workshop",
        tier=2,
        prerequisites=[
            ToolPrerequisite(
                tool_id="audience_research",
                type=PrerequisiteType.RECOMMENDED,
                reason="Provides enhanced persona data",
            ),
        ],
        used_by=["content_calendar", "platform_strategy"],
        description="Ideal Customer Profile, firmographics, psychographics",
    ),
    "content_audit": ToolDependencies(
        tool_id="content_audit",
        tier=2,
        prerequisites=[
            ToolPrerequisite(
                tool_id="seo_keyword_research",
                type=PrerequisiteType.OPTIONAL,
                reason="Checks keyword alignment in existing content",
            ),
        ],
        used_by=["content_gap_analysis", "content_calendar"],
        description="Performance analysis, update/archive recommendations",
    ),
    "business_report": ToolDependencies(
        tool_id="business_report",
        tier=2,
        prerequisites=[],
        used_by=[],
        description="Company perception analysis, strengths, pain points, value proposition",
    ),
    # Tier 3: Strategy Tools (Synthesize Research)
    "platform_strategy": ToolDependencies(
        tool_id="platform_strategy",
        tier=3,
        prerequisites=[
            ToolPrerequisite(
                tool_id="audience_research",
                type=PrerequisiteType.REQUIRED,
                reason="Provides audience understanding for platform selection",
            ),
            ToolPrerequisite(
                tool_id="content_gap_analysis",
                type=PrerequisiteType.RECOMMENDED,
                reason="Identifies content types needed per platform",
            ),
            ToolPrerequisite(
                tool_id="market_trends_research",
                type=PrerequisiteType.RECOMMENDED,
                reason="Identifies trending platforms and content formats",
            ),
        ],
        used_by=["content_calendar"],
        description="Platform recommendations, posting frequency, content mix",
    ),
    "story_mining": ToolDependencies(
        tool_id="story_mining",
        tier=3,
        prerequisites=[
            ToolPrerequisite(
                tool_id="voice_analysis",
                type=PrerequisiteType.RECOMMENDED,
                reason="Ensures stories match brand voice",
            ),
            ToolPrerequisite(
                tool_id="brand_archetype",
                type=PrerequisiteType.RECOMMENDED,
                reason="Frames stories according to brand archetype",
            ),
        ],
        used_by=["content_calendar"],
        description="Brand stories, customer success stories, narrative frameworks",
    ),
    # Tier 4: Execution Tools (Create Deliverables)
    "content_calendar": ToolDependencies(
        tool_id="content_calendar",
        tier=4,
        prerequisites=[
            ToolPrerequisite(
                tool_id="seo_keyword_research",
                type=PrerequisiteType.REQUIRED,
                reason="Provides topics to cover in content calendar",
            ),
            ToolPrerequisite(
                tool_id="platform_strategy",
                type=PrerequisiteType.REQUIRED,
                reason="Determines where to post content",
            ),
            ToolPrerequisite(
                tool_id="content_gap_analysis",
                type=PrerequisiteType.RECOMMENDED,
                reason="Prioritizes topics based on gaps",
            ),
            ToolPrerequisite(
                tool_id="market_trends_research",
                type=PrerequisiteType.RECOMMENDED,
                reason="Adds timely, trending topics",
            ),
            ToolPrerequisite(
                tool_id="story_mining",
                type=PrerequisiteType.OPTIONAL,
                reason="Includes story-based content in calendar",
            ),
        ],
        used_by=[],
        description="30-90 day content calendar with topics, platforms, timing",
    ),
}


class ResearchPrerequisites:
    """Manages research tool prerequisites and execution order"""

    def __init__(self):
        self.dependencies = TOOL_DEPENDENCIES

    def get_dependencies(self, tool_id: str) -> Optional[ToolDependencies]:
        """Get dependency information for a tool"""
        return self.dependencies.get(tool_id)

    def get_required_prerequisites(self, tool_id: str) -> List[str]:
        """Get list of REQUIRED prerequisite tool IDs"""
        deps = self.get_dependencies(tool_id)
        if not deps:
            return []

        return [
            prereq.tool_id
            for prereq in deps.prerequisites
            if prereq.type == PrerequisiteType.REQUIRED
        ]

    def get_recommended_prerequisites(self, tool_id: str) -> List[str]:
        """Get list of RECOMMENDED prerequisite tool IDs"""
        deps = self.get_dependencies(tool_id)
        if not deps:
            return []

        return [
            prereq.tool_id
            for prereq in deps.prerequisites
            if prereq.type == PrerequisiteType.RECOMMENDED
        ]

    def get_optional_prerequisites(self, tool_id: str) -> List[str]:
        """Get list of OPTIONAL prerequisite tool IDs"""
        deps = self.get_dependencies(tool_id)
        if not deps:
            return []

        return [
            prereq.tool_id
            for prereq in deps.prerequisites
            if prereq.type == PrerequisiteType.OPTIONAL
        ]

    def check_prerequisites_met(
        self, tool_id: str, completed_tools: Set[str]
    ) -> tuple[bool, List[str], List[str]]:
        """
        Check if prerequisites are met for a tool.

        Args:
            tool_id: Tool to check
            completed_tools: Set of tool IDs that have already completed

        Returns:
            Tuple of (can_run, missing_required, missing_recommended)
            - can_run: True if all REQUIRED prerequisites are met
            - missing_required: List of missing REQUIRED prerequisites
            - missing_recommended: List of missing RECOMMENDED prerequisites
        """
        required = self.get_required_prerequisites(tool_id)
        recommended = self.get_recommended_prerequisites(tool_id)

        missing_required = [t for t in required if t not in completed_tools]
        missing_recommended = [t for t in recommended if t not in completed_tools]

        can_run = len(missing_required) == 0

        return can_run, missing_required, missing_recommended

    def get_execution_order(self, tool_ids: List[str]) -> List[str]:
        """
        Determine optimal execution order for a list of tools based on dependencies.

        Uses topological sort to ensure prerequisites run before dependent tools.

        Args:
            tool_ids: List of tool IDs to execute

        Returns:
            Ordered list of tool IDs (prerequisites first)
        """
        # Build dependency graph
        graph: Dict[str, Set[str]] = {tool_id: set() for tool_id in tool_ids}
        in_degree: Dict[str, int] = {tool_id: 0 for tool_id in tool_ids}

        for tool_id in tool_ids:
            deps = self.get_dependencies(tool_id)
            if not deps:
                continue

            # Add edges for prerequisites that are in the current batch
            for prereq in deps.prerequisites:
                if prereq.tool_id in tool_ids:
                    # prereq.tool_id must run before tool_id
                    graph[prereq.tool_id].add(tool_id)
                    in_degree[tool_id] += 1

        # Topological sort (Kahn's algorithm)
        queue = [tool_id for tool_id in tool_ids if in_degree[tool_id] == 0]
        ordered = []

        while queue:
            # Sort by tier to maintain logical grouping
            queue.sort(
                key=lambda t: self.dependencies.get(t, ToolDependencies("", 999, [], [], "")).tier
            )

            current = queue.pop(0)
            ordered.append(current)

            # Process tools that depend on current
            for dependent in graph[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Check for circular dependencies
        if len(ordered) != len(tool_ids):
            cyclic = [t for t in tool_ids if t not in ordered]
            logger.error(f"Circular dependency detected in tools: {cyclic}")
            raise ValueError(f"Circular dependency detected among research tools: {cyclic}")

        logger.info(f"Execution order: {ordered}")
        return ordered

    def get_parallel_groups(self, tool_ids: List[str]) -> List[List[str]]:
        """
        Group tools into parallel execution batches based on dependencies.

        Tools within the same group have no inter-dependencies and can run concurrently.
        Groups must be executed sequentially (group N+1 waits for group N to finish).

        Args:
            tool_ids: List of tool IDs to execute

        Returns:
            List of groups; each group is a list of tool IDs safe to run in parallel
        """
        graph: Dict[str, Set[str]] = {tool_id: set() for tool_id in tool_ids}
        in_degree: Dict[str, int] = {tool_id: 0 for tool_id in tool_ids}

        for tool_id in tool_ids:
            deps = self.get_dependencies(tool_id)
            if not deps:
                continue
            for prereq in deps.prerequisites:
                if prereq.tool_id in tool_ids:
                    graph[prereq.tool_id].add(tool_id)
                    in_degree[tool_id] += 1

        def _tier(t: str) -> int:
            return self.dependencies.get(t, ToolDependencies("", 999, [], [], "")).tier

        groups: List[List[str]] = []
        current_level = sorted([t for t in tool_ids if in_degree[t] == 0], key=_tier)

        while current_level:
            groups.append(current_level)
            next_level: List[str] = []
            for tool in current_level:
                for dependent in graph[tool]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_level.append(dependent)
            current_level = sorted(next_level, key=_tier)

        if sum(len(g) for g in groups) != len(tool_ids):
            cyclic = [t for t in tool_ids if not any(t in g for g in groups)]
            logger.error(f"Circular dependency detected in tools: {cyclic}")
            raise ValueError(f"Circular dependency detected among research tools: {cyclic}")

        logger.info(f"Parallel groups: {groups}")
        return groups

    def get_missing_prerequisites_message(
        self, tool_id: str, missing_required: List[str], missing_recommended: List[str]
    ) -> str:
        """Generate user-friendly message about missing prerequisites"""
        tool_name = tool_id.replace("_", " ").title()

        messages = []

        if missing_required:
            prereq_names = [t.replace("_", " ").title() for t in missing_required]
            deps = self.get_dependencies(tool_id)
            reasons = []
            if deps:
                for prereq in deps.prerequisites:
                    if prereq.tool_id in missing_required:
                        reasons.append(
                            f"  - {prereq.tool_id.replace('_', ' ').title()}: {prereq.reason}"
                        )

            msg = f"❌ {tool_name} cannot run yet.\n\n"
            msg += f"Required prerequisites: {', '.join(prereq_names)}\n\n"
            if reasons:
                msg += "Why these are needed:\n" + "\n".join(reasons)
            messages.append(msg)

        if missing_recommended:
            prereq_names = [t.replace("_", " ").title() for t in missing_recommended]
            msg = f"⚠️ {tool_name} will run, but results would be better with: {', '.join(prereq_names)}"
            messages.append(msg)

        return "\n\n".join(messages)

    def get_tool_tier(self, tool_id: str) -> int:
        """Get execution tier for a tool (1-4)"""
        deps = self.get_dependencies(tool_id)
        return deps.tier if deps else 999  # Unknown tools go last


# System Prerequisites (Infrastructure Requirements)
# These are not research tools but configuration requirements


class SystemPrerequisiteType(str, Enum):
    """Types of system/infrastructure prerequisites"""

    WEB_SEARCH = "web_search"  # Requires web search API configured
    CENSUS_API = "census_api"  # Requires Census API configured


# Tools that require web search to be configured
REQUIRES_WEB_SEARCH = {
    "market_trends_research",
    "competitive_analysis",
    "content_gap_analysis",
    "audience_research",
    "business_report",
    "determine_competitors",
}


def get_system_prerequisites(tool_id: str) -> List[SystemPrerequisiteType]:
    """
    Get system/infrastructure prerequisites for a tool.

    Args:
        tool_id: Research tool identifier

    Returns:
        List of system prerequisites required
    """
    prerequisites = []

    if tool_id in REQUIRES_WEB_SEARCH:
        prerequisites.append(SystemPrerequisiteType.WEB_SEARCH)

    return prerequisites
