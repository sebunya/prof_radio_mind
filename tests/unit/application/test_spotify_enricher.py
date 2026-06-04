from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.application.spotify.enricher import enrich_songs_batch
from app.infrastructure.database.models.events import Artist, Song


def test_enrich_songs_batch_no_pending() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)

    count = asyncio.run(enrich_songs_batch(session, batch_size=5))
    assert count == 0
    assert session.commit.call_count == 0


def test_enrich_songs_batch_matched_success() -> None:
    session = AsyncMock()

    song_id = uuid.uuid4()
    artist_id = uuid.uuid4()
    mock_song = Song(
        id=song_id,
        title="Levitating",
        artist_id=artist_id,
        isrc="GBARL2000020",
    )
    mock_artist = Artist(
        id=artist_id,
        name="Dua Lipa",
    )

    mock_result = MagicMock()
    mock_result.all.return_value = [(mock_song, mock_artist)]
    session.execute = AsyncMock(return_value=mock_result)

    # Mock client and matcher calls
    with (
        patch(
            "app.application.spotify.enricher.SpotifyClient"
        ) as mock_client_cls,
        patch(
            "app.application.spotify.enricher.SpotifyMatcher"
        ) as mock_matcher_cls,
    ):
        mock_client = mock_client_cls.return_value
        mock_client.search_track = AsyncMock(return_value=[{"id": "sp_track_1"}])

        mock_matcher = mock_matcher_cls.return_value
        mock_best_track = {
            "id": "sp_track_1",
            "name": "Levitating",
            "popularity": 92,
            "artists": [{"name": "Dua Lipa"}],
            "album": {
                "name": "Future Nostalgia",
                "images": [{"url": "url_640"}, {"url": "url_300"}],
            },
            "external_ids": {"isrc": "GBARL2000020"},
        }
        mock_matcher.find_best_match = MagicMock(
            return_value=(mock_best_track, 0.98)
        )

        count = asyncio.run(
            enrich_songs_batch(session, batch_size=5, delay_seconds=0.0)
        )
        assert count == 1

        # Verify columns updated correctly on model
        assert mock_song.spotify_track_id == "sp_track_1"
        assert mock_song.spotify_album_name == "Future Nostalgia"
        assert mock_song.spotify_artist_name == "Dua Lipa"
        assert mock_song.spotify_popularity == 92
        assert mock_song.spotify_thumbnail_url == "url_300"
        assert mock_song.spotify_match_confidence == 0.98
        assert mock_song.spotify_enriched_at is not None

        # Verify DB transaction was committed
        assert session.commit.call_count == 1


def test_enrich_songs_batch_failed_match() -> None:
    session = AsyncMock()

    song_id = uuid.uuid4()
    artist_id = uuid.uuid4()
    mock_song = Song(
        id=song_id,
        title="Unknown Track",
        artist_id=artist_id,
    )
    mock_artist = Artist(
        id=artist_id,
        name="Unknown Artist",
    )

    mock_result = MagicMock()
    mock_result.all.return_value = [(mock_song, mock_artist)]
    session.execute = AsyncMock(return_value=mock_result)

    with (
        patch(
            "app.application.spotify.enricher.SpotifyClient"
        ) as mock_client_cls,
        patch(
            "app.application.spotify.enricher.SpotifyMatcher"
        ) as mock_matcher_cls,
    ):
        mock_client = mock_client_cls.return_value
        mock_client.search_track = AsyncMock(return_value=[])

        mock_matcher = mock_matcher_cls.return_value
        mock_matcher.find_best_match = MagicMock(return_value=(None, 0.15))

        count = asyncio.run(
            enrich_songs_batch(session, batch_size=5, delay_seconds=0.0)
        )
        assert count == 1

        # Verify marked enriched with confidence but other properties empty
        assert mock_song.spotify_track_id is None
        assert mock_song.spotify_match_confidence == 0.15
        assert mock_song.spotify_enriched_at is not None

        assert session.commit.call_count == 1
