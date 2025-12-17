"""Brief Quality Checker Agent: Assesses completeness and quality of client briefs"""

from typing import Dict, List, Optional

from ..models.brief_quality import BriefQualityReport, FieldQuality
from ..models.client_brief import ClientBrief
from ..utils.anthropic_client import AnthropicClient
from ..utils.logger import logger


class BriefQualityChecker:
    """
    Agent that analyzes brief quality and identifies gaps/weaknesses
    """

    # Field weights for overall score calculation
    # Higher weight = more critical for content generation
    FIELD_WEIGHTS = {
        # Critical fields (must have)
        "company_name": 1.0,
        "business_description": 1.0,
        "ideal_customer": 1.0,
        "main_problem_solved": 1.0,
        "brand_personality": 0.9,
        # Important fields (should have)
        "customer_pain_points": 0.8,
        "customer_questions": 0.8,
        "key_phrases": 0.7,
        "stories": 0.7,
        "main_cta": 0.6,
        # Optional fields (nice to have)
        "misconceptions": 0.5,
        "measurable_results": 0.5,
        "case_studies": 0.4,
        "founder_name": 0.3,
        "target_platforms": 0.5,
        "posting_frequency": 0.3,
    }

    def __init__(self, client: Optional[AnthropicClient] = None):
        """
        Initialize Brief Quality Checker

        Args:
            client: Anthropic client instance (creates default if not provided)
        """
        self.client = client or AnthropicClient()

    def assess_brief(self, client_brief: ClientBrief) -> BriefQualityReport:
        """
        Comprehensive brief quality assessment

        Args:
            client_brief: ClientBrief to assess

        Returns:
            BriefQualityReport with scores and recommendations
        """
        logger.info(f"Assessing brief quality for {client_brief.company_name}")

        # Assess each field
        field_quality: Dict[str, FieldQuality] = {}
        missing_fields: List[str] = []
        weak_fields: List[str] = []
        strong_fields: List[str] = []

        for field_name in self.FIELD_WEIGHTS.keys():
            quality = self._assess_field(client_brief, field_name)
            field_quality[field_name] = quality

            if quality == FieldQuality.MISSING:
                missing_fields.append(field_name)
            elif quality == FieldQuality.WEAK:
                weak_fields.append(field_name)
            elif quality == FieldQuality.STRONG:
                strong_fields.append(field_name)

        # Calculate scores
        completeness_score = self._calculate_completeness(field_quality)
        specificity_score = self._calculate_specificity(client_brief)
        usability_score = self._calculate_usability(field_quality)
        overall_score = (completeness_score + specificity_score + usability_score) / 3.0

        # Generate recommendations
        priority_improvements = self._generate_recommendations(
            missing_fields, weak_fields, field_quality
        )

        # Determine if ready for content generation
        can_generate = self._can_generate_content(field_quality)
        minimum_questions = self._calculate_minimum_questions(missing_fields, weak_fields)

        # Count filled fields (adequate + strong)
        filled_count = sum(
            1
            for quality in field_quality.values()
            if quality in [FieldQuality.ADEQUATE, FieldQuality.STRONG]
        )

        # Count required fields filled
        required_fields = [
            "company_name",
            "business_description",
            "ideal_customer",
            "main_problem_solved",
        ]
        required_filled = sum(
            1
            for field in required_fields
            if field_quality.get(field) not in [FieldQuality.MISSING, None]
        )

        report = BriefQualityReport(
            overall_score=overall_score,
            completeness_score=completeness_score,
            specificity_score=specificity_score,
            usability_score=usability_score,
            field_quality=field_quality,
            missing_fields=missing_fields,
            weak_fields=weak_fields,
            strong_fields=strong_fields,
            priority_improvements=priority_improvements,
            can_generate_content=can_generate,
            minimum_questions_needed=minimum_questions,
            total_fields=len(self.FIELD_WEIGHTS),
            filled_fields=filled_count,
            required_fields_filled=required_filled,
        )

        logger.info(
            f"Brief assessment complete: {overall_score:.0%} overall, "
            f"{filled_count}/{len(self.FIELD_WEIGHTS)} fields filled"
        )

        return report

    def _assess_field(self, brief: ClientBrief, field_name: str) -> FieldQuality:
        """
        Assess quality of a single field

        Args:
            brief: ClientBrief to assess
            field_name: Name of field to assess

        Returns:
            FieldQuality rating
        """
        value = getattr(brief, field_name, None)

        # Check if missing
        if value is None:
            return FieldQuality.MISSING

        if isinstance(value, str):
            if not value.strip():
                return FieldQuality.MISSING

            # Check for generic/placeholder values
            generic_indicators = [
                "not specified",
                "unknown",
                "tbd",
                "n/a",
                "none",
                "no description provided",
                "not provided",
            ]
            if any(indicator in value.lower() for indicator in generic_indicators):
                return FieldQuality.WEAK

            # Assess based on length and detail
            word_count = len(value.split())
            if word_count < 5:
                return FieldQuality.WEAK
            elif word_count >= 15:
                return FieldQuality.STRONG
            else:
                return FieldQuality.ADEQUATE

        if isinstance(value, list):
            if len(value) == 0:
                return FieldQuality.MISSING
            elif len(value) == 1:
                return FieldQuality.WEAK
            elif len(value) >= 4:
                return FieldQuality.STRONG
            else:
                return FieldQuality.ADEQUATE

        # For enum or other types, just check if present
        return FieldQuality.ADEQUATE

    def _calculate_completeness(self, field_quality: Dict[str, FieldQuality]) -> float:
        """
        Calculate completeness score based on field weights

        Args:
            field_quality: Quality ratings for each field

        Returns:
            Completeness score (0.0-1.0)
        """
        total_weight = sum(self.FIELD_WEIGHTS.values())
        achieved_weight = 0.0

        for field_name, quality in field_quality.items():
            weight = self.FIELD_WEIGHTS.get(field_name, 0)

            if quality == FieldQuality.STRONG:
                achieved_weight += weight
            elif quality == FieldQuality.ADEQUATE:
                achieved_weight += weight * 0.7
            elif quality == FieldQuality.WEAK:
                achieved_weight += weight * 0.3
            # MISSING contributes 0

        return achieved_weight / total_weight if total_weight > 0 else 0.0

    def _calculate_specificity(self, brief: ClientBrief) -> float:
        """
        Calculate how specific vs generic the brief is using LLM analysis

        Args:
            brief: ClientBrief to analyze

        Returns:
            Specificity score (0.0-1.0)
        """
        # Build sample text for analysis
        sample_text = f"""Business: {brief.business_description}
Customer: {brief.ideal_customer}
Problem: {brief.main_problem_solved}
Pain Points: {', '.join(brief.customer_pain_points[:3]) if brief.customer_pain_points else 'None provided'}"""

        specificity_prompt = f"""Assess the specificity of this client brief on a scale of 0.0 to 1.0.

0.0 = Extremely generic (e.g., "We help businesses grow")
0.5 = Somewhat specific (e.g., "We help SaaS companies with marketing")
1.0 = Very specific (e.g., "We help Series A fintech SaaS companies reduce CAC by 40% through content SEO")

Client Brief:
{sample_text}

Return ONLY a number between 0.0 and 1.0, no explanation."""

        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": specificity_prompt}],
                system="You are a brief quality assessor. Return only a number.",
                temperature=0.2,
                max_tokens=10,
            )

            # Parse score from response
            score_str = response.strip()
            score = float(score_str)
            return max(0.0, min(1.0, score))  # Clamp to 0.0-1.0

        except Exception as e:
            logger.warning(f"Failed to calculate specificity score: {e}, defaulting to 0.5")
            return 0.5  # Default to medium if LLM fails

    def _calculate_usability(self, field_quality: Dict[str, FieldQuality]) -> float:
        """
        Calculate usability for content generation

        Args:
            field_quality: Quality ratings for each field

        Returns:
            Usability score (0.0-1.0)
        """
        # Critical fields for content generation
        critical_fields = [
            "business_description",
            "ideal_customer",
            "main_problem_solved",
            "brand_personality",
        ]

        critical_filled = sum(
            1
            for field in critical_fields
            if field_quality.get(field) in [FieldQuality.ADEQUATE, FieldQuality.STRONG]
        )

        return critical_filled / len(critical_fields)

    def _can_generate_content(self, field_quality: Dict[str, FieldQuality]) -> bool:
        """
        Determine if brief is sufficient for content generation

        Args:
            field_quality: Quality ratings for each field

        Returns:
            True if ready to generate, False otherwise
        """
        # Must have all critical fields at least adequate
        critical_fields = [
            "company_name",
            "business_description",
            "ideal_customer",
            "main_problem_solved",
        ]

        for field in critical_fields:
            if field_quality.get(field) == FieldQuality.MISSING:
                return False

        # Must have at least 2 supporting fields
        supporting_fields = [
            "brand_personality",
            "customer_pain_points",
            "customer_questions",
            "key_phrases",
        ]

        supporting_count = sum(
            1
            for field in supporting_fields
            if field_quality.get(field) in [FieldQuality.ADEQUATE, FieldQuality.STRONG]
        )

        return supporting_count >= 2

    def _calculate_minimum_questions(
        self, missing_fields: List[str], weak_fields: List[str]
    ) -> int:
        """
        Calculate minimum questions needed to be ready for generation

        Args:
            missing_fields: List of missing field names
            weak_fields: List of weak field names

        Returns:
            Number of questions needed
        """
        # Count critical missing fields
        critical_missing = [f for f in missing_fields if self.FIELD_WEIGHTS.get(f, 0) >= 0.8]

        # Add top 3 weak fields
        critical_weak = [f for f in weak_fields[:3] if self.FIELD_WEIGHTS.get(f, 0) >= 0.6]

        return len(critical_missing) + len(critical_weak)

    def _generate_recommendations(
        self,
        missing_fields: List[str],
        weak_fields: List[str],
        field_quality: Dict[str, FieldQuality],
    ) -> List[str]:
        """
        Generate top priority improvement recommendations

        Args:
            missing_fields: List of missing field names
            weak_fields: List of weak field names
            field_quality: Quality ratings for all fields

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Prioritize critical missing fields
        critical_missing = [f for f in missing_fields if self.FIELD_WEIGHTS.get(f, 0) >= 0.8]
        if critical_missing:
            field_names = ", ".join(critical_missing)
            recommendations.append(f"Add critical information: {field_names}")

        # Then important weak fields
        important_weak = [f for f in weak_fields if self.FIELD_WEIGHTS.get(f, 0) >= 0.7]
        if important_weak:
            field_names = ", ".join(important_weak)
            recommendations.append(f"Improve specificity of: {field_names}")

        # Add specific guidance for common issues
        if field_quality.get("brand_personality") == FieldQuality.MISSING:
            recommendations.append(
                "Add brand personality traits (e.g., approachable, data-driven, witty)"
            )

        if field_quality.get("customer_pain_points") in [FieldQuality.MISSING, FieldQuality.WEAK]:
            recommendations.append("List at least 3 specific customer pain points")

        if field_quality.get("stories") == FieldQuality.MISSING:
            recommendations.append("Add 1-2 customer stories or personal examples for authenticity")

        if field_quality.get("customer_questions") in [FieldQuality.MISSING, FieldQuality.WEAK]:
            recommendations.append("List top 5 questions your customers always ask")

        if field_quality.get("main_cta") == FieldQuality.MISSING:
            recommendations.append("Define the main call-to-action for your content")

        # Return top 5 recommendations
        return recommendations[:5]
