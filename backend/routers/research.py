"""
Research API endpoints.

Handles research tool listing and execution with comprehensive input validation.
"""

from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.models import User
from backend.schemas import (
    VoiceAnalysisParams,
    SEOKeywordParams,
    CompetitiveAnalysisParams,
    ContentGapParams,
    ContentAuditParams,
    MarketTrendsParams,
    PlatformStrategyParams,
    ContentCalendarParams,
    AudienceResearchParams,
    ICPWorkshopParams,
    StoryMiningParams,
    BrandArchetypeParams,
)
from backend.services import crud
from backend.services.research_service import research_service
from backend.utils.logger import logger
from backend.utils.http_rate_limiter import strict_limiter, lenient_limiter
from backend.middleware.authorization import _check_ownership  # TR-021: IDOR prevention

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
        category="foundation",
    ),
    ResearchTool(
        name="brand_archetype",
        label="Brand Archetype Assessment",
        price=300.0,
        status="available",
        description="Identify brand personality and messaging framework",
        category="foundation",
    ),
    # SEO & Competition Tools ($1,400 Total)
    ResearchTool(
        name="seo_keyword_research",
        label="SEO Keyword Research",
        price=400.0,
        status="available",
        description="Discover target keywords and search opportunities",
        category="seo",
    ),
    ResearchTool(
        name="competitive_analysis",
        label="Competitive Analysis",
        price=500.0,
        status="available",
        description="Research competitors and identify positioning gaps",
        category="seo",
    ),
    ResearchTool(
        name="content_gap_analysis",
        label="Content Gap Analysis",
        price=500.0,
        status="available",
        description="Identify content opportunities competitors are missing",
        category="seo",
    ),
    # Market Intelligence Tools ($400 Total)
    ResearchTool(
        name="market_trends_research",
        label="Market Trends Research",
        price=400.0,
        status="available",
        description="Discover trending topics and emerging opportunities",
        category="market",
    ),
    # Strategy & Planning Tools
    ResearchTool(
        name="content_audit",
        label="Content Audit",
        price=400.0,
        status="available",
        description="Analyze existing content performance and opportunities",
        category="strategy",
    ),
    ResearchTool(
        name="platform_strategy",
        label="Platform Strategy",
        price=300.0,
        status="available",
        description="Recommend optimal platform mix for distribution",
        category="strategy",
    ),
    ResearchTool(
        name="content_calendar",
        label="Content Calendar Strategy",
        price=300.0,
        status="available",
        description="Create strategic 90-day content calendar",
        category="strategy",
    ),
    ResearchTool(
        name="audience_research",
        label="Audience Research",
        price=500.0,
        status="available",
        description="Deep-dive into target audience demographics and psychographics",
        category="strategy",
    ),
    # Workshop Assistants
    ResearchTool(
        name="icp_workshop",
        label="ICP Development Workshop",
        price=600.0,
        status="available",
        description="Facilitate ideal customer profile definition through guided conversation",
        category="workshop",
    ),
    ResearchTool(
        name="story_mining",
        label="Story Mining Interview",
        price=500.0,
        status="available",
        description="Extract customer success stories and case study material",
        category="workshop",
    ),
]


# Validation schema mapping for each research tool
VALIDATION_SCHEMAS = {
    "voice_analysis": VoiceAnalysisParams,
    "seo_keyword_research": SEOKeywordParams,
    "competitive_analysis": CompetitiveAnalysisParams,
    "content_gap_analysis": ContentGapParams,
    "content_audit": ContentAuditParams,
    "market_trends_research": MarketTrendsParams,
    "platform_strategy": PlatformStrategyParams,
    "content_calendar": ContentCalendarParams,
    "audience_research": AudienceResearchParams,
    "icp_workshop": ICPWorkshopParams,
    "story_mining": StoryMiningParams,
    "brand_archetype": BrandArchetypeParams,
}


