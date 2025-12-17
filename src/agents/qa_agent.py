"""QA Agent: Quality Assurance orchestrator for post validation"""

from typing import List, Optional

from ..models.post import Post
from ..models.qa_report import QAReport
from ..models.seo_keyword import KeywordStrategy
from ..utils.logger import logger
from ..validators.cta_validator import CTAValidator
from ..validators.headline_validator import HeadlineValidator
from ..validators.hook_validator import HookValidator
from ..validators.keyword_validator import KeywordValidator
from ..validators.length_validator import LengthValidator


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
        self.headline_validator = HeadlineValidator(min_elements=3)

        # Optional keyword validator
        self.keyword_validator = None
        if keyword_strategy:
            self.keyword_validator = KeywordValidator(keyword_strategy)

    def validate_posts(self, posts: List[Post], client_name: str) -> QAReport:
        """
        Run quality validation on a set of posts

        Args:
            posts: List of Post objects to validate
            client_name: Client name for report

        Returns:
            QAReport with validation results
        """
        logger.info(f"Running QA validation on {len(posts)} posts")

        # Run all validators
        hook_results = self.hook_validator.validate(posts)
        cta_results = self.cta_validator.validate(posts)
        length_results = self.length_validator.validate(posts)
        headline_results = self.headline_validator.validate(posts)

        # Run keyword validation if available
        keyword_results = None
        if self.keyword_validator:
            keyword_results = self.keyword_validator.validate(posts)

        # Collect all issues
        all_issues = []
        all_issues.extend(hook_results.get("issues", []))
        all_issues.extend(cta_results.get("issues", []))
        all_issues.extend(length_results.get("issues", []))
        all_issues.extend(headline_results.get("issues", []))
        if keyword_results:
            all_issues.extend(keyword_results.get("issues", []))

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

        quality_score = sum(scores) / len(scores) if scores else 0.0

        # Determine overall pass/fail
        overall_passed = (
            hook_results.get("passed", True)
            and cta_results.get("passed", True)
            and length_results.get("passed", True)
            and headline_results.get("passed", True)
            and (keyword_results.get("passed", True) if keyword_results else True)
        )

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
            total_issues=len(all_issues),
            all_issues=all_issues,
        )

        logger.info(
            f"QA validation complete: {'PASSED' if overall_passed else 'FAILED'} "
            f"(Quality: {quality_score:.1%}, Issues: {len(all_issues)})"
        )

        return report
