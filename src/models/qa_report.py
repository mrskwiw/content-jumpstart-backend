"""QA Report Model

Represents quality assurance report for a set of posts.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QAReport(BaseModel):
    """Quality assurance report for generated posts"""

    # Metadata
    client_name: str = Field(..., description="Client name")
    total_posts: int = Field(..., description="Total number of posts validated")
    generated_at: datetime = Field(
        default_factory=datetime.now, description="QA report generation timestamp"
    )

    # Overall Quality
    overall_passed: bool = Field(..., description="Whether all validators passed")
    quality_score: float = Field(..., description="Overall quality score (0.0-1.0)")

    # Validator Results
    hook_validation: Dict[str, Any] = Field(..., description="Hook uniqueness results")
    cta_validation: Dict[str, Any] = Field(..., description="CTA variety results")
    length_validation: Dict[str, Any] = Field(..., description="Length distribution results")
    headline_validation: Dict[str, Any] = Field(..., description="Headline engagement results")
    keyword_validation: Optional[Dict[str, Any]] = Field(
        None, description="SEO keyword usage results"
    )
    seo_validation: Optional[Dict[str, Any]] = Field(
        None, description="SEO optimization results for blog posts"
    )
    citation_validation: Optional[Dict[str, Any]] = Field(
        None, description="Unverified source attribution warnings (advisory only)"
    )
    engagement_prediction: Optional[Dict[str, Any]] = Field(
        None,
        description="Predicted-engagement summary (advisory pre-publish signal; does not affect pass/fail)",
    )
    answer_block_geo: Optional[Dict[str, Any]] = Field(
        None,
        description="GEO answer-block readiness across blog posts (advisory; does not affect pass/fail)",
    )

    # Summary
    total_issues: int = Field(0, description="Total number of issues found")
    all_issues: List[str] = Field(
        default_factory=list, description="All issues from all validators"
    )

    def to_markdown(self) -> str:
        """
        Generate markdown report

        Returns:
            Markdown-formatted QA report
        """
        lines = []

        # Header
        lines.append("# Quality Assurance Report")
        lines.append("")
        lines.append(f"**Client:** {self.client_name}")
        lines.append(f"**Posts Validated:** {self.total_posts}")
        lines.append(f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Overall Status
        status_emoji = "[PASS]" if self.overall_passed else "[WARN]"
        lines.append(f"## Overall Status: {status_emoji}")
        lines.append("")
        lines.append(f"**Quality Score:** {self.quality_score:.1%}")
        lines.append(f"**Total Issues:** {self.total_issues}")
        lines.append("")

        # Hook Validation
        lines.append("## Hook Uniqueness")
        lines.append("")
        hook_status = "[PASS] PASSED" if self.hook_validation["passed"] else "[FAIL] FAILED"
        lines.append(f"**Status:** {hook_status}")
        lines.append(f"**Uniqueness Score:** {self.hook_validation['uniqueness_score']:.1%}")
        lines.append(f"**Metric:** {self.hook_validation['metric']}")
        if self.hook_validation["issues"]:
            lines.append("")
            lines.append("**Issues:**")
            for issue in self.hook_validation["issues"]:
                lines.append(f"- {issue}")
        lines.append("")

        # CTA / Hashtag Validation (section label depends on platform)
        is_hashtag_check = self.cta_validation.get("is_hashtag_check", False)
        section_title = "Hashtag Coverage" if is_hashtag_check else "CTA Variety"
        score_label = "Hashtag Coverage" if is_hashtag_check else "Variety Score"
        dist_label = "Hashtag Presence" if is_hashtag_check else "Distribution"
        lines.append(f"## {section_title}")
        lines.append("")
        cta_status = "[PASS] PASSED" if self.cta_validation["passed"] else "[FAIL] FAILED"
        lines.append(f"**Status:** {cta_status}")
        variety_score = self.cta_validation.get("variety_score")
        if variety_score is not None:
            lines.append(f"**{score_label}:** {variety_score:.1%}")
        lines.append(f"**Metric:** {self.cta_validation['metric']}")
        dist = self.cta_validation.get("cta_distribution") or {}
        if dist:
            lines.append("")
            lines.append(f"**{dist_label}:**")
            for cta_type, count in sorted(dist.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- {cta_type}: {count} posts")
        if self.cta_validation["issues"]:
            lines.append("")
            lines.append("**Issues:**")
            for issue in self.cta_validation["issues"]:
                lines.append(f"- {issue}")
        lines.append("")

        # Length Validation
        lines.append("## Post Length")
        lines.append("")
        length_status = "[PASS] PASSED" if self.length_validation["passed"] else "[FAIL] FAILED"
        lines.append(f"**Status:** {length_status}")
        lines.append(f"**Average Length:** {self.length_validation['average_length']} words")
        lines.append(f"**Metric:** {self.length_validation['metric']}")
        lines.append(f"**Optimal Ratio:** {self.length_validation['optimal_ratio']:.1%}")
        if self.length_validation["length_distribution"]:
            lines.append("")
            lines.append("**Distribution:**")
            for range_name, count in self.length_validation["length_distribution"].items():
                if count > 0:
                    lines.append(f"- {range_name} words: {count} posts")
        if self.length_validation["issues"]:
            lines.append("")
            lines.append("**Issues:**")
            for issue in self.length_validation["issues"]:
                lines.append(f"- {issue}")
        lines.append("")

        # Headline Validation
        lines.append("## Headline Engagement (SEO Best Practices)")
        lines.append("")
        headline_status = "[PASS] PASSED" if self.headline_validation["passed"] else "[FAIL] FAILED"
        lines.append(f"**Status:** {headline_status}")
        lines.append(
            f"**Average Engagement Elements:** {self.headline_validation['average_elements']:.1f}/3+"
        )
        lines.append(f"**Metric:** {self.headline_validation['metric']}")
        if self.headline_validation["issues"]:
            lines.append("")
            lines.append("**Issues:**")
            for issue in self.headline_validation["issues"]:
                lines.append(f"- {issue}")
        lines.append("")
        lines.append(
            "*Blog best practice: Headlines should have 3+ engagement elements (numbers, power words, emotional triggers, questions)*"
        )
        lines.append("")

        # Keyword Validation (if available)
        if self.keyword_validation:
            lines.append("## SEO Keyword Usage")
            lines.append("")
            keyword_status = (
                "[PASS] PASSED" if self.keyword_validation["passed"] else "[FAIL] FAILED"
            )
            lines.append(f"**Status:** {keyword_status}")
            lines.append(
                f"**Primary Usage Ratio:** {self.keyword_validation['primary_usage_ratio']:.1%}"
            )
            lines.append(f"**Metric:** {self.keyword_validation['metric']}")
            if self.keyword_validation["issues"]:
                lines.append("")
                lines.append("**Issues:**")
                for issue in self.keyword_validation["issues"]:
                    lines.append(f"- {issue}")
            lines.append("")
            lines.append("*Note: Keywords should be integrated naturally, not forced*")
            lines.append("")

        # SEO Validation for Blog Posts (if available)
        if self.seo_validation and not self.seo_validation.get("skipped", False):
            lines.append("## SEO Optimization (Blog Posts)")
            lines.append("")
            seo_status = "[PASS] PASSED" if self.seo_validation["passed"] else "[FAIL] FAILED"
            lines.append(f"**Status:** {seo_status}")
            lines.append(f"**Average SEO Score:** {self.seo_validation['average_score']}/100")
            lines.append(f"**Metric:** {self.seo_validation['metric']}")
            if self.seo_validation.get("recommendations"):
                lines.append("")
                lines.append("**SEO Recommendations:**")
                for rec in self.seo_validation["recommendations"][:5]:  # Top 5
                    lines.append(f"- {rec}")
            if self.seo_validation["issues"]:
                lines.append("")
                lines.append("**Issues:**")
                for issue in self.seo_validation["issues"]:
                    lines.append(f"- {issue}")
            lines.append("")

        # Citation Warnings (advisory — do not affect pass/fail)
        if self.citation_validation:
            lines.append("## Citation Warnings")
            lines.append("")
            lines.append(
                "*The following posts contain source-attributed claims. "
                "Verify each citation is accurate before publishing.*"
            )
            lines.append("")
            for warning in self.citation_validation.get("warnings", []):
                lines.append(f"- {warning}")
            lines.append("")

        # Predicted Engagement (advisory — pre-publish signal, no pass/fail impact)
        if self.engagement_prediction:
            ep = self.engagement_prediction
            lines.append("## Predicted Engagement (advisory)")
            lines.append("")
            lines.append(f"**Average Score:** {ep['average_score']:.0f}/100")
            lines.append(f"**Lowest Score:** {ep['min_score']:.0f}/100")
            lines.append(
                f"**Below Floor ({ep['weak_floor']:.0f}):** "
                f"{ep['weak_count']} of {ep['total']} posts"
            )
            lines.append("")
            lines.append(
                "*Heuristic pre-publish estimate (hook, length fit, CTA, genericity) — "
                "not a guarantee of performance.*"
            )
            lines.append("")

        # GEO Answer Blocks (advisory — blog answer-engine readiness, no pass/fail impact)
        if self.answer_block_geo:
            ab = self.answer_block_geo
            lines.append("## GEO Answer Blocks (advisory)")
            lines.append("")
            lines.append(
                f"**Well-formed openings:** {ab['ok_count']} of {ab['total']} blog posts "
                "(a self-contained ~40–60-word opening answer)"
            )
            if ab["weak_count"]:
                lines.append(
                    f"**Needs attention:** {ab['weak_count']} blog posts "
                    "(opening isn't a ~40–60-word answer block)"
                )
            lines.append("")
            lines.append(
                "*AI answer engines preferentially cite a short, self-contained opening answer — "
                "a GEO signal, not a pass/fail gate.*"
            )
            lines.append("")

        # Recommendations
        if self.total_issues > 0:
            lines.append("## Recommendations")
            lines.append("")
            if not self.hook_validation["passed"]:
                lines.append(
                    "- **Hook Uniqueness:** Review duplicate hooks and revise for uniqueness"
                )
            if not self.cta_validation["passed"]:
                if self.cta_validation.get("is_hashtag_check"):
                    lines.append(
                        "- **Hashtag Coverage:** Add 1-2 keyword-derived hashtags to all microblog posts"
                    )
                else:
                    lines.append(
                        "- **CTA Variety:** Diversify call-to-action patterns across posts"
                    )
            if not self.length_validation["passed"]:
                lines.append("- **Length:** Adjust post lengths to optimal range (150-250 words)")
            if not self.headline_validation["passed"]:
                lines.append(
                    "- **Headline Engagement:** Add engagement elements to weak headlines (numbers, power words, questions, emotional triggers)"
                )
            lines.append("")

        return "\n".join(lines)

    def to_summary_string(self) -> str:
        """
        Generate concise summary for CLI display

        Returns:
            Summary string
        """
        status = "[PASS] PASSED" if self.overall_passed else "[WARN] NEEDS REVIEW"
        return (
            f"QA Report: {status} | "
            f"Quality: {self.quality_score:.0%} | "
            f"Issues: {self.total_issues}"
        )
