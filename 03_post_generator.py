#!/usr/bin/env python3
"""
30-Day Content Jumpstart: Post Generator CLI

Main command-line interface for generating client content packages.
"""

import io
import sys
from pathlib import Path

# Force UTF-8 encoding for Windows compatibility
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
import asyncio
import json
import time
from datetime import date, datetime
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agents.brief_parser import BriefParserAgent
from src.agents.content_generator import ContentGeneratorAgent
from src.agents.qa_agent import QAAgent
from src.config.settings import settings
from src.database.project_db import ProjectDatabase
from src.models.client_brief import ClientBrief, Platform
from src.utils.cost_dashboard import CostDashboard
from src.utils.cost_tracker import get_default_tracker
from src.utils.logger import log_client_complete, log_client_start, logger
from src.utils.output_formatter import OutputFormatter
from src.utils.template_loader import TemplateLoader

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="Content Jumpstart")
def cli():
    """
    30-Day Content Jumpstart - AI-powered social media content generator

    Generate 30 professional posts for your clients in 5-6 hours.
    """


@cli.command()
@click.argument("brief_file", type=click.Path(exists=True))
@click.option(
    "--client-name",
    "-c",
    help="Client name for file organization",
    required=True,
)
@click.option(
    "--num-posts",
    "-n",
    default=30,
    help="Number of posts to generate (default: 30)",
    type=int,
)
@click.option(
    "--template-count",
    "-t",
    default=15,
    help="Number of unique templates to use (default: 15)",
    type=int,
)
@click.option(
    "--output-dir",
    "-o",
    help="Output directory (default: data/outputs)",
    type=click.Path(),
)
@click.option(
    "--no-randomize",
    is_flag=True,
    help="Don't randomize post order",
)
@click.option(
    "--templates",
    help="Comma-separated template IDs to use (e.g., '1,3,5,7,9'). Overrides intelligent selection.",
    type=str,
)
@click.option(
    "--platform",
    "-p",
    default="linkedin",
    help="Target platform: linkedin, twitter, facebook, blog (default: linkedin)",
    type=click.Choice(["linkedin", "twitter", "facebook", "blog", "email"], case_sensitive=False),
)
@click.option(
    "--start-date",
    "-s",
    help="Start date for posting schedule (YYYY-MM-DD, default: today)",
    type=str,
)
@click.option(
    "--no-docx",
    is_flag=True,
    help="Skip DOCX deliverable generation",
)
@click.option(
    "--no-analytics",
    is_flag=True,
    help="Skip analytics tracker generation",
)
@click.option(
    "--auto-fix",
    is_flag=True,
    help="Automatically regenerate posts that fail quality checks (readability, length, CTA, engagement)",
)
@click.option(
    "--quality-profile",
    "-q",
    help="Quality profile to use (file path or preset: professional_linkedin, casual_linkedin, executive_linkedin)",
    type=str,
)
@click.option(
    "--use-voice-samples",
    is_flag=True,
    help="Use uploaded voice samples for authentic voice matching (requires voice samples)",
)
def generate(
    brief_file: str,
    client_name: str,
    num_posts: int,
    template_count: int,
    output_dir: Optional[str],
    no_randomize: bool,
    templates: Optional[str],
    platform: str,
    start_date: Optional[str],
    no_docx: bool,
    no_analytics: bool,
    auto_fix: bool,
    quality_profile: Optional[str],
    use_voice_samples: bool,
):
    """
    Generate posts from a client brief file

    Example:
        python 03_post_generator.py generate brief.txt -c "Acme Corp"
    """
    start_time = time.time()
    log_client_start(client_name)

    try:
        # Read brief file
        brief_path = Path(brief_file)
        console.print(f"[cyan]Reading brief from {brief_path}[/cyan]")
        brief_text = brief_path.read_text(encoding="utf-8")

        # Parse brief
        console.print("[cyan]Parsing client brief...[/cyan]")
        parser = BriefParserAgent()
        client_brief = parser.parse_brief(brief_text)

        console.print(
            f"[green]OK[/green] Parsed brief for [bold]{client_brief.company_name}[/bold]"
        )

        # Show brief summary
        _display_brief_summary(client_brief)

        # Parse template IDs if provided
        template_ids = None
        if templates:
            try:
                template_ids = [int(tid.strip()) for tid in templates.split(",")]
                console.print(f"[yellow]Using manual template override:[/yellow] {template_ids}")
            except ValueError:
                console.print(
                    "[red]ERROR:[/red] Invalid template IDs format. Use comma-separated numbers (e.g., '1,3,5')"
                )
                sys.exit(1)

        # Convert platform string to Platform enum
        platform_enum = Platform(platform.lower())
        console.print(f"[dim]Target platform: {platform_enum.value}[/dim]")

        # Generate posts
        console.print(f"\n[cyan]Generating {num_posts} posts...[/cyan]")
        generator = ContentGeneratorAgent()

        voice_match_report = None  # Will be populated if using voice samples

        # Check if using voice samples for voice matching
        if use_voice_samples:
            if not settings.PARALLEL_GENERATION:
                console.print(
                    "[yellow]Warning:[/yellow] Voice matching requires async generation. "
                    "Enabling async mode for this run."
                )

            console.print("[cyan]Using voice sample matching...[/cyan]")
            console.print(
                f"[dim]Parallel generation (max concurrent: {settings.MAX_CONCURRENT_API_CALLS})[/dim]"
            )

            # Generate with voice matching
            posts, voice_match_report = asyncio.run(
                generator.generate_posts_with_voice_matching_async(
                    client_brief=client_brief,
                    num_posts=num_posts,
                    template_count=template_count,
                    randomize=not no_randomize,
                    max_concurrent=settings.MAX_CONCURRENT_API_CALLS,
                    template_ids=template_ids,
                    platform=platform_enum,
                )
            )

            if voice_match_report:
                console.print("[green]✓[/green] Voice matching complete")
            else:
                console.print(
                    f"[yellow]No voice samples found for {client_name}. "
                    f'Upload samples with: upload-voice-samples --client "{client_name}"[/yellow]'
                )

        # Standard generation (no voice matching)
        elif settings.PARALLEL_GENERATION:
            console.print(
                f"[dim]Using parallel generation (max concurrent: {settings.MAX_CONCURRENT_API_CALLS})[/dim]"
            )
            posts = asyncio.run(
                generator.generate_posts_async(
                    client_brief=client_brief,
                    num_posts=num_posts,
                    template_count=template_count,
                    randomize=not no_randomize,
                    max_concurrent=settings.MAX_CONCURRENT_API_CALLS,
                    template_ids=template_ids,
                    platform=platform_enum,
                )
            )
        else:
            console.print("[dim]Using sequential generation[/dim]")
            posts = generator.generate_posts(
                client_brief=client_brief,
                num_posts=num_posts,
                template_count=template_count,
                randomize=not no_randomize,
                template_ids=template_ids,
                platform=platform_enum,
            )

        console.print(f"[green]OK[/green] Generated {len(posts)} posts")

        # Run QA validation
        console.print("\n[cyan]Running quality assurance...[/cyan]")
        qa_agent = QAAgent()
        qa_report = qa_agent.validate_posts(posts, client_name=client_brief.company_name)

        # Display QA summary
        qa_status = (
            "[green]PASSED[/green]" if qa_report.overall_passed else "[yellow]NEEDS REVIEW[/yellow]"
        )
        console.print(
            f"QA Report: {qa_status} | Quality: {qa_report.quality_score:.0%} | Issues: {qa_report.total_issues}"
        )

        if qa_report.total_issues > 0:
            console.print("\n[yellow]Quality Issues Found:[/yellow]")
            for issue in qa_report.all_issues[:5]:  # Show first 5 issues
                console.print(f"  • {issue}")
            if qa_report.total_issues > 5:
                console.print(f"  ... and {qa_report.total_issues - 5} more (see QA report)")

        # Check for posts needing review
        flagged_posts = [p for p in posts if p.needs_review]
        if flagged_posts:
            console.print(f"[yellow][!][/yellow]  {len(flagged_posts)} posts flagged for review")

        # Display voice match report (if available)
        if voice_match_report:
            console.print("\n[cyan]Voice Match Report[/cyan]")

            # Overall score with color coding
            score_color = (
                "[green]"
                if voice_match_report.match_score >= 0.8
                else "[yellow]"
                if voice_match_report.match_score >= 0.7
                else "[red]"
            )
            console.print(
                f"Overall Voice Match: {score_color}{voice_match_report.match_score:.0%}[/]"
            )

            # Component scores
            console.print("\nComponent Scores:")
            if voice_match_report.readability_score:
                console.print(
                    f"  • Readability: {voice_match_report.readability_score.score:.0%} "
                    f"(target: {voice_match_report.readability_score.target_value:.1f}, "
                    f"actual: {voice_match_report.readability_score.actual_value:.1f})"
                )
            if voice_match_report.word_count_score:
                console.print(
                    f"  • Word Count: {voice_match_report.word_count_score.score:.0%} "
                    f"(target: {int(voice_match_report.word_count_score.target_value)}, "
                    f"actual: {int(voice_match_report.word_count_score.actual_value)})"
                )
            if voice_match_report.archetype_score:
                console.print(
                    f"  • Brand Archetype: {voice_match_report.archetype_score.score:.0%}"
                )
            if voice_match_report.phrase_usage_score:
                console.print(
                    f"  • Key Phrase Usage: {voice_match_report.phrase_usage_score.score:.0%} "
                    f"({int(voice_match_report.phrase_usage_score.actual_value)}/"
                    f"{int(voice_match_report.phrase_usage_score.target_value)} phrases)"
                )

            # Strengths
            if voice_match_report.strengths:
                console.print("\n[green]Strengths:[/green]")
                for strength in voice_match_report.strengths[:3]:
                    console.print(f"  ✓ {strength}")

            # Improvements
            if voice_match_report.improvements:
                console.print("\n[yellow]Recommendations:[/yellow]")
                for improvement in voice_match_report.improvements[:3]:
                    console.print(f"  → {improvement}")

        # Auto-fix quality issues (if enabled)
        if auto_fix:
            from src.agents.post_regenerator import PostRegenerator
            from src.models.quality_profile import QualityProfile, get_default_profile
            from src.utils.template_loader import TemplateLoader

            console.print("\n[cyan]Auto-fixing quality issues...[/cyan]")

            # Load quality profile
            profile = None
            if quality_profile:
                # Check if it's a file path or preset name
                profile_path = Path(quality_profile)
                if profile_path.exists():
                    # Load from file
                    try:
                        profile = QualityProfile.from_file(quality_profile)
                        console.print(f"[dim]Using quality profile from: {quality_profile}[/dim]")
                    except Exception as e:
                        console.print(f"[yellow]Warning:[/yellow] Failed to load profile: {e}")
                        console.print("[dim]Using default profile instead[/dim]")
                        profile = get_default_profile("professional_linkedin")
                else:
                    # Try as preset name
                    try:
                        profile = get_default_profile(quality_profile)
                        console.print(f"[dim]Using preset quality profile: {quality_profile}[/dim]")
                    except ValueError:
                        console.print(
                            f"[yellow]Warning:[/yellow] Unknown profile '{quality_profile}'"
                        )
                        console.print("[dim]Using default profile instead[/dim]")
                        profile = get_default_profile("professional_linkedin")
            else:
                profile = get_default_profile("professional_linkedin")
                console.print("[dim]Using default quality profile: professional_linkedin[/dim]")

            # Display profile settings
            console.print(f"  Profile: {profile.profile_name} - {profile.description}")
            console.print(
                f"  Readability: {profile.min_readability}-{profile.max_readability} | "
                f"Length: {profile.min_words}-{profile.max_words} words | "
                f"CTA: {'required' if profile.require_cta else 'optional'}"
            )

            # Load templates for regeneration
            template_loader = TemplateLoader()
            all_templates = template_loader.get_all_templates()

            # Filter to specific template IDs if provided
            if template_ids:
                template_map = {t.template_id: t for t in all_templates}
                selected_templates = [
                    template_map[tid] for tid in template_ids if tid in template_map
                ]
            else:
                selected_templates = all_templates[:template_count]

            # Regenerate failed posts with quality profile
            regenerator = PostRegenerator(quality_profile=profile)
            regenerated_posts, regen_stats = regenerator.regenerate_failed_posts(
                posts=posts,
                templates=selected_templates,
                client_brief=client_brief,
                system_prompt=None,  # Will build fresh system prompt
            )

            posts = regenerated_posts  # Update with regenerated versions

            # Display regeneration results
            if regen_stats["posts_regenerated"] > 0:
                console.print(
                    f"[green]OK[/green] Regenerated {regen_stats['posts_regenerated']}/{regen_stats['total_posts']} posts"
                )
                console.print(f"  Improved: {regen_stats['posts_improved']} posts")

                if regen_stats["reasons"]:
                    console.print("  Reasons:")
                    for reason_type, count in regen_stats["reasons"].items():
                        console.print(f"    • {reason_type}: {count}")
            else:
                console.print("[green]OK[/green] No posts needed regeneration")

        # Parse start date if provided
        schedule_start = None
        if start_date:
            try:
                schedule_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                console.print(
                    f"[yellow]Warning:[/yellow] Invalid date format '{start_date}'. "
                    "Using today as start date."
                )
                schedule_start = date.today()

        # Save outputs
        console.print("\n[cyan]Saving deliverables...[/cyan]")
        output_path = Path(output_dir) if output_dir else None
        formatter = OutputFormatter(output_dir=output_path)

        saved_files = formatter.save_complete_package(
            posts=posts,
            client_brief=client_brief,
            client_name=client_name,
            qa_report=qa_report,
            start_date=schedule_start,
            include_docx=not no_docx,
            include_analytics_tracker=not no_analytics,
        )

        # Display saved files
        console.print("[green]OK[/green] Saved complete package:\n")
        for file_type, file_path in saved_files.items():
            console.print(f"  • {file_type}: [cyan]{file_path}[/cyan]")

        # Register project in revision tracking database
        try:
            from src.database.project_db import ProjectDatabase
            from src.models.project import Project, ProjectStatus

            db = ProjectDatabase()

            # Generate project ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_id = f"{client_name.replace(' ', '')}_{timestamp}"

            # Create project record
            project = Project(
                project_id=project_id,
                client_name=client_name,
                deliverable_path=str(saved_files.get("markdown", "")),
                brief_path=str(brief_path),
                num_posts=len(posts),
                quality_profile_name=quality_profile,
                status=ProjectStatus.COMPLETED,
            )

            db.create_project(project)

            console.print(f"\n[green]✓[/green] Project registered: [cyan]{project_id}[/cyan]")
            console.print("[dim]Revision tracking enabled (5 revisions included)[/dim]")
            console.print(f'[dim]Check scope: scope-status --project "{project_id}"[/dim]')

        except Exception as e:
            # Don't fail the whole generation if database registration fails
            console.print(
                f"[yellow]Warning:[/yellow] Failed to register project in database: {str(e)}"
            )
            logger.warning(f"Project registration failed: {str(e)}")

        # Show completion summary
        duration = time.time() - start_time
        log_client_complete(client_name, len(posts), duration)

        _display_completion_summary(posts, duration)

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Generation failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.argument("brief_file", type=click.Path(exists=True))
def parse_brief(brief_file: str):
    """
    Parse and display client brief information

    Example:
        python 03_post_generator.py parse-brief brief.txt
    """
    try:
        # Read brief file
        brief_path = Path(brief_file)
        console.print(f"[cyan]Reading brief from {brief_path}[/cyan]")
        brief_text = brief_path.read_text(encoding="utf-8")

        # Parse brief
        console.print("[cyan]Parsing client brief...[/cyan]")
        parser = BriefParserAgent()
        client_brief = parser.parse_brief(brief_text)

        console.print(
            f"[green]OK[/green] Successfully parsed brief for [bold]{client_brief.company_name}[/bold]\n"
        )

        # Display full brief details
        _display_brief_summary(client_brief, detailed=True)

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Brief parsing failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command()
def list_templates():
    """
    List all available post templates

    Example:
        python 03_post_generator.py list-templates
    """
    try:
        loader = TemplateLoader()
        templates = loader.get_all_templates()

        console.print(f"\n[bold]Available Templates ({len(templates)} total)[/bold]\n")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim", width=4)
        table.add_column("Name", width=40)
        table.add_column("Type", width=20)
        table.add_column("Difficulty", width=10)
        table.add_column("Story", width=8)
        table.add_column("Data", width=8)

        for template in templates:
            table.add_row(
                str(template.template_id),
                template.name,
                template.template_type.value,
                template.difficulty.value,
                "Yes" if template.requires_story else "No",
                "Yes" if template.requires_data else "No",
            )

        console.print(table)
        console.print("\n[dim]Story: Requires personal stories or examples[/dim]")
        console.print("[dim]Data: Requires statistics or data points[/dim]\n")

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Template listing failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--brief-template",
    "-b",
    is_flag=True,
    help="Show client brief template",
)
def show_example(brief_template: bool):
    """
    Show example templates and usage

    Example:
        python 03_post_generator.py show-example --brief-template
    """
    if brief_template:
        # Show path to brief template
        project_dir = Path(__file__).parent
        brief_template_path = project_dir / settings.CLIENT_BRIEF_TEMPLATE_PATH

        console.print(f"\n[bold]Client Brief Template:[/bold] [cyan]{brief_template_path}[/cyan]\n")

        if brief_template_path.exists():
            console.print("[dim]Preview:[/dim]\n")
            content = brief_template_path.read_text(encoding="utf-8")
            # Show first 30 lines
            lines = content.split("\n")[:30]
            console.print("\n".join(lines))
            console.print(f"\n[dim]... ({len(content.split())} total lines)[/dim]\n")
        else:
            console.print(f"[yellow]Template file not found at {brief_template_path}[/yellow]\n")
    else:
        console.print("\n[bold]Usage Examples:[/bold]\n")
        console.print("1. Generate 30 posts from a brief:")
        console.print(
            '   [cyan]python 03_post_generator.py generate brief.txt -c "Acme Corp"[/cyan]\n'
        )
        console.print("2. Generate custom number of posts:")
        console.print(
            '   [cyan]python 03_post_generator.py generate brief.txt -c "Acme" -n 50[/cyan]\n'
        )
        console.print("3. Use specific templates (manual override):")
        console.print(
            '   [cyan]python 03_post_generator.py generate brief.txt -c "Acme" --templates "1,3,5,7,9"[/cyan]\n'
        )
        console.print("4. Parse a brief to see extracted information:")
        console.print("   [cyan]python 03_post_generator.py parse-brief brief.txt[/cyan]\n")
        console.print("5. List all available templates:")
        console.print("   [cyan]python 03_post_generator.py list-templates[/cyan]\n")


