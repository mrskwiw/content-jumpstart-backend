"""
Research Service - Orchestrates research tool execution

Handles:
- Mapping research tool names to implementations
- Brief file creation for research tools
- Research tool execution
- Output file management
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi.concurrency import run_in_threadpool

from sqlalchemy.orm import Session

# Add src directory to path for imports
# In Docker: /app/src
# In local dev: {project_root}/src
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
if src_path.exists():
    sys.path.insert(0, str(project_root))
else:
    # Fallback: might be in /app in Docker
    app_src = Path("/app/src")
    if app_src.exists():
        sys.path.insert(0, "/app")

# Try importing research tools
RESEARCH_TOOLS_AVAILABLE = False
RESEARCH_TOOL_MAP = {}

try:
    from src.research.voice_analysis import VoiceAnalyzer
    from src.research.brand_archetype import BrandArchetypeAnalyzer
    from src.research.seo_keyword_research import SEOKeywordResearcher
    from src.research.determine_competitors import CompetitorDeterminer
    from src.research.competitive_analysis import CompetitiveAnalyzer
    from src.research.content_gap_analysis import ContentGapAnalyzer
    from src.research.market_trends_research import MarketTrendsResearcher
    from src.research.content_audit import ContentAuditor
    from src.research.platform_strategy import PlatformStrategist
    from src.research.content_calendar_strategy import ContentCalendarStrategist
    from src.research.audience_research import AudienceResearcher
    from src.research.icp_workshop import ICPWorkshopFacilitator
    from src.research.story_mining import StoryMiner
    from src.research.business_report import BusinessReportTool

    RESEARCH_TOOLS_AVAILABLE = True
    RESEARCH_TOOL_MAP = {
        "voice_analysis": VoiceAnalyzer,
        "brand_archetype": BrandArchetypeAnalyzer,
        "seo_keyword_research": SEOKeywordResearcher,
        "determine_competitors": CompetitorDeterminer,
        "competitive_analysis": CompetitiveAnalyzer,
        "content_gap_analysis": ContentGapAnalyzer,
        "market_trends_research": MarketTrendsResearcher,
        "content_audit": ContentAuditor,
        "platform_strategy": PlatformStrategist,
        "content_calendar": ContentCalendarStrategist,
        "audience_research": AudienceResearcher,
        "icp_workshop": ICPWorkshopFacilitator,
        "story_mining": StoryMiner,
        "business_report": BusinessReportTool,
    }
except ImportError as e:
    # Research tools not available - service will return stub responses
    RESEARCH_TOOLS_AVAILABLE = False
    RESEARCH_TOOL_MAP = {}
    logger = __import__("logging").getLogger(__name__)
    logger.warning(f"Research tools not available: {str(e)}")

# IMPORTANT: Use relative imports to avoid SQLAlchemy table redefinition errors
from backend.services.research_context_builder import invalidate_cache  # noqa: E402

# Absolute imports (backend.models) cause circular dependencies in production
from backend.models import Project, Client  # noqa: E402
from backend.services import crud  # noqa: E402

# Logger import with fallback
try:
    import sys
    from pathlib import Path

    # Add src to path for logger
    project_root = Path(__file__).parent.parent.parent
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    from utils.logger import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class ResearchService:
    """Service for research tool execution"""

    def __init__(self):
        # Initialize prerequisite checker
        from backend.services.research_prerequisites import ResearchPrerequisites

        self.prerequisites = ResearchPrerequisites()

    def _fetch_prerequisite_data(
        self, db: Session, project_id: str, tool_name: str
    ) -> Dict[str, Any]:
        """
        Fetch results from prerequisite tools and extract relevant data.

        This enables staged execution where tools access data from previously
        completed research stored in the database.

        Args:
            db: Database session
            project_id: Project ID
            tool_name: Tool requesting prerequisite data

        Returns:
            Dict of prerequisite data to merge into tool inputs
        """
        from backend.models import ResearchResult

        # Get all prerequisites for this tool
        all_prereqs = (
            self.prerequisites.get_required_prerequisites(tool_name)
            + self.prerequisites.get_recommended_prerequisites(tool_name)
            + self.prerequisites.get_optional_prerequisites(tool_name)
        )

        if not all_prereqs:
            return {}  # No prerequisites needed

        logger.info(f"Fetching prerequisite data for {tool_name}: {all_prereqs}")

        prerequisite_data = {}

        for prereq_tool in all_prereqs:
            # Fetch most recent completed result for this prerequisite
            result = (
                db.query(ResearchResult)
                .filter(
                    ResearchResult.project_id == project_id,
                    ResearchResult.tool_name == prereq_tool,
                    ResearchResult.status == "completed",
                )
                .order_by(ResearchResult.created_at.desc())
                .first()
            )

            if not result:
                logger.debug(f"Prerequisite {prereq_tool} not found for {tool_name}")
                continue

            # Extract relevant data based on prerequisite tool type
            if prereq_tool == "seo_keyword_research" and result.data:
                # Extract SEO keywords for tools that need them
                prerequisite_data["seo_keywords"] = result.data.get("primary_keywords", [])
                if not prerequisite_data["seo_keywords"]:
                    # Fallback to all keywords if primary not available
                    prerequisite_data["seo_keywords"] = result.data.get("keywords", [])

                logger.info(f"Loaded {len(prerequisite_data.get('seo_keywords', []))} SEO keywords")

            elif prereq_tool == "audience_research" and result.data:
                # Extract audience personas for Platform Strategy, ICP, etc.
                prerequisite_data["audience_personas"] = result.data.get("personas", [])
                prerequisite_data["audience_demographics"] = result.data.get("demographics", {})
                prerequisite_data["audience_pain_points"] = result.data.get("pain_points", [])

                logger.info("Loaded audience research data")

            elif prereq_tool == "competitive_analysis" and result.data:
                # Extract competitor insights for Content Gap
                prerequisite_data["competitor_insights"] = result.data.get("competitors", [])
                prerequisite_data["competitor_gaps"] = result.data.get("gaps", [])

                logger.info("Loaded competitive analysis data")

            elif prereq_tool == "market_trends_research" and result.data:
                # Extract trends for Platform Strategy, Content Calendar
                prerequisite_data["market_trends"] = result.data.get("trends", [])
                prerequisite_data["trending_topics"] = result.data.get("trending_topics", [])

                logger.info("Loaded market trends data")

            elif prereq_tool == "platform_strategy" and result.data:
                # Extract platform recommendations for Content Calendar
                prerequisite_data["platform_recommendations"] = result.data.get("platforms", [])
                prerequisite_data["posting_frequency"] = result.data.get("frequency", {})

                logger.info("Loaded platform strategy data")

            elif prereq_tool == "content_gap_analysis" and result.data:
                # Extract content gaps for Content Calendar
                prerequisite_data["content_gaps"] = result.data.get("gaps", [])
                prerequisite_data["priority_topics"] = result.data.get("priority_topics", [])

                logger.info("Loaded content gap data")

            elif prereq_tool == "voice_analysis" and result.data:
                # Extract voice patterns for Story Mining
                prerequisite_data["brand_voice"] = result.data.get("voice_profile", {})
                prerequisite_data["tone_guidelines"] = result.data.get("tone", {})

                logger.info("Loaded voice analysis data")

            elif prereq_tool == "brand_archetype" and result.data:
                # Extract archetype for Story Mining, Platform Strategy
                prerequisite_data["brand_archetype"] = result.data.get("primary_archetype", "")
                prerequisite_data["archetype_traits"] = result.data.get("traits", [])

                logger.info("Loaded brand archetype data")

            elif prereq_tool == "icp_workshop" and result.data:
                # Extract ICP for Platform Strategy, Content Calendar
                prerequisite_data["ideal_customer_profile"] = result.data.get("icp", {})

                logger.info("Loaded ICP workshop data")

            elif prereq_tool == "story_mining" and result.data:
                # Extract stories for Content Calendar
                prerequisite_data["brand_stories"] = result.data.get("stories", [])

                logger.info("Loaded story mining data")

        logger.info(f"Fetched prerequisite data for {tool_name}: {list(prerequisite_data.keys())}")
        return prerequisite_data

    def _get_completed_tools(self, db: Session, project_id: str) -> set[str]:
        """Get set of tool IDs that have been completed for this project"""
        from backend.models import ResearchResult

        completed = (
            db.query(ResearchResult.tool_name)
            .filter(
                ResearchResult.project_id == project_id,
                ResearchResult.status == "completed",
            )
            .distinct()
            .all()
        )

        return {tool[0] for tool in completed}

    def _get_completed_tools_for_client(self, db: Session, client_id: str) -> set[str]:
        """Get set of tool IDs that have been completed for this client across all projects"""
        from backend.models import ResearchResult

        completed = (
            db.query(ResearchResult.tool_name)
            .filter(
                ResearchResult.client_id == client_id,
                ResearchResult.status == "completed",
                ResearchResult.is_deleted.is_(False),  # Exclude soft-deleted results
            )
            .distinct()
            .all()
        )

        return {tool[0] for tool in completed}

    def check_client_prerequisites(
        self,
        db: Session,
        client_id: str,
        tool_id: str,
    ) -> tuple[bool, list[str], list[str]]:
        """
        Check if prerequisites are met for a tool based on client's completed research.

        Args:
            db: Database session
            client_id: Client ID
            tool_id: Tool to check

        Returns:
            Tuple of (can_run, missing_required, missing_recommended)
        """
        # Get completed tools for this client
        completed_tools = self._get_completed_tools_for_client(db, client_id)

        # Check prerequisites
        return self.prerequisites.check_prerequisites_met(tool_id, completed_tools)

    def get_client_prerequisite_status(
        self, db: Session, client_id: str, tool_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """
        Get prerequisite status for multiple tools for a specific client.

        Args:
            db: Database session
            client_id: Client ID
            tool_ids: List of tool IDs to check

        Returns:
            Dict mapping tool_id to status dict with keys:
            - can_run: bool
            - completed: bool (has this tool been run for this client)
            - missing_required: list[str]
            - missing_recommended: list[str]
        """
        completed_tools = self._get_completed_tools_for_client(db, client_id)
        status_map = {}

        for tool_id in tool_ids:
            can_run, missing_required, missing_recommended = self.check_client_prerequisites(
                db, client_id, tool_id
            )

            status_map[tool_id] = {
                "can_run": can_run,
                "completed": tool_id in completed_tools,
                "missing_required": missing_required,
                "missing_recommended": missing_recommended,
                "last_run_at": self._get_last_run_time(db, client_id, tool_id),
            }

        return status_map

    def _get_last_run_time(self, db: Session, client_id: str, tool_id: str) -> Optional[str]:
        """
        Get the last run time for a specific tool for a client.

        Args:
            db: Database session
            client_id: Client ID
            tool_id: Tool ID

        Returns:
            ISO 8601 timestamp of last run, or None if never run
        """
        from backend.models import ResearchResult

        last_result = (
            db.query(ResearchResult.created_at)
            .filter(
                ResearchResult.client_id == client_id,
                ResearchResult.tool_name == tool_id,
                ResearchResult.status == "completed",
                ResearchResult.is_deleted.is_(False),
            )
            .order_by(ResearchResult.created_at.desc())
            .first()
        )

        if last_result and last_result[0]:
            from datetime import timezone

            dt = last_result[0]
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()

        return None

    def check_prerequisites(
        self,
        db: Session,
        project_id: str,
        tool_id: str,
        planned_tools: Optional[list[str]] = None,
    ) -> tuple[bool, list[str], list[str]]:
        """
        Check if prerequisites are met for a tool.

        Args:
            db: Database session
            project_id: Project ID
            tool_id: Tool to check
            planned_tools: Optional list of tools planned to run in same batch

        Returns:
            Tuple of (can_run, missing_required, missing_recommended)
        """
        # Get completed tools for this project
        completed_tools = self._get_completed_tools(db, project_id)

        # If this is part of a batch run, add planned tools to completed set
        if planned_tools:
            completed_tools.update(planned_tools)

        # Check prerequisites
        return self.prerequisites.check_prerequisites_met(tool_id, completed_tools)

    async def execute_research_tool(
        self,
        db: Session,
        project_id: str,
        client_id: str,
        tool_name: str,
        params: Optional[Dict] = None,
        planned_tools: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a research tool

        Args:
            db: Database session
            project_id: Project ID
            client_id: Client ID
            tool_name: Name of research tool to execute
            params: Optional parameters for the tool

        Returns:
            Dict with:
                - success: bool
                - outputs: Dict[str, str] (format -> file path)
                - metadata: Dict with execution metadata
                - error: Optional error message
        """
        logger.info(f"Executing research tool '{tool_name}' for project {project_id}")

        # Get project and client
        project = crud.get_project(db, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        client = crud.get_client(db, client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        # Access all needed attributes while session is active to prevent detachment errors
        project_platforms = project.platforms
        project_user_id = project.user_id
        client_name = client.name
        client_business_description = client.business_description
        client_ideal_customer = client.ideal_customer

        # Check if research tools are available
        if not RESEARCH_TOOLS_AVAILABLE:
            logger.warning(
                f"Research tools not available - returning demo response for '{tool_name}'"
            )
            # Return demo response with realistic sample data
            return self._get_demo_response(tool_name, project_id, client)

        # Check if tool exists
        if tool_name not in RESEARCH_TOOL_MAP:
            raise ValueError(f"Research tool '{tool_name}' not found")

        # Import system prerequisite functions
        from backend.services.research_prerequisites import (
            get_system_prerequisites,
            SystemPrerequisiteType,
        )
        from backend.utils.web_search_validator import is_web_search_configured

        # Check system prerequisites (infrastructure requirements)
        system_prereqs = get_system_prerequisites(tool_name)
        if SystemPrerequisiteType.WEB_SEARCH in system_prereqs:
            is_configured, message = is_web_search_configured(db, project_user_id)
            if not is_configured:
                logger.warning(f"Web search not configured for {tool_name}: {message}")
                return {
                    "success": False,
                    "outputs": {},
                    "metadata": {
                        "tool_name": tool_name,
                        "blocked": True,
                        "system_prerequisite_missing": "web_search",
                    },
                    "error": f"This tool requires web search to be configured. {message}",
                }
            logger.info(f"Web search configured for {tool_name}: using {message}")

        # Check prerequisites — client-scoped so tools completed in any prior
        # project for this client count (prevents false "missing prerequisite" errors).
        # Bug #147: also treat tools in the same batch run as "planned" so that
        # e.g. content_calendar doesn't block when seo_keyword_research is selected
        # alongside it but hasn't saved to DB yet.
        completed_tools = self._get_completed_tools_for_client(db, client_id)
        if planned_tools:
            completed_tools.update(planned_tools)
        can_run, missing_required, missing_recommended = self.prerequisites.check_prerequisites_met(
            tool_name, completed_tools
        )

        if not can_run:
            error_msg = self.prerequisites.get_missing_prerequisites_message(
                tool_name, missing_required, missing_recommended
            )
            logger.warning(f"Prerequisites not met for {tool_name}: {missing_required}")
            return {
                "success": False,
                "outputs": {},
                "metadata": {
                    "tool_name": tool_name,
                    "blocked": True,
                    "missing_required": missing_required,
                    "missing_recommended": missing_recommended,
                },
                "error": error_msg,
            }

        # Log if running with missing recommended prerequisites
        if missing_recommended:
            logger.info(
                f"Running {tool_name} without recommended prerequisites: {missing_recommended}"
            )

        # Get tool class
        ToolClass = RESEARCH_TOOL_MAP[tool_name]

        # Prepare inputs based on tool requirements
        inputs = self._prepare_inputs(
            project,
            client,
            tool_name,
            params or {},
            cached_client_name=client_name,
            cached_client_business_description=client_business_description,
            cached_client_ideal_customer=client_ideal_customer,
            cached_project_platforms=project_platforms,
        )

        # STAGED EXECUTION: Fetch data from prerequisite tools stored in database
        prerequisite_data = self._fetch_prerequisite_data(db, project_id, tool_name)
        inputs.update(prerequisite_data)  # Merge prerequisite data into inputs

        if prerequisite_data:
            logger.info(
                f"Enhanced {tool_name} with prerequisite data: {list(prerequisite_data.keys())}"
            )

        # Auto-populate current_content_topics for content_gap_analysis if empty
        if tool_name == "content_gap_analysis":
            current_topics = inputs.get("current_content_topics", "").strip()
            if not current_topics:
                # Try to use SEO keywords from prerequisite data
                seo_keywords = inputs.get("seo_keywords", [])
                if seo_keywords:
                    # Extract keyword strings (handle both dict and string formats)
                    keyword_strings = [
                        kw["keyword"] if isinstance(kw, dict) else str(kw)
                        for kw in seo_keywords[:10]
                    ]
                    current_topics = ", ".join(keyword_strings)
                    logger.info(
                        f"Auto-generated current_content_topics from {len(seo_keywords[:10])} SEO keywords"
                    )
                else:
                    # Fallback: use business description
                    current_topics = client.business_description or "General business topics"
                    logger.info("Auto-generated current_content_topics from business description")

                inputs["current_content_topics"] = current_topics

        try:
            # Inject user-configured search client so tools that call
            # get_search_client() internally pick up the DB-stored API key
            # rather than falling back to env-var lookup (which may be unset).
            if SystemPrerequisiteType.WEB_SEARCH in system_prereqs:
                from backend.services.web_search_factory import get_user_search_client
                from src.utils.web_search import set_default_client

                set_default_client(get_user_search_client(db, project.user_id))

            # Instantiate and execute tool.
            # tool.execute() is synchronous and blocks for ~60s (Claude API calls).
            # Run it in a thread pool so the event loop stays free to handle other
            # requests (e.g. login, health checks) while the tool is running.
            tool = ToolClass(project_id=project_id)
            result = await run_in_threadpool(tool.execute, inputs)

            # Get tool metadata for database storage
            from backend.routers.research import RESEARCH_TOOLS

            tool_class_metadata = next(
                (t.dict() for t in RESEARCH_TOOLS if t.name == tool_name),
                {"label": tool_name, "price": None},
            )

            # Save result to database
            import uuid
            from datetime import datetime
            from backend.models import ResearchResult

            # Convert Path objects to strings for JSON serialization
            def convert_paths_to_strings(obj):
                """Recursively convert Path objects to strings"""
                if isinstance(obj, dict):
                    return {k: convert_paths_to_strings(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_paths_to_strings(item) for item in obj]
                elif hasattr(obj, "__fspath__"):  # Path-like object
                    return str(obj)
                else:
                    return obj

            serializable_outputs = convert_paths_to_strings(result.outputs)

            research_result = ResearchResult(
                id=f"res-{uuid.uuid4().hex[:12]}",
                user_id=project.user_id,
                client_id=client_id,
                project_id=project_id,
                tool_name=tool_name,
                tool_label=tool_class_metadata.get("label"),
                tool_price=None,  # DEPRECATED: Tools use credits, not dollar prices
                params=params,
                outputs=serializable_outputs,
                data=result.metadata.get("data"),  # Tool-specific structured data
                status="completed" if result.success else "failed",
                error_message=result.error,
                duration_seconds=result.metadata.get("duration_seconds"),
                created_at=datetime.utcnow(),
            )

            db.add(research_result)
            db.commit()
            db.refresh(research_result)

            # Sync token usage from cost_tracker.db to database
            try:
                from backend.services.token_sync_service import token_sync_service

                usage_data = token_sync_service.sync_research_token_usage(
                    db=db, research_result_id=research_result.id, client_id=client_id
                )
                if usage_data:
                    logger.info(
                        f"Token tracking for research {research_result.id}: "
                        f"{usage_data.get('total_input_tokens', 0)} input tokens, "
                        f"${usage_data.get('total_cost', 0):.4f} cost"
                    )
            except Exception as e:
                logger.warning(f"Failed to sync research token usage (non-critical): {e}")

            # Story Mining Integration: Save mined stories to database
            if tool_name == "story_mining" and result.success:
                try:
                    from backend.services.story_service import story_service
                    from backend.schemas import StoryCreate

                    # Extract story data from research result
                    story_data = result.metadata.get("data", {}).get("story")

                    if story_data:
                        # Build structured full_story JSON
                        full_story = {
                            "customer_background": story_data.get("customer_background"),
                            "challenge": story_data.get("challenge"),
                            "decision_process": story_data.get("decision_process"),
                            "implementation": story_data.get("implementation"),
                            "results": story_data.get("results"),
                            "testimonials": story_data.get("testimonials"),
                            "future_plans": story_data.get("future_plans"),
                        }

                        # Extract key metrics from quantitative results
                        results = story_data.get("results", {})
                        quantitative_results = results.get("quantitative_results", [])
                        key_metrics = {}
                        for i, metric in enumerate(quantitative_results[:5], 1):
                            key_metrics[f"metric_{i}"] = metric

                        # Extract emotional hook from testimonials
                        testimonials = story_data.get("testimonials", {})
                        emotional_hook = testimonials.get("headline_quote")

                        # Create story record
                        story_create = StoryCreate(
                            client_id=client_id,
                            project_id=project_id,
                            story_type="customer_win",  # Default type for mined stories
                            title=story_data.get("story_title"),
                            summary=story_data.get("one_sentence_summary"),
                            full_story=full_story,
                            key_metrics=key_metrics,
                            emotional_hook=emotional_hook,
                            source="story_mining_tool",
                        )

                        # Save to database
                        db_story = story_service.create_story(db, story_create, project.user_id)

                        # Classify story for content template eligibility
                        try:
                            import types as _types
                            from src.research.story_mining import StoryMiner

                            _story_ns = _types.SimpleNamespace(
                                one_sentence_summary=story_data.get("one_sentence_summary", "")
                                or story_data.get("story_title", ""),
                                customer_background=_types.SimpleNamespace(
                                    starting_situation=(
                                        story_data.get("customer_background") or {}
                                    ).get("starting_situation", "")
                                ),
                                challenge=_types.SimpleNamespace(
                                    problem_description=(story_data.get("challenge") or {}).get(
                                        "problem_description", ""
                                    )
                                ),
                                results=_types.SimpleNamespace(
                                    quantitative_results=(story_data.get("results") or {}).get(
                                        "quantitative_results", []
                                    )
                                ),
                            )
                            _miner = StoryMiner(project_id=project_id or "service-classification")
                            eligible_templates = _miner._classify_story_templates(_story_ns)
                            if eligible_templates:
                                db_story.eligible_templates = eligible_templates
                                db.commit()
                                db.refresh(db_story)
                                logger.info(
                                    f"Classified story {db_story.id} templates: {eligible_templates}"
                                )
                        except Exception as _ce:
                            logger.warning(
                                f"Story template classification failed (non-critical): {_ce}"
                            )

                        logger.info(
                            f"Saved mined story to database: {db_story.id} "
                            f"(title: {db_story.title})"
                        )

                except Exception as e:
                    # Don't fail the entire research execution if story saving fails
                    logger.error(
                        f"Failed to save story mining result to database: {str(e)}",
                        exc_info=True,
                    )

            # Platform Strategy Integration: Save recommended platforms to client
            if tool_name == "platform_strategy" and result.success:
                try:
                    # Extract recommended platforms from research result
                    platform_data = result.metadata.get("data", {})
                    recommended_platforms = platform_data.get("recommended_platforms")

                    if recommended_platforms:
                        # Save to client record for persistence across sessions
                        crud.update_client_recommended_platforms(
                            db=db,
                            client_id=client_id,
                            recommended_platforms=recommended_platforms,
                        )
                        logger.info(
                            f"Saved recommended platforms for client {client_id}: {recommended_platforms}"
                        )
                except Exception as e:
                    # Don't fail the entire research execution if platform saving fails
                    logger.error(
                        f"Failed to save platform strategy recommendations to database: {str(e)}",
                        exc_info=True,
                    )

            # Invalidate research context cache (Phase 4: Cache invalidation)
            try:
                invalidate_cache(client_id)
                logger.info(f"Invalidated research context cache for client {client_id}")
            except Exception as e:
                logger.warning(f"Could not invalidate research context cache: {e}")

            # Convert result to backend format with database ID
            return {
                "success": result.success,
                "outputs": {k: str(v) for k, v in result.outputs.items()},
                "metadata": {
                    **result.metadata,
                    "executed_at": result.executed_at.isoformat(),
                    "tool_name": result.tool_name,
                    "result_id": research_result.id,  # Add database ID for cache storage
                },
                "error": result.error,
            }

        except Exception as e:
            logger.error(f"Research tool execution failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "outputs": {},
                "metadata": {
                    "tool_name": tool_name,
                    "project_id": project_id,
                },
                "error": str(e),
            }

    async def execute_research_tools_batch(
        self,
        db: Session,
        project_id: str,
        client_id: str,
        tool_configs: list[dict],
    ) -> dict:
        """
        Execute multiple research tools in correct dependency order.

        Args:
            db: Database session
            project_id: Project ID
            client_id: Client ID
            tool_configs: List of dicts with 'tool_name' and optional 'params'

        Returns:
            Dict with:
                - execution_order: List of tool names in execution order
                - results: Dict mapping tool_name -> execution result
                - summary: Summary of successes/failures
        """
        # Extract tool names
        tool_names = [config["tool_name"] for config in tool_configs]

        # Determine execution order based on dependencies.
        # Raises ValueError on circular dependencies — let it propagate so the
        # batch endpoint returns a 422 rather than silently running tools out of order.
        ordered_tools = self.prerequisites.get_execution_order(tool_names)

        logger.info(f"Batch execution order for {len(tool_names)} tools: {ordered_tools}")

        # Execute tools in order
        results = {}
        successes = 0
        failures = 0
        blocked = 0

        # Track which tools have completed in this batch
        completed_in_batch = set()

        for tool_name in ordered_tools:
            # Find config for this tool
            config = next((c for c in tool_configs if c["tool_name"] == tool_name), {})
            params = config.get("params", {})

            logger.info(
                f"Executing {tool_name} ({ordered_tools.index(tool_name) + 1}/{len(ordered_tools)})"
            )

            # Check prerequisites — combine client-wide history with tools already
            # completed in this batch so cross-project and within-batch deps both resolve
            completed_for_client = self._get_completed_tools_for_client(db, client_id)
            completed_for_client.update(completed_in_batch)
            can_run, missing_required, missing_recommended = (
                self.prerequisites.check_prerequisites_met(tool_name, completed_for_client)
            )

            if not can_run:
                # Tool is blocked - missing required prerequisites
                error_msg = self.prerequisites.get_missing_prerequisites_message(
                    tool_name, missing_required, missing_recommended
                )
                logger.warning(f"Skipping {tool_name} - prerequisites not met: {missing_required}")
                results[tool_name] = {
                    "success": False,
                    "blocked": True,
                    "missing_required": missing_required,
                    "error": error_msg,
                }
                blocked += 1
                continue

            # Execute tool
            try:
                result = await self.execute_research_tool(
                    db, project_id, client_id, tool_name, params
                )
                results[tool_name] = result

                if result.get("success"):
                    successes += 1
                    completed_in_batch.add(tool_name)
                else:
                    failures += 1

            except Exception as e:
                logger.error(f"Error executing {tool_name}: {e}")
                results[tool_name] = {
                    "success": False,
                    "error": str(e),
                }
                failures += 1

        return {
            "execution_order": ordered_tools,
            "results": results,
            "summary": {
                "total": len(ordered_tools),
                "successes": successes,
                "failures": failures,
                "blocked": blocked,
            },
        }

    def _get_demo_response(
        self,
        tool_name: str,
        project_id: str,
        client: Client,
    ) -> Dict:
        """
        Generate realistic demo response for research tools when actual tools unavailable.
        This allows the UI to demonstrate the feature during demos.
        """
        from datetime import datetime

        client_name = client.name if client else "Demo Client"
        base_response = {
            "success": True,
            "metadata": {
                "status": "completed",
                "duration_seconds": 2.5,
                "tool_name": tool_name,
                "project_id": project_id,
                "executed_at": datetime.utcnow().isoformat(),
                "note": "Demo data - full analysis requires API key configuration",
            },
            "error": None,
        }

        # Tool-specific demo data
        demo_data = {
            "voice_analysis": {
                "summary": f"Voice analysis for {client_name}",
                "tone": "Professional and approachable",
                "readability_score": 72.5,
                "reading_level": "8th grade",
                "voice_dimensions": {
                    "formality": 0.7,
                    "enthusiasm": 0.6,
                    "technical_depth": 0.5,
                    "warmth": 0.65,
                },
                "recommendations": [
                    "Maintain conversational tone while keeping authority",
                    "Use more storytelling elements",
                    "Add concrete examples to abstract concepts",
                ],
            },
            "brand_archetype": {
                "summary": f"Brand archetype analysis for {client_name}",
                "primary_archetype": "Expert/Sage",
                "secondary_archetype": "Guide/Mentor",
                "archetype_traits": [
                    "Knowledge-focused",
                    "Trustworthy advisor",
                    "Clear communicator",
                ],
                "content_themes": [
                    "Industry insights and trends",
                    "How-to guides and tutorials",
                    "Thought leadership pieces",
                ],
                "voice_guidelines": {
                    "do": ["Share expertise generously", "Use data to support claims"],
                    "avoid": ["Being condescending", "Oversimplifying complex topics"],
                },
            },
            "competitive_analysis": {
                "summary": f"Competitive landscape for {client_name}",
                "competitors_analyzed": 3,
                "market_position": "Challenger with differentiation opportunity",
                "content_gaps": [
                    "Video content underutilized by competitors",
                    "LinkedIn presence stronger than competitors",
                    "Educational content opportunity",
                ],
                "differentiation_opportunities": [
                    "More personal storytelling",
                    "Behind-the-scenes content",
                    "Customer success stories",
                ],
            },
            "market_trends_research": {
                "summary": f"Market trends for {client_name}'s industry",
                "trending_topics": [
                    "AI integration in workflows",
                    "Remote work optimization",
                    "Sustainability practices",
                ],
                "content_opportunities": [
                    "Thought leadership on industry changes",
                    "Practical implementation guides",
                    "Case studies and results",
                ],
                "recommended_hashtags": ["#Innovation", "#FutureOfWork", "#Leadership"],
            },
            "seo_keyword_research": {
                "summary": f"SEO keyword analysis for {client_name}",
                "primary_keywords": [
                    {
                        "keyword": "business solutions",
                        "volume": 12000,
                        "difficulty": 65,
                    },
                    {
                        "keyword": "workflow automation",
                        "volume": 8500,
                        "difficulty": 55,
                    },
                ],
                "long_tail_opportunities": [
                    "how to improve team productivity",
                    "best practices for remote teams",
                ],
                "content_recommendations": [
                    "Create pillar content around primary keywords",
                    "Build topic clusters with long-tail content",
                ],
            },
        }

        # Get tool-specific data or generic response
        tool_data = demo_data.get(
            tool_name,
            {
                "summary": f"Analysis completed for {client_name}",
                "status": "Demo data generated",
                "recommendations": ["Full analysis available with API configuration"],
            },
        )

        base_response["data"] = tool_data
        base_response["outputs"] = {}  # No file outputs for demo mode

        return base_response

    def _prepare_inputs(
        self,
        project: Project,
        client: Client,
        tool_name: str,
        params: Dict,
        cached_client_name: Optional[str] = None,
        cached_client_business_description: Optional[str] = None,
        cached_client_ideal_customer: Optional[str] = None,
        cached_project_platforms: Optional[list] = None,
    ) -> Dict:
        """
        Prepare inputs for research tool execution.

        Note: Frontend now pre-populates most fields. This method serves as
        fallback for missing data or direct API calls.

        Args:
            project: Project model
            client: Client model
            tool_name: Name of research tool
            params: Additional parameters

        Returns:
            Dict of inputs for the research tool
        """
        # Track which fields came from frontend
        frontend_provided = set(params.keys())

        # Base inputs common to all tools
        # Use cached values if available to prevent detachment errors, fallback to object attributes
        inputs = {
            "company_name": cached_client_name or client.name,
            "business_name": cached_client_name
            or client.name,  # Propagate to all tools (prevents "Client Business" placeholder)
            "business_description": cached_client_business_description
            or client.business_description
            or "",
            "target_audience": cached_client_ideal_customer or client.ideal_customer or "",
            "platforms": cached_project_platforms or project.platforms or ["LinkedIn"],
            **params,  # Merge in additional parameters (explicit params take precedence)
        }

        # Tool-specific input preparation
        if tool_name == "voice_analysis":
            # Voice analysis needs sample content
            content_samples = params.get("content_samples")
            if not content_samples:
                # Auto-generate from business description
                business_desc = client.business_description or ""
                if len(business_desc) >= 50:
                    # Split into 5 samples of roughly equal length
                    words = business_desc.split()
                    chunk_size = max(len(words) // 5, 10)
                    content_samples = [
                        " ".join(words[i : i + chunk_size])
                        for i in range(0, len(words), chunk_size)
                    ][:5]
                else:
                    # Use placeholder samples
                    content_samples = [
                        f"{client.name} provides {business_desc or 'professional services'}",
                        f"Our target audience is {client.ideal_customer or 'business professionals'}",
                        f"We specialize in {client.industry or 'delivering value'}",
                        f"Our unique approach helps clients {client.main_problem_solved or 'achieve their goals'}",
                        f"We work with {client.ideal_customer or 'forward-thinking organizations'}",
                    ]
                logger.info(
                    f"Auto-generated {len(content_samples)} content samples from business profile"
                )
            inputs["content_samples"] = content_samples

        elif tool_name == "brand_archetype":
            # Brand archetype needs tone and values
            inputs["tone_preference"] = project.tone or "professional"
            inputs["brand_values"] = params.get("brand_values", [])

        elif tool_name == "seo_keyword_research":  # Fixed: was "seo_keyword"
            # SEO keyword research needs industry/niche
            inputs["industry"] = params.get("industry") or client.industry or "General business"
            inputs["target_keywords"] = params.get("target_keywords", [])
            inputs["main_topics"] = params.get("main_topics", [])  # Required by tool

        elif tool_name == "competitive_analysis":
            # Competitive analysis needs competitor list and industry
            inputs["competitors"] = params.get("competitors") or client.competitors or []
            inputs["industry"] = params.get("industry") or client.industry or "Not specified"

        elif tool_name == "content_gap_analysis":
            # Content gap needs current topics - will auto-populate after prerequisite merge if empty
            inputs["current_content_topics"] = params.get("current_content_topics", "")
            # Inject competitors and industry from client so web search fires correctly
            inputs["competitors"] = params.get("competitors") or client.competitors or []
            inputs["industry"] = params.get("industry") or client.industry or "Not specified"

        elif tool_name == "market_trends":
            # Market trends needs industry context
            inputs["industry"] = params.get("industry") or client.industry or "General business"

        elif tool_name == "audience_research":
            # Audience research needs business name, industry, and optional location for Census lookup
            inputs["business_name"] = (
                params.get("business_name") or client.name or "Client Business"
            )
            inputs["industry"] = params.get("industry") or client.industry or "General"
            if not inputs.get("location"):
                inputs["location"] = client.location or ""

        elif tool_name == "platform_strategy":
            # Platform strategy needs current platforms - fallback to client.platforms
            # BUG FIX #38: Add data injection and type normalization
            current_platforms = params.get("current_platforms")

            # Type normalization: handle string, None, or list
            if isinstance(current_platforms, str):
                # Convert comma-separated string to list
                current_platforms = [p.strip() for p in current_platforms.split(",") if p.strip()]
            elif current_platforms is None or current_platforms == "":
                # Fallback to client platforms
                current_platforms = client.platforms or []

            inputs["current_platforms"] = current_platforms if current_platforms else []
            inputs["content_goals"] = params.get("content_goals", "")

        elif tool_name == "content_audit":
            # Content audit needs content inventory
            content_inventory = params.get("content_inventory")
            if not content_inventory:
                # Auto-generate placeholder content piece
                from backend.schemas.research_schemas import ContentPiece

                placeholder = ContentPiece(
                    title=f"{client.name} - Content Portfolio",
                    url=None,
                    type="portfolio",
                    publish_date=None,
                    performance_metrics="Placeholder for client content analysis",
                )
                content_inventory = [placeholder.model_dump()]
                logger.info("Auto-generated placeholder content inventory")
            # Convert ContentPiece objects to dicts if needed
            inputs["content_inventory"] = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in content_inventory
            ]

        elif tool_name == "business_report":
            # Business report needs company name and location
            company_name = params.get("company_name")
            if not company_name:
                company_name = client.name or "Client Business"
                logger.info(f"Auto-populated company_name from client: {company_name}")
            inputs["company_name"] = company_name

            location = params.get("location")
            if not location:
                location = client.location or "United States"
                logger.info(f"Auto-populated location from client: {location}")
            inputs["location"] = location

        elif tool_name in ("content_calendar", "content_calendar_strategy"):
            # Content calendar strategy needs primary platforms
            primary_platforms = params.get("primary_platforms")
            if not primary_platforms and client.recommended_platforms:
                # Fallback to recommended platforms from platform strategy
                primary_platforms = client.recommended_platforms
                logger.info(
                    f"Auto-populated primary_platforms from client.recommended_platforms: {primary_platforms}"
                )
            inputs["primary_platforms"] = primary_platforms or []
            # Keep the client record authoritative for naming so the calendar
            # cannot inherit a stale or user-supplied competitor name.
            inputs["business_name"] = client.name or "Client Business"
            inputs["company_name"] = client.name or "Client Business"

        # Log data sources for transparency
        backend_injected = set(inputs.keys()) - frontend_provided
        if backend_injected:
            logger.info(f"{tool_name}: Backend injected fields: {backend_injected}")
        if frontend_provided:
            logger.info(f"{tool_name}: Frontend provided fields: {frontend_provided}")

        return inputs


# Global instance
research_service = ResearchService()
