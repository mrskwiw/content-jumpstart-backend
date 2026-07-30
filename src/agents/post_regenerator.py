"""Post Regeneration Agent: Automatically fixes posts that fail quality checks

This agent analyzes posts against quality thresholds and regenerates those that
fall outside acceptable parameters for readability, length, engagement, or CTAs.
"""

from typing import Any, Dict, List, Optional, Tuple

import re

from ..config.constants import POST_GENERATION_TEMPERATURE
from ..models.client_brief import ClientBrief, Platform
from ..models.post import Post
from ..models.quality_profile import QualityProfile, get_default_profile
from ..models.template import Template, TemplateType
from ..utils.anthropic_client import AnthropicClient
from ..utils.logger import logger
from ..analysis.content_intelligence import assess_post
from ..utils.voice_metrics import VoiceMetrics
from ..validators.cta_validator import CTAValidator
from .hashtag_researcher import strip_all_hashtags

# Template name keywords whose posts are designed to end with engagement questions.
# These are exempt from the post_ends_with_question regeneration trigger.
# Keyed by template_name substrings (case-insensitive) because post.template_name
# stores the display name, not the TemplateType enum value.
#   Template 3 stored name: "Against the Grain"  (TemplateType.CONTRARIAN)
#   Template 5 stored name: "Question"            (TemplateType.QUESTION)
#   Template 14 stored name: "Reader Question"    (TemplateType.Q_AND_A)
_ENGAGEMENT_QUESTION_TYPES: frozenset[str] = frozenset(
    {
        "against the grain",  # Template 3 actual stored name — does NOT contain "contrarian"
        TemplateType.QUESTION.value,  # "question" — covers Template 5 and Template 14
        TemplateType.CONTRARIAN.value,  # "contrarian" — future-proof if name ever changes
        TemplateType.Q_AND_A.value,  # "q_and_a"
        "q&a",  # matches any template literally named "Q&A ..."
    }
)


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

        # Evaluate the PROSE body. Appended hashtags are metadata, not prose —
        # counting them would skew length/CTA/readability diagnostics and
        # regenerate every hashtagged post (BUGS.md Decision #198). Uses the
        # Unicode-aware sanitizer so digit-led/non-Latin tags are stripped too.
        prose = strip_all_hashtags(post.content) if post.content else ""
        prose_word_count = len(prose.split())

        # Check readability score
        if post.content:
            readability = self.voice_metrics.calculate_readability(prose)

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

        # Check length constraints (prose only — appended hashtags don't count)
        if prose_word_count < self.profile.min_words:
            reasons.append(
                RegenerationReason(
                    "too_short",
                    f"Post too short (min: {self.profile.min_words} words)",
                    prose_word_count,
                )
            )
        elif prose_word_count > self.profile.max_words:
            reasons.append(
                RegenerationReason(
                    "too_long",
                    f"Post too long (max: {self.profile.max_words} words)",
                    prose_word_count,
                )
            )

        # Check CTA requirement
        if self.profile.require_cta and not post.has_cta:
            reasons.append(RegenerationReason("missing_cta", "Post lacks clear call-to-action"))

        # Check CTA placement and form (on the prose body, so an appended hashtag
        # line is not mistaken for the final line / a misplaced CTA).
        if prose:
            lines = [ln.strip() for ln in prose.strip().split("\n") if ln.strip()]
            if lines:
                last_line = lines[-1]
                body = "\n".join(lines[:-1]).lower()
                # Body scan: use strict placement patterns only — avoids false
                # positives from broad terms like "appointment" in body sentences.
                for pat in CTAValidator._PLACEMENT_PATTERNS:
                    if re.search(pat, body, re.IGNORECASE):
                        reasons.append(
                            RegenerationReason(
                                "cta_not_last",
                                "CTA appears mid-post — must be the final line",
                            )
                        )
                        break

                # Last-line question check: use full CTA_PATTERNS so every form
                # the validator recognises (including "Appointment?",
                # "Let's book?", "Ask us?") is caught and queued for repair.
                cta_pattern_matched = False
                for pat, _ in CTAValidator.CTA_PATTERNS:
                    if re.search(pat, last_line, re.IGNORECASE):
                        cta_pattern_matched = True
                        if last_line.rstrip().endswith("?"):
                            reasons.append(
                                RegenerationReason(
                                    "cta_is_question",
                                    "CTA is a question — must be a statement",
                                )
                            )
                        break

                # Generic question closer: last line ends with "?" but matches
                # no CTA pattern (e.g. "What do you think?").  Exempt templates
                # that are designed to end with engagement questions (Question
                # Post, Contrarian Take, Reader Q&A) — their question endings
                # are intentional and valid.  Flag all other templates.
                template_name_lower = (post.template_name or "").lower()
                is_engagement_question_template = any(
                    t in template_name_lower for t in _ENGAGEMENT_QUESTION_TYPES
                )
                if (
                    not cta_pattern_matched
                    and last_line.rstrip().endswith("?")
                    and not is_engagement_question_template
                ):
                    reasons.append(
                        RegenerationReason(
                            "post_ends_with_question",
                            "Post ends with a question — the final line must be a statement CTA",
                        )
                    )

        # Generic-AI voice check (BRAND-CORE-02) — opt-in per profile. Regenerate
        # posts that read as generic AI so they're pushed toward a point of view.
        # Evaluates the same prose body (hashtags already stripped); only the
        # genericity signal is used here — length/CTA/engagement are covered above,
        # so folding in the predictor's low-score branch would double-count them.
        if self.profile.check_genericity and prose:
            platform = post.target_platform.value if post.target_platform else "linkedin"
            assessment = assess_post(
                prose, platform=platform, generic_threshold=self.profile.max_genericity
            )
            if assessment.is_generic:
                detail = "Reads as generic AI — rewrite toward a specific point of view"
                if assessment.flags:
                    detail += f" ({', '.join(assessment.flags)})"
                reasons.append(
                    RegenerationReason("generic_voice", detail, assessment.genericity_score)
                )

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
                except (ValueError, IndexError):
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

        generation_max_tokens = 6000 if post.target_platform == Platform.BLOG else None

        try:
            # Generate improved content
            improved_content = self.client.generate_post_content(
                template_structure=template.structure,
                context=context,
                system_prompt=system_prompt or "",
                temperature=POST_GENERATION_TEMPERATURE,
                max_tokens=generation_max_tokens,
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
                    "- Add a statement CTA as the final line. Must be an imperative, not a question. "
                    "Examples: 'Book a free call at [link].' or 'Download the guide at [link].' or "
                    "'Reply with your biggest challenge and I'll share what worked for us.'"
                )

            elif reason.reason_type == "cta_not_last":
                guidance_parts.append(
                    "- Move the CTA to the very last line of the post. Nothing should follow it. "
                    "Remove or merge any CTA that appears mid-post."
                )

            elif reason.reason_type == "cta_is_question":
                guidance_parts.append(
                    "- Rewrite the CTA as a statement, not a question. "
                    "Instead of 'What do you think?' use 'Share your take in the comments.' "
                    "Instead of 'Have you tried this?' use 'Try this today and let me know how it goes.'"
                )

            elif reason.reason_type == "post_ends_with_question":
                guidance_parts.append(
                    "- Rewrite the final line as a statement, not a question. "
                    "Instead of 'Have you faced this?' use 'Share your experience below.' "
                    "Instead of 'What would you do?' use 'Try this approach and let me know how it goes.' "
                    "The final line must always be a statement."
                )

            elif reason.reason_type == "weak_headline":
                guidance_parts.append(
                    f"- Strengthen opening: Include at least {self.profile.min_engagement_score} of these: "
                    f"question, specific number, power word ('secret', 'mistake', 'surprising'), "
                    f"or contrarian statement."
                )

            elif reason.reason_type == "generic_voice":
                # Counters exactly the signals the genericity detector flags
                # (generic openers, clichés, AI-tell filler, templated bullets).
                # Without this, a post flagged generic regenerates with no direction
                # and can burn every retry unchanged.
                guidance_parts.append(
                    "- Kill the generic AI voice — TOP PRIORITY. Rewrite toward a specific, "
                    "opinionated point of view: "
                    "(1) Replace the opening line with a concrete hook drawn from the client's own "
                    "story or offer — never 'In today's world' or 'In the ever-evolving landscape of...'. "
                    "(2) Cut corporate clichés/buzzwords (leverage, synergy, cutting-edge, unlock, "
                    "supercharge, game-changer, robust, seamless, elevate, at the end of the day). "
                    "(3) Delete AI-tell filler ('it is important to note', 'in conclusion', "
                    "'in summary', 'when it comes to', 'navigating the'). "
                    "(4) Add specificity ONLY from the client's brief and the original post's real "
                    "details — do NOT invent statistics, numbers, studies, customers, or events. If no "
                    "concrete data is available, be specific through vivid, precise language and a clear "
                    "stance, never fabricated facts. "
                    "(5) Take a side — say what you actually believe, not what everyone already agrees with."
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
        regenerated_posts: List[Post] = []
        stats: Dict[str, Any] = {
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
