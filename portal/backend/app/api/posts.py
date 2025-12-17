"""Post management API endpoints."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Add project src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.agents.brief_parser import BriefParserAgent
from src.agents.content_generator import ContentGeneratorAgent
from src.models.client_brief import Platform

from ..core.deps import get_current_user, get_db
from ..models.brief import Brief
from ..models.post import Post
from ..models.project import Project
from ..models.user import User
from ..schemas.post import GeneratePostsRequest, PostListResponse, PostResponse, PostUpdate

router = APIRouter(prefix="/api/projects/{project_id}/posts", tags=["Posts"])


@router.get("/", response_model=PostListResponse)
async def list_posts(
    project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get list of posts for a project.

    Returns all generated posts for the project, ordered by post number.
    """
    # Verify user owns this project
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if project.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Get posts ordered by post number
    posts = db.query(Post).filter(Post.project_id == project_id).order_by(Post.post_number).all()

    return PostListResponse(total=len(posts), posts=[PostResponse.model_validate(p) for p in posts])


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_posts(
    project_id: str,
    generation_request: GeneratePostsRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger post generation for a project.

    Runs the post generator CLI tool in the background.
    Returns immediately with 202 Accepted status.
    """
    # Verify user owns this project
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if project.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Check if brief exists
    brief = db.query(Brief).filter(Brief.project_id == project_id).first()
    if not brief:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No brief found for this project"
        )

    # Update project status
    project.status = "processing"
    project.processing_started_at = datetime.utcnow()
    db.commit()

    # Schedule generation in background
    background_tasks.add_task(
        _run_generation,
        project_id=project_id,
        client_name=project.client_name,
        brief_text=brief.voice_notes,
        num_posts=generation_request.num_posts,
        platform=generation_request.platform,
        db_session=db,
    )

    return {
        "message": "Post generation started",
        "project_id": project_id,
        "status": "processing",
        "num_posts": generation_request.num_posts,
    }


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    project_id: str,
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific post by ID."""
    # Verify project access
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project or project.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Get post
    post = db.query(Post).filter(Post.post_id == post_id, Post.project_id == project_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    return PostResponse.model_validate(post)


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    project_id: str,
    post_id: str,
    post_update: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a post's content.

    This is used for inline editing and tracks revision history.
    """
    # Verify project access
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project or project.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Get post
    post = db.query(Post).filter(Post.post_id == post_id, Post.project_id == project_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Update content
    post.content = post_update.content
    post.word_count = len(post_update.content.split())
    post.last_edited_at = datetime.utcnow()
    post.edited_by = current_user.user_id

    if post_update.status:
        post.status = post_update.status

    db.commit()
    db.refresh(post)

    return PostResponse.model_validate(post)


def _build_brief_text(brief: Brief, client_name: str) -> str:
    """Build brief text from database Brief model."""
    sections = []

    sections.append(f"# Client Brief: {client_name}\n")

    if brief.tone_descriptors:
        sections.append(f"## Voice & Tone\n{brief.tone_descriptors}\n")

    if brief.voice_notes:
        sections.append(f"## Voice Notes\n{brief.voice_notes}\n")

    if brief.audience_type:
        sections.append(f"## Target Audience\n{brief.audience_type}")
        if brief.audience_title:
            sections.append(f" - {brief.audience_title}")
        if brief.audience_industry:
            sections.append(f" in {brief.audience_industry}")
        sections.append("\n")

    if brief.pain_points:
        sections.append(f"## Pain Points\n{brief.pain_points}\n")

    if brief.key_topics:
        sections.append(f"## Key Topics\n{brief.key_topics}\n")

    if brief.content_examples:
        sections.append(f"## Content Examples\n{brief.content_examples}\n")

    if brief.target_platforms:
        sections.append(f"## Target Platforms\n{brief.target_platforms}\n")

    if brief.conversion_goal:
        sections.append(f"## Conversion Goal\n{brief.conversion_goal}\n")

    if brief.customer_stories:
        sections.append(f"## Customer Stories\n{brief.customer_stories}\n")

    return "\n".join(sections)


def _run_generation(
    project_id: str,
    client_name: str,
    brief_text: str,
    num_posts: int,
    platform: str,
    db_session: Session,
):
    """
    Background task to run post generation using the CLI agents.
    """
    try:
        # Get brief from database
        brief = db_session.query(Brief).filter(Brief.project_id == project_id).first()
        if not brief:
            raise ValueError("Brief not found")

        # Build brief text from database model
        full_brief_text = _build_brief_text(brief, client_name)

        # Parse brief
        parser = BriefParserAgent()
        client_brief = parser.parse_brief(full_brief_text)

        # Convert platform string to Platform enum
        platform_enum = Platform(platform.lower())

        # Generate posts using async agent
        generator = ContentGeneratorAgent()

        # Run async generation in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            generated_posts = loop.run_until_complete(
                generator.generate_posts_async(
                    client_brief=client_brief, num_posts=num_posts, platform=platform_enum
                )
            )
        finally:
            loop.close()

        # Save generated posts to database
        for i, generated_post in enumerate(generated_posts, 1):
            post = Post(
                project_id=project_id,
                post_number=i,
                content=generated_post.content,
                template_name=generated_post.template_name,
                platform=platform,
                word_count=generated_post.word_count,
                status="draft",
                version=1,
            )
            db_session.add(post)

        db_session.commit()

        # Update project status
        project = db_session.query(Project).filter(Project.project_id == project_id).first()
        if project:
            project.status = "qa_review"
            project.completed_at = datetime.utcnow()
            db_session.commit()

    except Exception as e:
        # On error, update project status
        project = db_session.query(Project).filter(Project.project_id == project_id).first()
        if project:
            project.status = "brief_submitted"  # Reset to initial state
            db_session.commit()
        # Log the error
        print(f"Error generating posts: {str(e)}")
        raise
