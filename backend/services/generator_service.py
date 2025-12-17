"""
Generator Service - Orchestrates content generation workflow

Handles:
- Brief file creation from project data
- CLI execution for content generation
- Post creation in database
- Run status tracking
"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models import Post, Project, Run
from services import crud
from utils.cli_executor import cli_executor
from utils.logger import logger


class GeneratorService:
    """Service for content generation operations"""

    def __init__(self):
        # Use data directory relative to backend or in /app/data for Docker
        backend_dir = Path(__file__).parent.parent
        self.data_dir = backend_dir / "data"
        self.briefs_dir = self.data_dir / "briefs"

        # Create directories with proper error handling
        try:
            self.briefs_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Fallback to temp directory if permissions issue
            import tempfile
            self.data_dir = Path(tempfile.gettempdir()) / "content_jumpstart"
            self.briefs_dir = self.data_dir / "briefs"
            self.briefs_dir.mkdir(parents=True, exist_ok=True)

    async def generate_all_posts(
        self,
        db: Session,
        project_id: str,
        client_id: str,
        num_posts: int = 30,
        platform: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        Generate all posts for a project

        Args:
            db: Database session
            project_id: Project ID
            client_id: Client ID
            num_posts: Number of posts to generate
            platform: Target platform (optional)

        Returns:
            Dict with:
                - run_id: str
                - posts_created: int
                - output_dir: str
                - files: Dict[str, str]
        """
        logger.info(f"Starting content generation for project {project_id}")

        # Get project and client
        project = crud.get_project(db, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        client = crud.get_client(db, client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        # Create brief file from project data
        brief_path = self._create_brief_file(project, client)

        # Execute CLI
        result = await cli_executor.run_content_generation(
            brief_path=str(brief_path),
            client_name=client.name,
            num_posts=num_posts,
            platform=platform,
        )

        if not result["success"]:
            raise Exception(result.get("error", "Generation failed"))

        # Create Post records in database
        posts_created = 0
        if result.get("posts"):
            posts_created = self._create_post_records(
                db=db,
                project_id=project_id,
                posts_data=result["posts"],
            )

        logger.info(f"Successfully created {posts_created} post records")

        return {
            "posts_created": posts_created,
            "output_dir": result.get("output_dir"),
            "files": result.get("files", {}),
        }

    async def regenerate_posts(
        self,
        db: Session,
        project_id: str,
        post_ids: List[str],
    ) -> Dict[str, any]:
        """
        Regenerate specific posts

        Args:
            db: Database session
            project_id: Project ID
            post_ids: List of post IDs to regenerate

        Returns:
            Dict with regeneration results
        """
        logger.info(f"Regenerating {len(post_ids)} posts for project {project_id}")

        # TODO: Implement actual regeneration logic
        # This would:
        # 1. Get original posts from database
        # 2. Extract their templates and variants
        # 3. Call CLI with regeneration parameters
        # 4. Update post records with new content

        # For now, return stub response
        return {
            "posts_regenerated": len(post_ids),
            "status": "completed",
        }

    def _create_brief_file(self, project: Project, client: any) -> Path:
        """
        Create a brief file from project/client data

        Args:
            project: Project model
            client: Client model

        Returns:
            Path to created brief file
        """
        # Generate brief filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        brief_filename = f"{client.name}_{timestamp}_brief.txt"
        brief_path = self.briefs_dir / brief_filename

        # Build brief content
        # This is a simplified version - could be enhanced with more fields
        brief_content = f"""Company Name: {client.name}

Business Description: {project.description or 'Content creation project'}

Ideal Customer: {project.target_audience or 'General audience'}

Main Problem Solved: {project.pain_points or 'Communication challenges'}

Target Platforms: {', '.join(project.platforms or ['LinkedIn'])}

Tone Preference: {project.tone or 'Professional'}

Generated from project: {project.id}
Client ID: {client.id}
"""

        # Write brief file
        brief_path.write_text(brief_content, encoding='utf-8')
        logger.info(f"Created brief file: {brief_path}")

        return brief_path

    def _create_post_records(
        self,
        db: Session,
        project_id: str,
        posts_data: List[Dict],
    ) -> int:
        """
        Create Post records in database from generated posts

        Args:
            db: Database session
            project_id: Project ID
            posts_data: List of post data dicts from CLI

        Returns:
            Number of posts created
        """
        posts_created = 0

        for post_data in posts_data:
            try:
                # Create Post model
                post = Post(
                    id=f"post-{uuid.uuid4().hex[:12]}",
                    project_id=project_id,
                    content=post_data.get("content", ""),
                    platform=post_data.get("target_platform", "linkedin"),
                    template_id=str(post_data.get("template_id", "")),
                    template_name=post_data.get("template_name", ""),
                    variant=post_data.get("variant", 1),
                    word_count=post_data.get("word_count", 0),
                    has_cta=post_data.get("has_cta", False),
                    needs_review=post_data.get("needs_review", False),
                    review_reasons=post_data.get("review_reasons", []),
                    keywords_used=post_data.get("keywords_used", []),
                    status="approved",  # Default to approved, QA can flag
                    created_at=datetime.utcnow(),
                )

                db.add(post)
                posts_created += 1

            except Exception as e:
                logger.error(f"Failed to create post record: {str(e)}")
                continue

        # Commit all posts
        db.commit()

        return posts_created


# Global instance
generator_service = GeneratorService()
