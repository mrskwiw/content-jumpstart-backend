"""
Enhanced CLI entry point with Week 2 intelligence features

New capabilities:
- Proactive suggestions on startup
- Workflow planning and confirmation
- Batch operation support
- Error recovery with user prompts
- Scheduled task management
- Email notification support
"""

import asyncio
import sys

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

# Force UTF-8 encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Import enhanced agent
from agent import ContentAgentCoreEnhanced, SuggestionEngine, TaskScheduler, WorkflowPlan

console = Console()


def display_welcome():
    """Display welcome message with Week 2 features"""
    welcome_text = """
# 🤖 Content Generation Assistant (Enhanced v2.0)

I'm your AI assistant for managing the 30-Day Content Jumpstart service.

## ✨ NEW Intelligence Features (Week 2):

**Proactive Suggestions**
- I'll notify you about pending feedback, overdue items, and client milestones

**Workflow Planning**
- Multi-step operations are planned and confirmed before execution

**Batch Operations**
- Say "process all pending tasks" to handle everything at once

**Error Recovery**
- API failures and timeouts are automatically retried with exponential backoff

**Scheduling**
- Schedule future tasks: "remind me tomorrow to follow up with ClientX"

**Email Integration**
- Send deliverables, reminders, and invoices via email

## What I can help with:

- Generate posts for clients
- Manage projects and workflows
- Collect feedback and satisfaction surveys
- Send deliverables and invoices
- Handle revisions
- Process batch operations
- Schedule future tasks

**Special Commands:**
- `help` - Show this help message
- `pending` or `daily summary` - Show what needs attention
- `scheduled` - Show upcoming scheduled tasks
- `reset` - Start new conversation
- `new` - New chat session
- `exit` - Save and exit

**Conversation History:**
- Use `python agent_cli_enhanced.py export -s <session_id>` to export conversation
- Use `python agent_cli_enhanced.py search -s <session_id> <query>` to search
- Use `python agent_cli_enhanced.py summary -s <session_id>` for statistics

Let's get started! What would you like to work on?
"""
    console.print(Markdown(welcome_text))


def display_message(message: str):
    """Display agent message with markdown support and syntax highlighting"""
    import re

    # Check if message contains code blocks
    code_block_pattern = r"```(\w+)?\n(.*?)```"
    matches = list(re.finditer(code_block_pattern, message, re.DOTALL))

    if matches:
        # Message has code blocks - display with syntax highlighting
        last_end = 0
        for match in matches:
            # Display text before code block
            if match.start() > last_end:
                text_before = message[last_end : match.start()]
                if text_before.strip():
                    console.print(Markdown(text_before))

            # Display code block with syntax highlighting
            language = match.group(1) or "python"
            code = match.group(2)

            console.print(
                Panel(
                    Syntax(code, language, theme="monokai", line_numbers=True),
                    title=f"[bold cyan]{language}[/bold cyan]",
                    border_style="cyan",
                )
            )

            last_end = match.end()

        # Display remaining text after last code block
        if last_end < len(message):
            text_after = message[last_end:]
            if text_after.strip():
                console.print(Markdown(text_after))
    else:
        # No code blocks - display as markdown in a panel
        console.print(Panel(Markdown(message), border_style="magenta", padding=(1, 2)))


def display_suggestions(suggestions):
    """Display proactive suggestions with rich panels"""
    if not suggestions:
        return

    console.print("\n[bold yellow]💡 Proactive Suggestions:[/bold yellow]\n")

    for suggestion in suggestions[:5]:  # Show top 5
        priority_colors = {"critical": "red", "high": "yellow", "medium": "blue", "low": "green"}
        color = priority_colors.get(suggestion.priority.value, "white")

        # Format recommended actions
        actions_text = ""
        if suggestion.recommended_actions:
            actions_text = "\n\n[bold]Recommended Actions:[/bold]\n"
            for i, action in enumerate(suggestion.recommended_actions, 1):
                actions_text += f"  {i}. {action}\n"

        panel_content = f"{suggestion.description}{actions_text}"

        console.print(
            Panel(
                panel_content,
                title=f"[{color}]{suggestion.title}[/{color}]",
                border_style=color,
                padding=(0, 2),
            )
        )

    if len(suggestions) > 5:
        console.print(f"\n[dim]...and {len(suggestions) - 5} more suggestions[/dim]\n")