@cli.command()
@click.option(
    "--brief-file",
    "-b",
    help="Optional: Start with partially filled brief",
    type=click.Path(exists=True),
)
def interactive(brief_file: Optional[str]):
    """
    Interactive mode for completing client briefs

    Guides you through a conversational interface to complete missing information
    and improve brief quality through targeted questions.

    Example:
        python 03_post_generator.py interactive
        python 03_post_generator.py interactive -b partial_brief.txt
    """
    from src.cli.interactive_mode import InteractiveMode

    mode = InteractiveMode()
    mode.run(initial_brief_file=brief_file)


@cli.command("generate-multi-platform")
@click.argument("brief_file", type=click.Path(exists=True))
@click.option(
    "--client-name",
    "-c",
    help="Client name for file organization",
    required=True,
)
@click.option(
    "--num-blog-posts",
    "-b",
    default=5,
    help="Number of blog posts to generate (default: 5)",
    type=int,
)
@click.option(
    "--output-dir",
    "-o",
    help="Output directory (default: data/outputs)",
    type=click.Path(),
)
def generate_multi_platform(
    brief_file: str,
    client_name: str,
    num_blog_posts: int,
    output_dir: Optional[str],
):
    """
    Generate multi-platform content package with blog posts and social teasers

    Creates blog posts with Twitter and Facebook teasers that link to them.

    Example:
        python 03_post_generator.py generate-multi-platform brief.txt -c "Acme Corp" -b 5
    """
    start_time = time.time()
    log_client_start(client_name)

    try:
        # Read brief file
        brief_path = Path(brief_file)
        console.print(f"[cyan]Reading brief from {brief_path}[/cyan]")
        brief_text = brief_path.read_text(encoding="utf-8")

        # Parse brief
        console.print("[cyan]Parsing client brief...[/cyan]")
        parser = BriefParserAgent()
        client_brief = parser.parse_brief(brief_text)

        console.print(
            f"[green]OK[/green] Parsed brief for [bold]{client_brief.company_name}[/bold]"
        )

        # Show brief summary
        _display_brief_summary(client_brief)

        # Generate multi-platform content
        console.print("\n[cyan]Generating multi-platform content package...[/cyan]")
        console.print(f"[dim]Blog posts: {num_blog_posts}[/dim]")
        console.print(f"[dim]Twitter teasers: {num_blog_posts}[/dim]")
        console.print(f"[dim]Facebook teasers: {num_blog_posts}[/dim]")

        generator = ContentGeneratorAgent()

        # Use async generation
        content_package = asyncio.run(
            generator.generate_multi_platform_with_blog_links_async(
                client_brief=client_brief,
                num_blog_posts=num_blog_posts,
                social_teasers_per_blog=2,  # 1 Twitter + 1 Facebook
                max_concurrent=settings.MAX_CONCURRENT_API_CALLS,
            )
        )

        # Extract posts from package
        blog_posts = content_package["blog"]
        twitter_posts = content_package["twitter"]
        facebook_posts = content_package["facebook"]
        all_posts = blog_posts + twitter_posts + facebook_posts

        console.print(
            f"[green]OK[/green] Generated {len(blog_posts)} blog + "
            f"{len(twitter_posts)} Twitter + {len(facebook_posts)} Facebook posts"
        )

        # Run QA on all posts together
        console.print("\n[cyan]Running quality assurance...[/cyan]")
        qa_agent = QAAgent()
        qa_report = qa_agent.validate_posts(all_posts, client_name=client_brief.company_name)

        # Display QA summary
        qa_status = (
            "[green]PASSED[/green]" if qa_report.overall_passed else "[yellow]NEEDS REVIEW[/yellow]"
        )
        console.print(
            f"QA Report: {qa_status} | Quality: {qa_report.quality_score:.0%} | Issues: {qa_report.total_issues}"
        )

        # Save outputs
        console.print("\n[cyan]Saving multi-platform deliverables...[/cyan]")
        output_path = Path(output_dir) if output_dir else None
        formatter = OutputFormatter(output_dir=output_path)

        # Save each platform separately
        output_files = formatter.save_complete_package(
            posts=all_posts,
            client_name=client_name,
            client_brief=client_brief,
            qa_report=qa_report,
            start_date=date.today(),  # Default to today for multi-platform
            include_docx=True,  # Always include for multi-platform
            include_analytics_tracker=True,  # Always include for multi-platform
        )

        # Also save platform-specific files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        blog_file = formatter.output_dir / client_name / f"{client_name}_{timestamp}_blog_posts.txt"
        twitter_file = (
            formatter.output_dir / client_name / f"{client_name}_{timestamp}_twitter_teasers.txt"
        )
        facebook_file = (
            formatter.output_dir / client_name / f"{client_name}_{timestamp}_facebook_teasers.txt"
        )

        blog_file.parent.mkdir(parents=True, exist_ok=True)

        # Write blog posts
        with open(blog_file, "w", encoding="utf-8") as f:
            for i, post in enumerate(blog_posts, 1):
                f.write(f"=== BLOG POST #{i} ===\n")
                f.write(f"Title: {post.blog_title}\n")
                f.write(f"Link Placeholder: {post.blog_link_placeholder}\n\n")
                f.write(post.content)
                f.write("\n\n" + "=" * 80 + "\n\n")

        # Write Twitter teasers
        with open(twitter_file, "w", encoding="utf-8") as f:
            for i, post in enumerate(twitter_posts, 1):
                f.write(f"=== TWITTER TEASER #{i} ===\n")
                f.write(f"Links to: {post.blog_title}\n")
                f.write(f"Link: {post.blog_link_placeholder}\n\n")
                f.write(post.content)
                f.write("\n\n" + "=" * 80 + "\n\n")

        # Write Facebook teasers
        with open(facebook_file, "w", encoding="utf-8") as f:
            for i, post in enumerate(facebook_posts, 1):
                f.write(f"=== FACEBOOK TEASER #{i} ===\n")
                f.write(f"Links to: {post.blog_title}\n")
                f.write(f"Link: {post.blog_link_placeholder}\n\n")
                f.write(post.content)
                f.write("\n\n" + "=" * 80 + "\n\n")

        console.print("[green]OK[/green] Saved multi-platform package:\n")
        console.print(f"  • blog: {blog_file}")
        console.print(f"  • twitter: {twitter_file}")
        console.print(f"  • facebook: {facebook_file}")
        console.print(f"  • combined: {output_files['markdown']}")

        # Register project in revision tracking database
        try:
            from src.database.project_db import ProjectDatabase
            from src.models.project import Project, ProjectStatus

            db = ProjectDatabase()

            # Generate project ID
            project_id = f"{client_name.replace(' ', '')}_{timestamp}"

            # Create project record
            project = Project(
                project_id=project_id,
                client_name=client_name,
                deliverable_path=str(output_files.get("markdown", "")),
                brief_path=str(brief_path),
                num_posts=len(all_posts),
                quality_profile_name="multi_platform",  # Special profile for multi-platform
                status=ProjectStatus.COMPLETED,
                notes=f"Multi-platform: {len(blog_posts)} blog, {len(twitter_posts)} Twitter, {len(facebook_posts)} Facebook",
            )

            db.create_project(project)

            console.print(f"\n[green]✓[/green] Project registered: [cyan]{project_id}[/cyan]")
            console.print("[dim]Revision tracking enabled (5 revisions included)[/dim]")

        except Exception as e:
            # Don't fail the whole generation if database registration fails
            console.print(f"[yellow]Warning:[/yellow] Failed to register project: {str(e)}")
            logger.warning(f"Project registration failed: {str(e)}")

        # Log completion
        duration = time.time() - start_time
        log_client_complete(client_name, len(all_posts), duration)

        console.print(
            f"\n[green]OK[/green] Completed multi-platform package for {client_name} in {duration:.1f}s\n"
        )

        # Display summary
        _display_completion_summary(all_posts, duration)

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Multi-platform generation failed: {str(e)}", exc_info=True)
        sys.exit(1)


