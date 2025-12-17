"""Keyword Validator

Validates SEO keyword usage in generated posts.
"""

import re
from typing import Any, Dict, List

from ..models.post import Post
from ..models.seo_keyword import KeywordStrategy, KeywordUsage, PostKeywordAnalysis
from ..utils.logger import logger


class KeywordValidator:
    """Validates keyword usage in posts"""

    def __init__(
        self,
        keyword_strategy: KeywordStrategy,
        max_density: float = 0.03,  # 3% max density
        min_primary_usage: float = 0.7,  # 70% of posts should have primary keyword
    ):
        """
        Initialize keyword validator

        Args:
            keyword_strategy: Client's SEO keyword strategy
            max_density: Maximum allowed keyword density
            min_primary_usage: Minimum ratio of posts with primary keywords
        """
        self.keyword_strategy = keyword_strategy
        self.max_density = max_density
        self.min_primary_usage = min_primary_usage

    def validate(self, posts: List[Post]) -> Dict[str, Any]:
        """
        Validate keyword usage across all posts

        Args:
            posts: List of generated posts

        Returns:
            Validation results dictionary
        """
        logger.info(f"Validating keyword usage across {len(posts)} posts")

        # Analyze each post
        post_analyses = []
        for idx, post in enumerate(posts, 1):
            analysis = self.analyze_post_keywords(post, idx)
            post_analyses.append(analysis)

        # Aggregate results
        total_posts = len(posts)
        posts_with_primary = sum(1 for a in post_analyses if a.has_primary_keyword)
        posts_with_stuffing = sum(1 for a in post_analyses if a.keyword_stuffing_detected)
        posts_missing_keywords = sum(1 for a in post_analyses if a.missing_primary_keywords)

        primary_usage_ratio = posts_with_primary / total_posts if total_posts > 0 else 0
        passed = primary_usage_ratio >= self.min_primary_usage and posts_with_stuffing == 0

        # Build issues list
        issues = []
        if primary_usage_ratio < self.min_primary_usage:
            issues.append(
                f"Only {posts_with_primary}/{total_posts} posts contain primary keywords "
                f"(target: {self.min_primary_usage:.0%})"
            )

        if posts_with_stuffing > 0:
            issues.append(
                f"{posts_with_stuffing} post(s) have keyword stuffing (density > {self.max_density:.1%})"
            )

        if posts_missing_keywords > 0:
            issues.append(f"{posts_missing_keywords} post(s) missing primary keywords completely")

        results = {
            "passed": passed,
            "primary_usage_ratio": primary_usage_ratio,
            "posts_with_primary": posts_with_primary,
            "posts_with_stuffing": posts_with_stuffing,
            "posts_missing_keywords": posts_missing_keywords,
            "metric": f"{posts_with_primary}/{total_posts} posts with primary keywords",
            "issues": issues,
            "post_analyses": [a.to_dict() for a in post_analyses],
        }

        logger.info(
            f"Keyword validation: {'PASSED' if passed else 'FAILED'} "
            f"(Primary usage: {primary_usage_ratio:.0%})"
        )

        return results

    def analyze_post_keywords(self, post: Post, post_id: int) -> PostKeywordAnalysis:
        """
        Analyze keyword usage in a single post

        Args:
            post: Post to analyze
            post_id: Post identifier

        Returns:
            PostKeywordAnalysis with keyword usage details
        """
        content_lower = post.content.lower()
        word_count = post.word_count

        # Analyze each keyword tier
        primary_usage = self._analyze_keyword_tier(
            content_lower, word_count, self.keyword_strategy.primary_keywords
        )
        secondary_usage = self._analyze_keyword_tier(
            content_lower, word_count, self.keyword_strategy.secondary_keywords
        )
        longtail_usage = self._analyze_keyword_tier(
            content_lower, word_count, self.keyword_strategy.longtail_keywords
        )

        # Calculate metrics
        total_count = sum(u.count for u in primary_usage + secondary_usage + longtail_usage)
        overall_density = total_count / word_count if word_count > 0 else 0

        # Quality flags
        has_primary = len(primary_usage) > 0
        keyword_stuffing = overall_density > self.max_density
        missing_primary = len(primary_usage) == 0

        analysis = PostKeywordAnalysis(
            post_id=post_id,
            template_name=post.template_name,
            primary_keywords_used=primary_usage,
            secondary_keywords_used=secondary_usage,
            longtail_keywords_used=longtail_usage,
            total_keyword_count=total_count,
            overall_keyword_density=overall_density,
            has_primary_keyword=has_primary,
            keyword_stuffing_detected=keyword_stuffing,
            missing_primary_keywords=missing_primary,
        )

        return analysis

    def _analyze_keyword_tier(
        self, content: str, word_count: int, keywords: List
    ) -> List[KeywordUsage]:
        """
        Analyze usage of keywords from a specific tier

        Args:
            content: Lowercased post content
            word_count: Total word count
            keywords: List of SEOKeyword objects

        Returns:
            List of KeywordUsage objects
        """
        usage_list = []

        for kw in keywords:
            keyword_lower = kw.keyword.lower()

            # Count occurrences (whole word matching)
            pattern = r"\b" + re.escape(keyword_lower) + r"\b"
            matches = re.findall(pattern, content)
            count = len(matches)

            if count > 0:
                # Determine locations (simplified)
                locations = []
                lines = content.split("\n")
                if lines and keyword_lower in lines[0].lower():
                    locations.append("headline")
                if keyword_lower in content[len(content) // 2 :]:
                    locations.append("body")

                # Calculate density for this keyword
                density = count / word_count if word_count > 0 else 0

                # Check if integration appears natural (basic heuristic)
                natural = density <= 0.02  # 2% or less per keyword

                usage = KeywordUsage(
                    keyword=kw.keyword,
                    count=count,
                    locations=locations,
                    density=density,
                    natural=natural,
                )
                usage_list.append(usage)

        return usage_list
