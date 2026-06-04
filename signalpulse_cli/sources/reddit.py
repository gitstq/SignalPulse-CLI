"""
Reddit data source for SignalPulse-CLI.

Fetches hot/trending posts from specified subreddits using Reddit's
JSON API (no authentication required for public content).
"""

from typing import Any, Dict, List, Optional

from .base import BaseSource, SignalItem
from ..config import Config
from ..cache import CacheManager
from ..utils import timestamp_to_datetime


class RedditSource(BaseSource):
    """Data source adapter for Reddit.

    Uses Reddit's JSON API to fetch hot posts from configurable
    subreddits. No OAuth or API key required for public content.

    API Base: https://www.reddit.com/r/{subreddit}/hot.json
    """

    API_BASE = "https://www.reddit.com"

    def __init__(self, config: Config, cache: CacheManager) -> None:
        """Initialize the Reddit source.

        Args:
            config: Application configuration.
            cache: Cache manager instance.
        """
        super().__init__(config, cache)
        self.name = "reddit"
        # Override Accept header for Reddit
        self.session.headers.update({
            "Accept": "application/json, text/html, */*",
        })

    def fetch(self, limit: int = 25) -> List[SignalItem]:
        """Fetch hot posts from configured subreddits.

        Iterates through each configured subreddit and fetches
        hot posts. Deduplicates across subreddits by post ID.

        Args:
            limit: Maximum total number of posts to return.

        Returns:
            List of SignalItem objects from Reddit.
        """
        source_config = self.config.get_source_config("reddit")
        subreddits = source_config.get(
            "subreddits", ["technology", "programming", "machinelearning"]
        )
        per_subreddit_limit = max(5, limit // max(len(subreddits), 1))

        items: List[SignalItem] = []
        seen_ids: set = set()

        for subreddit in subreddits:
            subreddit_items = self._fetch_subreddit(
                subreddit, limit=per_subreddit_limit
            )
            for item in subreddit_items:
                if item.item_id not in seen_ids:
                    seen_ids.add(item.item_id)
                    items.append(item)
                    if len(items) >= limit:
                        break
            if len(items) >= limit:
                break

        return items

    def _fetch_subreddit(
        self, subreddit: str, limit: int = 25
    ) -> List[SignalItem]:
        """Fetch hot posts from a single subreddit.

        Args:
            subreddit: Subreddit name (without r/ prefix).
            limit: Maximum number of posts to fetch.

        Returns:
            List of SignalItem objects from this subreddit.
        """
        url = f"{self.API_BASE}/r/{subreddit}/hot.json"
        params = {"limit": min(limit, 50), "raw_json": "1"}

        data = self._get_json(url, params=params)
        if data is None:
            return []

        # Reddit wraps responses in a data dict
        children = []
        if isinstance(data, dict):
            listing = data.get("data", {})
            children = listing.get("children", [])
        elif isinstance(data, list):
            children = data

        items: List[SignalItem] = []
        for child in children:
            if not isinstance(child, dict):
                continue
            kind = child.get("kind", "")
            if kind != "t3":  # t3 = link post
                continue

            post_data = child.get("data", {})
            item = self._parse_post(post_data, subreddit)
            if item:
                items.append(item)
                # Cache the item
                self.cache.set(
                    source=self.name,
                    item_id=item.item_id,
                    title=item.title,
                    url=item.url,
                    score=item.score,
                    metadata={
                        "comments": item.comments,
                        "author": item.author,
                        "subreddit": subreddit,
                        "created_at": (
                            item.created_at.isoformat()
                            if item.created_at else None
                        ),
                    },
                )

        return items

    def _parse_post(
        self, data: Dict[str, Any], subreddit: str
    ) -> Optional[SignalItem]:
        """Parse a Reddit post into a SignalItem.

        Skips stickied posts, self-posts without meaningful content,
        and posts with very low scores.

        Args:
            data: Raw post data from Reddit API.
            subreddit: Subreddit name for metadata.

        Returns:
            A SignalItem, or None if the post should be skipped.
        """
        # Skip stickied posts
        if data.get("stickied", False):
            return None

        title = data.get("title", "").strip()
        if not title:
            return None

        # Build URL: prefer external link, fall back to Reddit comments
        url = data.get("url", "")
        if not url or url.startswith(f"{self.API_BASE}/r/"):
            post_id = data.get("id", "")
            url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/"

        # Parse creation timestamp (Reddit uses Unix epoch seconds)
        created_at = None
        if data.get("created_utc"):
            created_at = timestamp_to_datetime(data["created_utc"])

        # Reddit scores can be negative
        score = max(0, int(data.get("score", 0)))

        return SignalItem(
            source=self.name,
            item_id=str(data.get("id", "")),
            title=title,
            url=url,
            score=float(score),
            comments=int(data.get("num_comments", 0)),
            author=data.get("author"),
            created_at=created_at,
            metadata={
                "subreddit": subreddit,
                "is_self": data.get("is_self", False),
                "flair": data.get("link_flair_text", ""),
                "upvote_ratio": data.get("upvote_ratio", 1.0),
            },
        )
