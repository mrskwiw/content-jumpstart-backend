"""CTA Variety Validator

Ensures CTAs vary across posts and aren't overused.
"""

import re
from collections import Counter
from typing import Any, Dict, List, Optional

from ..config.constants import CTA_VARIETY_THRESHOLD
from ..models.client_brief import Platform
from ..models.post import Post
from ..utils.logger import logger


def _llm_cta_check(last_two_lines: str) -> bool:
    """Ask Claude Haiku whether text ends with a CTA (YES/NO).

    Called only when the deterministic regex returns no match AND the validator
    was constructed with use_llm_fallback=True.  Each call is independently
    guarded so one failure never affects other posts in the same batch.
    Cost: ~$0.00025 per call (Haiku, 5-token response).
    """
    try:
        from ..utils.anthropic_client import get_default_client

        client = get_default_client()
        prompt = (
            "Does the following text end with a call-to-action — an explicit "
            "imperative instruction for the reader to take a specific action "
            "such as booking, replying, subscribing, shopping, donating, or "
            "following?\n\n"
            "Soft reassurance, empathy statements, and descriptive closers are "
            "NOT calls-to-action.\n\n"
            f"TEXT:\n{last_two_lines}\n\n"
            "Answer with a single word: YES or NO."
        )
        response = client.create_message(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
            model="claude-haiku-4-5-20251001",
        )
        answer = (response or "").strip().upper()
        return answer.startswith("YES")
    except Exception as exc:
        logger.debug(f"CTA LLM fallback skipped for this post: {exc}")
        return False


# Service nouns that follow a booking verb on the last line.
# Shared between CTA_PATTERNS and _PLACEMENT_PATTERNS so both stay in sync.
# Grouped by industry for readability — all end up in a single alternation.
_BOOKING_NOUNS = (
    # General / B2B
    "call|meeting|demo|visit|appointment|consultation|session"
    "|conversation|evaluation|assessment|walkthrough|tour|screening"
    # Healthcare & dental
    "|exam|checkup|cleaning|whitening|treatment|procedure|hygiene"
    "|filling|extraction|service"
    # Fitness & wellness
    "|class|drop-in|trial|intro"
    "|facial|massage|blowout"
    # Trades / auto / home
    "|repair|inspection|detail"
    # Food & hospitality
    "|reservation|table"
    # Education
    "|lesson"
    # Real estate
    "|showing|valuation"
)

