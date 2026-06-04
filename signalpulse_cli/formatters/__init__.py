"""
Output formatter modules for SignalPulse-CLI.

Provides multiple output formats for displaying signal data:
terminal (Rich TUI), Markdown, and HTML reports.
"""

from .terminal import TerminalFormatter
from .markdown import MarkdownFormatter
from .html import HTMLFormatter

__all__ = [
    "TerminalFormatter",
    "MarkdownFormatter",
    "HTMLFormatter",
]

# Formatter registry: maps format names to their classes
FORMATTER_REGISTRY: dict = {
    "terminal": TerminalFormatter,
    "markdown": MarkdownFormatter,
    "html": HTMLFormatter,
}


def get_formatter(name: str, config: "Config") -> "Formatter":  # type: ignore
    """Factory function to instantiate a formatter by name.

    Args:
        name: The registered formatter name (e.g., "terminal").
        config: Application configuration.

    Returns:
        An instance of the requested formatter.

    Raises:
        ValueError: If the formatter name is not recognized.
    """
    if name not in FORMATTER_REGISTRY:
        available = ", ".join(sorted(FORMATTER_REGISTRY.keys()))
        raise ValueError(
            f"Unknown format '{name}'. Available formats: {available}"
        )
    return FORMATTER_REGISTRY[name](config=config)
