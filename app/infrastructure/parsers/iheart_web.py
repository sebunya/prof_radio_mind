"""iHeart web recently-played page parser.

Parses https://kiisfm.iheart.com/music/recently-played/ (and equivalent pages
for other iHeart stations) into a list of track records.

Strategy 1: __NEXT_DATA__ JSON embedded in <script id="__NEXT_DATA__"> (Next.js SSR).
            Recursively searches for recentlyPlayedSongs / songs / tracks keys.
Strategy 2: CSS selectors (TBD — update after running dry_run_kiis_iheart_web
            and inspecting the raw HTML).

Returns an empty list when the page is CSR-only (skeleton HTML, no SSR data).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

_TRACK_LIST_KEYS = frozenset({
    "recentlyPlayedSongs", "recentlyPlayed", "songHistory",
    "playHistory", "songs", "tracks", "playlist",
})
_MAX_DEPTH = 10


@dataclass
class IHeartWebParseResult:
    title: str
    artist: str
    played_at: datetime


def _find_track_list(data: Any, depth: int = 0) -> list | None:
    """Recursively locate the first list that looks like a track list."""
    if depth > _MAX_DEPTH:
        return None
    if isinstance(data, dict):
        for key in _TRACK_LIST_KEYS:
            val = data.get(key)
            if isinstance(val, list) and val:
                return val
        for value in data.values():
            found = _find_track_list(value, depth + 1)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_track_list(item, depth + 1)
            if found is not None:
                return found
    return None


def _extract_artist(item: dict) -> str:
    raw = item.get("artist") or item.get("artistName") or item.get("artistData") or ""
    if isinstance(raw, dict):
        raw = raw.get("name") or raw.get("artistName") or ""
    return str(raw).strip()


def _extract_played_at(item: dict) -> datetime:
    ts = (
        item.get("startTime")
        or item.get("playedAt")
        or item.get("timestamp")
        or item.get("airtime")
    )
    if isinstance(ts, (int, float)):
        # Unix timestamp — milliseconds if > 1e10, else seconds
        seconds = ts / 1000 if ts > 1_000_000_000_000 else ts
        return datetime.fromtimestamp(seconds, tz=UTC)
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(tz=UTC)


def _try_next_data(soup: BeautifulSoup) -> list[IHeartWebParseResult] | None:
    script = soup.find("script", id="__NEXT_DATA__")
    if not isinstance(script, Tag):
        return None
    try:
        data = json.loads(script.string or "")
    except (json.JSONDecodeError, TypeError):
        logger.debug("iheart_web: __NEXT_DATA__ present but JSON is invalid")
        return None

    raw_tracks = _find_track_list(data)
    if raw_tracks is None:
        logger.debug("iheart_web: __NEXT_DATA__ parsed but no track list key found")
        return None

    results: list[IHeartWebParseResult] = []
    for item in raw_tracks:
        if not isinstance(item, dict):
            continue
        title = str(
            item.get("title") or item.get("trackTitle") or item.get("name") or ""
        ).strip()
        artist = _extract_artist(item)
        if not title or not artist:
            continue
        results.append(IHeartWebParseResult(
            title=title,
            artist=artist,
            played_at=_extract_played_at(item),
        ))

    return results if results else None


def parse_iheart_web_recently_played(
    html: bytes | str,
    http_status: int | None = None,
) -> list[IHeartWebParseResult]:
    """Parse iHeart recently-played web page into track records.

    Returns an empty list when the page is CSR-only or structures are unknown.
    Caller should save raw HTML via the dry-run script if this returns empty.
    """
    if http_status is not None and http_status >= 400:
        logger.warning("iheart_web: HTTP %s — returning empty", http_status)
        return []

    soup = BeautifulSoup(html, "lxml")

    results = _try_next_data(soup)
    if results is not None:
        logger.info("iheart_web: __NEXT_DATA__ strategy returned %d tracks", len(results))
        return results

    # CSS strategy: TBD — run dry_run_kiis_iheart_web to obtain real HTML,
    # then add selectors here.
    logger.info(
        "iheart_web: page appears CSR-only or structure unknown — "
        "run dry_run_kiis_iheart_web and inspect /tmp/kiis_iheart_web_raw.html"
    )
    return []
