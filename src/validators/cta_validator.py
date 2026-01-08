"""CTA Variety Validator

Ensures CTAs vary across posts and aren't overused.
"""

import re
from collections import Counter
from typing import Any, Dict, List, Optional

from ..config.constants import CTA_VARIETY_THRESHOLD
from ..models.client_brief import Platform
from ..models.post import Post


class CTAValidator:
    """Validates CTA variety across a set of posts"""

    # Platform-specific variety thresholds
    PLATFORM_VARIETY_THRESHOLDS = {
        Platform.LINKEDIN: 0.40,  # 40% max - more variety needed
        Platform.TWITTER: 0.50,  # 50% max - fewer CTA types available
        Platform.FACEBOOK: 0.50,  # 50% max - ultra-concise
        Platform.BLOG: 0.60,  # 60% max - can repeat subscribe/download
        Platform.EMAIL: 0.70,  # 70% max - campaign-focused, single CTA type
    }

    # Common CTA patterns to detect
    CTA_PATTERNS = [
        (r"what(?:'s| is) your (?:take|thoughts?|experience)", "question_take"),
        (r"(?:drop|share|leave) (?:your|a) comment", "comment_request"),
        (r"(?:dm|message|reach out|contact) me", "direct_contact"),
        (r"reply (?:with|below)", "reply_request"),
        (r"(?:click|tap|check out) (?:the )?link", "link_click"),
        (r"(?:book|schedule|set up) (?:a )?(?:call|meeting|demo)", "booking"),
        (r"sign up|subscribe|join", "signup"),
        (r"download|get (?:the |your )", "download"),
        (r"learn more|find out", "learn_more"),
        (r"what(?:'s| is) (?:your|the) biggest", "question_biggest"),
        (r"(?:tell|share) me (?:in|about)", "share_request"),
        (r"curious (?:what|if|how)", "curious_question"),
        (r"does this (?:ring true|resonate|sound familiar)", "resonance_check"),
    ]

    def __init__(self, variety_threshold: Optional[float] = None):
        """
        Initialize CTA validator

        Args:
            variety_threshold: Maximum percentage of posts that can use the same CTA (0.0-1.0)
                              Defaults to CTA_VARIETY_THRESHOLD from constants
        """
        self.variety_threshold = variety_threshold or CTA_VARIETY_THRESHOLD

    def validate(self, posts: List[Post]) -> Dict[str, Any]:
        """
        Validate CTA variety across all posts (platform-aware)

        Args:
            posts: List of Post objects to validate

        Returns:
            Dictionary with validation results:
            - passed: bool
            - cta_distribution: Dict of CTA types and counts
            - variety_score: float (0.0-1.0)
            - issues: List of issue descriptions
            - platform: Detected platform (or None)
        """
        # Detect platform for platform-specific threshold
        platform = self._detect_platform(posts)

        # Use platform-specific threshold if available
        if platform and platform in self.PLATFORM_VARIETY_THRESHOLDS:
            variety_threshold = self.PLATFORM_VARIETY_THRESHOLDS[platform]
        else:
            variety_threshold = self.variety_threshold

        cta_types = self._extract_cta_types(posts)
        cta_counts = Counter(cta_types)

        # Calculate variety score (entropy-based)
        variety_score = self._calculate_variety_score(cta_counts, len(posts))

        # Check for overused CTAs
        issues = []
        max_allowed = int(len(posts) * variety_threshold)

        for cta_type, count in cta_counts.most_common():
            if count > max_allowed:
                percentage = (count / len(posts)) * 100
                issues.append(
                    f"CTA pattern '{cta_type}' overused: {count}/{len(posts)} posts ({percentage:.0f}%)"
                )

        # Check for posts without CTAs
        missing_cta = sum(1 for ct in cta_types if ct == "no_cta")
        if missing_cta > 0:
            issues.append(f"{missing_cta} post(s) missing clear CTA")

        return {
            "passed": len(issues) == 0,
            "cta_distribution": dict(cta_counts),
            "variety_score": variety_score,
            "issues": issues,
            "metric": f"{len(cta_counts)} unique CTA types across {len(posts)} posts",
            "platform": platform.value if platform else None,
            "variety_threshold": variety_threshold,
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
                pass
        return None

    def _extract_cta_types(self, posts: List[Post]) -> List[str]:
        """
        Extract CTA type from each post

        Args:
            posts: List of Post objects

        Returns:
            List of CTA type strings
        """
        cta_types = []

        for post in posts:
            # Get last 2 lines (where CTAs usually are)
            lines = post.content.strip().split("\n")
            cta_section = "\n".join(lines[-2:]).lower()

            # Match against patterns
            cta_type = "no_cta"
            for pattern, type_name in self.CTA_PATTERNS:
                if re.search(pattern, cta_section, re.IGNORECASE):
                    cta_type = type_name
                    break

            cta_types.append(cta_type)

        return cta_types

    def _calculate_variety_score(self, cta_counts: Counter, total_posts: int) -> float:
        """
        Calculate variety score based on distribution

        Args:
            cta_counts: Counter of CTA types
            total_posts: Total number of posts

        Returns:
            Variety score (0.0-1.0) where 1.0 is perfect variety
        """
        if total_posts == 0:
            return 1.0

        # Calculate normalized entropy
        # Perfect variety = each CTA used equally
        # Poor variety = one CTA dominates

        max_count = cta_counts.most_common(1)[0][1] if cta_counts else 0
        min_variety = max_count / total_posts  # Percentage of most common CTA

        # Inverse: lower dominance = higher variety
        variety_score = 1.0 - (min_variety - (1.0 / len(cta_counts)) if cta_counts else 0)

        return max(0.0, min(1.0, variety_score))
