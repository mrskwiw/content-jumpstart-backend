"""Length Validator

Validates post length distribution and flags outliers.
"""

from collections import Counter
from typing import Any, Dict, List, Optional

from ..config.platform_specs import PLATFORM_LENGTH_SPECS
from ..config.settings import settings
from ..models.client_brief import Platform
from ..models.post import Post


class LengthValidator:
    """Validates post length distribution"""

    def __init__(
        self,
        min_words: int = None,
        max_words: int = None,
        optimal_min: int = None,
        optimal_max: int = None,
        sameness_threshold: float = 0.70,
    ):
        """
        Initialize length validator

        Args:
            min_words: Minimum acceptable word count
            max_words: Maximum acceptable word count
            optimal_min: Optimal minimum word count
            optimal_max: Optimal maximum word count
            sameness_threshold: Threshold for flagging too-similar lengths
        """
        self.min_words = min_words or settings.MIN_POST_WORD_COUNT
        self.max_words = max_words or settings.MAX_POST_WORD_COUNT
        self.optimal_min = optimal_min or settings.OPTIMAL_POST_MIN_WORDS
        self.optimal_max = optimal_max or settings.OPTIMAL_POST_MAX_WORDS
        self.sameness_threshold = sameness_threshold

    def validate(self, posts: List[Post]) -> Dict[str, Any]:
        """
        Validate length distribution across all posts

        Args:
            posts: List of Post objects to validate

        Returns:
            Dictionary with validation results:
            - passed: bool
            - length_distribution: Dict of length ranges and counts
            - average_length: float
            - issues: List of issue descriptions
        """
        word_counts = [p.word_count for p in posts]
        avg_length = sum(word_counts) / len(word_counts) if word_counts else 0

        # Detect platform from posts (use first post's platform, or default to LinkedIn)
        platform = self._detect_platform(posts)

        # Get platform-specific specs if platform is detected
        if platform:
            specs = PLATFORM_LENGTH_SPECS.get(platform, {})
            min_words = specs.get("min_words", self.min_words)
            max_words = specs.get("max_words", self.max_words)
            optimal_min = specs.get("optimal_min_words", self.optimal_min)
            optimal_max = specs.get("optimal_max_words", self.optimal_max)
        else:
            min_words = self.min_words
            max_words = self.max_words
            optimal_min = self.optimal_min
            optimal_max = self.optimal_max

        issues = []

        # Check for too-short posts
        too_short = [(i + 1, p.word_count) for i, p in enumerate(posts) if p.word_count < min_words]
        if too_short:
            for post_num, word_count in too_short:
                issues.append(
                    f"Post {post_num} too short: {word_count} words (min: {min_words} for {platform.value if platform else 'default'})"
                )

        # Check for too-long posts
        too_long = [(i + 1, p.word_count) for i, p in enumerate(posts) if p.word_count > max_words]
        if too_long:
            for post_num, word_count in too_long:
                issues.append(
                    f"Post {post_num} too long: {word_count} words (max: {max_words} for {platform.value if platform else 'default'})"
                )

        # Check for lack of variety (too many posts same length)
        sameness_ratio = self._check_sameness(word_counts)
        if sameness_ratio > self.sameness_threshold:
            issues.append(
                f"{sameness_ratio:.0%} of posts have very similar length (±10 words) - lacks variety"
            )

        # Check optimal range
        in_optimal = sum(1 for wc in word_counts if optimal_min <= wc <= optimal_max)
        optimal_ratio = in_optimal / len(posts) if posts else 0

        # Distribution by range
        distribution = self._calculate_distribution(word_counts)

        return {
            "passed": len(issues) == 0,
            "length_distribution": distribution,
            "average_length": round(avg_length, 1),
            "optimal_ratio": optimal_ratio,
            "sameness_ratio": sameness_ratio,
            "issues": issues,
            "metric": f"{in_optimal}/{len(posts)} posts in optimal range ({optimal_min}-{optimal_max} words for {platform.value if platform else 'default'})",
            "platform": platform.value if platform else None,
        }

    def _check_sameness(self, word_counts: List[int]) -> float:
        """
        Check if too many posts have similar length

        Args:
            word_counts: List of word counts

        Returns:
            Ratio of posts with similar length
        """
        if len(word_counts) < 2:
            return 0.0

        # Group by length buckets (±10 words)
        buckets = Counter()
        for wc in word_counts:
            # Round to nearest 10
            bucket = round(wc / 10) * 10
            buckets[bucket] += 1

        # Find largest bucket
        max_bucket_count = buckets.most_common(1)[0][1] if buckets else 0

        return max_bucket_count / len(word_counts)

    def _calculate_distribution(self, word_counts: List[int]) -> Dict[str, int]:
        """
        Calculate distribution of posts by length range

        Args:
            word_counts: List of word counts

        Returns:
            Dictionary of length ranges and counts
        """
        distribution = {
            "0-100": 0,
            "100-150": 0,
            "150-200": 0,
            "200-250": 0,
            "250-300": 0,
            "300+": 0,
        }

        for wc in word_counts:
            if wc < 100:
                distribution["0-100"] += 1
            elif wc < 150:
                distribution["100-150"] += 1
            elif wc < 200:
                distribution["150-200"] += 1
            elif wc < 250:
                distribution["200-250"] += 1
            elif wc < 300:
                distribution["250-300"] += 1
            else:
                distribution["300+"] += 1

        return distribution

    def _detect_platform(self, posts: List[Post]) -> Optional[Platform]:
        """
        Detect platform from posts

        Args:
            posts: List of Post objects

        Returns:
            Platform enum if detected, None otherwise
        """
        if not posts:
            return None

        # Check first post's target_platform field
        first_post = posts[0]
        if hasattr(first_post, "target_platform") and first_post.target_platform:
            try:
                return Platform(first_post.target_platform)
            except ValueError:
                return None

        return None
