"""Headline Engagement Validator

Validates that headlines contain engagement elements (numbers, power words, emotional triggers).
Based on blog best practices: headlines should have 3+ engagement elements.
"""

import re
from typing import Any, Dict, List, Optional

from ..config.constants import MIN_HEADLINE_ELEMENTS
from ..models.client_brief import Platform
from ..models.post import Post


class HeadlineValidator:
    """Validates headline engagement elements across posts"""

    # Platform-specific minimum engagement elements
    PLATFORM_MIN_ELEMENTS = {
        Platform.LINKEDIN: 2,  # Professional but engaging hooks
        Platform.TWITTER: 1,  # Brevity prioritized
        Platform.FACEBOOK: 1,  # Ultra-concise, emotion/visual focus
        Platform.BLOG: 3,  # SEO-focused, click-through optimization
        Platform.EMAIL: 2,  # Subject-line style, curiosity triggers
    }

    # Power words that trigger engagement
    POWER_WORDS = {
        "secret",
        "hidden",
        "proven",
        "ultimate",
        "essential",
        "critical",
        "simple",
        "easy",
        "quick",
        "fast",
        "instant",
        "effortless",
        "amazing",
        "incredible",
        "shocking",
        "surprising",
        "stunning",
        "complete",
        "comprehensive",
        "definitive",
        "master",
        "expert",
        "free",
        "guaranteed",
        "powerful",
        "effective",
        "exclusive",
        "breakthrough",
        "revolutionary",
        "game-changing",
        "transformative",
        "essential",
        "crucial",
        "vital",
        "important",
        "key",
        "must-know",
    }

    # Emotional trigger words
    EMOTIONAL_TRIGGERS = {
        "struggle",
        "frustrated",
        "worried",
        "anxious",
        "afraid",
        "fear",
        "love",
        "hate",
        "anger",
        "joy",
        "excited",
        "thrilled",
        "confusing",
        "overwhelming",
        "stressful",
        "painful",
        "difficult",
        "success",
        "failure",
        "win",
        "lose",
        "mistake",
        "wrong",
        "breakthrough",
        "discovery",
        "revelation",
        "insight",
        "truth",
        "warning",
        "alert",
        "danger",
        "risk",
        "threat",
        "opportunity",
    }

    # Question words that indicate curiosity triggers
    QUESTION_WORDS = {"how", "why", "what", "when", "where", "which", "who"}

    def __init__(self, min_elements: Optional[int] = None):
        """
        Initialize headline validator

        Args:
            min_elements: Minimum engagement elements required
                         Defaults to MIN_HEADLINE_ELEMENTS from constants
        """
        self.min_elements = min_elements or MIN_HEADLINE_ELEMENTS

    def validate(self, posts: List[Post]) -> Dict[str, Any]:
        """
        Validate headline engagement across all posts (platform-aware)

        Args:
            posts: List of Post objects to validate

        Returns:
            Dictionary with validation results:
            - passed: bool
            - headlines_analyzed: int
            - average_elements: float
            - below_threshold: List of post indices with weak headlines
            - issues: List of issue descriptions
            - platform: Detected platform (or None)
        """
        # Detect platform for platform-specific threshold
        platform = self._detect_platform(posts)

        # Use platform-specific threshold if available
        if platform and platform in self.PLATFORM_MIN_ELEMENTS:
            min_elements = self.PLATFORM_MIN_ELEMENTS[platform]
        else:
            min_elements = self.min_elements

        headline_scores: List[Dict[str, Any]] = []
        below_threshold: List[int] = []
        issues: List[str] = []

        for idx, post in enumerate(posts):
            # Extract headline (first line)
            lines = post.content.strip().split("\n")
            headline = lines[0].strip() if lines else ""

            # Count engagement elements
            element_count = self._count_engagement_elements(headline)
            headline_scores.append(
                {
                    "post_idx": idx,
                    "headline": headline,
                    "elements": element_count,
                    "details": self._get_element_details(headline),
                }
            )

            # Flag if below threshold
            if element_count < min_elements:
                below_threshold.append(idx)
                issues.append(
                    f"Post {idx+1} headline has only {element_count}/{min_elements} "
                    f"engagement elements: '{headline[:60]}...'"
                )

        # Calculate average
        avg_elements = sum(s["elements"] for s in headline_scores) / len(posts) if posts else 0

        return {
            "passed": len(below_threshold) == 0,
            "headlines_analyzed": len(posts),
            "average_elements": avg_elements,
            "below_threshold_count": len(below_threshold),
            "below_threshold_posts": below_threshold,
            "headline_scores": headline_scores,
            "issues": issues,
            "metric": f"{len(posts) - len(below_threshold)}/{len(posts)} headlines meet threshold",
            "platform": platform.value if platform else None,
            "min_elements": min_elements,
        }

    def _detect_platform(self, posts: List[Post]) -> Optional[Platform]:
        """Detect platform from posts"""
        if not posts:
            return None
        first_post = posts[0]
        if hasattr(first_post, "target_platform") and first_post.target_platform:
            if isinstance(first_post.target_platform, Platform):
                return first_post.target_platform
            try:
                return Platform(first_post.target_platform)
            except ValueError:
                return None
        return None

    def _count_engagement_elements(self, headline: str) -> int:
        """
        Count engagement elements in headline

        Args:
            headline: Headline text

        Returns:
            Number of engagement elements found
        """
        headline_lower = headline.lower()
        element_count = 0

        # Check for numbers (dates, stats, list counts)
        if re.search(r"\d+", headline):
            element_count += 1

        # Check for power words
        for word in self.POWER_WORDS:
            if re.search(r"\b" + word + r"\b", headline_lower):
                element_count += 1
                break  # Count power words as single element

        # Check for emotional triggers
        for word in self.EMOTIONAL_TRIGGERS:
            if re.search(r"\b" + word + r"\b", headline_lower):
                element_count += 1
                break  # Count emotional triggers as single element

        # Check for question format
        if headline.strip().endswith("?"):
            element_count += 1

        # Check for curiosity triggers (question words)
        for word in self.QUESTION_WORDS:
            if re.search(r"\b" + word + r"\b", headline_lower):
                element_count += 1
                break  # Count question words as single element

        # Check for specificity (mentions specific tools, people, industries)
        # Look for proper nouns (capitalized words that aren't at start)
        proper_nouns = re.findall(r"(?<!\A)\b[A-Z][a-z]+\b", headline)
        if proper_nouns:
            element_count += 1

        return element_count

    def _get_element_details(self, headline: str) -> Dict[str, bool]:
        """
        Get detailed breakdown of engagement elements

        Args:
            headline: Headline text

        Returns:
            Dictionary of element types and whether they're present
        """
        headline_lower = headline.lower()

        details = {
            "has_number": bool(re.search(r"\d+", headline)),
            "has_power_word": any(
                re.search(r"\b" + word + r"\b", headline_lower) for word in self.POWER_WORDS
            ),
            "has_emotional_trigger": any(
                re.search(r"\b" + word + r"\b", headline_lower) for word in self.EMOTIONAL_TRIGGERS
            ),
            "is_question": headline.strip().endswith("?"),
            "has_question_word": any(
                re.search(r"\b" + word + r"\b", headline_lower) for word in self.QUESTION_WORDS
            ),
            "has_specificity": bool(re.findall(r"(?<!\A)\b[A-Z][a-z]+\b", headline)),
        }

        return details
