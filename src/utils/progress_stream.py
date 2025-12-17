"""Real-time progress streaming for long-running operations

Provides live progress updates during content generation, showing:
- Current operation status
- Completed/total items
- Estimated time remaining
- Token usage in real-time
- Cost accumulation

Usage:
    with ProgressStream("Generating 30 posts") as progress:
        for i, post in enumerate(posts):
            progress.update(i + 1, 30, f"Generating post {i+1}")
            # ... generate post ...
            progress.add_cost(0.015)
"""

import time
from contextlib import contextmanager
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table


class ProgressStream:
    """Real-time progress display for long-running operations"""

    def __init__(
        self,
        title: str,
        total: Optional[int] = None,
        show_cost: bool = True,
        show_tokens: bool = True,
    ):
        """Initialize progress stream

        Args:
            title: Title for the progress display
            total: Total number of items (None = indeterminate)
            show_cost: Show cost accumulation
            show_tokens: Show token usage
        """
        self.title = title
        self.total = total
        self.show_cost = show_cost
        self.show_tokens = show_tokens

        self.console = Console()
        self.start_time = None
        self.current = 0
        self.status_message = ""

        # Accumulators
        self.total_cost = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

        # Progress components
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
        )

        self.task_id = None
        self.live = None

    def __enter__(self):
        """Start progress display"""
        self.start_time = time.time()

        # Create main progress task
        self.task_id = self.progress.add_task(self.title, total=self.total)

        # Start live display
        self.live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=4,
        )
        self.live.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop progress display"""
        if self.live:
            self.live.stop()

        # Show completion message
        if exc_type is None:
            elapsed = time.time() - self.start_time
            self._show_completion(elapsed)

        return False  # Don't suppress exceptions

    def update(self, current: int, total: Optional[int] = None, status: Optional[str] = None):
        """Update progress

        Args:
            current: Current progress value
            total: Optional new total (if changed)
            status: Optional status message
        """
        self.current = current

        if total is not None and total != self.total:
            self.total = total
            self.progress.update(self.task_id, total=total)

        if status:
            self.status_message = status

        # Update progress
        self.progress.update(self.task_id, completed=current, description=status or self.title)

        # Refresh display
        if self.live:
            self.live.update(self._render())

    def add_cost(self, cost: float, input_tokens: int = 0, output_tokens: int = 0):
        """Add cost and token usage

        Args:
            cost: Cost in USD
            input_tokens: Input tokens used
            output_tokens: Output tokens used
        """
        self.total_cost += cost
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        # Refresh display
        if self.live:
            self.live.update(self._render())

    def set_status(self, status: str):
        """Update status message

        Args:
            status: New status message
        """
        self.status_message = status
        self.progress.update(self.task_id, description=status)

        if self.live:
            self.live.update(self._render())

    def _render(self):
        """Render complete progress display"""
        # Main progress bar
        renderable = self.progress

        # Add stats table if requested
        if self.show_cost or self.show_tokens:
            stats_table = self._create_stats_table()
            panel = Panel(
                stats_table,
                title="Statistics",
                border_style="blue",
            )

            # Combine progress + stats
            from rich.columns import Columns

            renderable = Columns([self.progress, panel], expand=True)

        return renderable

    def _create_stats_table(self) -> Table:
        """Create statistics table"""
        table = Table.grid(padding=(0, 2))
        table.add_column(style="cyan", justify="right")
        table.add_column(style="white")

        if self.show_cost:
            table.add_row("💰 Cost:", f"${self.total_cost:.4f}")

        if self.show_tokens:
            table.add_row("📊 Tokens:", f"{self.total_input_tokens + self.total_output_tokens:,}")
            table.add_row("  • Input:", f"{self.total_input_tokens:,}")
            table.add_row("  • Output:", f"{self.total_output_tokens:,}")

        if self.current and self.total:
            percent = (self.current / self.total) * 100
            table.add_row("📈 Progress:", f"{percent:.1f}%")

        return table

    def _show_completion(self, elapsed: float):
        """Show completion summary"""
        if self.total:
            summary_text = (
                f"[bold green]✓[/bold green] Completed {self.total} items in {elapsed:.1f}s"
            )
        else:
            summary_text = f"[bold green]✓[/bold green] Completed in {elapsed:.1f}s"

        if self.show_cost and self.total_cost > 0:
            summary_text += f" | Cost: ${self.total_cost:.4f}"

        if self.show_tokens and self.total_input_tokens + self.total_output_tokens > 0:
            total_tokens = self.total_input_tokens + self.total_output_tokens
            summary_text += f" | Tokens: {total_tokens:,}"

        self.console.print(summary_text)


class SimpleProgress:
    """Lightweight progress indicator for simpler cases"""

    def __init__(self, title: str, console: Optional[Console] = None):
        """Initialize simple progress

        Args:
            title: Progress title
            console: Optional Rich console
        """
        self.title = title
        self.console = console or Console()
        self.start_time = None

    def __enter__(self):
        """Start progress"""
        self.start_time = time.time()
        self.console.print(f"[cyan]{self.title}...[/cyan]", end="")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop progress"""
        if exc_type is None:
            elapsed = time.time() - self.start_time
            self.console.print(f" [green]✓[/green] ({elapsed:.1f}s)")
        else:
            self.console.print(" [red]✗[/red]")

        return False

    def update(self, message: str):
        """Update progress message

        Args:
            message: New message
        """
        elapsed = time.time() - self.start_time
        self.console.print(f"  [{elapsed:.1f}s] {message}")


# Async-compatible progress (for use with asyncio)
class AsyncProgressStream(ProgressStream):
    """Async version of ProgressStream for use with async operations"""

    async def aupdate(
        self, current: int, total: Optional[int] = None, status: Optional[str] = None
    ):
        """Async version of update (calls sync version)"""
        self.update(current, total, status)

    async def aadd_cost(self, cost: float, input_tokens: int = 0, output_tokens: int = 0):
        """Async version of add_cost (calls sync version)"""
        self.add_cost(cost, input_tokens, output_tokens)


# Context manager for batch operations
@contextmanager
def batch_progress(title: str, total: int, show_cost: bool = True, show_tokens: bool = True):
    """Context manager for batch progress tracking

    Usage:
        with batch_progress("Generating posts", 30) as progress:
            for i in range(30):
                progress.update(i + 1, status=f"Post {i+1}/30")
                # ... do work ...

    Args:
        title: Progress title
        total: Total items
        show_cost: Show cost tracking
        show_tokens: Show token tracking

    Yields:
        ProgressStream instance
    """
    with ProgressStream(title, total, show_cost, show_tokens) as progress:
        yield progress


# Simple spinner for quick operations
@contextmanager
def simple_spinner(title: str):
    """Simple spinner for quick operations

    Usage:
        with simple_spinner("Loading templates"):
            # ... do work ...

    Args:
        title: Spinner title
    """
    with SimpleProgress(title) as progress:
        yield progress
