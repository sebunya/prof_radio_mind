"""iHeart JSON parsers — now-playing, recently-played, and top-songs.

CRITICAL: HTTP 204 responses MUST be handled before calling these parsers.
Never call them with a 204 response — the callers handle 204 as a NoTrackEvent.

VAL-KIIS-001: stream ID 2501 is UNVALIDATED.
VAL-KIIS-003: HTTP 204 behaviour is UNCONFIRMED — guard is implemented regardless.
VAL-IHEART-TOP-001: topSongs endpoint URL and response schema are UNVALIDATED.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class IHeartParseResult:
    artist: str
    title: str
    source_event_id: str | None
    played_at: datetime
    parse_errors: list[str] = field(default_factory=list)


def parse_iheart_now_playing(
    raw_bytes: bytes,
    http_status: int | None,
) -> IHeartParseResult | None:
    """Parse iHeart now-playing JSON response.

    Returns None if http_status is 204 (caller should handle this as NoTrackEvent).
    Raises ValueError if the JSON structure does not match the expected schema.

    Args:
        raw_bytes: Raw response body bytes
        http_status: HTTP status code — 204 returns None immediately
    """
    # CRITICAL: HTTP 204 = no track playing — never parse the body
    if http_status == 204:
        return None

    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"iHeart response is not valid JSON: {exc}") from exc

    current = data.get("currentTrack")
    if not current or not isinstance(current, dict):
        raise ValueError("iHeart response missing 'currentTrack' field")

    artist = (current.get("artist") or "").strip()
    title = (current.get("title") or "").strip()

    if not artist or not title:
        raise ValueError(
            f"iHeart currentTrack missing artist or title: artist={artist!r} title={title!r}"
        )

    source_event_id = current.get("id")
    start_time = current.get("startTime")

    if start_time is not None:
        ts = int(start_time)
        if ts > 1_000_000_000_000:  # milliseconds
            ts //= 1000
        played_at = datetime.fromtimestamp(ts, tz=UTC)
    else:
        played_at = datetime.now(tz=UTC)

    return IHeartParseResult(
        artist=artist,
        title=title,
        source_event_id=str(source_event_id) if source_event_id else None,
        played_at=played_at,
    )


def parse_iheart_recently_played(
    raw_bytes: bytes,
    http_status: int | None,
) -> list[IHeartParseResult]:
    """Parse iHeart recently-played JSON response into a list of results.

    The recentlyPlayed endpoint returns the last N tracks played at the station.
    Expected response shape::

        {"tracks": [{"id": ..., "artist": "...", "title": "...", "startTime": ...}, ...]}

    Falls back to ``recentTracks`` key if ``tracks`` is absent.

    Returns an empty list for HTTP 204. Raises ValueError on malformed JSON or
    missing/unrecognised structure.

    Args:
        raw_bytes: Raw response body bytes
        http_status: HTTP status code — 204 returns [] immediately
    """
    if http_status == 204:
        return []

    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"iHeart recentlyPlayed response is not valid JSON: {exc}") from exc

    track_list = data.get("tracks") or data.get("recentTracks")
    if track_list is None:
        raise ValueError(
            "iHeart recentlyPlayed response missing 'tracks' or 'recentTracks' field"
        )
    if not isinstance(track_list, list):
        raise ValueError("iHeart recentlyPlayed 'tracks' field is not a list")

    results: list[IHeartParseResult] = []
    for item in track_list:
        if not isinstance(item, dict):
            continue

        artist = (item.get("artist") or "").strip()
        title = (item.get("title") or "").strip()
        if not artist or not title:
            continue

        source_event_id = item.get("id")
        start_time = item.get("startTime")
        if start_time is not None:
            ts = int(start_time)
            if ts > 1_000_000_000_000:
                ts //= 1000
            played_at = datetime.fromtimestamp(ts, tz=UTC)
        else:
            played_at = datetime.now(tz=UTC)

        results.append(
            IHeartParseResult(
                artist=artist,
                title=title,
                source_event_id=str(source_event_id) if source_event_id else None,
                played_at=played_at,
            )
        )

    return results


# ── Top-songs parser ──────────────────────────────────────────────────────────

@dataclass
class IHeartTopSongResult:
    artist: str
    title: str
    rank: int
    play_count: int | None
    source_event_id: str | None
    snapshot_at: datetime


def parse_iheart_top_songs(
    raw_bytes: bytes,
    http_status: int | None,
    *,
    iheart_station_id: str,
) -> list[IHeartTopSongResult]:
    """Parse iHeart top-songs JSON response into a ranked list.

    The topSongs endpoint returns the station's most-played songs for a rolling
    period (typically weekly).  Expected response shape::

        {
            "topSongs": [
                {"id": "...", "artist": "...", "title": "...", "rank": 1, "playCount": 47},
                ...
            ],
            "stationId": "821",
            "period": "weekly"
        }

    Falls back to ``songs`` key if ``topSongs`` is absent.

    Returns an empty list for HTTP 204 or when no songs are present.
    Raises ValueError on malformed JSON or unrecognised structure.

    VAL-IHEART-TOP-001: endpoint URL and exact schema are UNVALIDATED.

    Args:
        raw_bytes: Raw response body bytes.
        http_status: HTTP status code — 204 returns [] immediately.
        iheart_station_id: Numeric iHeart station ID (used to build source_event_id).
    """
    if http_status == 204:
        return []

    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"iHeart topSongs response is not valid JSON: {exc}") from exc

    _sentinel = object()
    song_list = data.get("topSongs", _sentinel)
    if song_list is _sentinel:
        song_list = data.get("songs", _sentinel)
    if song_list is _sentinel:
        raise ValueError("iHeart topSongs response missing 'topSongs' or 'songs' field")
    if not isinstance(song_list, list):
        raise ValueError("iHeart topSongs field is not a list")

    snapshot_at = datetime.now(tz=UTC)
    date_str = snapshot_at.strftime("%Y%m%d")

    results: list[IHeartTopSongResult] = []
    for item in song_list:
        if not isinstance(item, dict):
            continue

        artist = (item.get("artist") or item.get("artistName") or "").strip()
        title = (item.get("title") or "").strip()
        if not artist or not title:
            continue

        rank_raw = item.get("rank")
        rank = int(rank_raw) if rank_raw is not None else (len(results) + 1)

        play_count_raw = item.get("playCount") or item.get("play_count")
        play_count = int(play_count_raw) if play_count_raw is not None else None

        # source_event_id encodes station + rank + date so the same chart
        # position deduplicates within a single day's worth of polls.
        raw_id = item.get("id")
        source_event_id = (
            str(raw_id)
            if raw_id
            else f"iheart-top-{iheart_station_id}-rank{rank}-{date_str}"
        )

        results.append(
            IHeartTopSongResult(
                artist=artist,
                title=title,
                rank=rank,
                play_count=play_count,
                source_event_id=source_event_id,
                snapshot_at=snapshot_at,
            )
        )

    return results