def display_workflow_plan(plan: WorkflowPlan):
    """Display workflow plan for user approval with tree visualization"""
    # Create header panel
    header = Panel(
        f"[bold]Intent:[/bold] {plan.intent}\n"
        f"[bold]Total Steps:[/bold] {len(plan.tasks)}\n"
        f"[bold]Estimated Time:[/bold] {plan._format_duration(plan.total_estimated_duration_seconds)}",
        title="[bold cyan]📋 Workflow Plan[/bold cyan]",
        border_style="cyan",
    )
    console.print(header)

    # Create task tree for better visualization
    tree = Tree("📝 [bold]Tasks[/bold]")

    for i, task in enumerate(plan.tasks, 1):
        emoji = plan._get_task_emoji(task.task_type)
        priority_color = {"urgent": "red", "high": "yellow", "normal": "blue", "low": "green"}
        color = priority_color.get(task.priority.value, "white")

        # Create task label with priority badge
        task_label = f"[{color}]{emoji} {task.description}[/{color}] "
        task_label += f"[dim]({plan._format_duration(task.estimated_duration_seconds)})[/dim]"

        task_node = tree.add(task_label)

        # Add dependencies if any
        if task.depends_on:
            dep_branch = task_node.add("[dim]Dependencies:[/dim]")
            for dep_id in task.depends_on:
                dep_task = next((t for t in plan.tasks if t.task_id == dep_id), None)
                if dep_task:
                    dep_branch.add(f"[dim]→ {dep_task.description}[/dim]")

    console.print(tree)

    # Also show traditional table for detailed view
    table = Table(show_header=True, header_style="bold magenta", border_style="dim")
    table.add_column("#", style="dim", width=6)
    table.add_column("Task", min_width=30)
    table.add_column("Priority", justify="center", width=10)
    table.add_column("Time", justify="right", width=8)

    for i, task in enumerate(plan.tasks, 1):
        emoji = plan._get_task_emoji(task.task_type)
        priority_color = {
            "urgent": "[red]URGENT[/red]",
            "high": "[yellow]HIGH[/yellow]",
            "normal": "[blue]NORMAL[/blue]",
            "low": "[green]LOW[/green]",
        }

        table.add_row(
            str(i),
            f"{emoji} {task.description}",
            priority_color.get(task.priority.value, task.priority.value),
            plan._format_duration(task.estimated_duration_seconds),
        )

    console.print("\n[dim]Detailed View:[/dim]")
    console.print(table)
    console.print()


@click.group()
def cli():
    """Enhanced Content Generation Assistant CLI"""


