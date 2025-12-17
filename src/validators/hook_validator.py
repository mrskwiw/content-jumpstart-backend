"""Hook Uniqueness Validator

Detects duplicate or near-duplicate opening lines in posts.
Uses MinHash/LSH for O(n log n) performance on large post sets.
"""

import difflib
from typing import Any, Dict, List, Optional

from ..config.constants import HOOK_SIMILARITY_THRESHOLD
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
        Validate hook uniqueness across all posts

        Args:
            posts: List of Post objects to validate

        Returns:
            Dictionary with validation results:
            - passed: bool
            - duplicates: List of duplicate pairs
            - uniqueness_score: float (0.0-1.0)
            - issues: List of issue descriptions
        """
        hooks = self._extract_hooks(posts)
        duplicates = self._find_duplicates(hooks, posts)

        # Calculate uniqueness score (percentage of unique hooks)
        total_pairs = len(posts) * (len(posts) - 1) / 2  # n choose 2
        duplicate_pairs = len(duplicates)
        uniqueness_score = 1.0 - (duplicate_pairs / total_pairs if total_pairs > 0 else 0)

        issues = []
        for dup in duplicates:
            issues.append(
                f"Posts {dup['post1_idx']+1} and {dup['post2_idx']+1} have similar hooks "
                f"({dup['similarity']:.0%} similar)"
            )

        return {
            "passed": len(duplicates) == 0,
            "duplicates": duplicates,
            "uniqueness_score": uniqueness_score,
            "issues": issues,
            "metric": f"{len(posts) - len(duplicates)}/{len(posts)} unique hooks",
        }

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