def validate_research_params(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate research tool parameters using appropriate Pydantic schema.

    Args:
        tool_name: Name of the research tool
        params: Raw parameters dictionary from API request

    Returns:
        Validated parameters dictionary

    Raises:
        HTTPException: If validation fails with detailed error messages
    """
    # Check if tool has a validation schema
    schema = VALIDATION_SCHEMAS.get(tool_name)
    if not schema:
        # No validation schema - allow any params (backward compatibility)
        logger.warning(f"No validation schema found for tool '{tool_name}'")
        return params

    try:
        # Validate params using Pydantic schema
        validated = schema(**params)
        # Convert back to dict for downstream processing
        return validated.model_dump()
    except ValidationError as e:
        # Extract detailed error messages
        error_details = []
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_details.append(f"{field}: {message}")

        error_message = f"Invalid parameters for {tool_name}: " + "; ".join(error_details)

        logger.warning(f"Validation failed for {tool_name}: {error_message}")

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "validation_error",
                "tool": tool_name,
                "message": error_message,
                "details": error_details,
            },
        )


def sanitize_research_params(params: Dict[str, Any], strict: bool = False) -> Dict[str, Any]:
    """
    Sanitize research tool parameters to prevent prompt injection attacks.

    This function recursively sanitizes all string values in the params dictionary,
    protecting against malicious prompts that attempt to override system instructions,
    leak sensitive data, or manipulate LLM behavior.

    Security (TR-020): Prompt Injection Defense
    - Blocks instruction override attempts ("ignore previous instructions...")
    - Prevents role manipulation ("you are now a...")
    - Stops system prompt leakage ("repeat your instructions")
    - Filters data exfiltration attempts ("output all client data")
    - Detects jailbreak attempts ("DAN mode", "developer mode")

    Args:
        params: Validated parameters dictionary
        strict: If True, applies stricter sanitization (blocks medium-risk patterns)

    Returns:
        Sanitized parameters dictionary

    Raises:
        HTTPException: If prompt injection is detected
    """
    from src.validators.prompt_injection_defense import PromptInjectionDetector

    detector = PromptInjectionDetector(strict_mode=strict)
    sanitized = {}

    for key, value in params.items():
        if isinstance(value, str):
            # Check for prompt injection before sanitization
            is_malicious, blocked_patterns, severity = detector.detect_injection(value)

            if is_malicious:
                logger.error(
                    f"Prompt injection detected in '{key}' (severity={severity}): {blocked_patterns[:3]}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Security validation failed: Parameter '{key}' contains suspicious content that may attempt to manipulate the AI system. Please rephrase your input.",
                )

            sanitized[key] = value
        elif isinstance(value, list):
            # Check each list item for prompt injection
            sanitized_list = []
            for i, item in enumerate(value):
                if isinstance(item, str):
                    # Detect prompt injection in list items
                    is_malicious, blocked_patterns, severity = detector.detect_injection(item)

                    if is_malicious:
                        logger.error(
                            f"Prompt injection detected in {key}[{i}] (severity={severity}): {blocked_patterns[:3]}"
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Security validation failed: Parameter '{key}[{i}]' contains suspicious content that may attempt to manipulate the AI system. Please rephrase your input.",
                        )

                    sanitized_list.append(item)
                elif isinstance(item, dict):
                    # Recursive sanitization for nested dicts in lists
                    sanitized_list.append(sanitize_research_params(item, strict=strict))
                else:
                    sanitized_list.append(item)
            sanitized[key] = sanitized_list
        elif isinstance(value, dict):
            # Recursive sanitization for nested dicts
            sanitized[key] = sanitize_research_params(value, strict=strict)
        else:
            # Pass through non-string values (int, float, bool, None)
            sanitized[key] = value

    return sanitized


@router.get("/tools", response_model=List[ResearchTool])
@lenient_limiter.limit("1000/hour")  # TR-004: Cheap read operation
async def list_research_tools(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    List all available research tools.

    Returns metadata for all 12 research tools:
    - 7 implemented and available
    - 5 coming soon

    Rate limit: 1000/hour (cheap read operation)
    """
    return RESEARCH_TOOLS


@router.post("/run", response_model=ResearchRunResult)
@strict_limiter.limit("5/hour")  # TR-004: Expensive operation ($400-600/call), prevent abuse
async def run_research(
    request: Request,
    input: RunResearchInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Execute a research tool.

    Integrates with 13 research tools:
    - Voice Analysis, Brand Archetype Assessment, SEO Keyword Research
    - Competitive Analysis, Content Gap Analysis, Market Trends Research
    - Platform Strategy, Content Calendar, Audience Research
    - ICP Workshop, Story Mining, Content Audit

    Rate limit: 5/hour per IP+user (prevents abuse of expensive AI operations)

    SECURITY (TR-020): Multi-layer prompt injection defense:
    1. Pydantic validation (length limits, type checking, list size limits)
    2. Prompt sanitization (sanitize_research_params) before LLM execution
       - Blocks instruction override ("ignore previous instructions...")
       - Prevents role manipulation ("you are now a...")
       - Stops system prompt leakage ("repeat your instructions")
       - Filters data exfiltration ("output all client data")
       - Detects jailbreak attempts ("DAN mode", "developer mode")
    3. Recursive sanitization of nested dicts and lists

    All string parameters are sanitized before being passed to LLM prompts.
    """
    # Verify project exists
    project = crud.get_project(db, input.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {input.project_id} not found",
        )

    # TR-021: Verify user owns the project (IDOR prevention)
    if not _check_ownership("Project", project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't own this project",
        )

    # Verify client exists
    client = crud.get_client(db, input.client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {input.client_id} not found",
        )

    # TR-021: Verify user owns the client (IDOR prevention)
    if not _check_ownership("Client", client, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't own this client",
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
                    detail=f"Client profile incomplete: {input.tool} requires a business description of at least {min_length} characters. Please complete the client profile in the wizard before running research.",
                )

        # Check target_audience
        if "target_audience" in requirements:
            min_length = requirements["target_audience"]
            if len(ideal_customer) < min_length:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Client profile incomplete: {input.tool} requires a target audience description of at least {min_length} characters. Please complete the client profile in the wizard before running research.",
                )

        # Check content_samples (for voice_analysis)
        if "content_samples" in requirements:
            min_samples = requirements["content_samples"]
            samples = input.params.get("content_samples", [])

            if not isinstance(samples, list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{input.tool} requires content_samples as a list. Please provide {min_samples}-30 writing samples.",
                )

            if len(samples) < min_samples:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{input.tool} requires at least {min_samples} content samples. Please provide {min_samples}-30 samples of the client's existing writing (minimum 50 characters each).",
                )

    # Find the tool
    tool = next((t for t in RESEARCH_TOOLS if t.name == input.tool), None)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research tool '{input.tool}' not found",
        )

    # Check if tool is available
    if tool.status == "coming_soon":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Research tool '{input.tool}' is not yet available",
        )

    # Validate research tool parameters using Pydantic schemas
    # This provides comprehensive input validation with:
    # - Length limits (prevent DoS)
    # - Type checking (prevent type confusion)
    # - List size limits (prevent resource exhaustion)
    # - Whitespace stripping and sanitization
    validated_params = validate_research_params(input.tool, input.params or {})

    # SECURITY (TR-020): Sanitize validated params to prevent prompt injection
    # This protects against malicious prompts attempting to:
    # - Override system instructions
    # - Leak sensitive data or system prompts
    # - Manipulate LLM behavior via jailbreak techniques
    # All string values (including nested dicts and lists) are sanitized
    try:
        sanitized_params = sanitize_research_params(validated_params, strict=False)
        logger.info(
            f"Executing research tool '{input.tool}' for project {input.project_id} "
            f"with validated and sanitized params"
        )
    except HTTPException:
        # Re-raise HTTPExceptions from sanitization (prompt injection detected)
        raise
    except Exception as e:
        # Unexpected error during sanitization
        logger.error(f"Sanitization error for {input.tool}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Security validation failed: {str(e)}",
        )

    try:
        # Execute research tool via service with sanitized params
        result = await research_service.execute_research_tool(
            db=db,
            project_id=input.project_id,
            client_id=input.client_id,
            tool_name=input.tool,
            params=sanitized_params,  # Use sanitized params for LLM safety
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Research tool execution failed: {result.get('error', 'Unknown error')}",
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
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Research execution failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research execution failed: {str(e)}",
        )
