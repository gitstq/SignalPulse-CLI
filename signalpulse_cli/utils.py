"""
Utility functions for SignalPulse-CLI.

Provides common helpers used across the application including
timestamp handling, URL validation, and text sanitization.
"""

import re
import unicodedata
from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


def timestamp_to_datetime(ts: Optional[float]) -> Optional[datetime]:
    """Convert a Unix timestamp (seconds) to a UTC datetime object.

    Args:
        ts: Unix timestamp in seconds since epoch.

    Returns:
        A timezone-aware datetime in UTC, or None if ts is None/invalid.
    """
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def datetime_to_timestamp(dt: Optional[datetime]) -> Optional[float]:
    """Convert a datetime object to a Unix timestamp.

    Args:
        dt: A datetime object.

    Returns:
        Unix timestamp as float, or None if dt is None.
    """
    if dt is None:
        return None
    try:
        return dt.timestamp()
    except (OSError, OverflowError, ValueError):
        return None


def format_relative_time(dt: Optional[datetime]) -> str:
    """Format a datetime as a human-readable relative time string.

    Examples: "3 hours ago", "in 5 minutes", "just now"

    Args:
        dt: The datetime to format.

    Returns:
        A human-readable relative time string.
    """
    if dt is None:
        return "unknown"
    now = utc_now()
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 0:
        return "in the future"
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m ago"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours}h ago"
    days = seconds // 86400
    return f"{days}d ago"


def sanitize_text(text: str) -> str:
    """Remove or replace problematic characters from text.

    Strips control characters while preserving newlines and tabs.
    Normalizes unicode to NFC form.

    Args:
        text: The input text to sanitize.

    Returns:
        Cleaned text string.
    """
    # Normalize unicode
    text = unicodedata.normalize("NFC", text)
    # Remove control characters except newline and tab
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def truncate_text(text: str, max_length: int = 120, suffix: str = "...") -> str:
    """Truncate text to a maximum length, adding a suffix if truncated.

    Args:
        text: The input text.
        max_length: Maximum character length.
        suffix: Suffix to append when text is truncated.

    Returns:
        Truncated text string.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid HTTP/HTTPS URL.

    Args:
        url: The URL string to validate.

    Returns:
        True if the URL appears valid, False otherwise.
    """
    pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:\S+(?::\S*)?@)?"  # optional user:pass
        r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"  # domain
        r"[a-zA-Z]{2,}"  # TLD
        r"(?::\d{2,5})?"  # optional port
        r"(?:/[^\s]*)?$",  # optional path
        re.IGNORECASE,
    )
    return bool(pattern.match(url))


def extract_domain(url: str) -> str:
    """Extract the domain name from a URL.

    Args:
        url: A URL string.

    Returns:
        The domain portion of the URL, or the original string if parsing fails.
    """
    match = re.match(r"https?://([^/]+)", url)
    if match:
        return match.group(1)
    return url


def normalize_score(value: float, min_val: float, max_val: float) -> float:
    """Normalize a value using min-max normalization to [0, 1].

    Args:
        value: The value to normalize.
        min_val: The minimum possible value.
        max_val: The maximum possible value.

    Returns:
        Normalized value between 0.0 and 1.0.
    """
    if max_val == min_val:
        return 0.5
    normalized = (value - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, normalized))


def format_number(num: int) -> str:
    """Format a number with human-readable suffixes.

    Examples: 1500 -> "1.5K", 2500000 -> "2.5M"

    Args:
        num: The number to format.

    Returns:
        Formatted number string.
    """
    if num < 1000:
        return str(num)
    if num < 1_000_000:
        return f"{num / 1000:.1f}K"
    if num < 1_000_000_000:
        return f"{num / 1_000_000:.1f}M"
    return f"{num / 1_000_000_000:.1f}B"
