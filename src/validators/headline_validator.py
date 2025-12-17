"""Headline Engagement Validator

Validates that headlines contain engagement elements (numbers, power words, emotional triggers).
Based on blog best practices: headlines should have 3+ engagement elements.
"""

import re
from typing import Any, Dict, List, Optional

from ..config.constants import MIN_HEADLINE_ELEMENTS
from ..models.post import Post


class HeadlineValidator:
    """Validates headline engagement elements across posts"""

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
        Validate headline engagement across all posts

        Args:
            posts: List of Post objects to validate

        Returns:
            Dictionary with validation results:
            - passed: bool
            - headlines_analyzed: int
            - average_elements: float
            - below_threshold: List of post indices with weak headlines
            - issues: List of issue descriptions
        """
        headline_scores = []
        below_threshold = []
        issues = []

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
            if element_count < self.min_elements:
                below_threshold.append(idx)
                issues.append(
                    f"Post {idx+1} headline has only {element_count}/{self.min_elements} "
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
        }

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
