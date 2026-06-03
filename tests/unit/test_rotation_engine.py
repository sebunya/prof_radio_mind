"""Tests for rotation tier engine — pure functions, no DB."""

from __future__ import annotations

import uuid

import pytest

from app.application.playlist.rotation_engine import (
    SongSpinCount,
    _tier_rank,
    build_recommendations,
    spin_counts_from_plays,
)
from app.domain.entities.playlist_recommendation import (
    RecommendationType,
    RotationTier,
    classify_tier,
)

# --- classify_tier ---

@pytest.mark.parametrize("spins,expected", [
    (50, RotationTier.A),
    (35, RotationTier.A),
    (34, RotationTier.B),
    (20, RotationTier.B),
    (19, RotationTier.C),
    (10, RotationTier.C),
    (9, RotationTier.NEW_ENTRY),
    (1, RotationTier.NEW_ENTRY),
    (0, RotationTier.RETIRED),
])
def test_classify_tier_thresholds(spins: int, expected: RotationTier) -> None:
    assert classify_tier(spins) == expected


# --- _tier_rank ---

def test_tier_rank_ordering() -> None:
    assert _tier_rank(RotationTier.RETIRED) < _tier_rank(RotationTier.NEW_ENTRY)
    assert _tier_rank(RotationTier.NEW_ENTRY) < _tier_rank(RotationTier.C)
    assert _tier_rank(RotationTier.C) < _tier_rank(RotationTier.B)
    assert _tier_rank(RotationTier.B) < _tier_rank(RotationTier.A)


# --- spin_counts_from_plays ---

def test_spin_counts_from_plays_counts_correctly() -> None:
    plays = [
        ("Artist A", "Song X"),
        ("Artist A", "Song X"),
        ("Artist B", "Song Y"),
    ]
    results = spin_counts_from_plays(plays)
    counts = {(r.artist, r.title): r.weekly_spins for r in results}
    assert counts[("Artist A", "Song X")] == 2
    assert counts[("Artist B", "Song Y")] == 1


def test_spin_counts_most_common_first() -> None:
    plays = [("A", "1"), ("B", "2"), ("B", "2"), ("B", "2")]
    results = spin_counts_from_plays(plays)
    assert results[0].artist == "B"
    assert results[0].weekly_spins == 3


def test_spin_counts_with_current_tiers() -> None:
    plays = [("A", "1"), ("A", "1")]
    tiers = {("A", "1"): RotationTier.B}
    results = spin_counts_from_plays(plays, current_tiers=tiers)
    assert results[0].current_tier == RotationTier.B


def test_spin_counts_no_current_tier_defaults_none() -> None:
    plays = [("A", "1")]
    results = spin_counts_from_plays(plays)
    assert results[0].current_tier is None


# --- build_recommendations ---

def _station() -> uuid.UUID:
    return uuid.uuid4()


def test_build_recommendations_new_song_add() -> None:
    station_id = _station()
    spins = [SongSpinCount("Artist", "Song", weekly_spins=25, current_tier=None)]
    recs = build_recommendations(station_id, spins)
    assert len(recs) == 1
    assert recs[0].recommendation_type == RecommendationType.ADD
    assert recs[0].recommended_tier == RotationTier.B


def test_build_recommendations_retired_new_song_skipped() -> None:
    station_id = _station()
    spins = [SongSpinCount("Artist", "Song", weekly_spins=0, current_tier=None)]
    recs = build_recommendations(station_id, spins)
    assert recs == []


def test_build_recommendations_maintain() -> None:
    station_id = _station()
    spins = [SongSpinCount("A", "T", weekly_spins=40, current_tier=RotationTier.A)]
    recs = build_recommendations(station_id, spins)
    assert recs[0].recommendation_type == RecommendationType.MAINTAIN


def test_build_recommendations_increase() -> None:
    station_id = _station()
    spins = [SongSpinCount("A", "T", weekly_spins=40, current_tier=RotationTier.B)]
    recs = build_recommendations(station_id, spins)
    assert recs[0].recommendation_type == RecommendationType.INCREASE
    assert recs[0].recommended_tier == RotationTier.A


def test_build_recommendations_decrease() -> None:
    station_id = _station()
    spins = [SongSpinCount("A", "T", weekly_spins=5, current_tier=RotationTier.B)]
    recs = build_recommendations(station_id, spins)
    assert recs[0].recommendation_type == RecommendationType.DECREASE
    assert recs[0].recommended_tier == RotationTier.NEW_ENTRY


def test_build_recommendations_retire() -> None:
    station_id = _station()
    spins = [SongSpinCount("A", "T", weekly_spins=0, current_tier=RotationTier.C)]
    recs = build_recommendations(station_id, spins)
    assert recs[0].recommendation_type == RecommendationType.RETIRE


def test_build_recommendations_sorted_by_spins_desc() -> None:
    station_id = _station()
    spins = [
        SongSpinCount("A", "1", weekly_spins=5, current_tier=None),
        SongSpinCount("B", "2", weekly_spins=40, current_tier=None),
        SongSpinCount("C", "3", weekly_spins=15, current_tier=None),
    ]
    recs = build_recommendations(station_id, spins)
    assert recs[0].weekly_spins == 40
    assert recs[-1].weekly_spins == 5


def test_build_recommendations_approved_defaults_false() -> None:
    station_id = _station()
    spins = [SongSpinCount("A", "T", weekly_spins=25, current_tier=None)]
    recs = build_recommendations(station_id, spins)
    assert recs[0].approved is False


def test_playlist_recommendation_approve() -> None:
    station_id = _station()
    spins = [SongSpinCount("A", "T", weekly_spins=25, current_tier=None)]
    recs = build_recommendations(station_id, spins)
    rec = recs[0]
    rec.approve(approved_by="dj@station.com")
    assert rec.approved is True
    assert rec.approved_by == "dj@station.com"
    assert rec.approved_at is not None
