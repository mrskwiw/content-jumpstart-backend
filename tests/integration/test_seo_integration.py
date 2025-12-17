"""Test SEO Keyword Integration

Tests the complete SEO keyword extraction and integration workflow.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agents.brief_parser import BriefParserAgent
from src.agents.content_generator import ContentGeneratorAgent
from src.agents.keyword_agent import KeywordExtractionAgent
from src.agents.qa_agent import QAAgent
from src.utils.logger import console, logger
from src.utils.output_formatter import OutputFormatter
from src.validators.keyword_validator import KeywordValidator


def main():
    """Test SEO keyword integration"""

    console.print("\n[bold cyan]=== SEO Keyword Integration Test ===[/bold cyan]\n")

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

    # Step 2: Extract SEO keywords
    console.print("[cyan]Step 2: Extracting SEO keywords...[/cyan]")
    keyword_agent = KeywordExtractionAgent()
    keyword_strategy = keyword_agent.extract_keywords(client_brief)

    console.print("[green]OK[/green] Extracted keywords:")
    console.print(f"  Primary: {len(keyword_strategy.primary_keywords)}")
    for kw in keyword_strategy.primary_keywords[:3]:
        console.print(f"    - {kw.keyword} ({kw.intent.value}, priority {kw.priority})")
    console.print(f"  Secondary: {len(keyword_strategy.secondary_keywords)}")
    console.print(f"  Long-tail: {len(keyword_strategy.longtail_keywords)}\n")

    # Step 3: Generate posts with keyword integration
    console.print("[cyan]Step 3: Generating 5 posts with keyword integration...[/cyan]")
    generator = ContentGeneratorAgent(keyword_strategy=keyword_strategy)
    posts = generator.generate_posts(
        client_brief=client_brief, num_posts=5, template_count=15, randomize=True
    )

    console.print(f"[green]OK[/green] Generated {len(posts)} posts\n")

    # Step 4: Validate keyword usage
    console.print("[cyan]Step 4: Validating keyword usage...[/cyan]")
    validator = KeywordValidator(keyword_strategy)
    validation_results = validator.validate(posts)

    console.print("\n[bold]Keyword Validation Results:[/bold]")
    console.print(
        f"  Status: {'[green]PASSED[/green]' if validation_results['passed'] else '[yellow]NEEDS REVIEW[/yellow]'}"
    )
    console.print(
        f"  Posts with primary keywords: {validation_results['posts_with_primary']}/{len(posts)}"
    )
    console.print(f"  Posts with keyword stuffing: {validation_results['posts_with_stuffing']}")
    console.print(f"  Posts missing keywords: {validation_results['posts_missing_keywords']}")

    if validation_results["issues"]:
        console.print("\n[yellow]Issues:[/yellow]")
        for issue in validation_results["issues"]:
            console.print(f"  - {issue}")

    # Step 5: Show detailed keyword analysis for first post
    console.print("\n[bold]Sample Post Keyword Analysis (Post 1):[/bold]")
    if validation_results["post_analyses"]:
        analysis = validation_results["post_analyses"][0]
        console.print(f"  Template: {analysis['template']}")
        console.print(
            f"  Primary keywords found: {', '.join(analysis['primary_keywords']) or 'None'}"
        )
        console.print(f"  Total keyword occurrences: {analysis['total_keywords']}")
        console.print(f"  Keyword density: {analysis['density']}")
        console.print(f"  Has primary keyword: {analysis['has_primary']}")

    # Step 6: Display sample post
    console.print("\n[bold]Sample Generated Post:[/bold]")
    console.print("[dim]" + "=" * 60 + "[/dim]")
    console.print(
        posts[0].content[:300] + "..." if len(posts[0].content) > 300 else posts[0].content
    )
    console.print("[dim]" + "=" * 60 + "[/dim]\n")

    # Step 7: Run QA Agent with keyword validation
    console.print("[cyan]Step 7: Running QA agent with keyword validation...[/cyan]")
    qa_agent = QAAgent(keyword_strategy=keyword_strategy)
    qa_report = qa_agent.validate_posts(posts, client_brief.company_name)

    console.print(f"[green]OK[/green] QA complete: {qa_report.to_summary_string()}\n")

    # Step 8: Export complete deliverable package
    console.print("[cyan]Step 8: Exporting complete deliverable package...[/cyan]")
    formatter = OutputFormatter()
    saved_files = formatter.save_complete_package(
        posts=posts,
        client_brief=client_brief,
        client_name="SEO_Integration_Test",
        qa_report=qa_report,
        keyword_strategy=keyword_strategy,
    )

    console.print("[green]OK[/green] Deliverable package saved:")
    for file_type, file_path in saved_files.items():
        console.print(f"  - {file_type}: {file_path.name}")
    console.print("")

    console.print("[green][bold]Test completed successfully![/bold][/green]\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error("Test failed", exc_info=True)
        sys.exit(1)
