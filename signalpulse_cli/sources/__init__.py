"""
Source modules for SignalPulse-CLI.

Provides data source adapters for fetching trending topics from
various platforms.
"""

from .base import BaseSource, SignalItem
from .hackernews import HackerNewsSource
from .reddit import RedditSource
from .github import GitHubSource
from .producthunt import ProductHuntSource

__all__ = [
    "BaseSource",
    "SignalItem",
    "HackerNewsSource",
    "RedditSource",
    "GitHubSource",
    "ProductHuntSource",
]

# Source registry: maps source names to their implementation classes
SOURCE_REGISTRY: dict = {
    "hackernews": HackerNewsSource,
    "reddit": RedditSource,
    "github": GitHubSource,
    "producthunt": ProductHuntSource,
}


def get_source(name: str, config: "Config", cache: "CacheManager") -> BaseSource:  # type: ignore
    """Factory function to instantiate a data source by name.

    Args:
        name: The registered source name (e.g., "hackernews").
        config: Application configuration.
        cache: Cache manager instance.

    Returns:
        An instance of the requested source.

    Raises:
        ValueError: If the source name is not recognized.
    """
    if name not in SOURCE_REGISTRY:
        available = ", ".join(sorted(SOURCE_REGISTRY.keys()))
        raise ValueError(
            f"Unknown source '{name}'. Available sources: {available}"
        )
    return SOURCE_REGISTRY[name](config=config, cache=cache)