@cli.command()
@click.option("--session", "-s", default=None, help="Resume previous session by ID")
@click.option("--api-key", envvar="ANTHROPIC_API_KEY", help="Anthropic API key")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def chat(session, api_key, debug):
    """Start interactive chat with enhanced intelligence features"""

    if not api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY not found in environment[/red]")
        console.print("\nSet it in your .env file or environment:")
        console.print("  export ANTHROPIC_API_KEY=sk-ant-...")
        return

    display_welcome()

    # Initialize enhanced agent
    try:
        agent = ContentAgentCoreEnhanced(api_key=api_key, session_id=session)
    except Exception as e:
        console.print(f"[red]Error initializing agent: {e}[/red]")
        return

    # Show initial suggestions
    if not session:
        suggestions = agent.suggestion_engine.generate_suggestions()
        if suggestions:
            display_suggestions(suggestions)

    # Main conversation loop
    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")

            # Handle special commands
            if user_input.lower() in ["exit", "quit", "bye"]:
                console.print("\n[yellow]👋 Goodbye! Session saved.[/yellow]\n")
                break

            if user_input.lower() == "help":
                display_welcome()
                continue

            if user_input.lower() == "reset":
                agent.reset_conversation()
                console.print("\n[green]✅ Conversation reset[/green]\n")
                continue

            if user_input.lower() == "new":
                # Start new session
                agent = ContentAgentCoreEnhanced(api_key=api_key)
                console.print("\n[green]✅ New session started[/green]\n")
                continue

            if user_input.lower() in ["pending", "daily summary"]:
                summary = agent.suggestion_engine.get_daily_summary()
                console.print("\n[bold magenta]Agent[/bold magenta]:")
                display_message(summary)
                continue

            if user_input.lower() in ["scheduled", "show scheduled"]:
                summary = agent.scheduler.get_task_summary()
                console.print("\n[bold magenta]Agent[/bold magenta]:")
                display_message(summary)
                continue

            # Process message with agent
            with console.status("[bold green]Thinking...", spinner="dots"):
                response = asyncio.run(agent.handle_message(user_input))

            # Display response
            console.print("\n[bold magenta]Agent[/bold magenta]:")
            display_message(response.message)

            # Display any new suggestions
            if response.suggestions:
                display_suggestions(response.suggestions)

            # Display workflow plan if generated
            if response.workflow_plan:
                display_workflow_plan(response.workflow_plan)

                # Ask for confirmation
                if response.workflow_plan.requires_confirmation:
                    proceed = Confirm.ask("\n[bold yellow]Execute this workflow?[/bold yellow]")

                    if proceed:
                        console.print("\n[bold green]Executing workflow...[/bold green]\n")

                        with Progress(
                            SpinnerColumn(),
                            TextColumn("[bold blue]{task.description}"),
                            BarColumn(),
                            TaskProgressColumn(),
                            TextColumn("[bold green]{task.completed}/{task.total}"),
                            console=console,
                        ) as progress:
                            task = progress.add_task(
                                "Processing workflow tasks...",
                                total=len(response.workflow_plan.tasks),
                            )

                            results = asyncio.run(agent.execute_workflow(response.workflow_plan))

                            progress.update(task, completed=len(response.workflow_plan.tasks))

                        # Display results in a panel
                        result_text = (
                            f"[bold]Completed:[/bold] [green]{results['completed_tasks']}[/green] tasks\n"
                            f"[bold]Failed:[/bold] [red]{results['failed_tasks']}[/red] tasks"
                        )

                        if results["completed_tasks"] == len(response.workflow_plan.tasks):
                            result_panel = Panel(
                                result_text,
                                title="[bold green]✅ Workflow Complete![/bold green]",
                                border_style="green",
                            )
                        else:
                            result_panel = Panel(
                                result_text,
                                title="[bold yellow]⚠️  Workflow Completed with Errors[/bold yellow]",
                                border_style="yellow",
                            )

                        console.print(result_panel)
                    else:
                        console.print("\n[yellow]Workflow cancelled[/yellow]\n")

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]\n")
            continue
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]\n")
            if debug:
                import traceback

                console.print(traceback.format_exc())


@cli.command()
@click.option("--limit", "-l", default=10, help="Number of sessions to show")
def sessions(limit):
    """List recent chat sessions"""
    from agent.context import ContextManager

    manager = ContextManager()
    recent_sessions = manager.get_recent_sessions(limit=limit)

    if not recent_sessions:
        console.print("[yellow]No recent sessions found[/yellow]")
        return

    table = Table(title="Recent Sessions", show_header=True, header_style="bold magenta")
    table.add_column("Session ID", style="cyan")
    table.add_column("Client", style="green")
    table.add_column("Last Activity", style="yellow")
    table.add_column("Actions", justify="right", style="blue")

    for ctx in recent_sessions:
        last_activity = ctx.last_activity.strftime("%Y-%m-%d %H:%M")
        client = ctx.current_client or "[dim]None[/dim]"
        table.add_row(
            ctx.session_id[:12] + "...", client, last_activity, str(len(ctx.recent_actions))
        )

    console.print(table)


@cli.command()
def scheduled():
    """Show scheduled tasks"""
    scheduler = TaskScheduler()
    upcoming = scheduler.get_upcoming_tasks(limit=10)

    if not upcoming:
        console.print("[yellow]📅 No scheduled tasks[/yellow]")
        return

    table = Table(title="Upcoming Scheduled Tasks", show_header=True, header_style="bold magenta")
    table.add_column("Description", style="cyan", min_width=30)
    table.add_column("Scheduled For", style="green")
    table.add_column("Frequency", style="yellow")
    table.add_column("Status", style="blue")

    for task in upcoming:
        execution_time = task.next_execution or task.scheduled_for
        time_str = scheduler._format_relative_time(execution_time)
        freq_badge = task.frequency.value if task.frequency.value != "once" else "⚡ One-time"

        table.add_row(task.description, time_str, freq_badge, task.status.value)

    console.print(table)


