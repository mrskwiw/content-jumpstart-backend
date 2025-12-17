"""Brief submission API endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, get_db
from ..models.brief import Brief
from ..models.project import Project
from ..models.user import User
from ..schemas.brief import BriefCreate, BriefResponse, BriefUpdate

router = APIRouter(prefix="/api/briefs", tags=["Briefs"])


@router.post("/", response_model=BriefResponse, status_code=status.HTTP_201_CREATED)
async def create_brief(
    brief_data: BriefCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new brief for a project.

    - **project_id**: The project to attach this brief to
    - **tone_descriptors**: List of tone descriptors (professional, friendly, etc.)
    - **voice_notes**: Additional voice guidance
    - **audience_type**: Target audience type
    - **pain_points**: List of audience pain points
    - **key_topics**: Up to 5 key topics
    - **target_platforms**: List of target platforms
    - **conversion_goal**: Main conversion objective
    - **customer_stories**: Customer success stories
    - **personal_stories**: Personal/founder stories

    Returns created brief details.
    """
    # Verify project exists and user owns it
    project = db.query(Project).filter(Project.project_id == brief_data.project_id).first()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create a brief for this project",
        )

    # Check if brief already exists for this project
    existing_brief = db.query(Brief).filter(Brief.project_id == brief_data.project_id).first()
    if existing_brief:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A brief already exists for this project. Use PATCH to update it.",
        )

    # Helper function to serialize lists to JSON
    def serialize_list(value):
        if value is None:
            return None
        return json.dumps(value)

    # Create new brief
    new_brief = Brief(
        project_id=brief_data.project_id,
        tone_descriptors=serialize_list(brief_data.tone_descriptors),
        voice_notes=brief_data.voice_notes,
        audience_type=brief_data.audience_type,
        audience_title=brief_data.audience_title,
        audience_industry=brief_data.audience_industry,
        pain_points=serialize_list(brief_data.pain_points),
        key_topics=serialize_list(brief_data.key_topics),
        content_examples=brief_data.content_examples,
        target_platforms=serialize_list(brief_data.target_platforms),
        posting_frequency=brief_data.posting_frequency,
        conversion_goal=brief_data.conversion_goal,
        cta_preference=brief_data.cta_preference,
        customer_stories=serialize_list(brief_data.customer_stories),
        personal_stories=serialize_list(brief_data.personal_stories),
    )

    db.add(new_brief)
    db.commit()
    db.refresh(new_brief)

    return BriefResponse.model_validate(new_brief)


@router.get("/project/{project_id}", response_model=BriefResponse)
async def get_brief_by_project(
    project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get brief for a specific project.

    - **project_id**: The project ID to retrieve brief for

    Returns brief details if user owns the project.
    """
    # Verify project exists and user owns it
    project = db.query(Project).filter(Project.project_id == project_id).first()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this project's brief",
        )

    # Get brief
    brief = db.query(Brief).filter(Brief.project_id == project_id).first()

    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No brief found for this project"
        )

    return BriefResponse.model_validate(brief)


@router.get("/{brief_id}", response_model=BriefResponse)
async def get_brief(
    brief_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific brief.

    - **brief_id**: The brief ID to retrieve

    Returns brief details if user owns the associated project.
    """
    # Get brief
    brief = db.query(Brief).filter(Brief.brief_id == brief_id).first()

    if not brief:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")

    # Verify user owns the project
    project = db.query(Project).filter(Project.project_id == brief.project_id).first()
    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this brief",
        )

    return BriefResponse.model_validate(brief)


@router.patch("/{brief_id}", response_model=BriefResponse)
async def update_brief(
    brief_id: str,
    brief_update: BriefUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update brief fields.

    - **brief_id**: The brief ID to update
    - All fields are optional - only provided fields will be updated

    Returns updated brief details.
    """
    # Get brief
    brief = db.query(Brief).filter(Brief.brief_id == brief_id).first()

    if not brief:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")

    # Verify user owns the project
    project = db.query(Project).filter(Project.project_id == brief.project_id).first()
    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this brief",
        )

    # Helper function to serialize lists to JSON
    def serialize_list(value):
        if value is None:
            return None
        return json.dumps(value)

    # Update fields if provided
    update_data = brief_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        # Serialize list fields to JSON
        if field in [
            "tone_descriptors",
            "pain_points",
            "key_topics",
            "target_platforms",
            "customer_stories",
            "personal_stories",
        ]:
            value = serialize_list(value)

        setattr(brief, field, value)

    db.commit()
    db.refresh(brief)

    return BriefResponse.model_validate(brief)


@router.delete("/{brief_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brief(
    brief_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Delete a brief.

    - **brief_id**: The brief ID to delete

    Returns 204 No Content on success.
    """
    # Get brief
    brief = db.query(Brief).filter(Brief.brief_id == brief_id).first()

    if not brief:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")

    # Verify user owns the project
    project = db.query(Project).filter(Project.project_id == brief.project_id).first()
    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this brief",
        )

    db.delete(brief)
    db.commit()

    return None