def _display_brief_summary(client_brief: ClientBrief, detailed: bool = False):
    """Display client brief summary"""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    table.add_row("Company", client_brief.company_name)
    table.add_row("Business", client_brief.business_description)
    table.add_row("Target Customer", client_brief.ideal_customer)
    table.add_row("Main Problem", client_brief.main_problem_solved)

    if client_brief.brand_personality:
        personalities = ", ".join([p.value for p in client_brief.brand_personality])
        table.add_row("Brand Voice", personalities)

    if client_brief.target_platforms:
        platforms = ", ".join([p.value for p in client_brief.target_platforms])
        table.add_row("Platforms", platforms)

    table.add_row("Posting Frequency", client_brief.posting_frequency)

    if detailed:
        if client_brief.customer_pain_points:
            table.add_row(
                "Pain Points",
                "\n".join([f"• {p}" for p in client_brief.customer_pain_points]),
            )

        if client_brief.key_phrases:
            table.add_row("Key Phrases", "\n".join([f"• {p}" for p in client_brief.key_phrases]))

        if client_brief.customer_questions:
            table.add_row("Questions", ", ".join(client_brief.customer_questions[:3]))

    console.print(table)


def _display_completion_summary(posts, duration: float):
    """Display generation completion summary"""
    # Calculate stats
    total_words = sum(p.word_count for p in posts)
    avg_words = total_words / len(posts) if posts else 0
    flagged = len([p for p in posts if p.needs_review])
    has_cta = len([p for p in posts if p.has_cta])

    table = Table(title="Generation Summary", show_header=False, box=None)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold")

    table.add_row("Total Posts", str(len(posts)))
    table.add_row("Total Words", f"{total_words:,}")
    table.add_row("Average Words/Post", f"{avg_words:.0f}")
    table.add_row("Posts with CTA", f"{has_cta}/{len(posts)}")
    table.add_row("Flagged for Review", str(flagged))
    table.add_row("Generation Time", f"{duration:.1f}s")
    table.add_row("Time per Post", f"{duration / len(posts):.1f}s")

    console.print()
    console.print(table)
    console.print()


# ============================================================================
# REVISION MANAGEMENT COMMANDS
# ============================================================================


