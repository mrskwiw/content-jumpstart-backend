"""QA Agent: Quality Assurance orchestrator for post validation"""

from typing import List, Optional

from ..analysis.content_intelligence import assess_post
from ..analysis.geo import check_answer_block, opening_answer_block
from ..config.template_rules import ClientType
from ..models.post import Post
from ..models.qa_report import QAReport
from ..models.seo_keyword import KeywordStrategy
from ..utils.logger import logger
from ..validators.citation_validator import CitationValidator
from ..validators.cta_validator import CTAValidator
from ..validators.headline_validator import HeadlineValidator
from ..validators.hook_validator import HookValidator
from ..validators.keyword_validator import KeywordValidator
from ..validators.length_validator import LengthValidator
from ..validators.seo_validator import SEOValidator

# Client types that use conversational/local-service content — headline threshold 2.
# UNKNOWN is intentionally excluded: uncertain classification should default to
# the stricter threshold rather than silently pass bad headlines.
_LOCAL_SERVICE_TYPES: frozenset = frozenset(
    {
        ClientType.HEALTHCARE,
        ClientType.REAL_ESTATE,
        ClientType.RESTAURANT_HOSPITALITY,
        ClientType.ECOMMERCE_RETAIL,
        ClientType.NONPROFIT,
        ClientType.HOME_SERVICES,
        ClientType.EDUCATION,
        ClientType.FINANCIAL_SERVICES,
        ClientType.LEGAL,
    }
)


