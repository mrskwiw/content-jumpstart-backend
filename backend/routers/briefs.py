"""Briefs router"""

import sys
import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from backend.middleware.auth_dependency import get_current_user
from backend.schemas.brief import BriefCreate, BriefResponse
from backend.services import crud
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import User
from backend.models.brief_import import FieldExtraction, ParsedBriefResponse
from backend.utils.logger import logger
from backend.utils.http_rate_limiter import standard_limiter, lenient_limiter
from src.validators.prompt_injection_defense import sanitize_prompt_input

router = APIRouter()


@router.post("/create", response_model=BriefResponse, status_code=status.HTTP_201_CREATED)
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def create_brief_from_text(
    request: Request,
    brief: BriefCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create brief from pasted text.

    Rate limit: 100/hour per IP+user (standard operation)
    """
    # Verify project exists
    project = crud.get_project(db, brief.project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Check if brief already exists for this project
    existing_brief = crud.get_brief_by_project(db, brief.project_id)
    if existing_brief:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Brief already exists for this project"
        )

    # SECURITY (TR-020): Sanitize brief content before saving (will be passed to LLM later)
    try:
        sanitized_content = sanitize_prompt_input(brief.content, strict=False)
        logger.info(f"Sanitized brief content for project {brief.project_id}")
    except ValueError as e:
        logger.warning(f"Prompt injection detected in brief content: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brief content contains potentially unsafe patterns. Please review and resubmit.",
        )

    # Save brief to file (use sanitized content)
    briefs_dir = Path(settings.BRIEFS_DIR)
    briefs_dir.mkdir(parents=True, exist_ok=True)
    file_path = briefs_dir / f"{brief.project_id}.txt"
    file_path.write_text(sanitized_content, encoding="utf-8")

    # Create brief with sanitized content
    sanitized_brief = BriefCreate(project_id=brief.project_id, content=sanitized_content)
    return crud.create_brief(db, sanitized_brief, source="paste", file_path=str(file_path))


@router.post("/upload", response_model=BriefResponse, status_code=status.HTTP_201_CREATED)
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def upload_brief_file(
    request: Request,
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload brief file.

    Rate limit: 100/hour per IP+user (standard operation)
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {settings.ALLOWED_BRIEF_EXTENSIONS}",
        )

    # Read file content
    content = await file.read()
    text_content = content.decode("utf-8")

    # SECURITY (TR-020): Sanitize uploaded brief content before saving
    try:
        sanitized_content = sanitize_prompt_input(text_content, strict=False)
        logger.info(f"Sanitized uploaded brief for project {project_id}")
    except ValueError as e:
        logger.warning(f"Prompt injection detected in uploaded brief: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file contains potentially unsafe patterns. Please review and resubmit.",
        )

    # Save file (use sanitized content)
    briefs_dir = Path(settings.BRIEFS_DIR)
    briefs_dir.mkdir(parents=True, exist_ok=True)
    file_path = briefs_dir / f"{project_id}{file_ext}"
    file_path.write_text(sanitized_content, encoding="utf-8")

    # Create brief record (use sanitized content)
    brief_data = BriefCreate(project_id=project_id, content=sanitized_content)
    return crud.create_brief(db, brief_data, source="upload", file_path=str(file_path))


@router.get("/{brief_id}", response_model=BriefResponse)
@lenient_limiter.limit("1000/hour")  # TR-004: Cheap read operation
async def get_brief(
    request: Request,
    brief_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get brief by ID.

    Rate limit: 1000/hour (cheap read operation)
    """
    brief = crud.get_brief(db, brief_id)
    if not brief:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")
    return brief


@router.post("/parse", response_model=ParsedBriefResponse)
@standard_limiter.limit("100/hour")  # TR-004: AI parsing operation (moderate cost)
async def parse_brief_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Parse uploaded brief file and extract client data with confidence scores.

    Rate limit: 100/hour per IP+user (AI parsing operation)
    """
    start_time = time.time()

    # Validate file extension (.txt, .md only)
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".txt", ".md"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": "Only .txt and .md files are supported",
                "details": {"filename": file.filename, "extension": file_ext},
            },
        )

    # Validate file size (< 50KB)
    content = await file.read()
    file_size = len(content)
    max_size = 51200  # 50KB

    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": "File must be less than 50KB",
                "details": {
                    "filename": file.filename,
                    "sizeBytes": file_size,
                    "maxSizeBytes": max_size,
                },
            },
        )

    # Decode UTF-8
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "ENCODING_ERROR",
                "message": "File must be UTF-8 encoded",
                "details": {"filename": file.filename, "error": str(e)},
            },
        )

    # SECURITY (TR-020): Sanitize brief content before parsing with LLM
    try:
        sanitized_content = sanitize_prompt_input(text_content, strict=False)
        logger.info(f"Sanitized brief content for parsing: {file.filename}")
    except ValueError as e:
        logger.warning(f"Prompt injection detected in brief file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "SECURITY_VALIDATION_FAILED",
                "message": "File contains potentially unsafe content patterns",
                "details": {"filename": file.filename, "error": str(e)},
            },
        )

    # Parse with BriefParserAgent (use sanitized content)
    try:
        # Import here to avoid circular dependency
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.agents.brief_parser import BriefParserAgent

        parser = BriefParserAgent()
        parsed_brief = parser.parse_brief(sanitized_content)  # Use sanitized content

        # Convert ClientBrief to field extractions with confidence scoring
        fields_with_confidence = _add_confidence_scores(parsed_brief, text_content)

        # Generate warnings for missing/low-confidence fields
        warnings = _generate_warnings(fields_with_confidence)

        # Calculate metadata
        parse_time_ms = int((time.time() - start_time) * 1000)
        fields_extracted = sum(
            1 for field in fields_with_confidence.values() if field["confidence"] != "low"
        )
        fields_total = len(fields_with_confidence)

        return ParsedBriefResponse(
            success=True,
            fields=fields_with_confidence,
            warnings=warnings,
            metadata={
                "filename": file.filename,
                "parseTimeMs": parse_time_ms,
                "fieldsExtracted": fields_extracted,
                "fieldsTotal": fields_total,
            },
        )

    except Exception as e:
        logger.error(f"Brief parsing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "PARSE_FAILED",
                "message": "Failed to parse brief file",
                "details": {"filename": file.filename, "error": str(e)},
            },
        )


def _add_confidence_scores(parsed_brief, original_text: str) -> dict:
    """Add confidence scores to extracted fields based on content quality"""
    fields = {}

    # Map ClientBrief fields to extraction results
    field_mapping = {
        "companyName": parsed_brief.company_name,
        "businessDescription": parsed_brief.business_description,
        "idealCustomer": parsed_brief.ideal_customer,
        "mainProblemSolved": parsed_brief.main_problem_solved,
        "tonePreference": parsed_brief.tone_preference,
        "platforms": parsed_brief.platforms,
        "customerPainPoints": parsed_brief.customer_pain_points,
        "customerQuestions": parsed_brief.customer_questions,
    }

    for field_name, field_value in field_mapping.items():
        # Determine confidence based on field completeness
        if field_value is None or field_value == "" or field_value == []:
            confidence = "low"
            value = None
        elif isinstance(field_value, str):
            # String fields: high if >10 chars, medium if 3-10, low otherwise
            if len(field_value) > 10:
                confidence = "high"
            elif len(field_value) >= 3:
                confidence = "medium"
            else:
                confidence = "low"
            value = field_value if field_value else None
        elif isinstance(field_value, list):
            # List fields: high if 2+ items, medium if 1 item, low if empty
            if len(field_value) >= 2:
                confidence = "high"
            elif len(field_value) == 1:
                confidence = "medium"
            else:
                confidence = "low"
            value = field_value if field_value else None
        else:
            # Other types (enums, etc.)
            confidence = "high" if field_value else "low"
            value = field_value

        # Try to find source line number (approximate)
        source = None
        if value and isinstance(value, str):
            lines = original_text.split("\n")
            for i, line in enumerate(lines, 1):
                if value[:20] in line:  # Match first 20 chars
                    source = f"line {i}"
                    break

        fields[field_name] = FieldExtraction(value=value, confidence=confidence, source=source)

    return fields


def _generate_warnings(fields: dict) -> list:
    """Generate warnings for missing or low-confidence fields"""
    warnings = []

    # Required fields that should have high confidence
    required_fields = ["companyName", "businessDescription", "idealCustomer"]

    for field_name in required_fields:
        field = fields.get(field_name)
        if not field or field["confidence"] == "low":
            warnings.append(f"{field_name} not found or low confidence - may need manual entry")

    # Optional fields with defaults
    if fields.get("tonePreference", {}).get("confidence") == "low":
        warnings.append("tonePreference not found, defaulting to 'professional'")

    if fields.get("platforms", {}).get("confidence") == "low":
        warnings.append("No platforms specified - will need to select manually")

    return warnings
