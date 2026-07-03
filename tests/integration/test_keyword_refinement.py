"""Test Keyword Refinement Workflow

Demonstrates the keyword refinement capabilities.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agents.brief_parser import BriefParserAgent
from src.agents.keyword_agent import KeywordExtractionAgent
from src.agents.keyword_refiner import KeywordRefinementAgent
from src.utils.logger import console, logger


def main():
    """Test keyword refinement workflow"""

    console.print("\n[bold cyan]=== Keyword Refinement Test ===[/bold cyan]\n")

    # Step 1: Parse client brief
    console.print("[cyan]Step 1: Parsing client brief...[/cyan]")
    brief_path = Path("tests/fixtures/sample_brief.txt")

    if not brief_path.exists():
        console.print(f"[red]ERROR:[/red] Brief file not found: {brief_path}")
        return

    brief_text = brief_path.read_text()
    parser = BriefParserAgent()
    client_brief = parser.parse_brief(brief_text)

    console.print(f"[green]OK[/green] Parsed brief for [bold]{client_brief.company_name}[/bold]\n")

    # Step 2: Extract initial keywords
    console.print("[cyan]Step 2: Extracting initial SEO keywords...[/cyan]")
    keyword_agent = KeywordExtractionAgent()
    keyword_strategy = keyword_agent.extract_keywords(client_brief)

    console.print("[green]OK[/green] Extracted initial keywords:\n")

    # Step 3: Test add custom keywords
    console.print("[cyan]Step 3: Testing add custom keywords...[/cyan]")
    refiner = KeywordRefinementAgent()

    custom_keywords = ["content marketing automation", "AI content generation for B2B"]

    keyword_strategy = refiner.add_custom_keywords(
        keyword_strategy, custom_keywords, keyword_type="secondary"
    )

    console.print(f"[green]OK[/green] Added {len(custom_keywords)} custom keywords")
    console.print(f"  Total secondary keywords: {len(keyword_strategy.secondary_keywords)}\n")

    # Step 4: Test remove keywords
    console.print("[cyan]Step 4: Testing remove keywords...[/cyan]")

    # Find first keyword to remove
    if keyword_strategy.longtail_keywords:
        keyword_to_remove = keyword_strategy.longtail_keywords[0].keyword
        console.print(f"  Removing: '{keyword_to_remove}'")

        keyword_strategy = refiner.remove_keywords(keyword_strategy, [keyword_to_remove])

        console.print("[green]OK[/green] Removed keyword")
        console.print(f"  Total long-tail keywords: {len(keyword_strategy.longtail_keywords)}\n")

    # Step 5: Display final strategy
    console.print("[cyan]Step 5: Final keyword strategy summary...[/cyan]\n")
    refiner._display_keywords(keyword_strategy)

    console.print("\n[green][bold]Refinement test completed![/bold][/green]")
    console.print(
        "[dim]Note: Interactive review (review_keywords_interactive) requires user input[/dim]\n"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error("Test failed", exc_info=True)
        sys.exit(1)