@cli.command()
def pending():
    """Show pending items and suggestions"""
    engine = SuggestionEngine()
    suggestions = engine.generate_suggestions()

    if not suggestions:
        console.print("[green]✅ All caught up! No pending items.[/green]")
        return

    display_suggestions(suggestions)

    # Group by priority
    critical = [s for s in suggestions if s.priority.value == "critical"]
    high = [s for s in suggestions if s.priority.value == "high"]
    medium = [s for s in suggestions if s.priority.value == "medium"]

    console.print("\n[bold]Summary:[/bold]")
    if critical:
        console.print(f"  🔴 Critical: {len(critical)}")
    if high:
        console.print(f"  🟠 High: {len(high)}")
    if medium:
        console.print(f"  🟡 Medium: {len(medium)}")


@cli.command()
@click.option("--session", "-s", required=True, help="Session ID to export")
@click.option("--output", "-o", help="Output file path (default: data/exports/{session_id}.md)")
def export(session, output):
    """Export conversation history to markdown"""
    from pathlib import Path

    from agent.context import ContextManager

    manager = ContextManager()

    # Check if session exists
    context = manager.load_context(session)
    if not context:
        console.print(f"[red]Session {session} not found[/red]")
        return

    # Default output path if not provided
    if not output:
        output = f"data/exports/{session}.md"

    # Export conversation
    try:
        markdown = manager.export_conversation_markdown(session, output_path=Path(output))
        console.print(f"[green]✅ Conversation exported to {output}[/green]")

        # Show summary
        summary = manager.get_conversation_summary(session)
        console.print("\n[bold]Conversation Summary:[/bold]")
        console.print(f"  Total messages: {summary['total_messages']}")
        console.print(f"  User messages: {summary['user_messages']}")
        console.print(f"  Assistant messages: {summary['assistant_messages']}")
        if summary.get("duration"):
            console.print(f"  Duration: {summary['duration']}")
    except Exception as e:
        console.print(f"[red]Error exporting conversation: {e}[/red]")


@cli.command()
@click.option("--session", "-s", required=True, help="Session ID to search")
@click.argument("query")
@click.option("--role", "-r", type=click.Choice(["user", "assistant"]), help="Filter by role")
def search(session, query, role):
    """Search conversation history"""
    from agent.context import ContextManager

    manager = ContextManager()

    # Check if session exists
    context = manager.load_context(session)
    if not context:
        console.print(f"[red]Session {session} not found[/red]")
        return

    # Search conversation
    results = manager.search_conversation(session, query, role)

    if not results:
        console.print(f"[yellow]No messages found matching '{query}'[/yellow]")
        return

    console.print(f"\n[bold cyan]Found {len(results)} message(s) matching '{query}':[/bold cyan]\n")

    for i, msg in enumerate(results, 1):
        role_color = "cyan" if msg["role"] == "user" else "magenta"
        console.print(
            f"[{role_color}]{i}. {msg['role'].upper()}[/{role_color}] ({msg['timestamp']})"
        )

        # Show snippet of content (first 200 chars)
        content = msg["content"]
        if len(content) > 200:
            content = content[:200] + "..."
        console.print(f"   {content}\n")


@cli.command()
@click.option("--session", "-s", required=True, help="Session ID")
def summary(session):
    """Show conversation summary statistics"""
    from agent.context import ContextManager

    manager = ContextManager()

    # Check if session exists
    context = manager.load_context(session)
    if not context:
        console.print(f"[red]Session {session} not found[/red]")
        return

    # Get summary
    summary_data = manager.get_conversation_summary(session)

    if summary_data["total_messages"] == 0:
        console.print(f"[yellow]No messages in session {session}[/yellow]")
        return

    # Display summary
    console.print("\n[bold cyan]Conversation Summary[/bold cyan]\n")
    console.print(f"Session ID: {session}")
    console.print(f"Client: {context.current_client or 'N/A'}")
    console.print(f"Project: {context.current_project or 'N/A'}")
    console.print("\n[bold]Statistics:[/bold]")
    console.print(f"  Total messages: {summary_data['total_messages']}")
    console.print(f"  User messages: {summary_data['user_messages']}")
    console.print(f"  Assistant messages: {summary_data['assistant_messages']}")

    if summary_data.get("first_message"):
        from datetime import datetime

        first_dt = datetime.fromisoformat(summary_data["first_message"])
        last_dt = datetime.fromisoformat(summary_data["last_message"])
        console.print("\n[bold]Timeline:[/bold]")
        console.print(f"  First message: {first_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"  Last message: {last_dt.strftime('%Y-%m-%d %H:%M:%S')}")

    if summary_data.get("duration"):
        console.print(f"  Duration: {summary_data['duration']}")


if __name__ == "__main__":
    cli()
