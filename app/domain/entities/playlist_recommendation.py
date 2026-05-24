"""PlaylistRecommendation domain entity and rotation tier classification."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class RotationTier(StrEnum):
    A = "A"          # Power rotation — 35–50 spins/week
    B = "B"          # Medium rotation — 20–34 spins/week
    C = "C"          # Light rotation — 10–19 spins/week
    NEW_ENTRY = "new_entry"   # Testing phase — 1–9 spins/week
    RETIRED = "retired"       # 0 spins — removed from rotation


class RecommendationType(StrEnum):
    ADD = "add"               # Song not in playlist; trending up
    INCREASE = "increase"     # Move to higher rotation tier
    DECREASE = "decrease"     # Move to lower rotation tier (fatigue)
    RETIRE = "retire"         # Remove from rotation
    MAINTAIN = "maintain"     # No change needed


_TIER_THRESHOLDS: list[tuple[int, RotationTier]] = [
    (35, RotationTier.A),
    (20, RotationTier.B),
    (10, RotationTier.C),
    (1, RotationTier.NEW_ENTRY),
]


def classify_tier(weekly_spins: int) -> RotationTier:
    """Return the rotation tier for a given weekly spin count."""
    for threshold, tier in _TIER_THRESHOLDS:
        if weekly_spins >= threshold:
            return tier
    return RotationTier.RETIRED


@dataclass
class PlaylistRecommendation:
    id: uuid.UUID
    station_id: uuid.UUID
    artist: str
    title: str
    current_tier: RotationTier | None
    recommended_tier: RotationTier
    recommendation_type: RecommendationType
    weekly_spins: int
    reason: str
    approved: bool
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        station_id: uuid.UUID,
        artist: str,
        title: str,
        current_tier: RotationTier | None,
        recommended_tier: RotationTier,
        recommendation_type: RecommendationType,
        weekly_spins: int,
        reason: str,
    ) -> PlaylistRecommendation:
        return cls(
            id=uuid.uuid4(),
            station_id=station_id,
            artist=artist,
            title=title,
            current_tier=current_tier,
            recommended_tier=recommended_tier,
            recommendation_type=recommendation_type,
            weekly_spins=weekly_spins,
            reason=reason,
            approved=False,
            approved_by=None,
            approved_at=None,
            created_at=datetime.now(tz=UTC),
        )

    def approve(self, approved_by: str) -> None:
        self.approved = True
        self.approved_by = approved_by
        self.approved_at = datetime.now(tz=UTC)
