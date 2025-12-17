"""
CLI entry point for the conversational agent

Usage:
    python agent_cli.py chat                  # Start interactive chat
    python agent_cli.py chat --session <id>   # Resume previous session
    python agent_cli.py sessions              # List recent sessions
"""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.context import ContextManager
from agent.core import ContentAgentCore

console = Console()


def display_welcome():
    """Display welcome message"""
    welcome_text = """
# 🤖 Content Generation Assistant

I'm your AI assistant for managing the 30-Day Content Jumpstart service.

**What I can help with:**
- Generate posts for clients
- Manage projects and workflows
- Collect feedback and satisfaction surveys
- Upload voice samples
- View analytics dashboards
- Process revisions
- Search files and client history

**Tips:**
- Ask questions in natural language
- I remember context from our conversation
- Type 'help' for examples
- Type 'exit' to end the session
- Type 'reset' to start a new conversation

---
    """
    console.print(Panel(Markdown(welcome_text), title="Welcome", border_style="blue"))


def display_message(message: str, style: str = ""):
    """Display agent message with formatting"""
    if style:
        console.print(f"\n[{style}]{message}[/{style}]\n")
    else:
        # Check if message contains markdown
        if any(marker in message for marker in ["#", "-", "*", "```", "**"]):
            console.print(Markdown(message))
        else:
            console.print(message)


@click.group()
def cli():
    """Content Generation Agent CLI"""


@cli.command()
@click.option("--session", "-s", default=None, help="Resume previous session by ID")
@click.option("--api-key", envvar="ANTHROPIC_API_KEY", help="Anthropic API key")
def chat(session, api_key):
    """Start interactive chat with the agent"""

    if not api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY not found in environment[/red]")
        console.print("Set it in .env file or pass via --api-key")
        return

    # Display welcome
    display_welcome()

    # Initialize agent
    with console.status("[bold green]Initializing agent...", spinner="dots"):
        agent = ContentAgentCore(api_key=api_key, session_id=session)

    if session:
        console.print(f"[green]✓[/green] Resumed session: {session[:8]}...\n")
    else:
        console.print(f"[green]✓[/green] Started new session: {agent.get_session_id()[:8]}...\n")

    # Main conversation loop
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")

            # Handle special commands
            if user_input.lower() in ["exit", "quit", "bye"]:
                console.print("\n[yellow]👋 Goodbye! Session saved.[/yellow]\n")
                break

            if user_input.lower() == "reset":
                agent.reset_conversation()
                console.print("\n[green]✓ Conversation reset (context retained)[/green]\n")
                continue

            if user_input.lower() == "new":
                session_id = agent.start_new_session()
                console.print(f"\n[green]✓ Started new session: {session_id[:8]}...[/green]\n")
                continue

            if user_input.lower() == "help":
                display_help()
                continue

            if not user_input.strip():
                continue

            # Show thinking indicator
            with console.status("[bold green]Thinking...", spinner="dots"):
                # Get response from agent
                response = asyncio.run(agent.handle_message(user_input))

            # Display response
            console.print("\n[bold magenta]Agent[/bold magenta]:")
            display_message(response.message)

        except KeyboardInterrupt:
            console.print(
                "\n\n[yellow]Interrupted. Type 'exit' to quit or continue chatting.[/yellow]"
            )
            continue

        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]\n")
            continue


@cli.command()
def sessions():
    """List recent sessions"""
    context_manager = ContextManager()
    recent_sessions = context_manager.get_recent_sessions(limit=10)

    if not recent_sessions:
        console.print("[yellow]No recent sessions found[/yellow]")
        return

    table = Table(title="Recent Sessions")
    table.add_column("Session ID", style="cyan")
    table.add_column("Last Activity", style="green")
    table.add_column("Current Client", style="magenta")
    table.add_column("Actions", justify="right", style="blue")

    for ctx in recent_sessions:
        table.add_row(
            ctx.session_id[:16] + "...",
            ctx.last_activity.strftime("%Y-%m-%d %H:%M"),
            ctx.current_client or "—",
            str(len(ctx.recent_actions)),
        )

    console.print(table)
    console.print("\n[dim]Resume a session with: python agent_cli.py chat --session <id>[/dim]")


def display_help():
    """Display help with example commands"""
    help_text = """
# Example Commands

**Project Management:**
- "Generate posts for Acme Corp"
- "Show me all projects"
- "What's the status of project ABC123?"
- "List all clients"

**Workflows:**
- "Onboard new client TechStartup Inc"
- "Process pending feedback surveys"
- "What needs my attention today?"

**File Operations:**
- "Read the brief for Acme Corp"
- "Search for files with 'brief' in the name"
- "Find all projects for Marketing Agency"

**Analytics:**
- "Show me the dashboard"
- "Show analytics for Acme Corp"

**Context Commands:**
- 'help' - Show this help
- 'reset' - Reset conversation (keep context)
- 'new' - Start completely new session
- 'exit' - End session
    """
    console.print(Markdown(help_text))


if __name__ == "__main__":
    # Ensure UTF-8 encoding on Windows
    if sys.platform == "win32":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    cli()
