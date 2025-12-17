"""Keyword Extraction Agent

AI-powered agent that extracts and suggests SEO keywords from client briefs.
"""

import json
from typing import Any, Dict, List

from anthropic import Anthropic

from ..config.settings import settings
from ..models.client_brief import ClientBrief
from ..models.seo_keyword import KeywordDifficulty, KeywordIntent, KeywordStrategy, SEOKeyword
from ..utils.logger import logger


class KeywordExtractionAgent:
    """Agent for extracting SEO keywords from client context"""

    def __init__(self):
        """Initialize keyword extraction agent"""
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.ANTHROPIC_MODEL

    def extract_keywords(self, client_brief: ClientBrief) -> KeywordStrategy:
        """
        Extract SEO keywords from client brief using AI

        Args:
            client_brief: Parsed client brief

        Returns:
            KeywordStrategy with extracted keywords
        """
        logger.info(f"Extracting SEO keywords for {client_brief.company_name}")

        # Build context for keyword extraction
        context = self._build_extraction_context(client_brief)

        # Generate keyword strategy using Claude
        # Use smaller max_tokens to avoid JSON truncation issues
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,  # Increased for complete JSON responses
            temperature=0.3,  # Lower temperature for more consistent extraction
            system=self._build_system_prompt(),
            messages=[
                {
                    "role": "user",
                    "content": f"Extract SEO keywords for this client:\n\n{context}\n\nReturn valid JSON ONLY.",
                }
            ],
        )

        # Parse response with robust JSON extraction
        keywords_json = response.content[0].text
        keywords_data = self._extract_json_from_response(keywords_json)

        # Convert to KeywordStrategy
        strategy = self._parse_keyword_strategy(keywords_data)

        logger.info(
            f"Extracted {len(strategy.primary_keywords)} primary, "
            f"{len(strategy.secondary_keywords)} secondary, "
            f"{len(strategy.longtail_keywords)} long-tail keywords"
        )

        return strategy

    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """
        Extract and parse JSON from Claude's response with robust error handling

        Args:
            response_text: Raw response text from Claude

        Returns:
            Parsed JSON data as dictionary

        Raises:
            ValueError: If JSON cannot be extracted or parsed
        """
        import re

        # Strategy 1: Remove markdown code fences
        text = response_text.strip()
        if text.startswith("```"):
            # Find JSON block between code fences
            match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
            else:
                # Fallback: just remove first and last lines
                lines = text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text = "\n".join(lines).strip()

        # Strategy 2: Find JSON object boundaries
        # Look for outermost { ... } in case there's extra text
        if not text.startswith("{"):
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                text = match.group(0)

        # Strategy 3: Try to parse JSON
        try:
            data = json.loads(text)
            logger.debug("Successfully parsed JSON response")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.debug(f"Attempted to parse: {text[:500]}...")

            # Strategy 4: Try to fix common JSON issues
            # Fix truncated JSON (common with max_tokens limit)
            if "Unterminated string" in str(e) or "Expecting" in str(e):
                logger.warning("JSON appears truncated - attempting repair")
                # Try to complete the JSON by adding closing brackets
                text_fixed = text.rstrip(",\n ")
                # Count opening vs closing brackets
                open_braces = text_fixed.count("{")
                close_braces = text_fixed.count("}")
                open_brackets = text_fixed.count("[")
                close_brackets = text_fixed.count("]")

                # Add missing closing brackets
                if open_braces > close_braces:
                    text_fixed += "}" * (open_braces - close_braces)
                if open_brackets > close_brackets:
                    text_fixed += "]" * (open_brackets - close_brackets)

                try:
                    data = json.loads(text_fixed)
                    logger.info("Successfully repaired truncated JSON")
                    return data
                except json.JSONDecodeError:
                    pass

            # If all strategies fail, raise detailed error
            raise ValueError(
                f"Failed to extract valid JSON from response. "
                f"Error: {e}. "
                f"First 200 chars: {response_text[:200]}"
            )

    def _build_extraction_context(self, client_brief: ClientBrief) -> str:
        """Build context for keyword extraction"""
        lines = []

        lines.append(f"**Company:** {client_brief.company_name}")
        lines.append(f"**Business:** {client_brief.business_description}")
        lines.append(f"**Target Audience:** {client_brief.ideal_customer}")
        lines.append(f"**Main Problem:** {client_brief.main_problem_solved}")

        if client_brief.customer_pain_points:
            lines.append("\n**Pain Points:**")
            for pain in client_brief.customer_pain_points:
                lines.append(f"- {pain}")

        if client_brief.customer_questions:
            lines.append("\n**Customer Questions:**")
            for q in client_brief.customer_questions[:5]:
                lines.append(f"- {q}")

        if client_brief.misconceptions:
            lines.append("\n**Misconceptions to Address:**")
            for m in client_brief.misconceptions[:3]:
                lines.append(f"- {m}")

        return "\n".join(lines)

    def _build_system_prompt(self) -> str:
        """Build system prompt for keyword extraction"""
        return """You are an expert SEO keyword researcher specializing in B2B SaaS and content marketing.

Your task is to extract relevant SEO keywords from client information that will help their social media posts rank better and attract their target audience.

KEYWORD EXTRACTION RULES:

1. PRIMARY KEYWORDS (3-5 total):
   - High-value, specific to the client's core offering
   - Medium-to-high search volume
   - Directly aligned with business value
   - Example: "B2B content marketing" not "marketing"

2. SECONDARY KEYWORDS (8-10 total):
   - Support primary keywords
   - Address specific pain points or solutions
   - Include industry-specific terms
   - Example: "content calendar template", "editorial workflow"

3. LONG-TAIL KEYWORDS (10-12 total):
   - Very specific, lower competition
   - Question-based or conversational
   - Address niche problems
   - Example: "how to scale content without hiring writers"

KEYWORD INTENT CLASSIFICATION:
- informational: How-to, guides, education
- commercial: Product comparisons, evaluations
- transactional: Sign up, buy, get demo
- navigational: Brand/product searches

DIFFICULTY ESTIMATION:
- easy: Low competition, niche topics
- medium: Moderate competition
- hard: High competition, broad terms

OUTPUT FORMAT (strict JSON):
```json
{
  "primary_keywords": [
    {
      "keyword": "keyword phrase",
      "intent": "informational|commercial|transactional|navigational",
      "difficulty": "easy|medium|hard",
      "priority": 1,
      "related_keywords": ["related1", "related2"],
      "notes": "why this keyword matters"
    }
  ],
  "secondary_keywords": [ ... ],
  "longtail_keywords": [ ... ]
}
```

IMPORTANT:
- Return ONLY valid JSON, no markdown formatting
- Be specific and actionable
- Prioritize keywords that match the target audience's search behavior
- Consider LinkedIn and Twitter as primary platforms"""

    def _parse_keyword_strategy(self, data: Dict[str, Any]) -> KeywordStrategy:
        """Parse JSON response into KeywordStrategy"""

        def parse_keyword_list(keywords_data: List[Dict]) -> List[SEOKeyword]:
            """Parse list of keywords"""
            keywords = []
            for kw_data in keywords_data:
                try:
                    keyword = SEOKeyword(
                        keyword=kw_data["keyword"],
                        intent=KeywordIntent(kw_data.get("intent", "informational")),
                        difficulty=KeywordDifficulty(kw_data.get("difficulty", "medium")),
                        priority=kw_data.get("priority", 1),
                        related_keywords=kw_data.get("related_keywords", []),
                        notes=kw_data.get("notes"),
                    )
                    keywords.append(keyword)
                except Exception as e:
                    logger.warning(f"Failed to parse keyword: {e}")
                    continue
            return keywords

        strategy = KeywordStrategy(
            primary_keywords=parse_keyword_list(data.get("primary_keywords", [])),
            secondary_keywords=parse_keyword_list(data.get("secondary_keywords", [])),
            longtail_keywords=parse_keyword_list(data.get("longtail_keywords", [])),
        )

        return strategy
