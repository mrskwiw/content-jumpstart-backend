"""Revision Agent: Generates revised posts based on client feedback

This agent handles targeted post regeneration when clients request changes.
Unlike auto-regeneration (quality-based), this applies specific client feedback.
"""

from typing import List, Optional, Tuple

from ..config.constants import POST_GENERATION_TEMPERATURE
from ..models.client_brief import ClientBrief
from ..models.post import Post
from ..models.project import RevisionDiff
from ..models.template import Template
from ..utils.anthropic_client import AnthropicClient
from ..utils.logger import logger


class RevisionAgent:
    """Agent that generates revised posts based on client feedback"""

    def __init__(self, client: Optional[AnthropicClient] = None):
        """Initialize revision agent

        Args:
            client: Anthropic client for API calls (optional)
        """
        self.client = client or AnthropicClient()

    def generate_revised_post(
        self,
        original_post: Post,
        client_feedback: str,
        client_brief: ClientBrief,
        template: Template,
        system_prompt: Optional[str] = None,
    ) -> Tuple[Post, str]:
        """Generate a revised version of a post based on client feedback

        Args:
            original_post: The original post to revise
            client_feedback: Specific feedback on what to change
            client_brief: Client context
            template: Template structure
            system_prompt: Optional cached system prompt

        Returns:
            Tuple of (revised_post, changes_summary)
        """
        logger.info(
            f"Generating revision for post #{original_post.variant} "
            f"({original_post.template_name})"
        )

        # Build revision prompt
        revision_prompt = self._build_revision_prompt(
            original_post, client_feedback, client_brief, template
        )

        try:
            # Generate revised content
            revised_content = self.client.generate_post_content(
                template_structure=template.structure,
                context=revision_prompt,
                system_prompt=system_prompt or self._build_system_prompt(client_brief),
                temperature=POST_GENERATION_TEMPERATURE,
            )

            # Clean content
            revised_content = self._clean_content(revised_content)

            # Create revised post
            revised_post = Post(
                content=revised_content,
                template_id=original_post.template_id,
                template_name=original_post.template_name,
                variant=original_post.variant,  # Keep same variant number
                client_name=original_post.client_name,
                target_platform=original_post.target_platform,
            )

            # Generate changes summary
            changes_summary = self._generate_changes_summary(
                original_post, revised_post, client_feedback
            )

            logger.info(
                f"Successfully revised post #{original_post.variant}: "
                f"{original_post.word_count} -> {revised_post.word_count} words"
            )

            return revised_post, changes_summary

        except Exception as e:
            logger.error(f"Failed to revise post: {str(e)}", exc_info=True)
            # Return original post if revision fails
            return original_post, f"Revision failed: {str(e)}"

    def revise_multiple_posts(
        self,
        posts: List[Post],
        client_feedback: str,
        client_brief: ClientBrief,
        templates: List[Template],
        system_prompt: Optional[str] = None,
    ) -> List[Tuple[Post, str]]:
        """Revise multiple posts based on client feedback

        Args:
            posts: List of posts to revise
            client_feedback: Overall feedback that applies to all posts
            client_brief: Client context
            templates: Available templates
            system_prompt: Optional cached system prompt

        Returns:
            List of (revised_post, changes_summary) tuples
        """
        template_map = {t.template_id: t for t in templates}
        revised_posts = []

        for post in posts:
            template = template_map.get(post.template_id)
            if not template:
                logger.warning(f"Template {post.template_id} not found for post {post.variant}")
                revised_posts.append((post, "Template not found, kept original"))
                continue

            revised_post, changes = self.generate_revised_post(
                original_post=post,
                client_feedback=client_feedback,
                client_brief=client_brief,
                template=template,
                system_prompt=system_prompt,
            )
            revised_posts.append((revised_post, changes))

        return revised_posts

    def _build_revision_prompt(
        self,
        original_post: Post,
        client_feedback: str,
        client_brief: ClientBrief,
        template: Template,
    ) -> dict:
        """Build context for revision generation

        Args:
            original_post: Original post
            client_feedback: What to change
            client_brief: Client context
            template: Template structure

        Returns:
            Context dictionary for generation
        """
        context = client_brief.to_context_dict()

        # Add revision-specific guidance
        context["revision_mode"] = True
        context["original_content"] = original_post.content
        context["client_feedback"] = client_feedback
        context["template_type"] = template.template_type.value
        context["requires_story"] = template.requires_story
        context["requires_data"] = template.requires_data

        # Add specific revision guidance
        revision_instructions = self._parse_feedback_to_instructions(client_feedback)
        context[
            "variant_guidance"
        ] = f"""
CRITICAL: This is a REVISION based on client feedback.

**Original Post:**
{original_post.content}

**Client Feedback:**
{client_feedback}

**Required Changes:**
{revision_instructions}

**Important:**
- Apply ONLY the changes requested in the feedback
- Maintain the overall structure and template format
- Keep the same voice/tone unless feedback specifically requests a change
- Preserve any elements the client didn't mention (they liked those parts)
- Do NOT make improvements beyond what was requested
"""

        return context

    def _parse_feedback_to_instructions(self, feedback: str) -> str:
        """Parse client feedback into specific instructions

        Args:
            feedback: Raw client feedback

        Returns:
            Structured instructions for the model
        """
        instructions = []

        # Detect common feedback patterns
        feedback_lower = feedback.lower()

        if "more casual" in feedback_lower or "less formal" in feedback_lower:
            instructions.append("- Make tone more casual (use contractions, shorter sentences)")

        if "more professional" in feedback_lower or "more formal" in feedback_lower:
            instructions.append(
                "- Make tone more professional (avoid contractions, use precise language)"
            )

        if "shorter" in feedback_lower or "too long" in feedback_lower:
            instructions.append("- Reduce length while keeping core message")

        if (
            "longer" in feedback_lower
            or "too short" in feedback_lower
            or "expand" in feedback_lower
        ):
            instructions.append("- Expand with more detail or examples")

        if (
            "add cta" in feedback_lower
            or "call to action" in feedback_lower
            or "add question" in feedback_lower
        ):
            instructions.append("- Add a clear call-to-action or question at the end")

        if "emoji" in feedback_lower:
            if "more emoji" in feedback_lower or "add emoji" in feedback_lower:
                instructions.append("- Include 1-2 relevant emojis")
            elif "less emoji" in feedback_lower or "remove emoji" in feedback_lower:
                instructions.append("- Remove all emojis")

        if (
            "more data" in feedback_lower
            or "add stats" in feedback_lower
            or "add numbers" in feedback_lower
        ):
            instructions.append("- Include specific statistics or data points")

        if "more story" in feedback_lower or "add example" in feedback_lower:
            instructions.append("- Add a concrete example or personal story")

        if "simpler" in feedback_lower or "easier to understand" in feedback_lower:
            instructions.append("- Simplify language and sentence structure")

        # If no specific patterns detected, use feedback directly
        if not instructions:
            instructions.append(f"- {feedback}")

        return "\n".join(instructions)

    def _build_system_prompt(self, client_brief: ClientBrief) -> str:
        """Build system prompt for revision generation

        Args:
            client_brief: Client context

        Returns:
            System prompt
        """
        return f"""You are a professional content writer revising social media posts based on client feedback.

**Client Context:**
- Company: {client_brief.company_name}
- Business: {client_brief.business_description}
- Voice: {", ".join(client_brief.brand_voice_traits)}

**Your Task:**
Generate a revised version of the post that addresses the client's specific feedback while maintaining the overall quality and structure.

**Guidelines:**
- Apply ONLY the changes requested in the feedback
- Maintain professional quality
- Keep the same template structure
- Preserve elements the client didn't mention
- Focus on targeted improvements, not wholesale rewrites
"""

    def _clean_content(self, content: str) -> str:
        """Clean generated content"""
        import re

        content = content.strip()

        # Remove leading/trailing quotes
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        elif content.startswith("'") and content.endswith("'"):
            content = content[1:-1]

        # Remove markdown headers
        content = content.replace("# ", "").replace("## ", "")

        # Normalize line breaks (max 2 consecutive)
        content = re.sub(r"\n{3,}", "\n\n", content)

        return content.strip()

    def _generate_changes_summary(self, original: Post, revised: Post, feedback: str) -> str:
        """Generate human-readable summary of changes

        Args:
            original: Original post
            revised: Revised post
            feedback: Client feedback

        Returns:
            Changes summary string
        """
        changes = []

        # Length change
        word_diff = revised.word_count - original.word_count
        if abs(word_diff) >= 10:
            if word_diff > 0:
                changes.append(
                    f"Expanded by {word_diff} words ({original.word_count} -> {revised.word_count})"
                )
            else:
                changes.append(
                    f"Shortened by {abs(word_diff)} words ({original.word_count} -> {revised.word_count})"
                )

        # CTA change
        if original.has_cta != revised.has_cta:
            if revised.has_cta:
                changes.append("Added call-to-action")
            else:
                changes.append("Removed call-to-action")

        # Tone detection (simple heuristics)
        original_contractions = sum(
            1
            for word in ["don't", "won't", "can't", "it's", "you're"]
            if word in original.content.lower()
        )
        revised_contractions = sum(
            1
            for word in ["don't", "won't", "can't", "it's", "you're"]
            if word in revised.content.lower()
        )

        if revised_contractions > original_contractions + 2:
            changes.append("Made tone more casual")
        elif revised_contractions < original_contractions - 2:
            changes.append("Made tone more formal")

        # Emoji detection
        import re

        original_emojis = len(re.findall(r"[😀-🙏]", original.content))
        revised_emojis = len(re.findall(r"[😀-🙏]", revised.content))

        if revised_emojis > original_emojis:
            changes.append(f"Added {revised_emojis - original_emojis} emoji(s)")
        elif revised_emojis < original_emojis:
            changes.append(f"Removed {original_emojis - revised_emojis} emoji(s)")

        # If no automatic changes detected, use feedback
        if not changes:
            changes.append(f"Applied feedback: {feedback[:60]}...")

        return "; ".join(changes)

    def create_revision_diff(
        self, original: Post, revised: Post, changes_summary: str
    ) -> RevisionDiff:
        """Create a diff object showing changes

        Args:
            original: Original post
            revised: Revised post
            changes_summary: Summary of changes

        Returns:
            RevisionDiff object
        """
        word_diff = revised.word_count - original.word_count

        changes_list = changes_summary.split("; ")

        # Simple quality improvement score (based on length optimization)
        improvement_score = None
        if abs(word_diff) < 50:  # Good length adjustment
            improvement_score = 0.8
        elif abs(word_diff) < 100:
            improvement_score = 0.6
        else:
            improvement_score = 0.5  # Large changes might need more review

        return RevisionDiff(
            post_index=original.variant,
            template_name=original.template_name,
            original_length=original.word_count,
            revised_length=revised.word_count,
            word_count_change=word_diff,
            changes=changes_list,
            improvement_score=improvement_score,
        )