_BOOKING_VERB = r"(?:book|schedule|set up|reserve|claim)"


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
        (r"(?:dm|message|reach out|contact) (?:me|us|our team)", "direct_contact"),
        # "hit reply", "just reply", or "reply with/below/here/to this/me"
        # Requires prefix OR suffix — bare "reply" (e.g. "In reply to...") is excluded.
        (
            r"\b(?:hit|just)\s+reply\b|\breply\s+(?:with|below|here|to\s+(?:this|me))\b",
            "reply_request",
        ),
        (r"(?:click|tap|check out) (?:the )?link", "link_click"),
        # Link in bio — creator/e-commerce standard CTA form
        (r"\blink in bio\b", "link_click"),
        # Booking: "book/schedule/reserve/claim [optional adjectives] <service noun>"
        # Noun list covers clinical, service-business, fitness, real estate, and
        # general scheduling forms.  See _BOOKING_NOUNS above.
        (
            _BOOKING_VERB + r" (?:a |an |your )?(?:[\w-]+ )*(?:" + _BOOKING_NOUNS + r")\b",
            "booking",
        ),
        # Booking via URL destination: "book your cleaning at [url]"
        (
            _BOOKING_VERB + r" (?:[\w\s-]+ )?at (?:https?://|www\.|\w[\w-]*\.\w{2,6})",
            "booking",
        ),
        # Standalone scheduling terms that unambiguously signal a CTA on the last line
        (r"\b(?:appointment|consultation|exam|cleaning|screening|checkup)\b", "booking"),
        # Fitness / wellness standalone
        (r"\bfree (?:trial|class|session|consultation|drop-in|intro)\b", "booking"),
        # Real estate standalone
        (r"\b(?:home valuation|property tour)\b", "booking"),
        (r"sign up|subscribe|join", "signup"),
        (r"download|get (?:the |your )", "download"),
        (r"learn more|find out", "learn_more"),
        (r"(?:tell|share) me (?:in|about)", "share_request"),
        # E-commerce action — "shop now", "order today", "buy here"
        (r"\b(?:shop|order|buy|purchase) (?:now|today|here|online)\b", "ecommerce_action"),
        # Cause / non-profit action
        (r"\b(?:donate|give) (?:now|today|here|to (?:our|the|us))\b", "cause_action"),
        (r"\bvolunteer\b", "cause_action"),
        # Action verbs — word boundaries prevent "start" matching "restart", "try" matching "dentistry"
        (r"\b(?:read|watch|listen to|try|start|begin|explore)\b", "action_verb"),
        (r"\b(?:visit|follow|connect|register|apply)\b", "engagement"),
        # Soft CTAs common in service/healthcare/local business content
        (
            r"let[''']?s (?:get|start|make|do|try|book|talk|see|meet|schedule|change"
            r"|connect|plan|find|explore|work)",
            "soft_action",
        ),
        # Ask request — expanded to cover more professional service industries
        (
            r"ask (?:us|me|our team|your (?:dentist|doctor|therapist|attorney|advisor|trainer|realtor|agent))",
            "ask_request",
        ),
        (r"give (?:us|me) (?:a|your)\b", "soft_action"),
    ]

    # Placement patterns — used when scanning the post BODY for misplaced CTAs.
    # These must be specific enough that normal body text does not match, while
    # still covering every form that CTA_PATTERNS recognises as a valid CTA.
    # Excluded (still in CTA_PATTERNS for last-line detection):
    # - standalone appointment/consultation/exam (very common in body text)
    # - start/try/begin (opener phrases: "start with a question", "try to imagine")
    # - bare "visit" (service body text: "visit our office for care")
    # - bare "volunteer"/"donate" without action context word (body mentions)
    _PLACEMENT_PATTERNS = [
        r"(?:drop|share|leave) (?:your|a|it) (?:comment|take|thoughts?|feedback|experience|story|opinion|perspective|below)",
        r"(?:dm|message|reach out|contact) (?:me|us|our team)",
        # Body scan: "hit reply"/"just reply" are unambiguous CTAs.
        # "reply below" is safe to add — "in reply to..." never uses "below".
        # Broader "reply with/to this" still excluded (can appear as prose).
        r"\b(?:hit|just)\s+reply\b",
        r"\breply\s+below\b",
        r"(?:click|tap|check out) (?:the )?link",
        r"\blink in bio\b",
        # Booking verb + noun: safe in body because "book your cleaning at 9am"
        # is action instruction regardless of position.
        _BOOKING_VERB + r" (?:a |an |your )?(?:[\w-]+ )*(?:" + _BOOKING_NOUNS + r")\b",
        # Booking via URL destination
        _BOOKING_VERB + r" (?:[\w\s-]+ )?at (?:https?://|www\.|\w[\w-]*\.\w{2,6})",
        r"sign up|subscribe|join",
        r"download|get (?:the |your )",
        r"learn more|find out",
        r"(?:tell|share) me (?:in|about)",
        r"give (?:us|me) (?:a|your)\b",
        # E-commerce — require action context word to avoid "shop owners do X"
        r"\b(?:shop|order|buy|purchase) (?:now|today|here|online)\b",
        # Cause — require action context word to avoid "donate organs" as body prose
        r"\b(?:donate|give) (?:now|today|here|to (?:our|the|us))\b",
        # --- engagement verbs -----------------------------------------------
        # "follow us/me/our" is CTA; "follow the same logic" is body text.
        r"\bfollow (?:us|me|our|my)\b",
        # "connect with us/me" is CTA; "connect the dots" is body text.
        r"\bconnect (?:with us|with me)\b",
        # "visit us" is unambiguously CTA; "visit our office/etc." excluded
        # because service body text naturally says "visit our office for care".
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
        # let's + booking verb: unambiguously CTA even mid-body.
        r"let[''']?s (?:book|schedule|meet|connect|sign up|register|apply|get)\b",
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
        # Professional referral CTA forms — mid-body placement is still a CTA.
        r"ask (?:your dentist|your doctor|your therapist|your attorney|your advisor|your trainer)\b",
    ]

    def __init__(
        self,
        variety_threshold: Optional[float] = None,
        use_llm_fallback: bool = False,
    ):
        """
        Initialize CTA validator.

        Args:
            variety_threshold: Maximum percentage of posts that can use the same
                CTA type (0.0-1.0). Defaults to CTA_VARIETY_THRESHOLD.
            use_llm_fallback: When True, posts the regex marks as no_cta get a
                single Haiku YES/NO call to catch novel CTA forms the regex
                misses. Each call is independently try/except-guarded so one
                API error never blocks the rest of the batch. Default False so
                tests and offline callers stay deterministic.
        """
        self.variety_threshold = variety_threshold or CTA_VARIETY_THRESHOLD
        self.use_llm_fallback = use_llm_fallback

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
        # that intentionally end with engagement questions.
        _QUESTION_EXEMPT_KEYWORDS = frozenset(
            {
                "question",  # Template 5 + 14
                "against the grain",  # Template 3 actual stored name
                "contrarian",  # future-proof: matches any template with "contrarian" in name
                "q_and_a",
                "q&a",
                "future",  # Future-Thinking / Prediction posts
                "prediction",  # same
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

            # LLM fallback — only when opt-in AND regex found nothing.
            # Each call is independently guarded: one API error never affects
            # the remaining posts in the batch.
            if cta_type == "no_cta" and self.use_llm_fallback:
                if _llm_cta_check(cta_section):
                    cta_type = "llm_detected"
                    logger.info(
                        "CTA LLM fallback: regex missed a CTA — "
                        f"consider adding to CTA_PATTERNS: {cta_section!r:.120}"
                    )

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
        # on normal body sentences in service content.
        for pattern in self._PLACEMENT_PATTERNS:
            if re.search(pattern, body, re.IGNORECASE):
                issues.append(
                    f"CTA found mid-post in '{post.template_name or 'post'}': move to final line"
                )
                break

        # CTA on last line but ends with ? = question, not a statement.
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

        max_count = cta_counts.most_common(1)[0][1] if cta_counts else 0
        min_variety = max_count / total_posts  # Percentage of most common CTA

        # Inverse: lower dominance = higher variety
        variety_score = 1.0 - (min_variety - (1.0 / len(cta_counts)) if cta_counts else 0)

        return max(0.0, min(1.0, variety_score))
