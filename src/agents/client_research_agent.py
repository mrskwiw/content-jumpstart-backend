"""Client Research Agent: Discovers business info from name + location via web search + Claude."""

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..models.client_brief import ClientBrief
from ..utils.agent_helpers import call_claude_api
from ..utils.anthropic_client import AnthropicClient
from ..utils.logger import logger
from ..utils.web_search import SearchResult, get_search_client

CREDIT_COST = 200

_SYSTEM_PROMPT = """You are a business intelligence analyst. You receive web search snippets about a business and extract structured information.

Rules:
- Extract ONLY information explicitly stated or strongly implied in the provided snippets
- Set fields to null if not found — never hallucinate or invent details
- Confidence scores: 1.0 = explicitly stated, 0.7 = implied by multiple sources, 0.5 = implied by one source, 0.0 = not found
- Return valid JSON only — no commentary, no markdown fences"""


@dataclass
class ClientResearchResult:
    brief: ClientBrief
    confidence: Dict[str, float]
    sources: List[str]
    duration_seconds: float
    stub_mode: bool = False
    warning: Optional[str] = None


class ClientResearchAgent:
    """
    Given a business name + location, runs parallel web searches and synthesizes
    a pre-populated ClientBrief using Claude. Cost: 200 credits. Typical run: 5–15s.
    """

    CREDIT_COST = CREDIT_COST
    MAX_RESULTS_PER_QUERY = 5

    def __init__(self, client: Optional[AnthropicClient] = None):
        self.client = client or AnthropicClient()

    async def run(
        self,
        business_name: str,
        location: str,
        website: Optional[str] = None,
    ) -> ClientResearchResult:
        start = time.time()
        logger.info(f"ClientResearchAgent: researching '{business_name}' in '{location}'")

        snippets, sources, stub_mode = await self._parallel_search(business_name, location, website)

        # Synthesis is a sync Claude API call — run in thread to avoid blocking event loop
        brief, confidence = await asyncio.to_thread(
            self._synthesize, business_name, location, snippets
        )

        warning = None
        if stub_mode:
            warning = (
                "Web search is in stub mode — results are synthetic. "
                "Configure BRAVE_API_KEY or TAVILY_API_KEY for real research."
            )

        duration = round(time.time() - start, 2)
        logger.info(f"ClientResearchAgent: done in {duration}s, stub_mode={stub_mode}")

        return ClientResearchResult(
            brief=brief,
            confidence=confidence,
            sources=list(dict.fromkeys(sources)),  # deduplicate, preserve order
            duration_seconds=duration,
            stub_mode=stub_mode,
            warning=warning,
        )

    async def _parallel_search(
        self,
        business_name: str,
        location: str,
        website: Optional[str],
    ) -> tuple[List[SearchResult], List[str], bool]:
        search_client = get_search_client()
        stub_mode = search_client.provider == "stub"

        queries = [
            f'"{business_name}" {location}',
            f'"{business_name}" about founder CEO owner',
            f'"{business_name}" services products customers',
            f'"{business_name}" reviews testimonials results',
            f'"{business_name}" competitors alternatives {location}',
            f'"{business_name}" site:linkedin.com OR site:instagram.com OR site:facebook.com',
        ]
        if website:
            queries.append(f"site:{website}")

        tasks = [
            asyncio.to_thread(search_client.search, q, self.MAX_RESULTS_PER_QUERY) for q in queries
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        all_snippets: List[SearchResult] = []
        all_sources: List[str] = []
        for resp in responses:
            if isinstance(resp, BaseException):
                logger.warning(f"Search query failed: {resp}")
                continue
            for result in resp.results:
                all_snippets.append(result)
                if result.url:
                    all_sources.append(result.url)

        return all_snippets, all_sources, stub_mode

    def _synthesize(
        self,
        business_name: str,
        location: str,
        snippets: List[SearchResult],
    ) -> tuple[ClientBrief, Dict[str, float]]:
        capped = snippets[:30]
        snippets_text = "\n\n".join(
            f"[{i + 1}] {s.title}\nURL: {s.url}\n{s.snippet}" for i, s in enumerate(capped)
        )

        prompt = f"""Business Name: {business_name}
Location: {location}

Web search results ({len(capped)} snippets):

{snippets_text}

Based ONLY on the above search results, extract structured information about this business.
Set any field to null if not found. Return valid JSON only.

{{
  "brief": {{
    "company_name": "{business_name}",
    "founder_name": null,
    "website": null,
    "business_description": null,
    "industry": null,
    "keywords": [],
    "competitors": [],
    "location": "{location}",
    "ideal_customer": null,
    "main_problem_solved": null,
    "customer_pain_points": [],
    "customer_questions": [],
    "tone_preference": null,
    "brand_personality": [],
    "brand_voice": null,
    "tone_to_avoid": null,
    "key_phrases": [],
    "target_platforms": [],
    "posting_frequency": null,
    "main_cta": null,
    "data_usage": "moderate",
    "measurable_results": null,
    "stories": [],
    "misconceptions": []
  }},
  "confidence": {{
    "founder_name": 0.0,
    "website": 0.0,
    "business_description": 0.0,
    "industry": 0.0,
    "keywords": 0.0,
    "competitors": 0.0,
    "ideal_customer": 0.0,
    "main_problem_solved": 0.0,
    "customer_pain_points": 0.0,
    "tone_preference": 0.0,
    "brand_personality": 0.0,
    "key_phrases": 0.0,
    "target_platforms": 0.0,
    "main_cta": 0.0,
    "measurable_results": 0.0
  }}
}}

Field constraints:
- tone_preference: one of professional/conversational/authoritative/friendly/innovative/educational/approachable/direct/witty/vulnerable/data_driven — or null
- target_platforms: only include platforms with confirmed social links — values: linkedin/twitter/facebook/blog/email/generic
- business_description: 1-3 sentences maximum"""

        result_data = call_claude_api(
            self.client,
            prompt,
            system_prompt=_SYSTEM_PROMPT,
            max_tokens=3000,
            temperature=0.2,
            extract_json=True,
            fallback_on_error={},
        )

        # Strip null/empty values so _convert_to_client_brief uses its own defaults
        # for fields Claude couldn't discover (avoids Pydantic validation errors).
        raw_brief: dict = result_data.get("brief") or {}
        brief_data = {k: v for k, v in raw_brief.items() if v is not None and v != ""}
        confidence: Dict[str, float] = result_data.get("confidence", {})

        # Reuse BriefParserAgent conversion logic (enum coercion, synonym map, etc.)
        from .brief_parser import BriefParserAgent

        parser = BriefParserAgent(client=self.client)
        brief = parser._convert_to_client_brief(brief_data)

        return brief, confidence
