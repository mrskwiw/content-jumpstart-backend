"""Clients router"""

from typing import List
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from backend.middleware.auth_dependency import get_current_user
from backend.middleware.authorization import (
    verify_client_ownership,
    filter_user_clients,
)  # TR-021: Authorization
from backend.schemas.client import ClientCreate, ClientUpdate, ClientResponse
from backend.services import crud
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Client, User
from backend.utils.http_rate_limiter import standard_limiter

router = APIRouter()


@router.get("/", response_model=List[ClientResponse])
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def list_clients(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all clients.

    Rate limit: 100/hour per IP+user (standard operation)
    Authorization: TR-021 - Users see only their own clients
    """
    # TR-021: Filter to user's clients only
    query = filter_user_clients(db, current_user)
    return query.offset(skip).limit(limit).all()


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def create_client(
    request: Request,
    client: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new client.

    Rate limit: 100/hour per IP+user (standard operation)
    Authorization: TR-021 - Client owned by creating user
    """
    # TR-021: Create client with user_id for ownership
    return crud.create_client(db, client, user_id=current_user.id)


@router.get("/{client_id}", response_model=ClientResponse)
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def get_client(
    request: Request,
    client_id: str,
    client: Client = Depends(verify_client_ownership),  # TR-021: Authorization check
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get client by ID.

    Rate limit: 100/hour per IP+user (standard operation)
    Authorization: TR-021 - User must own client
    """
    # TR-021: client already verified by dependency
    return client


@router.patch("/{client_id}", response_model=ClientResponse)
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def update_client(
    request: Request,
    client_id: str,
    client_update: ClientUpdate,
    client: Client = Depends(verify_client_ownership),  # TR-021: Authorization check
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update client.

    Rate limit: 100/hour per IP+user (standard operation)
    Authorization: TR-021 - User must own client
    """
    # TR-021: client already verified by dependency
    updated_client = crud.update_client(db, client_id, client_update)
    if not updated_client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return updated_client


@router.get("/{client_id}/export-profile")
@standard_limiter.limit("100/hour")  # TR-004: Standard operation
async def export_client_profile(
    request: Request,
    client_id: str,
    client: Client = Depends(verify_client_ownership),  # TR-021: Authorization check
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export client profile as a standalone markdown document.

    Rate limit: 100/hour per IP+user (standard operation)
    Authorization: TR-021 - User must own client

    Returns a downloadable markdown file containing:
    - Company information
    - Business description
    - Ideal customer profile
    - Pain points
    - Customer questions
    - Tone preferences
    - Platform preferences

    This export does NOT include project-specific data.
    """
    # TR-021: client already verified by dependency

    # Create output directory if it doesn't exist
    output_dir = Path("data/outputs/client_profiles")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_client_name = (
        "".join(c for c in client.name if c.isalnum() or c in (" ", "-", "_"))
        .strip()
        .replace(" ", "_")
    )
    filename = f"{safe_client_name}_Profile_{timestamp}.md"
    file_path = output_dir / filename

    # Generate markdown content
    content = f"""# Client Profile: {client.name}

**Export Date:** {datetime.now().strftime("%B %d, %Y at %I:%M %p")}

---

## Company Information

**Company Name:** {client.name}

**Email:** {client.email or 'Not provided'}

**Created:** {client.created_at.strftime("%B %d, %Y") if client.created_at else 'Unknown'}

---

## Business Description

{client.business_description or 'Not provided'}

---

## Ideal Customer Profile

{client.ideal_customer or 'Not provided'}

---

## Main Problem Solved

{client.main_problem_solved or 'Not provided'}

---

## Customer Pain Points

"""

    # Add pain points list
    if client.customer_pain_points and isinstance(client.customer_pain_points, list):
        for i, pain_point in enumerate(client.customer_pain_points, 1):
            content += f"{i}. {pain_point}\n"
    else:
        content += "Not provided\n"

    content += "\n---\n\n## Customer Questions\n\n"

    # Add customer questions
    if client.customer_questions and isinstance(client.customer_questions, list):
        for i, question in enumerate(client.customer_questions, 1):
            content += f"{i}. {question}\n"
    else:
        content += "Not provided\n"

    content += "\n---\n\n## Brand Voice & Preferences\n\n"
    content += f"**Tone Preference:** {client.tone_preference or 'professional'}\n\n"

    # Add platforms
    content += "**Target Platforms:**\n\n"
    if client.platforms and isinstance(client.platforms, list):
        for platform in client.platforms:
            content += f"- {platform}\n"
    else:
        content += "Not specified\n"

    content += "\n---\n\n"
    content += "*This client profile was generated by the 30-Day Content Jumpstart system.*\n"
    content += "*For project-specific deliverables, see individual project exports.*\n"

    # Write content to file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Return file as download
    return FileResponse(
        path=file_path,
        media_type="text/markdown",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
