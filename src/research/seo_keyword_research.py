"""SEO Keyword Research Tool - $400 Add-On

Researches and recommends target keywords for content optimization.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import ResearchTool
from .validation_mixin import CommonValidationMixin
from ..models.seo_models import (
    CompetitorKeywords,
    Keyword,
    KeywordCluster,
    KeywordDifficulty,
    KeywordStrategy,
    SearchIntent,
)
from ..utils.logger import logger
from ..validators.research_input_validator import (
    ResearchInputValidator,
)


class SEOKeywordResearcher(ResearchTool, CommonValidationMixin):
    """Automated SEO keyword research and strategy development"""

    def __init__(self, project_id: str, config: Optional[Dict[str, Any]] = None):
        """Initialize SEO keyword researcher with input validator"""
        super().__init__(project_id=project_id, config=config)
        self.validator = ResearchInputValidator(strict_mode=False)

    @property
    def tool_name(self) -> str:
        return "seo_keyword_research"

    @property
    def price(self) -> int:
        return 400

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """
        Validate required inputs with comprehensive security checks (TR-019)

        Security Features:
        - Max length checks (prevent DOS attacks)
        - Prompt injection sanitization
        - Type validation
        - Field presence validation

        Uses CommonValidationMixin for standard validations (Phase 3 deduplication)

        NOTE: main_topics is now OPTIONAL - will auto-generate from business context if not provided
        """
        # Use mixin methods for standard validations
        inputs["business_description"] = self.validate_business_description(inputs)
        inputs["target_audience"] = self.validate_target_audience(inputs)

        # Optional fields via mixin
        inputs["industry"] = self.validate_optional_industry(inputs)
        if "competitors" in inputs and inputs["competitors"]:
            inputs["competitors"] = self.validate_competitor_list(inputs)

        # Tool-specific validation: main topics list (NOW OPTIONAL - auto-generated if missing)
        if "main_topics" in inputs and inputs["main_topics"]:
            inputs["main_topics"] = self.validator.validate_list(
                inputs.get("main_topics"),
                field_name="main_topics",
                min_items=1,
                max_items=10,
                required=False,  # Changed to optional
                item_validator=lambda topic: self.validator.validate_text(
                    topic,
                    field_name="main_topic",
                    min_length=2,
                    max_length=200,
                    required=True,
                    sanitize=True,
                ),
            )
        else:
            # Will auto-generate in run_analysis
            inputs["main_topics"] = None

        # Tool-specific validation: negative keywords (optional)
        if "negative_keywords" in inputs and inputs["negative_keywords"]:
            inputs["negative_keywords"] = self.validator.validate_list(
                inputs.get("negative_keywords"),
                field_name="negative_keywords",
                min_items=1,
                max_items=50,
                required=False,
                item_validator=lambda kw: self.validator.validate_text(
                    kw,
                    field_name="negative_keyword",
                    min_length=2,
                    max_length=200,
                    required=True,
                    sanitize=True,
                ),
            )
        else:
            inputs["negative_keywords"] = None

        # SECURITY: Validate optional location / geographic target (auto-populated from client profile)
        if "location" in inputs and inputs["location"]:
            inputs["location"] = self.validator.validate_text(
                inputs.get("location"),
                field_name="location",
                min_length=2,
                max_length=200,
                required=False,
                sanitize=True,
            )

        return True

    def run_analysis(self, inputs: Dict[str, Any]) -> KeywordStrategy:
        """Execute keyword research analysis"""
        business_desc = inputs["business_description"]
        target_audience = inputs["target_audience"]
        main_topics = inputs.get("main_topics")
        negative_keywords = inputs.get("negative_keywords") or []
        competitors = inputs.get("competitors", [])
        industry = inputs.get("industry") or "Not specified"
        location = inputs.get("location", "")

        if negative_keywords:
            logger.info(
                f"Excluding {len(negative_keywords)} negative keywords: {negative_keywords}"
            )

        # Auto-generate topics if not provided
        if not main_topics:
            # Shortcut: If user provided 5+ keywords, use them directly as topics
            user_keywords = inputs.get("keywords", [])
            if user_keywords and len(user_keywords) >= 5:
                logger.info(
                    f"Using {len(user_keywords)} user-provided keywords as main topics (shortcut)"
                )
                main_topics = user_keywords[:10]  # Use first 10
            else:
                # Auto-generate from business context using AI
                logger.info("Auto-generating main topics from business context")
                main_topics = self._auto_generate_topics(
                    business_description=business_desc,
                    industry=industry,
                    value_proposition=inputs.get("value_proposition"),
                    ideal_customer=inputs.get("ideal_customer"),
                    main_problem_solved=inputs.get("main_problem_solved"),
                    keywords=user_keywords,
                )

        logger.info(f"Researching keywords for {len(main_topics)} topics: {main_topics}")

        # Step 1: Research primary keywords (5-10)
        primary_keywords = self._research_primary_keywords(
            business_desc,
            target_audience,
            main_topics,
            industry,
            location=location,
            negative_keywords=negative_keywords,
        )

        # Step 2: Research secondary/long-tail keywords (20-30)
        secondary_keywords = self._research_secondary_keywords(
            business_desc,
            target_audience,
            main_topics,
            primary_keywords,
            negative_keywords=negative_keywords,
        )

        # Deduplicate: remove any secondary keyword already present in primary list
        primary_kw_set = {kw.keyword.lower().strip() for kw in primary_keywords}
        secondary_keywords = [
            kw for kw in secondary_keywords if kw.keyword.lower().strip() not in primary_kw_set
        ]

        # Step 2.5: Enrich keywords with Google Trends data (if available)
        all_keywords = primary_keywords + secondary_keywords
        self._enrich_with_google_trends(all_keywords)

        # Step 3: Create keyword clusters
        clusters = self._create_keyword_clusters(main_topics, primary_keywords, secondary_keywords)

        # Step 4: Identify quick wins
        quick_wins = self._identify_quick_wins(primary_keywords, secondary_keywords)

        # Step 5: Competitor analysis (if provided)
        competitor_analysis = []
        if competitors:
            competitor_analysis = self._analyze_competitors(
                competitors, business_desc, primary_keywords
            )

        # Step 6: Generate content priorities
        content_priorities = self._generate_content_priorities(
            clusters, quick_wins, competitor_analysis
        )

        # Step 7: Create strategy summary
        strategy_summary = self._create_strategy_summary(
            primary_keywords,
            secondary_keywords,
            clusters,
            quick_wins,
            competitor_analysis,
        )

        # Build complete strategy
        strategy = KeywordStrategy(
            business_name=inputs.get("business_name", "Client"),
            industry=industry,
            target_audience=target_audience,
            primary_keywords=primary_keywords,
            secondary_keywords=secondary_keywords,
            keyword_clusters=clusters,
            competitor_analysis=competitor_analysis,
            quick_win_keywords=quick_wins,
            content_priorities=content_priorities,
            negative_keywords=negative_keywords,
            strategy_summary=strategy_summary,
        )

        return strategy

    def _auto_generate_topics(
        self,
        business_description: str,
        industry: Optional[str] = None,
        value_proposition: Optional[str] = None,
        ideal_customer: Optional[str] = None,
        main_problem_solved: Optional[str] = None,
        keywords: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Auto-generate 3-5 main topics from business context using AI.

        This makes the tool fully automatic - no user input required!
        Leverages all available client data for intelligent topic extraction.

        Args:
            business_description: The company's business description
            industry: Optional industry context
            value_proposition: Optional value prop (legacy - usually not provided)
            ideal_customer: Optional target customer description
            main_problem_solved: Optional problem/pain point the business solves
            keywords: Optional existing keywords to use as inspiration

        Returns:
            List of 3-5 main topic keywords
        """
        from ..utils.anthropic_client import get_default_client

        logger.info("Auto-generating topics from business context")

        # Build context for topic extraction from ALL available sources
        context_parts = [f"Business: {business_description}"]

        if industry:
            context_parts.append(f"Industry: {industry}")

        if value_proposition:
            context_parts.append(f"Value Proposition: {value_proposition}")

        if ideal_customer:
            context_parts.append(f"Target Customer: {ideal_customer}")

        if main_problem_solved:
            context_parts.append(f"Problem Solved: {main_problem_solved}")

        if keywords and len(keywords) > 0:
            # Include existing keywords as inspiration (limit to 5 to avoid token bloat)
            context_parts.append(f"Existing Keywords: {', '.join(keywords[:5])}")

        context = "\n".join(context_parts)

        prompt = f"""Based on this business context, extract 3-5 main topic keywords that best represent what this company does and what their target audience would search for.

{context}

IMPORTANT:
- Return ONLY the topics, one per line
- Each topic should be 1-4 words
- Focus on what customers search for, not internal jargon
- Include industry-specific terms
- Prioritize topics with search volume potential
- If keywords are provided, use them as inspiration but create search-friendly variations

Example output format:
AI automation
content marketing
SEO strategy

Your topics:"""

        try:
            client = get_default_client()
            response = client.create_message(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.3,  # Lower temp for focused extraction
            )

            # Parse response - create_message returns string directly
            topics_text = response.strip()
            topics = [
                topic.strip()
                for topic in topics_text.split("\n")
                if topic.strip() and len(topic.strip()) > 2
            ]

            # Limit to 5 topics
            topics = topics[:5]

            # Ensure we have at least 3 topics
            if len(topics) < 3:
                # Fallback: extract key terms from business description
                logger.warning(f"AI generated only {len(topics)} topics, using fallback")
                topics = self._fallback_topic_extraction(
                    business_description, industry, ideal_customer, main_problem_solved
                )

            logger.info(f"Auto-generated {len(topics)} topics: {topics}")
            return topics

        except Exception as e:
            logger.error(f"Error auto-generating topics: {e}")
            # Fallback to simple extraction
            return self._fallback_topic_extraction(
                business_description, industry, ideal_customer, main_problem_solved
            )

    def _fallback_topic_extraction(
        self,
        business_description: str,
        industry: Optional[str] = None,
        ideal_customer: Optional[str] = None,
        main_problem_solved: Optional[str] = None,
    ) -> List[str]:
        """
        Fallback method to extract topics if AI generation fails.

        Uses simple keyword extraction from business description and other fields.
        """
        # Simple approach: use industry + key terms from description
        topics = []

        if industry and industry != "Not specified":
            topics.append(industry.lower())

        # Extract potential topics from all available text fields
        # Combine all text sources for keyword matching
        combined_text = business_description.lower()
        if ideal_customer:
            combined_text += " " + ideal_customer.lower()
        if main_problem_solved:
            combined_text += " " + main_problem_solved.lower()

        # Common business/tech keywords that make good topics
        good_keywords = [
            "marketing",
            "content",
            "seo",
            "automation",
            "ai",
            "saas",
            "analytics",
            "strategy",
            "social media",
            "email",
            "advertising",
            "branding",
            "sales",
            "crm",
            "data",
            "growth",
            "software",
            "platform",
            "tools",
            "services",
            "consulting",
            "agency",
        ]

        for keyword in good_keywords:
            if keyword in combined_text and keyword not in topics:
                topics.append(keyword)
                if len(topics) >= 5:
                    break

        # Ensure at least 3 topics
        if len(topics) < 3:
            topics.extend(["marketing", "strategy", "growth"][: 3 - len(topics)])

        return topics[:5]

    def _research_primary_keywords(
        self,
        business_desc: str,
        target_audience: str,
        main_topics: List[str],
        industry: str,
        location: str = "",
        negative_keywords: Optional[List[str]] = None,
    ) -> List[Keyword]:
        """
        Research primary target keywords with iterative deep dive (5-10 high-quality keywords)

        Enhancement: Uses multiple search strategies and quality scoring to ensure
        we always find at least 5 high-quality keywords (score >= 70).

        Iteration strategies:
        1. Broad topic keywords (initial attempt)
        2. Industry-specific terms (if insufficient quality)
        3. Long-tail variations (if still insufficient)
        4. Question-based keywords (final attempt)

        Max iterations: 3
        """
        from ..utils.keyword_quality_scorer import KeywordQualityScorer

        # Initialize quality scorer
        scorer = KeywordQualityScorer(business_desc, industry)

        all_keywords: List[Keyword] = []
        high_quality_keywords: List[Keyword] = []
        iteration = 0
        max_iterations = 3

        # Search strategies to try
        strategies = [
            {
                "name": "broad_topics",
                "description": "Broad topic-based keywords",
                "focus": "broad business topics and general industry terms",
            },
            {
                "name": "industry_specific",
                "description": "Industry-specific keywords",
                "focus": "industry-specific terminology and niche terms",
            },
            {
                "name": "long_tail",
                "description": "Long-tail variations",
                "focus": "specific long-tail keyword phrases (3+ words)",
            },
            {
                "name": "question_based",
                "description": "Question-based keywords",
                "focus": "question-based searches (how to, what is, etc.)",
            },
        ]

        while len(high_quality_keywords) < 5 and iteration < max_iterations:
            iteration += 1
            strategy = strategies[min(iteration - 1, len(strategies) - 1)]

            logger.info(
                f"Iteration {iteration}/{max_iterations}: "
                f"Trying {strategy['name']} strategy "
                f"(current high-quality count: {len(high_quality_keywords)})"
            )

            # Build prompt for this strategy
            prompt = self._build_keyword_research_prompt(
                business_desc,
                target_audience,
                main_topics,
                industry,
                strategy["focus"],
                iteration,
                location=location,
                negative_keywords=negative_keywords,
            )

            try:
                # Call Claude API
                keywords_data = self._call_claude_api(
                    prompt,
                    max_tokens=2000,
                    temperature=0.4,
                    extract_json=True,
                    fallback_on_error=[],
                )

                if not keywords_data:
                    logger.warning(f"No keywords returned for {strategy['name']} strategy")
                    continue

                # Parse keywords
                iteration_keywords = []
                for kw_data in keywords_data[:10]:
                    # Skip if kw_data is not a dict
                    if not isinstance(kw_data, dict):
                        logger.warning(
                            f"Skipping invalid keyword entry (expected dict, got {type(kw_data)}): {kw_data}"
                        )
                        continue

                    keyword = Keyword(
                        keyword=kw_data["keyword"],
                        search_intent=SearchIntent(kw_data["search_intent"]),
                        difficulty=KeywordDifficulty(kw_data["difficulty"]),
                        monthly_volume_estimate=kw_data["monthly_volume_estimate"],
                        relevance_score=float(kw_data["relevance_score"]),
                        long_tail=kw_data.get("long_tail", False),
                        question_based=kw_data.get("question_based", False),
                        related_topics=kw_data.get("related_topics", []),
                    )
                    iteration_keywords.append(keyword)

                # Post-filter: exclude keywords matching negative keywords
                if negative_keywords:
                    iteration_keywords = [
                        kw
                        for kw in iteration_keywords
                        if not any(neg.lower() in kw.keyword.lower() for neg in negative_keywords)
                    ]

                # Score keywords and filter high-quality ones
                high_quality_batch = scorer.filter_high_quality(iteration_keywords, min_score=70.0)

                # Add to results (avoid duplicates)
                for kw in high_quality_batch:
                    if kw.keyword not in [k.keyword for k in high_quality_keywords]:
                        high_quality_keywords.append(kw)

                # Also keep all keywords for potential secondary use
                all_keywords.extend(iteration_keywords)

                logger.info(
                    f"Iteration {iteration}: Found {len(high_quality_batch)} high-quality keywords "
                    f"(total now: {len(high_quality_keywords)})"
                )

                # If we have enough high-quality keywords, we can stop
                if len(high_quality_keywords) >= 5:
                    logger.info(
                        f"✓ Target achieved! Found {len(high_quality_keywords)} high-quality keywords"
                    )
                    break

            except Exception as e:
                logger.warning(f"Error in iteration {iteration} ({strategy['name']}): {e}")
                continue

        # If still insufficient after all iterations, use fallback
        if len(high_quality_keywords) < 5:
            logger.warning(
                f"After {iteration} iterations, only found {len(high_quality_keywords)} "
                f"high-quality keywords. Using fallback + best available."
            )

            # Get best keywords from all attempts
            all_keywords_scored = scorer.filter_high_quality(all_keywords, min_score=50.0)
            high_quality_keywords.extend(all_keywords_scored[: 5 - len(high_quality_keywords)])

            # If still not enough, use fallback
            if len(high_quality_keywords) < 5:
                fallback = self._generate_fallback_primary_keywords(
                    main_topics, negative_keywords=negative_keywords
                )
                high_quality_keywords.extend(fallback[: 5 - len(high_quality_keywords)])

        # Return top 10 high-quality keywords (sorted by quality score)
        final_keywords = sorted(
            high_quality_keywords, key=lambda k: k.quality_score or 0, reverse=True
        )[:10]

        # Log quality stats
        stats = scorer.get_keyword_stats(final_keywords)
        logger.info(
            f"Final keyword set: {stats['high_quality_count']} high-quality "
            f"(avg score: {stats['avg_quality']})"
        )

        return final_keywords

    def _build_keyword_research_prompt(
        self,
        business_desc: str,
        target_audience: str,
        main_topics: List[str],
        industry: str,
        focus: str,
        iteration: int,
        location: str = "",
        negative_keywords: Optional[List[str]] = None,
    ) -> str:
        """
        Build prompt for keyword research with specific focus

        Args:
            business_desc: Business description
            target_audience: Target audience
            main_topics: Main topics to focus on
            industry: Industry context
            focus: Strategy focus (e.g., "broad topics", "industry-specific")
            iteration: Current iteration number

        Returns:
            Formatted prompt string
        """
        location_line = f"\nGeographic Market: {location}" if location else ""
        negative_keywords_section = ""
        if negative_keywords:
            negative_keywords_section = f"\nKEYWORDS TO AVOID (do NOT suggest these or close variations):\n{', '.join(negative_keywords)}\nReason: Client has explicitly excluded these from their strategy."

        prompt = f"""Analyze this business and recommend 5-10 PRIMARY target keywords for SEO.

CRITICAL: Extract ALL fields for EVERY keyword. Do not leave any fields empty or use placeholder values.

Business: {business_desc}

Target Audience: {target_audience}

Industry: {industry}{location_line}

Main Topics: {', '.join(main_topics)}{negative_keywords_section}

**SEARCH STRATEGY (Iteration {iteration}):** Focus on {focus}

EXAMPLE INPUT/OUTPUT:

Input: "AI-powered project management tool for software teams"
Output:
[
  {{
    "keyword": "ai project management software",
    "search_intent": "commercial",
    "difficulty": "medium",
    "monthly_volume_estimate": "5K-10K",
    "relevance_score": 9.5,
    "long_tail": true,
    "question_based": false,
    "related_topics": ["agile project management", "team collaboration", "sprint planning"]
  }},
  {{
    "keyword": "how to manage software projects with ai",
    "search_intent": "informational",
    "difficulty": "low",
    "monthly_volume_estimate": "1K-5K",
    "relevance_score": 8.5,
    "long_tail": true,
    "question_based": true,
    "related_topics": ["project automation", "ai productivity tools"]
  }}
]

EXTRACTION RULES (FILL ALL FIELDS):

1. **keyword**: The exact keyword phrase (2-5 words typically)
   - Make it specific to the business and industry
   - Avoid overly generic terms ("marketing", "software")
   - Include variations based on search strategy focus

2. **search_intent**: MUST be one of: "informational", "navigational", "commercial", "transactional"
   - informational: How-to, guides, explanations
   - navigational: Brand/product searches
   - commercial: Comparison, reviews, "best X"
   - transactional: Buy, pricing, signup

3. **difficulty**: MUST be "low", "medium", or "high"
   - low: New sites can rank (long-tail, niche)
   - medium: Established sites needed (moderate competition)
   - high: Very competitive (major brands dominate)

4. **monthly_volume_estimate**: Realistic search volume range
   - Examples: "100-1K", "1K-5K", "5K-10K", "10K-50K"
   - Base on keyword specificity (long-tail = lower volume)
   - NEVER use "Unknown" - estimate based on context

5. **relevance_score**: Number from 1-10 (decimals allowed)
   - 9-10: Perfect match for business
   - 7-8: Highly relevant
   - 5-6: Moderately relevant
   - Below 5: Not recommended (don't include)

6. **long_tail**: true if 3+ words, false otherwise

7. **question_based**: true if starts with how/what/why/when/where/who

8. **related_topics**: Array of 2-5 related topic strings
   - Topics that this keyword connects to
   - Other relevant searches users might make

QUALITY CRITERIA:
- Relevance score MUST be 8+ (highly relevant to business)
- Mix search intents (not all informational)
- Prefer medium difficulty over high (realistic to rank)
- Estimate realistic search volumes (consider specificity)
- Include variety: some question-based, some long-tail, some short

IMPORTANT:
- Return 5-10 keywords minimum
- Fill ALL 8 fields for EVERY keyword
- Return ONLY valid JSON array (no markdown, no code blocks)
- Ensure variety in search intent and difficulty

Your JSON array:"""

        return prompt

    def _research_secondary_keywords(
        self,
        business_desc: str,
        target_audience: str,
        main_topics: List[str],
        primary_keywords: List[Keyword],
        negative_keywords: Optional[List[str]] = None,
    ) -> List[Keyword]:
        """Research secondary/long-tail keywords (20-30)"""
        primary_kw_list = [kw.keyword for kw in primary_keywords]

        negative_keywords_section = ""
        if negative_keywords:
            negative_keywords_section = f"\nKEYWORDS TO AVOID (do NOT suggest these or close variations):\n{', '.join(negative_keywords)}\nReason: Client has explicitly excluded these from their strategy."

        prompt = f"""Generate 20-30 SECONDARY/LONG-TAIL keywords based on these primary keywords.

CRITICAL: Generate 20-30 keywords minimum. Fill ALL 8 fields for EVERY keyword.

Business: {business_desc}

Target Audience: {target_audience}

Primary Keywords: {', '.join(primary_kw_list)}

Main Topics: {', '.join(main_topics)}{negative_keywords_section}

EXAMPLE SECONDARY KEYWORDS:

For primary: "ai project management software"
Secondary keywords:
[
  {{
    "keyword": "best ai project management tools for developers",
    "search_intent": "commercial",
    "difficulty": "low",
    "monthly_volume_estimate": "500-1K",
    "relevance_score": 8.5,
    "long_tail": true,
    "question_based": false,
    "related_topics": ["developer tools", "agile software", "team collaboration"]
  }},
  {{
    "keyword": "how does ai improve project management efficiency",
    "search_intent": "informational",
    "difficulty": "low",
    "monthly_volume_estimate": "100-500",
    "relevance_score": 7.5,
    "long_tail": true,
    "question_based": true,
    "related_topics": ["project automation", "ai productivity", "workflow optimization"]
  }},
  {{
    "keyword": "ai project tracking software for remote teams",
    "search_intent": "commercial",
    "difficulty": "medium",
    "monthly_volume_estimate": "1K-5K",
    "relevance_score": 9.0,
    "long_tail": true,
    "question_based": false,
    "related_topics": ["remote work tools", "distributed teams", "project visibility"]
  }}
]

SECONDARY KEYWORD RULES:

1. **Create Long-Tail Variations (3+ words)**
   - Expand primary keywords with modifiers
   - Add qualifiers: "best", "top", "affordable", "for [audience]"
   - Include use cases: "for small business", "for agencies", "for teams"

2. **Include Question-Based Keywords**
   - How to: "how to [action]", "how does [feature] work"
   - What is: "what is [concept]", "what are [features]"
   - Why: "why use [product]", "why choose [solution]"
   - When: "when to use [tool]", "when is [timing]"

3. **Focus on Lower Difficulty**
   - Target: 70% low difficulty, 30% medium difficulty
   - Long-tail = lower competition = easier to rank

4. **Mix Search Intents**
   - 50% informational (how-to, guides, explanations)
   - 40% commercial (comparisons, reviews, "best X")
   - 10% transactional (pricing, signup, buy)

5. **Support Primary Keywords**
   - Each secondary should relate to 1-2 primary keywords
   - Include primary keywords in related_topics
   - Create natural progression from awareness to decision

FIELD REQUIREMENTS (SAME AS PRIMARY):
- keyword: 3-7 words (long-tail)
- search_intent: informational/navigational/commercial/transactional
- difficulty: low/medium (NO high difficulty for secondary)
- monthly_volume_estimate: "100-500", "500-1K", "1K-5K" (lower volumes expected)
- relevance_score: 7-10 (minimum 7)
- long_tail: MUST be true (secondary = long-tail)
- question_based: true for question keywords
- related_topics: 2-5 topics

TARGET: Generate 20-30 keywords
MINIMUM: 20 keywords (fill all 20 if possible)

Return ONLY valid JSON array (no markdown, no code blocks):"""

        try:
            # Call Claude API with automatic JSON extraction (Phase 3 deduplication)
            # Bug #171: 3000 tokens is too small for 20-30 keyword objects
            # (each ~400 chars); responses are truncated mid-array, breaking
            # JSON extraction and triggering the fallback.
            keywords_data = self._call_claude_api(
                prompt,
                max_tokens=6000,
                temperature=0.5,
                extract_json=True,
                fallback_on_error=[],
            )

            if not keywords_data:
                logger.warning("Claude returned empty data for secondary keywords")
                return self._generate_fallback_secondary_keywords(
                    primary_keywords, negative_keywords=negative_keywords
                )

            # Normalize response format
            if isinstance(keywords_data, dict):
                # Unwrap if Claude returned {"keywords": [...]} instead of bare array
                keywords_data = next((v for v in keywords_data.values() if isinstance(v, list)), [])
            elif not isinstance(keywords_data, list):
                # If it's neither dict nor list, something went wrong
                logger.warning(f"Unexpected keywords_data type: {type(keywords_data)}")
                return self._generate_fallback_secondary_keywords(
                    primary_keywords, negative_keywords=negative_keywords
                )

            keywords = []

            for kw_data in keywords_data[:30]:  # Max 30 secondary
                # Claude sometimes returns plain strings instead of keyword objects.
                # Wrap them as minimal dicts rather than dropping them entirely.
                if isinstance(kw_data, str):
                    kw_data = {"keyword": kw_data}
                elif not isinstance(kw_data, dict):
                    logger.warning(
                        f"Skipping invalid keyword entry (expected dict, got {type(kw_data)}): {kw_data}"
                    )
                    continue

                keyword = Keyword(
                    keyword=kw_data["keyword"],
                    search_intent=SearchIntent(kw_data.get("search_intent", "informational")),
                    difficulty=KeywordDifficulty(kw_data.get("difficulty", "medium")),
                    monthly_volume_estimate=kw_data.get("monthly_volume_estimate", "unknown"),
                    relevance_score=float(kw_data.get("relevance_score", 5.0)),
                    long_tail=kw_data.get("long_tail", True),
                    question_based=kw_data.get("question_based", False),
                    related_topics=kw_data.get("related_topics", []),
                )
                keywords.append(keyword)

            # Post-filter: exclude keywords matching negative keywords
            if negative_keywords:
                keywords = [
                    kw
                    for kw in keywords
                    if not any(neg.lower() in kw.keyword.lower() for neg in negative_keywords)
                ]

            logger.info(f"Identified {len(keywords)} secondary keywords")
            return keywords

        except Exception as e:
            logger.error(f"Failed to research secondary keywords: {e}")
            return self._generate_fallback_secondary_keywords(
                primary_keywords, negative_keywords=negative_keywords
            )

    def _enrich_with_google_trends(self, keywords: List[Keyword]) -> None:
        """
        Enrich keywords with Google Trends data (in-place modification).

        Fetches trend data one keyword at a time with randomised inter-request
        delays to stay under Google's scraper detector.  Batching 5 keywords
        per request produces a traffic burst that triggers 429s immediately on
        cloud IPs; sequential single-keyword requests with jittered delays look
        much more like organic browsing.

        Updates per keyword:
        - trend_score: Average interest score (0-100)
        - trend_direction: rising/stable/declining/seasonal
        - seasonal: Boolean indicating seasonal variation
        - related_queries: Top related queries from Google Trends

        Args:
            keywords: List of Keyword objects to enrich (modified in-place)
        """
        try:
            import random
            import statistics
            import time

            from pytrends.request import TrendReq

            try:
                pytrends = TrendReq(
                    hl="en-US",
                    tz=360,
                    timeout=(10, 25),
                    retries=2,
                    backoff_factor=0.5,
                )
            except TypeError:
                pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))

            # Cap at 10 keywords — beyond that the marginal value doesn't justify
            # the extra request volume and latency.
            targets = keywords[: min(len(keywords), 10)]
            logger.info(f"Enriching {len(targets)} keywords with Google Trends data")

            MAX_RETRIES = 3
            consecutive_failures = 0

            for idx, keyword_obj in enumerate(targets):
                # Randomised inter-request delay: 2–5 s for the first request,
                # 3–7 s after the first to let the previous response settle.
                if idx > 0:
                    time.sleep(random.uniform(3.0, 7.0))  # nosec B311 — timing jitter, not crypto

                keyword_term = keyword_obj.keyword

                for attempt in range(MAX_RETRIES):
                    try:
                        if attempt > 0:
                            # Jittered backoff: 25–45 s on attempt 2, 50–90 s on attempt 3
                            base = 35 * attempt
                            time.sleep(random.uniform(base * 0.7, base * 1.3))  # nosec B311

                        pytrends.build_payload(
                            [keyword_term],
                            timeframe="today 12-m",
                            geo="",
                        )
                        interest_df = pytrends.interest_over_time()

                        if not interest_df.empty:
                            if "isPartial" in interest_df.columns:
                                interest_df = interest_df.drop("isPartial", axis=1)

                            if keyword_term in interest_df.columns:
                                values = interest_df[keyword_term].tolist()
                                if values:
                                    mean_score = float(statistics.mean(values[-4:]))
                                    keyword_obj.trend_score = mean_score
                                    keyword_obj.trend_momentum_score = mean_score
                                    if len(values) >= 8:
                                        recent_avg = statistics.mean(values[-4:])
                                        older_avg = statistics.mean(values[-8:-4])
                                        variance = (
                                            statistics.stdev(values) if len(values) > 1 else 0
                                        )
                                        keyword_obj.seasonal = variance > 25
                                        if keyword_obj.seasonal:
                                            keyword_obj.trend_direction = "seasonal"
                                        elif recent_avg > older_avg * 1.2:
                                            keyword_obj.trend_direction = "rising"
                                        elif recent_avg < older_avg * 0.8:
                                            keyword_obj.trend_direction = "declining"
                                        else:
                                            keyword_obj.trend_direction = "stable"
                                    else:
                                        keyword_obj.trend_direction = "stable"

                        # Related queries — extra request, so add a short delay first
                        try:
                            time.sleep(random.uniform(1.0, 2.5))  # nosec B311
                            related_queries = pytrends.related_queries()
                            if (
                                keyword_term in related_queries
                                and related_queries[keyword_term]["top"] is not None
                            ):
                                top_queries = related_queries[keyword_term]["top"]
                                if not top_queries.empty:
                                    keyword_obj.related_queries = (
                                        top_queries["query"].head(5).tolist()
                                    )
                        except Exception as rq_err:
                            # Re-raise 429s so the outer handler increments
                            # consecutive_failures and can trigger early exit.
                            # Swallow everything else — related queries are optional.
                            if "429" in str(rq_err) or "too many" in str(rq_err).lower():
                                raise
                            logger.debug(
                                f"Could not fetch related queries for '{keyword_term}': {rq_err}"
                            )

                        consecutive_failures = 0
                        break  # success

                    except Exception as e:
                        is_rate_limit = "429" in str(e) or "too many" in str(e).lower()
                        if is_rate_limit:
                            # Retries never recover a 429 within a single run — Google's
                            # rate-limit window far exceeds the backoff budget. Try
                            # DataForSEO as a fallback before giving up.
                            if self._try_dataforseo_fallback(keyword_term, keyword_obj):
                                consecutive_failures = 0
                                break  # DataForSEO succeeded — treat as success
                            logger.warning(
                                f"Trends 429 for '{keyword_term}' — skipping (IP rate-limited, no fallback)"
                            )
                            consecutive_failures += 1
                            break
                        else:
                            logger.warning(
                                f"Trends failed for '{keyword_term}' after {attempt + 1} attempt(s): {e}"
                            )
                            consecutive_failures += 1
                            break

                # If 3 keywords in a row have failed we're likely fully blocked —
                # stop early rather than burning time on guaranteed failures.
                if consecutive_failures >= 3:
                    logger.warning(
                        "3 consecutive Trends failures — stopping enrichment early "
                        "(IP likely blocked; remaining keywords will have no trend data)"
                    )
                    break

            enriched_count = sum(1 for kw in keywords if kw.trend_score is not None)
            logger.info(
                f"Successfully enriched {enriched_count}/{len(targets)} keywords with Google Trends data"
            )

        except ImportError:
            logger.warning("pytrends not installed - skipping Google Trends enrichment")
        except Exception as e:
            logger.error(f"Error during Google Trends enrichment: {e}")
            # Continue without trends data - not critical to fail the entire analysis

    def _try_dataforseo_fallback(self, keyword_term: str, keyword_obj: "Keyword") -> bool:
        """Attempt to enrich keyword_obj via DataForSEO when pytrends is rate-limited.

        Returns True if DataForSEO returned usable data and keyword_obj was updated.
        Returns False if DataForSEO is not configured, failed, or returned no data.
        """
        try:
            from ..utils.dataforseo_client import DataForSEOClient

            client = DataForSEOClient()
            if not client.configured:
                return False

            result = client.get_trends(keyword_term)
            if not result:
                return False

            keyword_obj.trend_score = result["trend_score"]
            keyword_obj.trend_direction = result["trend_direction"]
            keyword_obj.trend_momentum_score = result["trend_momentum_score"]
            keyword_obj.seasonal = result["trend_direction"] == "seasonal"
            logger.info(
                f"DataForSEO fallback succeeded for '{keyword_term}': "
                f"score={result['trend_score']:.1f}, direction={result['trend_direction']}"
            )
            return True

        except Exception as exc:
            logger.warning(f"DataForSEO fallback error for '{keyword_term}': {exc}")
            return False

    def _create_keyword_clusters(
        self,
        main_topics: List[str],
        primary_keywords: List[Keyword],
        secondary_keywords: List[Keyword],
    ) -> List[KeywordCluster]:
        """Group keywords into thematic clusters"""
        clusters = []
        all_keywords = primary_keywords + secondary_keywords

        # Create one cluster per main topic
        for topic in main_topics:
            # Find keywords related to this topic
            topic_keywords = [
                kw
                for kw in all_keywords
                if topic.lower() in kw.keyword.lower()
                or any(topic.lower() in t.lower() for t in kw.related_topics)
            ]

            if not topic_keywords:
                continue

            # Pick primary keyword (highest relevance)
            primary_kw = max(topic_keywords, key=lambda k: k.relevance_score)
            secondary_kws = [kw.keyword for kw in topic_keywords if kw != primary_kw][:10]

            # Determine priority based on keyword difficulty and relevance
            avg_difficulty = sum(
                (
                    1
                    if kw.difficulty == KeywordDifficulty.LOW
                    else 2 if kw.difficulty == KeywordDifficulty.MEDIUM else 3
                )
                for kw in topic_keywords
            ) / len(topic_keywords)
            avg_relevance = sum(kw.relevance_score for kw in topic_keywords) / len(topic_keywords)

            if avg_relevance >= 8 and avg_difficulty <= 2:
                priority = "High"
            elif avg_relevance >= 6:
                priority = "Medium"
            else:
                priority = "Low"

            # Generate content suggestions
            content_suggestions = [
                f"Ultimate guide to {primary_kw.keyword}",
                f"How to {primary_kw.keyword} (step-by-step)",
                f"{primary_kw.keyword}: Best practices and tips",
            ]

            cluster = KeywordCluster(
                theme=topic,
                primary_keyword=primary_kw.keyword,
                secondary_keywords=secondary_kws,
                content_suggestions=content_suggestions,
                priority=priority,
            )
            clusters.append(cluster)

        logger.info(f"Created {len(clusters)} keyword clusters")
        return clusters

    def _identify_quick_wins(
        self, primary_keywords: List[Keyword], secondary_keywords: List[Keyword]
    ) -> List[str]:
        """Identify low-difficulty, high-relevance keywords"""
        all_keywords = primary_keywords + secondary_keywords

        quick_wins = [
            kw.keyword
            for kw in all_keywords
            if kw.difficulty == KeywordDifficulty.LOW and kw.relevance_score >= 7.0
        ]

        # If not enough low difficulty, include medium difficulty with high relevance
        if len(quick_wins) < 5:
            medium_wins = [
                kw.keyword
                for kw in all_keywords
                if kw.difficulty == KeywordDifficulty.MEDIUM and kw.relevance_score >= 8.5
            ]
            quick_wins.extend(medium_wins[: 5 - len(quick_wins)])

        logger.info(f"Identified {len(quick_wins)} quick-win keywords")
        return quick_wins[:10]  # Max 10

    def _analyze_competitors(
        self,
        competitors: List[str],
        business_desc: str,
        primary_keywords: List[Keyword],
    ) -> List[CompetitorKeywords]:
        """Analyze competitor keyword strategies"""
        primary_kw_list = [kw.keyword for kw in primary_keywords]

        competitor_analysis = []

        for competitor in competitors[:3]:  # Max 3 competitors
            prompt = f"""Analyze this competitor's likely keyword strategy.

Competitor: {competitor}

Our Business: {business_desc}

Our Target Keywords: {', '.join(primary_kw_list)}

Estimate:
1. What 10-15 keywords are they likely targeting?
2. What keyword gaps exist (keywords we could target that they don't)?
3. What overlaps exist (keywords both of us target)?

Return as JSON with keys:
estimated_keywords (list), gaps (list), overlaps (list)"""

            try:
                # Call Claude API with automatic JSON extraction (Phase 3 deduplication)
                data = self._call_claude_api(
                    prompt,
                    max_tokens=1500,
                    temperature=0.4,
                    extract_json=True,
                    fallback_on_error={},
                )

                if not data:
                    logger.warning(f"Claude returned empty data for competitor {competitor}")
                    continue

                analysis = CompetitorKeywords(
                    competitor_name=competitor,
                    estimated_keywords=data.get("estimated_keywords", [])[:15],
                    gaps=data.get("gaps", [])[:10],
                    overlaps=data.get("overlaps", [])[:10],
                )
                competitor_analysis.append(analysis)

            except Exception as e:
                logger.warning(f"Failed to analyze competitor {competitor}: {e}")
                continue

        logger.info(f"Analyzed {len(competitor_analysis)} competitors")
        return competitor_analysis

    def _generate_content_priorities(
        self,
        clusters: List[KeywordCluster],
        quick_wins: List[str],
        competitor_analysis: List[CompetitorKeywords],
    ) -> List[str]:
        """Generate top 5 content pieces to create"""
        priorities = []

        # Priority 1-2: High-priority clusters
        high_priority_clusters = [c for c in clusters if c.priority == "High"]
        for cluster in high_priority_clusters[:2]:
            priorities.append(
                f"[HIGH] {cluster.content_suggestions[0]} (targets: {cluster.primary_keyword})"
            )

        # Priority 3-4: Quick win keywords
        for kw in quick_wins[:2]:
            priorities.append(f"[QUICK WIN] How-to guide for '{kw}'")

        # Priority 5: Gap opportunity from competitors (if available)
        if competitor_analysis:
            gaps = []
            for comp in competitor_analysis:
                gaps.extend(comp.gaps)
            if gaps:
                priorities.append(f"[GAP] Compete on '{gaps[0]}' (competitor weakness)")

        # Fill to 5 with medium priority clusters
        if len(priorities) < 5:
            medium_clusters = [c for c in clusters if c.priority == "Medium"]
            for cluster in medium_clusters[: 5 - len(priorities)]:
                priorities.append(
                    f"[MEDIUM] {cluster.content_suggestions[0]} (targets: {cluster.primary_keyword})"
                )

        return priorities[:5]

    def _create_strategy_summary(
        self,
        primary_keywords: List[Keyword],
        secondary_keywords: List[Keyword],
        clusters: List[KeywordCluster],
        quick_wins: List[str],
        competitor_analysis: List[CompetitorKeywords],
    ) -> str:
        """Generate executive summary of keyword strategy"""
        # Count intent distribution
        intent_counts: Dict[str, int] = {}
        for kw in primary_keywords:
            intent_counts[kw.search_intent.value] = intent_counts.get(kw.search_intent.value, 0) + 1

        # Count difficulty distribution — primary keywords only (matches the visible table)
        difficulty_counts: Dict[str, int] = {}
        for kw in primary_keywords:
            difficulty_counts[kw.difficulty.value] = (
                difficulty_counts.get(kw.difficulty.value, 0) + 1
            )

        # Find dominant intent for summary
        dominant_intent = (
            max(intent_counts, key=lambda k: intent_counts.get(k, 0))
            if intent_counts
            else "informational"
        )
        dominant_intent_count = intent_counts.get(dominant_intent, 0)
        intent_description = (
            "awareness and education"
            if dominant_intent == "informational"
            else "conversion and sales"
        )

        # Calculate average quality score if available
        quality_scores = [
            kw.quality_score for kw in primary_keywords if kw.quality_score is not None
        ]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
        high_quality_count = sum(1 for score in quality_scores if score >= 70)

        quality_summary = ""
        if avg_quality is not None:
            quality_summary = f"\n\n**Quality Assurance:** {high_quality_count}/{len(primary_keywords)} primary keywords rated high-quality (score ≥70). Average quality score: {avg_quality:.1f}/100. All keywords vetted through iterative deep-dive research process."

        # Bug #166: "0 thematic clusters" is confusing when cluster build fails.
        # Use a fallback phrase rather than printing a literal zero.
        cluster_str = (
            f"organized into {len(clusters)} thematic clusters"
            if clusters
            else "with supporting long-tail variations"
        )
        summary = f"""This keyword strategy identifies {len(primary_keywords)} primary keywords and {len(secondary_keywords)} secondary/long-tail keywords {cluster_str}.
{quality_summary}

**Search Intent Focus:** {dominant_intent.title()} intent dominates with {dominant_intent_count} primary keywords, supporting {intent_description}.

**Difficulty Balance:** {difficulty_counts.get('low', 0)} low-difficulty keywords offer quick wins, {difficulty_counts.get('medium', 0)} medium-difficulty keywords provide sustainable growth, and {difficulty_counts.get('high', 0)} high-difficulty keywords represent long-term authority plays.

**Quick Wins:** {len(quick_wins)} keywords identified as immediate opportunities due to low competition and high relevance.

{"**Competitive Positioning:** " + str(len(competitor_analysis)) + " competitors analyzed, revealing " + str(sum(len(c.gaps) for c in competitor_analysis)) + " gap opportunities where we can compete effectively." if competitor_analysis else ""}

**Recommended Approach:** Start with quick-win keywords to build authority, then systematically target medium-difficulty keywords in high-priority clusters."""

        return summary

    def _generate_fallback_primary_keywords(
        self, main_topics: List[str], negative_keywords: Optional[List[str]] = None
    ) -> List[Keyword]:
        """Generate basic keywords if API fails, filtering out negative keywords"""
        negative_keywords = negative_keywords or []
        keywords = []
        for topic in main_topics[:5]:
            # Filter: skip if topic matches any negative keyword
            if negative_keywords and any(neg.lower() in topic.lower() for neg in negative_keywords):
                logger.info(f"Skipping fallback keyword '{topic}' (matches negative keyword)")
                continue

            keyword = Keyword(
                keyword=topic.lower(),
                search_intent=SearchIntent.INFORMATIONAL,
                difficulty=KeywordDifficulty.MEDIUM,
                monthly_volume_estimate="Unknown",
                relevance_score=7.0,
                long_tail=False,
                question_based=False,
                related_topics=[topic],
            )
            keywords.append(keyword)
        return keywords

    def _generate_fallback_secondary_keywords(
        self, primary_keywords: List[Keyword], negative_keywords: Optional[List[str]] = None
    ) -> List[Keyword]:
        """Generate basic secondary keywords if API fails, filtering out negative keywords"""
        negative_keywords = negative_keywords or []
        keywords = []
        question_words = ["how to", "what is", "why", "when to", "best"]

        for primary_kw in primary_keywords[:5]:
            for qw in question_words:
                # Skip prefix if the primary keyword already starts with it (Bug #165):
                # prevents "how to how to automate..." or "best best approval workflow..."
                if primary_kw.keyword.lower().startswith(qw.lower()):
                    continue
                full_keyword = f"{qw} {primary_kw.keyword}"

                # Filter: skip if keyword matches any negative keyword
                if negative_keywords and any(
                    neg.lower() in full_keyword.lower() for neg in negative_keywords
                ):
                    continue

                keyword = Keyword(
                    keyword=full_keyword,
                    search_intent=SearchIntent.INFORMATIONAL,
                    difficulty=KeywordDifficulty.LOW,
                    monthly_volume_estimate="Unknown",
                    relevance_score=6.0,
                    long_tail=True,
                    question_based=True,
                    related_topics=primary_kw.related_topics,
                )
                keywords.append(keyword)
                if len(keywords) >= 20:
                    break
            if len(keywords) >= 20:
                break

        return keywords

    def generate_reports(self, strategy: KeywordStrategy) -> Dict[str, Path]:
        """Generate keyword strategy reports in multiple formats"""
        output_dir = self.base_output_dir / self.project_id
        output_dir.mkdir(parents=True, exist_ok=True)

        reports = {}

        # JSON report
        json_path = output_dir / "keyword_strategy.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(strategy.model_dump(), f, indent=2)
        reports["json"] = json_path

        # Markdown report
        markdown_path = output_dir / "keyword_strategy_report.md"
        markdown_content = self._format_markdown_report(strategy)
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        reports["markdown"] = markdown_path

        # Text report (simple list)
        text_path = output_dir / "keyword_list.txt"
        text_content = self._format_text_report(strategy)
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        reports["text"] = text_path

        logger.info(f"Generated {len(reports)} report formats")
        return reports

    def _format_markdown_report(self, strategy: KeywordStrategy) -> str:
        """Format strategy as markdown report"""
        md = f"""# SEO Keyword Strategy Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

**Business:** {strategy.business_name}
**Industry:** {strategy.industry}
**Target Audience:** {strategy.target_audience}

"""
        # Warn when Google Trends enrichment was partial or absent
        all_kw = strategy.primary_keywords + strategy.secondary_keywords
        enriched_count = sum(1 for kw in all_kw if kw.trend_score is not None)
        if all_kw and enriched_count < len(all_kw):
            if enriched_count == 0:
                md += (
                    "> **Note:** Google Trends data was unavailable for all keywords due to "
                    "rate limiting. Trend signals are not included in this report.\n\n"
                )
            else:
                md += (
                    f"> **Note:** Google Trends data available for {enriched_count}/{len(all_kw)} "
                    "keywords due to rate limiting. Trend signals may be incomplete.\n\n"
                )

        md += f"""---

## Executive Summary

{strategy.strategy_summary}

---

## Primary Keywords ({len(strategy.primary_keywords)})

"""

        for i, kw in enumerate(strategy.primary_keywords, 1):
            # Quality indicator
            quality_badge = ""
            if kw.quality_score is not None:
                if kw.quality_score >= 80:
                    quality_badge = " 🌟 HIGH QUALITY"
                elif kw.quality_score >= 70:
                    quality_badge = " ✅ GOOD QUALITY"
                else:
                    quality_badge = " ⚠️ MEDIUM QUALITY"

            md += f"""
### {i}. {kw.keyword}{quality_badge}

"""
            # Show quality score first if available
            if kw.quality_score is not None:
                md += f"- **Quality Score:** {kw.quality_score:.1f}/100 ⭐\n"

            md += f"""- **Search Intent:** {kw.search_intent.value.title()}
- **Difficulty:** {kw.difficulty.value.upper()}
- **Volume Estimate:** {kw.monthly_volume_estimate}
- **Relevance Score:** {kw.relevance_score}/10
- **Long-tail:** {"Yes" if kw.long_tail else "No"}
- **Question-based:** {"Yes" if kw.question_based else "No"}
- **Related Topics:** {", ".join(kw.related_topics)}
"""
            # Add Google Trends data if available
            if kw.trend_score is not None:
                md += f"- **Google Trends Score:** {kw.trend_score:.1f}/100\n"
            if kw.trend_direction:
                trend_emoji = {
                    "rising": "📈",
                    "stable": "➡️",
                    "declining": "📉",
                    "seasonal": "🔄",
                }.get(kw.trend_direction, "")
                md += f"- **Trend Direction:** {kw.trend_direction.title()} {trend_emoji}\n"
            if kw.seasonal:
                md += "- **Seasonal Variation:** Yes 🔄\n"
            if kw.related_queries:
                md += f"- **Related Searches:** {', '.join(kw.related_queries[:3])}\n"

        md += f"""
---

## Secondary Keywords ({len(strategy.secondary_keywords)})

"""

        for i, kw in enumerate(strategy.secondary_keywords, 1):
            md += f"{i}. **{kw.keyword}** ({kw.difficulty.value}, {kw.search_intent.value})\n"

        md += """
---

## Keyword Clusters

"""

        for cluster in strategy.keyword_clusters:
            md += f"""
### [{cluster.priority.upper()}] {cluster.theme}

**Primary Keyword:** {cluster.primary_keyword}

**Secondary Keywords:** {", ".join(cluster.secondary_keywords)}

**Content Ideas:**
"""
            for suggestion in cluster.content_suggestions:
                md += f"- {suggestion}\n"

        if strategy.quick_win_keywords:
            md += """
---

## Quick Win Keywords

Target these first for early SEO wins:

"""
            quick_win: str
            for quick_win in strategy.quick_win_keywords:
                md += f"- {quick_win}\n"

        if strategy.competitor_analysis:
            md += """
---

## Competitor Analysis

"""
            for comp in strategy.competitor_analysis:
                md += f"""
### {comp.competitor_name}

**Their Keywords:** {", ".join(comp.estimated_keywords)}

**Gap Opportunities:** {", ".join(comp.gaps)}

**Overlaps:** {", ".join(comp.overlaps)}

"""

        md += """
---

## Content Priorities

Recommended content pieces to create (in priority order):

"""
        for i, priority in enumerate(strategy.content_priorities, 1):
            md += f"{i}. {priority}\n"

        md += """
---

*Report generated by SEO Keyword Research Tool*
"""

        return md

    def _format_text_report(self, strategy: KeywordStrategy) -> str:
        """Format strategy as simple text list"""
        text = f"""SEO KEYWORD STRATEGY - {strategy.business_name}
{"=" * 60}

PRIMARY KEYWORDS ({len(strategy.primary_keywords)}):
"""

        for i, kw in enumerate(strategy.primary_keywords, 1):
            text += f"{i}. {kw.keyword} ({kw.difficulty.value}, {kw.search_intent.value})\n"

        text += f"\n\nSECONDARY KEYWORDS ({len(strategy.secondary_keywords)}):\n"

        for i, kw in enumerate(strategy.secondary_keywords, 1):
            text += f"{i}. {kw.keyword}\n"

        if strategy.quick_win_keywords:
            text += "\n\nQUICK WINS:\n"
            quick_win: str
            for quick_win in strategy.quick_win_keywords:
                text += f"- {quick_win}\n"

        text += "\n\nCONTENT PRIORITIES:\n"
        for i, priority in enumerate(strategy.content_priorities, 1):
            text += f"{i}. {priority}\n"

        return text
