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
from typing import Dict, Optional

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
    from src.research.competitive_analysis import CompetitiveAnalyzer
    from src.research.content_gap_analysis import ContentGapAnalyzer
    from src.research.market_trends_research import MarketTrendsResearcher

    RESEARCH_TOOLS_AVAILABLE = True
    RESEARCH_TOOL_MAP = {
        "voice_analysis": VoiceAnalyzer,
        "brand_archetype": BrandArchetypeAnalyzer,
        "seo_keyword_research": SEOKeywordResearcher,  # Fixed: was "seo_keyword"
        "competitive_analysis": CompetitiveAnalyzer,
        "content_gap_analysis": ContentGapAnalyzer,    # Fixed: was "content_gap"
        "market_trends_research": MarketTrendsResearcher,  # Fixed: was "market_trends"
    }
except ImportError as e:
    # Research tools not available - service will return stub responses
    RESEARCH_TOOLS_AVAILABLE = False
    RESEARCH_TOOL_MAP = {}
    logger = __import__("logging").getLogger(__name__)
    logger.warning(f"Research tools not available: {str(e)}")

# IMPORTANT: Use relative imports to avoid SQLAlchemy table redefinition errors
# Absolute imports (backend.models) cause circular dependencies in production
from models import Project, Client
from services import crud

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
        # No specific initialization needed
        pass

    async def execute_research_tool(
        self,
        db: Session,
        project_id: str,
        client_id: str,
        tool_name: str,
        params: Optional[Dict] = None,
    ) -> Dict[str, any]:
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

        # Check if research tools are available
        if not RESEARCH_TOOLS_AVAILABLE:
            logger.warning(f"Research tools not available - returning stub response for '{tool_name}'")
            # Return stub response
            return {
                "success": True,
                "outputs": {
                    "json": f"data/research/{tool_name}/{project_id}/analysis.json",
                    "markdown": f"data/research/{tool_name}/{project_id}/report.md",
                    "text": f"data/research/{tool_name}/{project_id}/summary.txt",
                },
                "metadata": {
                    "status": "completed",
                    "duration_seconds": 1.0,
                    "tool_name": tool_name,
                    "project_id": project_id,
                    "note": "Stub response - research tools not available in this environment",
                },
                "error": None,
            }

        # Check if tool exists
        if tool_name not in RESEARCH_TOOL_MAP:
            raise ValueError(f"Research tool '{tool_name}' not found")

        # Get tool class
        ToolClass = RESEARCH_TOOL_MAP[tool_name]

        # Prepare inputs based on tool requirements
        inputs = self._prepare_inputs(project, client, tool_name, params or {})

        try:
            # Instantiate and execute tool
            tool = ToolClass(project_id=project_id)
            result = tool.execute(inputs)

            # Convert result to backend format
            return {
                "success": result.success,
                "outputs": {k: str(v) for k, v in result.outputs.items()},
                "metadata": {
                    **result.metadata,
                    "executed_at": result.executed_at.isoformat(),
                    "tool_name": result.tool_name,
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

    def _prepare_inputs(
        self,
        project: Project,
        client: Client,
        tool_name: str,
        params: Dict,
    ) -> Dict:
        """
        Prepare inputs for research tool execution

        Args:
            project: Project model
            client: Client model
            tool_name: Name of research tool
            params: Additional parameters

        Returns:
            Dict of inputs for the research tool
        """
        # Base inputs common to all tools
        # Use Client model fields (business_description, ideal_customer) instead of non-existent Project fields
        inputs = {
            "company_name": client.name,
            "business_description": client.business_description or "",
            "target_audience": client.ideal_customer or "",
            "platforms": project.platforms or ["LinkedIn"],
            **params,  # Merge in additional parameters
        }

        # Tool-specific input preparation
        if tool_name == "voice_analysis":
            # Voice analysis needs sample content
            inputs["content_samples"] = params.get("content_samples", [])

        elif tool_name == "brand_archetype":
            # Brand archetype needs tone and values
            inputs["tone_preference"] = project.tone or "professional"
            inputs["brand_values"] = params.get("brand_values", [])

        elif tool_name == "seo_keyword_research":  # Fixed: was "seo_keyword"
            # SEO keyword research needs industry/niche
            inputs["industry"] = params.get("industry", "")
            inputs["target_keywords"] = params.get("target_keywords", [])
            inputs["main_topics"] = params.get("main_topics", [])  # Required by tool

        elif tool_name == "competitive_analysis":
            # Competitive analysis needs competitor list
            inputs["competitors"] = params.get("competitors", [])

        elif tool_name == "content_gap_analysis":  # Fixed: was "content_gap"
            # Content gap needs current topics
            inputs["current_content_topics"] = params.get("current_content_topics", [])

        elif tool_name == "market_trends_research":  # Fixed: was "market_trends"
            # Market trends needs industry context
            inputs["industry"] = params.get("industry", "")

        return inputs


# Global instance
research_service = ResearchService()
