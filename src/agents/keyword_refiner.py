"""Keyword Refinement Agent

Interactive agent for reviewing and refining extracted SEO keywords.
"""

from typing import List

from anthropic import Anthropic

from ..config.settings import settings
from ..models.seo_keyword import KeywordDifficulty, KeywordIntent, KeywordStrategy, SEOKeyword
from ..utils.logger import console, logger


class KeywordRefinementAgent:
    """Agent for refining keyword strategies based on user feedback"""

    def __init__(self):
        """Initialize keyword refinement agent"""
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.ANTHROPIC_MODEL

    def review_keywords_interactive(self, keyword_strategy: KeywordStrategy) -> KeywordStrategy:
        """
        Interactive keyword review and refinement

        Args:
            keyword_strategy: Initial keyword strategy to review

        Returns:
            Refined keyword strategy
        """
        console.print("\n[bold cyan]=== Keyword Strategy Review ===[/bold cyan]\n")

        # Display current keywords
        self._display_keywords(keyword_strategy)

        # Ask for feedback
        console.print("\n[yellow]Review the keywords above.[/yellow]")
        console.print("[dim]Press Enter to accept, or type feedback to refine[/dim]")
        feedback = input("\nYour feedback (or press Enter to continue): ").strip()

        if not feedback:
            logger.info("Keywords accepted without changes")
            return keyword_strategy

        # Refine based on feedback
        console.print("\n[cyan]Refining keywords based on your feedback...[/cyan]")
        refined_strategy = self._refine_with_ai(keyword_strategy, feedback)

        logger.info("Keywords refined based on user feedback")
        return refined_strategy

    def add_custom_keywords(
        self,
        keyword_strategy: KeywordStrategy,
        custom_keywords: List[str],
        keyword_type: str = "secondary",
    ) -> KeywordStrategy:
        """
        Add custom keywords to strategy

        Args:
            keyword_strategy: Existing strategy
            custom_keywords: List of custom keyword phrases
            keyword_type: Type of keywords (primary, secondary, longtail)

        Returns:
            Updated keyword strategy
        """
        logger.info(f"Adding {len(custom_keywords)} custom {keyword_type} keywords")

        # Create SEOKeyword objects for custom keywords
        new_keywords = []
        for kw_text in custom_keywords:
            keyword = SEOKeyword(
                keyword=kw_text,
                intent=KeywordIntent.INFORMATIONAL,  # Default intent
                difficulty=KeywordDifficulty.MEDIUM,  # Default difficulty
                priority=len(new_keywords) + 1,
                related_keywords=[],
                notes="User-provided custom keyword",
            )
            new_keywords.append(keyword)

        # Add to appropriate list
        if keyword_type == "primary":
            keyword_strategy.primary_keywords.extend(new_keywords)
        elif keyword_type == "longtail":
            keyword_strategy.longtail_keywords.extend(new_keywords)
        else:  # secondary
            keyword_strategy.secondary_keywords.extend(new_keywords)

        return keyword_strategy

    def remove_keywords(
        self, keyword_strategy: KeywordStrategy, keywords_to_remove: List[str]
    ) -> KeywordStrategy:
        """
        Remove specific keywords from strategy

        Args:
            keyword_strategy: Current strategy
            keywords_to_remove: List of keyword phrases to remove

        Returns:
            Updated strategy with keywords removed
        """
        logger.info(f"Removing {len(keywords_to_remove)} keywords")

        # Remove from all lists
        keyword_strategy.primary_keywords = [
            kw
            for kw in keyword_strategy.primary_keywords
            if kw.keyword.lower() not in [k.lower() for k in keywords_to_remove]
        ]
        keyword_strategy.secondary_keywords = [
            kw
            for kw in keyword_strategy.secondary_keywords
            if kw.keyword.lower() not in [k.lower() for k in keywords_to_remove]
        ]
        keyword_strategy.longtail_keywords = [
            kw
            for kw in keyword_strategy.longtail_keywords
            if kw.keyword.lower() not in [k.lower() for k in keywords_to_remove]
        ]

        return keyword_strategy

    def _display_keywords(self, strategy: KeywordStrategy):
        """Display keywords in a readable format"""
        console.print("[bold]Primary Keywords:[/bold]")
        for kw in strategy.primary_keywords:
            console.print(f"  - {kw.keyword} [dim]({kw.intent.value}, {kw.difficulty.value})[/dim]")

        console.print("\n[bold]Secondary Keywords:[/bold]")
        for kw in strategy.secondary_keywords[:5]:  # Show first 5
            console.print(f"  - {kw.keyword} [dim]({kw.intent.value})[/dim]")
        if len(strategy.secondary_keywords) > 5:
            console.print(f"  [dim]... and {len(strategy.secondary_keywords) - 5} more[/dim]")

        console.print("\n[bold]Long-tail Keywords:[/bold]")
        for kw in strategy.longtail_keywords[:5]:  # Show first 5
            console.print(f"  - {kw.keyword}")
        if len(strategy.longtail_keywords) > 5:
            console.print(f"  [dim]... and {len(strategy.longtail_keywords) - 5} more[/dim]")

    def _refine_with_ai(self, strategy: KeywordStrategy, feedback: str) -> KeywordStrategy:
        """
        Refine keywords using AI based on user feedback

        Args:
            strategy: Current keyword strategy
            feedback: User feedback on what to change

        Returns:
            Refined keyword strategy
        """
        # Build refinement prompt
        current_keywords = {
            "primary": [kw.keyword for kw in strategy.primary_keywords],
            "secondary": [kw.keyword for kw in strategy.secondary_keywords],
            "longtail": [kw.keyword for kw in strategy.longtail_keywords],
        }

        system_prompt = """You are an SEO keyword strategist.
Refine the keyword strategy based on user feedback.
Return the updated keywords in the same JSON format.
Keep the same structure but update keywords according to feedback."""

        user_prompt = f"""Current keywords:
{current_keywords}

User feedback: {feedback}

Please refine the keyword strategy and return updated JSON with:
- primary_keywords (3-5)
- secondary_keywords (8-10)
- longtail_keywords (10-12)

Each keyword should have: keyword, intent, difficulty, priority, related_keywords, notes"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            temperature=0.3,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Parse response (reuse existing extraction logic)
        from .keyword_agent import KeywordExtractionAgent

        extractor = KeywordExtractionAgent()
        keywords_data = extractor._extract_json_from_response(response.content[0].text)

        # Parse into strategy
        refined_strategy = extractor._parse_keyword_strategy(keywords_data)

        return refined_strategy
