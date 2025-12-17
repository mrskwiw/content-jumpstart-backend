"""Post Regeneration Agent: Automatically fixes posts that fail quality checks

This agent analyzes posts against quality thresholds and regenerates those that
fall outside acceptable parameters for readability, length, engagement, or CTAs.
"""

from typing import Dict, List, Optional, Tuple

from ..config.constants import POST_GENERATION_TEMPERATURE
from ..models.client_brief import ClientBrief
from ..models.post import Post
from ..models.quality_profile import QualityProfile, get_default_profile
from ..models.template import Template
from ..utils.anthropic_client import AnthropicClient
from ..utils.logger import logger
from ..utils.voice_metrics import VoiceMetrics


class RegenerationReason:
    """Structured reason for why a post needs regeneration"""

    def __init__(self, reason_type: str, details: str, current_value: Optional[float] = None):
        """Initialize regeneration reason

        Args:
            reason_type: Type of issue (e.g., 'low_readability', 'too_short')
            details: Human-readable explanation
            current_value: Optional metric value that triggered regeneration
        """
        self.reason_type = reason_type
        self.details = details
        self.current_value = current_value

    def __repr__(self):
        """String representation of regeneration reason"""
        if self.current_value is not None:
            return f"{self.reason_type}: {self.details} (current: {self.current_value})"
        return f"{self.reason_type}: {self.details}"


