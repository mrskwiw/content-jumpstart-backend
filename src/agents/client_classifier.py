"""Client Classifier Agent: Determines client business type for template selection"""

from typing import Tuple

from ..config.template_rules import CLIENT_TYPE_KEYWORDS, ClientType
from ..models.client_brief import ClientBrief
from ..utils.logger import logger


class ClientClassifier:
    """
    Agent that classifies clients into business types for intelligent template selection
    """

    def classify_client(self, client_brief: ClientBrief) -> Tuple[ClientType, float]:
        """
        Classify client into a business type based on their brief

        Args:
            client_brief: ClientBrief instance with client information

        Returns:
            Tuple of (ClientType, confidence_score)
            confidence_score is between 0.0 and 1.0
        """
        # Combine text fields for analysis
        business_text = (
            f"{client_brief.business_description} {client_brief.main_problem_solved}"
        ).lower()
        customer_text = f"{client_brief.ideal_customer}".lower()

        # Score each client type
        scores = {}

        for client_type, keywords in CLIENT_TYPE_KEYWORDS.items():
            score = 0.0
            total_keywords = 0

            # Check business description keywords
            if "business_description" in keywords:
                for keyword in keywords["business_description"]:
                    total_keywords += 1
                    if keyword in business_text:
                        score += 1.0

            # Check ideal customer keywords
            if "ideal_customer" in keywords:
                for keyword in keywords["ideal_customer"]:
                    total_keywords += 1
                    if keyword in customer_text:
                        score += 1.0

            # Calculate confidence as percentage of keywords matched
            if total_keywords > 0:
                scores[client_type] = score / total_keywords
            else:
                scores[client_type] = 0.0

        # Find best match
        if not scores:
            return ClientType.UNKNOWN, 0.0

        best_type = max(scores, key=lambda x: scores[x])
        confidence = scores[best_type]

        # If confidence is too low, return UNKNOWN
        if confidence < 0.15:  # At least 15% keyword match required
            logger.info(
                f"Client classification uncertain (confidence: {confidence:.2%}), using UNKNOWN"
            )
            return ClientType.UNKNOWN, confidence

        logger.info(f"Classified client as {best_type.value} (confidence: {confidence:.2%})")

        return best_type, confidence

    def get_classification_reasoning(
        self, client_brief: ClientBrief, client_type: ClientType, confidence: float
    ) -> str:
        """
        Generate human-readable explanation of classification

        Args:
            client_brief: Client brief
            client_type: Classified type
            confidence: Confidence score

        Returns:
            Explanation string
        """
        reasoning = f"Client Type: {client_type.value.replace('_', ' ').title()}\n"
        reasoning += f"Confidence: {confidence:.1%}\n\n"

        if client_type == ClientType.UNKNOWN:
            reasoning += "Classification uncertain - using default safe template set.\n"
            reasoning += "Consider reviewing business description for clearer industry signals.\n"
        else:
            reasoning += "Based on analysis of:\n"
            reasoning += f"- Business: {client_brief.business_description[:100]}...\n"
            reasoning += f"- Customer: {client_brief.ideal_customer[:100]}...\n"

        return reasoning
