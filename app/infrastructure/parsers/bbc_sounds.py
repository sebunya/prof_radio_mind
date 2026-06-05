"""BBC Sounds (BBC RMS) JSON parser for BBC Radio 1 now-playing segments.

Endpoint: GET https://rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest

The response is a list of recently broadcast segments in reverse chronological order.
Each segment has a type ("music" or "speech") and contributor/title metadata.
Only "music" segments produce PlayEvents; speech segments are silently skipped.

VAL-BBC1-001: live reachability UNVALIDATED.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class BBCSoundsParseResult:
    artist: str
    title: str
    source_event_id: str | None
    played_at: datetime
    parse_errors: list[str] = field(default_factory=list)


def parse_bbc_sounds_now_playing(
    raw_bytes: bytes,
    http_status: int | None,
) -> BBCSoundsParseResult | None:
    """Parse BBC Sounds RMS API response to extract the current (most recent music) track.

    Returns None when http_status is 204 or when all segments are non-music (speech/jingle).
    Raises ValueError on malformed JSON or unrecognised top-level structure.

    Args:
        raw_bytes: Raw response body bytes
        http_status: HTTP status code — 204 returns None immediately
    """
    if http_status == 204:
        return None

    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"BBC Sounds response is not valid JSON: {exc}") from exc

    segments = data.get("data")
    if segments is None:
        raise ValueError("BBC Sounds response missing 'data' field")
    if not isinstance(segments, list):
        raise ValueError("BBC Sounds 'data' field is not a list")

    # Prefer the segment flagged now_playing=true; fall back to first music segment.
    current: dict | None = None
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        if seg.get("type") != "music":
            continue
        offset = seg.get("offset") or {}
        if offset.get("now_playing") is True:
            current = seg
            break
        if current is None:
            current = seg  # first music segment as fallback

    if current is None:
        return None

    contributors = current.get("primary_contributors") or []
    artist = ""
    if isinstance(contributors, list) and contributors:
        first = contributors[0]
        if isinstance(first, dict):
            artist = (first.get("name") or "").strip()

    titles = current.get("titles") or {}
    title = (titles.get("primary") or "").strip() if isinstance(titles, dict) else ""

    if not artist or not title:
        return None

    source_event_id = current.get("id")
    start_time = (current.get("offset") or {}).get("start")
    if start_time is not None:
        ts = int(start_time)
        if ts > 1_000_000_000_000:  # milliseconds guard
            ts //= 1000
        played_at = datetime.fromtimestamp(ts, tz=UTC)
    else:
        played_at = datetime.now(tz=UTC)

    return BBCSoundsParseResult(
        artist=artist,
        title=title,
        source_event_id=str(source_event_id) if source_event_id else None,
        played_at=played_at,
    )
