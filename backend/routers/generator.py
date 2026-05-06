"""
Generator API endpoints.

Handles content generation, regeneration, and export operations.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from backend.database import get_db, SessionLocal
from backend.middleware.auth_dependency import get_current_user
from backend.models import User
from backend.models.project import Project
from backend.models.research_result import ResearchResult
from backend.schemas.run import RunResponse, LogEntry
from backend.schemas.deliverable import DeliverableResponse
from backend.services import crud
from backend.services.generator_service import generator_service
from backend.utils.logger import logger
from backend.utils.http_rate_limiter import strict_limiter, standard_limiter
from src.validators.prompt_injection_defense import sanitize_prompt_input
from src.utils.template_parser import template_parser
from backend.services import credit_service
from backend.services.credit_service import InsufficientCreditsError
from backend.pricing.credit_pricing import get_content_cost
from backend.services.template_prerequisites import (
    check_template_prerequisites,
    TEMPLATE_IDS,
)

router = APIRouter()


class GenerateAllInput(BaseModel):
    """Input for generate-all endpoint"""

    project_id: str
    client_id: str
    is_batch: bool = True
    num_posts: Optional[int] = (
        None  # Number of posts to generate (defaults to project setting or 30)
    )
    template_quantities: Optional[dict[str, int]] = (
        None  # Optional template quantities from frontend
    )
    custom_topics: Optional[list[str]] = None  # NEW: topic override for content generation
    target_platform: Optional[str] = (
        None  # Bug #106: was "blog" (truthy), blocked project.target_platform fallback
    )

    @field_validator("num_posts")
    @classmethod
    def validate_num_posts(cls, v):
        """Validate num_posts is positive if provided"""
        if v is not None and v <= 0:
            raise ValueError("num_posts must be greater than 0")
        return v


class ValidateTemplatesInput(BaseModel):
    """Input for template validation endpoint"""

    client_id: str
    project_id: Optional[str] = None  # For querying completed research tools
    template_quantities: dict[str, int]  # Template ID -> quantity mapping


class RegenerateInput(BaseModel):
    """Input for regenerate endpoint"""

    project_id: str
    post_ids: list[str]


class ExportInput(BaseModel):
    """Input for export endpoint"""

    project_id: str
    format: str = "txt"  # txt, md, docx
    include_audit_log: bool = False
    include_research: bool = False  # NEW: Include research results appendix


async def run_generation_background(
    run_id: str,
    project_id: str,
    client_id: str,
    user_id: str,  # NEW: for credit refund on failure
    num_posts: int = 30,
    template_quantities: Optional[dict[str, int]] = None,
    custom_topics: Optional[list[str]] = None,  # NEW: topic override for generation
    target_platform: Optional[
        str
    ] = "linkedin",  # Target platform; defaults to linkedin if not resolved
):
    """
    Background task to run content generation.

    This prevents HTTP timeouts by running generation asynchronously.
    Updates the Run record with progress and results.
    """
    # Create new DB session for background task
    db = SessionLocal()

    try:
        logger.info(f"Background generation started for run {run_id}")
        if template_quantities:
            logger.info(f"Using template quantities from request: {template_quantities}")

        # SECURITY (TR-020): Sanitize custom_topics before passing to LLM
        sanitized_topics = None
        if custom_topics:
            try:
                sanitized_topics = [
                    sanitize_prompt_input(topic, strict=False) for topic in custom_topics
                ]
                logger.info(f"Sanitized {len(custom_topics)} custom topics for generation")
            except ValueError as e:
                logger.error(f"Prompt injection detected in custom_topics: {e}")
                # Update run to failed status
                crud.update_run(
                    db,
                    run_id,
                    status="failed",
                    error_message=f"Security validation failed: {str(e)}",
                )
                return

        # Execute content generation via service
        result = await generator_service.generate_all_posts(
            db=db,
            project_id=project_id,
            client_id=client_id,
            num_posts=num_posts,
            template_quantities=template_quantities,
            custom_topics=sanitized_topics,  # Use sanitized topics
            platform=target_platform,  # NEW: Pass target platform for platform-specific generation
            run_id=run_id,  # Pass run_id so posts can reference the run
        )

        # Update run status to succeeded (use LogEntry format)
        from datetime import datetime
        from backend.schemas.run import LogEntry
        from src.utils.cost_tracker import get_default_tracker

        posts_created = result["posts_created"]
        posts_failed = result.get("posts_failed", 0)
        placeholder_count = result.get("placeholder_count", 0)
        succeeded_count = posts_created - placeholder_count
        expected_count = sum(template_quantities.values()) if template_quantities else num_posts

        timestamp = datetime.now().isoformat()
        logs = [
            LogEntry(timestamp=timestamp, message="Generation started"),
            LogEntry(timestamp=timestamp, message="CLI execution completed"),
            LogEntry(
                timestamp=timestamp,
                message=f"Created {posts_created} post records",
            ),
            LogEntry(timestamp=timestamp, message=f"Output directory: {result['output_dir']}"),
        ]

        # Bug #110: surface unsupported platform substitution to operator
        platform_warning = result.get("platform_warning")
        if platform_warning:
            logs.append(LogEntry(timestamp=timestamp, message=platform_warning))

        # Surface count shortfall (DB save failures)
        if posts_created < expected_count:
            shortfall = expected_count - posts_created
            warning_msg = (
                f"⚠️ WARNING: {posts_created} of {expected_count} posts were saved. "
                f"{shortfall} posts missing"
                + (f" ({posts_failed} failed to save to DB)." if posts_failed else ".")
            )
            logger.warning(warning_msg)
            logs.append(LogEntry(timestamp=timestamp, message=warning_msg))

        # Surface placeholder posts (generation failures after all QA retries)
        if placeholder_count > 0:
            placeholder_msg = (
                f"⚠️ PARTIAL RESULTS: {succeeded_count} of {posts_created} posts generated "
                f"successfully. {placeholder_count} post(s) failed after all retry attempts "
                f"and were saved as placeholders — they are flagged for review and will not "
                f"appear in exports. Check the Posts tab to regenerate individual posts."
            )
            logger.warning(placeholder_msg)
            logs.append(LogEntry(timestamp=timestamp, message=placeholder_msg))

        # Capture token usage and cost (Task #32)
        try:
            cost_tracker = get_default_tracker()
            project_cost = cost_tracker.get_project_cost(project_id)

            # Add token usage log entry
            logs.append(
                LogEntry(
                    timestamp=timestamp,
                    message=f"Token usage: {project_cost.total_input_tokens:,} input, "
                    f"{project_cost.total_output_tokens:,} output "
                    f"(${project_cost.total_cost:.2f})",
                )
            )

            run_status = "partial" if placeholder_count > 0 else "succeeded"
            # Token fields are already set per-run by sync_run_token_usage inside
            # _generate_with_template_quantities.  get_project_cost returns all-time
            # project totals, not per-run, so we must not overwrite them here.
            crud.update_run(
                db,
                run_id,
                status=run_status,
                logs=[log.model_dump() for log in logs],
            )
        except Exception as cost_err:
            # If cost tracking fails, still update run status (Bug #59 diagnostic)
            logger.error(
                f"Failed to track costs for run {run_id}: {cost_err.__class__.__name__}: {cost_err}",
                exc_info=True,
            )
            logs.append(
                LogEntry(
                    timestamp=timestamp,
                    message=f"WARNING: Cost tracking failed - {str(cost_err)[:100]}",
                )
            )
            run_status = "partial" if placeholder_count > 0 else "succeeded"
            crud.update_run(db, run_id, status=run_status, logs=[log.model_dump() for log in logs])

        logger.info(f"Background generation completed successfully for run {run_id}")

    except Exception as e:
        logger.error(f"Background generation failed for run {run_id}: {str(e)}", exc_info=True)

        # CREDIT REFUND: Refund credits if generation failed
        try:
            credit_service.refund_credits(
                db=db,
                user_id=user_id,
                amount=num_posts * get_content_cost("blog_post"),
                description=f"Refund for failed generation (run {run_id})",
                reference_id=run_id,
                reference_type="run_refund",
            )
            logger.info(
                f"Refunded {num_posts * get_content_cost('blog_post')} credits to user {user_id}"
            )
        except Exception as refund_err:
            logger.error(f"Failed to refund credits for run {run_id}: {refund_err}")

        # Update run status to failed
        crud.update_run(db, run_id, status="failed", error_message=str(e))

    finally:
        db.close()


@router.get("/template-dependencies/{template_number}")
@standard_limiter.limit("100/minute")
async def get_template_dependencies(
    request: Request,
    template_number: int,
    current_user: User = Depends(get_current_user),
):
    """
    Get research dependencies for a specific template.

    Returns the required and recommended research tools for a given template,
    helping users understand what research to run before generating content.

    Args:
        template_number: Template number (1-15)

    Returns:
        Dict with template info and research dependencies:
        {
            "template_number": 1,
            "template_title": "The Problem-Recognition Post",
            "research_dependencies": {
                "required": ["audience_research"],
                "recommended": ["icp_workshop", "seo_keyword_research"]
            }
        }

    Raises:
        HTTPException 404: Template not found
    """
    if not 1 <= template_number <= 15:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_number} not found. Valid range: 1-15",
        )

    try:
        templates = template_parser.parse_all_templates()
        template = templates.get(template_number)

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template {template_number} not found",
            )

        return {
            "template_number": template["number"],
            "template_title": template["title"],
            "research_dependencies": template["research_dependencies"],
        }

    except FileNotFoundError as e:
        logger.error(f"Template library file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Template library file not found",
        )
    except Exception as e:
        logger.error(f"Failed to parse template dependencies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse template dependencies: {str(e)}",
        )


@router.get("/templates")
async def list_templates():
    """
    Get all templates with their research prerequisites.

    Returns list of templates with updated P0/P1/P2 prerequisites from
    template_prerequisites.py configuration (Bug #42 fix).

    Returns:
        List of template objects with:
        - id: Template number (1-15)
        - name: Template name
        - description: Template format/structure
        - bestFor: What the template is best used for
        - difficulty: Difficulty level (fast/medium/slow)
        - required: P0 (Critical) research tools list
        - recommended: P1 (Recommended) research tools list
        - optional: P2 (Optional) research tools list

    Raises:
        HTTPException 404: Template library file not found
        HTTPException 500: Failed to parse templates
    """
    try:
        # Import here to avoid circular dependency
        from src.config.template_prerequisites import get_template_prerequisites

        # Parse all templates from library file
        templates = template_parser.parse_all_templates()

        # Build response with updated prerequisites
        result = []
        for template_id, template_data in sorted(templates.items()):
            # Get updated prerequisites from Bug #42 fix
            prereqs = get_template_prerequisites(template_id)

            result.append(
                {
                    "id": template_id,
                    "name": template_data["title"],
                    "description": template_data.get("format", ""),
                    "bestFor": template_data.get("best_for", ""),
                    "difficulty": _infer_difficulty(template_data),
                    "required": prereqs.get("required", []),  # P0 - Critical
                    "recommended": prereqs.get("recommended", []),  # P1 - Recommended
                    "optional": prereqs.get("optional", []),  # P2 - Optional
                    "requiresWebSearch": prereqs.get("requires_web_search", False),
                }
            )

        return result

    except FileNotFoundError as e:
        logger.error(f"Template library file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template library file not found",
        )
    except Exception as e:
        logger.error(f"Failed to list templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}",
        )


def _infer_difficulty(template_data: dict) -> str:
    """Infer template difficulty from template data.

    Fast: Simple structure, no story required, no complex data
    Medium: Moderate complexity, may require specific data
    Slow: Complex structure, story required, needs significant thought

    Args:
        template_data: Template metadata dict

    Returns:
        Difficulty level: 'fast', 'medium', or 'slow'
    """
    name = template_data.get("title", "").lower()

    # Slow templates (require stories, vulnerability, deep thought)
    if any(word in name for word in ["story", "personal", "vulnerability", "wrong", "changed"]):
        return "slow"

    # Fast templates (simple structure, quick to write)
    if any(word in name for word in ["question", "how-to", "problem", "statistic"]):
        return "fast"

    # Everything else is medium
    return "medium"


def validate_template_prerequisites(
    template_quantities: dict[str, int],
    client_data: dict,
    completed_research_tools: list[str] | None = None,
) -> dict:
    """
    Validate that all templates have required data.

    Args:
        template_quantities: Dict of {template_id: quantity}
        client_data: Client data dict
        completed_research_tools: List of research tool names already run for this project

    Returns:
        dict with:
        - can_generate (bool): Whether generation should proceed
        - blocked_templates (list): Templates that are blocked
        - warnings (list): Warning messages for HIGH risk templates
        - errors (list): Error messages for CRITICAL templates
    """
    if completed_research_tools is None:
        completed_research_tools = []

    blocked_templates = []
    warnings = []
    errors = []

    if not template_quantities:
        return {
            "can_generate": True,
            "blocked_templates": [],
            "warnings": [],
            "errors": [],
        }

    for template_id_str, quantity in template_quantities.items():
        if quantity <= 0:
            continue

        # Convert template ID to template name
        template_id_num = int(template_id_str)
        template_name = TEMPLATE_IDS.get(template_id_num)

        if not template_name:
            logger.warning(f"Unknown template ID: {template_id_str}")
            continue

        # Check prerequisites
        result = check_template_prerequisites(template_name, client_data, completed_research_tools)

        # Handle CRITICAL templates that are blocked
        if result.get("should_block"):
            blocked_templates.append(
                {
                    "template_id": template_id_str,
                    "template_name": template_name,
                    "error_message": result.get("error_message"),
                    "missing_fields": result.get("missing_required_fields", []),
                    "missing_tools": result.get("missing_required_tools", []),
                }
            )
            errors.append(f"Template '{template_name}': {result.get('error_message')}")

        # Handle HIGH risk templates with warnings
        elif result.get("warning_message"):
            warnings.append(
                {
                    "template_id": template_id_str,
                    "template_name": template_name,
                    "warning_message": result.get("warning_message"),
                    "missing_recommended_fields": result.get("missing_recommended_fields", []),
                    "missing_research_tools": result.get("missing_research_tools", []),
                }
            )

    can_generate = len(blocked_templates) == 0

    return {
        "can_generate": can_generate,
        "blocked_templates": blocked_templates,
        "warnings": warnings,
        "errors": errors,
    }


@router.post("/validate-templates")
@standard_limiter.limit("100/hour")  # Lightweight validation endpoint
async def validate_templates(
    request: Request,
    input: ValidateTemplatesInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validate template prerequisites before generation.

    Returns validation results including:
    - Whether generation can proceed
    - Blocked templates (CRITICAL risk missing data)
    - Warnings (HIGH risk templates)
    - Missing fields for each template

    Frontend can use this to show prerequisites UI before generation starts.
    """
    # Verify client exists and user has access
    client = crud.get_client(db, input.client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {input.client_id} not found",
        )

    # TR-021: Verify user owns the client
    if (
        hasattr(client, "user_id")
        and client.user_id != current_user.id
        and not current_user.is_superuser
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't own this client",
        )

    # Convert client to dict for validation
    client_data = {
        "industry": client.industry,
        "business_description": client.business_description,
        "founder_name": getattr(client, "founder_name", None),
        "customer_pain_points": client.customer_pain_points or [],
        "ideal_customer": client.ideal_customer,
        "main_problem_solved": client.main_problem_solved,
        "customer_questions": client.customer_questions or [],
    }

    # Query completed research tools for this client/project
    research_query = db.query(ResearchResult.tool_name).filter(
        ResearchResult.client_id == input.client_id,
        ResearchResult.status == "completed",
        ResearchResult.is_deleted.is_(False),
    )
    if input.project_id:
        research_query = research_query.filter(ResearchResult.project_id == input.project_id)
    completed_research_tools = [row[0] for row in research_query.distinct().all()]

    # Validate templates
    validation = validate_template_prerequisites(
        input.template_quantities, client_data, completed_research_tools
    )

    # Add available story counts for story-based templates (6, 8, 12, 15)
    story_counts: dict = {}
    _STORY_TEMPLATE_MAP = {
        6: "personal_story",
        8: "things_i_got_wrong",
        12: "inside_look",
        15: "milestone",
    }
    try:
        from backend.services.story_service import story_service as _ss

        for _tid, _tname in _STORY_TEMPLATE_MAP.items():
            if str(_tid) in (input.template_quantities or {}):
                _avail = _ss.get_available_stories_for_template(
                    db, input.client_id, _tname, input.project_id or "", limit=10
                )
                story_counts[_tname] = len(_avail)
    except Exception as _sce:
        logger.warning(f"Could not fetch story counts: {_sce}")

    return {
        "can_generate": validation["can_generate"],
        "blocked_templates": validation["blocked_templates"],
        "warnings": validation["warnings"],
        "errors": validation["errors"],
        "story_counts": story_counts,
    }


@router.post("/generate-all", response_model=RunResponse)
@strict_limiter.limit("10/hour")  # TR-004: Expensive AI generation (composite key: IP+user)
async def generate_all(
    request: Request,
    background_tasks: BackgroundTasks,
    input: GenerateAllInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate all posts for a project.

    Authorization: TR-021 - User must own project

    This endpoint:
    1. Creates a Run record with status="pending"
    2. Queues background task to run generation
    3. Returns immediately with run_id
    4. Client polls GET /api/runs/{run_id} for status updates

    Prevents HTTP timeouts by running generation asynchronously.
    """
    # TR-021: Manual authorization check (project_id comes from request body)
    project = crud.get_project(db, input.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {input.project_id} not found",
        )

    # Reattach detached object to session for attribute access
    project = db.merge(project)

    # TR-021: Verify user owns the project
    if project.user_id != current_user.id and not current_user.is_superuser:
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

    # TEMPLATE PREREQUISITES: Validate templates have required data
    if input.template_quantities:
        # Convert client SQLAlchemy model to dict for validation
        client_data = {
            "industry": client.industry,
            "business_description": client.business_description,
            "founder_name": getattr(client, "founder_name", None),
            "customer_pain_points": client.customer_pain_points or [],
            "ideal_customer": client.ideal_customer,
            "main_problem_solved": client.main_problem_solved,
            "customer_questions": client.customer_questions or [],
        }

        # Query completed research tools for this project
        completed_research_tools = [
            row[0]
            for row in db.query(ResearchResult.tool_name)
            .filter(
                ResearchResult.client_id == input.client_id,
                ResearchResult.project_id == input.project_id,
                ResearchResult.status == "completed",
                ResearchResult.is_deleted.is_(False),
            )
            .distinct()
            .all()
        ]

        validation = validate_template_prerequisites(
            input.template_quantities, client_data, completed_research_tools
        )

        # Block generation if CRITICAL templates are missing data
        if not validation["can_generate"]:
            error_details = {
                "message": "Cannot generate: Required data missing for selected templates",
                "blocked_templates": validation["blocked_templates"],
                "errors": validation["errors"],
            }
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error_details,
            )

        # Log warnings for HIGH risk templates (but allow generation)
        if validation["warnings"]:
            logger.warning(
                f"Template warnings for project {input.project_id}: {validation['warnings']}"
            )

    # Create Run record with status="pending"
    db_run = crud.create_run(db, project_id=input.project_id, is_batch=input.is_batch)

    logger.info(f"Created run {db_run.id} for project {input.project_id}")

    # BUG FIX #54: Calculate num_posts from template_quantities if provided, else use defaults
    if input.template_quantities and not input.num_posts:
        num_posts = sum(input.template_quantities.values())
        logger.info(
            f"Calculated num_posts={num_posts} from template_quantities: {input.template_quantities}"
        )
    else:
        num_posts = input.num_posts or project.num_posts or 30

    # Determine target_platform: input > project setting > default 'blog'
    target_platform = input.target_platform or project.target_platform or "blog"

    # CREDIT DEDUCTION: Calculate and deduct credits before generation
    credit_cost = num_posts * get_content_cost("blog_post")
    try:
        credit_service.deduct_credits(
            db=db,
            user_id=current_user.id,
            amount=credit_cost,
            description=f"Post generation: {num_posts} posts",
            reference_id=db_run.id,
            reference_type="run",
        )
        logger.info(
            f"Deducted {credit_cost} credits from user {current_user.id} for {num_posts} posts"
        )
    except InsufficientCreditsError:
        # Delete the run record since we're not proceeding
        crud.delete_run(db, db_run.id)
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Required: {credit_cost} credits for {num_posts} posts. "
            f"Your balance: {current_user.credit_balance} credits. Please purchase more credits.",
        )

    # Queue background task (returns immediately)
    background_tasks.add_task(
        run_generation_background,
        run_id=db_run.id,
        project_id=input.project_id,
        client_id=input.client_id,
        user_id=current_user.id,  # NEW: pass user_id for refund on failure
        num_posts=num_posts,
        template_quantities=input.template_quantities,  # Pass template quantities from frontend
        custom_topics=input.custom_topics,  # NEW: pass topic override for generation
        target_platform=target_platform,  # NEW: pass target platform for platform-specific generation
    )

    # Update run status to running (background task will update to succeeded/failed)
    db_run = crud.update_run(db, db_run.id, status="running")

    logger.info(f"Queued background generation task for run {db_run.id}")

    return db_run


@router.post("/regenerate", response_model=RunResponse)
@strict_limiter.limit("20/hour")  # TR-004: Expensive AI regeneration (composite key: IP+user)
async def regenerate(
    request: Request,
    input: RegenerateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Regenerate specific posts.

    Authorization: TR-021 - User must own project

    Used for quality gate - regenerate flagged posts.
    """
    # Verify project exists — query directly so the session never holds a stale
    # posts collection from the cache.  db.merge(cached_project) would import an
    # old Project.posts list that, combined with cascade="all, delete-orphan",
    # causes SQLAlchemy to DELETE freshly-generated posts on the next commit.
    project = db.query(Project).filter(Project.id == input.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {input.project_id} not found",
        )

    # TR-021: Verify user owns the project
    if project.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't own this project",
        )

    # Create Run record for regeneration
    db_run = crud.create_run(db, project_id=input.project_id, is_batch=False)

    # CREDIT DEDUCTION: Calculate and deduct credits for regeneration
    num_posts_to_regenerate = len(input.post_ids)
    credit_cost = num_posts_to_regenerate * get_content_cost("blog_post")
    try:
        credit_service.deduct_credits(
            db=db,
            user_id=current_user.id,
            amount=credit_cost,
            description=f"Post regeneration: {num_posts_to_regenerate} posts",
            reference_id=db_run.id,
            reference_type="run",
        )
        logger.info(
            f"Deducted {credit_cost} credits from user {current_user.id} "
            f"for regenerating {num_posts_to_regenerate} posts"
        )
    except InsufficientCreditsError:
        # Delete the run record since we're not proceeding
        crud.delete_run(db, db_run.id)
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Required: {credit_cost} credits for {num_posts_to_regenerate} posts. "
            f"Your balance: {current_user.credit_balance} credits. Please purchase more credits.",
        )

    # Update run status to running
    crud.update_run(db, db_run.id, status="running")

    try:
        logger.info(
            f"Starting regeneration for {len(input.post_ids)} posts in project {input.project_id}"
        )

        # Execute regeneration via service
        result = await generator_service.regenerate_posts(
            db=db,
            project_id=input.project_id,
            post_ids=input.post_ids,
        )

        # Update run status to succeeded (use LogEntry format)
        timestamp = datetime.now().isoformat()
        logs = [
            LogEntry(timestamp=timestamp, message="Regeneration started"),
            LogEntry(
                timestamp=timestamp,
                message=f"Regenerated {result.get('posts_regenerated', 0)} posts",
            ),
            LogEntry(
                timestamp=timestamp,
                message=f"Status: {result.get('status', 'completed')}",
            ),
        ]

        # Capture token usage and cost (Task #32)
        from src.utils.cost_tracker import get_default_tracker

        try:
            cost_tracker = get_default_tracker()
            project_cost = cost_tracker.get_project_cost(input.project_id)

            # Add token usage log entry
            logs.append(
                LogEntry(
                    timestamp=timestamp,
                    message=f"Token usage: {project_cost.total_input_tokens:,} input, "
                    f"{project_cost.total_output_tokens:,} output "
                    f"(${project_cost.total_cost:.2f})",
                )
            )

            crud.update_run(
                db,
                db_run.id,
                status="succeeded",
                logs=[log.model_dump() for log in logs],
                total_input_tokens=project_cost.total_input_tokens,
                total_output_tokens=project_cost.total_output_tokens,
                total_cache_creation_tokens=project_cost.total_cache_creation_tokens,
                total_cache_read_tokens=project_cost.total_cache_read_tokens,
                total_cost_usd=project_cost.total_cost,
            )
        except Exception as cost_err:
            # If cost tracking fails, still update run status
            logger.warning(f"Failed to track costs for run {db_run.id}: {cost_err}")
            crud.update_run(
                db,
                db_run.id,
                status="succeeded",
                logs=[log.model_dump() for log in logs],
            )

        db.refresh(db_run)
        logger.info(f"Regeneration completed successfully for run {db_run.id}")
        return db_run

    except Exception as e:
        logger.error(f"Regeneration failed: {str(e)}", exc_info=True)

        # CREDIT REFUND: Refund credits if regeneration failed
        try:
            credit_service.refund_credits(
                db=db,
                user_id=current_user.id,
                amount=credit_cost,
                description=f"Refund for failed regeneration (run {db_run.id})",
                reference_id=db_run.id,
                reference_type="run_refund",
            )
            logger.info(f"Refunded {credit_cost} credits to user {current_user.id}")
        except Exception as refund_err:
            logger.error(f"Failed to refund credits for run {db_run.id}: {refund_err}")

        crud.update_run(db, db_run.id, status="failed", error_message=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Regeneration failed: {str(e)}",
        )


