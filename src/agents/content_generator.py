"""Content Generator Agent: Generates posts from templates and client context"""

import asyncio
import random
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..config.template_angles import TEMPLATE_ANGLES, MAX_QUANTITY_PER_TEMPLATE
from ..config.brand_frameworks import (
    get_archetype_from_client_type,
    get_archetype_guidance,
    get_writing_principles_guidance,
)
from ..config.hook_frameworks import build_hook_guidance
from ..config.constants import AI_TELL_PHRASES, MAX_POST_WORD_COUNT, MIN_POST_WORD_COUNT
from ..config.platform_specs import (
    PLATFORM_LENGTH_SPECS,
    get_platform_prompt_guidance,
    get_platform_target_length,
)
from ..config.prompts import SystemPrompts
from ..models.client_brief import ClientBrief, Platform
from ..models.client_memory import ClientMemory
from ..models.post import Post
from ..models.seo_keyword import KeywordStrategy
from ..models.template import Template
from ..models.voice_sample import VoiceMatchReport
from ..utils.agent_helpers import call_claude_api_async
from ..utils.anthropic_client import AnthropicClient
from ..utils.logger import log_post_generated, logger
from ..utils.skill_loader import load_skill, Skill
from ..utils.template_loader import TemplateLoader
from ..validators.prompt_injection_defense import (
    sanitize_prompt_input,
    detect_prompt_leakage,
)

# TYPE_CHECKING import to avoid circular dependencies
if TYPE_CHECKING:
    from ..database.project_db import ProjectDatabase

# Research context integration
try:
    from backend.services.research_context_builder import (
        build_research_context,
        get_brand_archetype_from_research,
        get_story_context_for_template,
    )

    RESEARCH_CONTEXT_AVAILABLE = True
except ImportError:
    RESEARCH_CONTEXT_AVAILABLE = False
    build_research_context = None
    get_brand_archetype_from_research = None
    get_story_context_for_template = None

try:
    from ..utils.web_search_context import (
        TEMPLATE_WEB_SEARCH_CONFIG,
        MAX_SEARCHES_PER_RUN,
        build_web_search_context,
    )

    WEB_SEARCH_CONTEXT_AVAILABLE = True
except ImportError:
    WEB_SEARCH_CONTEXT_AVAILABLE = False
    TEMPLATE_WEB_SEARCH_CONFIG = {}
    MAX_SEARCHES_PER_RUN = 5
    build_web_search_context = None