class PostRegenerator:
    """Agent that regenerates posts failing quality thresholds"""

    def __init__(
        self,
        client: Optional[AnthropicClient] = None,
        quality_profile: Optional[QualityProfile] = None,
    ):
        """Initialize post regenerator

        Args:
            client: Anthropic client for regeneration API calls
            quality_profile: Quality thresholds to use (defaults to professional_linkedin)
        """
        self.client = client or AnthropicClient()
        self.voice_metrics = VoiceMetrics()
        self.profile = quality_profile or get_default_profile("professional_linkedin")

    def should_regenerate(self, post: Post) -> Tuple[bool, List[RegenerationReason]]:
        """Determine if post should be regenerated and why

        Args:
            post: Post to evaluate

        Returns:
            Tuple of (should_regenerate: bool, reasons: List[RegenerationReason])
        """
        reasons = []

        # Check readability score
        if post.content:
            readability = self.voice_metrics.calculate_readability(post.content)

            if readability < self.profile.min_readability:
                reasons.append(
                    RegenerationReason(
                        "low_readability",
                        f"Readability too difficult (min: {self.profile.min_readability})",
                        readability,
                    )
                )
            elif readability > self.profile.max_readability:
                reasons.append(
                    RegenerationReason(
                        "high_readability",
                        f"Readability too simple for professional content (max: {self.profile.max_readability})",
                        readability,
                    )
                )

        # Check length constraints
        if post.word_count < self.profile.min_words:
            reasons.append(
                RegenerationReason(
                    "too_short",
                    f"Post too short (min: {self.profile.min_words} words)",
                    post.word_count,
                )
            )
        elif post.word_count > self.profile.max_words:
            reasons.append(
                RegenerationReason(
                    "too_long",
                    f"Post too long (max: {self.profile.max_words} words)",
                    post.word_count,
                )
            )

        # Check CTA requirement
        if self.profile.require_cta and not post.has_cta:
            reasons.append(RegenerationReason("missing_cta", "Post lacks clear call-to-action"))

        # Check headline engagement (if available from review reason)
        if post.needs_review and post.review_reason:
            reason = post.review_reason
            if "headline has only" in reason.lower() and "engagement elements" in reason.lower():
                # Extract score from reason like "headline has only 1/3 engagement elements"
                try:
                    score_part = reason.split("only")[1].split("/")[0].strip()
                    score = int(score_part)
                    if score < self.profile.min_engagement_score:
                        reasons.append(
                            RegenerationReason(
                                "weak_headline",
                                f"Headline needs more engagement (min: {self.profile.min_engagement_score} elements)",
                                score,
                            )
                        )
                except:
                    pass

        should_regen = len(reasons) > 0
        return should_regen, reasons

    def regenerate_post(
        self,
        post: Post,
        template: Template,
        client_brief: ClientBrief,
        reasons: List[RegenerationReason],
        attempt: int = 1,
        system_prompt: Optional[str] = None,
    ) -> Post:
        """Regenerate a post with improvement guidance

        Args:
            post: Original post to improve
            template: Template that was used
            client_brief: Client context
            reasons: Reasons for regeneration
            attempt: Current attempt number (1-based)
            system_prompt: Optional cached system prompt

        Returns:
            Regenerated Post object
        """
        if attempt > self.profile.max_attempts:
            logger.warning(
                f"Max regeneration attempts ({self.profile.max_attempts}) reached for post {post.template_name}"
            )
            return post

        logger.info(
            f"Regenerating post {post.template_name} (attempt {attempt}/{self.profile.max_attempts}): "
            f"{', '.join(r.reason_type for r in reasons)}"
        )

        # Build improvement guidance
        improvement_prompt = self._build_improvement_prompt(post, reasons, client_brief)

        # Build context
        context = client_brief.to_context_dict()
        context["variant_guidance"] = improvement_prompt
        context["template_type"] = template.template_type.value
        context["requires_story"] = template.requires_story
        context["requires_data"] = template.requires_data

        try:
            # Generate improved content
            improved_content = self.client.generate_post_content(
                template_structure=template.structure,
                context=context,
                system_prompt=system_prompt or "",
                temperature=POST_GENERATION_TEMPERATURE,
            )

            # Clean content
            improved_content = self._clean_content(improved_content)

            # Create new post
            regenerated_post = Post(
                content=improved_content,
                template_id=post.template_id,
                template_name=post.template_name,
                variant=post.variant + 100 * attempt,  # Mark as regeneration (101, 201, etc.)
                client_name=post.client_name,
                target_platform=post.target_platform,
            )

            # Check if regeneration succeeded
            should_retry, new_reasons = self.should_regenerate(regenerated_post)

            if should_retry and attempt < self.profile.max_attempts:
                # Try again with more specific guidance
                logger.info(f"Regeneration attempt {attempt} still has issues, retrying...")
                return self.regenerate_post(
                    regenerated_post,
                    template,
                    client_brief,
                    new_reasons,
                    attempt + 1,
                    system_prompt,
                )

            logger.info(f"Successfully regenerated post {post.template_name}")
            return regenerated_post

        except Exception as e:
            logger.error(f"Failed to regenerate post: {str(e)}", exc_info=True)
            # Return original post if regeneration fails
            return post

    def _build_improvement_prompt(
        self, post: Post, reasons: List[RegenerationReason], client_brief: ClientBrief
    ) -> str:
        """Build specific improvement guidance based on reasons

        Args:
            post: Post being regenerated
            reasons: Why it needs regeneration
            client_brief: Client context

        Returns:
            Improvement guidance string
        """
        guidance_parts = [
            "CRITICAL: This is a regeneration to fix specific issues. Address ALL of these:"
        ]

        for reason in reasons:
            if reason.reason_type == "low_readability":
                guidance_parts.append(
                    f"- Simplify language: Current readability is {reason.current_value:.1f}, "
                    f"target {self.profile.min_readability}-{self.profile.max_readability}. Use shorter sentences "
                    f"and simpler words while maintaining professionalism."
                )

            elif reason.reason_type == "high_readability":
                guidance_parts.append(
                    f"- Add sophistication: Current readability is {reason.current_value:.1f}, "
                    f"target {self.profile.min_readability}-{self.profile.max_readability}. Use more varied "
                    f"sentence structure and precise vocabulary appropriate for professional audience."
                )

            elif reason.reason_type == "too_short":
                guidance_parts.append(
                    f"- Expand content: Currently {reason.current_value} words, need {self.profile.min_words}+. "
                    f"Add a concrete example, data point, or personal story to support your point."
                )

            elif reason.reason_type == "too_long":
                guidance_parts.append(
                    f"- Tighten content: Currently {reason.current_value} words, stay under {self.profile.max_words}. "
                    f"Cut unnecessary details and focus on the core insight."
                )

            elif reason.reason_type == "missing_cta":
                guidance_parts.append(
                    "- Add clear CTA: End with a specific question or invitation. Examples: "
                    "'What's your experience with [topic]?' or 'Try [specific action] and let me know how it goes.'"
                )

            elif reason.reason_type == "weak_headline":
                guidance_parts.append(
                    f"- Strengthen opening: Include at least {self.profile.min_engagement_score} of these: "
                    f"question, specific number, power word ('secret', 'mistake', 'surprising'), "
                    f"or contrarian statement."
                )

        return "\n".join(guidance_parts)

    def _clean_content(self, content: str) -> str:
        """Clean generated content"""
        import re

        content = content.strip()

        # Remove leading/trailing quotes
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]

        # Remove markdown headers
        content = content.replace("# ", "").replace("## ", "")

        # Normalize line breaks (max 2 consecutive)
        content = re.sub(r"\n{3,}", "\n\n", content)

        return content.strip()

    def regenerate_failed_posts(
        self,
        posts: List[Post],
        templates: List[Template],
        client_brief: ClientBrief,
        system_prompt: Optional[str] = None,
    ) -> Tuple[List[Post], Dict]:
        """Regenerate all posts that fail quality checks

        Args:
            posts: List of posts to check
            templates: Templates used (for regeneration)
            client_brief: Client context
            system_prompt: Optional cached system prompt

        Returns:
            Tuple of (regenerated_posts: List[Post], stats: Dict)
        """
        regenerated_posts = []
        stats = {
            "total_posts": len(posts),
            "posts_regenerated": 0,
            "posts_improved": 0,
            "posts_unchanged": 0,
            "reasons": {},
        }

        # Create template lookup
        template_map = {t.template_id: t for t in templates}

        for post in posts:
            should_regen, reasons = self.should_regenerate(post)

            if should_regen:
                # Track reasons
                for reason in reasons:
                    stats["reasons"][reason.reason_type] = (
                        stats["reasons"].get(reason.reason_type, 0) + 1
                    )

                # Get template
                template = template_map.get(post.template_id)
                if not template:
                    logger.warning(f"Template {post.template_id} not found, skipping regeneration")
                    regenerated_posts.append(post)
                    stats["posts_unchanged"] += 1
                    continue

                # Regenerate
                regenerated_post = self.regenerate_post(
                    post, template, client_brief, reasons, attempt=1, system_prompt=system_prompt
                )

                # Check if actually improved
                new_should_regen, new_reasons = self.should_regenerate(regenerated_post)

                if not new_should_regen or len(new_reasons) < len(reasons):
                    stats["posts_improved"] += 1
                    regenerated_posts.append(regenerated_post)
                else:
                    stats["posts_unchanged"] += 1
                    regenerated_posts.append(regenerated_post)  # Still use regenerated version

                stats["posts_regenerated"] += 1
            else:
                regenerated_posts.append(post)

        logger.info(
            f"Regeneration complete: {stats['posts_regenerated']}/{stats['total_posts']} posts regenerated, "
            f"{stats['posts_improved']} improved"
        )

        return regenerated_posts, stats
