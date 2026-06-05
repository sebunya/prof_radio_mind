"""Heart FM last-played-songs HTML parser.

Parses https://www.heart.co.uk/radio/last-played-songs/ into a list of track results.

VAL-HEARTFM-002: Selector drift confirmed on 2026-06-05. Old selectors
(div.station-song-history, div.song-item, span.song-item__title) replaced with
new selectors (div.last_played_songs, div.song_wrapper, div.song__text-content).

Three-strategy parsing order:
  1. __NEXT_DATA__ JSON  — embedded Next.js page props (most robust; survives CSS changes)
  2. New CSS selectors   — div.last_played_songs > div.song_wrapper (live as of 2026-06-05)
  3. Old CSS selectors   — div.station-song-history > div.song-item (pre-drift fallback)

Raises ValueError when all three strategies fail so the collector marks the run
FAILED and a review item is created — never silently returns zero rows on drift.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from typing import Any

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


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
    Raises ValueError when the page structure is missing or unrecognisable.

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

    # Strategy 1: __NEXT_DATA__ JSON (Next.js — survives CSS redesigns)
    results = _try_next_data(soup, base_date)
    if results is not None:
        return results

    # Strategy 2: new CSS selectors (live as of 2026-06-05)
    results = _try_new_selectors(soup, base_date)
    if results is not None:
        return results

    # Strategy 3: old CSS selectors (pre-drift backwards compat)
    results = _try_old_selectors(soup, base_date)
    if results is not None:
        return results

    raise ValueError(
        "Heart FM: page structure unrecognised — all three parsing strategies failed. "
        "Check div.last_played_songs, div.station-song-history, and __NEXT_DATA__. "
        "Selector drift? Re-run VAL-HEARTFM-002 against the live page."
    )


# ─── Strategy 1: __NEXT_DATA__ ────────────────────────────────────────────────


def _try_next_data(soup: BeautifulSoup, base_date: date) -> list[HeartParseResult] | None:
    """Extract tracks from the embedded Next.js __NEXT_DATA__ JSON block.

    Returns None if the script tag is absent (not a Next.js page).
    Returns [] if the block is present but contains no track data.
    """
    script = soup.find("script", {"id": "__NEXT_DATA__"})
    if not isinstance(script, Tag):
        return None

    try:
        data: dict[str, Any] = json.loads(script.string or "")
    except (json.JSONDecodeError, TypeError):
        logger.debug("Heart FM __NEXT_DATA__: JSON parse failed")
        return None

    tracks = _find_tracks_in_next_data(data)
    if tracks is None:
        logger.debug("Heart FM __NEXT_DATA__: no track list found in page props")
        return None

    results: list[HeartParseResult] = []
    for item in tracks:
        title = str(item.get("title", "") or item.get("trackName", "") or "").strip()
        artist = str(item.get("artist", "") or item.get("artistName", "") or "").strip()
        if not title or not artist:
            continue

        time_str = str(item.get("playTime", "") or item.get("time", "") or "").strip()
        played_at = _parse_time_str(time_str, base_date)
        track_id = str(item.get("id", "") or item.get("trackId", "") or "").strip() or None

        results.append(
            HeartParseResult(
                artist=artist,
                title=title,
                played_at=played_at,
                source_event_id=track_id,
            )
        )

    return results


def _find_tracks_in_next_data(data: Any, _depth: int = 0) -> list[dict] | None:
    """Recursively search for a list of track-shaped objects in the NEXT_DATA tree.

    A track-shaped object has string fields 'title' (or 'trackName') and
    'artist' (or 'artistName').  Stops at depth 8 to avoid runaway recursion.
    """
    if _depth > 8:
        return None

    if isinstance(data, list) and len(data) > 0:
        sample = data[0]
        if isinstance(sample, dict) and (
            ("title" in sample or "trackName" in sample)
            and ("artist" in sample or "artistName" in sample)
        ):
            return data

    if isinstance(data, dict):
        for key in ("lastPlayedSongs", "recentlyPlayed", "tracklist", "songs", "tracks"):
            if key in data and isinstance(data[key], list):
                candidate = data[key]
                if candidate and isinstance(candidate[0], dict):
                    return candidate

        for v in data.values():
            found = _find_tracks_in_next_data(v, _depth + 1)
            if found is not None:
                return found

    if isinstance(data, list):
        for item in data:
            found = _find_tracks_in_next_data(item, _depth + 1)
            if found is not None:
                return found

    return None


# ─── Strategy 2: new CSS selectors (2026-06-05) ──────────────────────────────


def _try_new_selectors(soup: BeautifulSoup, base_date: date) -> list[HeartParseResult] | None:
    """Parse using div.last_played_songs > div.song_wrapper structure.

    Returns None if the container is absent (strategy not applicable).
    Returns [] if the container is present but empty.
    """
    container = soup.select_one("div.last_played_songs")
    if container is None:
        return None

    items = container.select("div.song_wrapper")
    if not items:
        return []

    results: list[HeartParseResult] = []
    for item in items:
        if not isinstance(item, Tag):
            continue

        title, artist = _extract_title_artist_new(item)
        if not title or not artist:
            continue

        track_id = item.get("data-track-id")
        source_event_id = str(track_id) if track_id else None

        time_el = item.select_one("span.song__time") or item.select_one("time")
        time_str = time_el.get_text(strip=True) if time_el else ""
        played_at = _parse_time_str(time_str, base_date)

        results.append(
            HeartParseResult(
                artist=artist,
                title=title,
                played_at=played_at,
                source_event_id=source_event_id,
            )
        )

    return results


def _extract_title_artist_new(item: Tag) -> tuple[str, str]:
    """Extract title and artist from a song_wrapper element.

    Tries explicit class names first; falls back to positional children of
    song__text-content when classes are absent.
    """
    content = item.select_one("div.song__text-content")

    # Explicit class approach
    title_el = item.select_one("p.song__title") or item.select_one("span.song__title")
    artist_el = item.select_one("p.song__artist") or item.select_one("span.song__artist")
    if title_el and artist_el:
        return title_el.get_text(strip=True), artist_el.get_text(strip=True)

    # Positional fallback: first two block children of song__text-content
    if content is not None:
        children = [c for c in content.children if isinstance(c, Tag)]
        if len(children) >= 2:
            return children[0].get_text(strip=True), children[1].get_text(strip=True)
        if len(children) == 1:
            text = children[0].get_text(strip=True)
            if " - " in text:
                parts = text.split(" - ", 1)
                return parts[1].strip(), parts[0].strip()

    return "", ""


# ─── Strategy 3: old CSS selectors (pre-drift) ───────────────────────────────


def _try_old_selectors(soup: BeautifulSoup, base_date: date) -> list[HeartParseResult] | None:
    """Parse using legacy div.station-song-history > div.song-item structure.

    Returns None if the container is absent (strategy not applicable).
    """
    container = soup.select_one("div.station-song-history")
    if container is None:
        return None

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

        track_id = item.get("data-track-id")
        source_event_id = str(track_id) if track_id else None

        time_el = item.select_one("time.song-item__time")
        time_str = time_el.get_text(strip=True) if time_el else ""
        played_at = _parse_time_str(time_str, base_date)

        results.append(
            HeartParseResult(
                artist=artist,
                title=title,
                played_at=played_at,
                source_event_id=source_event_id,
            )
        )

    return results


# ─── Shared helpers ───────────────────────────────────────────────────────────


def _parse_time_str(raw: str, base_date: date) -> datetime:
    """Convert 'HH:MM' to a UTC-aware datetime anchored to base_date.

    Falls back to datetime.now(UTC) when the string is absent or unparseable.
    All Heart FM broadcasts are in UK time; we use UTC directly since the page
    displays times in the user's local context and we lack the DST offset
    without a live network call. VAL-HEARTFM-005 covers this assumption.
    """
    try:
        h, m = (int(p) for p in raw.strip().split(":"))
        return datetime.combine(base_date, time(h, m), tzinfo=UTC)
    except (ValueError, AttributeError):
        return datetime.now(tz=UTC)


# Keep the old name for any code that imports _parse_time_element directly.
def _parse_time_element(time_el: Tag | None, base_date: date) -> datetime:
    raw = time_el.get_text(strip=True) if time_el else ""
    return _parse_time_str(raw, base_date)
