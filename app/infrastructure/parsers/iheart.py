"""iHeart Now Playing JSON parser for KIIS-FM (station ID 2501).

CRITICAL: HTTP 204 responses MUST be handled before calling this parser.
Never call this parser with a 204 response — the caller (KIISIHeartCollector)
handles 204 as a NoTrackEvent.

VAL-KIIS-001: station ID 2501 is UNVALIDATED.
VAL-KIIS-003: HTTP 204 behaviour is UNCONFIRMED — guard is implemented regardless.
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
