"""
Product Hunt data source for SignalPulse-CLI.

Fetches trending products from Product Hunt using their public
GraphQL API or falls back to RSS feed parsing.
"""

import json
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .base import BaseSource, SignalItem
from ..config import Config
from ..cache import CacheManager


class ProductHuntSource(BaseSource):
    """Data source adapter for Product Hunt.

    Attempts to fetch data from Product Hunt's frontend GraphQL API.
    Falls back to parsing the public RSS feed if GraphQL fails.

    GraphQL Endpoint: https://www.producthunt.com/frontend/graphql
    RSS Feed: https://www.producthunt.com/feed
    """

    GRAPHQL_URL = "https://www.producthunt.com/frontend/graphql"
    RSS_URL = "https://www.producthunt.com/feed"

    def __init__(self, config: Config, cache: CacheManager) -> None:
        """Initialize the Product Hunt source.

        Args:
            config: Application configuration.
            cache: Cache manager instance.
        """
        super().__init__(config, cache)
        self.name = "producthunt"

    def fetch(self, limit: int = 25) -> List[SignalItem]:
        """Fetch trending products from Product Hunt.

        Tries the GraphQL API first, falls back to RSS parsing.

        Args:
            limit: Maximum number of products to return.

        Returns:
            List of SignalItem objects for trending products.
        """
        source_config = self.config.get_source_config("producthunt")
        limit = source_config.get("limit", limit)

        # Check cache first
        cached_items = self.cache.get_bulk(self.name)
        if cached_items and len(cached_items) >= limit:
            return [
                SignalItem.from_dict({
                    "source": self.name,
                    "item_id": c["item_id"],
                    "title": c["title"],
                    "url": c["url"],
                    "score": c["score"],
                    "comments": c["metadata"].get("comments", 0),
                    "author": c["metadata"].get("author"),
                    "metadata": c["metadata"],
                })
                for c in cached_items[:limit]
            ]

        # Try GraphQL API first
        items = self._fetch_graphql(limit)
        if items:
            self._cache_items(items)
            return items[:limit]

        # Fall back to RSS
        items = self._fetch_rss(limit)
        if items:
            self._cache_items(items)
            return items[:limit]

        # Fall back to cached data
        if cached_items:
            return [
                SignalItem.from_dict({
                    "source": self.name,
                    "item_id": c["item_id"],
                    "title": c["title"],
                    "url": c["url"],
                    "score": c["score"],
                    "comments": c["metadata"].get("comments", 0),
                    "author": c["metadata"].get("author"),
                    "metadata": c["metadata"],
                })
                for c in cached_items
            ]

        return []

    def _fetch_graphql(self, limit: int) -> List[SignalItem]:
        """Fetch products using Product Hunt's GraphQL API.

        Sends a GraphQL query to fetch today's featured products
        with their upvote counts and details.

        Args:
            limit: Maximum number of products to fetch.

        Returns:
            List of SignalItem objects.
        """
        query = """
        query {
          posts(order: VOTES, first: %d) {
            edges {
              node {
                id
                name
                tagline
                description
                url
                votesCount
                commentsCount
                website
                createdAt
                topics {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """ % limit

        payload = {
            "query": query,
            "variables": {},
        }

        try:
            response = self.session.post(
                self.GRAPHQL_URL,
                json=payload,
                timeout=self.DEFAULT_TIMEOUT,
                headers={
                    **self.session.headers,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"[warning] Product Hunt GraphQL request failed: {e}")
            return []

        items: List[SignalItem] = []
        edges = (
            data.get("data", {}).get("posts", {}).get("edges", [])
        )
        for edge in edges:
            node = edge.get("node", {})
            item = self._parse_graphql_node(node)
            if item:
                items.append(item)

        return items

    def _parse_graphql_node(self, node: Dict[str, Any]) -> Optional[SignalItem]:
        """Parse a GraphQL node into a SignalItem.

        Args:
            node: Product data from GraphQL response.

        Returns:
            A SignalItem, or None if parsing fails.
        """
        name = node.get("name", "").strip()
        if not name:
            return None

        # Build title from name and tagline
        tagline = node.get("tagline", "").strip()
        title = f"{name}: {tagline}" if tagline else name

        url = node.get("url") or node.get("website", "")
        if not url:
            url = f"https://www.producthunt.com/posts/{name.lower().replace(' ', '-')}"

        # Parse creation date
        created_at = None
        created_str = node.get("createdAt", "")
        if created_str:
            try:
                created_at = datetime.fromisoformat(
                    created_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # Extract topics
        topics = []
        topic_edges = node.get("topics", {}).get("edges", [])
        for te in topic_edges:
            topic_name = te.get("node", {}).get("name", "")
            if topic_name:
                topics.append(topic_name)

        return SignalItem(
            source=self.name,
            item_id=str(node.get("id", name)),
            title=title,
            url=url,
            score=float(node.get("votesCount", 0)),
            comments=int(node.get("commentsCount", 0)),
            metadata={
                "name": name,
                "tagline": tagline,
                "description": node.get("description", ""),
                "topics": topics,
                "website": node.get("website", ""),
            },
        )

    def _fetch_rss(self, limit: int) -> List[SignalItem]:
        """Fetch products from Product Hunt's RSS feed.

        Parses the RSS XML feed using regex (no lxml dependency)
        to extract product entries.

        Args:
            limit: Maximum number of products to fetch.

        Returns:
            List of SignalItem objects.
        """
        response = self._http_get(
            self.RSS_URL,
            timeout=self.DEFAULT_TIMEOUT,
        )
        if response is None:
            return []

        html = response.text
        items = self._parse_rss(html)
        return items[:limit]

    def _parse_rss(self, xml_text: str) -> List[SignalItem]:
        """Parse Product Hunt RSS feed using regex.

        Extracts item entries from the RSS XML, handling both
        standard RSS and Atom feed formats.

        Args:
            xml_text: Raw RSS/Atom feed XML content.

        Returns:
            List of SignalItem objects.
        """
        items: List[SignalItem] = []

        # Extract individual <item> or <entry> blocks
        entry_pattern = re.compile(
            r'<(?:item|entry)\b[^>]*>(.*?)</(?:item|entry)>',
            re.DOTALL | re.IGNORECASE,
        )
        entries = entry_pattern.findall(xml_text)

        for entry in entries:
            item = self._parse_rss_entry(entry)
            if item:
                items.append(item)

        return items

    def _parse_rss_entry(self, entry_xml: str) -> Optional[SignalItem]:
        """Parse a single RSS/Atom entry into a SignalItem.

        Args:
            entry_xml: XML fragment for a single feed entry.

        Returns:
            A SignalItem, or None if parsing fails.
        """
        # Extract title
        title = self._extract_xml_tag(entry_xml, "title")
        if not title:
            return None

        # Extract link
        link = self._extract_xml_tag(entry_xml, "link")
        if not link:
            # Try href attribute
            link_match = re.search(r'<link[^>]+href="([^"]+)"', entry_xml)
            link = link_match.group(1) if link_match else ""

        # Extract description/content
        description = self._extract_xml_tag(entry_xml, "description")
        if not description:
            description = self._extract_xml_tag(
                entry_xml, "content", "encoded"
            )
        if not description:
            description = self._extract_xml_tag(entry_xml, "summary")

        # Clean HTML from description
        if description:
            description = re.sub(r'<[^>]+>', '', description).strip()

        # Generate a unique ID from the link
        item_id = re.sub(r'[^a-zA-Z0-9]', '_', link or title)[:50]

        # Try to extract upvotes from description (Product Hunt includes this)
        upvotes = 0
        if description:
            upvote_match = re.search(
                r'(\d+)\s*(?:upvotes|votes|points)',
                description,
                re.IGNORECASE,
            )
            if upvote_match:
                upvotes = int(upvote_match.group(1))

        return SignalItem(
            source=self.name,
            item_id=item_id,
            title=title,
            url=link,
            score=float(upvotes),
            metadata={
                "description": description[:200] if description else "",
            },
        )

    @staticmethod
    def _extract_xml_tag(
        xml: str, tag_name: str, sub_tag: str = ""
    ) -> str:
        """Extract text content from an XML tag using regex.

        Args:
            xml: XML string to search.
            tag_name: Name of the tag to extract.
            sub_tag: Optional sub-tag name (for namespaced tags
                     like content:encoded).

        Returns:
            Extracted text content, or empty string if not found.
        """
        if sub_tag:
            pattern = re.compile(
                rf'<{tag_name}:[^>]*>(.*?)</{tag_name}:{sub_tag}>',
                re.DOTALL,
            )
        else:
            # Handle CDATA sections
            pattern = re.compile(
                rf'<{tag_name}[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{tag_name}>',
                re.DOTALL,
            )
        match = pattern.search(xml)
        if match:
            return match.group(1).strip()
        return ""

    def _cache_items(self, items: List[SignalItem]) -> None:
        """Cache a list of fetched items.

        Args:
            items: List of SignalItem objects to cache.
        """
        cache_data = []
        for item in items:
            cache_data.append({
                "item_id": item.item_id,
                "title": item.title,
                "url": item.url,
                "score": item.score,
                "metadata": {
                    **item.metadata,
                    "comments": item.comments,
                    "author": item.author,
                },
            })
        if cache_data:
            self.cache.set_bulk(self.name, cache_data)
