"""Content Generator Agent: Generates posts from templates and client context"""

import asyncio
import random
import re
from typing import Any, Dict, List, Optional

from ..config.brand_frameworks import (
    get_archetype_from_client_type,
    get_archetype_guidance,
    get_writing_principles_guidance,
)
from ..config.constants import AI_TELL_PHRASES, MAX_POST_WORD_COUNT, MIN_POST_WORD_COUNT
from ..config.platform_specs import get_platform_prompt_guidance, get_platform_target_length
from ..config.prompts import SystemPrompts
from ..models.client_brief import ClientBrief, Platform
from ..models.post import Post
from ..models.seo_keyword import KeywordStrategy
from ..models.template import Template
from ..utils.anthropic_client import AnthropicClient
from ..utils.logger import log_post_generated, logger
from ..utils.template_loader import TemplateLoader


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
        db: Optional[Any] = None,
    ):
        """
        Initialize Content Generator Agent

        Args:
            client: Anthropic client instance
            template_loader: Template loader instance
            keyword_strategy: Optional SEO keyword strategy for keyword-aware generation
            db: Optional ProjectDatabase instance for client memory integration
        """
        self.client = client or AnthropicClient()
        self.template_loader = template_loader or TemplateLoader()
        self.keyword_strategy = keyword_strategy
        self.db = db

    def generate_posts(
        self,
        client_brief: ClientBrief,
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
            num_posts: Total number of posts to generate (default 30)
            template_count: Number of unique templates to use (default 15)
            randomize: Whether to randomize post order
            template_ids: Optional list of specific template IDs to use (overrides intelligent selection)
            platform: Target platform for content generation (default LinkedIn)
            use_client_memory: Whether to use client memory for optimization (default True)

        Returns:
            List of generated Post objects
        """
        logger.info(
            f"Generating {num_posts} posts for {client_brief.company_name} "
            f"using {template_count} templates"
        )

        # Load client memory if available and enabled
        client_memory = None
        if use_client_memory and self.db:
            client_memory = self.db.get_client_memory(client_brief.company_name)
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
                client_brief,
                count=template_count,
                boost_templates=client_memory.preferred_templates if client_memory else [],
                avoid_templates=client_memory.avoided_templates if client_memory else [],
            )

        # Cache system prompt and base context for reuse across all posts
        cached_system_prompt = self._build_system_prompt(client_brief, platform, client_memory)
        base_context = client_brief.to_context_dict()

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
            num_posts: Total number of posts to generate (default 30)
            template_count: Number of unique templates to use (default 15)
            randomize: Whether to randomize post order
            max_concurrent: Maximum concurrent API calls (default 5)
            template_ids: Optional list of specific template IDs to use (overrides intelligent selection)
            platform: Target platform for content generation (default LinkedIn)
            use_client_memory: Whether to use client memory for optimization (default True)

        Returns:
            List of generated Post objects
        """

        logger.info(
            f"Generating {num_posts} posts for {client_brief.company_name} "
            f"using {template_count} templates (async mode, max concurrent: {max_concurrent})"
        )

        # Load client memory if available and enabled
        client_memory = None
        if use_client_memory and self.db:
            client_memory = self.db.get_client_memory(client_brief.company_name)
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
                client_brief,
                count=template_count,
                boost_templates=client_memory.preferred_templates if client_memory else [],
                avoid_templates=client_memory.avoided_templates if client_memory else [],
            )

        # Cache system prompt and base context for reuse across all posts
        cached_system_prompt = self._build_system_prompt(client_brief, platform, client_memory)
        base_context = client_brief.to_context_dict()

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
            """Generate single post with concurrency limit via semaphore"""
            async with semaphore:
                return await self._generate_single_post_async(
                    template=task_params["template"],
                    client_brief=client_brief,
                    variant=task_params["variant"],
                    post_number=task_params["post_number"],
                    cached_system_prompt=task_params["cached_system_prompt"],
                    base_context=task_params["base_context"],
                    platform=platform,
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

            logger.info(
                f"Voice Match Score: {voice_match_report.match_score:.1%} "
                f"(Readability: {voice_match_report.readability_score.score:.1%}, "
                f"Word Count: {voice_match_report.word_count_score.score:.1%}, "
                f"Archetype: {voice_match_report.archetype_score.score:.1%}, "
                f"Phrases: {voice_match_report.phrase_usage_score.score:.1%})"
            )

            return posts, voice_match_report

        except Exception as e:
            logger.error(f"Failed to calculate voice match report: {e}")
            return posts, None

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

        # Use cached system prompt if available, otherwise build it
        # Note: When using cached prompt, platform info is already embedded from the cache
        system_prompt = cached_system_prompt or self._build_system_prompt(
            client_brief, Platform.LINKEDIN
        )

        # Generate post content via API
        try:
            content = self.client.generate_post_content(
                template_structure=template.structure,
                context=context,
                system_prompt=system_prompt,
                temperature=0.7,  # Balanced creativity
            )

            # Clean up content
            content = self._clean_post_content(content)

            # Create Post object
            post = Post(
                content=content,
                template_id=template.template_id,
                template_name=template.name,
                variant=variant,
                client_name=client_brief.company_name,
                target_platform=platform.value,
            )

            # Check if post needs review
            self._check_quality_flags(post, template, client_brief)

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
                target_platform=platform.value,
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

        # Use cached system prompt if available, otherwise build it
        # Note: When using cached prompt, platform info is already embedded from the cache
        system_prompt = cached_system_prompt or self._build_system_prompt(
            client_brief, Platform.LINKEDIN
        )

        # Generate post content via API (async)
        try:
            content = await self.client.generate_post_content_async(
                template_structure=template.structure,
                context=context,
                system_prompt=system_prompt,
                temperature=0.7,  # Balanced creativity
            )

            # Clean up content
            content = self._clean_post_content(content)

            # Create Post object
            post = Post(
                content=content,
                template_id=template.template_id,
                template_name=template.name,
                variant=variant,
                client_name=client_brief.company_name,
                target_platform=platform.value,
            )

            # Check if post needs review
            self._check_quality_flags(post, template, client_brief)

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
                target_platform=platform.value,
            )
            post.flag_for_review(f"Generation failed: {str(e)}")
            return post

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
        context = base_context.copy() if base_context else client_brief.to_context_dict()

        # Add variant-specific guidance
        if variant == 1:
            context["variant_guidance"] = "Use a direct, problem-focused angle"
        elif variant == 2:
            context["variant_guidance"] = "Use a story-driven or example-based angle"
        else:
            context["variant_guidance"] = "Use a unique angle different from previous variants"

        # Add template-specific context
        context["template_type"] = template.template_type.value
        context["requires_story"] = template.requires_story
        context["requires_data"] = template.requires_data

        return context

    def _build_system_prompt(
        self,
        client_brief: ClientBrief,
        platform: Platform = Platform.LINKEDIN,
        client_memory: Optional[Any] = None,
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

        # Add platform-specific guidance
        platform_guidance = get_platform_prompt_guidance(platform)
        target_length = get_platform_target_length(platform)
        from ..config.platform_specs import PLATFORM_LENGTH_SPECS

        specs = PLATFORM_LENGTH_SPECS.get(platform, {})

        prompt += f"\n\nPLATFORM: {platform.value.upper()}"
        prompt += f"\nTARGET LENGTH: {target_length}"

        # Add strict length enforcement for platforms with tight limits
        if platform in [Platform.TWITTER, Platform.FACEBOOK]:
            optimal_min = specs.get("optimal_min_words", 10)
            optimal_max = specs.get("optimal_max_words", 20)
            prompt += f"\n\n⚠️ CRITICAL LENGTH REQUIREMENT: Your post MUST be between {optimal_min}-{optimal_max} words. This is a hard limit. Posts longer than {optimal_max} words will be rejected."

        prompt += f"\n{platform_guidance}"

        # Add client-specific voice guidance
        if client_brief.brand_personality:
            personalities = ", ".join([p.value for p in client_brief.brand_personality])
            prompt += f"\n\nCLIENT VOICE: This client is {personalities}."

        if client_brief.key_phrases:
            phrases = '", "'.join(client_brief.key_phrases)
            prompt += f'\n\nKEY PHRASES TO USE: "{phrases}"'

        if client_brief.misconceptions:
            avoid = ", ".join(client_brief.misconceptions)
            prompt += f"\n\nCOMMON MISCONCEPTIONS TO ADDRESS: {avoid}"

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

        return prompt

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
        # Try to get client type from classifier if available
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

    def _check_quality_flags(
        self, post: Post, template: Template, client_brief: ClientBrief
    ) -> None:
        """Check post for quality issues and flag if needed"""
        content_lower = post.content.lower()

        # Check for AI tells using module constant
        for tell in AI_TELL_PHRASES:
            if tell in content_lower:
                post.flag_for_review(f"Contains AI tell: '{tell}'")
                return

        # Check if post is too short or too long using constants
        if post.word_count < MIN_POST_WORD_COUNT:
            post.flag_for_review(f"Post too short: {post.word_count} words")
            return

        if post.word_count > MAX_POST_WORD_COUNT:
            post.flag_for_review(f"Post too long: {post.word_count} words")
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

        try:
            revised_content = self.client.refine_post(
                original_post=original_post.content,
                feedback=feedback,
                context=context,
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

For Twitter: Hook + key insight teaser + link + 1-2 hashtags (max 280 chars total)
For Facebook: Ultra-short teaser + link (under 80 chars total)

Example Twitter format:
"Your content strategy is backwards. Here's why → {blog_meta['link_placeholder']} #ContentMarketing"

Example Facebook format:
"This changes everything → {blog_meta['link_placeholder']}"

Generate the {platform.value} teaser now:"""

        try:
            # Generate teaser content
            content = await self.client.create_message_async(
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.8,  # More creative for teasers
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
                target_platform=platform.value,
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
                target_platform=platform.value,
                related_blog_post_id=blog_meta["id"],
                blog_link_placeholder=blog_meta["link_placeholder"],
                blog_title=blog_meta["title"],
            )
            post.flag_for_review(f"Teaser generation failed: {str(e)}")
            return post
