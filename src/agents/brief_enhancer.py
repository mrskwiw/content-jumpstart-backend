"""Brief Enhancement Agent: Auto-enriches weak briefs with AI suggestions"""

import json
from typing import Any, Dict, Optional

from ..models.brief_quality import BriefQualityReport
from ..models.client_brief import ClientBrief
from ..utils.anthropic_client import AnthropicClient
from ..utils.logger import logger


class BriefEnhancerAgent:
    """
    Agent that automatically enhances weak briefs with AI-suggested improvements
    while maintaining client voice and not inventing facts
    """

    def __init__(self, client: Optional[AnthropicClient] = None):
        """
        Initialize Brief Enhancer Agent

        Args:
            client: Anthropic client instance (creates default if not provided)
        """
        self.client = client or AnthropicClient()

    def enhance_brief(
        self, client_brief: ClientBrief, quality_report: BriefQualityReport, auto_apply: bool = True
    ) -> ClientBrief:
        """
        Enhance brief by filling weak areas with AI suggestions

        Args:
            client_brief: Current brief state
            quality_report: Quality assessment
            auto_apply: If True, auto-fill suggestions; if False, just generate them

        Returns:
            Enhanced ClientBrief (or original if quality is already high)
        """
        logger.info(
            f"Enhancing brief for {client_brief.company_name} "
            f"(quality: {quality_report.overall_score:.0%})"
        )

        # Skip if quality is already high
        if quality_report.overall_score >= 0.85:
            logger.info("Brief quality is already high (≥85%), skipping enhancement")
            return client_brief

        # Generate enhancement suggestions
        enhancements = self._generate_enhancements(client_brief, quality_report)

        if not enhancements:
            logger.warning("No enhancements generated")
            return client_brief

        # Apply enhancements if requested
        if auto_apply:
            enhanced_brief = self._apply_enhancements(client_brief, enhancements)
            logger.info(f"Applied {len(enhancements)} enhancements")
            return enhanced_brief
        else:
            logger.info(f"Generated {len(enhancements)} suggestions (not applied)")
            return client_brief

    def _generate_enhancements(
        self, client_brief: ClientBrief, quality_report: BriefQualityReport
    ) -> Dict[str, Any]:
        """
        Generate AI suggestions for weak/missing fields

        Args:
            client_brief: Current brief state
            quality_report: Quality assessment

        Returns:
            Dictionary of field_name -> suggested_value
        """
        # Build current brief data for context
        brief_data = client_brief.model_dump()

        # Identify fields that need enhancement
        enhancement_targets = []

        # Add weak fields (present but inadequate)
        for field in quality_report.weak_fields:
            current_value = brief_data.get(field)
            enhancement_targets.append(
                {"field": field, "current_value": current_value, "issue": "too generic or brief"}
            )

        # Add high-priority missing fields
        for field in quality_report.missing_fields:
            # Only suggest enhancements for fields we can reasonably infer
            if field in ["target_platforms", "posting_frequency"]:
                enhancement_targets.append(
                    {"field": field, "current_value": None, "issue": "missing"}
                )

        if not enhancement_targets:
            return {}

        # Build enhancement prompt
        enhancement_prompt = self._build_enhancement_prompt(client_brief, enhancement_targets)

        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": enhancement_prompt}],
                system="You are a content strategist enhancing client briefs. Return only JSON.",
                temperature=0.5,
                max_tokens=1000,
            )

            # Parse response
            enhancements = self._extract_json(response)

            logger.info(f"Generated enhancements for {len(enhancements)} fields")
            return enhancements

        except Exception as e:
            logger.error(f"Enhancement generation failed: {e}", exc_info=True)
            return {}

    def _build_enhancement_prompt(
        self, client_brief: ClientBrief, enhancement_targets: list
    ) -> str:
        """
        Build prompt for enhancement generation

        Args:
            client_brief: Current brief
            enhancement_targets: List of fields to enhance

        Returns:
            Enhancement prompt string
        """
        brief_context = {
            "company_name": client_brief.company_name,
            "business_description": client_brief.business_description,
            "ideal_customer": client_brief.ideal_customer,
            "main_problem_solved": client_brief.main_problem_solved,
        }

        targets_str = "\n".join(
            [
                f"- {target['field']}: {target['issue']} (current: {target.get('current_value', 'None')})"
                for target in enhancement_targets
            ]
        )

        prompt = f"""You are enhancing a client brief for content generation.

**Current Brief Context:**
{json.dumps(brief_context, indent=2)}

**Fields that need enhancement:**
{targets_str}

**Task:**
Suggest improvements for the weak/missing fields listed above. Follow these rules:

1. **Maintain client voice** - Don't change their tone or language style
2. **Don't invent facts** - Only suggest defaults or industry standards
3. **Be specific** - Avoid generic corporate speak
4. **Mark uncertainty** - If you can't reasonably infer a value, return "NEED_CLIENT_INPUT"

**For weak fields:** Expand or make more specific based on the context provided.
**For missing fields:** Suggest industry-standard defaults only if clearly appropriate.

Return JSON with suggested enhancements:
{{
  "field_name": "suggested value or NEED_CLIENT_INPUT",
  ...
}}

Return ONLY valid JSON, no additional commentary."""

        return prompt

    def _apply_enhancements(
        self, client_brief: ClientBrief, enhancements: Dict[str, Any]
    ) -> ClientBrief:
        """
        Apply enhancement suggestions to brief

        Args:
            client_brief: Current brief
            enhancements: Dictionary of field -> suggested value

        Returns:
            Updated ClientBrief
        """
        updated_data = client_brief.model_dump()
        applied_count = 0

        for field_name, suggested_value in enhancements.items():
            # Skip if marked as needs client input
            if suggested_value == "NEED_CLIENT_INPUT":
                logger.debug(f"Skipping {field_name}: needs client input")
                continue

            # Get current value
            current_value = updated_data.get(field_name)

            # Apply enhancement if current value is weak/missing
            should_apply = False

            if current_value is None:
                should_apply = True
            elif isinstance(current_value, str) and not current_value.strip():
                should_apply = True
            elif isinstance(current_value, list) and len(current_value) == 0:
                should_apply = True
            elif isinstance(current_value, str) and len(current_value.split()) < 5:
                # Current value is too short, enhance it
                should_apply = True

            if should_apply:
                updated_data[field_name] = suggested_value
                applied_count += 1
                logger.debug(f"Applied enhancement to {field_name}")

        if applied_count > 0:
            logger.info(f"Applied {applied_count} enhancements")

        try:
            return ClientBrief(**updated_data)
        except Exception as e:
            logger.error(f"Failed to create enhanced brief: {e}", exc_info=True)
            # Return original brief if enhancement fails validation
            return client_brief

    def _extract_json(self, response: str) -> Dict[str, Any]:
        """
        Extract JSON from API response

        Args:
            response: API response text

        Returns:
            Parsed JSON dictionary

        Raises:
            ValueError: If JSON extraction fails
        """
        import re

        # Try to find JSON block
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Assume entire response is JSON
            json_str = response.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {response}")
            raise ValueError(f"Invalid JSON in response: {str(e)}")

    def suggest_enhancements_only(
        self, client_brief: ClientBrief, quality_report: BriefQualityReport
    ) -> Dict[str, str]:
        """
        Generate enhancement suggestions without applying them

        Useful for showing suggestions to user before applying.

        Args:
            client_brief: Current brief
            quality_report: Quality assessment

        Returns:
            Dictionary of field_name -> suggestion text for display
        """
        enhancements = self._generate_enhancements(client_brief, quality_report)

        # Format for display
        suggestions = {}
        for field_name, value in enhancements.items():
            if value != "NEED_CLIENT_INPUT":
                suggestions[field_name] = value

        return suggestions
