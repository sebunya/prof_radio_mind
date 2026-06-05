"""ukradiolive.com playlist page parser.

Parses https://ukradiolive.com/capital-fm/playlist into track records.

Strategy 1: __NEXT_DATA__ JSON (Next.js SSR — common for UK radio aggregators).
Strategy 2: CSS selectors (TBD — update after running dry_run_capital_ukradiolive).

Returns an empty list when structure is unknown. Run the dry-run script to
capture raw HTML and inform selector development.
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
    "songs", "tracks", "playlist", "history", "recentTracks",
    "recentlyPlayed", "nowPlaying", "playlistItems",
})
_MAX_DEPTH = 10


@dataclass
class UKRadioLiveParseResult:
    title: str
    artist: str
    played_at: datetime


def _find_track_list(data: Any, depth: int = 0) -> list | None:
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


def _extract_played_at(item: dict) -> datetime:
    ts = item.get("time") or item.get("timestamp") or item.get("playedAt") or item.get("startTime")
    if isinstance(ts, (int, float)):
        seconds = ts / 1000 if ts > 1_000_000_000_000 else ts
        return datetime.fromtimestamp(seconds, tz=UTC)
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(tz=UTC)


def _try_next_data(soup: BeautifulSoup) -> list[UKRadioLiveParseResult] | None:
    script = soup.find("script", id="__NEXT_DATA__")
    if not isinstance(script, Tag):
        return None
    try:
        data = json.loads(script.string or "")
    except (json.JSONDecodeError, TypeError):
        logger.debug("ukradiolive: __NEXT_DATA__ present but JSON invalid")
        return None

    raw_tracks = _find_track_list(data)
    if raw_tracks is None:
        logger.debug("ukradiolive: __NEXT_DATA__ parsed but no track list found")
        return None

    results: list[UKRadioLiveParseResult] = []
    for item in raw_tracks:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("name") or item.get("song") or "").strip()
        artist = str(
            item.get("artist") or item.get("artistName") or item.get("author") or ""
        ).strip()
        if not title or not artist:
            continue
        results.append(UKRadioLiveParseResult(
            title=title,
            artist=artist,
            played_at=_extract_played_at(item),
        ))

    return results if results else None


def parse_ukradiolive_playlist(
    html: bytes | str,
    http_status: int | None = None,
) -> list[UKRadioLiveParseResult]:
    """Parse ukradiolive.com playlist page into track records.

    Returns an empty list when no known structure is found. Run
    dry_run_capital_ukradiolive to save raw HTML for selector development.
    """
    if http_status is not None and http_status >= 400:
        logger.warning("ukradiolive: HTTP %s — returning empty", http_status)
        return []

    soup = BeautifulSoup(html, "lxml")

    results = _try_next_data(soup)
    if results is not None:
        logger.info("ukradiolive: __NEXT_DATA__ strategy returned %d tracks", len(results))
        return results

    # CSS strategy: TBD — run dry_run_capital_ukradiolive and inspect
    # /tmp/capital_ukradiolive_raw.html to identify the correct selectors.
    logger.info(
        "ukradiolive: no __NEXT_DATA__ and no CSS selectors configured — "
        "inspect /tmp/capital_ukradiolive_raw.html"
    )
    return []
