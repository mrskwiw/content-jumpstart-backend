"""
Research API endpoints.

Handles research tool listing and execution.
"""
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.models import User
from backend.services import crud
from backend.services.research_service import research_service
from backend.utils.logger import logger

router = APIRouter()


class ResearchTool(BaseModel):
    """Research tool metadata"""
    name: str
    label: str
    price: Optional[float] = None
    status: str = "available"  # available, coming_soon
    description: Optional[str] = None
    category: Optional[str] = None


class RunResearchInput(BaseModel):
    """Input for running research"""
    project_id: str
    client_id: str
    tool: str
    params: Optional[Dict[str, Any]] = {}


class ResearchRunResult(BaseModel):
    """Result from research execution"""
    tool: str
    outputs: Dict[str, str]
    metadata: Optional[Dict[str, Any]] = {}


# Research tool catalog (6 implemented tools)
RESEARCH_TOOLS = [
    # Client Foundation Tools ($700 Total)
    ResearchTool(
        name="voice_analysis",
        label="Voice Analysis",
        price=400.0,
        status="available",
        description="Extract writing patterns from client's existing content",
        category="foundation"
    ),
    ResearchTool(
        name="brand_archetype",
        label="Brand Archetype Assessment",
        price=300.0,
        status="available",
        description="Identify brand personality and messaging framework",
        category="foundation"
    ),

    # SEO & Competition Tools ($1,400 Total)
    ResearchTool(
        name="seo_keyword_research",
        label="SEO Keyword Research",
        price=400.0,
        status="available",
        description="Discover target keywords and search opportunities",
        category="seo"
    ),
    ResearchTool(
        name="competitive_analysis",
        label="Competitive Analysis",
        price=500.0,
        status="available",
        description="Research competitors and identify positioning gaps",
        category="seo"
    ),
    ResearchTool(
        name="content_gap_analysis",
        label="Content Gap Analysis",
        price=500.0,
        status="available",
        description="Identify content opportunities competitors are missing",
        category="seo"
    ),

    # Market Intelligence Tools ($400 Total)
    ResearchTool(
        name="market_trends_research",
        label="Market Trends Research",
        price=400.0,
        status="available",
        description="Discover trending topics and emerging opportunities",
        category="market"
    ),

    # Strategy & Planning Tools
    ResearchTool(
        name="content_audit",
        label="Content Audit",
        price=400.0,
        status="available",
        description="Analyze existing content performance and opportunities",
        category="strategy"
    ),
    ResearchTool(
        name="platform_strategy",
        label="Platform Strategy",
        price=300.0,
        status="available",
        description="Recommend optimal platform mix for distribution",
        category="strategy"
    ),
    ResearchTool(
        name="content_calendar",
        label="Content Calendar Strategy",
        price=300.0,
        status="available",
        description="Create strategic 90-day content calendar",
        category="strategy"
    ),
    ResearchTool(
        name="audience_research",
        label="Audience Research",
        price=500.0,
        status="coming_soon",
        description="Deep-dive into target audience demographics and psychographics",
        category="strategy"
    ),

    # Workshop Assistants
    ResearchTool(
        name="icp_workshop",
        label="ICP Development Workshop",
        price=600.0,
        status="coming_soon",
        description="Facilitate ideal customer profile definition through guided conversation",
        category="workshop"
    ),
    ResearchTool(
        name="story_mining",
        label="Story Mining Interview",
        price=500.0,
        status="coming_soon",
        description="Extract customer success stories and case study material",
        category="workshop"
    ),
]


@router.get("/tools", response_model=List[ResearchTool])
async def list_research_tools(
    current_user: User = Depends(get_current_user),
):
    """
    List all available research tools.

    Returns metadata for all 12 research tools:
    - 7 implemented and available
    - 5 coming soon
    """
    return RESEARCH_TOOLS


@router.post("/run", response_model=ResearchRunResult)
async def run_research(
    input: RunResearchInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Execute a research tool.

    Currently stubbed - will integrate with actual research tools:
    - Voice Analysis
    - Brand Archetype Assessment
    - SEO Keyword Research
    - Competitive Analysis
    - Content Gap Analysis
    - Market Trends Research
    """
    # Verify project exists
    project = crud.get_project(db, input.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {input.project_id} not found"
        )

    # Verify client exists
    client = crud.get_client(db, input.client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {input.client_id} not found"
        )

    # Validate client has sufficient data for research
    # Research tools require minimum business context
    business_desc = client.business_description or ""
    ideal_customer = client.ideal_customer or ""

    # Most research tools require at least 50 characters of business description
    # All tools now use 70 character minimum for consistency with wizard validation
    TOOL_REQUIREMENTS = {
        "brand_archetype": {"business_description": 70},
        "content_audit": {"business_description": 50},
        "content_gap_analysis": {"business_description": 50},
        "platform_strategy": {"business_description": 50, "target_audience": 20},
        "audience_research": {"business_description": 50},
        "competitive_analysis": {"business_description": 50},
        "voice_analysis": {"content_samples": 5},  # Requires 5-30 writing samples
    }

    if input.tool in TOOL_REQUIREMENTS:
        requirements = TOOL_REQUIREMENTS[input.tool]

        # Check business_description
        if "business_description" in requirements:
            min_length = requirements["business_description"]
            if len(business_desc) < min_length:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Client profile incomplete: {input.tool} requires a business description of at least {min_length} characters. Please complete the client profile in the wizard before running research."
                )

        # Check target_audience
        if "target_audience" in requirements:
            min_length = requirements["target_audience"]
            if len(ideal_customer) < min_length:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Client profile incomplete: {input.tool} requires a target audience description of at least {min_length} characters. Please complete the client profile in the wizard before running research."
                )

        # Check content_samples (for voice_analysis)
        if "content_samples" in requirements:
            min_samples = requirements["content_samples"]
            samples = input.params.get("content_samples", [])

            if not isinstance(samples, list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{input.tool} requires content_samples as a list. Please provide {min_samples}-30 writing samples."
                )

            if len(samples) < min_samples:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{input.tool} requires at least {min_samples} content samples. Please provide {min_samples}-30 samples of the client's existing writing (minimum 50 characters each)."
                )

    # Find the tool
    tool = next((t for t in RESEARCH_TOOLS if t.name == input.tool), None)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research tool '{input.tool}' not found"
        )

    # Check if tool is available
    if tool.status == "coming_soon":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Research tool '{input.tool}' is not yet available"
        )

    logger.info(f"Executing research tool '{input.tool}' for project {input.project_id}")

    try:
        # Execute research tool via service
        result = await research_service.execute_research_tool(
            db=db,
            project_id=input.project_id,
            client_id=input.client_id,
            tool_name=input.tool,
            params=input.params or {},
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Research tool execution failed: {result.get('error', 'Unknown error')}"
            )

        # Return result in expected format
        return ResearchRunResult(
            tool=input.tool,
            outputs=result["outputs"],
            metadata={
                **result["metadata"],
                "price": tool.price,
                "project_id": input.project_id,
                "client_id": input.client_id,
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Research execution failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research execution failed: {str(e)}"
        )
