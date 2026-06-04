from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.spotify.matcher import SpotifyMatcher
from app.infrastructure.database.models.events import Artist as ArtistModel
from app.infrastructure.database.models.events import Song as SongModel
from app.infrastructure.spotify.client import SpotifyClient

logger = logging.getLogger(__name__)


async def enrich_songs_batch(
    session: AsyncSession, batch_size: int = 50, delay_seconds: float = 0.5
) -> int:
    """Fetch pending songs from the DB and enrich them with Spotify metadata."""
    # Find active songs that have not yet been enriched by Spotify
    stmt = (
        select(SongModel, ArtistModel)
        .join(ArtistModel, SongModel.artist_id == ArtistModel.id)
        .where(SongModel.spotify_enriched_at.is_(None))
        .limit(batch_size)
    )

    result = await session.execute(stmt)
    rows = result.all()
    if not rows:
        return 0

    client = SpotifyClient()
    matcher = SpotifyMatcher()
    enriched_count = 0

    for i, (song, artist) in enumerate(rows):
        title = song.title
        artist_name = artist.name
        isrc = song.isrc

        logger.info(
            "Enriching song id=%s title=%r artist=%r isrc=%r",
            song.id,
            title,
            artist_name,
            isrc,
        )

        try:
            # Search tracks on Spotify catalog
            tracks = await client.search_track(title, artist_name, isrc)
            best_track, confidence = matcher.find_best_match(
                title, artist_name, tracks
            )

            now = datetime.now(UTC)
            song.spotify_enriched_at = now
            song.spotify_match_confidence = confidence

            if best_track:
                song.spotify_track_id = best_track.get("id")
                song.spotify_album_name = best_track.get("album", {}).get("name")

                # Retrieve comma-separated artists list
                artists_list = [
                    a.get("name", "") for a in best_track.get("artists", [])
                ]
                song.spotify_artist_name = ", ".join(artists_list)

                song.spotify_popularity = best_track.get("popularity", 0)

                # Smallest image is typically the last in the array (e.g. 64x64 thumbnail)
                images = best_track.get("album", {}).get("images", [])
                if images:
                    song.spotify_thumbnail_url = images[-1].get("url")
                else:
                    song.spotify_thumbnail_url = None

                # Extract matched ISRC
                spotify_isrc = best_track.get("external_ids", {}).get("isrc")
                song.spotify_isrc = spotify_isrc

                # Option: Backfill core song isrc if empty
                if not song.isrc and spotify_isrc:
                    song.isrc = spotify_isrc

                logger.info(
                    "Spotify match found: title=%r confidence=%.2f track_id=%s",
                    best_track.get("name"),
                    confidence,
                    song.spotify_track_id,
                )
            else:
                logger.info(
                    "No Spotify match found: confidence=%.2f (below threshold)",
                    confidence,
                )

            enriched_count += 1

        except Exception as e:
            logger.error("Failed to enrich song id=%s: %s", song.id, e)

        # Respectful API delay sleep between lookups
        if i < len(rows) - 1:
            await asyncio.sleep(delay_seconds)

    # Persist the batch updates
    await session.commit()
    return enriched_count
