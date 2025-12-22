"""Hook Uniqueness Validator

Detects duplicate or near-duplicate opening lines in posts.
Uses MinHash/LSH for O(n log n) performance on large post sets.
"""

import difflib
from typing import Any, Dict, List, Optional

from ..config.constants import HOOK_SIMILARITY_THRESHOLD
from ..config.platform_specs import PLATFORM_HOOK_SPECS
from ..models.client_brief import Platform
from ..models.post import Post

# Optional: MinHash/LSH for performance optimization
try:
    from datasketch import MinHash, MinHashLSH

    MINHASH_AVAILABLE = True
except ImportError:
    MINHASH_AVAILABLE = False


class HookValidator:
    """Validates hook uniqueness across a set of posts

    Uses MinHash/LSH for O(n log n) performance when available,
    falls back to O(n²) algorithm for small datasets or when library unavailable.
    """

    def __init__(
        self,
        similarity_threshold: Optional[float] = None,
        use_optimized: bool = True,
        minhash_threshold: int = 50,
    ):
        """
        Initialize hook validator

        Args:
            similarity_threshold: Similarity ratio above which hooks are considered duplicates (0.0-1.0)
                                  Defaults to HOOK_SIMILARITY_THRESHOLD from constants
            use_optimized: Use optimized MinHash/LSH algorithm when available (default: True)
            minhash_threshold: Minimum post count to use MinHash (below this uses simple algorithm)
        """
        self.similarity_threshold = similarity_threshold or HOOK_SIMILARITY_THRESHOLD
        self.use_optimized = use_optimized and MINHASH_AVAILABLE
        self.minhash_threshold = minhash_threshold

    def validate(self, posts: List[Post]) -> Dict[str, Any]:
        """
        Validate hook uniqueness and platform-specific hook length requirements

        Args:
            posts: List of Post objects to validate

        Returns:
            Dictionary with validation results:
            - passed: bool (True if both uniqueness AND length requirements pass)
            - duplicates: List of duplicate pairs
            - uniqueness_score: float (0.0-1.0)
            - hook_length_issues: List of platform-specific length violations
            - issues: List of all issue descriptions (uniqueness + length)
            - metric: Combined metric string
            - platform: Detected platform (or None)
        """
        # Detect platform for platform-specific validation
        platform = self._detect_platform(posts)

        # Validate hook uniqueness (existing logic)
        hooks = self._extract_hooks(posts)
        duplicates = self._find_duplicates(hooks, posts)

        # Calculate uniqueness score (percentage of unique hooks)
        total_pairs = len(posts) * (len(posts) - 1) / 2  # n choose 2
        duplicate_pairs = len(duplicates)
        uniqueness_score = 1.0 - (duplicate_pairs / total_pairs if total_pairs > 0 else 0)

        # Validate platform-specific hook lengths (new logic)
        hook_length_violations = self._validate_hook_lengths(posts, platform)

        # Build combined issues list
        issues = []

        # Add uniqueness issues
        for dup in duplicates:
            issues.append(
                f"Posts {dup['post1_idx']+1} and {dup['post2_idx']+1} have similar hooks "
                f"({dup['similarity']:.0%} similar)"
            )

        # Add hook length issues
        for violation in hook_length_violations:
            issues.append(
                f"Post {violation['post_idx']+1}: {violation['violation']}"
            )

        # Build metric string
        unique_count = len(posts) - len(duplicates)
        length_pass_count = len(posts) - len(hook_length_violations)

        if platform:
            metric = (
                f"{unique_count}/{len(posts)} unique hooks, "
                f"{length_pass_count}/{len(posts)} meet {platform.value} hook length requirements"
            )
        else:
            metric = f"{unique_count}/{len(posts)} unique hooks"

        return {
            "passed": len(duplicates) == 0 and len(hook_length_violations) == 0,
            "duplicates": duplicates,
            "uniqueness_score": uniqueness_score,
            "hook_length_issues": hook_length_violations,
            "issues": issues,
            "metric": metric,
            "platform": platform.value if platform else None,
        }

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
            # Handle both Platform enum (new) and string (backward compatibility)
            if isinstance(first_post.target_platform, Platform):
                return first_post.target_platform  # Already an enum
            try:
                return Platform(first_post.target_platform)  # Convert string to enum
            except ValueError:
                return None

        return None

    def _extract_hooks(self, posts: List[Post]) -> List[str]:
        """
        Extract first line (hook) from each post

        Args:
            posts: List of Post objects

        Returns:
            List of hook strings
        """
        hooks = []
        for post in posts:
            # Get first line, strip whitespace
            lines = post.content.strip().split("\n")
            hook = lines[0].strip() if lines else ""
            hooks.append(hook)

        return hooks

    def _validate_hook_lengths(
        self, posts: List[Post], platform: Optional[Platform]
    ) -> List[Dict[str, Any]]:
        """
        Validate hook lengths against platform-specific requirements

        Args:
            posts: List of Post objects
            platform: Platform enum (LinkedIn, Twitter, Facebook, Blog, Email)

        Returns:
            List of hook length violations with details
        """
        if not platform or platform not in PLATFORM_HOOK_SPECS:
            # Skip validation if platform not detected or not in specs
            return []

        hook_spec = PLATFORM_HOOK_SPECS[platform]
        violations = []

        for i, post in enumerate(posts):
            # Extract hook based on platform type
            if platform == Platform.BLOG:
                # Blog: First paragraph (up to double newline or 50 words)
                content = post.content.strip()
                paragraphs = content.split("\n\n")
                hook = paragraphs[0] if paragraphs else content
                hook_word_count = len(hook.split())
                max_words = hook_spec.get("hook_max_words", 50)

                if hook_word_count > max_words:
                    violations.append(
                        {
                            "post_idx": i,
                            "hook_length": hook_word_count,
                            "max_allowed": max_words,
                            "unit": "words",
                            "violation": f"Hook too long for {platform.value} ({hook_word_count} > {max_words} words)",
                        }
                    )
            else:
                # Social platforms: First line or entire post (whichever is shorter)
                lines = post.content.strip().split("\n")
                first_line = lines[0].strip() if lines else ""

                # For Twitter/Facebook, entire post might be shorter than first line
                # (if post is single line with no breaks)
                if platform in [Platform.TWITTER, Platform.FACEBOOK]:
                    # Use entire post if it's shorter than arbitrary "first line" split
                    hook = post.content.strip() if len(post.content.strip()) < len(first_line) + 50 else first_line
                else:
                    hook = first_line

                hook_char_count = len(hook)
                max_chars = hook_spec.get("hook_max_chars", 140)

                if hook_char_count > max_chars:
                    violations.append(
                        {
                            "post_idx": i,
                            "hook_length": hook_char_count,
                            "max_allowed": max_chars,
                            "unit": "characters",
                            "violation": f"Hook too long for {platform.value} ({hook_char_count} > {max_chars} chars)",
                        }
                    )

        return violations

    def _find_duplicates(self, hooks: List[str], posts: List[Post]) -> List[Dict[str, Any]]:
        """
        Find duplicate or near-duplicate hooks

        Uses optimized MinHash/LSH algorithm for large datasets (O(n log n)),
        falls back to simple pairwise comparison for small datasets (O(n²)).

        Args:
            hooks: List of hook strings
            posts: List of Post objects (for indexing)

        Returns:
            List of duplicate pairs with similarity scores
        """
        # Use optimized algorithm for large datasets
        if self.use_optimized and len(hooks) >= self.minhash_threshold:
            return self._find_duplicates_optimized(hooks, posts)

        # Use simple algorithm for small datasets or when optimization unavailable
        return self._find_duplicates_simple(hooks, posts)

    def _find_duplicates_simple(self, hooks: List[str], posts: List[Post]) -> List[Dict[str, Any]]:
        """
        Simple O(n²) pairwise comparison algorithm

        Used for small datasets (< 50 posts) or when MinHash unavailable.

        Args:
            hooks: List of hook strings
            posts: List of Post objects (for indexing)

        Returns:
            List of duplicate pairs with similarity scores
        """
        duplicates = []

        for i in range(len(hooks)):
            for j in range(i + 1, len(hooks)):
                similarity = self._calculate_similarity(hooks[i], hooks[j])

                if similarity >= self.similarity_threshold:
                    duplicates.append(
                        {
                            "post1_idx": i,
                            "post2_idx": j,
                            "hook1": hooks[i],
                            "hook2": hooks[j],
                            "similarity": similarity,
                            "post1_template": posts[i].template_name,
                            "post2_template": posts[j].template_name,
                        }
                    )

        return duplicates

    def _find_duplicates_optimized(
        self, hooks: List[str], posts: List[Post]
    ) -> List[Dict[str, Any]]:
        """
        Optimized O(n log n) duplicate detection using MinHash/LSH

        Uses Locality-Sensitive Hashing to find candidate pairs efficiently,
        then verifies with exact similarity calculation.

        Args:
            hooks: List of hook strings
            posts: List of Post objects (for indexing)

        Returns:
            List of duplicate pairs with similarity scores
        """
        if not MINHASH_AVAILABLE:
            # Fallback to simple algorithm
            return self._find_duplicates_simple(hooks, posts)

        # Initialize LSH index with similarity threshold
        # num_perm controls accuracy (higher = more accurate but slower)
        lsh = MinHashLSH(threshold=self.similarity_threshold, num_perm=128)
        minhashes = {}

        # Build MinHash index - O(n)
        for i, hook in enumerate(hooks):
            if not hook or not hook.strip():
                continue

            m = MinHash(num_perm=128)
            # Tokenize by words and add to MinHash
            words = hook.lower().split()
            for word in words:
                m.update(word.encode("utf-8"))

            key = f"hook_{i}"
            lsh.insert(key, m)
            minhashes[key] = m

        # Query for duplicates - O(n log n) average case
        duplicates = []
        seen_pairs = set()

        for i, hook in enumerate(hooks):
            if not hook or not hook.strip():
                continue

            key = f"hook_{i}"
            if key not in minhashes:
                continue

            # Find candidate matches using LSH
            candidates = lsh.query(minhashes[key])

            for candidate_key in candidates:
                j = int(candidate_key.split("_")[1])

                # Skip self-matches and already-seen pairs
                if i >= j or (i, j) in seen_pairs:
                    continue

                # Verify with exact similarity calculation
                similarity = self._calculate_similarity(hooks[i], hooks[j])

                if similarity >= self.similarity_threshold:
                    duplicates.append(
                        {
                            "post1_idx": i,
                            "post2_idx": j,
                            "hook1": hooks[i],
                            "hook2": hooks[j],
                            "similarity": similarity,
                            "post1_template": posts[i].template_name,
                            "post2_template": posts[j].template_name,
                        }
                    )
                    seen_pairs.add((i, j))

        return duplicates

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Similarity ratio (0.0-1.0)
        """
        # Use SequenceMatcher for fuzzy matching
        return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
