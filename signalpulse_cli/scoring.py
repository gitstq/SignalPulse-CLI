"""
Engagement scoring engine for SignalPulse-CLI.

Normalizes and scores items across different platforms using
configurable weights, producing a unified ranking that reflects
real user engagement rather than SEO metrics.
"""

import math
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .config import Config
from .sources.base import SignalItem
from .utils import utc_now, normalize_score


class ScoringEngine:
    """Cross-platform engagement scoring engine.

    Normalizes raw scores from different platforms using min-max
    normalization, applies configurable weights for score, comments,
    and recency, and combines them into a unified engagement score.

    The scoring formula:
        normalized_score = w_score * norm(score)
                        + w_comments * norm(comments)
                        + w_recency * recency_decay(hours_since_post)

    Attributes:
        config: Application configuration.
        weights: Scoring weight configuration.
        recency_half_life: Half-life for recency decay in hours.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the scoring engine with configuration.

        Args:
            config: Application configuration object.
        """
        self.config = config
        scoring_config = config.get("scoring", {})
        self.weights: Dict[str, float] = scoring_config.get(
            "weights", {"score": 0.5, "comments": 0.3, "recency": 0.2}
        )
        self.recency_half_life: float = scoring_config.get(
            "recency_half_life_hours", 12.0
        )

        # Source-specific weight multipliers
        self.source_weights: Dict[str, float] = {}
        for source_name in config.get_enabled_sources():
            source_config = config.get_source_config(source_name)
            self.source_weights[source_name] = source_config.get("weight", 1.0)

    def score_items(self, items: List[SignalItem]) -> List[SignalItem]:
        """Score and rank a list of signal items.

        First normalizes raw scores across all items, then computes
        a unified engagement score for each item, and finally sorts
        by score descending.

        Args:
            items: List of SignalItem objects to score.

        Returns:
            New list of SignalItem objects sorted by normalized_score
            in descending order.
        """
        if not items:
            return []

        # Work on copies to avoid mutating originals
        scored = [self._deep_copy_item(item) for item in items]

        # Compute normalization ranges per source
        source_ranges = self._compute_source_ranges(scored)

        # Score each item
        for item in scored:
            item.normalized_score = self._compute_item_score(
                item, source_ranges
            )

        # Sort by normalized score descending
        scored.sort(key=lambda x: x.normalized_score, reverse=True)

        return scored

    def _compute_source_ranges(
        self, items: List[SignalItem]
    ) -> Dict[str, Dict[str, Tuple[float, float]]]:
        """Compute min/max ranges for score and comments per source.

        Used for min-max normalization within each source's scale,
        since different platforms have vastly different score ranges.

        Args:
            items: List of SignalItem objects.

        Returns:
            Nested dict mapping source -> metric -> (min, max) tuples.
        """
        source_stats: Dict[str, Dict[str, List[float]]] = {}

        for item in items:
            source = item.source
            if source not in source_stats:
                source_stats[source] = {"score": [], "comments": []}
            source_stats[source]["score"].append(item.score)
            source_stats[source]["comments"].append(float(item.comments))

        ranges: Dict[str, Dict[str, Tuple[float, float]]] = {}
        for source, stats in source_stats.items():
            ranges[source] = {}
            for metric, values in stats.items():
                if values:
                    ranges[source][metric] = (min(values), max(values))
                else:
                    ranges[source][metric] = (0.0, 1.0)

        return ranges

    def _compute_item_score(
        self,
        item: SignalItem,
        source_ranges: Dict[str, Dict[str, Tuple[float, float]]],
    ) -> float:
        """Compute the unified normalized score for a single item.

        Combines normalized score, comments, and recency using
        configured weights. Applies source-specific weight multiplier.

        Args:
            item: The SignalItem to score.
            source_ranges: Pre-computed normalization ranges.

        Returns:
            Unified normalized score between 0.0 and 1.0.
        """
        source = item.source
        ranges = source_ranges.get(source, {})

        # Normalize score (0-1)
        score_range = ranges.get("score", (0.0, 1.0))
        norm_score = normalize_score(item.score, score_range[0], score_range[1])

        # Normalize comments (0-1)
        comments_range = ranges.get("comments", (0.0, 1.0))
        norm_comments = normalize_score(
            float(item.comments), comments_range[0], comments_range[1]
        )

        # Compute recency score using exponential decay
        recency_score = self._compute_recency_score(item.created_at)

        # Combine with weights
        w_score = self.weights.get("score", 0.5)
        w_comments = self.weights.get("comments", 0.3)
        w_recency = self.weights.get("recency", 0.2)

        # Normalize weights to sum to 1.0
        total_weight = w_score + w_comments + w_recency
        if total_weight > 0:
            w_score /= total_weight
            w_comments /= total_weight
            w_recency /= total_weight

        unified = (
            w_score * norm_score
            + w_comments * norm_comments
            + w_recency * recency_score
        )

        # Apply source weight multiplier
        source_weight = self.source_weights.get(source, 1.0)
        unified *= source_weight

        return round(max(0.0, min(1.0, unified)), 6)

    def _compute_recency_score(
        self, created_at: Optional[datetime]
    ) -> float:
        """Compute a recency score using exponential time decay.

        Newer items get higher recency scores. Uses a half-life
        model: after recency_half_life hours, the score drops to 0.5.

        Args:
            created_at: When the item was created (UTC).

        Returns:
            Recency score between 0.0 (very old) and 1.0 (brand new).
        """
        if created_at is None:
            return 0.5  # Default for unknown times

        now = utc_now()
        age_hours = (now - created_at).total_seconds() / 3600.0

        if age_hours < 0:
            return 1.0  # Future-dated items get max score

        # Exponential decay: score = 2^(-age / half_life)
        decay = math.pow(2.0, -age_hours / self.recency_half_life)
        return max(0.0, min(1.0, decay))

    @staticmethod
    def _deep_copy_item(item: SignalItem) -> SignalItem:
        """Create a copy of a SignalItem.

        Args:
            item: The item to copy.

        Returns:
            A new SignalItem with the same data.
        """
        return SignalItem(
            source=item.source,
            item_id=item.item_id,
            title=item.title,
            url=item.url,
            score=item.score,
            comments=item.comments,
            author=item.author,
            created_at=item.created_at,
            fetched_at=item.fetched_at,
            metadata=dict(item.metadata),
            normalized_score=item.normalized_score,
        )
