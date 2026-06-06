"""radoxo.com playlist page parser.

Parses https://radoxo.com/australia/nova-969/playlist and equivalent station pages.

Confirmed on real HTML (2026-06-06):
  li.playlist-track
    span.playlist-track__status.js-playlist-local-time[data-ts]  → Unix timestamp (seconds)
    span.playlist-track__song                                     → song title
    span.playlist-track__artist                                   → artist name

The data-ts attribute is a Unix timestamp in SECONDS, giving exact UTC broadcast
times to second precision. This is the most accurate timestamp source in the system.

Up to 86+ tracks per day (full day's playlist) available for the active tab.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

_DRIFT_FRACTION = 0.5
_MIN_EXPECTED_TRACKS = 4


@dataclass
class RadoxoParseResult:
    title: str
    artist: str
    played_at: datetime
    source_event_id: str | None = field(default=None)


def parse_radoxo_playlist(
    html: bytes | str,
    http_status: int | None = None,
    expected_min_tracks: int = _MIN_EXPECTED_TRACKS,
) -> list[RadoxoParseResult]:
    """Parse radoxo.com playlist page into track records.

    Returns an empty list on HTTP error or if no playlist structure is found.
    """
    if http_status is not None and http_status >= 400:
        logger.warning("radoxo: HTTP %s — returning empty", http_status)
        return []

    soup = BeautifulSoup(html, "lxml")
    tracks = soup.select("li.playlist-track")
    if not tracks:
        logger.info("radoxo: no li.playlist-track elements found")
        return []

    results: list[RadoxoParseResult] = []
    for track in tracks:
        if not isinstance(track, Tag):
            continue

        ts_el = track.select_one("span.playlist-track__status")
        title_el = track.select_one("span.playlist-track__song")
        artist_el = track.select_one("span.playlist-track__artist")

        if not title_el or not artist_el:
            continue

        title = title_el.get_text(strip=True)
        artist = artist_el.get_text(strip=True)
        if not title or not artist:
            continue

        played_at: datetime
        source_event_id: str | None = None
        if isinstance(ts_el, Tag):
            ts_raw = ts_el.get("data-ts")
            if ts_raw:
                try:
                    ts_int = int(str(ts_raw))
                    played_at = datetime.fromtimestamp(ts_int, tz=UTC)
                    source_event_id = f"radoxo-{ts_int}"
                except (ValueError, OSError):
                    played_at = datetime.now(tz=UTC)
            else:
                played_at = datetime.now(tz=UTC)
        else:
            played_at = datetime.now(tz=UTC)

        results.append(RadoxoParseResult(
            title=title,
            artist=artist,
            played_at=played_at,
            source_event_id=source_event_id,
        ))

    parsed = len(results)
    found = len(tracks)
    threshold = max(expected_min_tracks * _DRIFT_FRACTION, 1)
    if found and parsed < threshold:
        logger.warning(
            "radoxo: drift detected — parsed %d from %d tracks (expected >= %d)",
            parsed, found, threshold,
        )
    else:
        logger.info("radoxo: parsed %d tracks", parsed)

    return results
