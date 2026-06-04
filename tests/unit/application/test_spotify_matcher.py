from __future__ import annotations

from app.application.spotify.matcher import SpotifyMatcher
from app.core.settings import settings


def test_text_normalization() -> None:
    matcher = SpotifyMatcher()

    # Test feature string stripping
    assert matcher.normalize_text("Levitating (feat. DaBaby)") == "levitating"
    assert matcher.normalize_text("Levitating feat. DaBaby") == "levitating"
    assert matcher.normalize_text("Levitating featuring DaBaby") == "levitating"

    # Test punctuation stripping and spacing
    assert matcher.normalize_text("Don't Start Now!!!") == "don t start now"
    assert matcher.normalize_text("  Physical   ") == "physical"

    # Test parenthetical extra details removal
    assert matcher.normalize_text("Physical (produced by Ian)") == "physical"
    assert matcher.normalize_text("Levitating (Vocals Only)") == "levitating"
    assert matcher.normalize_text("Levitating (DaBaby Mix)") == "levitating"


def test_similarity_calculation() -> None:
    matcher = SpotifyMatcher()

    # Perfect match
    sim = matcher.calculate_similarity(
        db_title="Levitating",
        db_artist="Dua Lipa",
        sp_title="Levitating",
        sp_artists=["Dua Lipa"],
    )
    assert sim == 1.0

    # Match with collaborator in DB artist
    sim2 = matcher.calculate_similarity(
        db_title="Levitating",
        db_artist="Dua Lipa feat. DaBaby",
        sp_title="Levitating",
        sp_artists=["Dua Lipa", "DaBaby"],
    )
    # The artist normalization strips "feat. DaBaby" leaving "dua lipa",
    # which matches "Dua Lipa" perfectly.
    assert sim2 == 1.0

    # Typos in title
    sim3 = matcher.calculate_similarity(
        db_title="Levitatin",
        db_artist="Dua Lipa",
        sp_title="Levitating",
        sp_artists=["Dua Lipa"],
    )
    # Confidence is high but not 1.0
    assert 0.85 < sim3 < 1.0


def test_find_best_match_meets_threshold() -> None:
    matcher = SpotifyMatcher()

    tracks = [
        {
            "name": "Levitating (feat. DaBaby)",
            "artists": [{"name": "Dua Lipa"}, {"name": "DaBaby"}],
            "id": "track_match",
        },
        {
            "name": "Physical",
            "artists": [{"name": "Dua Lipa"}],
            "id": "track_wrong",
        },
    ]

    best_track, confidence = matcher.find_best_match(
        db_title="Levitating",
        db_artist="Dua Lipa",
        spotify_tracks=tracks,
    )

    assert best_track is not None
    assert best_track["id"] == "track_match"
    assert confidence >= settings.spotify_match_confidence_threshold


def test_find_best_match_below_threshold() -> None:
    matcher = SpotifyMatcher()

    tracks = [
        {
            "name": "Physical",
            "artists": [{"name": "Dua Lipa"}],
            "id": "track_wrong",
        }
    ]

    best_track, confidence = matcher.find_best_match(
        db_title="Levitating",
        db_artist="Dua Lipa",
        spotify_tracks=tracks,
    )

    assert best_track is None
    assert confidence < settings.spotify_match_confidence_threshold
