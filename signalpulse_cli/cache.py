"""
SQLite-based cache manager for SignalPulse-CLI.

Provides local caching of fetched items to avoid repeated API calls
and improve response times on subsequent runs.
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import Config
from .utils import utc_now, timestamp_to_datetime, datetime_to_timestamp


class CacheManager:
    """Thread-safe SQLite cache for social signal data.

    Stores fetched items with expiration timestamps to avoid redundant
    API calls. Supports get, set, and cleanup operations.

    Attributes:
        db_path: Path to the SQLite database file.
        default_ttl_minutes: Default time-to-live for cached items.
    """

    _local = threading.local()

    def __init__(self, config: Config) -> None:
        """Initialize the cache manager and create the database schema.

        Args:
            config: Application configuration object.
        """
        self.db_path: Path = config.get_cache_path()
        self.default_ttl_minutes: int = config.get("cache.ttl_minutes", 60)
        self._enabled: bool = config.get("cache.enabled", True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection.

        Uses thread-local storage to ensure each thread gets its own
        connection, avoiding SQLite threading issues.

        Returns:
            A sqlite3.Connection object.
        """
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=10.0,
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrent read performance
            self._local.connection.execute("PRAGMA journal_mode=WAL")
        return self._local.connection

    def _init_db(self) -> None:
        """Create the cache database schema if it doesn't exist.

        Creates the 'items' table with columns for source identification,
        item metadata, scores, and expiration tracking.
        """
        if not self._enabled:
            return
        conn = self._get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                item_id TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT,
                score REAL DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                cached_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                UNIQUE(source, item_id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_source
            ON items(source)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_expires
            ON items(expires_at)
            """
        )
        conn.commit()

    @property
    def enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._enabled

    def get(
        self, source: str, item_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a cached item if it exists and hasn't expired.

        Args:
            source: The data source name (e.g., "hackernews").
            item_id: Unique identifier for the item within the source.

        Returns:
            Cached item data dict, or None if not found or expired.
        """
        if not self._enabled:
            return None

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT source, item_id, title, url, score, metadata,
                       cached_at, expires_at
                FROM items
                WHERE source = ? AND item_id = ? AND expires_at > ?
                """,
                (source, item_id, datetime_to_timestamp(utc_now())),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            metadata = {}
            if row["metadata"]:
                try:
                    metadata = json.loads(row["metadata"])
                except (json.JSONDecodeError, TypeError):
                    metadata = {}

            return {
                "source": row["source"],
                "item_id": row["item_id"],
                "title": row["title"],
                "url": row["url"],
                "score": row["score"],
                "metadata": metadata,
                "cached_at": timestamp_to_datetime(row["cached_at"]),
                "expires_at": timestamp_to_datetime(row["expires_at"]),
            }
        except sqlite3.Error:
            return None

    def get_bulk(self, source: str) -> List[Dict[str, Any]]:
        """Retrieve all non-expired cached items for a given source.

        Args:
            source: The data source name.

        Returns:
            List of cached item data dicts.
        """
        if not self._enabled:
            return []

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT source, item_id, title, url, score, metadata,
                       cached_at, expires_at
                FROM items
                WHERE source = ? AND expires_at > ?
                ORDER BY score DESC
                """,
                (source, datetime_to_timestamp(utc_now())),
            )
            results = []
            for row in cursor.fetchall():
                metadata = {}
                if row["metadata"]:
                    try:
                        metadata = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}

                results.append({
                    "source": row["source"],
                    "item_id": row["item_id"],
                    "title": row["title"],
                    "url": row["url"],
                    "score": row["score"],
                    "metadata": metadata,
                    "cached_at": timestamp_to_datetime(row["cached_at"]),
                    "expires_at": timestamp_to_datetime(row["expires_at"]),
                })
            return results
        except sqlite3.Error:
            return []

    def set(
        self,
        source: str,
        item_id: str,
        title: str,
        url: Optional[str] = None,
        score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_minutes: Optional[int] = None,
    ) -> bool:
        """Store an item in the cache.

        Uses INSERT OR REPLACE to handle updates to existing items.

        Args:
            source: The data source name.
            item_id: Unique identifier for the item.
            title: Item title.
            url: Item URL (optional).
            score: Item score/rating.
            metadata: Additional metadata as dict (optional).
            ttl_minutes: Time-to-live in minutes. Uses default if None.

        Returns:
            True if the item was stored successfully, False otherwise.
        """
        if not self._enabled:
            return False

        ttl = ttl_minutes if ttl_minutes is not None else self.default_ttl_minutes
        now = utc_now()
        expires = now + timedelta(minutes=ttl)

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO items
                    (source, item_id, title, url, score, metadata,
                     cached_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source,
                    item_id,
                    title,
                    url,
                    score,
                    json.dumps(metadata or {}),
                    datetime_to_timestamp(now),
                    datetime_to_timestamp(expires),
                ),
            )
            conn.commit()
            return True
        except sqlite3.Error:
            return False

    def set_bulk(
        self,
        source: str,
        items: List[Dict[str, Any]],
        ttl_minutes: Optional[int] = None,
    ) -> int:
        """Store multiple items in the cache in a single transaction.

        Args:
            source: The data source name.
            items: List of item dicts with at least 'item_id' and 'title'.
            ttl_minutes: Time-to-live in minutes. Uses default if None.

        Returns:
            Number of items successfully stored.
        """
        if not self._enabled or not items:
            return 0

        ttl = ttl_minutes if ttl_minutes is not None else self.default_ttl_minutes
        now = utc_now()
        expires = now + timedelta(minutes=ttl)
        now_ts = datetime_to_timestamp(now)
        expires_ts = datetime_to_timestamp(expires)

        conn = self._get_connection()
        stored = 0
        try:
            for item in items:
                item_id = str(item.get("item_id", item.get("id", "")))
                if not item_id:
                    continue
                conn.execute(
                    """
                    INSERT OR REPLACE INTO items
                        (source, item_id, title, url, score, metadata,
                         cached_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source,
                        item_id,
                        item.get("title", ""),
                        item.get("url"),
                        item.get("score", 0.0),
                        json.dumps({k: v for k, v in item.items()
                                    if k not in ("item_id", "id", "title", "url", "score")}),
                        now_ts,
                        expires_ts,
                    ),
                )
                stored += 1
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
        return stored

    def cleanup(self, max_age_days: int = 7) -> int:
        """Remove expired and old cached items to free disk space.

        Args:
            max_age_days: Remove items older than this many days,
                          regardless of expiration.

        Returns:
            Number of items removed.
        """
        if not self._enabled:
            return 0

        conn = self._get_connection()
        try:
            now = utc_now()
            cutoff = now - timedelta(days=max_age_days)
            cursor = conn.execute(
                """
                DELETE FROM items
                WHERE expires_at <= ? OR cached_at <= ?
                """,
                (
                    datetime_to_timestamp(now),
                    datetime_to_timestamp(cutoff),
                ),
            )
            conn.commit()
            return cursor.rowcount
        except sqlite3.Error:
            return 0

    def clear(self, source: Optional[str] = None) -> int:
        """Clear all cached items, optionally for a specific source.

        Args:
            source: If provided, only clear items from this source.

        Returns:
            Number of items removed.
        """
        if not self._enabled:
            return 0

        conn = self._get_connection()
        try:
            if source:
                cursor = conn.execute(
                    "DELETE FROM items WHERE source = ?", (source,)
                )
            else:
                cursor = conn.execute("DELETE FROM items")
            conn.commit()
            return cursor.rowcount
        except sqlite3.Error:
            return 0

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats (total items, per-source counts, etc.).
        """
        if not self._enabled:
            return {"enabled": False, "total": 0}

        conn = self._get_connection()
        try:
            now_ts = datetime_to_timestamp(utc_now())

            # Total items (including expired)
            total_cursor = conn.execute("SELECT COUNT(*) FROM items")
            total = total_cursor.fetchone()[0]

            # Active (non-expired) items
            active_cursor = conn.execute(
                "SELECT COUNT(*) FROM items WHERE expires_at > ?", (now_ts,)
            )
            active = active_cursor.fetchone()[0]

            # Per-source counts
            source_cursor = conn.execute(
                """
                SELECT source, COUNT(*) as count
                FROM items
                WHERE expires_at > ?
                GROUP BY source
                """,
                (now_ts,),
            )
            sources = {row[0]: row[1] for row in source_cursor.fetchall()}

            return {
                "enabled": True,
                "total": total,
                "active": active,
                "expired": total - active,
                "sources": sources,
            }
        except sqlite3.Error:
            return {"enabled": True, "total": 0, "active": 0, "expired": 0, "sources": {}}

    def close(self) -> None:
        """Close the database connection for the current thread."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None