class ContentGeneratorAgent:
    """
    Agent that generates social media posts from templates using client context
    """

    # Use centralized system prompt
    SYSTEM_PROMPT = SystemPrompts.CONTENT_GENERATOR

    def __init__(
        self,
        client: Optional[AnthropicClient] = None,
        template_loader: Optional[TemplateLoader] = None,
        keyword_strategy: Optional[KeywordStrategy] = None,
        db: Optional["ProjectDatabase"] = None,
        use_content_skill: bool = True,
        backend_session: Optional[Any] = None,  # SQLAlchemy Session for research context
    ):
        """
        Initialize Content Generator Agent

        Args:
            client: Anthropic client instance
            template_loader: Template loader instance
            keyword_strategy: Optional SEO keyword strategy for keyword-aware generation
            db: Optional ProjectDatabase instance for client memory integration
            use_content_skill: Whether to load and use the content-creator skill (default True)
        """
        self.client = client or AnthropicClient()
        self.template_loader = template_loader or TemplateLoader()
        self.keyword_strategy = keyword_strategy
        self.db = db
        self.backend_session = backend_session  # For research context integration

        # Load content-creator skill for enhanced guidance
        self.content_skill: Optional[Skill] = None
        if use_content_skill:
            try:
                self.content_skill = load_skill("content-creator")
                if self.content_skill:
                    logger.info(
                        f"Loaded content-creator skill v{self.content_skill.metadata.version} "
                        f"with {len(self.content_skill.references)} references"
                    )
            except Exception as e:
                logger.warning(f"Could not load content-creator skill: {e}")

    def generate_posts(
        self,
        client_brief: ClientBrief,
        template_quantities: Optional[Dict[int, int]] = None,
        num_posts: int = 30,
        template_count: int = 15,
        randomize: bool = True,
        template_ids: Optional[List[int]] = None,
        platform: Platform = Platform.LINKEDIN,
        use_client_memory: bool = True,
    ) -> List[Post]:
        """
        Generate a complete set of posts for a client

        Args:
            client_brief: Client brief with context
            template_quantities: NEW: Dict mapping template_id -> quantity (e.g., {1: 3, 2: 5, 9: 2})
                                Takes priority over num_posts/template_count when provided
            num_posts: Total number of posts to generate (default 30, ignored if template_quantities provided)
            template_count: Number of unique templates to use (default 15, ignored if template_quantities provided)
            randomize: Whether to randomize post order
            template_ids: Optional list of specific template IDs to use (overrides intelligent selection)
            platform: Target platform for content generation (default LinkedIn)
            use_client_memory: Whether to use client memory for optimization (default True)

        Returns:
            List of generated Post objects
        """
        # NEW: Priority 1 - Use template quantities if provided
        if template_quantities:
            total_posts = sum(template_quantities.values())
            logger.info(
                f"Generating {total_posts} posts for {client_brief.company_name} "
                f"using template quantities: {template_quantities}"
            )
            return self._generate_posts_from_quantities(
                client_brief=client_brief,
                template_quantities=template_quantities,
                randomize=randomize,
                platform=platform,
                use_client_memory=use_client_memory,
            )

        # Legacy mode: equal distribution
        logger.info(
            f"Generating {num_posts} posts for {client_brief.company_name} "
            f"using {template_count} templates (legacy equal distribution mode)"
        )

        # SECURITY: Sanitize client brief before processing (TR-014)
        try:
            sanitized_brief = self._sanitize_client_brief(client_brief)
        except ValueError as e:
            logger.error(f"Prompt injection detected, aborting generation: {e}")
            raise

        # Load client memory if available and enabled
        client_memory = None
        if use_client_memory and self.db:
            client_memory = self.db.get_client_memory(sanitized_brief.company_name)
            if client_memory and client_memory.is_repeat_client:
                logger.info(
                    f"[REPEAT CLIENT] Welcome back {client_brief.company_name}! "
                    f"Using learnings from {client_memory.total_projects} previous project(s)"
                )
                if client_memory.preferred_templates:
                    logger.info(
                        f"Boosting preferred templates: {client_memory.preferred_templates}"
                    )
                if client_memory.avoided_templates:
                    logger.info(
                        f"Avoiding problematic templates: {client_memory.avoided_templates}"
                    )

        # Select appropriate templates
        if template_ids:
            # Manual template selection - get templates by ID
            selected_templates = []
            for tid in template_ids:
                template = self.template_loader.get_template_by_id(tid)
                if template:
                    selected_templates.append(template)
                else:
                    logger.warning(f"Template ID {tid} not found, skipping")

            if not selected_templates:
                raise ValueError(f"No valid templates found from IDs: {template_ids}")

            logger.info(f"Using manual template override: {template_ids}")
        else:
            # Intelligent template selection with memory-aware preferences
            selected_templates = self.template_loader.select_templates_for_client(
                sanitized_brief,
                count=template_count,
                boost_templates=client_memory.preferred_templates if client_memory else [],
                avoid_templates=client_memory.avoided_templates if client_memory else [],
            )

        # Cache system prompt and base context for reuse across all posts
        cached_system_prompt = self._build_system_prompt(sanitized_brief, platform, client_memory)
        base_context = sanitized_brief.to_context_dict()

        # Generate posts (each template used twice for variety)
        posts = []
        post_number = 1

        # Calculate how many times to use each template
        uses_per_template = num_posts // len(selected_templates)
        extra_posts = num_posts % len(selected_templates)

        for template in selected_templates:
            # Use template the standard number of times
            for variant in range(1, uses_per_template + 1):
                post = self._generate_single_post(
                    template=template,
                    client_brief=sanitized_brief,  # SECURITY FIX: Use sanitized brief (TR-014)
                    variant=variant,
                    post_number=post_number,
                    cached_system_prompt=cached_system_prompt,
                    base_context=base_context,
                    platform=platform,
                )
                posts.append(post)
                log_post_generated(post_number, template.name, post.word_count)
                post_number += 1

        # Generate extra posts to reach target count
        for i in range(extra_posts):
            template = selected_templates[i % len(selected_templates)]
            variant = uses_per_template + 1
            post = self._generate_single_post(
                template=template,
                client_brief=client_brief,
                variant=variant,
                post_number=post_number,
                cached_system_prompt=cached_system_prompt,
                base_context=base_context,
                platform=platform,
            )
            posts.append(post)
            log_post_generated(post_number, template.name, post.word_count)
            post_number += 1

        # Randomize order for variety
        if randomize:
            random.shuffle(posts)
            logger.info("Randomized post order for variety")

        logger.info(f"Successfully generated {len(posts)} posts")
        return posts

    async def generate_posts_async(
        self,
        client_brief: ClientBrief,
        template_quantities: Optional[Dict[int, int]] = None,
        num_posts: int = 30,
        template_count: int = 15,
        randomize: bool = True,
        max_concurrent: int = 5,
        template_ids: Optional[List[int]] = None,
        platform: Platform = Platform.LINKEDIN,
        use_client_memory: bool = True,
    ) -> List[Post]:
        """
        Generate posts in parallel using async API calls

        Args:
            client_brief: Client brief with context
            template_quantities: NEW: Dict mapping template_id -> quantity (e.g., {1: 3, 2: 5, 9: 2})
                                Takes priority over num_posts/template_count when provided
            num_posts: Total number of posts to generate (default 30, ignored if template_quantities provided)
            template_count: Number of unique templates to use (default 15, ignored if template_quantities provided)
            randomize: Whether to randomize post order
            max_concurrent: Maximum concurrent API calls (default 5)
            template_ids: Optional list of specific template IDs to use (overrides intelligent selection)
            platform: Target platform for content generation (default LinkedIn)
            use_client_memory: Whether to use client memory for optimization (default True)

        Returns:
            List of generated Post objects
        """

        # NEW: Priority 1 - Use template quantities if provided
        if template_quantities:
            total_posts = sum(template_quantities.values())
            logger.info(
                f"Generating {total_posts} posts for {client_brief.company_name} "
                f"using template quantities: {template_quantities} (async mode, max concurrent: {max_concurrent})"
            )
            return await self._generate_posts_from_quantities_async(
                client_brief=client_brief,
                template_quantities=template_quantities,
                randomize=randomize,
                max_concurrent=max_concurrent,
                platform=platform,
                use_client_memory=use_client_memory,
            )

        # Legacy mode: equal distribution
        logger.info(
            f"Generating {num_posts} posts for {client_brief.company_name} "
            f"using {template_count} templates (async mode, legacy equal distribution, max concurrent: {max_concurrent})"
        )

        # SECURITY: Sanitize client brief before processing (TR-014)
        try:
            sanitized_brief = self._sanitize_client_brief(client_brief)
        except ValueError as e:
            logger.error(f"Prompt injection detected, aborting generation: {e}")
            raise

        # Load client memory if available and enabled
        client_memory = None
        if use_client_memory and self.db:
            client_memory = self.db.get_client_memory(sanitized_brief.company_name)
            if client_memory and client_memory.is_repeat_client:
                logger.info(
                    f"[REPEAT CLIENT] Welcome back {client_brief.company_name}! "
                    f"Using learnings from {client_memory.total_projects} previous project(s)"
                )
                if client_memory.preferred_templates:
                    logger.info(
                        f"Boosting preferred templates: {client_memory.preferred_templates}"
                    )
                if client_memory.avoided_templates:
                    logger.info(
                        f"Avoiding problematic templates: {client_memory.avoided_templates}"
                    )

        # Select appropriate templates
        if template_ids:
            # Manual template selection - get templates by ID
            selected_templates = []
            for tid in template_ids:
                template = self.template_loader.get_template_by_id(tid)
                if template:
                    selected_templates.append(template)
                else:
                    logger.warning(f"Template ID {tid} not found, skipping")

            if not selected_templates:
                raise ValueError(f"No valid templates found from IDs: {template_ids}")

            logger.info(f"Using manual template override: {template_ids}")
        else:
            # Intelligent template selection with memory-aware preferences
            selected_templates = self.template_loader.select_templates_for_client(
                sanitized_brief,
                count=template_count,
                boost_templates=client_memory.preferred_templates if client_memory else [],
                avoid_templates=client_memory.avoided_templates if client_memory else [],
            )

        # Cache system prompt and base context for reuse across all posts
        cached_system_prompt = self._build_system_prompt(sanitized_brief, platform, client_memory)
        base_context = sanitized_brief.to_context_dict()

        # Build list of post generation tasks
        tasks = []
        post_number = 1

        # Calculate how many times to use each template
        uses_per_template = num_posts // len(selected_templates)
        extra_posts = num_posts % len(selected_templates)

        for template in selected_templates:
            # Use template the standard number of times
            for variant in range(1, uses_per_template + 1):
                tasks.append(
                    {
                        "template": template,
                        "variant": variant,
                        "post_number": post_number,
                        "cached_system_prompt": cached_system_prompt,
                        "base_context": base_context,
                    }
                )
                post_number += 1

        # Generate extra posts to reach target count
        for i in range(extra_posts):
            template = selected_templates[i % len(selected_templates)]
            variant = uses_per_template + 1
            tasks.append(
                {
                    "template": template,
                    "variant": variant,
                    "post_number": post_number,
                    "cached_system_prompt": cached_system_prompt,
                    "base_context": base_context,
                }
            )
            post_number += 1

        # Generate posts in parallel with concurrency limit
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_limit(task_params):
            """Generate single post with concurrency limit via semaphore and quality retry"""
            async with semaphore:
                return await self._generate_single_post_with_retry_async(
                    template=task_params["template"],
                    client_brief=sanitized_brief,  # SECURITY FIX: Use sanitized brief (TR-014)
                    variant=task_params["variant"],
                    post_number=task_params["post_number"],
                    cached_system_prompt=task_params["cached_system_prompt"],
                    base_context=task_params["base_context"],
                    platform=platform,
                    max_attempts=10,  # Try up to 10 times for quality
                )

        # Execute all tasks in parallel
        posts = await asyncio.gather(*[generate_with_limit(task) for task in tasks])

        # Randomize order for variety
        if randomize:
            random.shuffle(posts)
            logger.info("Randomized post order for variety")

        logger.info(f"Successfully generated {len(posts)} posts (async)")
        return posts

    async def generate_posts_with_voice_matching_async(
        self,
        client_brief: ClientBrief,
        num_posts: int = 30,
        template_count: int = 15,
        randomize: bool = True,
        max_concurrent: int = 5,
        template_ids: Optional[List[int]] = None,
        platform: Platform = Platform.LINKEDIN,
        use_client_memory: bool = True,
    ) -> tuple[List[Post], Optional["VoiceMatchReport"]]:
        """
        Generate posts using voice samples for authentic voice matching

        This method:
        1. Checks if client has uploaded voice samples
        2. Analyzes samples to create reference voice guide
        3. Generates posts with enhanced voice guidance
        4. Calculates voice match report comparing generated to reference

        Args:
            client_brief: Client brief with context
            num_posts: Total number of posts to generate (default 30)
            template_count: Number of unique templates to use (default 15)
            randomize: Whether to randomize post order
            max_concurrent: Maximum concurrent API calls (default 5)
            template_ids: Optional list of specific template IDs to use
            platform: Target platform for content generation
            use_client_memory: Whether to use client memory for optimization

        Returns:
            Tuple of (List[Post], Optional[VoiceMatchReport])
            - Posts: Generated posts
            - VoiceMatchReport: Voice matching analysis (None if no samples)
        """
        from ..agents.voice_analyzer import VoiceAnalyzer
        from ..database.project_db import ProjectDatabase
        from ..utils.voice_matcher import VoiceMatcher

        logger.info(
            f"Generating {num_posts} posts with voice matching for {client_brief.company_name}"
        )

        # Check if client has voice samples
        if not self.db:
            self.db = ProjectDatabase()

        voice_sample_stats = self.db.get_voice_sample_upload_stats(client_brief.company_name)

        if not voice_sample_stats or voice_sample_stats.get("sample_count", 0) == 0:
            logger.warning(
                f"No voice samples found for {client_brief.company_name}. "
                f"Proceeding with standard generation (no voice matching)."
            )
            # Fall back to standard generation
            posts = await self.generate_posts_async(
                client_brief=client_brief,
                num_posts=num_posts,
                template_count=template_count,
                randomize=randomize,
                max_concurrent=max_concurrent,
                template_ids=template_ids,
                platform=platform,
                use_client_memory=use_client_memory,
            )
            return posts, None

        # Get voice samples from database
        logger.info(
            f"Found {voice_sample_stats['sample_count']} voice samples "
            f"({voice_sample_stats['total_words']} total words)"
        )

        voice_samples = self.db.get_voice_sample_uploads(client_brief.company_name)

        if not voice_samples:
            logger.warning("Voice samples stats exist but couldn't retrieve samples")
            posts = await self.generate_posts_async(
                client_brief=client_brief,
                num_posts=num_posts,
                template_count=template_count,
                randomize=randomize,
                max_concurrent=max_concurrent,
                template_ids=template_ids,
                platform=platform,
                use_client_memory=use_client_memory,
            )
            return posts, None

        # Analyze voice samples to create reference voice guide
        logger.info("Analyzing voice samples to create reference voice guide...")
        voice_analyzer = VoiceAnalyzer()

        sample_texts = [sample.sample_text for sample in voice_samples]
        reference_voice_guide = voice_analyzer.analyze_voice_samples(
            samples=sample_texts,
            client_name=client_brief.company_name,
            source=voice_samples[0].sample_source if voice_samples else "mixed",
        )

        logger.info(
            f"Reference voice guide created: "
            f"Readability={reference_voice_guide.average_readability_score:.1f}, "
            f"Archetype={reference_voice_guide.voice_archetype}, "
            f"Word Count={reference_voice_guide.average_word_count}"
        )

        # Store voice guide in client brief for context enhancement
        # Note: We'll enhance the system prompt with voice guide details
        original_voice = client_brief.brand_voice if client_brief.brand_voice else ""

        # Enhance brand voice with reference guide details
        voice_enhancement = []
        if reference_voice_guide.voice_archetype:
            voice_enhancement.append(f"Brand Archetype: {reference_voice_guide.voice_archetype}")
        if reference_voice_guide.average_readability_score:
            voice_enhancement.append(
                f"Target Readability: {reference_voice_guide.average_readability_score:.1f} "
                f"(Flesch Reading Ease)"
            )
        if reference_voice_guide.average_word_count:
            voice_enhancement.append(
                f"Typical Length: {reference_voice_guide.average_word_count} words per post"
            )
        if reference_voice_guide.key_phrases_used:
            top_phrases = reference_voice_guide.key_phrases_used[:5]
            voice_enhancement.append(f"Key Phrases: {', '.join(top_phrases)}")

        if voice_enhancement:
            enhanced_voice = original_voice + "\n\n" + "\n".join(voice_enhancement)
            client_brief.brand_voice = enhanced_voice
            logger.info("Enhanced client brief with voice guide details")

        # Generate posts with enhanced voice context
        posts = await self.generate_posts_async(
            client_brief=client_brief,
            num_posts=num_posts,
            template_count=template_count,
            randomize=randomize,
            max_concurrent=max_concurrent,
            template_ids=template_ids,
            platform=platform,
            use_client_memory=use_client_memory,
        )

        # Restore original brand voice
        client_brief.brand_voice = original_voice

        # Calculate voice match report
        logger.info("Calculating voice match report...")
        voice_matcher = VoiceMatcher()

        try:
            voice_match_report = voice_matcher.calculate_match_score(
                generated_posts=posts, reference_voice_guide=reference_voice_guide
            )

            readability = (
                voice_match_report.readability_score.score
                if voice_match_report.readability_score
                else 0.0
            )
            word_count = (
                voice_match_report.word_count_score.score
                if voice_match_report.word_count_score
                else 0.0
            )
            archetype = (
                voice_match_report.archetype_score.score
                if voice_match_report.archetype_score
                else 0.0
            )
            phrases = (
                voice_match_report.phrase_usage_score.score
                if voice_match_report.phrase_usage_score
                else 0.0
            )
            logger.info(
                f"Voice Match Score: {voice_match_report.match_score:.1%} "
                f"(Readability: {readability:.1%}, "
                f"Word Count: {word_count:.1%}, "
                f"Archetype: {archetype:.1%}, "
                f"Phrases: {phrases:.1%})"
            )

            return posts, voice_match_report

        except Exception as e:
            logger.error(f"Failed to calculate voice match report: {e}")
            return posts, None

    def _generate_posts_from_quantities(
        self,
        client_brief: ClientBrief,
        template_quantities: Dict[int, int],
        randomize: bool = True,
        platform: Platform = Platform.LINKEDIN,
        use_client_memory: bool = True,
    ) -> List[Post]:
        """
        Generate posts using exact template quantities (sync version).

        This method generates posts based on the exact quantities specified for each template,
        rather than using equal distribution across all templates.

        Args:
            client_brief: Client brief with context
            template_quantities: Dict mapping template_id -> quantity (e.g., {1: 3, 2: 5, 9: 2})
            randomize: Whether to randomize post order
            platform: Target platform for content generation
            use_client_memory: Whether to use client memory for optimization

        Returns:
            List of generated Post objects

        Example:
            template_quantities = {1: 3, 2: 5, 9: 2}  # 10 total posts
            # Generates: 3 posts from template 1, 5 from template 2, 2 from template 9
        """
        # SECURITY: Sanitize client brief before processing (TR-014)
        try:
            sanitized_brief = self._sanitize_client_brief(client_brief)
        except ValueError as e:
            logger.error(f"Prompt injection detected, aborting generation: {e}")
            raise

        # Load client memory if available and enabled
        client_memory = None
        if use_client_memory and self.db:
            client_memory = self.db.get_client_memory(sanitized_brief.company_name)

        # Cache system prompt and base context for reuse (using sanitized brief)
        cached_system_prompt = self._build_system_prompt(sanitized_brief, platform, client_memory)
        base_context = sanitized_brief.to_context_dict()

        # Generate posts according to specified quantities
        posts = []
        post_number = 1

        # Iterate through template quantities
        for template_id, quantity in template_quantities.items():
            # Get template by ID
            template = self.template_loader.get_template_by_id(template_id)
            if not template:
                logger.warning(f"Template ID {template_id} not found, skipping {quantity} posts")
                continue

            # Generate specified quantity for this template
            for variant in range(1, quantity + 1):
                post = self._generate_single_post(
                    template=template,
                    client_brief=sanitized_brief,  # SECURITY FIX: Use sanitized brief (TR-014)
                    variant=variant,
                    post_number=post_number,
                    cached_system_prompt=cached_system_prompt,
                    base_context=base_context,
                    platform=platform,
                )
                posts.append(post)
                log_post_generated(post_number, template.name, post.word_count)
                post_number += 1

        # Randomize order for variety
        if randomize:
            random.shuffle(posts)
            logger.info("Randomized post order for variety")

        logger.info(f"Successfully generated {len(posts)} posts from template quantities")
        return posts

    async def _generate_posts_from_quantities_async(
        self,
        client_brief: ClientBrief,
        template_quantities: Dict[int, int],
        randomize: bool = True,
        max_concurrent: int = 5,
        platform: Platform = Platform.LINKEDIN,
        use_client_memory: bool = True,
    ) -> List[Post]:
        """
        Generate posts using exact template quantities (async version).

        This method generates posts based on the exact quantities specified for each template,
        using parallel API calls for improved performance.

        Args:
            client_brief: Client brief with context
            template_quantities: Dict mapping template_id -> quantity (e.g., {1: 3, 2: 5, 9: 2})
            randomize: Whether to randomize post order
            max_concurrent: Maximum concurrent API calls (default 5)
            platform: Target platform for content generation
            use_client_memory: Whether to use client memory for optimization

        Returns:
            List of generated Post objects

        Example:
            template_quantities = {1: 3, 2: 5, 9: 2}  # 10 total posts
            # Generates: 3 posts from template 1, 5 from template 2, 2 from template 9
        """
        # SECURITY: Sanitize client brief before processing (TR-014)
        try:
            sanitized_brief = self._sanitize_client_brief(client_brief)
        except ValueError as e:
            logger.error(f"Prompt injection detected, aborting generation: {e}")
            raise

        # Load client memory if available and enabled
        client_memory = None
        if use_client_memory and self.db:
            client_memory = self.db.get_client_memory(sanitized_brief.company_name)

        # Cache system prompt and base context for reuse (using sanitized brief)
        cached_system_prompt = self._build_system_prompt(sanitized_brief, platform, client_memory)
        base_context = sanitized_brief.to_context_dict()

        # Pre-fetch web search results for data-driven templates (max MAX_SEARCHES_PER_RUN per run)
        # Done before parallel generation to avoid concurrent duplicate searches.
        # Falls back silently — never blocks generation.
        web_search_cache: Dict[int, Optional[str]] = {}
        if WEB_SEARCH_CONTEXT_AVAILABLE and build_web_search_context is not None:
            search_count = 0
            industry = getattr(sanitized_brief, "industry", None)
            for tid in template_quantities:
                if tid not in TEMPLATE_WEB_SEARCH_CONFIG or tid in web_search_cache:
                    continue
                if search_count >= MAX_SEARCHES_PER_RUN:
                    logger.info(
                        f"Web search cap ({MAX_SEARCHES_PER_RUN}) reached — "
                        f"remaining templates will generate without live data"
                    )
                    break
                result = build_web_search_context(tid, industry)
                web_search_cache[tid] = result
                if result:
                    search_count += 1
                    logger.info(f"Web search context ready for template {tid}")

        # Build list of post generation tasks
        tasks = []
        post_number = 1

        # Iterate through template quantities
        for template_id, quantity in template_quantities.items():
            # Enforce the per-template ceiling before making any API calls.
            if quantity > MAX_QUANTITY_PER_TEMPLATE:
                raise ValueError(
                    f"Template {template_id} requested {quantity} posts but the maximum is "
                    f"{MAX_QUANTITY_PER_TEMPLATE} per template per run. "
                    "Reduce the quantity or split across multiple runs."
                )

            # Get template by ID
            template = self.template_loader.get_template_by_id(template_id)
            if not template:
                logger.warning(f"Template ID {template_id} not found, skipping {quantity} posts")
                continue

            # Pre-sample unique angles for this template's batch so every post
            # in the run gets a distinct execution approach. Falls back gracefully
            # if the template_id is not yet in TEMPLATE_ANGLES (future templates).
            available_angles = TEMPLATE_ANGLES.get(template_id, [])
            if available_angles and quantity <= len(available_angles):
                selected_angles: List[str] = random.sample(available_angles, quantity)  # nosec B311
            else:
                # Graceful degradation: cycle through available angles if pool is
                # smaller than quantity (shouldn't happen given the cap above).
                selected_angles = [
                    available_angles[i % len(available_angles)] if available_angles else ""
                    for i in range(quantity)
                ]

            # Build a template-specific base context when web search results are available.
            # _build_context() copies base_context, so this is safe to share across variants.
            web_results = web_search_cache.get(template_id)
            template_base_ctx = (
                {**base_context, "web_search_results": web_results} if web_results else base_context
            )

            # Create one task per post, embedding the pre-sampled angle via a fresh
            # dict spread per task. The "_angle" sentinel key is consumed by
            # _build_context and never forwarded to the LLM as a raw context entry.
            for variant_idx, angle in enumerate(selected_angles):
                tasks.append(
                    {
                        "template": template,
                        "variant": variant_idx + 1,
                        "post_number": post_number,
                        "cached_system_prompt": cached_system_prompt,
                        "base_context": {**template_base_ctx, "_angle": angle},
                    }
                )
                post_number += 1

        # Warn if any template IDs were silently skipped (not found in loader)
        requested_total = sum(template_quantities.values())
        if len(tasks) < requested_total:
            skipped = requested_total - len(tasks)
            logger.warning(
                f"⚠️ {skipped} of {requested_total} requested posts will not be generated "
                f"because their template IDs were not found in the template library. "
                f"Check the template_quantities configuration."
            )

        # Generate posts in parallel with concurrency limit
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_limit(task_params):
            """Generate single post with concurrency limit via semaphore and quality retry"""
            async with semaphore:
                return await self._generate_single_post_with_retry_async(
                    template=task_params["template"],
                    client_brief=sanitized_brief,  # SECURITY FIX: Use sanitized brief (TR-014)
                    variant=task_params["variant"],
                    post_number=task_params["post_number"],
                    cached_system_prompt=task_params["cached_system_prompt"],
                    base_context=task_params["base_context"],
                    platform=platform,
                    max_attempts=10,  # Try up to 10 times for quality
                )

        # Execute all tasks in parallel
        posts = await asyncio.gather(*[generate_with_limit(task) for task in tasks])

        # Randomize order for variety
        if randomize:
            random.shuffle(posts)
            logger.info("Randomized post order for variety")

        logger.info(f"Successfully generated {len(posts)} posts from template quantities (async)")
        return posts

    def _generate_single_post(
        self,
        template: Template,
        client_brief: ClientBrief,
        variant: int,
        post_number: int,
        cached_system_prompt: Optional[str] = None,
        base_context: Optional[Dict[str, Any]] = None,
        platform: Platform = Platform.LINKEDIN,
    ) -> Post:
        """
        Generate a single post from a template

        Args:
            template: Template to use
            client_brief: Client context
            variant: Variant number (for creating different versions)
            post_number: Post number in sequence
            cached_system_prompt: Pre-built system prompt (for performance)
            base_context: Pre-built base context dictionary (for performance)

        Returns:
            Generated Post object
        """
        # Build context for template rendering
        context = self._build_context(client_brief, template, variant, base_context)

        # Inject platform into context (mirrors async path)
        context["target_platform"] = platform.value.upper()
        context["platform_length_requirement"] = get_platform_target_length(platform)

        # Use cached system prompt if available, otherwise build it
        # Note: When using cached prompt, platform info is already embedded from the cache
        system_prompt = cached_system_prompt or self._build_system_prompt(client_brief, platform)

        # Platform-specific template structure overrides (mirrors async path)
        if platform == Platform.TWITTER:
            _kw = getattr(client_brief, "keywords", None) or []
            _hashtag_rule = (
                f"End with one or more hashtags drawn from the client's keywords: {', '.join(_kw[:5])}"
                if _kw
                else "End with one or more relevant hashtags"
            )
            template_structure_to_use = f"""Write a single microblog post. HARD LIMIT: 280 characters. Target: 70-100 characters.

Template theme (use as inspiration only — do NOT follow its multi-part structure): {template.name}

Rules:
- One punchy sentence; two very short sentences only if unavoidable
- No paragraph breaks or line breaks
- Distil the template's core idea into one ultra-concise statement or hook
- {_hashtag_rule} — hashtags serve as the CTA for microblog format; hashtags like #ContentStrategy or #BookACall count as both discovery and call-to-action (count toward the 280-char limit)
- REQUIRED: at least one hashtag (#) must appear — posts without a hashtag will be rejected
- Count characters before outputting — rewrite from scratch if over 280"""
        elif platform == Platform.FACEBOOK:
            template_structure_to_use = f"""Write a Facebook post. Target: 10-15 words (40-80 characters). Maximum: 125 characters.

Template theme (use as inspiration only — do NOT follow its multi-part structure): {template.name}

Rules:
- Complete, self-contained observation or insight — no teasers
- Conversational and relatable tone
- End with a soft question or invitation if it fits naturally"""
        else:
            template_structure_to_use = template.structure

        # Blog posts need a larger token budget: 2000-word target + ~2000 tokens
        # of prompt leaves no headroom at the default 4096 cap.
        generation_max_tokens = 6000 if platform == Platform.BLOG else None

        # Generate post content via API
        try:
            content = self.client.generate_post_content(
                template_structure=template_structure_to_use,
                context=context,
                system_prompt=system_prompt,
                temperature=0.7,  # Balanced creativity
                max_tokens=generation_max_tokens,
            )

            # SECURITY: Validate output for prompt leakage (TR-014)
            if detect_prompt_leakage(content):
                logger.error(
                    f"Prompt leakage detected in generated post {post_number}. "
                    f"Flagging for manual review."
                )
                # Don't use the leaked content, create placeholder
                content = "[SECURITY: Content flagged for possible prompt leakage]"

            # Clean up content
            content = self._clean_post_content(content)

            # Create Post object
            post = Post(
                content=content,
                template_id=template.template_id,
                template_name=template.name,
                variant=variant,
                client_name=client_brief.company_name,
                target_platform=platform,
            )

            # Generate Twitter/X share copy for blog posts
            if platform == Platform.BLOG:
                post.twitter_share_copy = self._generate_twitter_share_copy(content)

            # Check if post needs review — pass generation platform explicitly so
            # the correct word-count limits apply even if post.target_platform is None
            self._check_quality_flags(post, template, client_brief, generation_platform=platform)

            # Mark story as used for this template+project if story context was injected
            _used_story_id = context.get("_story_id_for_template")
            if _used_story_id and self.backend_session and hasattr(client_brief, "project_id"):
                try:
                    from backend.services.story_service import story_service
                    from backend.services.template_prerequisites import TEMPLATE_IDS

                    _tmpl_slug = TEMPLATE_IDS.get(template.template_id, "")
                    story_service.mark_story_used_for_template(
                        self.backend_session,
                        story_id=_used_story_id,
                        template_name=_tmpl_slug,
                        project_id=client_brief.project_id or "",
                    )
                except Exception as _me:
                    logger.warning(f"Could not mark story {_used_story_id} as used: {_me}")

            return post

        except Exception as e:
            logger.error(
                f"Failed to generate post {post_number} with template {template.name}: {str(e)}",
                exc_info=True,
            )
            # Create placeholder post to maintain count
            post = Post(
                content=f"[ERROR: Failed to generate post - {str(e)}]",
                template_id=template.template_id,
                template_name=template.name,
                variant=variant,
                client_name=client_brief.company_name,
                target_platform=platform,
            )
            post.flag_for_review(f"Generation failed: {str(e)}")
            return post

    async def _generate_single_post_async(
        self,
        template: Template,
        client_brief: ClientBrief,
        variant: int,
        post_number: int,
        cached_system_prompt: Optional[str] = None,
        base_context: Optional[Dict[str, Any]] = None,
        platform: Platform = Platform.LINKEDIN,
        quality_feedback: Optional[str] = None,
    ) -> Post:
        """
        Generate a single post from a template (async version)

        Args:
            template: Template to use
            client_brief: Client context
            variant: Variant number (for creating different versions)
            post_number: Post number in sequence
            cached_system_prompt: Pre-built system prompt (for performance)
            base_context: Pre-built base context dictionary (for performance)

        Returns:
            Generated Post object
        """
        # Build context for template rendering
        context = self._build_context(client_brief, template, variant, base_context)

        # Inject platform into context so it appears in the rendered Client Context block
        # the LLM reads in the user message — not just buried in the system prompt.
        context["target_platform"] = platform.value.upper()
        context["platform_length_requirement"] = get_platform_target_length(platform)

        # Use cached system prompt if available, otherwise build it
        # Note: When using cached prompt, platform info is already embedded from the cache
        system_prompt = cached_system_prompt or self._build_system_prompt(client_brief, platform)

        # On retries, tailor the feedback to the actual failure reason so the model
        # knows what to fix. Wrong instruction → wasted retry.
        if quality_feedback:
            feedback_lower = quality_feedback.lower()
            if "too short" in feedback_lower:
                # Length failure — the model needs to write substantially more content.
                # Re-state the target length and explain how to expand, not just "try again".
                if platform == Platform.BLOG:
                    system_prompt = (
                        system_prompt
                        + f"\n\nREVISION REQUIRED: {quality_feedback}\n"
                        + "Your previous draft was too short. You MUST write a full blog article of at least 1500 words.\n"
                        + "Expand every section: add concrete examples, patient stories, data points, and actionable how-to steps.\n"
                        + "Add a Section 4 (case study or FAQ, 200-300 words) if needed to reach length.\n"
                        + "Do not submit until your word count is at least 1500 words."
                    )
                else:
                    system_prompt = (
                        system_prompt
                        + f"\n\nREVISION REQUIRED: {quality_feedback}\n"
                        + "Write a longer version that fully develops the idea with more detail and examples."
                    )
            elif "too long" in feedback_lower:
                system_prompt = (
                    system_prompt
                    + f"\n\nREVISION REQUIRED: {quality_feedback}\n"
                    + "Your previous draft was too long. Trim it: shorten examples to 1-2 sentences, "
                    + "cut any section that does not add new information, remove redundant paragraphs."
                )
            else:
                # Banned phrase or other issue — re-emit the full banned word list so the
                # model cannot simply swap one banned word for another.
                banned_words_str = ", ".join(f'"{w}"' for w in AI_TELL_PHRASES)
                system_prompt = (
                    system_prompt
                    + f"\n\nREVISION REQUIRED: Your previous draft was rejected: {quality_feedback}\n"
                    + f"Every word in this list is banned — do not use any of them:\n{banned_words_str}\n"
                    + "Write a completely new version using plain, direct, conversational language only."
                )

        # Platform-specific template structure overrides.
        # LinkedIn templates are multi-part and long-form; short-form platforms need a
        # different structure or the model ignores character limits and over-generates.
        if platform == Platform.BLOG:
            blog_template_structure = """Write a comprehensive, in-depth blog post that thoroughly explores the topic.
Your blog post should include:
- A compelling introduction that hooks readers and states the problem (200-300 words)
- 3-5 main sections (H2 headers) with concrete examples, data, and actionable insights
- A strong conclusion with key takeaways and an imperative CTA (1500-2000 words total, MINIMUM 800)

This is a blog post, not a social media post — depth and thoroughness matter. Cover the topic comprehensively."""
            template_structure_to_use = blog_template_structure
        elif platform == Platform.TWITTER:
            _kw = getattr(client_brief, "keywords", None) or []
            _hashtag_rule = (
                f"End with one or more hashtags drawn from the client's keywords: {', '.join(_kw[:5])}"
                if _kw
                else "End with one or more relevant hashtags"
            )
            template_structure_to_use = f"""Write a single microblog post. HARD LIMIT: 280 characters. Target: 70-100 characters.

Template theme (use as inspiration only — do NOT follow its multi-part structure): {template.name}

Rules:
- One punchy sentence; two very short sentences only if unavoidable
- No paragraph breaks or line breaks
- Distil the template's core idea into one ultra-concise statement or hook
- {_hashtag_rule} — hashtags serve as the CTA for microblog format; hashtags like #ContentStrategy or #BookACall count as both discovery and call-to-action (count toward the 280-char limit)
- REQUIRED: at least one hashtag (#) must appear — posts without a hashtag will be rejected
- Count characters before outputting — rewrite from scratch if over 280"""
        elif platform == Platform.FACEBOOK:
            template_structure_to_use = f"""Write a Facebook post. Target: 10-15 words (40-80 characters). Maximum: 125 characters.

Template theme (use as inspiration only — do NOT follow its multi-part structure): {template.name}

Rules:
- Complete, self-contained observation or insight — no teasers
- Conversational and relatable tone
- End with a soft question or invitation if it fits naturally"""
        else:
            template_structure_to_use = template.structure

        # Blog posts need a larger token budget: 2000-word target + ~2000 tokens
        # of prompt leaves no headroom at the default 4096 cap.
        generation_max_tokens = 6000 if platform == Platform.BLOG else None

        # Generate post content via API (async)
        try:
            content = await self.client.generate_post_content_async(
                template_structure=template_structure_to_use,
                context=context,
                system_prompt=system_prompt,
                temperature=0.7,  # Balanced creativity
                max_tokens=generation_max_tokens,
                project_id=getattr(client_brief, "project_id", None),
            )

            # SECURITY: Validate output for prompt leakage (TR-014)
            if detect_prompt_leakage(content):
                logger.error(
                    f"Prompt leakage detected in generated post {post_number}. "
                    f"Flagging for manual review."
                )
                # Don't use the leaked content, create placeholder
                content = "[SECURITY: Content flagged for possible prompt leakage]"

            # Clean up content
            content = self._clean_post_content(content)

            # Create Post object
            post = Post(
                content=content,
                template_id=template.template_id,
                template_name=template.name,
                variant=variant,
                client_name=client_brief.company_name,
                target_platform=platform,
            )

            # Check if post needs review — pass generation platform explicitly
            self._check_quality_flags(post, template, client_brief, generation_platform=platform)

            # Log completion
            log_post_generated(post_number, template.name, post.word_count)

            return post

        except Exception as e:
            logger.error(
                f"Failed to generate post {post_number} with template {template.name}: {str(e)}",
                exc_info=True,
            )
            # Create placeholder post to maintain count
            post = Post(
                content=f"[ERROR: Failed to generate post - {str(e)}]",
                template_id=template.template_id,
                template_name=template.name,
                variant=variant,
                client_name=client_brief.company_name,
                target_platform=platform,
            )
            post.flag_for_review(f"Generation failed: {str(e)}")
            return post

    async def _generate_single_post_with_retry_async(
        self,
        template: Template,
        client_brief: ClientBrief,
        variant: int,
        post_number: int,
        cached_system_prompt: Optional[str] = None,
        base_context: Optional[Dict[str, Any]] = None,
        platform: Platform = Platform.LINKEDIN,
        max_attempts: int = 10,
    ) -> Post:
        """
        Generate a single post with quality-based retry logic.

        Attempts up to max_attempts times, caching all results.
        Returns first post with no quality flags, or best of all attempts.

        Args:
            template: Template to use
            client_brief: Client context
            variant: Variant number
            post_number: Post number in sequence
            cached_system_prompt: Pre-built system prompt
            base_context: Pre-built base context
            platform: Target platform
            max_attempts: Maximum generation attempts (default 10)

        Returns:
            Generated Post object (either first adequate or best of attempts)
        """
        attempts: list[dict[str, Any]] = []
        last_review_reason: Optional[str] = None

        for attempt in range(max_attempts):
            # Generate post — pass quality feedback from previous attempt on retries
            post = await self._generate_single_post_async(
                template=template,
                client_brief=client_brief,
                variant=variant,
                post_number=post_number,
                cached_system_prompt=cached_system_prompt,
                base_context=base_context,
                platform=platform,
                quality_feedback=last_review_reason,
            )

            # Calculate quality score based on flags and metrics
            quality_score = self._calculate_post_quality_score(post)

            # Cache attempt
            attempts.append(
                {
                    "post": post,
                    "quality_score": quality_score,
                    "has_flags": post.needs_review,
                    "attempt_number": attempt + 1,
                }
            )

            # If post has no quality flags, it's adequate - return immediately
            if not post.needs_review:
                logger.info(
                    f"Post {post_number} passed quality check on attempt {attempt + 1}/{max_attempts} "
                    f"(quality score: {quality_score:.2%})"
                )
                return post

            # Capture reason for next attempt's feedback
            last_review_reason = post.review_reason

            # Log retry
            logger.info(
                f"Post {post_number} attempt {attempt + 1}/{max_attempts} has quality issues: {post.review_reason}. "
                f"Retrying..."
                if attempt < max_attempts - 1
                else "Max attempts reached."
            )

        # No adequate result - return best attempt
        best = max(attempts, key=lambda x: x["quality_score"])
        best_post: Post = best["post"]
        logger.warning(
            f"Post {post_number} did not meet quality standards after {max_attempts} attempts. "
            f"Returning best attempt (#{best['attempt_number']}, quality score: {best['quality_score']:.2%}, "
            f"review reason: {best_post.review_reason if best_post.review_reason else 'none'})"
        )

        return best_post

    def _calculate_post_quality_score(self, post: Post) -> float:
        """
        Calculate a quality score for a post based on various metrics.

        Returns a score from 0.0 to 1.0 where:
        - 1.0 = perfect (no flags, good length, has CTA)
        - 0.0 = very poor (multiple flags, bad length, no CTA)
        """
        score = 1.0

        # Penalize if post needs review (0.2 penalty)
        if post.needs_review:
            score -= 0.2

        # Reward for appropriate word count (within target range)
        if post.word_count:
            if MIN_POST_WORD_COUNT <= post.word_count <= MAX_POST_WORD_COUNT:
                # Perfect length
                pass
            elif post.word_count < MIN_POST_WORD_COUNT * 0.8:
                # Very short
                score -= 0.2
            elif post.word_count > MAX_POST_WORD_COUNT * 1.2:
                # Very long
                score -= 0.2
            else:
                # Slightly off
                score -= 0.1

        # Reward for having CTA
        if not post.has_cta:
            score -= 0.1

        # Ensure score stays in valid range
        return max(0.0, min(1.0, score))

    def _sanitize_client_brief(self, client_brief: ClientBrief) -> ClientBrief:
        """
        Sanitize client brief to prevent prompt injection attacks (TR-014)

        This method removes or escapes malicious patterns from all user-provided
        fields before they are included in prompts sent to the LLM.

        Security: Protects against OWASP LLM01 - Prompt Injection

        Args:
            client_brief: Original client brief with potentially unsafe input

        Returns:
            Sanitized client brief safe for use in prompts

        Raises:
            ValueError: If critical prompt injection detected
        """
        from copy import deepcopy

        # Create a copy to avoid mutating original
        sanitized = deepcopy(client_brief)

        # Sanitize all user-provided text fields
        try:
            # Core business fields
            sanitized.business_description = sanitize_prompt_input(
                client_brief.business_description, strict=False
            )
            sanitized.ideal_customer = sanitize_prompt_input(
                client_brief.ideal_customer, strict=False
            )
            sanitized.main_problem_solved = sanitize_prompt_input(
                client_brief.main_problem_solved, strict=False
            )

            # Optional fields (only sanitize if present)
            if client_brief.customer_pain_points:
                sanitized.customer_pain_points = [
                    sanitize_prompt_input(point, strict=False)
                    for point in client_brief.customer_pain_points
                ]

            if client_brief.customer_questions:
                sanitized.customer_questions = [
                    sanitize_prompt_input(q, strict=False) for q in client_brief.customer_questions
                ]

            logger.debug(f"Sanitized client brief for {client_brief.company_name}")
            return sanitized

        except ValueError as e:
            logger.error(
                f"Critical prompt injection detected in client brief for {client_brief.company_name}: {e}"
            )
            raise ValueError(
                f"Client brief contains unsafe content that could not be sanitized. "
                f"Please review the input and remove any suspicious patterns: {str(e)}"
            )

    def _build_context(
        self,
        client_brief: ClientBrief,
        template: Template,
        variant: int,
        base_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build context dictionary for template rendering

        Args:
            client_brief: Client brief
            template: Template being used
            variant: Variant number
            base_context: Pre-built base context for performance

        Returns:
            Context dictionary
        """
        # Use cached base context if available, otherwise build it
        # Note: Sanitization should happen before caching in the calling code
        context = base_context.copy() if base_context else client_brief.to_context_dict()

        # Add research insights if available (Phase 2: Research Context Integration)
        if (
            RESEARCH_CONTEXT_AVAILABLE
            and self.backend_session
            and hasattr(client_brief, "client_id")
        ):
            try:
                research_context = build_research_context(
                    self.backend_session, client_brief.client_id
                )
                if research_context.get("formatted_text"):
                    context["research_insights"] = research_context["formatted_text"]
                    logger.info(
                        f"Added research context: {research_context['tool_count']} tools, "
                        f"~{research_context['total_tokens']} tokens"
                    )
            except Exception as e:
                logger.warning(f"Could not add research context: {e}")

        # Add variant-specific guidance.
        # If a pre-sampled angle was embedded into base_context by the task builder,
        # consume it here and use it directly. The "_angle" sentinel is popped so it
        # never appears as a raw key in the serialised prompt context.
        _injected_angle: str = context.pop("_angle", "")
        if _injected_angle:
            context["variant_guidance"] = _injected_angle
        elif variant == 1:
            context["variant_guidance"] = "Use a direct, problem-focused angle"
        elif variant == 2:
            context["variant_guidance"] = "Use a story-driven or example-based angle"
        else:
            context["variant_guidance"] = "Use a unique angle different from previous variants"

        # Add template-specific context
        context["template_type"] = template.template_type.value
        context["requires_story"] = template.requires_story
        context["requires_data"] = template.requires_data

        # FIX (Bug #42): Add measurable_results for data-driven templates
        # Template 2 (Statistic), 7 (Myth-busting), 13 (Future-thinking)
        # Note: measurable_results already in base context from to_context_dict() as "results"
        # This is just adding a reminder for data-driven templates
        if template.requires_data and context.get("results"):
            context["use_measurable_results"] = (
                "YES - incorporate the results listed above into your content"
            )

        # Web search guidance: explicit per-template instruction covering both
        # the "data present" and "data absent" cases so the model always knows
        # what to do rather than relying only on the system-prompt guidance.
        _WEB_SEARCH_TEMPLATE_GUIDANCE: Dict[int, str] = {
            2: (  # Statistic + Insight
                "WEB SEARCH GUIDANCE (Template 2 — Statistic + Insight): "
                "If web_search_results are present above, open with one specific, "
                "citable statistic from those results and cite the source naturally. "
                "If NO web search results are present, anchor to a concrete number "
                "from the client's own measurable_results (the 'results' field above) "
                "or state 'industry data shows' with a plausible directional claim — "
                "never fabricate a precise percentage or dollar figure."
            ),
            3: (  # Contrarian Take
                "WEB SEARCH GUIDANCE (Template 3 — Contrarian Take): "
                "If web_search_results are present above, open with a REAL mainstream "
                "claim or conventional wisdom pulled from those results — quote or "
                "paraphrase it, then challenge it with the client's experience. "
                "If NO web search results are present, state a commonly-held belief "
                "in the client's industry as the foil (e.g., 'Everyone says X…') "
                "and challenge it using data or stories from the brief."
            ),
            13: (  # Future Thinking
                "WEB SEARCH GUIDANCE (Template 13 — Future Thinking): "
                "If web_search_results are present above, ground your predictions in "
                "one or two specific trends named in those results and cite them. "
                "If NO web search results are present, use the market_trends research "
                "data above (if available) or make directional predictions tied to "
                "observable patterns the client describes — avoid specific year-over-year "
                "figures you cannot verify."
            ),
        }
        if template.template_id in _WEB_SEARCH_TEMPLATE_GUIDANCE:
            context["web_search_guidance"] = _WEB_SEARCH_TEMPLATE_GUIDANCE[template.template_id]

        # FIX (Bug #42): Add competitors for comparison template (Template 10)
        if template.template_id == 10 and context.get("competitors"):
            context["comparison_guidance"] = (
                "Use the competitors list above to create a detailed comparison"
            )

        # Inject story context for story-based templates (6=personal_story, 8=things_i_got_wrong, 15=milestone)
        _STORY_TEMPLATE_IDS = {6, 8, 15}
        if (
            RESEARCH_CONTEXT_AVAILABLE
            and get_story_context_for_template is not None
            and template.template_id in _STORY_TEMPLATE_IDS
            and self.backend_session
            and hasattr(client_brief, "client_id")
            and hasattr(client_brief, "project_id")
        ):
            try:
                from backend.services.template_prerequisites import TEMPLATE_IDS

                _tmpl_slug = TEMPLATE_IDS.get(template.template_id, "")
                _story_ctx = get_story_context_for_template(
                    self.backend_session,
                    client_brief.client_id,
                    _tmpl_slug,
                    client_brief.project_id or "",
                )
                if _story_ctx["formatted_text"]:
                    context["story_context"] = _story_ctx["formatted_text"]
                    context["_story_id_for_template"] = _story_ctx["story_id"]
            except Exception as _se:
                logger.warning(
                    f"Could not inject story context for template {template.template_id}: {_se}"
                )

        return context

    def _build_system_prompt(
        self,
        client_brief: ClientBrief,
        platform: Platform = Platform.LINKEDIN,
        client_memory: Optional[ClientMemory] = None,
    ) -> str:
        """Build customized system prompt for client with platform-specific guidance

        Args:
            client_brief: Client brief with context
            platform: Target platform for content generation
            client_memory: Optional client memory for repeat client optimization

        Returns:
            Customized system prompt string
        """
        # Start with base prompt
        prompt = self.SYSTEM_PROMPT

        # Add platform-specific guidance with enhanced emphasis
        platform_guidance = get_platform_prompt_guidance(platform)
        target_length = get_platform_target_length(platform)
        # Add prominent platform header
        prompt += f"\n\n{'=' * 60}"
        prompt += f"\nPLATFORM-SPECIFIC REQUIREMENTS FOR {platform.value.upper()}"
        prompt += f"\n{'=' * 60}"
        prompt += f"\n\nTARGET LENGTH: **{target_length}** (STRICTLY ENFORCE THIS)"

        # Add critical length enforcement for platforms with tight limits
        if platform == Platform.TWITTER:
            prompt += """

🚨 TWITTER ULTRA-CONCISE REQUIREMENTS (STRICTLY ENFORCE):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. MAXIMUM 280 characters total (HARD LIMIT - will FAIL if exceeded)
2. Aim for 70-100 characters for standalone posts
3. Single sentence preferred; two very short sentences only if needed
4. NO paragraph breaks, NO line breaks
5. NO explanations, backstory, or setup
6. Make EVERY character count - remove filler aggressively

EXAMPLES OF CORRECT LENGTH:
✓ "Systems break when teams juggle too many tools." (47 chars)
✓ "Tool chaos costs teams hours every week. Simplify the stack." (61 chars)
✓ "Your process is slower than it should be. Fix the bottlenecks." (65 chars)
✗ "I've been tracking this across 200+ engineering teams and the data clearly shows..." (WRONG - too long)

CRITICAL: If your draft exceeds 100 characters for a standalone tweet, rewrite it shorter.
If it exceeds 280 characters at any point, DO NOT OUTPUT. Rewrite from scratch.
Think: billboard, not paragraph. Punchy, not explanatory.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        elif platform == Platform.FACEBOOK:
            prompt += """

📘 FACEBOOK POST REQUIREMENTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TARGET: 10-15 words (40-80 characters) for standalone posts

CRITICAL: Write a COMPLETE, self-contained post.
Do NOT write a teaser or headline that implies more content follows.
❌ WRONG: "Here's what top teams do differently." (too vague and incomplete)
❌ WRONG: "Most teams make this mistake. Here's the fix." (teaser with no follow-through)
✓ RIGHT: Deliver the actual insight, story, or value IN the post itself.

STRUCTURE:
1. Hook (1 sentence) — relatable observation or bold statement
2. Core insight or story (2-3 sentences) — the actual point, not a promise of it
3. CTA (1 sentence) — question, invitation to comment, or soft next step

EXAMPLE:
"Most content teams burn time on the wrong posts.
They plan by volume — 30 posts per month — instead of planning by impact.
The fix is simple: identify the 3 topics your audience actually asks about, then write 10 posts on those. Everything else is noise.
What's the #1 topic your clients keep asking you about? Drop it below."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        # Add full platform-specific writing guidelines
        prompt += f"\n\n{platform_guidance}"

        # Add LinkedIn-specific length requirements
        if platform == Platform.LINKEDIN:
            prompt += """

📏 LINKEDIN LENGTH REQUIREMENTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MINIMUM: 200 words (posts under 200 will FAIL validation)
OPTIMAL: 220-280 words (best engagement range)
MAXIMUM: 300 words (do not exceed)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL: First 140 characters must contain your key message (mobile cutoff)

If your first draft is 150-199 words, ADD:
- One more supporting point or example
- A relevant statistic or data point
- A brief anecdote or scenario
- Additional context or background

Aim for 220-250 words for optimal engagement.
"""

        # Add blog-specific structure requirements
        elif platform == Platform.BLOG:
            prompt += """

📝 BLOG POST LENGTH GUIDELINES:
🎯 TARGET RANGE: 1500-2000 words for optimal SEO performance
💯 SWEET SPOT: 1700-1800 words (ideal engagement + SEO)
⚠️  MINIMUM: 800 words (posts under 800 fail validation)

RECOMMENDED 5-SECTION STRUCTURE (aim for full depth in each section):

## Introduction (200-300 words) [CHECKPOINT: ~250 words]
- Powerful hook: a compelling statistic, question, or relatable scenario (2-3 sentences)
- Clearly state the problem your audience faces (1 paragraph)
- Preview the specific value/solutions readers will learn (1 paragraph)
- Include a concrete example or real data point to build credibility

## Section 1: [Core Concept/Problem Deep-Dive] (300-400 words) [CHECKPOINT: ~600 words total]
- H2 header clearly describing this section
- 3-4 substantial paragraphs breaking down the problem or concept
- Include 2-3 specific examples with real numbers or names
- Add bullet points or numbered lists to structure information
- Cite relevant data/statistics (at least 1-2 data points)

## Section 2: [Framework/Approach] (300-400 words) [CHECKPOINT: ~1000 words total]
- H2 header describing your solution framework
- Break down complex concepts with step-by-step explanations
- Use real-world examples from recognizable companies/situations
- Address common objections or questions preemptively
- Include actionable insights, not just theory

## Section 3: [Implementation/How-To] (300-400 words) [CHECKPOINT: ~1400 words total]
- H2 header focused on practical application
- Provide detailed "how-to" steps (numbered list of 3-5 steps)
- Each step should have 2-3 sentences of explanation
- Include specific tools, resources, or templates
- Add "what to avoid" warnings or common mistakes

## Conclusion (200-300 words) [FINAL CHECKPOINT: 1500-2000 words total]
- Summarize 3-5 key takeaways (each with 1 sentence of explanation)
- Reinforce the main benefit and transformation available
- Clear, specific CTA using IMPERATIVE form (command, not question)
  Examples: "Subscribe now", "Download the guide", "Book your call today"
  NOT questions like: "Want to learn more?" or "Ready to get started?"
- End with a forward-looking statement about what's possible

🚨 CRITICAL WRITING REQUIREMENTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ MINIMUM 1500 words total (count your words before submitting)
✓ Include 4-5 H2 headers (## format)
✓ Use concrete examples with specific numbers/names/companies
✓ Include data/statistics in at least 3 sections
✓ Front-load key message in first 2 paragraphs for SEO
✓ Write for search intent + readability (not just engagement)
✓ Use bullet points and numbered lists to break up text
✓ Short paragraphs — 2-3 sentences max

PRE-OUTPUT LENGTH CHECK (MANDATORY):
Before returning your blog post, count the words mentally:
- If under 1500 words → DO NOT OUTPUT YET. Add one of: a Section 4 with a case study or FAQ (200-300 words), expand each section with one more concrete example, or add "what to avoid" warnings. Then recount.
- If over 2000 words → trim redundant paragraphs, shorten examples to 2-3 sentences, cut any section that does not add new information.
A post that is under 800 words FAILS quality validation and will be regenerated.
"""

        # Repeat length reminder at end for emphasis (platform-specific)
        if platform == Platform.BLOG:
            prompt += "\n\n📏 FINAL REMINDER: Target 1500–2000 words for best SEO. MINIMUM 800 words — if under 1500, add a case study section or expand examples before submitting. Aim for depth and substance."
        else:
            prompt += f"\n\n📏 REMINDER: Target length is {target_length}. DO NOT EXCEED THIS."

        # Add client-specific voice guidance
        if client_brief.brand_personality:
            # brand_personality is List[str], not List[Enum]
            personalities = ", ".join(client_brief.brand_personality)
            prompt += f"\n\nCLIENT VOICE: This client is {personalities}."

        if client_brief.key_phrases:
            phrases = '", "'.join(client_brief.key_phrases)
            prompt += f'\n\nKEY PHRASES TO USE: "{phrases}"'

        if client_brief.misconceptions:
            avoid = ", ".join(client_brief.misconceptions)
            prompt += f"\n\nCOMMON MISCONCEPTIONS TO ADDRESS: {avoid}"

        # FIX (Bug #42): Add tone_preference usage - previously only used for template selection
        if client_brief.tone_preference:
            tone_guidance = {
                "professional": "polished, credible, authoritative",
                "conversational": "friendly, approachable, relatable",
                "authoritative": "confident, expert, commanding",
                "friendly": "warm, personable, welcoming",
                "innovative": "forward-thinking, creative, bold",
                "educational": "clear, informative, instructive",
            }
            tone_key = client_brief.tone_preference.value
            if tone_key in tone_guidance:
                prompt += f"\n\nTONE: Write in a {tone_key} tone ({tone_guidance[tone_key]})."

        # FIX (Bug #42): Add data_preference usage - previously added to context but never used
        if client_brief.data_usage:
            if client_brief.data_usage.value == "heavy":
                prompt += "\n\nDATA USAGE: Include statistics, data points, and metrics throughout the post to support claims."
            elif client_brief.data_usage.value == "minimal":
                prompt += "\n\nDATA USAGE: Minimize statistics - focus on stories, examples, and narrative. Use data sparingly."

        # FIX (Bug #42): Add industry context - previously collected but not added to context
        if client_brief.industry:
            prompt += f"\n\nINDUSTRY CONTEXT: {client_brief.industry}"

        # NEW: Add client memory insights for repeat clients
        if client_memory and client_memory.is_repeat_client:
            prompt += f"\n\n[CLIENT HISTORY]: This is a repeat client with {client_memory.total_projects} previous project(s)."

            # Add voice adjustments from past feedback
            if client_memory.voice_adjustments:
                prompt += "\n\nLEARNED PREFERENCES (from past feedback):"
                for adj_type, adj_value in client_memory.voice_adjustments.items():
                    prompt += f"\n  • {adj_type.replace('_', ' ').title()}: {adj_value}"

            # Add signature phrases
            if client_memory.signature_phrases:
                phrases = '", "'.join(client_memory.signature_phrases)
                prompt += f'\n\nCLIENT SIGNATURE PHRASES (use naturally): "{phrases}"'

            # Add optimal word count guidance
            if client_memory.optimal_word_count_min and client_memory.optimal_word_count_max:
                prompt += f"\n\nOPTIMAL LENGTH FOR THIS CLIENT: {client_memory.optimal_word_count_min}-{client_memory.optimal_word_count_max} words (based on past successful posts)"

        # Add SEO keyword guidance if available
        if self.keyword_strategy:
            prompt += self._build_keyword_guidance()

        # NEW: Add brand archetype guidance
        archetype = self._infer_archetype(client_brief)
        if archetype:
            archetype_guidance = get_archetype_guidance(archetype)
            prompt += f"\n{archetype_guidance}"

        # NEW: Add professional writing principles
        writing_principles = get_writing_principles_guidance()
        prompt += f"\n{writing_principles}"

        # NEW: Add hook copywriting frameworks (from hook-creator skill)
        # Infer template type from context for framework selection
        template_type = self._infer_template_type_for_hooks(client_brief)
        hook_guidance = build_hook_guidance(
            template_type=template_type,
            platform=platform.value,
            include_examples=True,
        )
        prompt += hook_guidance

        # NEW: Add content-creator skill guidance if available
        skill_guidance = self._build_skill_guidance(platform)
        if skill_guidance:
            prompt += skill_guidance

        # Phase 5: Add research insights guidance if available
        if RESEARCH_CONTEXT_AVAILABLE and self.backend_session:
            prompt += """

RESEARCH INSIGHTS GUIDANCE:
The context may include research insights from completed research tools for this client.
If research insights are present, use them to:
- Match the identified voice patterns and readability level
- Naturally integrate recommended keywords where relevant
- Address identified content gaps and differentiation opportunities
- Align with the brand archetype and audience preferences

IMPORTANT: Do NOT explicitly mention the research tools or insights in your content.
Instead, let them inform your writing style, topic selection, and messaging naturally.
Think of research insights as your secret knowledge about the client - use them subtly.
"""

        # Add web search data guidance when the feature is active
        if WEB_SEARCH_CONTEXT_AVAILABLE:
            prompt += """

WEB SEARCH DATA GUIDANCE:
The context may include a "web_search_results" block containing live web data fetched at generation time.
If web_search_results are present:
- Use ONLY specific statistics, claims, or trends from those results — do not fabricate data
- Cite the source naturally ("According to [source]..." or "Recent data shows...")
- Prefer data points that are surprising, specific, or counterintuitive
- If the data does not directly match the client's situation, adapt the insight conceptually

If web_search_results are NOT present in the context, do not invent statistics.
Use the client's own measurable results and data from their brief instead.
"""

        # Add banned word list — injected as a hard writing constraint, not a process note,
        # so the model treats avoidance as a content rule rather than a downstream concern.
        banned_words_str = ", ".join(f'"{w}"' for w in AI_TELL_PHRASES)
        prompt += f"""

HARD WRITING RULE — NEVER USE THESE WORDS OR PHRASES:
{banned_words_str}

Do not use any of the above, even in passing. They are AI clichés that will cause the post to be rejected and regenerated. Write in plain, direct, conversational language. Say exactly what you mean — no corporate buzzwords, no marketing speak, no motivational filler."""

        return prompt

    def _build_skill_guidance(self, platform: Platform = Platform.LINKEDIN) -> str:
        """
        Build guidance from the content-creator skill's reference materials.

        Extracts relevant sections from brand guidelines, content frameworks,
        and social media optimization references.

        Args:
            platform: Target platform for content generation

        Returns:
            Skill-based guidance string, or empty string if skill not loaded
        """
        if not self.content_skill:
            return ""

        lines = ["\n\n" + "=" * 60]
        lines.append("PROFESSIONAL CONTENT CREATION GUIDELINES (from content-creator skill)")
        lines.append("=" * 60)

        # Extract brand guidelines summary
        brand_guide = self.content_skill.get_reference("brand_guidelines")
        if brand_guide:
            # Extract key sections (first 500 chars of relevant sections)
            lines.append("\n**BRAND VOICE BEST PRACTICES:**")
            if "Voice Dimensions" in brand_guide:
                # Extract a brief section
                lines.append("- Consider formality level appropriate for audience")
                lines.append("- Maintain consistent tone throughout")
                lines.append("- Match perspective to brand personality")

        # Extract content framework guidance based on platform
        content_frameworks = self.content_skill.get_reference("content_frameworks")
        if content_frameworks:
            lines.append("\n**CONTENT STRUCTURE PRINCIPLES:**")
            lines.append("- Hook first, value second, CTA last")
            lines.append("- Use scannable formatting (bullets, short paragraphs)")
            lines.append("- Include concrete examples and data points")

        # Extract platform-specific optimization if available
        social_opt = self.content_skill.get_reference("social_media_optimization")
        if social_opt:
            lines.append(f"\n**{platform.value.upper()} OPTIMIZATION (from skill):**")

            if platform == Platform.LINKEDIN:
                lines.append("- First line must hook (visible before 'see more')")
                lines.append("- Use line breaks for readability")
                lines.append("- End with clear imperative CTA (command, NOT question)")
                lines.append("- Optimal posting: Tue-Thu 8-10am, 12pm, 5-6pm")
            elif platform == Platform.TWITTER:
                lines.append("- Front-load value in first sentence")
                lines.append("- Use strong verbs, remove filler words")
                lines.append("- Hashtags: 1-2 max, placed at end")
            elif platform == Platform.FACEBOOK:
                lines.append("- Visual-first approach (assume image accompanies)")
                lines.append("- Emotional or curiosity-driven hooks")
                lines.append("- Keep text brief, let visual do heavy lifting")
            elif platform == Platform.BLOG:
                lines.append("- SEO: Include primary keyword in first 100 words")
                lines.append("- Structure: H2s every 300-400 words")
                lines.append("- Internal/external links for authority")
                lines.append("- Meta description: 150-160 chars with keyword")

        lines.append("\n" + "-" * 40)

        return "\n".join(lines)

    def _build_keyword_guidance(self) -> str:
        """Build SEO keyword guidance section for system prompt"""
        if not self.keyword_strategy:
            return ""

        lines = ["\n\nSEO KEYWORD INTEGRATION:"]
        lines.append("Naturally integrate these keywords when relevant (DO NOT force or stuff):")

        # Primary keywords (highest priority)
        if self.keyword_strategy.primary_keywords:
            primary_kws = [
                kw.keyword for kw in self.keyword_strategy.get_keywords_by_priority(max_priority=2)
            ]
            if primary_kws:
                lines.append("\n**Primary Keywords (aim for 1-2 per post):**")
                for kw in primary_kws[:5]:  # Top 5 primary
                    lines.append(f"- {kw}")

        # Secondary keywords
        if self.keyword_strategy.secondary_keywords:
            secondary_kws = [kw.keyword for kw in self.keyword_strategy.secondary_keywords[:10]]
            if secondary_kws:
                lines.append("\n**Secondary Keywords (use when contextually appropriate):**")
                for kw in secondary_kws[:5]:  # Show top 5
                    lines.append(f"- {kw}")

        lines.append(
            "\n**IMPORTANT:** Only use keywords where they fit naturally. Authenticity > SEO optimization."
        )

        return "\n".join(lines)

    def _infer_archetype(self, client_brief: ClientBrief) -> str:
        """
        Infer brand archetype from client brief.

        Uses client type classification as primary signal. If client has a
        classifier attribute, uses that. Otherwise, makes a simple inference
        from business description.

        Args:
            client_brief: Client brief with context

        Returns:
            Archetype name (Expert, Friend, Innovator, Guide, Motivator) or empty string
        """
        # Primary source: completed brand_archetype research for this client
        if (
            RESEARCH_CONTEXT_AVAILABLE
            and get_brand_archetype_from_research is not None
            and self.backend_session
            and hasattr(client_brief, "client_id")
        ):
            research_archetype = get_brand_archetype_from_research(
                self.backend_session, client_brief.client_id
            )
            if research_archetype:
                logger.info(f"Using brand_archetype from research: '{research_archetype}'")
                return research_archetype

        # Fallback: client type classification
        client_type = getattr(client_brief, "client_type", None)

        if client_type:
            # Convert ClientType enum to string if needed
            client_type_str = (
                client_type.value if hasattr(client_type, "value") else str(client_type)
            )
            archetype = get_archetype_from_client_type(client_type_str.upper())
            logger.info(f"Inferred archetype '{archetype}' from client type '{client_type_str}'")
            return archetype

        # Fallback: Simple keyword-based inference from business description
        business_desc = client_brief.business_description.lower()

        # B2B/SaaS indicators -> Expert
        if any(
            word in business_desc for word in ["saas", "software", "b2b", "enterprise", "analytics"]
        ):
            logger.info("Inferred archetype 'Expert' from business description keywords")
            return "Expert"

        # Coaching/consulting indicators -> Guide
        if any(
            word in business_desc for word in ["coach", "consultant", "training", "mentor", "guide"]
        ):
            logger.info("Inferred archetype 'Guide' from business description keywords")
            return "Guide"

        # Creator/founder indicators -> Friend
        if any(
            word in business_desc for word in ["creator", "founder", "community", "personal brand"]
        ):
            logger.info("Inferred archetype 'Friend' from business description keywords")
            return "Friend"

        # Default: Guide (safe, versatile archetype)
        logger.info("No clear archetype signals - defaulting to 'Guide'")
        return "Guide"

    def _infer_template_type_for_hooks(self, client_brief: ClientBrief) -> str:
        """
        Infer a template type for hook framework selection.

        This method analyzes the client brief to determine which hook frameworks
        would be most appropriate. Returns a template type that maps to
        recommended hook frameworks.

        Args:
            client_brief: Client brief with context

        Returns:
            Template type string (e.g., "problem_recognition", "how_to")
        """
        business_desc = client_brief.business_description.lower()
        pain_points = (
            " ".join(client_brief.customer_pain_points).lower()
            if client_brief.customer_pain_points
            else ""
        )

        # Check for problem-focused content
        if any(
            word in business_desc or word in pain_points
            for word in ["problem", "struggle", "challenge", "pain"]
        ):
            return "problem_recognition"

        # Check for how-to content
        if any(word in business_desc for word in ["how to", "guide", "step", "process", "method"]):
            return "how_to"

        # Check for comparison/competitive content
        if any(
            word in business_desc
            for word in ["vs", "versus", "compare", "alternative", "better than"]
        ):
            return "comparison"

        # Check for innovation/future content
        if any(
            word in business_desc for word in ["innovate", "future", "trend", "next", "transform"]
        ):
            return "future_thinking"

        # Check for data-driven content
        if any(
            word in business_desc
            for word in ["data", "analytics", "metric", "measure", "roi", "percent"]
        ):
            return "statistic_insight"

        # Default to problem recognition (most versatile)
        return "problem_recognition"

    def _clean_post_content(self, content: str) -> str:
        """Clean and normalize post content"""
        # Remove markdown formatting if present
        content = content.strip()

        # Remove any leading/trailing quotes
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]

        # Remove markdown headers
        content = content.replace("# ", "").replace("## ", "")

        # Normalize line breaks (max 2 consecutive)
        content = re.sub(r"\n{3,}", "\n\n", content)

        return content.strip()

    @staticmethod
    def _generate_twitter_share_copy(content: str) -> str:
        """
        Build a ready-to-post tweet to drive traffic to a blog post.

        Strategy:
        - Extract the first sentence (up to 180 chars) as the hook
        - Append the [YOUR_BLOG_URL] placeholder
        - Keep total ≤ 240 chars (Twitter counts t.co URLs as 23 chars,
          but we leave extra room for the real URL)

        Returns a non-empty string always (falls back to a generic prompt).
        """
        import re

        MAX_HOOK_CHARS = 180
        URL_PLACEHOLDER = "[YOUR_BLOG_URL]"

        # Extract first sentence — split on ". " or ".\n" or end of string
        sentences = re.split(r"(?<=\.)\s+|\n", content.strip())
        hook = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) >= 20:  # skip very short fragments
                hook = sentence
                break

        if not hook:
            hook = content.strip()

        # Truncate hook to MAX_HOOK_CHARS
        if len(hook) > MAX_HOOK_CHARS:
            # Try to cut at the last word boundary
            truncated = hook[:MAX_HOOK_CHARS].rsplit(" ", 1)[0]
            hook = truncated.rstrip(".,;:") + "..."

        tweet = f"{hook}\n\n{URL_PLACEHOLDER}"

        # Final safety truncation (should never trigger with MAX_HOOK_CHARS=180)
        if len(tweet) > 280:
            tweet = tweet[:276] + "..."

        return tweet

    def _check_quality_flags(
        self,
        post: Post,
        template: Template,
        client_brief: ClientBrief,
        generation_platform: Optional[Platform] = None,
    ) -> None:
        """Check post for quality issues and flag if needed.

        generation_platform: the platform passed to the generator — used as the
        authoritative source for word-count limits instead of post.target_platform,
        which can be None if the Post object wasn't constructed with it yet.
        """
        content_lower = post.content.lower()

        # Check for AI tells using module constant
        for tell in AI_TELL_PHRASES:
            if tell in content_lower:
                post.flag_for_review(f"Contains AI tell: '{tell}'")
                return

        # Prefer the generation platform passed in; fall back to post.target_platform.
        # post.target_platform can be None when _check_quality_flags is called from
        # paths that don't set it, causing silent fallback to the LinkedIn defaults
        # (min 75 words) instead of the platform-specific minimum.
        platform = generation_platform or post.target_platform
        if platform and platform in PLATFORM_LENGTH_SPECS:
            specs = PLATFORM_LENGTH_SPECS[platform]
            min_words = specs["min_words"]
            max_words = specs["max_words"]
        else:
            min_words = MIN_POST_WORD_COUNT
            max_words = MAX_POST_WORD_COUNT

        logger.debug(
            f"Quality check: {post.word_count} words, platform={platform}, "
            f"min={min_words}, max={max_words}"
        )

        if post.word_count < min_words:
            post.flag_for_review(f"Post too short: {post.word_count} words (min: {min_words})")
            return

        if post.word_count > max_words:
            post.flag_for_review(f"Post too long: {post.word_count} words (max: {max_words})")
            return

        # Twitter/microblog posts use hashtags instead of CTAs
        if platform == Platform.TWITTER:
            if "#" not in post.content:
                post.flag_for_review("No hashtag detected in microblog post")
            return

        # Check if CTA is present when expected
        if not post.has_cta:
            post.flag_for_review("No clear CTA detected")
            return

    def generate_variant(
        self, original_post: Post, client_brief: ClientBrief, feedback: str
    ) -> Post:
        """
        Generate a variant of an existing post based on feedback

        Args:
            original_post: Original post to revise
            client_brief: Client context
            feedback: Revision feedback

        Returns:
            Revised Post object
        """
        logger.info(f"Generating variant for post: {original_post.template_name}")

        context = client_brief.to_context_dict()

        generation_max_tokens = 6000 if original_post.target_platform == Platform.BLOG else None

        try:
            revised_content = self.client.refine_post(
                original_post=original_post.content,
                feedback=feedback,
                context=context,
                max_tokens=generation_max_tokens,
            )

            revised_content = self._clean_post_content(revised_content)

            # Create new post with revised content
            revised_post = Post(
                content=revised_content,
                template_id=original_post.template_id,
                template_name=original_post.template_name,
                variant=original_post.variant + 100,  # Mark as revision
                client_name=client_brief.company_name,
            )

            logger.info("Successfully generated variant")
            return revised_post

        except Exception as e:
            logger.error(f"Failed to generate variant: {str(e)}", exc_info=True)
            # Return original if revision fails
            return original_post

    async def generate_multi_platform_with_blog_links_async(
        self,
        client_brief: ClientBrief,
        num_blog_posts: int = 5,
        social_teasers_per_blog: int = 2,  # 1 Twitter + 1 Facebook per blog
        template_count: int = 15,
        randomize: bool = True,
        max_concurrent: int = 5,
    ) -> Dict[str, List[Post]]:
        """
        Generate multi-platform content with blog posts and social teasers that link to them

        Args:
            client_brief: Client brief with context
            num_blog_posts: Number of blog posts to generate (default 5)
            social_teasers_per_blog: Number of social teasers per blog (default 2: 1 Twitter + 1 Facebook)
            template_count: Number of unique templates to use
            randomize: Whether to randomize post order
            max_concurrent: Maximum concurrent API calls

        Returns:
            Dictionary with keys 'blog', 'twitter', 'facebook' containing respective Post lists
        """
        logger.info(
            f"Generating multi-platform content for {client_brief.company_name}: "
            f"{num_blog_posts} blog posts + {num_blog_posts * social_teasers_per_blog} social teasers"
        )

        # Step 1: Generate blog posts first
        logger.info(f"Step 1: Generating {num_blog_posts} blog posts...")
        blog_posts = await self.generate_posts_async(
            client_brief=client_brief,
            num_posts=num_blog_posts,
            template_count=template_count,
            randomize=randomize,
            max_concurrent=max_concurrent,
            platform=Platform.BLOG,
        )

        # Step 2: Extract blog metadata
        blog_metadata = []
        for i, blog_post in enumerate(blog_posts):
            title = self._extract_blog_title(blog_post.content)
            slug = self._create_slug(title)
            summary = self._extract_blog_summary(blog_post.content)

            blog_metadata.append(
                {
                    "id": i + 1,
                    "post": blog_post,
                    "title": title,
                    "slug": slug,
                    "summary": summary,
                    "link_placeholder": f"[BLOG_LINK_{i + 1}]",
                }
            )

            # Update blog post with its own metadata
            blog_post.blog_title = title
            blog_post.blog_link_placeholder = f"[BLOG_LINK_{i + 1}]"

        logger.info(f"Extracted metadata for {len(blog_metadata)} blog posts")

        # Step 3: Generate social teasers for each blog
        twitter_posts = []
        facebook_posts = []

        for blog_meta in blog_metadata:
            # Generate Twitter teaser
            twitter_post = await self._generate_blog_teaser_async(
                client_brief=client_brief,
                blog_meta=blog_meta,
                platform=Platform.TWITTER,
            )
            twitter_posts.append(twitter_post)

            # Generate Facebook teaser
            facebook_post = await self._generate_blog_teaser_async(
                client_brief=client_brief,
                blog_meta=blog_meta,
                platform=Platform.FACEBOOK,
            )
            facebook_posts.append(facebook_post)

        logger.info(
            f"Successfully generated multi-platform content: "
            f"{len(blog_posts)} blog + {len(twitter_posts)} Twitter + {len(facebook_posts)} Facebook"
        )

        return {
            "blog": blog_posts,
            "twitter": twitter_posts,
            "facebook": facebook_posts,
        }

    def _extract_blog_title(self, content: str) -> str:
        """Extract title from blog post content (first line or first heading)"""
        lines = content.strip().split("\n")
        if not lines:
            return "Untitled Blog Post"

        # Check for markdown heading
        first_line = lines[0].strip()
        if first_line.startswith("#"):
            return first_line.lstrip("#").strip()

        # Otherwise use first line, truncate if too long
        title = first_line[:100]
        if len(first_line) > 100:
            title += "..."
        return title

    def _create_slug(self, title: str) -> str:
        """Create URL-friendly slug from title"""
        # Convert to lowercase, replace spaces with hyphens, remove special chars
        slug = title.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)
        slug = slug.strip("-")
        # Limit to 60 characters
        return slug[:60]

    def _extract_blog_summary(self, content: str) -> str:
        """Extract first 200 characters as summary"""
        # Remove markdown headings
        clean_content = re.sub(r"^#+\s+", "", content, flags=re.MULTILINE)
        # Get first 200 chars
        summary = clean_content.strip()[:200]
        if len(clean_content) > 200:
            summary += "..."
        return summary

    async def _generate_blog_teaser_async(
        self,
        client_brief: ClientBrief,
        blog_meta: Dict,
        platform: Platform,
    ) -> Post:
        """
        Generate a social media teaser that links to a blog post

        Args:
            client_brief: Client brief
            blog_meta: Blog metadata dict with title, summary, etc.
            platform: Target platform (Twitter or Facebook)

        Returns:
            Post object with teaser content and blog link
        """
        # Build teaser-specific prompt
        platform_guidance = get_platform_prompt_guidance(platform)
        target_length = get_platform_target_length(platform)

        # Build system prompt for teaser generation
        system_prompt = f"""You are an expert social media content creator specializing in {platform.value}.
Your goal is to create compelling, clickable teasers that drive traffic to blog content.
You understand the psychology of curiosity gaps and urgency-driven CTAs.

{platform_guidance}

CRITICAL: You MUST include the provided link placeholder in your post."""

        # Build user prompt with blog context
        user_prompt = f"""Create a {platform.value} post to drive traffic to this blog post:

BLOG TITLE: {blog_meta['title']}
BLOG SUMMARY: {blog_meta['summary']}

REQUIREMENTS:
1. Include the link placeholder {blog_meta['link_placeholder']} in your post
2. Create curiosity/urgency to click through to the blog
3. Tease the value without giving everything away
4. Target length: {target_length}

For Twitter: Hook + key insight teaser + link + 1-2 hashtags. Target 70-100 characters for standalone copy, or 240-280 characters when including a link. HARD FAIL at 280 characters — count before outputting and rewrite if over.
For Facebook: Ultra-short teaser + link (10-15 words or 40-80 chars total)

Example Twitter format:
"Your content strategy is backwards → {blog_meta['link_placeholder']}"

Example Facebook format:
"This changes everything → {blog_meta['link_placeholder']}"

Generate the {platform.value} teaser now:"""

        try:
            # Generate teaser content
            content = await call_claude_api_async(
                self.client,
                user_prompt,
                system_prompt=system_prompt,
                temperature=0.8,  # More creative for teasers
                extract_json=False,
                fallback_on_error="",
            )

            # Clean content
            content = self._clean_post_content(content)

            # Create Post object
            post = Post(
                content=content,
                template_id=0,  # Teaser, not from template
                template_name="Blog Teaser",
                variant=1,
                client_name=client_brief.company_name,
                target_platform=platform,
                related_blog_post_id=blog_meta["id"],
                blog_link_placeholder=blog_meta["link_placeholder"],
                blog_title=blog_meta["title"],
            )

            logger.info(f"Generated {platform.value} teaser for blog #{blog_meta['id']}")
            return post

        except Exception as e:
            logger.error(f"Failed to generate teaser: {str(e)}", exc_info=True)
            # Create placeholder post
            post = Post(
                content=f"[ERROR: Failed to generate teaser - {str(e)}]",
                template_id=0,
                template_name="Blog Teaser",
                variant=1,
                client_name=client_brief.company_name,
                target_platform=platform,
                related_blog_post_id=blog_meta["id"],
                blog_link_placeholder=blog_meta["link_placeholder"],
                blog_title=blog_meta["title"],
            )
            post.flag_for_review(f"Teaser generation failed: {str(e)}")
            return post
