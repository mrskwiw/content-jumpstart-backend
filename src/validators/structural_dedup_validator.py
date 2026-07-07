"""Structural Deduplication Validator

Detects repeated mid-post story scaffolds (e.g., "one of our clients told us")
across posts in a run. Complements HookValidator's opening-line MinHash/LSH by
checking sentence-level structural patterns anywhere in the post body.

Phase 1: MinHash fingerprinting of structurally-matched sentences.
"""

import re
from typing import Any, Dict, List, Tuple

from ..models.post import Post

try:
    from datasketch import MinHash  # type: ignore[import-untyped]

    _MINHASH_AVAILABLE = True
except ImportError:
    _MINHASH_AVAILABLE = False

# (compiled_pattern, scaffold_label) — match against individual sentences
_STRUCTURAL_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(
            r"\bone\s+of\s+(our|my)\s+(clients?|patients?|customers?)\s+told\s+us",
            re.IGNORECASE,
        ),
        "client-told-us scaffold",
    ),
    (
        re.compile(
            r"\bone\s+of\s+(our|my)\s+(clients?|patients?|customers?)\s+(mentioned|shared|said|asked)",
            re.IGNORECASE,
        ),
        "client-mentioned scaffold",
    ),
    (
        re.compile(
            r"\b(I\s+recently|just)\s+(spoke\s+with|talked\s+to|met\s+with)\s+a\s+(client|patient|prospect|customer)",
            re.IGNORECASE,
        ),
        "first-person-client-encounter scaffold",
    ),
    (
        re.compile(
            r"\b(last|this)\s+(month|week|quarter)\s+.{0,30}(client|customer|patient)\s+(told|shared|asked|said)",
            re.IGNORECASE,
        ),
        "time-anchored client quote",
    ),
    (
        re.compile(
            r"\b(years?\s+from\s+now|by\s+20\d{2})\b.{0,60}\b(will|won.t|won.t\s+be|no\s+longer)",
            re.IGNORECASE,
        ),
        "future-prediction scaffold",
    ),
]

_SIMILARITY_THRESHOLD = 0.6  # Jaccard similarity above which two sentences are "the same structure"


def _shingle(text: str, k: int = 3) -> List[str]:
    """Return k-word shingles from text."""
    words = re.findall(r"\w+", text.lower())
    if len(words) < k:
        return words
    return [" ".join(words[i : i + k]) for i in range(len(words) - k + 1)]


def _jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _minhash_similarity(a_shingles: List[str], b_shingles: List[str]) -> float:
    if not _MINHASH_AVAILABLE:
        return _jaccard(a_shingles, b_shingles)
    m1 = MinHash(num_perm=64)
    m2 = MinHash(num_perm=64)
    for s in a_shingles:
        m1.update(s.encode("utf8"))
    for s in b_shingles:
        m2.update(s.encode("utf8"))
    return m1.jaccard(m2)


def _extract_matching_sentences(content: str) -> List[Tuple[str, str]]:
    """
    Extract sentences from content that match any structural pattern.
    Returns list of (sentence, scaffold_label) pairs.
    """
    # Rough sentence split on period, exclamation, question mark followed by space/newline
    sentences = re.split(r"(?<=[.!?])\s+", content)
    matches = []
    for sentence in sentences:
        for pattern, label in _STRUCTURAL_PATTERNS:
            if pattern.search(sentence):
                matches.append((sentence.strip(), label))
                break  # one label per sentence is enough
    return matches


class StructuralDedupValidator:
    """
    Detects repeated story-framing scaffolds across posts in a run.

    Checks sentence-level structural similarity — not just exact literal matches —
    so that variants like "One client told us recently" and "A client mentioned last month"
    are flagged as the same structural scaffold.
    """

    def validate(self, posts: List[Post]) -> Dict[str, Any]:
        """
        Scan all posts for structurally similar story-framing sentences.

        Returns:
            Dict with:
            - issues: list of issue strings (consistent with all other validators)
            - passed: bool
            - scaffold_hits: raw list of (post_index, sentence, label) for debug
        """
        issues: List[str] = []
        scaffold_hits: List[Tuple[int, str, str]] = []

        # Collect (post_index, sentence, label, shingles) for all structural hits
        all_hits = []
        for idx, post in enumerate(posts):
            for sentence, label in _extract_matching_sentences(post.content):
                shingles = _shingle(sentence)
                all_hits.append((idx, sentence, label, shingles))
                scaffold_hits.append((idx, sentence, label))

        # Pairwise comparison — flag when two hits are similar AND share the same scaffold label
        flagged_posts = set()
        for i in range(len(all_hits)):
            for j in range(i + 1, len(all_hits)):
                idx_a, sent_a, label_a, sh_a = all_hits[i]
                idx_b, sent_b, label_b, sh_b = all_hits[j]

                if idx_a == idx_b:
                    continue  # same post — internal repetition, not cross-post

                if label_a != label_b:
                    continue  # different scaffold types — not a duplicate

                sim = _minhash_similarity(sh_a, sh_b)
                if sim >= _SIMILARITY_THRESHOLD:
                    # Flag the later post (higher index) for regeneration
                    later_idx = max(idx_a, idx_b)
                    if later_idx not in flagged_posts:
                        flagged_posts.add(later_idx)
                        issues.append(
                            f"Post {later_idx + 1} uses the same {label_a} as post "
                            f"{min(idx_a, idx_b) + 1} (similarity {sim:.0%}). "
                            f"Do NOT use the {label_a} — rephrase or use a different story angle."
                        )

        return {
            "issues": issues,
            "passed": len(issues) == 0,
            "scaffold_hits": scaffold_hits,
            "posts_flagged": len(flagged_posts),
        }
