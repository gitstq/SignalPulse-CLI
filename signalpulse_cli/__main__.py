"""
Main entry point for SignalPulse-CLI.

Provides the primary application logic that orchestrates data
fetching, scoring, AI synthesis, and output formatting.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import __version__
from .cli import parse_args, parse_source_names
from .config import Config, DEFAULT_CONFIG
from .cache import CacheManager
from .sources import get_source, SOURCE_REGISTRY
from .sources.base import SignalItem
from .scoring import ScoringEngine
from .synthesis import Synthesizer
from .formatters import get_formatter
from .utils import utc_now


class SignalPulseApp:
    """Main application class for SignalPulse-CLI.

    Orchestrates the complete workflow: configuration loading,
    data fetching from multiple sources, scoring, optional AI
    synthesis, and output formatting.

    Attributes:
        config: Application configuration.
        cache: Cache manager instance.
        args: Parsed CLI arguments.
    """

    def __init__(self, args: Optional[Any] = None) -> None:
        """Initialize the application.

        Args:
            args: Parsed CLI arguments (uses sys.argv if None).
        """
        self.args = args if args is not None else parse_args()
        self.config = Config()
        self._setup_config()
        self.cache = CacheManager(self.config)

    def _setup_config(self) -> None:
        """Load configuration from file, environment, and CLI overrides."""
        # Load from file
        self.config.load_file(path=self.args.config)

        # Load environment variable overrides
        self.config.load_env_overrides()

        # Apply CLI argument overrides
        overrides: Dict[str, Any] = {}

        # Disable cache if --no-cache flag is set
        if getattr(self.args, "no_cache", False):
            overrides["cache.enabled"] = False

        # AI provider/model overrides
        if getattr(self.args, "provider", None):
            overrides["ai.provider"] = self.args.provider
        if getattr(self.args, "model", None):
            overrides["ai.model"] = self.args.model
        if getattr(self.args, "top_n", None):
            overrides["ai.top_n"] = self.args.top_n

        # Output format override
        if getattr(self.args, "format", None):
            overrides["output.format"] = self.args.format

        # Max items override
        if getattr(self.args, "limit", None):
            overrides["output.max_items"] = self.args.limit

        self.config.apply_overrides(overrides)

    def run(self) -> int:
        """Execute the requested command.

        Dispatches to the appropriate handler based on the
        CLI subcommand.

        Returns:
            Exit code (0 for success, 1 for errors).
        """
        command = self.args.command

        try:
            if command == "fetch":
                return self._cmd_fetch()
            elif command == "brief":
                return self._cmd_brief()
            elif command == "report":
                return self._cmd_report()
            elif command == "config":
                return self._cmd_config()
            else:
                print(f"Unknown command: {command}")
                return 1
        except KeyboardInterrupt:
            print("\n[info] Operation cancelled by user")
            return 130
        except Exception as e:
            print(f"[error] Unexpected error: {e}")
            if getattr(self.args, "verbose", False):
                import traceback
                traceback.print_exc()
            return 1
        finally:
            self.cache.close()

    def _get_enabled_source_names(self) -> List[str]:
        """Determine which sources to fetch based on config and CLI args.

        Returns:
            List of source names to fetch from.
        """
        # CLI override
        cli_sources = getattr(self.args, "sources", None)
        if cli_sources:
            parsed = parse_source_names(cli_sources)
            if parsed:
                return parsed

        # Config defaults
        return self.config.get_enabled_sources()

    def _fetch_all_sources(self) -> List[SignalItem]:
        """Fetch items from all enabled sources.

        Iterates through enabled sources, fetching items with
        progress indication. Handles source failures gracefully.

        Returns:
            Combined list of SignalItem objects from all sources.
        """
        source_names = self._get_enabled_source_names()
        all_items: List[SignalItem] = []
        total_sources = len(source_names)

        for i, source_name in enumerate(source_names, 1):
            if source_name not in SOURCE_REGISTRY:
                print(f"[warning] Unknown source: {source_name}, skipping")
                continue

            source_label = source_name.capitalize()
            print(f"  [{i}/{total_sources}] Fetching from {source_label}...", end="")

            try:
                source = get_source(source_name, self.config, self.cache)
                items = source.fetch()
                source.close()
                print(f" {len(items)} items")
                all_items.extend(items)
            except Exception as e:
                print(f" failed: {e}")
                if getattr(self.args, "verbose", False):
                    import traceback
                    traceback.print_exc()

        return all_items

    def _score_items(self, items: List[SignalItem]) -> List[SignalItem]:
        """Score and rank items using the scoring engine.

        Args:
            items: Raw SignalItem objects.

        Returns:
            Scored and sorted list of SignalItem objects.
        """
        if getattr(self.args, "no_score", False):
            return items

        engine = ScoringEngine(self.config)
        scored = engine.score_items(items)

        # Apply sort override if specified
        sort_by = getattr(self.args, "sort", "score")
        if sort_by == "time":
            scored.sort(
                key=lambda x: x.created_at or utc_now(),
                reverse=True,
            )
        elif sort_by == "comments":
            scored.sort(key=lambda x: x.comments, reverse=True)

        return scored

    def _cmd_fetch(self) -> int:
        """Handle the 'fetch' command.

        Fetches items from all sources, scores them, and displays
        in the terminal.

        Returns:
            Exit code.
        """
        print("\n[SignalPulse] Fetching trending signals...\n")

        # Fetch from all sources
        items = self._fetch_all_sources()

        if not items:
            print("[warning] No items fetched from any source")
            return 0

        # Score and rank
        items = self._score_items(items)

        # Apply limit
        max_items = self.config.get("output.max_items", 50)
        cli_limit = getattr(self.args, "limit", None)
        limit = cli_limit if cli_limit else max_items
        items = items[:limit]

        # Display in terminal
        formatter = get_formatter("terminal", self.config)
        formatter.render_items(items, title="Trending Signals")
        formatter.render_summary(items)

        return 0

    def _cmd_brief(self) -> int:
        """Handle the 'brief' command.

        Fetches items, scores them, generates an AI briefing,
        and displays the result.

        Returns:
            Exit code.
        """
        print("\n[SignalPulse] Generating intelligence briefing...\n")

        # Fetch from all sources
        items = self._fetch_all_sources()

        if not items:
            print("[warning] No items fetched from any source")
            return 0

        # Score and rank
        items = self._score_items(items)

        # Display fetched items summary
        formatter = get_formatter("terminal", self.config)
        formatter.render_summary(items)
        print()

        # Generate AI briefing
        synthesizer = Synthesizer(self.config)
        briefing = synthesizer.synthesize(items)

        if briefing:
            formatter.render_briefing(briefing)
        else:
            print(
                "[info] AI briefing not generated. "
                "Configure your AI provider in config.yaml or "
                "set SIGNALPULSE_AI_API_KEY environment variable."
            )

        return 0

    def _cmd_report(self) -> int:
        """Handle the 'report' command.

        Generates a full report in the specified format (terminal,
        markdown, or HTML) with optional AI briefing.

        Returns:
            Exit code.
        """
        output_format = getattr(self.args, "format", "terminal")
        output_path = getattr(self.args, "output", None)
        title = getattr(self.args, "title", "SignalPulse Intelligence Report")

        print(f"\n[SignalPulse] Generating {output_format} report...\n")

        # Fetch from all sources
        items = self._fetch_all_sources()

        if not items:
            print("[warning] No items fetched from any source")
            return 0

        # Score and rank
        items = self._score_items(items)

        # Apply limit
        max_items = self.config.get("output.max_items", 50)
        cli_limit = getattr(self.args, "limit", None)
        limit = cli_limit if cli_limit else max_items
        items = items[:limit]

        # Optional AI briefing
        briefing: Optional[str] = None
        if getattr(self.args, "with_briefing", False):
            print("\n[info] Generating AI briefing...")
            synthesizer = Synthesizer(self.config)
            briefing = synthesizer.synthesize(items)
            if briefing:
                print("[info] Briefing generated successfully")
            else:
                print("[warning] AI briefing generation failed")

        # Format output
        formatter = get_formatter(output_format, self.config)

        if output_format == "terminal":
            formatter.render_items(items, title=title)
            formatter.render_summary(items)
            if briefing:
                formatter.render_briefing(briefing)
        elif output_format == "markdown":
            report = formatter.render_full_report(items, briefing)
            self._write_output(report, output_path, "md")
        elif output_format == "html":
            report = formatter.render_full_report(items, briefing)
            self._write_output(report, output_path, "html")

        return 0

    def _cmd_config(self) -> int:
        """Handle the 'config' command.

        Manages configuration: show, init, path, cache operations.

        Returns:
            Exit code.
        """
        config_command = getattr(self.args, "config_command", None)

        if config_command == "show":
            return self._config_show()
        elif config_command == "init":
            return self._config_init()
        elif config_command == "path":
            return self._config_path()
        elif config_command == "cache":
            return self._config_cache()
        else:
            print("Usage: signalpulse config {show|init|path|cache}")
            return 1

    def _config_show(self) -> int:
        """Display current configuration with API keys masked.

        Returns:
            Exit code.
        """
        import json

        config_data = dict(self.config.data)

        # Mask sensitive values
        def mask_sensitive(obj: Any) -> Any:
            """Recursively mask API keys and secrets in config dict."""
            if isinstance(obj, dict):
                result = {}
                for key, value in obj.items():
                    if any(
                        sensitive in key.lower()
                        for sensitive in ("key", "secret", "token", "password")
                    ):
                        if isinstance(value, str) and value:
                            result[key] = value[:4] + "****" + value[-4:] if len(value) > 8 else "****"
                        else:
                            result[key] = value
                    else:
                        result[key] = mask_sensitive(value)
                return result
            elif isinstance(obj, list):
                return [mask_sensitive(item) for item in obj]
            return obj

        masked = mask_sensitive(config_data)
        print(json.dumps(masked, indent=2, default=str))
        return 0

    def _config_init(self) -> int:
        """Create a default configuration file.

        Returns:
            Exit code.
        """
        force = getattr(self.args, "force", False)
        custom_path = getattr(self.args, "path", None)

        if custom_path:
            config_path = Path(custom_path).expanduser().resolve()
        else:
            config_path = Path.home() / ".signalpulse" / "config.yaml"

        if config_path.exists() and not force:
            print(
                f"[warning] Config file already exists at {config_path}\n"
                "Use --force to overwrite."
            )
            return 1

        # Generate default config content
        default_content = self._generate_default_config()

        # Write the config file
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(default_content, encoding="utf-8")
        print(f"[info] Configuration file created at {config_path}")
        return 0

    def _config_path(self) -> int:
        """Show the configuration file path.

        Returns:
            Exit code.
        """
        if self.config.config_path:
            print(str(self.config.config_path))
        else:
            default_path = Path.home() / ".signalpulse" / "config.yaml"
            print(f"No config file found. Default location: {default_path}")
            print("Run 'signalpulse config init' to create one.")
        return 0

    def _config_cache(self) -> int:
        """Handle cache management subcommands.

        Returns:
            Exit code.
        """
        cache_command = getattr(self.args, "cache_command", None)

        if cache_command == "stats":
            stats = self.cache.stats()
            print("Cache Statistics:")
            print(f"  Enabled: {stats.get('enabled', False)}")
            print(f"  Total items: {stats.get('total', 0)}")
            print(f"  Active items: {stats.get('active', 0)}")
            print(f"  Expired items: {stats.get('expired', 0)}")
            sources = stats.get("sources", {})
            if sources:
                print("  Per-source breakdown:")
                for source, count in sorted(sources.items()):
                    print(f"    {source}: {count} items")
            return 0

        elif cache_command == "clear":
            removed = self.cache.clear()
            print(f"[info] Cleared {removed} cached items")
            return 0

        elif cache_command == "cleanup":
            removed = self.cache.cleanup()
            print(f"[info] Removed {removed} expired items")
            return 0

        else:
            print("Usage: signalpulse config cache {stats|clear|cleanup}")
            return 1

    def _write_output(
        self, content: str, output_path: Optional[str], default_ext: str
    ) -> None:
        """Write report content to a file or stdout.

        Args:
            content: Report content string.
            output_path: File path, or None for stdout.
            default_ext: Default file extension.
        """
        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"\n[info] Report saved to {path}")
        else:
            # Default filename
            timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
            default_name = f"signalpulse_report_{timestamp}.{default_ext}"
            path = Path.cwd() / default_name
            path.write_text(content, encoding="utf-8")
            print(f"\n[info] Report saved to {path}")

    @staticmethod
    def _generate_default_config() -> str:
        """Generate a default YAML configuration file content.

        Returns:
            YAML configuration string.
        """
        return """# SignalPulse-CLI Configuration
