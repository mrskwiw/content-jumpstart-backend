"""Cost dashboard and reporting for API usage analysis

Generates formatted reports and dashboards for cost tracking data.
Supports multiple output formats:
- Rich terminal output with tables and charts
- Markdown reports
- CSV exports
- HTML dashboards (optional)

Usage:
    dashboard = CostDashboard()

    # Show project summary
    dashboard.show_project_summary("Client_20250101_120000")

    # Show all projects
    dashboard.show_all_projects()

    # Generate markdown report
    dashboard.generate_markdown_report("report.md", project_id="Client_20250101_120000")
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .cost_tracker import CostTracker, ProjectCost, get_default_tracker
from .logger import logger


class CostDashboard:
    """Generate cost reports and dashboards"""

    def __init__(self, tracker: Optional[CostTracker] = None):
        """Initialize dashboard

        Args:
            tracker: CostTracker instance (default: singleton)
        """
        self.tracker = tracker or get_default_tracker()
        self.console = Console()

    def show_project_summary(self, project_id: str):
        """Display project cost summary in terminal

        Args:
            project_id: Project identifier
        """
        cost = self.tracker.get_project_cost(project_id)

        if cost.total_calls == 0:
            self.console.print(f"[yellow]No cost data found for project: {project_id}[/yellow]")
            return

        # Create summary panel
        duration = cost.last_call - cost.first_call
        duration_str = self._format_duration(duration)

        summary_text = f"""[bold]Project:[/bold] {project_id}

[bold]Total Cost:[/bold] [green]${cost.total_cost:.4f}[/green]

[bold]Token Usage:[/bold]
  • Input Tokens:     {cost.total_input_tokens:,}
  • Output Tokens:    {cost.total_output_tokens:,}
  • Cache Creation:   {cost.total_cache_creation_tokens:,}
  • Cache Read:       {cost.total_cache_read_tokens:,}
  • [bold]Total:[/bold]            [cyan]{cost.total_input_tokens + cost.total_output_tokens:,}[/cyan]

[bold]API Calls:[/bold] {cost.total_calls}
[bold]Duration:[/bold] {duration_str}
[bold]First Call:[/bold] {cost.first_call.strftime('%Y-%m-%d %H:%M:%S')}
[bold]Last Call:[/bold] {cost.last_call.strftime('%Y-%m-%d %H:%M:%S')}
"""

        panel = Panel(summary_text, title="💰 Cost Summary", border_style="green")

        self.console.print(panel)

        # Calculate cost breakdown
        if cost.total_cache_read_tokens > 0:
            cache_savings = self._calculate_cache_savings(cost)
            self.console.print(
                f"\n[bold cyan]Cache Savings:[/bold cyan] [green]${cache_savings:.4f}[/green] "
                f"({(cache_savings / (cost.total_cost + cache_savings) * 100):.1f}%)"
            )

    def show_project_calls(self, project_id: str, limit: int = 20):
        """Display recent API calls for a project

        Args:
            project_id: Project identifier
            limit: Maximum number of calls to show
        """
        calls = self.tracker.get_project_calls(project_id)

        if not calls:
            self.console.print(f"[yellow]No API calls found for project: {project_id}[/yellow]")
            return

        # Create table
        table = Table(
            title=f"API Calls for {project_id} (showing {min(limit, len(calls))} of {len(calls)})"
        )

        table.add_column("Time", style="cyan", no_wrap=True)
        table.add_column("Operation", style="yellow")
        table.add_column("Input", justify="right", style="blue")
        table.add_column("Output", justify="right", style="blue")
        table.add_column("Cache", justify="right", style="magenta")
        table.add_column("Cost", justify="right", style="green")

        for call in calls[:limit]:
            table.add_row(
                call.timestamp.strftime("%H:%M:%S"),
                call.operation[:20],
                f"{call.input_tokens:,}",
                f"{call.output_tokens:,}",
                f"{call.cache_read_tokens:,}" if call.cache_read_tokens > 0 else "-",
                f"${call.cost:.4f}",
            )

        self.console.print(table)

    def show_all_projects(self):
        """Display cost summary for all projects"""
        projects = self.tracker.get_all_projects()

        if not projects:
            self.console.print("[yellow]No projects tracked yet[/yellow]")
            return

        # Create table
        table = Table(title=f"All Projects ({len(projects)} total)")

        table.add_column("Project ID", style="cyan")
        table.add_column("Calls", justify="right", style="blue")
        table.add_column("Input Tokens", justify="right", style="blue")
        table.add_column("Output Tokens", justify="right", style="blue")
        table.add_column("Total Cost", justify="right", style="green")
        table.add_column("Last Activity", style="yellow")

        total_cost = 0.0
        total_calls = 0
        total_input = 0
        total_output = 0

        for project_id in projects:
            cost = self.tracker.get_project_cost(project_id)

            total_cost += cost.total_cost
            total_calls += cost.total_calls
            total_input += cost.total_input_tokens
            total_output += cost.total_output_tokens

            table.add_row(
                project_id,
                str(cost.total_calls),
                f"{cost.total_input_tokens:,}",
                f"{cost.total_output_tokens:,}",
                f"${cost.total_cost:.4f}",
                cost.last_call.strftime("%Y-%m-%d"),
            )

        # Add totals row
        table.add_section()
        table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold]{total_calls}[/bold]",
            f"[bold]{total_input:,}[/bold]",
            f"[bold]{total_output:,}[/bold]",
            f"[bold green]${total_cost:.4f}[/bold green]",
            "",
        )

        self.console.print(table)

        # Summary stats
        avg_cost = total_cost / len(projects) if projects else 0
        self.console.print(
            f"\n[bold]Average cost per project:[/bold] [green]${avg_cost:.4f}[/green]"
        )

    def show_period_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period_name: str = "Period",
    ):
        """Display cost summary for a time period

        Args:
            start_date: Start date (None = all time)
            end_date: End date (None = now)
            period_name: Name of period for display
        """
        totals = self.tracker.get_total_costs(start_date, end_date)

        if totals["total_calls"] == 0:
            self.console.print(f"[yellow]No data for period: {period_name}[/yellow]")
            return

        summary_text = f"""[bold]{period_name} Summary[/bold]

