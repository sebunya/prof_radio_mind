"""MusicBrainz enrichment service.

Looks up ISRC codes, canonical artist names, and release dates via the
MusicBrainz API. Results are used to populate songs.isrc and songs.label.

Rate limiting: MusicBrainz requires no more than 1 request/second from
unauthenticated clients and asks for a proper User-Agent. Authenticated
clients using MusicBrainz accounts get higher limits.

See: https://musicbrainz.org/doc/MusicBrainz_API
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_MB_BASE = "https://musicbrainz.org/ws/2"
_MB_USER_AGENT = "RMIAS/0.1.0 (radio-music-intelligence; contact@example.com)"
_REQUEST_TIMEOUT = 10.0


@dataclass
class EnrichmentResult:
    artist: str
    title: str
    isrc: str | None
    canonical_artist: str | None
    label: str | None
    release_date: str | None
    mb_recording_id: str | None


async def lookup_recording(artist: str, title: str) -> EnrichmentResult:
    """Query MusicBrainz for ISRC and label data for a (artist, title) pair.

    Uses the lucene search API to find the best matching recording.
    Returns None fields when no confident match is found.

    This call makes a live HTTP request — only call from scheduled enrichment
    jobs, never from unit tests.
    """
    from app.infrastructure.http.client import build_client

    query = f'recording:"{title}" AND artist:"{artist}"'
    params = {
        "query": query,
        "fmt": "json",
        "limit": "1",
    }

    try:
        async with await build_client(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.get(
                f"{_MB_BASE}/recording",
                params=params,
                headers={"User-Agent": _MB_USER_AGENT},
            )
    except Exception as exc:
        logger.warning("musicbrainz_lookup_failed artist=%s title=%s error=%s", artist, title, exc)
        return EnrichmentResult(
            artist=artist, title=title,
            isrc=None, canonical_artist=None, label=None,
            release_date=None, mb_recording_id=None,
        )

    if response.status_code != 200:
        logger.warning("musicbrainz_http_error status=%d", response.status_code)
        return EnrichmentResult(
            artist=artist, title=title,
            isrc=None, canonical_artist=None, label=None,
            release_date=None, mb_recording_id=None,
        )

    try:
        data = response.json()
        recordings = data.get("recordings", [])
    except Exception:
        return EnrichmentResult(
            artist=artist, title=title,
            isrc=None, canonical_artist=None, label=None,
            release_date=None, mb_recording_id=None,
        )

    if not recordings:
        return EnrichmentResult(
            artist=artist, title=title,
            isrc=None, canonical_artist=None, label=None,
            release_date=None, mb_recording_id=None,
        )

    rec = recordings[0]
    mb_id = rec.get("id")

    isrcs = rec.get("isrcs", [])
    isrc = isrcs[0] if isrcs else None

    canonical_artist = None
    artists = rec.get("artist-credit", [])
    if artists and isinstance(artists[0], dict):
        canonical_artist = artists[0].get("artist", {}).get("name")

    release_date = None
    releases = rec.get("releases", [])
    if releases:
        release_date = releases[0].get("date")

    label = None
    if releases:
        label_info = releases[0].get("label-info", [])
        if label_info and isinstance(label_info[0], dict):
            label = label_info[0].get("label", {}).get("name")

    logger.debug("musicbrainz_hit artist=%s title=%s isrc=%s", artist, title, isrc)
    return EnrichmentResult(
        artist=artist,
        title=title,
        isrc=isrc,
        canonical_artist=canonical_artist,
        label=label,
        release_date=release_date,
        mb_recording_id=mb_id,
    )


async def enrich_batch(
    songs: list[tuple[str, str]],
    delay_seconds: float = 1.1,
) -> list[EnrichmentResult]:
    """Enrich a batch of (artist, title) pairs with a respectful delay between calls."""
    import asyncio

    results: list[EnrichmentResult] = []
    for i, (artist, title) in enumerate(songs):
        result = await lookup_recording(artist, title)
        results.append(result)
        if i < len(songs) - 1:
            await asyncio.sleep(delay_seconds)
    return results