# Copy this file to ~/.signalpulse/config.yaml and customize

# Data sources configuration
sources:
  hackernews:
    enabled: true
    weight: 1.0
    limit: 30
  reddit:
    enabled: true
    weight: 1.0
    limit: 25
    subreddits:
      - technology
      - programming
      - machinelearning
  github:
    enabled: true
    weight: 0.8
    limit: 25
  producthunt:
    enabled: true
    weight: 0.7
    limit: 20

# Scoring configuration
scoring:
  weights:
    score: 0.5       # Raw engagement score weight
    comments: 0.3    # Comment count weight
    recency: 0.2     # Time decay weight
  recency_half_life_hours: 12.0  # Half-life for recency decay

# AI synthesis configuration
ai:
  provider: openai    # openai, anthropic, or ollama
  api_key: ""         # Set via env var SIGNALPULSE_AI_API_KEY
  api_base: "https://api.openai.com/v1"
  model: gpt-3.5-turbo
  max_tokens: 2048
  temperature: 0.7
  top_n: 15           # Number of items to send to AI

# Cache configuration
cache:
  enabled: true
  ttl_minutes: 60     # Cache items for 1 hour
  db_path: ~/.signalpulse/cache.db

# Output configuration
output:
  format: terminal    # terminal, markdown, or html
  theme: dark
  max_items: 50
"""


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for SignalPulse-CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code.
    """
    args = parse_args(argv)
    app = SignalPulseApp(args)
    return app.run()
