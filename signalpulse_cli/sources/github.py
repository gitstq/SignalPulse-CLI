"""
GitHub Trending data source for SignalPulse-CLI.

Scrapes the GitHub Trending page (https://github.com/trending)
using regex parsing (no BeautifulSoup dependency) to extract
trending repositories with their metadata.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseSource, SignalItem
from ..config import Config
from ..cache import CacheManager


class GitHubSource(BaseSource):
    """Data source adapter for GitHub Trending.

    Scrapes the GitHub Trending page using regex to extract
    repository names, descriptions, star counts, and programming
    languages. No external HTML parsing library required.

    URL: https://github.com/trending
    """

    TRENDING_URL = "https://github.com/trending"

    def __init__(self, config: Config, cache: CacheManager) -> None:
        """Initialize the GitHub Trending source.

        Args:
            config: Application configuration.
            cache: Cache manager instance.
        """
        super().__init__(config, cache)
        self.name = "github"
        # GitHub trending is HTML, not JSON
        self.session.headers.update({
            "Accept": "text/html, application/xhtml+xml, */*",
        })

    def fetch(self, limit: int = 25) -> List[SignalItem]:
        """Fetch trending repositories from GitHub.

        Scrapes the GitHub Trending page and parses repository
        information using regex patterns.

        Args:
            limit: Maximum number of repositories to return.

        Returns:
            List of SignalItem objects for trending GitHub repos.
        """
        source_config = self.config.get_source_config("github")
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
                    "comments": c["metadata"].get("forks", 0),
                    "metadata": c["metadata"],
                })
                for c in cached_items[:limit]
            ]

        # Fetch the trending page HTML
        response = self._http_get(self.TRENDING_URL, timeout=20)
        if response is None:
            # Fall back to cached data if available
            if cached_items:
                return [
                    SignalItem.from_dict({
                        "source": self.name,
                        "item_id": c["item_id"],
                        "title": c["title"],
                        "url": c["url"],
                        "score": c["score"],
                        "comments": c["metadata"].get("forks", 0),
                        "metadata": c["metadata"],
                    })
                    for c in cached_items
                ]
            return []

        html = response.text
        items = self._parse_trending_page(html)

        # Cache all items
        cache_data = []
        for item in items[:limit]:
            cache_data.append({
                "item_id": item.item_id,
                "title": item.title,
                "url": item.url,
                "score": item.score,
                "metadata": item.metadata,
            })
        if cache_data:
            self.cache.set_bulk(self.name, cache_data)

        return items[:limit]

    def _parse_trending_page(self, html: str) -> List[SignalItem]:
        """Parse the GitHub Trending page HTML using regex.

        Extracts repository entries from the HTML by identifying
        the repeating article elements that contain repo info.

        Args:
            html: Raw HTML content of the trending page.

        Returns:
            List of SignalItem objects for parsed repositories.
        """
        items: List[SignalItem] = []

        # Split HTML into article blocks (each repo is in an <article> tag)
        # GitHub uses <article class="Box-row"> for each trending repo
        article_pattern = re.compile(
            r'<article[^>]*class="Box-row"[^>]*>(.*?)</article>',
            re.DOTALL,
        )
        articles = article_pattern.findall(html)

        if not articles:
            # Fallback: try a looser pattern
            article_pattern = re.compile(
                r'<article[^>]*>(.*?)</article>',
                re.DOTALL,
            )
            articles = article_pattern.findall(html)

        for article_html in articles:
            item = self._parse_repo_article(article_html)
            if item:
                items.append(item)

        return items

    def _parse_repo_article(self, html: str) -> Optional[SignalItem]:
        """Parse a single repository article element.

        Extracts repo name, description, stars, forks, and language
        from the HTML fragment using regex.

        Args:
            html: HTML fragment for a single repository entry.

        Returns:
            A SignalItem for the repository, or None if parsing fails.
        """
        # Extract repo name (owner/repo format)
        # Pattern: href="/owner/repo"
        repo_match = re.search(
            r'<h2[^>]*>.*?href="/([^"]+)"[^>]*>(.*?)</a>\s*</h2>',
            html,
            re.DOTALL,
        )
        if not repo_match:
            # Try alternative pattern
            repo_match = re.search(
                r'href="/([^/]+/[^"]+)"',
                html,
            )
            if not repo_match:
                return None

        repo_full_name = repo_match.group(1).strip()
        # Clean up any whitespace or newlines in repo name
        repo_full_name = re.sub(r'\s+', '', repo_full_name)

        # Validate it looks like a repo path (owner/repo)
        if "/" not in repo_full_name or repo_full_name.count("/") != 1:
            return None

        # Extract description
        description = ""
        desc_match = re.search(
            r'<p[^>]*class="[^"]*color-fg-muted[^"]*"[^>]*>(.*?)</p>',
            html,
            re.DOTALL,
        )
        if desc_match:
            description = self._strip_html_tags(desc_match.group(1)).strip()

        # Extract star count
        # Pattern: href="/owner/repo/stargazers" followed by a number
        stars = 0
        stars_match = re.search(
            r'href="/[^"]+/stargazers"[^>]*>\s*<[^>]*>\s*([\d,]+)\s*</',
            html,
            re.DOTALL,
        )
        if stars_match:
            stars = self._parse_number(stars_match.group(1))

        # Fallback star pattern
        if stars == 0:
            stars_match = re.search(
                r'(?:stargazers|star)[^>]*>\s*<[^>]*>\s*([\d,]+)',
                html,
                re.DOTALL,
            )
            if stars_match:
                stars = self._parse_number(stars_match.group(1))

        # Extract fork count
        forks = 0
        forks_match = re.search(
            r'href="/[^"]+/forks"[^>]*>\s*<[^>]*>\s*([\d,]+)\s*</',
            html,
            re.DOTALL,
        )
        if forks_match:
            forks = self._parse_number(forks_match.group(1))

        # Fallback fork pattern
        if forks == 0:
            forks_match = re.search(
                r'(?:forks)[^>]*>\s*<[^>]*>\s*([\d,]+)',
                html,
                re.DOTALL,
            )
            if forks_match:
                forks = self._parse_number(forks_match.group(1))

        # Extract programming language
        language = ""
        lang_match = re.search(
            r'(?:itemprop="programmingLanguage"|class="[^"]*language[^"]*")'
            r'[^>]*>\s*(\w[\w\s+#.]*)\s*</',
            html,
        )
        if lang_match:
            language = lang_match.group(1).strip()

        # Build title: use description if available, else repo name
        title = description if description else f"{repo_full_name}"
        url = f"https://github.com/{repo_full_name}"

        return SignalItem(
            source=self.name,
            item_id=repo_full_name,
            title=title,
            url=url,
            score=float(stars),
            comments=forks,
            author=repo_full_name.split("/")[0],
            metadata={
                "repo": repo_full_name,
                "language": language,
                "stars": stars,
                "forks": forks,
                "description": description,
            },
        )

    @staticmethod
    def _strip_html_tags(text: str) -> str:
        """Remove HTML tags from a string.

        Args:
            text: String potentially containing HTML tags.

        Returns:
            Plain text with tags removed.
        """
        return re.sub(r'<[^>]+>', '', text)

    @staticmethod
    def _parse_number(text: str) -> int:
        """Parse a number string that may contain commas or K/M suffixes.

        Args:
            text: Number string (e.g., "1,234", "5.2k", "1.2M").

        Returns:
            Parsed integer value.
        """
        text = text.strip().replace(",", "").lower()
        try:
            if text.endswith("k"):
                return int(float(text[:-1]) * 1000)
            if text.endswith("m"):
                return int(float(text[:-1]) * 1_000_000)
            return int(float(text))
        except (ValueError, IndexError):
            return 0
