"""Memory Learning Agent

Automatically learns from completed projects to optimize future content generation.
Tracks template performance, voice patterns, feedback themes, and quality profiles.
"""

from typing import Dict, List, Optional

from ..database.project_db import ProjectDatabase
from ..models.client_memory import ClientMemory, FeedbackTheme, VoiceSample
from ..models.post import Post
from ..models.project import Project, Revision
from ..models.voice_guide import EnhancedVoiceGuide
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class MemoryLearningAgent:
    """Agent that learns from project outcomes to improve future generations"""

    def __init__(self, db: ProjectDatabase):
        """Initialize learning agent

        Args:
            db: Project database instance
        """
        self.db = db

    def learn_from_project(
        self, project: Project, posts: List[Post], voice_guide: Optional[EnhancedVoiceGuide] = None
    ) -> ClientMemory:
        """Learn from a completed project

        Args:
            project: Completed project
            posts: Generated posts
            voice_guide: Voice guide (if available)

        Returns:
            Updated client memory
        """
        logger.info(f"Learning from project: {project.project_id}")

        # Get or create client memory
        memory = self.db.get_or_create_client_memory(project.client_name)

        # Update project stats
        memory.add_project(
            num_posts=project.num_posts,
            project_value=0.0,  # TODO: Add project value to Project model
            project_date=project.created_at,
        )

        # Learn from voice guide
        if voice_guide:
            self._learn_from_voice_guide(memory, voice_guide, project.project_id)

        # Learn from template usage (which templates were used)
        self._learn_from_template_usage(memory, posts, project.client_name)

        # Save updated memory
        self.db.update_client_memory(memory)

        logger.info(f"Learned from project. Client now has {memory.total_projects} projects")

        return memory

    def learn_from_revision(
        self, revision: Revision, memory: Optional[ClientMemory] = None
    ) -> ClientMemory:
        """Learn from a revision request

        Args:
            revision: Revision request
            memory: Existing client memory (optional)

        Returns:
            Updated client memory
        """
        logger.info(f"Learning from revision: {revision.revision_id}")

        # Get project to find client name
        project = self.db.get_project(revision.project_id)
        if not project:
            logger.warning(f"Project not found for revision: {revision.project_id}")
            return memory or ClientMemory(client_name="Unknown")

        # Get or create memory
        if memory is None:
            memory = self.db.get_or_create_client_memory(project.client_name)

        # Update revision count
        memory.add_revisions(1)

        # Extract feedback themes from revision feedback
        themes = self._extract_feedback_themes(revision.feedback)
        for theme in themes:
            self.db.record_feedback_theme(project.client_name, theme)

        # Get revised posts to update template performance
        revised_posts = self.db.get_revision_posts(revision.revision_id)
        for post_data in revised_posts:
            # Mark this template as revised for this client
            self.db.update_template_performance(
                client_name=project.client_name,
                template_id=post_data["template_id"],
                was_revised=True,
                quality_score=0.0,  # No quality score for revisions
            )

        # Save updated memory
        self.db.update_client_memory(memory)

        logger.info(f"Learned from revision. Total revisions: {memory.total_revisions}")

        return memory

    def _learn_from_voice_guide(
        self, memory: ClientMemory, voice_guide: EnhancedVoiceGuide, project_id: str
    ) -> None:
        """Extract learnings from voice guide

        Args:
            memory: Client memory to update
            voice_guide: Voice guide from project
            project_id: Project ID
        """
        logger.debug(f"Learning from voice guide for project: {project_id}")

        # Extract simple lists from VoicePattern objects
        hooks = []
        if voice_guide.common_opening_hooks:
            for pattern in voice_guide.common_opening_hooks[:3]:
                hooks.extend(pattern.examples[:2])

        transitions = []
        if voice_guide.common_transitions:
            for pattern in voice_guide.common_transitions[:3]:
                transitions.extend(pattern.examples[:2])

        ctas = []
        if voice_guide.common_ctas:
            for pattern in voice_guide.common_ctas[:3]:
                ctas.extend(pattern.examples[:2])

        # Create voice sample
        voice_sample = VoiceSample(
            client_name=memory.client_name,
            project_id=project_id,
            average_readability=voice_guide.average_readability_score,
            voice_archetype=voice_guide.voice_archetype,
            dominant_tone=voice_guide.dominant_tones[0] if voice_guide.dominant_tones else "",
            average_word_count=voice_guide.average_word_count,
            question_usage_rate=voice_guide.question_usage_rate,
            common_hooks=hooks[:5],
            common_transitions=transitions[:5],
            common_ctas=ctas[:5],
            key_phrases=voice_guide.key_phrases_used[:10] if voice_guide.key_phrases_used else [],
        )

        # Store voice sample
        self.db.store_voice_sample(voice_sample)

        # Update memory's aggregated voice patterns
        if voice_guide.voice_archetype and not memory.voice_archetype:
            # First project sets archetype
            memory.voice_archetype = voice_guide.voice_archetype

        if voice_guide.average_readability_score:
            if memory.average_readability_score is None:
                memory.average_readability_score = voice_guide.average_readability_score
            else:
                # Running average
                total = memory.total_projects
                memory.average_readability_score = (
                    memory.average_readability_score * (total - 1)
                    + voice_guide.average_readability_score
                ) / total

        # Update signature phrases (keep unique phrases)
        if voice_guide.key_phrases_used:
            existing = set(memory.signature_phrases)
            new_phrases = [p for p in voice_guide.key_phrases_used if p not in existing]
            memory.signature_phrases.extend(new_phrases[:5])  # Add up to 5 new phrases

        logger.debug(f"Voice guide learning complete. Archetype: {memory.voice_archetype}")

    def _learn_from_template_usage(
        self, memory: ClientMemory, posts: List[Post], client_name: str
    ) -> None:
        """Learn from template usage patterns

        Args:
            memory: Client memory to update
            posts: Posts from project
            client_name: Client name
        """
        logger.debug(f"Learning from {len(posts)} posts")

        # Count template usage
        template_usage: Dict[int, int] = {}
        for post in posts:
            template_id = post.template_id
            template_usage[template_id] = template_usage.get(template_id, 0) + 1

        # Update template performance (initially, no revisions)
        for template_id, count in template_usage.items():
            for _ in range(count):
                self.db.update_template_performance(
                    client_name=client_name,
                    template_id=template_id,
                    was_revised=False,  # Not revised (yet)
                    quality_score=8.0,  # Default quality for accepted posts
                )

        logger.debug(f"Template usage learned: {len(template_usage)} unique templates")

    def _extract_feedback_themes(self, feedback: str) -> List[FeedbackTheme]:
        """Extract structured themes from revision feedback

        Args:
            feedback: Free-form revision feedback

        Returns:
            List of detected feedback themes
        """
        themes = []

        feedback_lower = feedback.lower()

        # Tone adjustments
        tone_patterns = {
            "more casual": ["more casual", "less formal", "friendly", "conversational"],
            "more professional": ["more professional", "more formal", "less casual"],
            "more direct": ["more direct", "get to the point", "shorter intro"],
            "more warm": ["more warm", "warmer", "friendlier"],
        }

        for phrase, keywords in tone_patterns.items():
            if any(kw in feedback_lower for kw in keywords):
                themes.append(FeedbackTheme(theme_type="tone", feedback_phrase=phrase))
                break  # Only one tone adjustment per feedback

        # Length adjustments
        if any(kw in feedback_lower for kw in ["too long", "shorter", "more concise"]):
            themes.append(FeedbackTheme(theme_type="length", feedback_phrase="too long"))
        elif any(kw in feedback_lower for kw in ["too short", "longer", "more detail"]):
            themes.append(FeedbackTheme(theme_type="length", feedback_phrase="too short"))

        # CTA adjustments
        if any(kw in feedback_lower for kw in ["cta", "call to action", "call-to-action"]):
            if any(kw in feedback_lower for kw in ["stronger", "clearer", "more direct"]):
                themes.append(FeedbackTheme(theme_type="cta", feedback_phrase="stronger cta"))
            elif "remove" in feedback_lower or "no cta" in feedback_lower:
                themes.append(FeedbackTheme(theme_type="cta", feedback_phrase="remove cta"))

        # Data usage
        if any(
            kw in feedback_lower
            for kw in ["more data", "add stats", "add numbers", "more stats", "stats and numbers"]
        ):
            themes.append(FeedbackTheme(theme_type="data_usage", feedback_phrase="add more data"))
        elif any(kw in feedback_lower for kw in ["less data", "remove stats", "too many numbers"]):
            themes.append(FeedbackTheme(theme_type="data_usage", feedback_phrase="less data"))

        # Emoji
        if any(
            kw in feedback_lower
            for kw in ["add emoji", "add emojis", "add some emoji", "use emoji", "some emoji"]
        ):
            themes.append(FeedbackTheme(theme_type="emoji", feedback_phrase="add emoji"))
        elif any(kw in feedback_lower for kw in ["remove emoji", "no emoji", "no emojis"]):
            themes.append(FeedbackTheme(theme_type="emoji", feedback_phrase="remove emoji"))

        # Structure
        if any(kw in feedback_lower for kw in ["better structure", "reorganize", "flow"]):
            themes.append(
                FeedbackTheme(theme_type="structure", feedback_phrase="improve structure")
            )

        logger.debug(f"Extracted {len(themes)} themes from feedback")

        return themes

    def synthesize_multi_project_learnings(self, client_name: str) -> ClientMemory:
        """Synthesize learnings across multiple projects for a client

        Args:
            client_name: Client name

        Returns:
            Updated client memory with synthesized patterns
        """
        logger.info(f"Synthesizing multi-project learnings for: {client_name}")

        memory = self.db.get_client_memory(client_name)
        if not memory or memory.total_projects < 2:
            logger.info("Not enough projects to synthesize (need 2+)")
            return memory

        # Get template performance
        perf = self.db.get_template_performance(client_name)

        # Identify preferred templates (low revision rate, used 2+ times)
        preferred = []
        avoided = []

        for template_id, data in perf.items():
            if data["usage_count"] >= 2:
                if data["revision_rate"] <= 0.2:
                    preferred.append(template_id)
                elif data["revision_rate"] >= 0.5:
                    avoided.append(template_id)

        memory.preferred_templates = preferred
        memory.avoided_templates = avoided

        # Get all feedback themes
        themes = self.db.get_feedback_themes(client_name)

        # Convert recurring themes to voice adjustments
        theme_counts = {}
        for theme in themes:
            key = f"{theme.theme_type}:{theme.feedback_phrase}"
            theme_counts[key] = theme.occurrence_count

        # If a theme appears 2+ times, add to voice adjustments
        for key, count in theme_counts.items():
            if count >= 2:
                theme_type, phrase = key.split(":", 1)
                memory.voice_adjustments[theme_type] = phrase

        # Get voice samples to find consistent patterns
        voice_samples = self.db.get_voice_samples(client_name, limit=10)

        # Calculate average word count from voice samples
        if voice_samples:
            avg_words = sum(s.average_word_count for s in voice_samples) / len(voice_samples)
            if avg_words > 0:
                # Set optimal word count based on actual usage
                if avg_words < 200:
                    memory.optimal_word_count_min = 100
                    memory.optimal_word_count_max = 200
                elif avg_words > 300:
                    memory.optimal_word_count_min = 250
                    memory.optimal_word_count_max = 350
                else:
                    memory.optimal_word_count_min = 150
                    memory.optimal_word_count_max = 250

        # Save synthesized memory
        self.db.update_client_memory(memory)

        logger.info(
            f"Synthesis complete. Preferred templates: {len(preferred)}, Voice adjustments: {len(memory.voice_adjustments)}"
        )

        return memory

    def get_memory_insights(self, client_name: str) -> Dict:
        """Get human-readable insights about client memory

        Args:
            client_name: Client name

        Returns:
            Dictionary of insights
        """
        memory = self.db.get_client_memory(client_name)
        if not memory:
            return {"error": "Client not found"}

        insights = {
            "client_name": client_name,
            "total_projects": memory.total_projects,
            "is_repeat_client": memory.is_repeat_client,
            "is_high_value": memory.is_high_value_client,
            "avg_revisions_per_project": memory.avg_revisions_per_project,
            "lifetime_value": f"${memory.lifetime_value:.2f}",
            "preferred_templates": memory.preferred_templates,
            "avoided_templates": memory.avoided_templates,
            "voice_adjustments": memory.voice_adjustments,
            "optimal_word_count": f"{memory.optimal_word_count_min}-{memory.optimal_word_count_max} words",
            "voice_archetype": memory.voice_archetype,
            "signature_phrases": memory.signature_phrases,
        }

        # Get top feedback themes
        themes = self.db.get_feedback_themes(client_name)
        if themes:
            top_themes = [(t.theme_type, t.feedback_phrase, t.occurrence_count) for t in themes[:5]]
            insights["top_feedback_themes"] = top_themes

        # Get template performance summary
        perf = self.db.get_template_performance(client_name)
        if perf:
            best_templates = sorted(
                [(tid, data["revision_rate"]) for tid, data in perf.items()], key=lambda x: x[1]
            )[:5]
            insights["best_templates"] = [(tid, f"{rate:.1%}") for tid, rate in best_templates]

        return insights