class QAAgent:
    """
    Quality Assurance Agent that validates post quality across multiple dimensions
    """

    def __init__(self, keyword_strategy: Optional[KeywordStrategy] = None):
        """
        Initialize QA Agent with validators

        Args:
            keyword_strategy: Optional SEO keyword strategy for keyword validation
        """
        self.hook_validator = HookValidator(similarity_threshold=0.80)
        self.cta_validator = CTAValidator(variety_threshold=0.40)
        self.length_validator = LengthValidator()
        self.citation_validator = CitationValidator()

        # Optional keyword validator
        self.keyword_validator = None
        if keyword_strategy:
            self.keyword_validator = KeywordValidator(keyword_strategy)

        # SEO validator for blog posts (uses same keyword strategy if available)
        self.seo_validator = SEOValidator(keyword_strategy=keyword_strategy)

    def validate_posts(
        self,
        posts: List[Post],
        client_name: str,
        client_type: Optional[ClientType] = None,
    ) -> QAReport:
        """
        Run quality validation on a set of posts

        Args:
            posts: List of Post objects to validate
            client_name: Client name for report
            client_type: Optional client type — adjusts headline threshold

        Returns:
            QAReport with validation results
        """
        logger.info(f"Running QA validation on {len(posts)} posts")

        # Headline threshold: local-service/consumer clients use conversational
        # openers that naturally score lower on thought-leadership elements.
        headline_threshold = 2 if client_type in _LOCAL_SERVICE_TYPES else 3
        headline_validator = HeadlineValidator(min_elements=headline_threshold)

        # Run all validators
        hook_results = self.hook_validator.validate(posts)
        cta_results = self.cta_validator.validate(posts)
        length_results = self.length_validator.validate(posts)
        headline_results = headline_validator.validate(posts)

        # Run keyword validation if available
        keyword_results = None
        if self.keyword_validator:
            keyword_results = self.keyword_validator.validate(posts)

        # Run SEO validation for blog posts
        seo_results = self.seo_validator.validate(posts)

        # Cross-post consistency checks (Bug #143, #139)
        stat_conflicts = self._check_stat_conflicts(posts)
        source_dups = self._check_source_dedup(posts)

        # Citation scan — non-blocking, advisory only
        citation_results = self.citation_validator.validate(posts)

        # Collect all issues
        all_issues = []
        all_issues.extend(hook_results.get("issues", []))
        all_issues.extend(cta_results.get("issues", []))
        all_issues.extend(length_results.get("issues", []))
        all_issues.extend(headline_results.get("issues", []))
        if keyword_results:
            all_issues.extend(keyword_results.get("issues", []))
        if seo_results and not seo_results.get("skipped", False):
            all_issues.extend(seo_results.get("issues", []))
        all_issues.extend(stat_conflicts)
        all_issues.extend(source_dups)
        # Citation warnings are advisory — kept in citation_validation only,
        # not counted in total_issues or all_issues so they don't affect pass/fail
        # semantics or trigger the Recommendations section on clean reports.

        # Calculate overall quality score (average of all validator scores)
        scores = []
        if "uniqueness_score" in hook_results:
            scores.append(hook_results["uniqueness_score"])
        if "variety_score" in cta_results:
            scores.append(cta_results["variety_score"])
        if "optimal_ratio" in length_results:
            scores.append(length_results["optimal_ratio"])
        # Headline score: percentage of posts meeting threshold
        if headline_results.get("headlines_analyzed", 0) > 0:
            headline_score = 1.0 - (
                headline_results.get("below_threshold_count", 0)
                / headline_results["headlines_analyzed"]
            )
            scores.append(headline_score)
        # Keyword score: primary keyword usage ratio
        if keyword_results and "primary_usage_ratio" in keyword_results:
            scores.append(keyword_results["primary_usage_ratio"])
        # SEO score: normalized from 0-100 to 0-1
        if seo_results and not seo_results.get("skipped", False) and "average_score" in seo_results:
            scores.append(seo_results["average_score"] / 100.0)

        quality_score = sum(scores) / len(scores) if scores else 0.0

        # Determine overall pass/fail
        overall_passed = (
            hook_results.get("passed", True)
            and cta_results.get("passed", True)
            and length_results.get("passed", True)
            and headline_results.get("passed", True)
            and (keyword_results.get("passed", True) if keyword_results else True)
            and (
                seo_results.get("passed", True)
                if seo_results and not seo_results.get("skipped", False)
                else True
            )
        )

        # Advisory pre-publish engagement prediction (does not affect pass/fail)
        engagement_prediction = self._predict_engagement_summary(posts)

        # Advisory GEO answer-block readiness across blog posts (does not affect pass/fail)
        answer_block_geo = self._answer_block_summary(posts)

        # Create report
        report = QAReport(
            client_name=client_name,
            total_posts=len(posts),
            overall_passed=overall_passed,
            quality_score=quality_score,
            hook_validation=hook_results,
            cta_validation=cta_results,
            length_validation=length_results,
            headline_validation=headline_results,
            keyword_validation=keyword_results,
            seo_validation=seo_results if not seo_results.get("skipped", False) else None,
            citation_validation=citation_results if citation_results["posts_flagged"] > 0 else None,
            engagement_prediction=engagement_prediction,
            answer_block_geo=answer_block_geo,
            total_issues=len(all_issues),
            all_issues=all_issues,
        )

        logger.info(
            f"QA validation complete: {'PASSED' if overall_passed else 'FAILED'} "
            f"(Quality: {quality_score:.1%}, Issues: {len(all_issues)})"
        )

        return report

    # ------------------------------------------------------------------
    # Cross-post consistency checks (Bug #143, #139)
    # These run after all posts are generated and flag issues without
    # blocking delivery — operators see warnings in the run log.
    # ------------------------------------------------------------------

    # Predicted engagement below this heuristic floor counts as "weak". Matches the
    # regenerator's regenerate-below floor (PREDICT-01 / content_intelligence).
    _ENGAGEMENT_WEAK_FLOOR = 45.0

    def _predict_engagement_summary(self, posts: "List[Post]") -> Optional[dict]:
        """Advisory pre-publish engagement estimate across the batch.

        Uses the canonical ``assess_post`` facade — the SAME signal the regenerator
        acts on — so a post's QA-report score matches its regenerate/no-regenerate
        score exactly (assess_post strips appended hashtags before scoring, which
        content_generator adds before QA runs). Summarises average, minimum, and the
        count below the weak floor. Purely informational — surfaced in the report,
        never gates pass/fail. Returns None for an empty batch.
        """
        if not posts:
            return None

        scores = []
        for post in posts:
            if not post.content:
                continue
            platform = post.target_platform.value if post.target_platform else "linkedin"
            scores.append(assess_post(post.content, platform=platform).predicted_score)

        if not scores:
            return None

        weak = sum(1 for s in scores if s < self._ENGAGEMENT_WEAK_FLOOR)
        return {
            "average_score": round(sum(scores) / len(scores), 1),
            "min_score": min(scores),
            "weak_count": weak,
            "weak_floor": self._ENGAGEMENT_WEAK_FLOOR,
            "total": len(scores),
        }

    def _answer_block_summary(self, posts: "List[Post]") -> Optional[dict]:
        """Advisory GEO answer-block readiness across the batch's BLOG posts (GEO-01).

        For each blog post, checks whether the opening paragraph is the ~40-60-word
        self-contained answer AI answer engines prefer to extract (``check_answer_block``).
        Answer blocks are blog-specific — social posts have none — so this returns None when
        the batch has no blog posts. Purely informational: surfaced in the QA report, never
        gates pass/fail (mirrors the engagement prediction). A missing/empty opening counts as
        "not well-formed".
        """
        total = 0
        ok = 0
        for post in posts:
            platform = post.target_platform.value if post.target_platform else ""
            if platform != "blog" or not post.content:
                continue
            total += 1
            opening = opening_answer_block(post.content)
            if opening and check_answer_block(opening).ok:
                ok += 1
        if total == 0:
            return None
        return {"total": total, "ok_count": ok, "weak_count": total - ok}

    def _check_stat_conflicts(self, posts: "List[Post]") -> "List[str]":
        """Detect contradictory percentage claims on the same topic (Bug #143).

        Extracts percentage values near topic keywords and flags cases where
        the same topic carries two different numbers across posts in the run.
        """
        import re

        PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
        TOPIC_GROUPS: "dict[str, list[str]]" = {
            # Healthcare / dental
            "flossing": ["floss"],
            "cavity / decay": ["cavit", "decay", "caries"],
            "dental anxiety": ["anxiet", "anxious", "fear of dent", "dentophob"],
            "brushing": ["brush", "oral hygiene"],
            "blood pressure": ["blood pressure", "hypertens"],
            "diabetes": ["diabet"],
            "obesity": ["obes", "overweight"],
            "vaccination": ["vaccin", "immuniz"],
            # Real estate / finance
            "home values": ["home value", "property value", "house price"],
            "mortgage rates": ["mortgage rate", "interest rate"],
            "savings rate": ["savings rate", "saving rate"],
            "investment returns": ["investment return", "stock return", "portfolio return"],
            "customer retention": ["retention rate", "churn rate"],
            # Fitness / wellness
            "exercise": ["exercis", "workout", "physical activity"],
            "sleep": ["sleep disorder", "insomnia", "sleep quality"],
            "weight loss": ["weight loss", "lose weight"],
            # Marketing / SaaS
            "conversion rate": ["conversion rate"],
            "engagement rate": ["engagement rate"],
            "open rate": ["open rate", "email open"],
            "click-through rate": ["click rate", "click-through", "ctr"],
            "revenue growth": ["revenue growth", "revenue increas"],
        }

        topic_claims: "dict[str, dict[float, list[int]]]" = {}
        for i, post in enumerate(posts):
            for topic_key, keywords in TOPIC_GROUPS.items():
                content_lower = post.content.lower()
                if not any(kw in content_lower for kw in keywords):
                    continue
                for m in PERCENT_RE.finditer(post.content):
                    start = max(0, m.start() - 120)
                    end = min(len(post.content), m.end() + 120)
                    ctx = post.content[start:end].lower()
                    if any(kw in ctx for kw in keywords):
                        pct = float(m.group(1))
                        topic_claims.setdefault(topic_key, {}).setdefault(pct, []).append(i + 1)

        warnings: "List[str]" = []
        for topic_key, pct_map in topic_claims.items():
            if len(pct_map) >= 2:
                detail = "; ".join(f"{p}% in post(s) {ns}" for p, ns in sorted(pct_map.items()))
                warnings.append(
                    f"⚠ STAT CONFLICT ({topic_key}): conflicting figures — {detail}. "
                    "Review before publishing."
                )
        return warnings

    def _check_source_dedup(self, posts: "List[Post]") -> "List[str]":
        """Detect reuse of the same book/source across Learning Posts (Bug #139).

        Learning Post (template 11) gravitates to the same book for the same topic
        when generated in parallel.  Flag when the same italicised or quoted title
        appears in two or more Learning Posts in the same package.
        """
        import re

        # Match *italicised title* or "quoted title" (5-80 chars)
        SOURCE_RE = re.compile(r'\*([^*]{5,80})\*|"([^"]{5,80})"')

        source_map: "dict[str, list[int]]" = {}
        for i, post in enumerate(posts):
            template_name = (post.template_name or "").lower()
            is_learning = "learning" in template_name or getattr(post, "template_id", None) == 11
            if not is_learning:
                continue
            for m in SOURCE_RE.finditer(post.content[:600]):
                title = (m.group(1) or m.group(2) or "").strip()
                if len(title) > 5:
                    source_map.setdefault(title.lower(), []).append(i + 1)

        warnings: "List[str]" = []
        for title, post_nums in source_map.items():
            if len(post_nums) >= 2:
                warnings.append(
                    f"⚠ SOURCE REPEAT: '{title}' cited in {len(post_nums)} Learning Posts "
                    f"(posts {post_nums}). Use distinct sources per post."
                )
        return warnings
