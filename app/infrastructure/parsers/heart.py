"""Heart FM last-played-songs HTML parser.

Parses https://www.heart.co.uk/radio/last-played-songs/ — the official Heart FM
recently-played page — into a list of track results.

VAL-HEARTFM-002 UNVALIDATED: CSS selectors below (div.station-song-history,
div.song-item, span.song-item__title, span.song-item__artist, time.song-item__time)
were designed against a synthetic fixture and MUST be verified against the live page
before enabling the collector. See docs/VALIDATION_REGISTER.md.

On selector drift, the parser raises ValueError so the base collector marks the run
FAILED and creates a review item — never silently returns zero rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time

from bs4 import BeautifulSoup, Tag


@dataclass
class HeartParseResult:
    artist: str
    title: str
    played_at: datetime
    source_event_id: str | None = None
    parse_errors: list[str] = field(default_factory=list)


def parse_heart_last_played(
    html: bytes | str,
    http_status: int | None = None,
    base_date: date | None = None,
) -> list[HeartParseResult]:
    """Parse Heart FM last-played-songs HTML into a list of track results.

    Returns an empty list for HTTP 204 or an empty track history section.
    Raises ValueError when the page structure is missing or unrecognisable
    (enables drift detection — never silently returns zero on a structural mismatch).

    Args:
        html: Raw response body (bytes or str)
        http_status: HTTP status code — 204 returns [] immediately
        base_date: UTC date used to anchor HH:MM timestamps (defaults to today)
    """
    if http_status == 204:
        return []

    if not html:
        raise ValueError("Heart FM last-played-songs response is empty")

    if base_date is None:
        base_date = datetime.now(tz=UTC).date()

    soup = BeautifulSoup(html, "lxml")

    container = soup.select_one("div.station-song-history")
    if container is None:
        raise ValueError(
            "Heart FM: could not find div.station-song-history — "
            "selector drift? Run VAL-HEARTFM-002 against the live page."
        )

    items = container.select("div.song-item")
    if not items:
        return []

    results: list[HeartParseResult] = []
    for item in items:
        if not isinstance(item, Tag):
            continue

        title_el = item.select_one("span.song-item__title")
        artist_el = item.select_one("span.song-item__artist")

        title = title_el.get_text(strip=True) if title_el else ""
        artist = artist_el.get_text(strip=True) if artist_el else ""

        if not title or not artist:
            continue

        # Extract source_event_id from data-track-id attribute
        track_id = item.get("data-track-id")
        source_event_id = str(track_id) if track_id else None

        # Parse time from <time> element
        time_el = item.select_one("time.song-item__time")
        played_at = _parse_time_element(time_el, base_date)

        results.append(
            HeartParseResult(
                artist=artist,
                title=title,
                played_at=played_at,
                source_event_id=source_event_id,
            )
        )

    return results


def _parse_time_element(
    time_el: Tag | None,
    base_date: date,
) -> datetime:
    """Convert a <time> element's text (HH:MM) to a UTC-aware datetime.

    Falls back to datetime.now(UTC) when the element is absent or unparseable.
    All Heart FM broadcasts are in UK time (Europe/London); we use UTC directly
    since the page displays times in the user's local context and we lack the
    DST offset without a live network call.  VAL-HEARTFM-005 covers this assumption.
    """
    if time_el is None:
        return datetime.now(tz=UTC)

    raw = time_el.get_text(strip=True)
    try:
        h, m = (int(p) for p in raw.split(":"))
        return datetime.combine(base_date, time(h, m), tzinfo=UTC)
    except (ValueError, AttributeError):
        return datetime.now(tz=UTC)
