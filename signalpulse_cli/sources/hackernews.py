"""
Hacker News data source for SignalPulse-CLI.

Fetches trending stories from the Hacker News Firebase API
(https://hacker-news.firebaseio.com/v0/) and converts them
into SignalItem objects.
"""

from typing import Any, Dict, List, Optional

from .base import BaseSource, SignalItem
from ..config import Config
from ..cache import CacheManager
from ..utils import timestamp_to_datetime


class HackerNewsSource(BaseSource):
    """Data source adapter for Hacker News.

    Uses the official HN Firebase API to fetch top and new stories,
    then retrieves individual item details including title, URL,
    score, author, and comment count.

    API Base: https://hacker-news.firebaseio.com/v0/
    """

    API_BASE = "https://hacker-news.firebaseio.com/v0"

    def __init__(self, config: Config, cache: CacheManager) -> None:
        """Initialize the Hacker News source.

        Args:
            config: Application configuration.
            cache: Cache manager instance.
        """
        super().__init__(config, cache)
        self.name = "hackernews"

    def fetch(self, limit: int = 25) -> List[SignalItem]:
        """Fetch top stories from Hacker News.

        Retrieves the top story IDs, then fetches details for each
        story up to the specified limit. Uses caching to avoid
        re-fetching unchanged items.

        Args:
            limit: Maximum number of stories to return.

        Returns:
            List of SignalItem objects for top HN stories.
        """
        source_config = self.config.get_source_config("hackernews")
        limit = source_config.get("limit", limit)

        # Fetch top story IDs
        story_ids = self._get_json(f"{self.API_BASE}/topstories.json")
        if story_ids is None or not isinstance(story_ids, list):
            print("[warning] Failed to fetch HN top stories list")
            return []

        items: List[SignalItem] = []
        story_ids = story_ids[:limit]

        # Fetch details for each story
        for story_id in story_ids:
            # Check cache first
            cached = self.cache.get(self.name, str(story_id))
            if cached:
                item = SignalItem.from_dict({
                    "source": self.name,
                    "item_id": str(story_id),
                    "title": cached["title"],
                    "url": cached["url"],
                    "score": cached["score"],
                    "comments": cached["metadata"].get("comments", 0),
                    "author": cached["metadata"].get("author"),
                    "created_at": cached["metadata"].get("created_at"),
                })
                items.append(item)
                continue

            # Fetch item details from API
            detail = self._get_json(
                f"{self.API_BASE}/item/{story_id}.json"
            )
            if detail is None:
                continue

            item = self._parse_item(detail)
            if item:
                items.append(item)
                # Cache the item
                self.cache.set(
                    source=self.name,
                    item_id=str(story_id),
                    title=item.title,
                    url=item.url,
                    score=item.score,
                    metadata={
                        "comments": item.comments,
                        "author": item.author,
                        "created_at": (
                            item.created_at.isoformat()
                            if item.created_at else None
                        ),
                    },
                )

        return items

    def _parse_item(self, data: Dict[str, Any]) -> Optional[SignalItem]:
        """Parse a Hacker News API item into a SignalItem.

        Handles both story and job types. Filters out items
        without titles or Ask HN posts without URLs.

        Args:
            data: Raw item data from the HN API.

        Returns:
            A SignalItem, or None if the item should be skipped.
        """
        # Skip non-story items (polls, etc.) but keep Ask HN
        item_type = data.get("type", "")
        if item_type not in ("story", "job", "poll"):
            return None

        title = data.get("title", "").strip()
        if not title:
            return None

        # Use the HN comments page URL if no external URL
        url = data.get("url")
        if not url:
            hn_id = data.get("id", "")
            url = f"https://news.ycombinator.com/item?id={hn_id}"

        # Parse creation timestamp
        created_at = None
        if data.get("time"):
            created_at = timestamp_to_datetime(data["time"])

        return SignalItem(
            source=self.name,
            item_id=str(data.get("id", "")),
            title=title,
            url=url,
            score=float(data.get("score", 0)),
            comments=int(data.get("descendants", 0)),
            author=data.get("by"),
            created_at=created_at,
            metadata={
                "type": item_type,
                "hn_id": data.get("id"),
            },
        )
