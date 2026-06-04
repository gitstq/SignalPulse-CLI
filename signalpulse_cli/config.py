"""
Configuration management for SignalPulse-CLI.

Handles loading, validating, and providing access to configuration
from YAML files, environment variables, and sensible defaults.
"""

import os
import copy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .utils import utc_now


# Default configuration values used when no config file is present
DEFAULT_CONFIG: Dict[str, Any] = {
    "sources": {
        "hackernews": {"enabled": True, "weight": 1.0, "limit": 30},
        "reddit": {
            "enabled": True,
            "weight": 1.0,
            "limit": 25,
            "subreddits": ["technology", "programming", "machinelearning"],
        },
        "github": {"enabled": True, "weight": 0.8, "limit": 25},
        "producthunt": {"enabled": True, "weight": 0.7, "limit": 20},
    },
    "scoring": {
        "weights": {
            "score": 0.5,
            "comments": 0.3,
            "recency": 0.2,
        },
        "recency_half_life_hours": 12.0,
    },
    "ai": {
        "provider": "openai",
        "api_key": "",
        "api_base": "https://api.openai.com/v1",
        "model": "gpt-3.5-turbo",
        "max_tokens": 2048,
        "temperature": 0.7,
        "top_n": 15,
    },
    "cache": {
        "enabled": True,
        "ttl_minutes": 60,
        "db_path": "~/.signalpulse/cache.db",
    },
    "output": {
        "format": "terminal",
        "theme": "dark",
        "max_items": 50,
    },
}