[bold]Total Projects:[/bold] {totals['total_projects']}
[bold]Total API Calls:[/bold] {totals['total_calls']}

[bold]Token Usage:[/bold]
  • Input:  {totals['total_input_tokens']:,}
  • Output: {totals['total_output_tokens']:,}
  • Total:  {totals['total_input_tokens'] + totals['total_output_tokens']:,}

[bold]Total Cost:[/bold] [green]${totals['total_cost']:.2f}[/green]
[bold]Avg Cost per Project:[/bold] [cyan]${totals['avg_cost_per_project']:.4f}[/cyan]
"""

        panel = Panel(summary_text, border_style="blue")
        self.console.print(panel)

    def generate_markdown_report(
        self, output_path: Path, project_id: Optional[str] = None, include_calls: bool = False
    ):
        """Generate markdown cost report

        Args:
            output_path: Path to save report
            project_id: Optional specific project (None = all projects)
            include_calls: Include detailed call listing
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        lines.append("# Cost Report")
        lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        if project_id:
            # Single project report
            cost = self.tracker.get_project_cost(project_id)

            if cost.total_calls == 0:
                lines.append(f"No cost data found for project: {project_id}")
            else:
                lines.append(f"## Project: {project_id}\n")
                lines.append(f"**Total Cost:** ${cost.total_cost:.4f}\n")
                lines.append("### Token Usage\n")
                lines.append(f"- Input Tokens: {cost.total_input_tokens:,}")
                lines.append(f"- Output Tokens: {cost.total_output_tokens:,}")
                lines.append(f"- Cache Creation: {cost.total_cache_creation_tokens:,}")
                lines.append(f"- Cache Read: {cost.total_cache_read_tokens:,}")
                lines.append(
                    f"- **Total:** {cost.total_input_tokens + cost.total_output_tokens:,}\n"
                )

                lines.append("### Statistics\n")
                lines.append(f"- API Calls: {cost.total_calls}")
                lines.append(f"- First Call: {cost.first_call.strftime('%Y-%m-%d %H:%M:%S')}")
                lines.append(f"- Last Call: {cost.last_call.strftime('%Y-%m-%d %H:%M:%S')}")

                duration = cost.last_call - cost.first_call
                lines.append(f"- Duration: {self._format_duration(duration)}\n")

                if include_calls:
                    calls = self.tracker.get_project_calls(project_id)
                    lines.append("### API Calls\n")
                    lines.append("| Time | Operation | Input | Output | Cost |")
                    lines.append("|------|-----------|-------|--------|------|")
                    for call in calls:
                        lines.append(
                            f"| {call.timestamp.strftime('%H:%M:%S')} | "
                            f"{call.operation} | "
                            f"{call.input_tokens:,} | "
                            f"{call.output_tokens:,} | "
                            f"${call.cost:.4f} |"
                        )
        else:
            # All projects report
            totals = self.tracker.get_total_costs()
            projects = self.tracker.get_all_projects()

            lines.append("## Summary\n")
            lines.append(f"**Total Projects:** {totals['total_projects']}")
            lines.append(f"**Total API Calls:** {totals['total_calls']}")
            lines.append(f"**Total Cost:** ${totals['total_cost']:.2f}")
            lines.append(f"**Average Cost per Project:** ${totals['avg_cost_per_project']:.4f}\n")

            lines.append("## Projects\n")
            lines.append("| Project ID | Calls | Input Tokens | Output Tokens | Total Cost |")
            lines.append("|------------|-------|--------------|---------------|------------|")

            for proj_id in projects:
                cost = self.tracker.get_project_cost(proj_id)
                lines.append(
                    f"| {proj_id} | "
                    f"{cost.total_calls} | "
                    f"{cost.total_input_tokens:,} | "
                    f"{cost.total_output_tokens:,} | "
                    f"${cost.total_cost:.4f} |"
                )

        # Write file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Markdown report saved to {output_path}")
        self.console.print(f"[green]✓[/green] Report saved to {output_path}")

    def _format_duration(self, duration: timedelta) -> str:
        """Format duration in human-readable format"""
        total_seconds = int(duration.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds} seconds"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def _calculate_cache_savings(self, cost: ProjectCost) -> float:
        """Calculate cost savings from cache usage

        Cache reads cost ~10x less than input tokens
        """
        # Assume cached tokens would have been input tokens
        cache_read_cost = cost.total_cache_read_tokens / 1_000_000 * 0.0003
        would_have_cost = cost.total_cache_read_tokens / 1_000_000 * 0.003
        savings = would_have_cost - cache_read_cost

        return savings


# Convenience functions
def show_project_summary(project_id: str):
    """Show project summary (convenience function)"""
    dashboard = CostDashboard()
    dashboard.show_project_summary(project_id)


def show_all_projects():
    """Show all projects (convenience function)"""
    dashboard = CostDashboard()
    dashboard.show_all_projects()
