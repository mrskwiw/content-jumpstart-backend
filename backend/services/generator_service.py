"""
Generator Service - Orchestrates content generation workflow

Handles:
- Brief file creation from project data
- CLI execution for content generation
- Post creation in database
- Run status tracking
"""

import re
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models import Post, Project, Run
from backend.services import crud
from backend.utils.cli_executor import cli_executor
from backend.utils.logger import logger

# Patterns for Bug #143 (contradictory stats) and Bug #139 (duplicate book sources)
_STAT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*%", re.IGNORECASE)
_BOOK_PATTERN = re.compile(
    r"(?:reading|from|in)\s+[\"']?([A-Z][^\"'\n]{3,60})[\"']?\s+by\s+([A-Z][a-z]+ [A-Z][a-z]+)",
    re.IGNORECASE,
)


def _check_batch_consistency(posts: list) -> List[str]:
    """Bug #139 + #143: detect same-book reuse and contradictory stat values."""
    warnings: List[str] = []

    # Bug #139 — same book cited more than once across the batch
    book_occurrences: Dict[str, List[int]] = defaultdict(list)
    for i, post in enumerate(posts, 1):
        content = getattr(post, "content", "") or ""
        for match in _BOOK_PATTERN.finditer(content):
            key = match.group(1).strip().lower()[:40]
            book_occurrences[key].append(i)

    for book_key, post_indices in book_occurrences.items():
        if len(post_indices) > 1:
            warnings.append(
                f"Same source '{book_key}' cited in posts {post_indices}. "
                f"Consider using a different source in one of these posts."
            )

    # Bug #143 — same topic cited with different specific percentages
    # Group % figures by the 5-word window preceding them (rough topic fingerprint)
    topic_stats: Dict[str, Dict[float, List[int]]] = defaultdict(lambda: defaultdict(list))
    for i, post in enumerate(posts, 1):
        content = getattr(post, "content", "") or ""
        for m in _STAT_PATTERN.finditer(content):
            pct = float(m.group(1))
            # Use the 5 words before the match as the topic key
            char_pos = m.start()
            pre_text = content[:char_pos].split()
            topic_key = " ".join(pre_text[-5:]).lower().strip()
            topic_stats[topic_key][pct].append(i)

    for topic_key, pct_map in topic_stats.items():
        if len(pct_map) > 1:
            conflict_str = ", ".join(
                f"{p}% (post {idx})" for p, idxs in pct_map.items() for idx in idxs
            )
            warnings.append(
                f"Contradictory statistics near '{topic_key}': {conflict_str}. "
                f"Verify before publishing."
            )

    return warnings


