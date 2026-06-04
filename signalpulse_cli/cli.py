"""
CLI argument parsing for SignalPulse-CLI.

Provides the command-line interface with subcommands for fetching
data, generating AI briefings, producing reports, and managing
configuration.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def build_parser() -> argparse.ArgumentParser:
    """Build the main argument parser with all subcommands.

    Creates a hierarchical argument parser with the following commands:
    - fetch: Fetch and display trending signals from all sources
    - brief: Generate an AI-powered intelligence briefing
    - report: Generate a full report in various formats
    - config: Manage configuration (show, init, path)

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="signalpulse",
        description=(
            "SignalPulse-CLI: Lightweight terminal-based cross-platform "
            "social signal aggregation and AI-powered briefing engine."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  signalpulse fetch                    # Fetch trending signals\n"
            "  signalpulse fetch --limit 50        # Fetch more items\n"
            "  signalpulse brief                    # Generate AI briefing\n"
            "  signalpulse report --format html    # Export as HTML\n"
            "  signalpulse report -o report.md     # Save to file\n"
            "  signalpulse config show              # Show current config\n"
            "  signalpulse config init              # Create default config\n"
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_get_version()}",
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="Path to configuration file (default: auto-detect)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose output",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        default=False,
        help="Disable caching for this run",
    )

    # Subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        title="Commands",
        description="Available commands",
        metavar="COMMAND",
    )

    # 'fetch' command
    fetch_parser = subparsers.add_parser(
        "fetch",
        help="Fetch trending signals from all sources",
        description="Fetch and display trending topics from configured sources.",
    )
    fetch_parser.add_argument(
        "-l", "--limit",
        type=int,
        default=None,
        help="Maximum number of items per source (default: from config)",
    )
    fetch_parser.add_argument(
        "-s", "--sources",
        type=str,
        default=None,
        help="Comma-separated list of sources to fetch (e.g., hn,reddit,gh,ph)",
    )
    fetch_parser.add_argument(
        "--sort",
        type=str,
        choices=["score", "time", "comments"],
        default="score",
        help="Sort items by field (default: score)",
    )
    fetch_parser.add_argument(
        "--no-score",
        action="store_true",
        default=False,
        help="Skip scoring and show raw results",
    )

    # 'brief' command
    brief_parser = subparsers.add_parser(
        "brief",
        help="Generate an AI-powered intelligence briefing",
        description="Fetch signals and generate an AI synthesis briefing.",
    )
    brief_parser.add_argument(
        "-l", "--limit",
        type=int,
        default=None,
        help="Maximum number of items to include in briefing context",
    )
    brief_parser.add_argument(
        "-s", "--sources",
        type=str,
        default=None,
        help="Comma-separated list of sources to include",
    )
    brief_parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override AI model name",
    )
    brief_parser.add_argument(
        "--provider",
        type=str,
        choices=["openai", "anthropic", "ollama"],
        default=None,
        help="Override AI provider",
    )
    brief_parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Number of top items to send to AI (default: from config)",
    )

    # 'report' command
    report_parser = subparsers.add_parser(
        "report",
        help="Generate a report in various formats",
        description="Generate a full report with optional AI briefing.",
    )
    report_parser.add_argument(
        "-f", "--format",
        type=str,
        choices=["terminal", "markdown", "html"],
        default="terminal",
        help="Output format (default: terminal)",
    )
    report_parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout for terminal)",
    )
    report_parser.add_argument(
        "-l", "--limit",
        type=int,
        default=None,
        help="Maximum number of items to include",
    )
    report_parser.add_argument(
        "-s", "--sources",
        type=str,
        default=None,
        help="Comma-separated list of sources to include",
    )
    report_parser.add_argument(
        "--with-briefing",
        action="store_true",
        default=False,
        help="Include AI briefing in the report",
    )
    report_parser.add_argument(
        "--title",
        type=str,
        default="SignalPulse Intelligence Report",
        help="Report title",
    )

    # 'config' command
    config_parser = subparsers.add_parser(
        "config",
        help="Manage configuration",
        description="View and manage SignalPulse configuration.",
    )
    config_subparsers = config_parser.add_subparsers(
        dest="config_command",
        title="Config Commands",
        metavar="COMMAND",
    )

    # config show
    config_subparsers.add_parser(
        "show",
        help="Show current configuration (with API keys masked)",
    )

    # config init
    init_parser = config_subparsers.add_parser(
        "init",
        help="Create a default configuration file",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Overwrite existing config file",
    )
    init_parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Custom path for the config file",
    )

    # config path
    config_subparsers.add_parser(
        "path",
        help="Show the configuration file path",
    )

    # config cache
    cache_parser = config_subparsers.add_parser(
        "cache",
        help="Manage the local cache",
    )
    cache_subparsers = cache_parser.add_subparsers(
        dest="cache_command",
        title="Cache Commands",
        metavar="COMMAND",
    )
    cache_subparsers.add_parser(
        "stats",
        help="Show cache statistics",
    )
    cache_subparsers.add_parser(
        "clear",
        help="Clear all cached data",
    )
    cache_subparsers.add_parser(
        "cleanup",
        help="Remove expired cache entries",
    )

    return parser


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed arguments namespace.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Handle no command case
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    return args


def parse_source_names(source_str: Optional[str]) -> Optional[List[str]]:
    """Parse a comma-separated source string into a list.

    Supports both full names and abbreviations:
    - hn -> hackernews
    - reddit, rd -> reddit
    - github, gh -> github
    - producthunt, ph -> producthunt

    Args:
        source_str: Comma-separated source names/abbreviations.

    Returns:
        List of normalized source names, or None if input is None.
    """
    if source_str is None:
        return None

    name_map = {
        "hn": "hackernews",
        "hackernews": "hackernews",
        "reddit": "reddit",
        "rd": "reddit",
        "github": "github",
        "gh": "github",
        "producthunt": "producthunt",
        "ph": "producthunt",
    }

    names = []
    for part in source_str.lower().split(","):
        part = part.strip()
        if part in name_map:
            names.append(name_map[part])
        else:
            print(f"[warning] Unknown source: '{part}', skipping")

    return names if names else None


def _get_version() -> str:
    """Get the package version string.

    Returns:
        Version string from the package.
    """
    try:
        from . import __version__
        return __version__
    except ImportError:
        return "unknown"