@router.post("/export", response_model=DeliverableResponse)
@standard_limiter.limit("100/hour")  # TR-004: Standard operation (file generation)
async def export_package(
    request: Request,
    input: ExportInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export deliverable package.

    Authorization: TR-021 - User must own project

    Creates a deliverable file (TXT/DOCX) from generated posts.
    Supports format selection and optional audit log inclusion.
    """
    try:
        # Verify project exists
        project = crud.get_project(db, input.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {input.project_id} not found",
            )

        # Reattach detached object to session for attribute access
        project = db.merge(project)

        # TR-021: Verify user owns the project
        if project.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You don't own this project",
            )

        # Use eager-loaded client (already loaded by crud.get_project)
        client = project.client
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client {project.client_id} not found",
            )

        # Get posts for this project, scoped to the latest run to prevent stale
        # posts from previous runs (including test runs with wrong client data)
        # from appearing in the export.
        from backend.models import Post as PostModel, Run as RunModel

        latest_run = (
            db.query(RunModel)
            .filter(RunModel.project_id == input.project_id)
            .order_by(RunModel.started_at.desc())
            .first()
        )

        if latest_run:
            posts = (
                db.query(PostModel)
                .filter(
                    PostModel.project_id == input.project_id,
                    PostModel.run_id == latest_run.id,
                    PostModel.is_placeholder.isnot(True),  # Exclude placeholder posts
                )
                .all()
            )
        else:
            # No run record — fall back to all posts for backward compatibility
            posts = (
                db.query(PostModel)
                .filter(
                    PostModel.project_id == input.project_id,
                    PostModel.is_placeholder.isnot(True),  # Exclude placeholder posts
                )
                .all()
            )

        if not posts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No posts found for this project. Generate content first.",
            )

        logger.info(
            f"Creating deliverable export for project {input.project_id} in format {input.format} "
            f"with {len(posts)} posts from run {latest_run.id if latest_run else 'N/A'} "
            f"(audit_log={input.include_audit_log})"
        )

        from pathlib import Path
        from backend.models import Deliverable
        from backend.services.export_service import generate_export_file
        import uuid
        from datetime import datetime

        # Generate actual file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{project.name}_{timestamp}_deliverable.{input.format}"
        relative_path = f"{project.name}/{filename}"

        # Generate the file using export service
        file_path, file_size = await generate_export_file(
            posts=posts,
            client=client,
            project=project,
            format=input.format,
            relative_path=relative_path,
            include_audit_log=input.include_audit_log,
            include_research=input.include_research,  # NEW
            db=db,
        )

        # Store the ACTUAL file path and format, not the requested ones.
        # export_service may fall back (e.g. python-docx absent → .txt) and return a
        # different path/extension than what was requested.
        base_path = Path("data/outputs")
        actual_path = file_path.relative_to(base_path).as_posix()
        actual_format = file_path.suffix.lstrip(".")  # "docx", "txt", "md", …

        # Create deliverable record
        db_deliverable = Deliverable(
            id=f"del-{uuid.uuid4().hex[:12]}",
            project_id=input.project_id,
            client_id=project.client_id,
            run_id=latest_run.id if latest_run else None,
            format=actual_format,
            path=actual_path,
            status="ready",
            created_at=datetime.utcnow(),
            file_size_bytes=file_size,
        )

        db.add(db_deliverable)
        db.commit()
        db.refresh(db_deliverable)

        logger.info(f"Deliverable created successfully: {db_deliverable.id} at {file_path}")
        return db_deliverable

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )
