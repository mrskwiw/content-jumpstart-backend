"""Citation Validator

Scans posts for attributed statistics and flags them for operator review.
Non-blocking: warnings appear in the QA report but never fail a post or
trigger regeneration.
"""

import re
from typing import Any, Dict, List

from ..models.post import Post

# Patterns that indicate a specific source attribution.
# Inline (?i:...) flags make keywords case-insensitive while keeping [A-Z]
# strict so lowercase common words (e.g. "your") aren't treated as org names.
# Requires Python 3.11+ for (?-i:...) / inline flag group support (3.12 used here).
_CITATION_PATTERNS = [
    r"(?i:according to)\s+[A-Z][A-Za-z]",
    r"[A-Z][A-Za-z]+\s+(?i:reports?|found|data\s+shows?|study|survey|says|notes?)\b",
    r"\b(?i:per)\s+[A-Z][A-Za-z]+[,\s]",
    r"(?i:\(source:)",
    r"(?i:source:)\s*[A-Z][A-Za-z]",
]

_CITATION_RE = re.compile("|".join(_CITATION_PATTERNS))


class CitationValidator:
    """Flags posts that contain source-attributed claims for operator review."""

    def validate(self, posts: List[Post]) -> Dict[str, Any]:
        """Scan each post for attribution patterns.

        Returns a dict with:
          warnings     — list of human-readable warning strings
          posts_flagged — count of posts containing at least one citation
        """
        warnings: List[str] = []

        for i, post in enumerate(posts, 1):
            content = post.content or ""
            match = _CITATION_RE.search(content)
            if match:
                snippet = content[match.start() : match.start() + 60].strip().rstrip(",")
                warnings.append(
                    f"Post {i} ({post.template_name}): "
                    f'unverified citation — "{snippet}..." — verify before publishing'
                )

        return {
            "warnings": warnings,
            "posts_flagged": len(warnings),
        }
