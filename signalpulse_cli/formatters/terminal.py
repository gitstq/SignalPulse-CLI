"""
Terminal output formatter for SignalPulse-CLI.

Uses the Rich library to render signal data as beautiful terminal
output with colored tables, progress bars, panels, and markdown.
"""

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.markdown import Markdown
from rich.progress import BarColumn, Progress
from rich.text import Text
from rich import box

from ..config import Config
from ..sources.base import SignalItem
from ..utils import format_relative_time, format_number, extract_domain


# Source display configuration: icon, color, label
SOURCE_STYLES: Dict[str, Dict[str, str]] = {
    "hackernews": {"icon": "[orange3]HN[/orange3]", "label": "Hacker News"},
    "reddit": {"icon": "[red]RD[/red]", "label": "Reddit"},
    "github": {"icon": "[green]GH[/green]", "label": "GitHub"},
    "producthunt": {"icon": "[blue3]PH[/blue3]", "label": "Product Hunt"},
}


class TerminalFormatter:
    """Rich terminal output formatter.

    Renders signal items and AI briefings as colorful, well-structured
    terminal output using the Rich library.

    Attributes:
        config: Application configuration.
        console: Rich Console instance for output.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the terminal formatter.

        Args:
            config: Application configuration.
        """
        self.config = config
        self.console = Console()

    def render_items(self, items: List[SignalItem], title: str = "Signal Pulse") -> None:
        """Render a list of signal items as a Rich table.

        Displays each item with its source icon, score bar, title,
        URL domain, and relative time.

        Args:
            items: List of scored SignalItem objects.
            title: Header title for the output.
        """
        # Print header
        self.console.print()
        header = Text()
        header.append("  SignalPulse", style="bold cyan")
        header.append(f"  |  {len(items)} signals aggregated", style="dim")
        self.console.print(Panel(header, box=box.ROUNDED))
        self.console.print()

        if not items:
            self.console.print(
                "[yellow]No signals found. Try again later.[/yellow]"
            )
            return

        # Create main table
        table = Table(
            show_header=True,
            header_style="bold magenta",
            box=box.SIMPLE,
            padding=(0, 1),
            title=title,
        )
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("Source", width=6)
        table.add_column("Score", width=8)
        table.add_column("Title", min_width=40, no_wrap=False)
        table.add_column("Domain", width=25, style="dim")
        table.add_column("Age", width=8, justify="right")
        table.add_column("Cmt", width=5, justify="right")

        for i, item in enumerate(items, 1):
            # Source icon
            source_style = SOURCE_STYLES.get(item.source, {})
            source_icon = source_style.get("icon", f"[dim]{item.source[:2].upper()}[/dim]")

            # Score bar (visual representation)
            score_bar = self._render_score_bar(item.normalized_score)

            # Title (truncated for display)
            title_text = item.title[:80] + "..." if len(item.title) > 80 else item.title

            # Domain
            domain = extract_domain(item.url) if item.url else ""

            # Age
            age = format_relative_time(item.created_at)

            # Comments
            comments = format_number(item.comments)

            table.add_row(
                str(i),
                source_icon,
                score_bar,
                title_text,
                domain,
                age,
                comments,
            )

        self.console.print(table)
        self.console.print()

    def render_briefing(self, briefing: str) -> None:
        """Render an AI-generated briefing as Rich markdown.

        Args:
            briefing: Markdown-formatted briefing text.
        """
        self.console.print()
        self.console.print(
            Panel(
                "[bold cyan]AI Intelligence Briefing[/bold cyan]",
                box=box.DOUBLE,
            )
        )
        self.console.print()

        # Render as markdown with Rich
        md = Markdown(briefing)
        self.console.print(md)
        self.console.print()

    def render_summary(self, items: List[SignalItem]) -> None:
        """Render a summary panel showing per-source statistics.

        Args:
            items: List of SignalItem objects.
        """
        # Count items per source
        source_counts: Dict[str, int] = {}
        for item in items:
            source_counts[item.source] = source_counts.get(item.source, 0) + 1

        # Build summary text
        summary_parts: List[str] = []
        for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            style = SOURCE_STYLES.get(source, {})
            label = style.get("label", source.capitalize())
            summary_parts.append(f"[bold]{label}[/bold]: {count} items")

        summary_text = "  |  ".join(summary_parts)

        self.console.print(
            Panel(summary_text, title="[bold]Sources[/bold]", box=box.SIMPLE)
        )

    def render_error(self, message: str) -> None:
        """Render an error message.

        Args:
            message: Error message to display.
        """
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def render_warning(self, message: str) -> None:
        """Render a warning message.

        Args:
            message: Warning message to display.
        """
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")

    def render_info(self, message: str) -> None:
        """Render an informational message.

        Args:
            message: Info message to display.
        """
        self.console.print(f"[bold blue]Info:[/bold blue] {message}")

    def render_progress(
        self, current: int, total: int, label: str = ""
    ) -> None:
        """Render a progress indicator.

        Args:
            current: Current progress count.
            total: Total items to process.
            label: Optional label for the progress bar.
        """
        if total > 0:
            pct = int((current / total) * 100)
            bar_width = 30
            filled = int((current / total) * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            self.console.print(
                f"  {label} [{cyan}{bar}[/cyan] {pct}%] "
                f"({current}/{total})",
                end="\r",
            )
            if current >= total:
                self.console.print()  # New line after completion

    def _render_score_bar(self, score: float) -> Text:
        """Render a score as a colored progress bar.

        Args:
            score: Normalized score between 0.0 and 1.0.

        Returns:
            Rich Text object with colored bar.
        """
        bar_width = 6
        filled = int(score * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Color based on score intensity
        if score >= 0.8:
            color = "bold red"
        elif score >= 0.6:
            color = "bold yellow"
        elif score >= 0.4:
            color = "green"
        else:
            color = "dim"

        text = Text()
        text.append(bar, style=color)
        text.append(f" {score:.0%}", style=color)
        return text
