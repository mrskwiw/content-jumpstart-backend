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

    # Statement-only CTA patterns. Questions are not valid CTAs -- CTAs must be
    # imperative statements placed on the final line of the post.
    # Full detection patterns — used on the LAST 2 LINES only.
    # These are comprehensive and may be too broad for body-scanning.
    CTA_PATTERNS = [
        (
            r"(?:drop|share|leave) (?:your|a|it) (?:comment|take|thoughts?|feedback|experience|story|opinion|perspective|below)",
            "comment_request",
        ),
        (r"(?:dm|message|reach out|contact) me", "direct_contact"),
        # "hit reply", "just reply", or "reply with/below/here/to this/me"
        # Requires prefix OR suffix — bare "reply" (e.g. "In reply to...") is excluded.
        (
            r"\b(?:hit|just)\s+reply\b|\breply\s+(?:with|below|here|to\s+(?:this|me))\b",
            "reply_request",
        ),
        (r"(?:click|tap|check out) (?:the )?link", "link_click"),
        # Booking: "book/schedule [optional adjectives] <service noun>"
        # Noun list covers clinical, service-business, and general scheduling forms.
        (
            r"(?:book|schedule|set up) (?:a |an |your )?(?:[\w-]+ )*"
            r"(?:call|meeting|demo|visit|appointment|consultation|session"
            r"|conversation|exam|evaluation|assessment|checkup|walkthrough|tour|screening)\b",
            "booking",
        ),
        # Standalone appointment/consultation in the CTA line
        (r"\b(?:appointment|consultation)\b", "booking"),
        (r"sign up|subscribe|join", "signup"),
        (r"download|get (?:the |your )", "download"),
        (r"learn more|find out", "learn_more"),
        (r"(?:tell|share) me (?:in|about)", "share_request"),
        # Action verbs — word boundaries prevent "start" matching "restart", "try" matching "dentistry"
        (r"\b(?:read|watch|listen to|try|start|begin|explore)\b", "action_verb"),
        (r"\b(?:visit|follow|connect|register|apply)\b", "engagement"),
        # Soft CTAs common in service/healthcare/local business content
        (r"let['‘’]?s (?:get|start|make|do|try|book|talk|see|meet|schedule|change)", "soft_action"),
        (r"ask (?:us|me|your dentist|your doctor|our team)", "ask_request"),
        (r"give (?:us|me) (?:a|your)\b", "soft_action"),
    ]

    # Placement patterns — used when scanning the post BODY for misplaced CTAs.
    # These must be specific enough that normal body text does not match, while
    # still covering every form that CTA_PATTERNS recognises as a valid CTA.
    # Excluded (still in CTA_PATTERNS for last-line detection):
    # - standalone appointment/consultation (very common in dental body text)
    # - start/try/begin (opener phrases: "start with a question", "try to imagine")
    # - bare "visit" (dental: "visit our office for care")
    _PLACEMENT_PATTERNS = [
        r"(?:drop|share|leave) (?:your|a|it) (?:comment|take|thoughts?|feedback|experience|story|opinion|perspective|below)",
        r"(?:dm|message|reach out|contact) me",
        # Body scan: only prefix form is safe — "hit reply"/"just reply" cannot
        # appear as ordinary prose. "reply with/below/to this" can ("in reply to
        # this point") so it is excluded from body patterns; CTA_PATTERNS covers
        # it for the last-two-lines check.
        r"\b(?:hit|just)\s+reply\b",
        r"(?:click|tap|check out) (?:the )?link",
        r"(?:book|schedule|set up) (?:a |an |your )?(?:[\w-]+ )*"
        r"(?:call|meeting|demo|visit|appointment|consultation|session"
        r"|conversation|exam|evaluation|assessment|checkup|walkthrough|tour|screening)\b",
        r"sign up|subscribe|join",
        r"download|get (?:the |your )",
        r"learn more|find out",
        r"(?:tell|share) me (?:in|about)",
        r"give (?:us|me) (?:a|your)\b",
        # --- engagement verbs -----------------------------------------------
        # "follow us/me/our" is CTA; "follow the same logic" is body text.
        r"\bfollow (?:us|me|our|my)\b",
        # "connect with us/me" is CTA; "connect the dots" is body text.
        r"\bconnect (?:with us|with me)\b",
        # "visit us" is unambiguously CTA; "visit our office/etc." excluded
        # because dental body text naturally says "visit our office for care".
        r"\bvisit us\b",
        # "register" is unambiguous as a CTA in body context.
        # "apply" requires a follow-up word: "apply now/today/here/for/to"
        # to avoid matching "we apply fluoride" or "apply the same logic".
        r"\bregister\b",
        r"\bapply\b(?=\s+(?:now|today|here|for|to)\b)",
        # --- action verbs ---------------------------------------------------
        # read/watch/explore the/our/my: catches "read the guide", "watch our video".
        # "this" excluded: "if you have read this far" is body text, not a CTA.
        r"(?:read|watch|listen to|explore) (?:the|our|my)\b",
        # --- soft CTAs ------------------------------------------------------
        # let’s + booking verb: unambiguously CTA even mid-body.
        # "let’s get" added for "let’s get started"; "let’s make" excluded
        # because "let’s make this clear" is a sentence opener, not a CTA.
        r"let['‘’]?s (?:book|schedule|meet|connect|sign up|register|apply|get)\b",
        # "try it/us/our": "try it free", "try us today" are CTAs mid-body;
        # "try to imagine" excluded by requiring it/us/our after try.
        r"\btry (?:it|us|our)\b",
        # "start your/a free/today/now": "start your free trial" is a CTA;
        # "start with this idea" excluded by requiring a CTA context word.
        r"\bstart (?:your|a free|today|now)\b",
        # "begin your/a/the": "begin your journey" is a CTA;
        # "begin by understanding" excluded by requiring your/a/the.
        r"\bbegin (?:your|a|the)\b",
        # "let's make/do it/now": "let's make it work", "let's do it now" are CTAs.
        # "this" excluded: "let's make this clear" and "let's do this analysis"
        # are body-text transitions, not CTAs.
        r"let[''']?s (?:make|do) (?:it|now)\b",
        # "visit our website/page/site/link/profile": specific CTA form;
        # "visit our office" excluded by requiring a web/link noun.
        r"\bvisit (?:our|the) (?:website|page|site|link|profile)\b",
        # "ask us/me/our team" with request context word (existing pattern).
        r"ask (?:us|me|our team) (?:for|to )\b",
        # bare "ask us/me" followed by CTA-specific words: "ask us anything",
        # "ask me below", "ask me in the comments" are mid-post CTAs.
        r"ask (?:us|me) (?:anything|below|in the)\b",
        # "ask your dentist/doctor": professional referral CTA forms.
        r"ask (?:your dentist|your doctor)\b",
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
        Validate CTA variety across all posts (platform-aware).

        For microblog/Twitter posts: skips CTA checks and validates
        hashtag presence instead (see _validate_twitter_hashtags).

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

        # Microblog posts use hashtags (from client keywords) instead of CTAs
        if platform == Platform.TWITTER:
            return self._validate_twitter_hashtags(posts)

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

        # Check CTA placement and question-ending per-post.
        # _check_post_ends_with_question is skipped for posts from templates
        # that intentionally end with engagement questions (Question Post,
        # Contrarian Take, Reader Q&A) — their question endings are valid.
        # All other posts (including unlabelled ones) are checked so that
        # generic question closers don't pass the batch validator silently.
        # "against the grain" is Template 3's stored name (TemplateType.CONTRARIAN).
        # "question" covers Template 5 ("Question") and Template 14 ("Reader Question").
        _QUESTION_EXEMPT_KEYWORDS = frozenset(
            {
                "question",  # Template 5 + 14
                "against the grain",  # Template 3 actual stored name
                "contrarian",  # future-proof: matches any template with "contrarian" in name
                "q_and_a",
                "q&a",
            }
        )
        for post in posts:
            issues.extend(self._check_post_cta_placement(post))
            template_lower = (getattr(post, "template_name", None) or "").lower()
            if not any(kw in template_lower for kw in _QUESTION_EXEMPT_KEYWORDS):
                issues.extend(self._check_post_ends_with_question(post))

        return {
            "passed": len(issues) == 0,
            "cta_distribution": dict(cta_counts),
            "variety_score": variety_score,
            "issues": issues,
            "metric": f"{len(cta_counts)} unique CTA types across {len(posts)} posts",
            "platform": platform.value if platform else None,
            "variety_threshold": variety_threshold,
        }

    def _validate_twitter_hashtags(self, posts: List[Post]) -> Dict[str, Any]:
        """Check that each microblog post contains at least one keyword-derived hashtag.

        Returns a dict that is shape-compatible with the standard CTA result so that
        all downstream consumers (QAReport.to_markdown, qa_agent scoring, etc.) work
        without branching: variety_score is the hashtag-coverage ratio, and
        cta_distribution is repurposed to show per-post hashtag presence.
        """
        hashtag_re = re.compile(r"#[A-Za-z]\w*")
        issues: List[str] = []
        has_tags: List[bool] = []

        for post in posts:
            found = bool(hashtag_re.search(post.content))
            has_tags.append(found)
            if not found:
                issues.append(
                    f"Microblog post '{post.template_name or 'post'}' is missing a hashtag "
                    "— add 1-2 hashtags drawn from the client's keywords"
                )

        posts_with_tags = sum(has_tags)
        coverage = posts_with_tags / len(posts) if posts else 1.0
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            # Shape-compatible fields so QAReport.to_markdown() never KeyErrors:
            "variety_score": coverage,  # hashtag coverage (1.0 = all posts have tags)
            "cta_distribution": {  # repurposed: hashtag presence counts
                "has_hashtag": posts_with_tags,
                "missing_hashtag": len(posts) - posts_with_tags,
            },
            "variety_threshold": 1.0,  # every post must have a hashtag
            "metric": f"{posts_with_tags}/{len(posts)} microblog posts contain hashtags",
            "platform": Platform.TWITTER.value,
            "is_hashtag_check": True,  # sentinel so to_markdown can label correctly
        }

    def _detect_platform(self, posts: List[Post]) -> Optional[Platform]:
        """Detect platform from posts"""
        if not posts:
            return None
        first_post = posts[0]
        if hasattr(first_post, "target_platform") and first_post.target_platform:
            # target_platform is already typed as Optional[Platform]
            return first_post.target_platform
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

            # Match against imperative CTA patterns
            cta_type = "no_cta"
            for pattern, type_name in self.CTA_PATTERNS:
                if re.search(pattern, cta_section, re.IGNORECASE):
                    cta_type = type_name
                    break

            # Engagement question on the last line is a valid CTA type for
            # templates like Question Post, Contrarian Take, Prediction Post, Q&A.
            if cta_type == "no_cta":
                last_line = lines[-1].strip() if lines else ""
                if last_line.endswith("?"):
                    cta_type = "engagement_question"

            cta_types.append(cta_type)

        return cta_types

    def _check_post_cta_placement(self, post: "Post") -> List[str]:
        """Check that this post's CTA is on the final line and is a statement.

        Returns a list of issue strings (empty = no placement issues).
        """
        issues: List[str] = []
        lines = [ln.strip() for ln in post.content.strip().splitlines() if ln.strip()]
        if not lines:
            return issues

        last_line = lines[-1].lower()
        body = " ".join(lines[:-1]).lower()

        # CTA found in body (not last line) = wrong placement.
        # Uses _PLACEMENT_PATTERNS (not CTA_PATTERNS) so that broad patterns
        # like standalone action verbs or "appointment" don't false-positive
        # on normal body sentences in dental/healthcare/service content.
        for pattern in self._PLACEMENT_PATTERNS:
            if re.search(pattern, body, re.IGNORECASE):
                issues.append(
                    f"CTA found mid-post in '{post.template_name or 'post'}': move to final line"
                )
                break

        # CTA on last line but ends with ? = question, not a statement.
        # Uses the full CTA_PATTERNS (not just _PLACEMENT_PATTERNS) so that ALL
        # recognised CTA forms — including standalone "Appointment?" or
        # "Consultation?" — are caught as question-ending violations.  The body
        # scan above still uses the stricter _PLACEMENT_PATTERNS to avoid false
        # positives from those same broad patterns appearing in body sentences.
        for pattern, _ in self.CTA_PATTERNS:
            if re.search(pattern, last_line, re.IGNORECASE):
                if last_line.rstrip().endswith("?"):
                    issues.append(
                        f"CTA is a question in '{post.template_name or 'post'}': rewrite as a statement"
                    )
                break

        return issues

    def _check_post_ends_with_question(self, post: "Post") -> List[str]:
        """Check that the post does not end with a question mark.

        This is broader than ``_check_post_cta_placement``'s question check: it
        catches any post whose final non-empty line ends with ``?``, regardless of
        whether that line contains a recognised CTA pattern.

        Returns a list of issue strings (empty = no issues).
        """
        lines = [ln.strip() for ln in post.content.strip().splitlines() if ln.strip()]
        if not lines:
            return []
        if lines[-1].rstrip().endswith("?"):
            return [
                f"Post ends with a question in '{post.template_name or 'post'}': "
                "the final line must be a statement"
            ]
        return []

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