class Config:
    """Manages application configuration with layered overrides.

    Configuration is loaded from multiple sources in order of priority:
    1. CLI arguments (handled externally, passed via apply_overrides)
    2. Environment variables (SIGNALPULSE_*)
    3. User config file (~/.signalpulse/config.yaml)
    4. Built-in defaults

    Attributes:
        data: The merged configuration dictionary.
        config_path: Path to the loaded config file, if any.
    """

    def __init__(self) -> None:
        """Initialize config with defaults."""
        self.data: Dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self.config_path: Optional[Path] = None

    def load_file(self, path: Optional[str] = None) -> None:
        """Load configuration from a YAML file and merge with defaults.

        Searches for config in this order:
        1. Explicit path argument
        2. SIGNALPULSE_CONFIG environment variable
        3. ~/.signalpulse/config.yaml
        4. ./config.yaml (current directory)

        Args:
            path: Explicit path to a config file. If None, auto-detects.
        """
        config_path = self._find_config_file(path)
        if config_path is None:
            return

        self.config_path = config_path
        file_data = self._read_yaml_file(config_path)
        if file_data:
            self.data = self._deep_merge(self.data, file_data)

    def _find_config_file(self, path: Optional[str] = None) -> Optional[Path]:
        """Locate a configuration file.

        Args:
            path: Explicit path, or None to search standard locations.

        Returns:
            Path to the found config file, or None.
        """
        candidates: List[str] = []

        if path:
            candidates.append(path)

        env_path = os.environ.get("SIGNALPULSE_CONFIG")
        if env_path:
            candidates.append(env_path)

        home_config = Path.home() / ".signalpulse" / "config.yaml"
        candidates.append(str(home_config))

        local_config = Path.cwd() / "config.yaml"
        candidates.append(str(local_config))

        for candidate in candidates:
            p = Path(candidate).expanduser().resolve()
            if p.is_file():
                return p
        return None

    def _read_yaml_file(self, path: Path) -> Optional[Dict[str, Any]]:
        """Read and parse a YAML file.

        Attempts to use PyYAML if available, otherwise falls back to
        a simple manual parser for basic YAML structures.

        Args:
            path: Path to the YAML file.

        Returns:
            Parsed dictionary, or None if parsing fails.
        """
        try:
            content = path.read_text(encoding="utf-8")
        except (IOError, OSError) as e:
            print(f"[warning] Could not read config file {path}: {e}")
            return None

        # Try PyYAML first
        try:
            import yaml  # type: ignore

            return yaml.safe_load(content) or {}
        except ImportError:
            pass

        # Fallback: simple YAML-like parser for basic key-value structures
        return self._simple_yaml_parse(content)

    def _simple_yaml_parse(self, content: str) -> Dict[str, Any]:
        """Minimal YAML parser for basic nested structures.

        Supports key: value pairs, indentation-based nesting, and
        basic list items. Not a full YAML parser but handles common
        config file patterns.

        Args:
            content: YAML file content as string.

        Returns:
            Parsed dictionary.
        """
        result: Dict[str, Any] = {}
        stack: List[Tuple[int, Dict[str, Any]]] = [(0, result)]
        current_list_key: Optional[str] = None

        for line in content.splitlines():
            # Skip empty lines and comments
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Calculate indentation level
            indent = len(line) - len(line.lstrip())

            # Handle list items
            if stripped.startswith("- "):
                value = stripped[2:].strip().strip('"').strip("'")
                # Pop stack to correct level
                while stack and stack[-1][0] >= indent:
                    stack.pop()
                if stack:
                    parent = stack[-1][1]
                    # Find the last key in the parent that should receive list items
                    if isinstance(parent, dict):
                        last_key = list(parent.keys())[-1] if parent else None
                        if last_key and isinstance(parent.get(last_key), list):
                            parent[last_key].append(value)
                        elif last_key:
                            parent[last_key] = [value]
                continue

            # Handle key: value pairs
            if ":" in stripped:
                key_part, _, val_part = stripped.partition(":")
                key = key_part.strip()
                val = val_part.strip()

                # Pop stack to parent level
                while stack and stack[-1][0] >= indent:
                    stack.pop()

                if not stack:
                    continue

                parent = stack[-1][1]

                # Determine value type
                parsed_val: Any = val
                if val == "":
                    parsed_val = {}
                elif val.lower() == "true":
                    parsed_val = True
                elif val.lower() == "false":
                    parsed_val = False
                elif val.lower() == "null" or val == "~":
                    parsed_val = None
                elif val.startswith("[") and val.endswith("]"):
                    # Parse inline list
                    items = val[1:-1].split(",")
                    parsed_val = [
                        item.strip().strip('"').strip("'")
                        for item in items
                        if item.strip()
                    ]
                else:
                    # Try numeric conversion
                    try:
                        parsed_val = int(val)
                    except ValueError:
                        try:
                            parsed_val = float(val)
                        except ValueError:
                            parsed_val = val.strip('"').strip("'")

                if isinstance(parent, dict):
                    parent[key] = parsed_val
                    # If value is a dict placeholder, push onto stack
                    if isinstance(parsed_val, dict):
                        stack.append((indent, parsed_val))

        return result

    def apply_overrides(self, overrides: Dict[str, Any]) -> None:
        """Apply configuration overrides (typically from CLI arguments).

        Merges override values into the existing configuration using
        dot-notation keys.

        Args:
            overrides: Dictionary of override values. Keys can use dot
                       notation (e.g., "ai.model" -> "gpt-4").
        """
        for key, value in overrides.items():
            parts = key.split(".")
            target = self.data
            for part in parts[:-1]:
                if part not in target or not isinstance(target[part], dict):
                    target[part] = {}
                target = target[part]
            target[parts[-1]] = value

    def load_env_overrides(self) -> None:
        """Load configuration overrides from environment variables.

        Supported variables:
            SIGNALPULSE_AI_API_KEY - AI provider API key
            SIGNALPULSE_AI_MODEL - AI model name
            SIGNALPULSE_AI_PROVIDER - AI provider (openai/anthropic/ollama)
            SIGNALPULSE_AI_API_BASE - Custom API base URL
            SIGNALPULSE_CACHE_DB_PATH - Custom cache database path
        """
        env_map = {
            "SIGNALPULSE_AI_API_KEY": ("ai", "api_key"),
            "SIGNALPULSE_AI_MODEL": ("ai", "model"),
            "SIGNALPULSE_AI_PROVIDER": ("ai", "provider"),
            "SIGNALPULSE_AI_API_BASE": ("ai", "api_base"),
            "SIGNALPULSE_CACHE_DB_PATH": ("cache", "db_path"),
        }

        for env_var, (section, key) in env_map.items():
            value = os.environ.get(env_var)
            if value:
                if section not in self.data:
                    self.data[section] = {}
                self.data[section][key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot-notation key path.

        Args:
            key: Dot-notation key (e.g., "ai.model").
            default: Default value if key not found.

        Returns:
            The configuration value, or default.
        """
        parts = key.split(".")
        target = self.data
        for part in parts:
            if isinstance(target, dict) and part in target:
                target = target[part]
            else:
                return default
        return target

    def get_source_config(self, source_name: str) -> Dict[str, Any]:
        """Get configuration for a specific data source.

        Args:
            source_name: Name of the source (e.g., "hackernews").

        Returns:
            Source-specific configuration dictionary.
        """
        sources = self.data.get("sources", {})
        source_config = sources.get(source_name, {})
        # Ensure defaults for common fields
        return {
            "enabled": source_config.get("enabled", True),
            "weight": source_config.get("weight", 1.0),
            "limit": source_config.get("limit", 25),
            **source_config,
        }

    def get_enabled_sources(self) -> List[str]:
        """Get list of enabled data source names.

        Returns:
            List of source names that are enabled in config.
        """
        sources = self.data.get("sources", {})
        return [
            name
            for name, config in sources.items()
            if isinstance(config, dict) and config.get("enabled", True)
        ]

    def get_cache_path(self) -> Path:
        """Get the resolved cache database path.

        Returns:
            Path object for the SQLite cache database.
        """
        db_path = self.get("cache.db_path", "~/.signalpulse/cache.db")
        return Path(db_path).expanduser().resolve()

    def ensure_cache_dir(self) -> Path:
        """Ensure the cache directory exists and return its path.

        Returns:
            Path to the cache directory.
        """
        cache_path = self.get_cache_path()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        return cache_path.parent

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries. Override values take precedence.

        Args:
            base: Base dictionary.
            override: Override dictionary.

        Returns:
            Merged dictionary.
        """
        result = copy.deepcopy(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = Config._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    def __repr__(self) -> str:
        """String representation of the config."""
        return f"Config(path={self.config_path})"
