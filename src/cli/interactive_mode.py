"""Interactive CLI Mode: Conversational interface for brief completion"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..agents.brief_enhancer import BriefEnhancerAgent
from ..agents.brief_parser import BriefParserAgent
from ..agents.brief_quality_checker import BriefQualityChecker
from ..agents.question_generator import QuestionGeneratorAgent
from ..models.brief_quality import BriefQualityReport
from ..models.client_brief import ClientBrief, Platform, TonePreference
from ..models.question import Question
from ..utils.logger import logger

console = Console()


class InteractiveMode:
    """
    Interactive conversational mode for guided brief completion
    """

    def __init__(self):
        """Initialize interactive mode with all required agents"""
        self.parser = BriefParserAgent()
        self.quality_checker = BriefQualityChecker()
        self.question_generator = QuestionGeneratorAgent()
        self.enhancer = BriefEnhancerAgent()
        self.client_brief: Optional[ClientBrief] = None
        self.iteration_count = 0

    def run(self, initial_brief_file: Optional[str] = None):
        """
        Main interactive loop

        Args:
            initial_brief_file: Optional path to partially filled brief
        """
        console.print("\n[bold cyan]━━━ Welcome to Interactive Brief Mode! ━━━[/bold cyan]\n")
        console.print(
            "I'll help you complete your client brief through a short conversation.\n"
            "You can type [yellow][skip][/yellow] to skip any question and return to it later.\n"
        )

        try:
            # Load or create initial brief
            if initial_brief_file:
                self.client_brief = self._load_initial_brief(initial_brief_file)
            else:
                self.client_brief = self._create_minimal_brief()

            # Main conversation loop
            self._conversation_loop()

            # Final enhancement
            self._apply_final_enhancements()

            # Save and display results
            final_path = self._save_final_brief()

            self._display_completion(final_path)

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Session interrupted. Progress has been saved.[/yellow]")
            if self.client_brief:
                self._save_progress()
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]")
            logger.error(f"Interactive mode error: {e}", exc_info=True)
            if self.client_brief:
                self._save_progress()

    def _load_initial_brief(self, brief_file: str) -> ClientBrief:
        """Load and parse initial brief from file"""
        console.print(f"[cyan]Loading brief from {brief_file}...[/cyan]")

        try:
            brief_path = Path(brief_file)
            brief_text = brief_path.read_text(encoding="utf-8")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(description="Parsing brief...", total=None)
                client_brief = self.parser.parse_brief(brief_text)

            console.print(
                f"[green]✓[/green] Loaded brief for [bold]{client_brief.company_name}[/bold]\n"
            )
            return client_brief

        except Exception as e:
            console.print(f"[red]Failed to load brief: {e}[/red]")
            console.print("[yellow]Starting from scratch instead...[/yellow]\n")
            return self._create_minimal_brief()

    def _create_minimal_brief(self) -> ClientBrief:
        """Create minimal brief from scratch with basic questions"""
        console.print("[yellow]Starting from scratch - let's get some basic info first.[/yellow]\n")

        company_name = Prompt.ask("[bold]What's the company name?[/bold]")

        business_description = Prompt.ask(
            "[bold]What does the company do?[/bold] (one sentence)", default=""
        )

        ideal_customer = Prompt.ask("[bold]Who's the ideal customer?[/bold]", default="")

        main_problem = Prompt.ask("[bold]What main problem do you solve?[/bold]", default="")

        console.print("\n[green]✓[/green] Got the basics! Let's dig deeper...\n")

        return ClientBrief(
            company_name=company_name,
            business_description=business_description or "No description provided",
            ideal_customer=ideal_customer or "Not specified",
            main_problem_solved=main_problem or "Not specified",
        )

    def _conversation_loop(self):
        """Main conversation loop - iteratively improve brief quality"""
        max_iterations = 10  # Safety limit
        self.iteration_count = 0

        while self.iteration_count < max_iterations:
            self.iteration_count += 1

            # Assess current brief quality
            quality_report = self.quality_checker.assess_brief(self.client_brief)

            # Show progress
            self._display_progress(quality_report, iteration=self.iteration_count)

            # Check if ready to generate
            if quality_report.can_generate_content:
                if self._confirm_ready(quality_report):
                    break

            # Generate questions for this iteration
            questions = self.question_generator.generate_questions(
                self.client_brief, quality_report, max_questions=3  # Ask 3 questions at a time
            )

            if not questions:
                console.print("\n[green]✓ Brief is complete![/green]\n")
                break

            # Ask the questions
            self._ask_questions(questions)

            # Save progress after each iteration
            self._save_progress()

            # Brief pause
            console.print()

        if self.iteration_count >= max_iterations:
            console.print(
                "\n[yellow]Reached maximum iterations. "
                "You can continue improving the brief by running interactive mode again.[/yellow]\n"
            )

    def _display_progress(self, quality_report: BriefQualityReport, iteration: int):
        """Display current brief quality progress"""
        console.print("\n" + "─" * 60)

        # Create progress table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="bold")
        table.add_column(style="cyan")

        table.add_row("Iteration:", f"{iteration}")
        table.add_row("Overall Quality:", f"{quality_report.overall_score:.0%}")
        table.add_row("├─ Completeness:", f"{quality_report.completeness_score:.0%}")
        table.add_row("├─ Specificity:", f"{quality_report.specificity_score:.0%}")
        table.add_row("└─ Usability:", f"{quality_report.usability_score:.0%}")
        table.add_row("", "")
        table.add_row(
            "Fields Filled:", f"{quality_report.filled_fields}/{quality_report.total_fields}"
        )

        console.print(table)

        # Status indicator
        if quality_report.can_generate_content:
            console.print("[green]✓ Brief is ready for content generation![/green]")
        else:
            needed = quality_report.minimum_questions_needed
            console.print(f"[yellow]⚠ Need ~{needed} more answers to proceed[/yellow]")

        console.print("─" * 60 + "\n")

    def _ask_questions(self, questions: List[Question]):
        """Ask user a batch of questions"""
        total = len(questions)
        console.print(
            f"[bold cyan]Let's answer {total} question{'s' if total > 1 else ''}:[/bold cyan]\n"
        )

        for i, question in enumerate(questions, 1):
            self._ask_single_question(question, i, total)

    def _ask_single_question(self, question: Question, index: int, total: int):
        """Ask a single question and process the answer"""
        # Display question header
        priority_emoji = "🔴" if question.priority == 1 else "🟡" if question.priority == 2 else "🟢"
        console.print(f"\n{priority_emoji} [bold]Question {index}/{total}:[/bold]")

        if question.context:
            console.print(f"[dim]{question.context}[/dim]")

        console.print(f"\n{question.text}\n")

        if question.example_answer:
            console.print(f"[dim]Example: {question.example_answer}[/dim]\n")

        # Get answer
        answer = Prompt.ask("[bold cyan]Your answer[/bold cyan]", default="[skip]")

        # Process answer
        if answer.lower() == "[skip]":
            console.print("[dim]Skipped - we can come back to this[/dim]")
            return

        # Update brief with answer
        self._update_brief_field(question.field_name, answer)
        console.print("[green]✓[/green] Got it!")

        # Check if follow-up needed (only for priority 1-2 questions)
        if question.priority <= 2:
            follow_up = self.question_generator.generate_follow_up_question(
                question.field_name, answer, self.client_brief
            )

            if follow_up:
                console.print(f"\n[yellow]Quick follow-up:[/yellow] {follow_up.text}\n")
                follow_up_answer = Prompt.ask(
                    "[bold cyan]Your answer[/bold cyan]", default="[skip]"
                )

                if follow_up_answer.lower() != "[skip]":
                    self._update_brief_field(question.field_name, follow_up_answer, append=True)
                    console.print("[green]✓[/green] Thanks!")

    def _update_brief_field(self, field_name: str, value: str, append: bool = False):
        """
        Update a field in the client brief

        Args:
            field_name: Name of field to update
            value: New value
            append: If True, append to existing value instead of replacing
        """
        try:
            current_data = self.client_brief.model_dump()
            current_value = current_data.get(field_name)

            # Determine how to update based on field type
            if isinstance(current_value, list):
                # List field - parse as comma-separated or line-separated
                new_items = self._parse_list_input(value)

                if append and current_value:
                    current_data[field_name] = current_value + new_items
                else:
                    current_data[field_name] = new_items

            elif field_name == "brand_personality":
                # Special handling for enum list
                personalities = self._parse_list_input(value)
                tone_prefs = []
                for p in personalities:
                    try:
                        tone_prefs.append(TonePreference(p.lower().replace(" ", "_")))
                    except ValueError:
                        logger.warning(f"Unknown tone preference: {p}")
                current_data[field_name] = tone_prefs

            elif field_name == "target_platforms":
                # Special handling for platform enum list
                platforms = self._parse_list_input(value)
                platform_enums = []
                for p in platforms:
                    try:
                        platform_enums.append(Platform(p.lower()))
                    except ValueError:
                        logger.warning(f"Unknown platform: {p}")
                current_data[field_name] = platform_enums

            else:
                # String field
                if append and current_value:
                    current_data[field_name] = f"{current_value} {value}"
                else:
                    current_data[field_name] = value

            # Rebuild brief with updated data
            self.client_brief = ClientBrief(**current_data)
            logger.info(f"Updated field: {field_name}")

        except Exception as e:
            logger.error(f"Failed to update field {field_name}: {e}", exc_info=True)
            console.print(f"[red]Error updating field: {e}[/red]")

    def _parse_list_input(self, value: str) -> List[str]:
        """
        Parse list input from various formats

        Args:
            value: User input string

        Returns:
            List of cleaned items
        """
        # Try comma-separated first
        if "," in value:
            items = [item.strip() for item in value.split(",") if item.strip()]
        # Try newline-separated
        elif "\n" in value:
            items = [
                item.strip().lstrip("-•*").strip() for item in value.split("\n") if item.strip()
            ]
        # Try numbered list (1., 2., etc.)
        elif any(f"{i}." in value or f"{i})" in value for i in range(1, 10)):
            import re

            items = re.split(r"\d+[\.\)]\s*", value)
            items = [item.strip() for item in items if item.strip()]
        # Single item
        else:
            items = [value.strip()]

        return items

    def _confirm_ready(self, quality_report: BriefQualityReport) -> bool:
        """Ask user if they want to proceed or continue improving"""
        console.print("\n[bold green]Your brief is ready for content generation![/bold green]")
        console.print(f"Quality score: [bold]{quality_report.overall_score:.0%}[/bold]\n")

        console.print("You can:")
        console.print("  1. [green]Proceed now[/green] - Start generating content")
        console.print(
            "  2. [yellow]Continue improving[/yellow] - Answer more questions for higher quality\n"
        )

        proceed = Confirm.ask("Proceed with content generation?", default=True)

        if not proceed:
            console.print("\n[cyan]Great! Let's make it even better...[/cyan]\n")

        return proceed

    def _apply_final_enhancements(self):
        """Apply AI enhancements to improve brief quality"""
        console.print("\n[cyan]Applying final enhancements with AI...[/cyan]")

        try:
            # Get current quality
            quality_report = self.quality_checker.assess_brief(self.client_brief)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(description="Enhancing brief...", total=None)
                self.client_brief = self.enhancer.enhance_brief(
                    self.client_brief, quality_report, auto_apply=True
                )

            console.print("[green]✓[/green] Enhancements applied\n")

        except Exception as e:
            logger.error(f"Enhancement failed: {e}", exc_info=True)
            console.print(
                "[yellow]⚠ Could not apply enhancements, but brief is still usable[/yellow]\n"
            )

    def _save_progress(self):
        """Save current brief state as work-in-progress"""
        try:
            output_dir = Path("data/briefs")
            output_dir.mkdir(parents=True, exist_ok=True)

            safe_name = self.client_brief.company_name.replace(" ", "_").replace("/", "_")
            filename = f"{safe_name}_wip.json"
            filepath = output_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.client_brief.model_dump(), f, indent=2, default=str)

            logger.info(f"Saved progress to {filepath}")

        except Exception as e:
            logger.error(f"Failed to save progress: {e}", exc_info=True)

    def _save_final_brief(self) -> str:
        """Save completed brief as text file"""
        output_dir = Path("data/briefs")
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_name = self.client_brief.company_name.replace(" ", "_").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}_complete.txt"
        filepath = output_dir / filename

        # Format as human-readable text
        brief_text = self._format_brief_as_text()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(brief_text)

        logger.info(f"Saved final brief to {filepath}")
        return str(filepath)

    def _format_brief_as_text(self) -> str:
        """Format brief as human-readable text"""
        lines = [
            "# Client Brief - " + self.client_brief.company_name,
            "",
            "## Basic Information",
            f"Company: {self.client_brief.company_name}",
        ]

        if self.client_brief.founder_name:
            lines.append(f"Founder: {self.client_brief.founder_name}")

        if self.client_brief.website:
            lines.append(f"Website: {self.client_brief.website}")

        lines.extend(
            [
                f"Business: {self.client_brief.business_description}",
                f"Ideal Customer: {self.client_brief.ideal_customer}",
                f"Problem Solved: {self.client_brief.main_problem_solved}",
                "",
                "## Brand Voice",
            ]
        )

        if self.client_brief.brand_personality:
            personalities = ", ".join([p.value for p in self.client_brief.brand_personality])
            lines.append(f"Personality: {personalities}")

        if self.client_brief.key_phrases:
            lines.append(f"Key Phrases: {', '.join(self.client_brief.key_phrases)}")

        if self.client_brief.tone_to_avoid:
            lines.append(f"Tone to Avoid: {self.client_brief.tone_to_avoid}")

        lines.extend(
            [
                "",
                "## Customer Insights",
            ]
        )

        if self.client_brief.customer_pain_points:
            lines.append("Pain Points:")
            for pp in self.client_brief.customer_pain_points:
                lines.append(f"- {pp}")

        if self.client_brief.customer_questions:
            lines.append("")
            lines.append("Customer Questions:")
            for q in self.client_brief.customer_questions:
                lines.append(f"- {q}")

        if self.client_brief.misconceptions:
            lines.append("")
            lines.append("Misconceptions to Correct:")
            for m in self.client_brief.misconceptions:
                lines.append(f"- {m}")

        if self.client_brief.stories:
            lines.append("")
            lines.append("Stories:")
            for story in self.client_brief.stories:
                lines.append(f"- {story}")

        if self.client_brief.main_cta:
            lines.append("")
            lines.append(f"Main CTA: {self.client_brief.main_cta}")

        return "\n".join(lines)

    def _display_completion(self, filepath: str):
        """Display completion message and next steps"""
        # Final quality check
        quality_report = self.quality_checker.assess_brief(self.client_brief)

        console.print("\n" + "━" * 60)
        console.print("[bold green]✓ Brief Complete![/bold green]\n")

        # Show final stats
        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_column(style="bold")
        stats_table.add_column(style="cyan")

        stats_table.add_row("Company:", self.client_brief.company_name)
        stats_table.add_row("Final Quality:", f"{quality_report.overall_score:.0%}")
        stats_table.add_row(
            "Fields Filled:", f"{quality_report.filled_fields}/{quality_report.total_fields}"
        )
        stats_table.add_row("Saved To:", filepath)

        console.print(stats_table)
        console.print("\n" + "━" * 60 + "\n")

        # Show next steps
        console.print("[bold cyan]Next Steps:[/bold cyan]\n")
        console.print("Generate content with this command:\n")
        console.print(
            f"  [yellow]python 03_post_generator.py generate {filepath} "
            f'-c "{self.client_brief.company_name}"[/yellow]\n'
        )

        if quality_report.overall_score < 0.75:
            console.print(
                "[dim]Tip: For higher quality posts, consider running interactive mode "
                "again to improve the brief further.[/dim]\n"
            )