def _calculate_readability(content: str) -> float:
    """Flesch Reading Ease score (0–100) for a post."""
    words = len(content.split())
    if words == 0:
        return 0.0
    sentences = max(1, len([s for s in content.split(".") if s.strip()]))
    syllables = sum(max(1, len(word) // 3) for word in content.split())
    score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
    return max(0.0, min(100.0, round(score, 1)))


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
        template_quantities: Optional[Dict[str, int]] = None,
        custom_topics: Optional[List[str]] = None,  # NEW: topic override for generation
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate all posts for a project

        NEW: Supports template quantities from project model OR from parameter.
        Priority: parameter template_quantities > project.template_quantities > num_posts

        Args:
            db: Database session
            project_id: Project ID
            client_id: Client ID
            num_posts: Number of posts to generate (optional, lowest priority)
            platform: Target platform (optional)
            template_quantities: Template quantities from frontend (optional, highest priority)

        Returns:
            Dict with:
                - run_id: str
                - posts_created: int
                - output_dir: str
                - files: Dict[str, str]
        """
        logger.info(f"Starting content generation for project {project_id}")
        if template_quantities:
            logger.info(f"Using template quantities from parameter: {template_quantities}")

        # Get project and client
        project = crud.get_project(db, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        client = crud.get_client(db, client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        # Priority 1: Use template quantities from parameter (from frontend)
        # Priority 2: Use template quantities from project model (saved in DB)
        # Priority 3: Use num_posts parameter (legacy mode)
        quantities_to_use = template_quantities or project.template_quantities
        if quantities_to_use:
            # Validate regardless of source — project-saved quantities are not
            # gated by the API request validator and can contain zero/negative values.
            bad = {tid: qty for tid, qty in quantities_to_use.items() if qty < 1}
            if bad:
                raise ValueError(
                    f"template_quantities contains invalid values (must be >= 1): {bad}. "
                    f"Source: {'request parameter' if template_quantities else 'project record'}."
                )

            # Convert string keys to integers (JSON stores keys as strings)
            template_quantities_int = {int(k): v for k, v in quantities_to_use.items()}
            total_posts = sum(template_quantities_int.values())
            source = "parameter (frontend)" if template_quantities else "project model (database)"
            logger.info(
                f"Using template quantities from {source}: {template_quantities_int} "
                f"(total: {total_posts} posts)"
            )

            # Use template quantities for generation
            return await self._generate_with_template_quantities(
                db=db,
                project=project,
                client=client,
                template_quantities=template_quantities_int,
                platform=platform,
                custom_topics=custom_topics,  # NEW: pass topic override
                run_id=run_id,
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
            error_details = result.get("error", "Unknown error - CLI execution failed")
            logger.error(f"CLI generation failed: {error_details}")
            logger.error(f"Full result: {result}")
            raise Exception(f"Content generation failed: {error_details}")

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
        feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Regenerate specific posts with new content

        Args:
            db: Database session
            project_id: Project ID
            post_ids: List of post IDs to regenerate
            feedback: Optional feedback/instructions for regeneration

        Returns:
            Dict with regeneration results including updated posts
        """
        logger.info(f"Regenerating {len(post_ids)} posts for project {project_id}")

        # Get project and client
        project = crud.get_project(db, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        client = crud.get_client(db, project.client_id)
        if not client:
            raise ValueError(f"Client {project.client_id} not found")

        # Fetch all requested posts in one query — avoids N individual lookups
        # and any identity-map interference from the cached project object.
        original_posts = (
            db.query(Post).filter(Post.id.in_(post_ids), Post.project_id == project_id).all()
        )
        found_ids = {p.id for p in original_posts}
        for pid in post_ids:
            if pid not in found_ids:
                logger.warning(f"Post {pid} not found or doesn't belong to project {project_id}")

        if not original_posts:
            return {
                "posts_regenerated": 0,
                "status": "completed",
                "message": "No valid posts found to regenerate",
            }

        # Build template quantities from original posts
        template_quantities: Dict[int, int] = {}
        for post in original_posts:
            if post.template_id:
                template_id = int(post.template_id)
                template_quantities[template_id] = template_quantities.get(template_id, 0) + 1

        logger.info(f"Template quantities for regeneration: {template_quantities}")

        try:
            # Import content generator
            import sys
            from pathlib import Path

            project_root = Path(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            from src.agents.content_generator import ContentGeneratorAgent
            from src.models.client_brief import ClientBrief, Platform

            # Map platform string to Platform enum
            platform_str = original_posts[0].target_platform or "linkedin"
            platform_upper = platform_str.upper()
            regen_platform_warning: Optional[str] = None
            try:
                platform_enum = Platform[platform_upper]
            except KeyError:
                regen_platform_warning = (
                    f"⚠️ Platform '{platform_str}' is not supported and was substituted with "
                    f"'{Platform.LINKEDIN.value}'. Supported platforms: "
                    f"{', '.join(sorted(p.value for p in Platform))}."
                )
                platform_enum = Platform.LINKEDIN

            # Create client brief (with optional feedback incorporated)
            business_desc = client.business_description or "Content creation project"
            if feedback:
                business_desc = f"{business_desc}\n\nRegeneration feedback: {feedback}"

            brief = ClientBrief(
                company_name=client.name,
                business_description=business_desc,
                ideal_customer=client.ideal_customer or "General audience",
                main_problem_solved=client.main_problem_solved or "Communication challenges",
                platforms=[platform_enum],
                tone_preference=project.tone or client.tone_preference or "Professional",
                customer_pain_points=client.customer_pain_points or [],
                customer_questions=client.customer_questions or [],
                project_id=project_id,
            )

            # Generate new posts
            generator = ContentGeneratorAgent()
            new_posts = await generator.generate_posts_async(
                client_brief=brief,
                template_quantities=template_quantities,
                platform=platform_enum,
                randomize=True,
                max_concurrent=5,
                use_client_memory=False,
            )

            logger.info(f"Generated {len(new_posts)} new posts for regeneration")

            # Update original posts with new content
            posts_updated = 0
            new_posts_iter = iter(new_posts)

            for original_post in original_posts:
                try:
                    new_post = next(new_posts_iter, None)
                    if new_post:
                        # Update the post record in-place; run_id intentionally
                        # preserved so the export query finds all posts via the
                        # original generation run (partial regen would otherwise
                        # leave a mixed-run_id set that exports incompletely).
                        original_post.content = new_post.content
                        original_post.word_count = new_post.word_count
                        original_post.has_cta = new_post.has_cta
                        original_post.status = "approved"  # Reset status after regeneration
                        original_post.flags = None  # Clear any flags
                        posts_updated += 1
                        logger.info(f"Updated post {original_post.id} with new content")
                except Exception as e:
                    logger.error(f"Failed to update post {original_post.id}: {str(e)}")
                    continue

            db.commit()
            logger.info(f"Successfully regenerated {posts_updated} posts")

            return {
                "posts_regenerated": posts_updated,
                "status": "completed",
                "message": f"Successfully regenerated {posts_updated} posts",
                "platform_warning": regen_platform_warning,  # Bug #110
            }

        except Exception as e:
            logger.error(f"Regeneration failed: {str(e)}", exc_info=True)
            db.rollback()
            return {
                "posts_regenerated": 0,
                "status": "failed",
                "message": f"Regeneration failed: {str(e)}",
            }

    async def _generate_with_template_quantities(
        self,
        db: Session,
        project: Project,
        client: Any,
        template_quantities: Dict[int, int],
        platform: Optional[str] = None,
        custom_topics: Optional[List[str]] = None,  # NEW: topic override for generation
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
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
        try:
            import sys
            from pathlib import Path

            logger.info(f"Starting _generate_with_template_quantities for project {project.id}")
            logger.info(f"Template quantities: {template_quantities}")
            logger.info(f"Client: {client.name} (ID: {client.id})")
            logger.info(f"Project: {project.name} (ID: {project.id})")

            # Add project root to path to import from src package
            project_root = Path(__file__).parent.parent.parent
            logger.info(f"Adding project root to sys.path: {project_root}")

            if not project_root.exists():
                raise FileNotFoundError(f"Project root does not exist: {project_root}")

            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
                logger.info(f"Successfully added {project_root} to sys.path")

            # Import required modules (use src.* imports since project root is in sys.path)
            logger.info("Importing ContentGeneratorAgent and models...")
            try:
                from src.agents.content_generator import ContentGeneratorAgent
                from src.models.client_brief import ClientBrief, Platform

                logger.info("Successfully imported required modules")
            except ImportError as e:
                logger.error(f"Failed to import required modules: {str(e)}", exc_info=True)
                raise

            # Build client brief from project/client data
            logger.info("Building client brief from project data")
            logger.info(
                f"Client data - name: {client.name}, business_description: {client.business_description[:100] if client.business_description else 'None'}..."
            )

            # Map platform string to Platform enum
            platform_enum = Platform.LINKEDIN  # Default
            platform_warning: Optional[str] = None
            if platform:
                platform_upper = platform.upper()
                try:
                    platform_enum = Platform[platform_upper]
                    logger.info(f"Using platform: {platform_enum.value}")
                except KeyError:
                    platform_warning = (
                        f"⚠️ Platform '{platform}' is not supported and was substituted with "
                        f"'{Platform.LINKEDIN.value}'. Supported platforms: "
                        f"{', '.join(sorted(p.value for p in Platform))}."
                    )
                    logger.warning(f"Unknown platform '{platform}', using LINKEDIN")

            # Create client brief
            try:
                brief = ClientBrief(
                    company_name=client.name,
                    business_description=client.business_description or "Content creation project",
                    ideal_customer=client.ideal_customer or "General audience",
                    main_problem_solved=client.main_problem_solved or "Communication challenges",
                    platforms=[platform_enum],
                    tone_preference=project.tone or client.tone_preference or "Professional",
                    customer_pain_points=client.customer_pain_points or [],
                    customer_questions=client.customer_questions or [],
                    project_id=project.id,
                )
                logger.info(f"Successfully created ClientBrief for {brief.company_name}")
            except Exception as e:
                logger.error(f"Failed to create ClientBrief: {str(e)}", exc_info=True)
                raise

            # Initialize content generator
            logger.info("Initializing content generator")
            try:
                generator = ContentGeneratorAgent()
                logger.info("Successfully initialized ContentGeneratorAgent")
            except Exception as e:
                logger.error(
                    f"Failed to initialize ContentGeneratorAgent: {str(e)}",
                    exc_info=True,
                )
                raise

            # Generate posts using template quantities
            logger.info(
                f"Calling generate_posts_async with template quantities: {template_quantities}"
            )
            logger.info(f"Template quantities type: {type(template_quantities)}")
            logger.info(
                f"Template quantities keys: {list(template_quantities.keys()) if template_quantities else 'None'}"
            )
            logger.info(
                f"Template quantities values: {list(template_quantities.values()) if template_quantities else 'None'}"
            )
            logger.info(
                f"Expected total posts: {sum(template_quantities.values()) if template_quantities else 0}"
            )

            skipped_tasks = 0  # posts whose template ID was not found in the library
            try:
                expected_posts = sum(template_quantities.values()) if template_quantities else 0
                # No outer asyncio.wait_for timeout. Individual API calls are bounded by
                # the 120s httpx read timeout set on AnthropicClient, and each post caps
                # at MAX_ATTEMPTS=10 quality retries. An outer timeout caused zombie tasks:
                # wait_for cancelled the outer coroutine, the SDK converted CancelledError
                # → APIConnectionError, and the retry loop kept running in the background
                # while the run was already marked failed.
                logger.info(f"Starting generation of {expected_posts} posts")
                from src.config.constants import DEFAULT_MAX_CONCURRENT_CALLS

                posts = await generator.generate_posts_async(
                    client_brief=brief,
                    template_quantities=template_quantities,
                    platform=platform_enum,
                    randomize=True,
                    max_concurrent=DEFAULT_MAX_CONCURRENT_CALLS,
                    use_client_memory=False,
                )
                # Posts whose template ID was not found in the library are silently
                # excluded by the generator — they never become tasks at all.
                # Compute the count here so it can surface in the dashboard run log.
                skipped_tasks = max(0, expected_posts - len(posts))
                logger.info(
                    f"Successfully generated {len(posts)} posts (expected: {expected_posts}"
                    + (f", skipped: {skipped_tasks}" if skipped_tasks else "")
                    + ")"
                )

                if len(posts) == 0:
                    logger.warning("⚠️ CRITICAL: generate_posts_async returned 0 posts!")
                    logger.warning(
                        f"Expected posts based on template_quantities: {sum(template_quantities.values())}"
                    )

            except Exception as e:
                logger.error(f"Failed to generate posts: {str(e)}", exc_info=True)
                raise

            # --- Batch consistency checks (pre-commit) ---
            # Bug #143: flag contradictory specific percentages for the same topic
            # Bug #139: flag same book/source cited more than once in the batch
            if posts:
                _batch_consistency_warnings = _check_batch_consistency(posts)
                for w in _batch_consistency_warnings:
                    logger.warning(f"⚠️ BATCH CONSISTENCY: {w}")

            # --- Batch QA (pre-commit) ---
            # Run before writing to DB so the score and per-post flags are
            # available when records are created. The per-post QA retries
            # already ran during generation; this pass catches batch-level
            # issues (hook uniqueness, CTA variety, SEO, headlines).
            qa_score_pre: float | None = None
            qa_overall_passed: bool | None = None  # None = QA didn't run
            if run_id and posts:
                try:
                    from src.agents.client_classifier import ClientClassifier
                    from src.agents.qa_agent import QAAgent

                    _client_type = None
                    try:
                        _client_type, _ = ClientClassifier().classify_client(brief)
                    except Exception as _ce:
                        logger.warning(f"Client classification for QA failed (non-critical): {_ce}")

                    qa_report = QAAgent().validate_posts(
                        posts, client.name or "", client_type=_client_type
                    )
                    qa_score_pre = qa_report.quality_score
                    qa_overall_passed = qa_report.overall_passed
                    logger.info(
                        f"Pre-commit QA: {qa_score_pre:.1%} "
                        f"({'PASSED' if qa_overall_passed else 'NEEDS REVIEW'}), "
                        f"issues: {qa_report.total_issues}"
                    )
                    if not qa_overall_passed:
                        logger.warning(
                            f"Batch QA failed before commit — {qa_report.total_issues} issue(s). "
                            f"Posts will be saved with needs_review=True."
                        )
                except Exception as e:
                    logger.warning(f"Pre-commit QA failed (non-critical): {e}")

            # Store qa_score on the run record now so it's committed together with posts
            if qa_score_pre is not None and run_id:
                try:
                    run_record = db.get(Run, run_id)
                    if run_record:
                        run_record.qa_score = qa_score_pre
                except Exception as e:
                    logger.warning(f"Failed to set run qa_score before commit: {e}")

            # Create Post records in database
            logger.info(f"Creating {len(posts)} Post records in database for project {project.id}")
            posts_created = 0
            posts_failed = 0
            placeholder_count = 0

            # Determine per-post CTA status so only posts that genuinely lack a
            # CTA are flagged — not every post in the batch when one fails.
            from src.validators.cta_validator import CTAValidator as _CTAValidator

            _cta_types = _CTAValidator(use_llm_fallback=True)._extract_cta_types(posts)

            for idx, post in enumerate(posts):
                try:
                    post_id = f"post-{uuid.uuid4().hex[:12]}"
                    logger.info(
                        f"Creating post {idx+1}/{len(posts)}: {post_id} (template: {post.template_name})"
                    )

                    is_placeholder = post.content.startswith("[ERROR:")
                    # Flag only posts that genuinely have no CTA of any kind.
                    # Engagement questions are a valid CTA type and must not be flagged.
                    post_has_no_cta = _cta_types[idx] == "no_cta"
                    # Derive has_cta from _cta_types (the authoritative result that
                    # includes the LLM fallback) rather than post.has_cta (regex-only).
                    # This keeps the persisted flag consistent with the approval decision.
                    post_has_cta = not post_has_no_cta
                    needs_flag = is_placeholder or post_has_no_cta
                    post_flags: list[str] = []
                    if is_placeholder:
                        post_flags.append("placeholder")
                    if post_has_no_cta and not is_placeholder:
                        post_flags.append("no_cta")
                    db_post = Post(
                        id=post_id,
                        project_id=project.id,
                        run_id=run_id
                        or f"run-{uuid.uuid4().hex[:12]}",  # Use provided run_id or generate new one
                        content=post.content,
                        target_platform=post.target_platform.value.lower(),  # Fixed: was 'platform', should be 'target_platform'
                        template_id=str(post.template_id),
                        template_name=post.template_name,
                        variant=post.variant,
                        word_count=post.word_count,
                        has_cta=post_has_cta,
                        readability_score=_calculate_readability(post.content),
                        status="flagged" if needs_flag else "approved",
                        flags=post_flags,
                        is_placeholder=is_placeholder,
                        created_at=datetime.utcnow(),
                        twitter_share_copy=getattr(post, "twitter_share_copy", None),
                    )
                    db.add(db_post)
                    posts_created += 1
                    if is_placeholder:
                        placeholder_count += 1
                    logger.info(f"Successfully created post record {post_id}")

                except Exception as e:
                    posts_failed += 1
                    logger.error(
                        f"Failed to save post {idx+1}/{len(posts)} to database: {str(e)}",
                        exc_info=True,
                    )
                    continue

            if posts_failed:
                logger.error(
                    f"⚠️ {posts_failed} of {len(posts)} posts failed to save — "
                    f"only {posts_created} will appear in the deliverable."
                )

            # Commit all posts
            logger.info(f"Committing {posts_created} posts to database...")
            try:
                db.commit()
                logger.info(f"✅ Successfully committed {posts_created} post records to database")
            except Exception as e:
                logger.error(f"Failed to commit posts to database: {str(e)}", exc_info=True)
                db.rollback()
                raise

            # qa_score already set and committed above (pre-commit QA block)

            # Verify posts were saved — filter by run_id to avoid counting prior-run posts
            saved_posts = crud.get_posts(db, project_id=project.id, run_id=run_id, limit=100)
            logger.info(
                f"Verification: Found {len(saved_posts)} posts for run {run_id} in database"
            )

            if len(saved_posts) != posts_created:
                logger.warning(
                    f"⚠️ Mismatch: Created {posts_created} posts but only {len(saved_posts)} "
                    f"found for run {run_id} — some posts may not have committed correctly"
                )

            # Sync token usage from cost_tracker.db to database
            try:
                from backend.services.token_sync_service import token_sync_service

                logger.info(f"Syncing token usage for run {run_id}...")
                usage_data = token_sync_service.sync_run_token_usage(
                    db=db, run_id=run_id, project_id=project.id
                )

                if usage_data:
                    # Estimate token usage for individual posts
                    posts_updated = token_sync_service.estimate_post_token_usage(
                        db=db, run_id=run_id
                    )
                    logger.info(
                        f"Token tracking complete: {usage_data.get('total_input_tokens', 0)} input tokens, "
                        f"{usage_data.get('total_output_tokens', 0)} output tokens, "
                        f"${usage_data.get('total_cost', 0):.4f} cost ({posts_updated} posts)"
                    )
            except Exception as e:
                logger.warning(f"Failed to sync token usage (non-critical): {e}")

            return {
                "posts_created": posts_created,
                "posts_failed": posts_failed,
                "placeholder_count": placeholder_count,
                "skipped_tasks": skipped_tasks,
                "output_dir": None,  # No file output for direct generation
                "files": {},
                "platform_warning": platform_warning,  # Bug #110: None if platform was valid
            }

        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                f"❌ CRITICAL ERROR in _generate_with_template_quantities: {error_type}: {str(e)}",
                exc_info=True,
            )
            # Re-raise with more context
            raise Exception(f"Template-based generation failed ({error_type}): {str(e)}") from e

    def _create_brief_file(self, project: Project, client: Any) -> Path:
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
        brief_path.write_text(brief_content, encoding="utf-8")
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
                content = post_data.get("content", "")
                post = Post(
                    id=f"post-{uuid.uuid4().hex[:12]}",
                    project_id=project_id,
                    content=content,
                    platform=post_data.get("target_platform", "linkedin"),
                    template_id=str(post_data.get("template_id", "")),
                    template_name=post_data.get("template_name", ""),
                    variant=post_data.get("variant", 1),
                    word_count=post_data.get("word_count", 0),
                    has_cta=post_data.get("has_cta", False),
                    needs_review=post_data.get("needs_review", False),
                    review_reasons=post_data.get("review_reasons", []),
                    keywords_used=post_data.get("keywords_used", []),
                    readability_score=_calculate_readability(content),
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
