"""
Voice matching system for Phase 8C

Compares generated content to client voice samples to ensure authenticity
"""

import statistics
from typing import List, Optional

from src.models.post import Post
from src.models.voice_guide import EnhancedVoiceGuide
from src.models.voice_sample import VoiceMatchComponentScore, VoiceMatchReport
from src.utils.voice_metrics import VoiceMetrics


class VoiceMatcher:
    """
    Compare generated posts to reference voice guide from client samples

    Calculates overall match score and component scores for:
    - Readability (Flesch Reading Ease)
    - Word count
    - Brand archetype
    - Key phrase usage
    """

    def __init__(self):
        """Initialize voice matcher with metrics analyzer"""
        self.voice_metrics = VoiceMetrics()

    def calculate_match_score(
        self, generated_posts: List[Post], reference_voice_guide: EnhancedVoiceGuide
    ) -> VoiceMatchReport:
        """
        Calculate how well generated posts match reference voice

        Args:
            generated_posts: List of generated posts to evaluate
            reference_voice_guide: Target voice from client samples

        Returns:
            VoiceMatchReport with overall score and component breakdowns
        """
        if not generated_posts:
            raise ValueError("No posts provided for matching")

        if not reference_voice_guide:
            raise ValueError("No reference voice guide provided")

        # Calculate component scores
        component_scores = []

        # 1. Readability score
        readability_score = None
        if reference_voice_guide.average_readability_score is not None:
            readability_score = self._compare_readability(
                generated_posts, reference_voice_guide.average_readability_score
            )
            component_scores.append(readability_score.score)

        # 2. Word count score
        word_count_score = None
        if reference_voice_guide.average_word_count is not None:
            word_count_score = self._compare_word_count(
                generated_posts, reference_voice_guide.average_word_count
            )
            component_scores.append(word_count_score.score)

        # 3. Archetype score
        archetype_score = None
        if reference_voice_guide.voice_archetype:
            archetype_score = self._compare_archetype(
                generated_posts, reference_voice_guide.voice_archetype
            )
            component_scores.append(archetype_score.score)

        # 4. Phrase usage score
        phrase_usage_score = None
        if reference_voice_guide.key_phrases_used:
            phrase_usage_score = self._compare_phrase_usage(
                generated_posts, reference_voice_guide.key_phrases_used
            )
            component_scores.append(phrase_usage_score.score)

        # Calculate overall score (average of components)
        overall_score = statistics.mean(component_scores) if component_scores else 0.5

        # Generate recommendations
        strengths, weaknesses, improvements = self._generate_recommendations(
            overall_score, readability_score, word_count_score, archetype_score, phrase_usage_score
        )

        return VoiceMatchReport(
            client_name=reference_voice_guide.company_name,
            match_score=overall_score,
            readability_score=readability_score,
            word_count_score=word_count_score,
            archetype_score=archetype_score,
            phrase_usage_score=phrase_usage_score,
            strengths=strengths,
            weaknesses=weaknesses,
            improvements=improvements,
        )

    def _compare_readability(
        self, posts: List[Post], target_readability: float
    ) -> VoiceMatchComponentScore:
        """Compare readability scores (±5 points acceptable)"""
        # Calculate average readability of generated posts
        readabilities = []
        for post in posts:
            score = self.voice_metrics.calculate_readability(post.content)
            readabilities.append(score)

        avg_readability = statistics.mean(readabilities)
        difference = abs(avg_readability - target_readability)

        # Score: 1.0 if within 5 points, linearly decreases to 0.0 at 20 points difference
        score = max(0.0, 1.0 - (difference / 20.0))

        return VoiceMatchComponentScore(
            component="Readability",
            score=score,
            target_value=target_readability,
            actual_value=avg_readability,
            difference=difference,
        )

    def _compare_word_count(
        self, posts: List[Post], target_word_count: int
    ) -> VoiceMatchComponentScore:
        """Compare word counts (±20% acceptable)"""
        # Calculate average word count
        avg_word_count = statistics.mean([post.word_count for post in posts])

        # Calculate percentage difference
        if target_word_count == 0:
            diff_ratio = 1.0  # Avoid division by zero
        else:
            diff_ratio = abs(avg_word_count - target_word_count) / target_word_count

        # Score: 1.0 if within 20%, linearly decreases to 0.0 at 50% difference
        score = max(0.0, 1.0 - (diff_ratio / 0.5))

        return VoiceMatchComponentScore(
            component="Word Count",
            score=score,
            target_value=float(target_word_count),
            actual_value=avg_word_count,
            difference=abs(avg_word_count - target_word_count),
        )

    def _compare_archetype(
        self, posts: List[Post], target_archetype: str
    ) -> VoiceMatchComponentScore:
        """Compare brand archetypes (binary match)"""
        # Detect archetype from generated posts
        combined_text = "\n\n".join(post.content for post in posts)

        # Use voice metrics to analyze dimensions
        dimensions = self.voice_metrics.analyze_voice_dimensions(combined_text)

        # Infer archetype from dimensions
        from src.config.brand_frameworks import infer_archetype_from_voice_dimensions

        formality = dimensions.get("formality", {}).get("dominant", "professional")
        tone = dimensions.get("tone", {}).get("dominant", "educational")
        perspective = dimensions.get("perspective", {}).get("dominant", "collaborative")

        detected_archetype = infer_archetype_from_voice_dimensions(formality, tone, perspective)

        # Binary match: 1.0 if exact match, 0.5 if different (not 0 since some overlap)
        score = 1.0 if detected_archetype.lower() == target_archetype.lower() else 0.5

        return VoiceMatchComponentScore(
            component="Brand Archetype",
            score=score,
            target_value=None,  # Categorical, not numeric
            actual_value=None,
            difference=None,
        )

    def _compare_phrase_usage(
        self, posts: List[Post], target_phrases: List[str]
    ) -> VoiceMatchComponentScore:
        """Compare key phrase usage"""
        if not target_phrases:
            return VoiceMatchComponentScore(
                component="Phrase Usage",
                score=0.5,  # Neutral score if no target phrases
                target_value=0.0,
                actual_value=0.0,
                difference=0.0,
            )

        # Count how many target phrases appear in generated posts
        combined_text = "\n\n".join(post.content for post in posts).lower()

        phrases_found = sum(1 for phrase in target_phrases if phrase.lower() in combined_text)

        # Calculate percentage of phrases used
        phrase_usage_rate = phrases_found / len(target_phrases)

        # Score: 1.0 if 50%+ phrases used, 0.0 if no phrases used
        score = min(1.0, phrase_usage_rate * 2.0)

        return VoiceMatchComponentScore(
            component="Phrase Usage",
            score=score,
            target_value=float(len(target_phrases)),
            actual_value=float(phrases_found),
            difference=float(len(target_phrases) - phrases_found),
        )

    def _generate_recommendations(
        self,
        overall_score: float,
        readability_score: Optional[VoiceMatchComponentScore],
        word_count_score: Optional[VoiceMatchComponentScore],
        archetype_score: Optional[VoiceMatchComponentScore],
        phrase_usage_score: Optional[VoiceMatchComponentScore],
    ) -> tuple[List[str], List[str], List[str]]:
        """Generate strengths, weaknesses, and improvement recommendations"""
        strengths = []
        weaknesses = []
        improvements = []

        # Overall assessment
        if overall_score >= 0.9:
            strengths.append(
                "Excellent overall voice match - indistinguishable from client samples"
            )
        elif overall_score >= 0.8:
            strengths.append("Good overall voice match with minor variations")
        elif overall_score >= 0.7:
            strengths.append("Acceptable voice match - professional quality")

        # Readability assessment
        if readability_score:
            if readability_score.score >= 0.9:
                strengths.append(
                    f"Readability perfectly matches target ({readability_score.target_value:.1f})"
                )
            elif readability_score.score < 0.7:
                weaknesses.append(
                    f"Readability differs from target (target: {readability_score.target_value:.1f}, actual: {readability_score.actual_value:.1f})"
                )
                if readability_score.actual_value > readability_score.target_value:
                    improvements.append(
                        "Make content slightly more complex to match client's style"
                    )
                else:
                    improvements.append("Simplify language to match client's easier reading level")

        # Word count assessment
        if word_count_score:
            if word_count_score.score >= 0.9:
                strengths.append(
                    f"Post length matches target well ({int(word_count_score.target_value)} words)"
                )
            elif word_count_score.score < 0.7:
                weaknesses.append(
                    f"Post length differs from target (target: {int(word_count_score.target_value)}, actual: {int(word_count_score.actual_value)})"
                )
                if word_count_score.actual_value > word_count_score.target_value:
                    improvements.append("Shorten posts to match client's typical length")
                else:
                    improvements.append("Expand posts to match client's typical length")

        # Archetype assessment
        if archetype_score:
            if archetype_score.score >= 0.9:
                strengths.append("Brand archetype perfectly aligned")
            elif archetype_score.score < 0.7:
                weaknesses.append("Brand archetype doesn't fully match client's voice")
                improvements.append(
                    "Adjust tone and perspective to better match client's archetype"
                )

        # Phrase usage assessment
        if phrase_usage_score:
            if phrase_usage_score.score >= 0.8:
                strengths.append("Good use of client's key phrases")
            elif phrase_usage_score.score < 0.5:
                weaknesses.append(
                    f"Only {int(phrase_usage_score.actual_value)} of {int(phrase_usage_score.target_value)} key phrases used"
                )
                improvements.append("Incorporate more of client's signature phrases and vocabulary")

        # Overall improvement suggestion
        if overall_score < 0.7:
            improvements.append("Consider regenerating posts with stronger voice guide emphasis")

        return strengths, weaknesses, improvements
