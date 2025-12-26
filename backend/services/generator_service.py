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
        num_posts: Optional[int] = None,
        platform: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        Generate all posts for a project

        NEW: Supports template quantities from project model.
        If project has template_quantities, uses those for generation.
        Otherwise, falls back to legacy num_posts parameter.

        Args:
            db: Database session
            project_id: Project ID
            client_id: Client ID
            num_posts: Number of posts to generate (optional, overrides template_quantities)
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

        # NEW: Check for template quantities
        template_quantities = project.template_quantities
        if template_quantities:
            # Convert string keys to integers (JSON stores keys as strings)
            template_quantities_int = {
                int(k): v for k, v in template_quantities.items()
            }
            total_posts = sum(template_quantities_int.values())
            logger.info(
                f"Using template quantities from project: {template_quantities_int} "
                f"(total: {total_posts} posts)"
            )

            # Use template quantities for generation
            return await self._generate_with_template_quantities(
                db=db,
                project=project,
                client=client,
                template_quantities=template_quantities_int,
                platform=platform,
            )

        # Legacy mode: use num_posts parameter
        if num_posts is None:
            num_posts = project.num_posts or 30
        logger.info(f"Using legacy num_posts mode: {num_posts} posts")

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

    async def _generate_with_template_quantities(
        self,
        db: Session,
        project: Project,
        client: any,
        template_quantities: Dict[int, int],
        platform: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        Generate posts using template quantities (direct content generator call)

        This method bypasses the CLI executor and calls the content generator directly
        when template quantities are provided, allowing for precise control over
        which templates are used and how many posts are generated from each.

        Args:
            db: Database session
            project: Project model
            client: Client model
            template_quantities: Dict mapping template_id -> quantity
            platform: Target platform (optional)

        Returns:
            Dict with generation results
        """
        import sys
        from pathlib import Path

        # Add src to path to import content generator
        src_path = Path(__file__).parent.parent.parent / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        from agents.content_generator import ContentGeneratorAgent
        from models.client_brief import ClientBrief, Platform

        # Build client brief from project/client data
        logger.info("Building client brief from project data")

        # Map platform string to Platform enum
        platform_enum = Platform.LINKEDIN  # Default
        if platform:
            platform_upper = platform.upper()
            try:
                platform_enum = Platform[platform_upper]
            except KeyError:
                logger.warning(f"Unknown platform '{platform}', using LINKEDIN")

        # Create client brief
        brief = ClientBrief(
            company_name=client.name,
            business_description=client.business_description or "Content creation project",
            ideal_customer=client.ideal_customer or "General audience",
            main_problem_solved=client.main_problem_solved or "Communication challenges",
            platforms=[platform_enum],
            tone_preference=project.tone or client.tone_preference or "Professional",
            customer_pain_points=client.customer_pain_points or [],
            customer_questions=client.customer_questions or [],
        )

        # Initialize content generator
        logger.info("Initializing content generator")
        generator = ContentGeneratorAgent()

        # Generate posts using template quantities
        logger.info(f"Generating posts with template quantities: {template_quantities}")
        posts = await generator.generate_posts_async(
            client_brief=brief,
            template_quantities=template_quantities,
            platform=platform_enum,
            randomize=True,
            max_concurrent=5,
            use_client_memory=False,  # Not using client memory for now
        )

        logger.info(f"Generated {len(posts)} posts")

        # Create Post records in database
        posts_created = 0
        for post in posts:
            try:
                db_post = Post(
                    id=f"post-{uuid.uuid4().hex[:12]}",
                    project_id=project.id,
                    content=post.content,
                    platform=post.target_platform.value.lower(),
                    template_id=str(post.template_id),
                    template_name=post.template_name,
                    variant=post.variant,
                    word_count=post.word_count,
                    has_cta=post.has_cta,
                    needs_review=False,  # Template quantities are deliberate choices
                    review_reasons=[],
                    keywords_used=post.keywords_used or [],
                    status="approved",
                    created_at=datetime.utcnow(),
                )
                db.add(db_post)
                posts_created += 1

            except Exception as e:
                logger.error(f"Failed to create post record: {str(e)}")
                continue

        # Commit all posts
        db.commit()
        logger.info(f"Successfully created {posts_created} post records in database")

        return {
            "posts_created": posts_created,
            "output_dir": None,  # No file output for direct generation
            "files": {},
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

        # Build brief content from client and project data
        # Client has the business profile fields from the wizard
        brief_content = f"""Company Name: {client.name}

Business Description: {client.business_description or 'Content creation project'}

Ideal Customer: {client.ideal_customer or 'General audience'}

Main Problem Solved: {client.main_problem_solved or 'Communication challenges'}

Target Platforms: {', '.join(project.platforms or ['LinkedIn'])}

Tone Preference: {project.tone or client.tone_preference or 'Professional'}

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
