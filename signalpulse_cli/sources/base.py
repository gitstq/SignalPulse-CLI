"""
Base source class for SignalPulse-CLI data sources.

Defines the interface and common functionality that all data source
adapters must implement.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from ..config import Config
from ..cache import CacheManager
from ..utils import utc_now, timestamp_to_datetime, sanitize_text, truncate_text


@dataclass
class SignalItem:
    """Represents a single social signal item from any source.

    Attributes:
        source: Name of the data source (e.g., "hackernews").
        item_id: Unique identifier within the source.
        title: Item title/headline.
        url: Direct URL to the item or external resource.
        score: Raw engagement score (upvotes, points, etc.).
        comments: Number of comments/replies.
        author: Username of the item author.
        created_at: When the item was created (UTC datetime).
        fetched_at: When the item was fetched (UTC datetime).
        metadata: Additional source-specific data.
        normalized_score: Score after cross-platform normalization.
    """

    source: str
    item_id: str
    title: str
    url: Optional[str] = None
    score: float = 0.0
    comments: int = 0
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    normalized_score: float = 0.0

    def __post_init__(self) -> None:
        """Clean up fields after initialization."""
        self.title = sanitize_text(self.title)
        self.title = truncate_text(self.title, 300)
        if self.fetched_at is None:
            self.fetched_at = utc_now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the signal item to a plain dictionary.

        Returns:
            Dictionary representation of the item.
        """
        return {
            "source": self.source,
            "item_id": self.item_id,
            "title": self.title,
            "url": self.url,
            "score": self.score,
            "comments": self.comments,
            "author": self.author,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "fetched_at": (
                self.fetched_at.isoformat() if self.fetched_at else None
            ),
            "metadata": self.metadata,
            "normalized_score": self.normalized_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignalItem":
        """Create a SignalItem from a dictionary.

        Args:
            data: Dictionary with item fields.

        Returns:
            A new SignalItem instance.
        """
        created = data.get("created_at")
        if isinstance(created, str):
            from ..utils import utc_now
            try:
                from dateutil.parser import parse as parse_date
                created = parse_date(created)
            except ImportError:
                created = None
        elif isinstance(created, (int, float)):
            created = timestamp_to_datetime(created)

        fetched = data.get("fetched_at")
        if isinstance(fetched, str):
            try:
                from dateutil.parser import parse as parse_date
                fetched = parse_date(fetched)
            except ImportError:
                fetched = None
        elif isinstance(fetched, (int, float)):
            fetched = timestamp_to_datetime(fetched)

        return cls(
            source=data.get("source", "unknown"),
            item_id=str(data.get("item_id", "")),
            title=data.get("title", ""),
            url=data.get("url"),
            score=float(data.get("score", 0)),
            comments=int(data.get("comments", 0)),
            author=data.get("author"),
            created_at=created,
            fetched_at=fetched,
            metadata=data.get("metadata", {}),
            normalized_score=float(data.get("normalized_score", 0)),
        )


class BaseSource(ABC):
    """Abstract base class for all data source adapters.

    Provides common HTTP request functionality, error handling,
    and caching integration. Subclasses must implement the fetch()
    method to retrieve items from their specific platform.

    Attributes:
        name: Human-readable source name.
        config: Application configuration.
        cache: Cache manager instance.
        session: requests.Session for HTTP connections.
    """

    # User-Agent string for HTTP requests
    USER_AGENT: str = (
        "SignalPulse-CLI/1.0 (https://github.com/signalpulse/cli; "
        "social-signal-aggregator)"
    )

    # Default request timeout in seconds
    DEFAULT_TIMEOUT: int = 15

    def __init__(self, config: Config, cache: CacheManager) -> None:
        """Initialize the data source.

        Args:
            config: Application configuration object.
            cache: Cache manager instance.
        """
        self.name: str = self.__class__.__name__.replace("Source", "").lower()
        self.config = config
        self.cache = cache
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
        })

    @abstractmethod
    def fetch(self, limit: int = 25) -> List[SignalItem]:
        """Fetch trending items from this data source.

        Must be implemented by subclasses to retrieve and parse
        items from their specific platform API or web page.

        Args:
            limit: Maximum number of items to return.

        Returns:
            List of SignalItem objects sorted by relevance/score.
        """
        ...

    def _http_get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Optional[requests.Response]:
        """Perform an HTTP GET request with error handling.

        Args:
            url: The URL to fetch.
            params: Optional query parameters.
            timeout: Request timeout in seconds.

        Returns:
            Response object, or None if the request failed.
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        try:
            response = self.session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            print(f"[warning] Request to {url} timed out after {timeout}s")
            return None
        except requests.exceptions.ConnectionError:
            print(f"[warning] Could not connect to {url}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"[warning] HTTP error from {url}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[warning] Request to {url} failed: {e}")
            return None

    def _get_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Optional[Any]:
        """Perform an HTTP GET request and parse JSON response.

        Args:
            url: The URL to fetch.
            params: Optional query parameters.
            timeout: Request timeout in seconds.

        Returns:
            Parsed JSON data, or None if the request/parsing failed.
        """
        response = self._http_get(url, params=params, timeout=timeout)
        if response is None:
            return None
        try:
            return response.json()
        except (ValueError, KeyError) as e:
            print(f"[warning] Failed to parse JSON from {url}: {e}")
            return None

    def close(self) -> None:
        """Clean up resources used by this source."""
        self.session.close()
