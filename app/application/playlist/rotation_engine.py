"""Rotation tier engine — classifies songs into A/B/C/New Entry/Retired tiers.

Pure functions; no database calls. The caller is responsible for loading
the required spin counts and current tier state.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass

from app.domain.entities.playlist_recommendation import (
    PlaylistRecommendation,
    RecommendationType,
    RotationTier,
    classify_tier,
)


@dataclass(frozen=True)
class SongSpinCount:
    artist: str
    title: str
    weekly_spins: int
    current_tier: RotationTier | None = None


def build_recommendations(
    station_id: uuid.UUID,
    spin_counts: list[SongSpinCount],
) -> list[PlaylistRecommendation]:
    """Build playlist recommendations from spin count data.

    For each song:
    - Classify the recommended tier from weekly_spins
    - Compare to current_tier to determine recommendation type
    - Generate a human-readable reason
    """
    recommendations: list[PlaylistRecommendation] = []

    for song in spin_counts:
        recommended = classify_tier(song.weekly_spins)
        current = song.current_tier

        if current is None:
            if recommended == RotationTier.RETIRED:
                continue
            rec_type = RecommendationType.ADD
            reason = (
                f"{song.weekly_spins} spins/week — not yet in playlist; "
                f"recommended for {recommended.value}-rotation."
            )
        elif recommended == current:
            rec_type = RecommendationType.MAINTAIN
            reason = f"{song.weekly_spins} spins/week — maintaining {current.value}-rotation."
        elif _tier_rank(recommended) > _tier_rank(current):
            rec_type = RecommendationType.INCREASE
            reason = (
                f"{song.weekly_spins} spins/week — up from {current.value} "
                f"to {recommended.value}."
            )
        elif recommended == RotationTier.RETIRED:
            rec_type = RecommendationType.RETIRE
            reason = f"0 spins/week — retire from {current.value}-rotation."
        else:
            rec_type = RecommendationType.DECREASE
            reason = (
                f"{song.weekly_spins} spins/week — down from {current.value} "
                f"to {recommended.value}."
            )

        recommendations.append(
            PlaylistRecommendation.create(
                station_id=station_id,
                artist=song.artist,
                title=song.title,
                current_tier=current,
                recommended_tier=recommended,
                recommendation_type=rec_type,
                weekly_spins=song.weekly_spins,
                reason=reason,
            )
        )

    return sorted(recommendations, key=lambda r: r.weekly_spins, reverse=True)


def spin_counts_from_plays(
    plays: list[tuple[str, str]],
    current_tiers: dict[tuple[str, str], RotationTier] | None = None,
) -> list[SongSpinCount]:
    """Build SongSpinCount list from (artist, title) tuples."""
    current_tiers = current_tiers or {}
    counter: Counter[tuple[str, str]] = Counter(plays)
    return [
        SongSpinCount(
            artist=artist,
            title=title,
            weekly_spins=count,
            current_tier=current_tiers.get((artist, title)),
        )
        for (artist, title), count in counter.most_common()
    ]


def _tier_rank(tier: RotationTier) -> int:
    """Higher = stronger rotation."""
    order = [
        RotationTier.RETIRED,
        RotationTier.NEW_ENTRY,
        RotationTier.C,
        RotationTier.B,
        RotationTier.A,
    ]
    return order.index(tier) if tier in order else -1