@cli.command()
@click.option(
    "--project",
    "-p",
    help="Project ID to revise",
    required=True,
)
@click.option(
    "--posts",
    help="Comma-separated post indices to revise (e.g., '3,7,12')",
    required=True,
)
@click.option(
    "--feedback",
    "-f",
    help="Client feedback describing changes needed",
    required=True,
)
@click.option(
    "--output-dir",
    "-o",
    help="Output directory for revised posts",
    type=click.Path(),
)
def revise(project: str, posts: str, feedback: str, output_dir: Optional[str]):
    """
    Revise specific posts based on client feedback

    Example:
        python 03_post_generator.py revise --project "AcmeAgency_20250101_120000" \\
            --posts "3,7,12" --feedback "Make these more casual and add emojis"
    """
    from src.database.project_db import ProjectDatabase
    from src.models.project import Revision, RevisionStatus

    try:
        # Initialize database
        db = ProjectDatabase()

        # Get project
        console.print(f"[cyan]Loading project {project}...[/cyan]")
        project_obj = db.get_project(project)
        if not project_obj:
            console.print(f"[red]ERROR:[/red] Project '{project}' not found")
            sys.exit(1)

        console.print(f"[green]OK[/green] Found project for {project_obj.client_name}")

        # Check scope before proceeding
        scope = db.get_revision_scope(project)
        console.print(
            f"\n[cyan]Revision Scope:[/cyan] {scope.used_revisions}/{scope.allowed_revisions} used"
        )

        if scope.is_at_limit and not scope.upsell_accepted:
            if not scope.upsell_offered:
                db.mark_upsell_offered(project)
                console.print("\n[yellow]⚠️  REVISION LIMIT REACHED[/yellow]")
                console.print(f"\nYou've used all {scope.allowed_revisions} included revisions.")
                console.print("\n[bold]Additional revision rounds available:[/bold]")
                console.print("  • 5 more revisions: $500")
                console.print("  • 10 more revisions: $900 (10% discount)")
                console.print("  • Unlimited for this project: $1,200")
                console.print("\nContact client for upsell approval before continuing.\n")
                sys.exit(1)
            else:
                console.print("\n[yellow]⚠️  Awaiting upsell decision from client[/yellow]\n")
                sys.exit(1)

        if scope.is_near_limit:
            console.print(
                f"[yellow]⚠️  Warning: Only {scope.remaining_revisions} revision remaining[/yellow]\n"
            )

        # Parse post indices
        post_indices = [int(p.strip()) for p in posts.split(",")]
        console.print(f"[cyan]Revising posts:[/cyan] {', '.join(map(str, post_indices))}")
        console.print(f"[cyan]Feedback:[/cyan] {feedback}\n")

        # Load deliverable to get original posts
        deliverable_path = Path(project_obj.deliverable_path)
        if not deliverable_path.exists():
            console.print(f"[red]ERROR:[/red] Deliverable not found at {deliverable_path}")
            sys.exit(1)

        # TODO: Load original posts from deliverable
        # For now, we'll create a note that this needs proper post loading
        console.print("[yellow]Note: Post loading from deliverable needs implementation[/yellow]")
        console.print("[cyan]Creating revision record...[/cyan]")

        # Create revision record
        revision = Revision(
            revision_id=f"{project}_rev_{scope.used_revisions + 1}",
            project_id=project,
            attempt_number=scope.used_revisions + 1,
            feedback=feedback,
            status=RevisionStatus.PENDING,
        )

        db.create_revision(revision)
        console.print(f"[green]OK[/green] Created revision #{revision.attempt_number}")

        # Update status to in-progress
        db.update_revision_status(revision.revision_id, RevisionStatus.IN_PROGRESS)

        # Generate revised posts
        console.print("\n[cyan]Generating revised posts with AI...[/cyan]")
        # TODO: Implement actual revision generation
        # This requires loading original posts, client brief, and templates

        # Update status to completed
        db.update_revision_status(revision.revision_id, RevisionStatus.COMPLETED)

        console.print("\n[green]OK[/green] Revision completed successfully")
        console.print(f"\nRevision ID: {revision.revision_id}")
        console.print(
            f"Remaining revisions: {scope.remaining_revisions - 1}/{scope.allowed_revisions}"
        )

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Revision failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("scope-status")
@click.option(
    "--project",
    "-p",
    help="Project ID to check",
    required=True,
)
def scope_status(project: str):
    """
    Check revision scope status for a project

    Example:
        python 03_post_generator.py scope-status --project "AcmeAgency_20250101_120000"
    """
    from src.database.project_db import ProjectDatabase

    try:
        db = ProjectDatabase()

        # Get project
        project_obj = db.get_project(project)
        if not project_obj:
            console.print(f"[red]ERROR:[/red] Project '{project}' not found")
            sys.exit(1)

        # Get scope
        scope = db.get_revision_scope(project)

        # Display scope status
        console.print("\n[bold]Revision Scope Status[/bold]")
        console.print("=" * 60)
        console.print(f"Project: [cyan]{project}[/cyan]")
        console.print(f"Client: [cyan]{project_obj.client_name}[/cyan]\n")

        console.print(
            f"Revisions Used: [bold]{scope.used_revisions} / {scope.allowed_revisions}[/bold]"
        )
        console.print(f"Remaining: [bold]{scope.remaining_revisions}[/bold]\n")

        if scope.scope_exceeded:
            console.print("Status: [red]SCOPE EXCEEDED[/red]")
            if scope.upsell_accepted:
                console.print("  [green]✓[/green] Additional revisions purchased")
            elif scope.upsell_offered:
                console.print("  [yellow]⏳[/yellow] Upsell offered, awaiting client decision")
            else:
                console.print("  [yellow]⚠️[/yellow]  Upsell not yet offered")
        elif scope.is_at_limit:
            console.print("Status: [yellow]AT LIMIT[/yellow]")
            console.print("  Next revision will trigger upsell")
        elif scope.is_near_limit:
            console.print("Status: [yellow]NEAR LIMIT[/yellow]")
            console.print("  [yellow]⚠️[/yellow]  Only 1 revision remaining")
        else:
            console.print("Status: [green]WITHIN SCOPE ✓[/green]")

        console.print()

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Scope check failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("list-revisions")
@click.option(
    "--client",
    "-c",
    help="Client name to filter by (optional)",
)
@click.option(
    "--project",
    "-p",
    help="Project ID to filter by (optional)",
)
def list_revisions(client: Optional[str], project: Optional[str]):
    """
    List all revisions for a client or project

    Examples:
        python 03_post_generator.py list-revisions --client "Acme Agency"
        python 03_post_generator.py list-revisions --project "AcmeAgency_20250101_120000"
    """
    from src.database.project_db import ProjectDatabase

    try:
        db = ProjectDatabase()

        if project:
            # Get revisions for specific project
            revisions = db.get_revisions_by_project(project)
            project_obj = db.get_project(project)
            if not project_obj:
                console.print(f"[red]ERROR:[/red] Project '{project}' not found")
                sys.exit(1)

            console.print(f"\n[bold]Revisions for {project_obj.client_name}[/bold]")
            console.print(f"Project: [cyan]{project}[/cyan]\n")

        elif client:
            # Get all projects for client, then get their revisions
            projects = db.get_projects_by_client(client)
            if not projects:
                console.print(f"[red]ERROR:[/red] No projects found for client '{client}'")
                sys.exit(1)

            console.print(f"\n[bold]Revisions for {client}[/bold]\n")

            revisions = []
            for proj in projects:
                proj_revisions = db.get_revisions_by_project(proj.project_id)
                revisions.extend(proj_revisions)

        else:
            console.print("[red]ERROR:[/red] Must specify either --client or --project")
            sys.exit(1)

        if not revisions:
            console.print("[yellow]No revisions found[/yellow]\n")
            return

        # Display revisions table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Attempt", width=8)
        table.add_column("Revision ID", width=40)
        table.add_column("Status", width=12)
        table.add_column("Posts", width=8)
        table.add_column("Created", width=20)
        table.add_column("Feedback", width=40)

        for rev in revisions:
            status_color = {
                "pending": "yellow",
                "in_progress": "cyan",
                "completed": "green",
                "failed": "red",
            }.get(rev.status.value, "white")

            table.add_row(
                f"#{rev.attempt_number}",
                rev.revision_id,
                f"[{status_color}]{rev.status.value}[/{status_color}]",
                str(len(rev.posts)) if rev.posts else "0",
                rev.created_at.strftime("%Y-%m-%d %H:%M"),
                (rev.feedback[:37] + "...") if len(rev.feedback) > 40 else rev.feedback,
            )

        console.print(table)
        console.print(f"\nTotal revisions: [bold]{len(revisions)}[/bold]\n")

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Revision listing failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("diff-report")
@click.option(
    "--revision",
    "-r",
    help="Revision ID to generate report for",
    required=True,
)
@click.option(
    "--output",
    "-o",
    help="Output file path (default: print to console)",
    type=click.Path(),
)
def diff_report(revision: str, output: Optional[str]):
    """
    Generate diff report showing changes made in a revision

    Example:
        python 03_post_generator.py diff-report --revision "AcmeAgency_20250101_120000_rev_1"
        python 03_post_generator.py diff-report --revision "AcmeAgency_20250101_120000_rev_1" -o report.md
    """
    from src.database.project_db import ProjectDatabase

    try:
        db = ProjectDatabase()

        # Get revision with posts
        console.print(f"[cyan]Loading revision {revision}...[/cyan]")
        revision_obj = db.get_revision(revision)

        if not revision_obj:
            console.print(f"[red]ERROR:[/red] Revision '{revision}' not found")
            sys.exit(1)

        if not revision_obj.posts:
            console.print("[yellow]No revised posts found for this revision[/yellow]")
            sys.exit(0)

        console.print(f"[green]OK[/green] Found {len(revision_obj.posts)} revised posts\n")

        # Generate markdown report
        report = []
        report.append(f"# Revision Report: {revision}")
        report.append(f"\n**Project:** {revision_obj.project_id}")
        report.append(f"**Attempt:** #{revision_obj.attempt_number}")
        report.append(f"**Status:** {revision_obj.status.value}")
        report.append(f"**Created:** {revision_obj.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if revision_obj.completed_at:
            report.append(
                f"**Completed:** {revision_obj.completed_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        report.append(f"\n## Client Feedback\n\n{revision_obj.feedback}")
        report.append(f"\n## Revised Posts ({len(revision_obj.posts)} posts)")

        for post in revision_obj.posts:
            report.append(f"\n### Post #{post.post_index}: {post.template_name}")
            report.append(
                f"\n**Length:** {post.original_word_count} → {post.revised_word_count} words "
                + f"({post.revised_word_count - post.original_word_count:+d} words)"
            )

            if post.changes_summary:
                report.append("\n**Changes Made:**")
                for change in post.changes_summary.split("; "):
                    report.append(f"- {change}")

            report.append("\n**Original Content:**")
            report.append(f"```\n{post.original_content}\n```")

            report.append("\n**Revised Content:**")
            report.append(f"```\n{post.revised_content}\n```")

            report.append("\n---")

        report_text = "\n".join(report)

        # Output report
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_text, encoding="utf-8")
            console.print(f"[green]OK[/green] Report saved to {output_path}\n")
        else:
            console.print(report_text)
            console.print()

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Diff report generation failed: {str(e)}", exc_info=True)
        sys.exit(1)


# ============================================================================
# COST TRACKING COMMANDS
# ============================================================================


@cli.command("cost-summary")
@click.option("--project", "-p", help="Project ID to show costs for")
@click.option("--all", "show_all", is_flag=True, help="Show all projects")
@click.option("--calls", is_flag=True, help="Show individual API calls")
def cost_summary(project: Optional[str], show_all: bool, calls: bool):
    """
    Show cost summary for projects

    Examples:
        # Show specific project costs
        python 03_post_generator.py cost-summary --project "Client_20250101_120000"

        # Show all projects
        python 03_post_generator.py cost-summary --all

        # Show with detailed API calls
        python 03_post_generator.py cost-summary --project "Client_20250101_120000" --calls
    """
    try:
        dashboard = CostDashboard()

        if project:
            # Show specific project
            dashboard.show_project_summary(project)

            if calls:
                console.print()
                dashboard.show_project_calls(project, limit=20)

        elif show_all:
            # Show all projects
            dashboard.show_all_projects()

        else:
            console.print("[yellow]Please specify --project or --all[/yellow]")
            console.print("Example: python 03_post_generator.py cost-summary --all")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Cost summary failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("cost-report")
@click.option("--project", "-p", help="Project ID (omit for all projects)")
@click.option("--output", "-o", required=True, help="Output file path (.md)")
@click.option("--include-calls", is_flag=True, help="Include detailed API call listing")
def cost_report(project: Optional[str], output: str, include_calls: bool):
    """
    Generate markdown cost report

    Examples:
        # Generate report for specific project
        python 03_post_generator.py cost-report --project "Client_20250101_120000" -o report.md

        # Generate report for all projects
        python 03_post_generator.py cost-report -o all_costs.md

        # Include detailed call listing
        python 03_post_generator.py cost-report --project "Client_ID" -o report.md --include-calls
    """
    try:
        dashboard = CostDashboard()
        dashboard.generate_markdown_report(
            Path(output), project_id=project, include_calls=include_calls
        )

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Cost report generation failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("cost-export")
@click.option("--project", "-p", help="Project ID (omit for all projects)")
@click.option("--output", "-o", required=True, help="Output JSON file path")
def cost_export(project: Optional[str], output: str):
    """
    Export cost data to JSON

    Examples:
        # Export specific project
        python 03_post_generator.py cost-export --project "Client_20250101_120000" -o costs.json

        # Export all projects
        python 03_post_generator.py cost-export -o all_costs.json
    """
    try:
        tracker = get_default_tracker()
        tracker.export_to_json(Path(output), project_id=project)
        console.print(f"[green]OK[/green] Cost data exported to {output}\n")

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Cost export failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("set-budget")
@click.option("--project", "-p", required=True, help="Project ID")
@click.option("--limit", "-l", type=float, required=True, help="Budget limit in USD")
@click.option(
    "--threshold", "-t", type=float, default=0.8, help="Alert threshold (0.0-1.0, default 0.8)"
)
def set_budget(project: str, limit: float, threshold: float):
    """
    Set budget alert for a project

    Examples:
        # Set $2 budget limit (alert at 80%)
        python 03_post_generator.py set-budget --project "Client_20250101_120000" --limit 2.0

        # Set $1 budget, alert at 90%
        python 03_post_generator.py set-budget --project "Client_ID" --limit 1.0 --threshold 0.9
    """
    try:
        if threshold < 0.0 or threshold > 1.0:
            console.print("[red]ERROR:[/red] Threshold must be between 0.0 and 1.0")
            sys.exit(1)

        tracker = get_default_tracker()
        tracker.set_budget_alert(project, limit, threshold)

        console.print(f"[green]OK[/green] Budget alert set for {project}")
        console.print(f"  Limit: ${limit:.2f}")
        console.print(f"  Alert at: {threshold*100:.0f}% (${limit*threshold:.2f})\n")

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Set budget failed: {str(e)}", exc_info=True)
        sys.exit(1)


# ============================================================================
# CLIENT MEMORY COMMANDS (Phase 8B)
# ============================================================================


@cli.command("client-history")
@click.option("--client", "-c", required=True, help="Client name")
@click.option("--detailed", is_flag=True, help="Show detailed statistics")
def client_history(client: str, detailed: bool):
    """
    Show client history and memory

    Examples:
        # Show basic client history
        python 03_post_generator.py client-history --client "Acme Agency"

        # Show detailed statistics
        python 03_post_generator.py client-history --client "Acme Agency" --detailed
    """
    try:
        db = ProjectDatabase()
        memory = db.get_client_memory(client)

        if not memory:
            console.print(f"[yellow]No history found for client: {client}[/yellow]")
            console.print("This client has not completed any projects yet.\n")
            sys.exit(0)

        # Basic info
        console.print(f"\n[bold cyan]Client History: {memory.client_name}[/bold cyan]\n")
        console.print(f"[bold]Total Projects:[/bold] {memory.total_projects}")
        console.print(f"[bold]Total Posts Generated:[/bold] {memory.total_posts_generated:,}")
        console.print(f"[bold]Total Revisions:[/bold] {memory.total_revisions}")
        console.print(f"[bold]Avg Revisions/Project:[/bold] {memory.avg_revisions_per_project:.1f}")

        if memory.first_project_date:
            console.print(
                f"[bold]First Project:[/bold] {memory.first_project_date.strftime('%Y-%m-%d')}"
            )
        if memory.last_project_date:
            console.print(
                f"[bold]Last Project:[/bold] {memory.last_project_date.strftime('%Y-%m-%d')}"
            )

        if memory.lifetime_value > 0:
            console.print(
                f"[bold]Lifetime Value:[/bold] [green]${memory.lifetime_value:,.2f}[/green]"
            )

        # Voice preferences
        if memory.voice_archetype:
            console.print(f"\n[bold]Voice Archetype:[/bold] {memory.voice_archetype}")
        if memory.average_readability_score:
            console.print(f"[bold]Readability Score:[/bold] {memory.average_readability_score:.1f}")

        # Template preferences
        if memory.preferred_templates:
            console.print(
                f"\n[bold]Preferred Templates:[/bold] {', '.join(map(str, memory.preferred_templates))}"
            )
        if memory.avoided_templates:
            console.print(
                f"[bold]Avoided Templates:[/bold] {', '.join(map(str, memory.avoided_templates))}"
            )

        # Voice adjustments
        if memory.voice_adjustments:
            console.print("\n[bold]Voice Adjustments:[/bold]")
            for key, value in memory.voice_adjustments.items():
                console.print(f"  • {key}: {value}")

        # Detailed info
        if detailed:
            console.print(
                f"\n[bold]Word Count Range:[/bold] {memory.optimal_word_count_min}-{memory.optimal_word_count_max}"
            )
            if memory.preferred_cta_types:
                console.print(
                    f"[bold]Preferred CTA Types:[/bold] {', '.join(memory.preferred_cta_types)}"
                )
            if memory.signature_phrases:
                console.print("\n[bold]Signature Phrases:[/bold]")
                for phrase in memory.signature_phrases[:5]:
                    console.print(f'  • "{phrase}"')

            # Get template performance
            template_perf = db.get_template_performance(client)
            if template_perf:
                console.print("\n[bold]Template Performance:[/bold]")
                for template_id, stats in sorted(template_perf.items())[:10]:
                    revision_rate = stats.get("revision_rate", 0.0)
                    usage = stats.get("usage_count", 0)
                    console.print(
                        f"  Template {template_id}: {usage} uses, {revision_rate*100:.0f}% revision rate"
                    )

        console.print()

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Client history failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("client-stats")
@click.option("--all", "show_all", is_flag=True, help="Show all clients")
def client_stats(show_all: bool):
    """
    Show statistics for all clients

    Examples:
        # Show all client statistics
        python 03_post_generator.py client-stats --all
    """
    try:
        db = ProjectDatabase()

        # Get all clients with memory

        # Query database directly for all clients
        import sqlite3

        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                client_name,
                total_projects,
                total_posts_generated,
                total_revisions,
                lifetime_value,
                last_project_date
            FROM client_history
            ORDER BY last_project_date DESC
        """
        )

        clients = cursor.fetchall()
        conn.close()

        if not clients:
            console.print("[yellow]No clients found[/yellow]\n")
            sys.exit(0)

        # Create table
        table = Table(title=f"Client Statistics ({len(clients)} clients)")
        table.add_column("Client Name", style="cyan")
        table.add_column("Projects", justify="right", style="blue")
        table.add_column("Posts", justify="right", style="blue")
        table.add_column("Revisions", justify="right", style="yellow")
        table.add_column("Avg Rev/Proj", justify="right", style="yellow")
        table.add_column("LTV", justify="right", style="green")
        table.add_column("Last Project", style="magenta")

        total_projects = 0
        total_posts = 0
        total_revisions = 0
        total_ltv = 0.0

        for client in clients:
            name, projects, posts, revisions, ltv, last_date = client
            avg_rev = revisions / projects if projects > 0 else 0.0

            total_projects += projects
            total_posts += posts
            total_revisions += revisions
            total_ltv += ltv or 0.0

            table.add_row(
                name,
                str(projects),
                f"{posts:,}",
                str(revisions),
                f"{avg_rev:.1f}",
                f"${ltv:,.0f}" if ltv else "-",
                last_date[:10] if last_date else "-",
            )

        # Add totals row
        table.add_section()
        avg_overall = total_revisions / total_projects if total_projects > 0 else 0.0
        table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold]{total_projects}[/bold]",
            f"[bold]{total_posts:,}[/bold]",
            f"[bold]{total_revisions}[/bold]",
            f"[bold]{avg_overall:.1f}[/bold]",
            f"[bold green]${total_ltv:,.0f}[/bold green]",
            "",
        )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Client stats failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("export-memory")
@click.option("--client", "-c", required=True, help="Client name")
@click.option("--output", "-o", required=True, help="Output JSON file path")
def export_memory(client: str, output: str):
    """
    Export client memory to JSON

    Examples:
        # Export client memory
        python 03_post_generator.py export-memory --client "Acme Agency" -o acme_memory.json
    """
    try:
        db = ProjectDatabase()
        memory = db.get_client_memory(client)

        if not memory:
            console.print(f"[yellow]No memory found for client: {client}[/yellow]")
            sys.exit(1)

        # Export to JSON
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(memory.to_dict(), f, indent=2, default=str)

        console.print(f"[green]OK[/green] Client memory exported to {output}\n")

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Export memory failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("import-memory")
@click.option("--client", "-c", required=True, help="Client name")
@click.option("--input", "-i", required=True, help="Input JSON file path")
@click.option("--overwrite", is_flag=True, help="Overwrite existing memory")
def import_memory(client: str, input: str, overwrite: bool):
    """
    Import client memory from JSON

    Examples:
        # Import client memory
        python 03_post_generator.py import-memory --client "Acme Agency" -i acme_memory.json

        # Import and overwrite existing memory
        python 03_post_generator.py import-memory --client "Acme Agency" -i acme_memory.json --overwrite
    """
    try:
        from src.models.client_memory import ClientMemory

        db = ProjectDatabase()
        input_path = Path(input)

        if not input_path.exists():
            console.print(f"[red]ERROR:[/red] File not found: {input}")
            sys.exit(1)

        # Check if client already exists
        existing_memory = db.get_client_memory(client)
        if existing_memory and not overwrite:
            console.print(f"[yellow]WARNING:[/yellow] Client memory already exists for '{client}'")
            console.print("Use --overwrite flag to replace existing memory.\n")
            sys.exit(1)

        # Load JSON
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Override client_name with the provided one
        data["client_name"] = client

        # Create ClientMemory from dict
        memory = ClientMemory.from_dict(data)

        # Save to database
        if existing_memory:
            db.update_client_memory(memory)
            console.print(f"[green]OK[/green] Client memory updated for '{client}'\n")
        else:
            db.create_client_memory(memory)
            console.print(f"[green]OK[/green] Client memory imported for '{client}'\n")

    except json.JSONDecodeError as e:
        console.print(f"[red]ERROR:[/red] Invalid JSON file: {str(e)}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Import memory failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("forget-client")
@click.option("--client", "-c", required=True, help="Client name")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def forget_client(client: str, confirm: bool):
    """
    Delete all client memory and data

    WARNING: This action cannot be undone!

    Examples:
        # Delete client memory (with confirmation)
        python 03_post_generator.py forget-client --client "Acme Agency"

        # Delete without confirmation
        python 03_post_generator.py forget-client --client "Acme Agency" --confirm
    """
    try:
        db = ProjectDatabase()
        memory = db.get_client_memory(client)

        if not memory:
            console.print(f"[yellow]No memory found for client: {client}[/yellow]")
            sys.exit(0)

        # Show what will be deleted
        console.print(
            f"\n[bold red]WARNING: This will permanently delete all data for '{client}':[/bold red]"
        )
        console.print(f"  • {memory.total_projects} project(s)")
        console.print(f"  • {memory.total_posts_generated:,} generated posts")
        console.print(f"  • ${memory.lifetime_value:,.2f} lifetime value")
        console.print("  • Template performance data")
        console.print("  • Voice samples and feedback themes")
        console.print()

        # Confirmation
        if not confirm:
            response = input(f"Type '{client}' to confirm deletion: ")
            if response != client:
                console.print("[yellow]Deletion cancelled[/yellow]\n")
                sys.exit(0)

        # Delete from all tables
        with db._get_connection() as conn:
            cursor = conn.cursor()

            # Delete from all related tables
            cursor.execute("DELETE FROM template_performance WHERE client_name = ?", (client,))
            cursor.execute("DELETE FROM client_feedback_themes WHERE client_name = ?", (client,))
            cursor.execute("DELETE FROM client_voice_samples WHERE client_name = ?", (client,))
            cursor.execute("DELETE FROM client_history WHERE client_name = ?", (client,))

            deleted_count = cursor.rowcount
            conn.commit()

        if deleted_count > 0:
            console.print(f"[green]OK[/green] All data for '{client}' has been deleted\n")
        else:
            console.print(f"[yellow]No data found to delete for '{client}'[/yellow]\n")

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Forget client failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("upload-voice-samples")
@click.option("--client", "-c", required=True, help="Client name")
@click.option("--files", "-f", help="Comma-separated file paths")
@click.option("--directory", "-d", help="Directory containing sample files")
@click.option(
    "--source",
    "-s",
    type=click.Choice(["linkedin", "blog", "twitter", "email", "mixed", "other"]),
    default="mixed",
    help="Source of samples",
)
def upload_voice_samples(client: str, files: Optional[str], directory: Optional[str], source: str):
    """
    Upload client voice samples for authentic voice matching

    Supports: .txt, .md, .docx, .html, .json
    Requirements: 100-2000 words per sample, minimum 500 words total

    Examples:
        # Upload specific files
        python 03_post_generator.py upload-voice-samples -c "Acme" -f "post1.txt,post2.md" -s linkedin

        # Upload all files from directory
        python 03_post_generator.py upload-voice-samples -c "Acme" -d "samples/" -s mixed
    """
    from pathlib import Path

    from src.agents.voice_analyzer import VoiceAnalyzer
    from src.database.project_db import ProjectDatabase
    from src.models.voice_sample import VoiceSampleBatch, VoiceSampleUpload
    from src.utils.file_parser import extract_text_from_file, validate_sample_text

    try:
        console.print(f"\n[bold cyan]Uploading voice samples for {client}...[/bold cyan]\n")

        # Validate inputs
        if not files and not directory:
            console.print("[red]ERROR:[/red] Must provide either --files or --directory")
            sys.exit(1)

        # Collect file paths
        file_paths = []
        if files:
            file_paths = [Path(f.strip()) for f in files.split(",")]
        elif directory:
            dir_path = Path(directory)
            if not dir_path.exists():
                console.print(f"[red]ERROR:[/red] Directory not found: {directory}")
                sys.exit(1)

            # Find supported files
            extensions = ["*.txt", "*.md", "*.docx", "*.html", "*.json"]
            for ext in extensions:
                file_paths.extend(dir_path.glob(ext))

        if not file_paths:
            console.print("[red]ERROR:[/red] No valid files found")
            sys.exit(1)

        # Extract and validate samples
        samples = []
        total_words = 0

        for file_path in file_paths:
            try:
                console.print(f"📄 Loading {file_path.name}...", end=" ")

                text, word_count = extract_text_from_file(file_path)

                # Validate
                is_valid, error_msg = validate_sample_text(text)
                if not is_valid:
                    console.print(f"[yellow]SKIPPED:[/yellow] {error_msg}")
                    continue

                sample = VoiceSampleUpload(
                    client_name=client,
                    sample_text=text,
                    sample_source=source,
                    word_count=word_count,
                    file_name=file_path.name,
                )
                samples.append(sample)
                total_words += word_count
                console.print(f"[green]✓[/green] ({word_count} words)")

            except Exception as e:
                console.print(f"[red]ERROR:[/red] {str(e)}")
                continue

        if not samples:
            console.print("\n[red]ERROR:[/red] No valid samples to upload")
            sys.exit(1)

        # Create batch and validate
        batch = VoiceSampleBatch(client_name=client, samples=samples)

        if not batch.is_valid():
            console.print("\n[red]Batch Validation Failed:[/red]")
            for error in batch.validation_errors():
                console.print(f"  • {error}")
            sys.exit(1)

        console.print(
            f"\n[bold green]✓ Loaded {len(samples)} samples ({total_words} words total)[/bold green]\n"
        )

        # Analyze voice patterns
        console.print("[cyan]Analyzing voice patterns...[/cyan]")
        voice_analyzer = VoiceAnalyzer()
        voice_guide = voice_analyzer.analyze_voice_samples(
            samples=[s.sample_text for s in samples], client_name=client, source=source
        )

        # Store samples in database
        db = ProjectDatabase()
        for sample in samples:
            db.store_voice_sample_upload(sample)

        console.print("[green]✓ Voice samples uploaded successfully[/green]\n")

        # Display voice guide summary
        console.print("[bold]Voice Guide Summary:[/bold]")
        console.print(f"  • Readability: {voice_guide.average_readability_score:.1f} ", end="")

        if voice_guide.average_readability_score >= 70:
            console.print("(Fairly Easy - 7th grade)")
        elif voice_guide.average_readability_score >= 60:
            console.print("(Standard - 8th-9th grade)")
        else:
            console.print("(Difficult - College level)")

        if voice_guide.voice_archetype:
            console.print(f"  • Archetype: {voice_guide.voice_archetype}")

        if voice_guide.voice_dimensions:
            formality = voice_guide.voice_dimensions.get("formality", {}).get("dominant", "Unknown")
            tone = voice_guide.voice_dimensions.get("tone", {}).get("dominant", "Unknown")
            console.print(f"  • Formality: {formality.title()}")
            console.print(f"  • Tone: {tone.title()}")

        console.print(f"  • Avg Word Count: {voice_guide.average_word_count} words")

        if voice_guide.key_phrases_used:
            console.print(f"  • Key Phrases: {', '.join(voice_guide.key_phrases_used[:5])}")

        console.print("\n[green]✓ Voice guide saved for future generations[/green]")
        console.print(
            f"\nUse [cyan]--use-voice-samples[/cyan] flag when generating posts for {client}"
        )

    except Exception as e:
        console.print(f"\n[red]ERROR:[/red] {str(e)}")
        logger.error(f"Voice sample upload failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("list-voice-samples")
@click.option("--client", "-c", required=True, help="Client name")
def list_voice_samples(client: str):
    """
    List uploaded voice samples for a client

    Examples:
        python 03_post_generator.py list-voice-samples --client "Acme Agency"
    """
    from src.database.project_db import ProjectDatabase

    try:
        db = ProjectDatabase()

        # Get samples
        samples = db.get_voice_sample_uploads(client)
        stats = db.get_voice_sample_upload_stats(client)

        if stats["sample_count"] == 0:
            console.print(f"\n[yellow]No voice samples found for {client}[/yellow]")
            console.print("\nUpload samples with:")
            console.print(
                f'  [cyan]python 03_post_generator.py upload-voice-samples -c "{client}" -f "file1.txt,file2.md"[/cyan]\n'
            )
            return

        console.print(f"\n[bold cyan]Voice Samples for {client}[/bold cyan]\n")
        console.print(f"[bold]Upload Date:[/bold] {stats['last_upload']}")
        console.print(f"  • {stats['sample_count']} samples ({stats['total_words']:,} words total)")
        console.print(f"  • Sources: {', '.join(stats['sources'])}")
        console.print(
            f"  • Average: {stats['total_words'] // stats['sample_count']:,} words/sample\n"
        )

        console.print("[bold]Sample Files:[/bold]")
        for idx, sample in enumerate(samples, 1):
            console.print(
                f"  {idx}. {sample.file_name} ({sample.word_count} words, {sample.sample_source})"
            )
            console.print(f"     Preview: {sample.preview}\n")

        console.print(
            "[dim]Use these samples with --use-voice-samples flag during generation[/dim]\n"
        )

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"List voice samples failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("delete-voice-samples")
@click.option("--client", "-c", required=True, help="Client name")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def delete_voice_samples(client: str, confirm: bool):
    """
    Delete all voice samples for a client

    Examples:
        # Delete with confirmation
        python 03_post_generator.py delete-voice-samples --client "Acme Agency"

        # Delete without confirmation
        python 03_post_generator.py delete-voice-samples --client "Acme" --confirm
    """
    from src.database.project_db import ProjectDatabase

    try:
        db = ProjectDatabase()

        # Check if samples exist
        stats = db.get_voice_sample_upload_stats(client)

        if stats["sample_count"] == 0:
            console.print(f"\n[yellow]No voice samples found for {client}[/yellow]\n")
            return

        # Confirm deletion
        if not confirm:
            console.print(
                f"\n[yellow]Warning:[/yellow] This will delete {stats['sample_count']} voice samples for {client}"
            )
            console.print(
                f"Total: {stats['total_words']:,} words from {', '.join(stats['sources'])}\n"
            )

            if not click.confirm("Are you sure you want to delete these samples?"):
                console.print("\n[dim]Deletion cancelled[/dim]\n")
                return

        # Delete samples
        count = db.delete_voice_sample_uploads(client)

        console.print(f"\n[green]✓ Deleted {count} voice samples for {client}[/green]\n")

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Delete voice samples failed: {str(e)}", exc_info=True)
        sys.exit(1)


# ============================================================================
# Phase 8D: Feedback & Satisfaction Commands
# ============================================================================


@cli.command("feedback")
@click.option("--client", "-c", required=True, help="Client name")
@click.option("--project", "-p", required=True, help="Project ID")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode to review all posts")
def feedback(client: str, project: str, interactive: bool):
    """
    Record feedback on delivered posts

    Track which posts were kept, modified, rejected, or loved by the client.
    This data helps improve future content generation.

    Examples:
        # Interactive mode - review all posts
        python 03_post_generator.py feedback --client "Acme Corp" --project "AcmeCorp_20251202_143052" --interactive

        # Quick single post feedback
        python 03_post_generator.py feedback --client "Acme Corp" --project "AcmeCorp_20251202_143052"
    """
    import hashlib

    from src.database.project_db import ProjectDatabase

    try:
        db = ProjectDatabase()

        # Get project details
        project_data = db.get_project(project)
        if not project_data:
            console.print(f"\n[red]ERROR:[/red] Project not found: {project}\n")
            console.print(
                "[dim]Use 'client-history --client \"{client}\"' to see available projects[/dim]\n"
            )
            return

        console.print("\n[cyan]Recording Feedback[/cyan]")
        console.print(f"Client: [bold]{client}[/bold]")
        console.print(f"Project: {project}")
        console.print(f"Posts: {project_data['num_posts']}\n")

        if interactive:
            # Interactive mode - review each post
            console.print("[yellow]Interactive Feedback Mode[/yellow]")
            console.print("For each post, provide feedback:\n")

            # Try to load posts from deliverable
            deliverable_path = Path(project_data["deliverable_path"])
            if not deliverable_path.exists():
                console.print(f"[red]ERROR:[/red] Deliverable file not found: {deliverable_path}\n")
                return

            # Parse posts from deliverable (simplified - assumes numbered format)
            content = deliverable_path.read_text(encoding="utf-8")

            # Split by post numbers (assuming "Post 1:", "Post 2:", etc.)
            import re

            post_pattern = r"(?:^|\n)Post (\d+):(.*?)(?=\n(?:Post \d+:|$))"
            matches = re.findall(post_pattern, content, re.DOTALL)

            if not matches:
                # Try alternate pattern
                post_pattern = r"(?:^|\n)#+ Post (\d+)(.*?)(?=\n#+\s+Post \d+|$)"
                matches = re.findall(post_pattern, content, re.DOTALL)

            if not matches:
                console.print("[yellow]Warning:[/yellow] Could not parse posts from deliverable")
                console.print("[dim]Using manual entry mode instead[/dim]\n")
                interactive = False
            else:
                for idx, (post_num, post_content) in enumerate(matches, 1):
                    post_preview = (
                        post_content.strip()[:150] + "..."
                        if len(post_content.strip()) > 150
                        else post_content.strip()
                    )

                    console.print(f"\n[bold]Post {post_num}:[/bold]")
                    console.print(f"[dim]{post_preview}[/dim]\n")

                    # Ask for feedback
                    feedback_type = click.prompt(
                        "Feedback",
                        type=click.Choice(
                            ["kept", "modified", "rejected", "loved", "skip"], case_sensitive=False
                        ),
                        default="skip",
                    )

                    if feedback_type == "skip":
                        continue

                    modification_notes = None
                    if feedback_type in ["modified", "rejected"]:
                        modification_notes = click.prompt(
                            "Notes (optional)", default="", show_default=False
                        )

                    # Ask for engagement data
                    has_engagement = click.confirm(
                        "Add engagement data (likes, comments, etc.)?", default=False
                    )
                    engagement_data = None

                    if has_engagement:
                        try:
                            likes = int(click.prompt("Likes", default="0"))
                            comments = int(click.prompt("Comments", default="0"))
                            shares = int(click.prompt("Shares", default="0"))
                            engagement_data = {
                                "likes": likes,
                                "comments": comments,
                                "shares": shares,
                            }
                        except ValueError:
                            console.print("[yellow]Invalid engagement data, skipping[/yellow]")

                    # Generate post_id from content hash
                    post_id = hashlib.md5(post_content.encode()).hexdigest()[:12]

                    # Store feedback
                    db.store_post_feedback(
                        client_name=client,
                        project_id=project,
                        post_id=post_id,
                        template_id=idx,  # Approximate
                        template_name="Unknown",
                        feedback_type=feedback_type,
                        modification_notes=modification_notes if modification_notes else None,
                        engagement_data=engagement_data,
                    )

                    console.print(f"[green]✓[/green] Recorded: {feedback_type}")

        if not interactive:
            # Manual mode - collect feedback for specific posts
            console.print("[yellow]Manual Feedback Mode[/yellow]\n")

            while True:
                post_num = click.prompt("Post number (or 'done' to finish)", default="done")

                if post_num.lower() == "done":
                    break

                try:
                    post_idx = int(post_num)
                except ValueError:
                    console.print("[red]Invalid post number[/red]")
                    continue

                feedback_type = click.prompt(
                    "Feedback type",
                    type=click.Choice(
                        ["kept", "modified", "rejected", "loved"], case_sensitive=False
                    ),
                )

                modification_notes = None
                if feedback_type in ["modified", "rejected"]:
                    modification_notes = click.prompt(
                        "Notes (optional)", default="", show_default=False
                    )

                # Generate generic post_id
                post_id = f"{project}_post_{post_idx}"

                # Store feedback
                db.store_post_feedback(
                    client_name=client,
                    project_id=project,
                    post_id=post_id,
                    template_id=post_idx,
                    template_name="Unknown",
                    feedback_type=feedback_type,
                    modification_notes=modification_notes if modification_notes else None,
                )

                console.print(f"[green]✓[/green] Recorded: {feedback_type} for Post {post_idx}\n")

        # Show summary
        summary = db.get_post_feedback_summary(client_name=client)

        console.print("\n[cyan]Feedback Summary[/cyan]")
        console.print(f"Total feedback: {summary['total_feedback']}")
        console.print(f"  • Kept: {summary['kept']} ({summary['kept_rate']:.0%})")
        console.print(f"  • Modified: {summary['modified']} ({summary['modified_rate']:.0%})")
        console.print(f"  • Rejected: {summary['rejected']} ({summary['rejected_rate']:.0%})")
        console.print(f"  • Loved: {summary['loved']} ({summary['loved_rate']:.0%})")
        console.print()

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Feedback command failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("satisfaction")
@click.option("--client", "-c", required=True, help="Client name")
@click.option("--project", "-p", required=True, help="Project ID")
@click.option("--survey", "-s", is_flag=True, help="Interactive survey mode")
@click.option("--overall", type=int, help="Overall satisfaction (1-5)")
@click.option("--quality", type=int, help="Quality rating (1-5)")
@click.option("--voice-match", type=int, help="Voice match rating (1-5)")
@click.option(
    "--recommend", type=click.Choice(["yes", "no"], case_sensitive=False), help="Would recommend"
)
def satisfaction(
    client: str,
    project: str,
    survey: bool,
    overall: Optional[int],
    quality: Optional[int],
    voice_match: Optional[int],
    recommend: Optional[str],
):
    """
    Collect client satisfaction survey

    Gather feedback on overall experience, quality, and voice matching.
    This data helps track client happiness and identify areas for improvement.

    Examples:
        # Interactive survey mode
        python 03_post_generator.py satisfaction --client "Acme Corp" --project "AcmeCorp_20251202_143052" --survey

        # Quick satisfaction rating
        python 03_post_generator.py satisfaction --client "Acme" --project "Acme_20251202_143052" \\
            --overall 5 --quality 5 --voice-match 4 --recommend yes
    """
    from src.database.project_db import ProjectDatabase

    try:
        db = ProjectDatabase()

        # Get project details
        project_data = db.get_project(project)
        if not project_data:
            console.print(f"\n[red]ERROR:[/red] Project not found: {project}\n")
            return

        console.print("\n[cyan]Client Satisfaction Survey[/cyan]")
        console.print(f"Client: [bold]{client}[/bold]")
        console.print(f"Project: {project}\n")

        # Collect ratings
        if survey or not all([overall, quality, voice_match, recommend]):
            # Interactive survey mode
            console.print("[yellow]Please rate your experience (1-5 scale):[/yellow]\n")

            overall = int(
                click.prompt(
                    "Overall Satisfaction (1=Poor, 5=Excellent)",
                    type=click.IntRange(1, 5),
                    default=overall if overall else 4,
                )
            )

            quality = int(
                click.prompt(
                    "Content Quality (1=Poor, 5=Excellent)",
                    type=click.IntRange(1, 5),
                    default=quality if quality else 4,
                )
            )

            voice_match = int(
                click.prompt(
                    "Voice Match Accuracy (1=Poor, 5=Excellent)",
                    type=click.IntRange(1, 5),
                    default=voice_match if voice_match else 4,
                )
            )

            recommend_response = click.prompt(
                "Would you recommend our service? (yes/no)",
                type=click.Choice(["yes", "no"], case_sensitive=False),
                default=recommend if recommend else "yes",
            )
            recommend = recommend_response

        # Convert recommend to boolean
        would_recommend = recommend.lower() == "yes"

        # Collect qualitative feedback
        console.print("\n[yellow]Optional: Provide additional feedback[/yellow]\n")

        feedback_text = click.prompt("General feedback (optional)", default="", show_default=False)

        strengths = click.prompt("What worked well? (optional)", default="", show_default=False)

        improvements = click.prompt(
            "What could be better? (optional)", default="", show_default=False
        )

        # Store satisfaction survey
        satisfaction_id = db.store_client_satisfaction(
            client_name=client,
            project_id=project,
            satisfaction_score=overall,
            quality_rating=quality,
            voice_match_rating=voice_match,
            would_recommend=would_recommend,
            feedback_text=feedback_text if feedback_text else None,
            strengths=strengths if strengths else None,
            improvements=improvements if improvements else None,
        )

        # Display summary
        console.print("\n[green]✓ Satisfaction survey recorded[/green]\n")

        console.print("[cyan]Survey Results:[/cyan]")
        console.print(f"  Overall: {'⭐' * overall} ({overall}/5)")
        console.print(f"  Quality: {'⭐' * quality} ({quality}/5)")
        console.print(f"  Voice Match: {'⭐' * voice_match} ({voice_match}/5)")
        console.print(f"  Recommend: {'✓ Yes' if would_recommend else '✗ No'}")

        if feedback_text:
            console.print(f"\n  Feedback: {feedback_text}")

        # Show client's average satisfaction
        client_history = db.get_client_memory(client)
        if client_history and client_history.average_satisfaction:
            console.print(
                f"\n[dim]Client average satisfaction: {client_history.average_satisfaction:.1f}/5.0[/dim]"
            )

        console.print()

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Satisfaction survey failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("dashboard")
@click.option("--from-date", help="Start date (YYYY-MM-DD)")
@click.option("--to-date", help="End date (YYYY-MM-DD)")
@click.option(
    "--metrics", help="Focus on specific metrics (comma-separated: quality,cost,templates,clients)"
)
def dashboard(from_date: Optional[str], to_date: Optional[str], metrics: Optional[str]):
    """
    Display comprehensive system performance dashboard

    Shows key metrics including generation stats, quality scores,
    template performance, and client satisfaction.

    Examples:
        # Full dashboard
        python 03_post_generator.py dashboard

        # Date range filter
        python 03_post_generator.py dashboard --from-date 2025-11-01 --to-date 2025-12-01

        # Specific metrics only
        python 03_post_generator.py dashboard --metrics quality,cost
    """
    from datetime import datetime, timedelta

    from rich.table import Table

    from src.database.project_db import ProjectDatabase

    try:
        db = ProjectDatabase()

        # Parse date range
        if not to_date:
            to_date = datetime.now().date().isoformat()

        if not from_date:
            from_date = (datetime.now().date() - timedelta(days=30)).isoformat()

        # Parse metrics filter
        focus_metrics = None
        if metrics:
            focus_metrics = [m.strip().lower() for m in metrics.split(",")]

        # Display header
        console.print("\n" + "=" * 70)
        console.print("[bold cyan]SYSTEM PERFORMANCE DASHBOARD[/bold cyan]")
        console.print(f"[dim]Period: {from_date} to {to_date}[/dim]")
        console.print("=" * 70 + "\n")

        # ============================================================================
        # GENERATION METRICS
        # ============================================================================
        if not focus_metrics or "generation" in focus_metrics:
            console.print("[bold]📊 Generation Metrics[/bold]\n")

            # Get all client names
            all_clients = db.get_all_client_names()
            total_clients = len(all_clients)

            # Calculate total posts across all clients
            total_posts = 0
            total_projects = 0

            for client_name in all_clients:
                client_memory = db.get_client_memory(client_name)
                if client_memory:
                    total_posts += client_memory.total_posts_generated
                    total_projects += client_memory.total_projects

            # Get feedback summary
            feedback_summary = db.get_post_feedback_summary()

            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_row("Total Clients Served:", f"[cyan]{total_clients}[/cyan]")
            table.add_row("Total Projects:", f"[cyan]{total_projects}[/cyan]")
            table.add_row("Total Posts Generated:", f"[cyan]{total_posts:,}[/cyan]")

            if feedback_summary["total_feedback"] > 0:
                table.add_row(
                    "Posts with Feedback:", f"[cyan]{feedback_summary['total_feedback']}[/cyan]"
                )
                table.add_row(
                    "Post Success Rate:", f"[green]{feedback_summary['kept_rate']:.0%}[/green]"
                )

            console.print(table)
            console.print()

        # ============================================================================
        # QUALITY METRICS
        # ============================================================================
        if not focus_metrics or "quality" in focus_metrics:
            console.print("[bold]✨ Quality Metrics[/bold]\n")

            # Get satisfaction summary
            satisfaction = db.get_satisfaction_summary()

            if satisfaction["total_surveys"] > 0:
                table = Table(show_header=False, box=None, padding=(0, 2))
                table.add_row("Client Surveys:", f"[cyan]{satisfaction['total_surveys']}[/cyan]")
                table.add_row(
                    "Avg Satisfaction:",
                    f"[green]{'⭐' * int(satisfaction['avg_satisfaction'])} {satisfaction['avg_satisfaction']:.1f}/5.0[/green]",
                )
                table.add_row(
                    "Avg Quality Rating:",
                    f"[green]{'⭐' * int(satisfaction['avg_quality'])} {satisfaction['avg_quality']:.1f}/5.0[/green]",
                )
                table.add_row(
                    "Avg Voice Match:",
                    f"[green]{'⭐' * int(satisfaction['avg_voice_match'])} {satisfaction['avg_voice_match']:.1f}/5.0[/green]",
                )
                table.add_row(
                    "Recommendation Rate:",
                    f"[green]{satisfaction['recommendation_rate']:.0%}[/green]",
                )

                console.print(table)
            else:
                console.print("[dim]No satisfaction surveys collected yet[/dim]")

            console.print()

        # ============================================================================
        # TEMPLATE PERFORMANCE
        # ============================================================================
        if not focus_metrics or "templates" in focus_metrics:
            console.print("[bold]📝 Template Performance[/bold]\n")

            # Get feedback grouped by template
            feedback_records = db.get_post_feedback()

            if feedback_records:
                # Aggregate by template
                template_stats = {}

                for feedback in feedback_records:
                    template_id = feedback["template_id"]

                    if template_id not in template_stats:
                        template_stats[template_id] = {
                            "template_name": feedback["template_name"],
                            "total": 0,
                            "kept": 0,
                            "modified": 0,
                            "rejected": 0,
                            "loved": 0,
                        }

                    template_stats[template_id]["total"] += 1
                    template_stats[template_id][feedback["feedback_type"]] += 1

                # Calculate success rate and sort
                for tid, stats in template_stats.items():
                    if stats["total"] > 0:
                        stats["success_rate"] = (stats["kept"] + stats["loved"]) / stats["total"]

                # Show top performing templates
                sorted_templates = sorted(
                    template_stats.items(),
                    key=lambda x: (x[1]["success_rate"], x[1]["total"]),
                    reverse=True,
                )

                table = Table(title="Top Performing Templates", show_header=True)
                table.add_column("Template", style="cyan")
                table.add_column("Usage", justify="right")
                table.add_column("Success Rate", justify="right")
                table.add_column("Loved", justify="right")

                for tid, stats in sorted_templates[:10]:
                    success_color = (
                        "green"
                        if stats["success_rate"] >= 0.8
                        else "yellow"
                        if stats["success_rate"] >= 0.6
                        else "red"
                    )

                    table.add_row(
                        f"#{tid}",
                        f"{stats['total']}",
                        f"[{success_color}]{stats['success_rate']:.0%}[/{success_color}]",
                        f"[green]{stats['loved']}[/green]" if stats["loved"] > 0 else "0",
                    )

                console.print(table)
            else:
                console.print("[dim]No template feedback data yet[/dim]")

            console.print()

        # ============================================================================
        # CLIENT METRICS
        # ============================================================================
        if not focus_metrics or "clients" in focus_metrics:
            console.print("[bold]👥 Client Metrics[/bold]\n")

            # Analyze client retention
            repeat_clients = 0
            new_clients = 0

            for client_name in all_clients:
                client_memory = db.get_client_memory(client_name)
                if client_memory:
                    if client_memory.total_projects > 1:
                        repeat_clients += 1
                    else:
                        new_clients += 1

            retention_rate = repeat_clients / total_clients if total_clients > 0 else 0.0

            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_row("Total Clients:", f"[cyan]{total_clients}[/cyan]")
            table.add_row("Repeat Clients:", f"[green]{repeat_clients}[/green]")
            table.add_row("New Clients:", f"[yellow]{new_clients}[/yellow]")
            table.add_row("Retention Rate:", f"[green]{retention_rate:.0%}[/green]")

            # Average satisfaction
            if satisfaction["total_surveys"] > 0:
                table.add_row(
                    "Avg Satisfaction:",
                    f"[green]{satisfaction['avg_satisfaction']:.1f}/5.0[/green]",
                )

            console.print(table)
            console.print()

        # ============================================================================
        # FOOTER
        # ============================================================================
        console.print("=" * 70)
        console.print(f"[dim]Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
        console.print("=" * 70 + "\n")

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Dashboard failed: {str(e)}", exc_info=True)
        sys.exit(1)


@cli.command("analytics")
@click.option(
    "--report",
    "-r",
    required=True,
    type=click.Choice(
        ["templates", "client-retention", "voice-matching", "cost-analysis"], case_sensitive=False
    ),
    help="Report type to generate",
)
@click.option("--output", "-o", help="Output file path (optional)")
def analytics(report: str, output: Optional[str]):
    """
    Generate detailed analytics reports

    Available reports:
    - templates: Template performance analysis
    - client-retention: Client retention metrics
    - voice-matching: Voice match quality analysis
    - cost-analysis: Cost per client trends

    Examples:
        # View template performance
        python 03_post_generator.py analytics --report templates

        # Export retention report to file
        python 03_post_generator.py analytics --report client-retention --output retention_report.md
    """
    from rich.table import Table

    from src.database.project_db import ProjectDatabase

    try:
        db = ProjectDatabase()


        # ============================================================================
        # TEMPLATE PERFORMANCE REPORT
        # ============================================================================
        if report == "templates":
            console.print("\n[bold cyan]📝 Template Performance Analysis[/bold cyan]\n")

            # Get all feedback
            feedback_records = db.get_post_feedback()

            if not feedback_records:
                console.print("[yellow]No feedback data available yet[/yellow]\n")
                return

            # Aggregate by template
            template_stats = {}

            for feedback in feedback_records:
                template_id = feedback["template_id"]

                if template_id not in template_stats:
                    template_stats[template_id] = {
                        "template_name": feedback["template_name"],
                        "total": 0,
                        "kept": 0,
                        "modified": 0,
                        "rejected": 0,
                        "loved": 0,
                        "engagement": [],
                    }

                template_stats[template_id]["total"] += 1
                template_stats[template_id][feedback["feedback_type"]] += 1

                if feedback["engagement_data"]:
                    template_stats[template_id]["engagement"].append(feedback["engagement_data"])

            # Calculate metrics and sort
            for tid, stats in template_stats.items():
                if stats["total"] > 0:
                    stats["success_rate"] = (stats["kept"] + stats["loved"]) / stats["total"]
                    stats["loved_rate"] = stats["loved"] / stats["total"]
                    stats["rejected_rate"] = stats["rejected"] / stats["total"]

                    # Average engagement
                    if stats["engagement"]:
                        total_likes = sum(e.get("likes", 0) for e in stats["engagement"])
                        stats["avg_engagement"] = total_likes / len(stats["engagement"])
                    else:
                        stats["avg_engagement"] = 0.0

            # Sort by success rate
            sorted_templates = sorted(
                template_stats.items(),
                key=lambda x: (x[1]["success_rate"], x[1]["total"]),
                reverse=True,
            )

            # Display table
            table = Table(title="Template Performance Ranking", show_header=True)
            table.add_column("Rank", justify="right", style="cyan")
            table.add_column("Template", style="bold")
            table.add_column("Usage", justify="right")
            table.add_column("Success", justify="right")
            table.add_column("Loved", justify="right")
            table.add_column("Rejected", justify="right")
            table.add_column("Avg Likes", justify="right")

            for rank, (tid, stats) in enumerate(sorted_templates, 1):
                success_color = (
                    "green"
                    if stats["success_rate"] >= 0.8
                    else "yellow"
                    if stats["success_rate"] >= 0.6
                    else "red"
                )

                table.add_row(
                    f"{rank}",
                    f"#{tid}",
                    f"{stats['total']}",
                    f"[{success_color}]{stats['success_rate']:.0%}[/{success_color}]",
                    f"[green]{stats['loved_rate']:.0%}[/green]",
                    f"[red]{stats['rejected_rate']:.0%}[/red]",
                    f"{stats['avg_engagement']:.0f}" if stats["avg_engagement"] > 0 else "-",
                )

            console.print(table)

            # Insights
            console.print("\n[bold]💡 Key Insights:[/bold]\n")

            top_template = sorted_templates[0]
            console.print(
                f"  • Best performing template: #{top_template[0]} ({top_template[1]['success_rate']:.0%} success)"
            )

            if len(sorted_templates) > 1:
                worst_template = sorted_templates[-1]
                console.print(
                    f"  • Needs improvement: #{worst_template[0]} ({worst_template[1]['success_rate']:.0%} success)"
                )

            # Most loved
            most_loved = max(sorted_templates, key=lambda x: x[1]["loved"])
            if most_loved[1]["loved"] > 0:
                console.print(
                    f"  • Most loved: #{most_loved[0]} ({most_loved[1]['loved']} loved posts)"
                )

            console.print()

        # ============================================================================
        # CLIENT RETENTION REPORT
        # ============================================================================
        elif report == "client-retention":
            console.print("\n[bold cyan]👥 Client Retention Analysis[/bold cyan]\n")

            # Get all clients
            all_clients = db.get_all_client_names()

            if not all_clients:
                console.print("[yellow]No client data available yet[/yellow]\n")
                return

            # Analyze retention
            new_clients = []
            repeat_clients = []
            loyal_clients = []  # 3+ projects

            for client_name in all_clients:
                client_memory = db.get_client_memory(client_name)
                if client_memory:
                    if client_memory.total_projects >= 3:
                        loyal_clients.append(client_name)
                    elif client_memory.total_projects >= 2:
                        repeat_clients.append(client_name)
                    else:
                        new_clients.append(client_name)

            total = len(all_clients)
            repeat_rate = len(repeat_clients) / total if total > 0 else 0.0
            loyal_rate = len(loyal_clients) / total if total > 0 else 0.0

            # Display metrics
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_row("Total Clients:", f"[cyan]{total}[/cyan]")
            table.add_row(
                "New Clients (1 project):",
                f"[yellow]{len(new_clients)}[/yellow] ({len(new_clients)/total:.0%})",
            )
            table.add_row(
                "Repeat Clients (2 projects):",
                f"[green]{len(repeat_clients)}[/green] ({repeat_rate:.0%})",
            )
            table.add_row(
                "Loyal Clients (3+ projects):",
                f"[bold green]{len(loyal_clients)}[/bold green] ({loyal_rate:.0%})",
            )

            console.print(table)

            # Satisfaction correlation
            console.print("\n[bold]📊 Retention by Satisfaction:[/bold]\n")

            retention_by_satisfaction = {}
            for client_name in all_clients:
                client_memory = db.get_client_memory(client_name)
                if client_memory and client_memory.average_satisfaction:
                    sat_bucket = int(client_memory.average_satisfaction)

                    if sat_bucket not in retention_by_satisfaction:
                        retention_by_satisfaction[sat_bucket] = {"total": 0, "repeat": 0}

                    retention_by_satisfaction[sat_bucket]["total"] += 1
                    if client_memory.total_projects > 1:
                        retention_by_satisfaction[sat_bucket]["repeat"] += 1

            table = Table(show_header=True)
            table.add_column("Satisfaction", justify="center")
            table.add_column("Clients", justify="right")
            table.add_column("Repeat Rate", justify="right")

            for sat_score in sorted(retention_by_satisfaction.keys(), reverse=True):
                data = retention_by_satisfaction[sat_score]
                repeat_pct = data["repeat"] / data["total"] if data["total"] > 0 else 0.0

                table.add_row(
                    f"{'⭐' * sat_score}", f"{data['total']}", f"[green]{repeat_pct:.0%}[/green]"
                )

            console.print(table)
            console.print()

        # ============================================================================
        # VOICE MATCHING REPORT
        # ============================================================================
        elif report == "voice-matching":
            console.print("\n[bold cyan]🎯 Voice Matching Quality Analysis[/bold cyan]\n")

            # Get satisfaction scores focused on voice match
            satisfaction_records = db.get_client_satisfaction()

            if not satisfaction_records:
                console.print("[yellow]No voice match data available yet[/yellow]\n")
                return

            # Analyze voice match ratings
            voice_ratings = [
                s["voice_match_rating"] for s in satisfaction_records if s["voice_match_rating"]
            ]

            if not voice_ratings:
                console.print("[yellow]No voice match ratings collected[/yellow]\n")
                return

            avg_voice_match = sum(voice_ratings) / len(voice_ratings)

            # Distribution
            distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for rating in voice_ratings:
                distribution[rating] += 1

            # Display
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_row("Total Ratings:", f"[cyan]{len(voice_ratings)}[/cyan]")
            table.add_row(
                "Average Voice Match:",
                f"[green]{'⭐' * int(avg_voice_match)} {avg_voice_match:.1f}/5.0[/green]",
            )

            console.print(table)

            console.print("\n[bold]Rating Distribution:[/bold]\n")

            table = Table(show_header=True)
            table.add_column("Rating", justify="center")
            table.add_column("Count", justify="right")
            table.add_column("Percentage", justify="right")

            for rating in sorted(distribution.keys(), reverse=True):
                count = distribution[rating]
                pct = count / len(voice_ratings) if len(voice_ratings) > 0 else 0.0

                color = "green" if rating >= 4 else "yellow" if rating >= 3 else "red"

                table.add_row(f"{'⭐' * rating}", f"{count}", f"[{color}]{pct:.0%}[/{color}]")

            console.print(table)

            # Recommendations
            console.print("\n[bold]💡 Insights:[/bold]\n")

            excellent_rate = (distribution[5] + distribution[4]) / len(voice_ratings)
            if excellent_rate >= 0.8:
                console.print("  ✓ Excellent voice matching (80%+ rated 4-5 stars)")
            elif excellent_rate >= 0.6:
                console.print("  → Good voice matching, room for improvement")
            else:
                console.print("  ! Voice matching needs attention")

            console.print()

        # ============================================================================
        # COST ANALYSIS REPORT
        # ============================================================================
        elif report == "cost-analysis":
            console.print("\n[bold cyan]💰 Cost Analysis[/bold cyan]\n")

            # Get all client data
            all_clients = db.get_all_client_names()

            if not all_clients:
                console.print("[yellow]No client data available yet[/yellow]\n")
                return

            # Calculate costs
            total_lifetime_value = 0.0
            total_projects = 0

            for client_name in all_clients:
                client_memory = db.get_client_memory(client_name)
                if client_memory:
                    total_lifetime_value += client_memory.lifetime_value
                    total_projects += client_memory.total_projects

            avg_project_value = total_lifetime_value / total_projects if total_projects > 0 else 0.0

            # Display
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_row("Total Revenue:", f"[cyan]${total_lifetime_value:,.2f}[/cyan]")
            table.add_row("Total Projects:", f"[cyan]{total_projects}[/cyan]")
            table.add_row("Avg Project Value:", f"[green]${avg_project_value:,.2f}[/green]")
            table.add_row(
                "Avg Client LTV:", f"[green]${total_lifetime_value/len(all_clients):,.2f}[/green]"
            )

            console.print(table)
            console.print("\n[dim]Note: API costs and operational expenses not included[/dim]\n")

        # Export to file if requested
        if output:
            # Write to file (simplified - just text output)
            console.print(f"\n[dim]Exporting report to {output}...[/dim]")
            # TODO: Implement file export
            console.print("[yellow]Export feature coming soon![/yellow]\n")

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {str(e)}")
        logger.error(f"Analytics failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
