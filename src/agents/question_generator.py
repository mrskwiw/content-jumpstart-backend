"""Question Generator Agent: Creates targeted questions to fill brief gaps"""

import json
from typing import Any, Dict, List, Optional

from ..models.brief_quality import BriefQualityReport
from ..models.client_brief import ClientBrief
from ..models.question import Question, QuestionType
from ..utils.anthropic_client import AnthropicClient
from ..utils.logger import logger


class QuestionGeneratorAgent:
    """
    Agent that generates smart, contextual questions based on brief quality report
    """

    # Question templates for each field
    # Each template includes the question text and an example answer
    QUESTION_TEMPLATES: Dict[str, Dict[str, str]] = {
        "business_description": {
            "text": "Can you describe what your business does in one sentence? Be specific about who you serve and what problem you solve.",
            "example": "We help Series A SaaS companies reduce customer churn by 40% through AI-powered retention analytics.",
        },
        "ideal_customer": {
            "text": "Who is your ideal customer? Be specific about their role, company size, industry, and current situation.",
            "example": "VP of Sales at B2B SaaS companies with $2-10M ARR who are struggling to hit quota with their current sales team.",
        },
        "customer_pain_points": {
            "text": "What are the top 3-5 pain points your customers face before working with you? What keeps them up at night?",
            "example": "1) Can't predict which deals will close, 2) Sales team spending too much time on unqualified leads, 3) Losing deals to competitors with better data",
        },
        "brand_personality": {
            "text": "How would you describe your brand personality? Choose 2-3 traits that describe your communication style.",
            "example": "Direct, data-driven, conversational (not: corporate jargon, overly formal, salesy)",
        },
        "customer_questions": {
            "text": "What are the top 5 questions your customers always ask you? What do they want to know before buying?",
            "example": "1) How long until we see results? 2) Do you integrate with Salesforce? 3) What's your pricing model?",
        },
        "stories": {
            "text": "Tell me 1-2 specific stories: either a customer success story or a personal experience that shaped your business philosophy.",
            "example": "We had a customer who was about to shut down their sales team until our platform helped them close $2M in deals in 90 days.",
        },
        "main_cta": {
            "text": "What's the main action you want readers to take after seeing your content?",
            "example": "Book a 15-minute demo call to see the platform in action",
        },
        "misconceptions": {
            "text": "What are 2-3 common misconceptions in your industry that you want to correct?",
            "example": "1) You need a huge budget for content marketing, 2) SEO is dead, 3) You can't measure content ROI",
        },
        "key_phrases": {
            "text": "What specific phrases or terminology do you always use? What language patterns are uniquely yours?",
            "example": "We say 'revenue intelligence' not 'sales analytics', 'deal velocity' not 'sales cycle time'",
        },
        "measurable_results": {
            "text": "What measurable results do you deliver? Use specific numbers or percentages.",
            "example": "Reduce hiring time from 6 weeks to 2 weeks, increase close rates by 35%",
        },
        "founder_name": {
            "text": "What's the name of the founder or primary voice for this content?",
            "example": "Sarah Chen, CEO",
        },
        "target_platforms": {
            "text": "Which platforms do you want to create content for? (LinkedIn, Twitter, Blog, Email, etc.)",
            "example": "LinkedIn and Blog primarily",
        },
        "case_studies": {
            "text": "Do you have any case studies or customer success stories we can reference? Provide links or brief summaries.",
            "example": "Helped Acme Corp increase revenue by $500K in 6 months: [link]",
        },
    }

    # Field weights from BriefQualityChecker to determine priority
    FIELD_WEIGHTS = {
        "company_name": 1.0,
        "business_description": 1.0,
        "ideal_customer": 1.0,
        "main_problem_solved": 1.0,
        "brand_personality": 0.9,
        "customer_pain_points": 0.8,
        "customer_questions": 0.8,
        "key_phrases": 0.7,
        "stories": 0.7,
        "main_cta": 0.6,
        "misconceptions": 0.5,
        "measurable_results": 0.5,
        "case_studies": 0.4,
        "founder_name": 0.3,
        "target_platforms": 0.5,
    }

    def __init__(self, client: Optional[AnthropicClient] = None):
        """
        Initialize Question Generator Agent

        Args:
            client: Anthropic client instance (creates default if not provided)
        """
        self.client = client or AnthropicClient()

    def generate_questions(
        self, client_brief: ClientBrief, quality_report: BriefQualityReport, max_questions: int = 5
    ) -> List[Question]:
        """
        Generate targeted questions based on brief quality

        Args:
            client_brief: Current brief state
            quality_report: Quality assessment
            max_questions: Maximum questions to generate

        Returns:
            List of Question objects, ordered by priority
        """
        logger.info(
            f"Generating questions for {client_brief.company_name}: "
            f"{len(quality_report.missing_fields)} missing, "
            f"{len(quality_report.weak_fields)} weak fields"
        )

        questions: List[Question] = []

        # Generate questions for missing critical fields (priority 1)
        for field in quality_report.missing_fields:
            if self.FIELD_WEIGHTS.get(field, 0) >= 0.8:
                question = self._generate_question_for_field(field, client_brief, priority=1)
                if question:
                    questions.append(question)

        # Generate questions for weak important fields (priority 2)
        for field in quality_report.weak_fields:
            if self.FIELD_WEIGHTS.get(field, 0) >= 0.6:
                question = self._generate_question_for_field(
                    field, client_brief, priority=2, is_clarifying=True
                )
                if question:
                    questions.append(question)

        # Add optional enrichment questions if still under max (priority 3)
        if len(questions) < max_questions:
            optional_fields = ["stories", "misconceptions", "case_studies", "measurable_results"]
            for field in optional_fields:
                if field in quality_report.missing_fields:
                    question = self._generate_question_for_field(field, client_brief, priority=3)
                    if question:
                        questions.append(question)
                        if len(questions) >= max_questions:
                            break

        # Sort by priority (critical first) and limit
        questions.sort(key=lambda q: (q.priority, q.field_name))
        limited_questions = questions[:max_questions]

        logger.info(f"Generated {len(limited_questions)} questions")
        return limited_questions

    def _generate_question_for_field(
        self, field_name: str, client_brief: ClientBrief, priority: int, is_clarifying: bool = False
    ) -> Optional[Question]:
        """
        Generate a question for a specific field

        Args:
            field_name: Name of the ClientBrief field
            client_brief: Current brief state
            priority: Question priority (1-3)
            is_clarifying: If True, this is asking for more detail on existing value

        Returns:
            Question object or None if template not found
        """
        template = self.QUESTION_TEMPLATES.get(field_name)
        if not template:
            logger.warning(f"No question template for field: {field_name}")
            return None

        # Get current value for context
        current_value = getattr(client_brief, field_name, None)

        if is_clarifying and current_value:
            # Generate clarifying question
            text = f"You mentioned: '{current_value}'. Can you be more specific? {template['text']}"
            context = f"Need more detail for {field_name}"
            question_type = QuestionType.CLARIFYING
        else:
            # Use template question
            text = template["text"]
            context = f"Missing: {field_name}"
            question_type = QuestionType.OPEN_ENDED

        return Question(
            text=text,
            field_name=field_name,
            question_type=question_type,
            context=context,
            example_answer=template.get("example"),
            priority=priority,
        )

    def generate_follow_up_question(
        self, field_name: str, user_answer: str, client_brief: ClientBrief
    ) -> Optional[Question]:
        """
        Generate intelligent follow-up question based on user's answer

        Uses LLM to analyze if the answer is sufficient or needs clarification.

        Args:
            field_name: Which field they answered for
            user_answer: Their answer text
            client_brief: Current brief state

        Returns:
            Follow-up question if needed, None if answer is sufficient
        """
        logger.info(f"Analyzing answer for follow-up: {field_name}")

        follow_up_prompt = f"""Analyze this client answer and determine if a follow-up question would improve quality.

Field: {field_name}
User Answer: "{user_answer}"

Consider:
- Is the answer too vague or generic?
- Are there obvious gaps in detail?
- Could we get more specific information?
- Is the answer long enough and detailed enough?

Return JSON:
{{
  "needs_followup": true or false,
  "reason": "brief explanation why or why not",
  "suggested_question": "the follow-up question text" (only if needs_followup=true)
}}

Return ONLY valid JSON, no other text."""

        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": follow_up_prompt}],
                system="You are a content strategist conducting client discovery. Return only JSON.",
                temperature=0.4,
                max_tokens=200,
            )

            # Extract JSON from response
            result = self._extract_json(response)

            if result.get("needs_followup"):
                logger.info(f"Follow-up needed: {result['reason']}")
                return Question(
                    text=result["suggested_question"],
                    field_name=field_name,
                    question_type=QuestionType.CLARIFYING,
                    context=result["reason"],
                    example_answer=None,
                    priority=2,
                )
            else:
                logger.info(f"Answer is sufficient: {result['reason']}")
                return None

        except Exception as e:
            logger.warning(f"Failed to generate follow-up question: {e}")
            return None

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
