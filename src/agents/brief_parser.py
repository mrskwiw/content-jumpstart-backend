"""Brief Parser Agent: Extracts structured information from client briefs"""

import json
from typing import Any, Dict, Optional

from ..config.constants import BRIEF_PARSING_TEMPERATURE
from ..config.prompts import SystemPrompts
from ..exceptions import BriefParsingError
from ..models.client_brief import ClientBrief, DataUsagePreference, Platform, TonePreference
from ..utils.anthropic_client import AnthropicClient
from ..utils.logger import logger


class BriefParserAgent:
    """
    Agent that uses Anthropic API to parse and structure client briefs
    """

    # Use centralized system prompt
    SYSTEM_PROMPT = SystemPrompts.BRIEF_PARSER

    def __init__(self, client: Optional[AnthropicClient] = None):
        """
        Initialize Brief Parser Agent

        Args:
            client: Anthropic client instance (creates default if not provided)
        """
        self.client = client or AnthropicClient()

    def parse_brief(self, brief_text: str) -> ClientBrief:
        """
        Parse raw client brief text into structured ClientBrief

        Args:
            brief_text: Raw text from client brief form or conversation

        Returns:
            Structured ClientBrief object

        Raises:
            ValueError: If parsing fails or required fields missing
        """
        logger.info("Parsing client brief with Anthropic API")

        try:
            # Get structured JSON from API using centralized temperature
            response = self.client.create_message(
                messages=[{"role": "user", "content": brief_text}],
                system=self.SYSTEM_PROMPT,
                temperature=BRIEF_PARSING_TEMPERATURE,
            )

            # Parse JSON response
            brief_data = self._extract_json_from_response(response)

            # Validate and convert to ClientBrief
            client_brief = self._convert_to_client_brief(brief_data)

            logger.info(f"Successfully parsed brief for {client_brief.company_name}")
            return client_brief

        except BriefParsingError:
            # Re-raise custom exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Failed to parse client brief: {str(e)}", exc_info=True)
            raise BriefParsingError(f"Brief parsing failed: {str(e)}")

    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        Extract JSON from API response

        Args:
            response: API response text

        Returns:
            Parsed JSON dictionary

        Raises:
            ValueError: If JSON extraction fails
        """
        # Try to find JSON in response
        # Sometimes the model wraps JSON in markdown code blocks
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

    def _convert_to_client_brief(self, data: Dict[str, Any]) -> ClientBrief:
        """
        Convert parsed dictionary to ClientBrief model

        Args:
            data: Parsed brief data dictionary

        Returns:
            ClientBrief instance

        Raises:
            ValueError: If required fields missing or invalid
        """
        # Convert string personality values to enum
        brand_personality = []
        for personality in data.get("brand_personality", []):
            try:
                brand_personality.append(TonePreference(personality.lower()))
            except ValueError:
                logger.warning(f"Unknown personality type: {personality}, skipping")

        # Convert platform strings to enum
        target_platforms = []
        for platform in data.get("target_platforms", []):
            try:
                target_platforms.append(Platform(platform))
            except ValueError:
                logger.warning(f"Unknown platform: {platform}, skipping")

        # Convert data usage string to enum
        data_usage_str = data.get("data_usage", "moderate").lower()
        try:
            data_usage = DataUsagePreference(data_usage_str)
        except ValueError:
            logger.warning(f"Unknown data usage: {data_usage_str}, defaulting to moderate")
            data_usage = DataUsagePreference.MODERATE

        # Build ClientBrief
        try:
            client_brief = ClientBrief(
                company_name=data.get("company_name", "Unknown Company"),
                business_description=data.get("business_description", "No description provided"),
                ideal_customer=data.get("ideal_customer", "Not specified"),
                main_problem_solved=data.get("main_problem_solved", "Not specified"),
                customer_pain_points=data.get("customer_pain_points", []),
                customer_questions=data.get("customer_questions", []),
                brand_personality=brand_personality,
                key_phrases=data.get("key_phrases", []),
                target_platforms=target_platforms,
                posting_frequency=data.get("posting_frequency", "3-4x weekly"),
                data_usage=data_usage,
                stories=data.get("stories", data.get("personal_stories", [])),
                misconceptions=data.get("misconceptions", data.get("avoid_topics", [])),
            )

            return client_brief

        except Exception as e:
            logger.error(f"Failed to create ClientBrief: {str(e)}", exc_info=True)
            raise ValueError(f"Invalid brief data: {str(e)}")

    def enrich_brief(self, client_brief: ClientBrief, additional_context: str) -> ClientBrief:
        """
        Enrich an existing brief with additional context

        Args:
            client_brief: Existing ClientBrief
            additional_context: Additional information to incorporate

        Returns:
            Updated ClientBrief
        """
        logger.info(f"Enriching brief for {client_brief.company_name}")

        # Convert existing brief to dict for context
        existing_data = client_brief.model_dump()

        enrichment_prompt = f"""Here is an existing client brief:

{json.dumps(existing_data, indent=2)}

New information has been provided:

{additional_context}

Please merge this new information with the existing brief and return the complete updated JSON.
Keep all existing information unless the new information explicitly contradicts or updates it.

Return ONLY the complete updated JSON, no additional commentary."""

        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": enrichment_prompt}],
                system=self.SYSTEM_PROMPT,
                temperature=0.3,
            )

            brief_data = self._extract_json_from_response(response)
            updated_brief = self._convert_to_client_brief(brief_data)

            logger.info(f"Successfully enriched brief for {client_brief.company_name}")
            return updated_brief

        except Exception as e:
            logger.error(f"Failed to enrich brief: {str(e)}", exc_info=True)
            # Return original brief if enrichment fails
            logger.warning("Returning original brief due to enrichment failure")
            return client_brief
