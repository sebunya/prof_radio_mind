"""ukradiolive.com playlist page parser.

Parses https://ukradiolive.com/capital-fm/playlist into track records.

Strategy 1: __NEXT_DATA__ JSON (Next.js SSR).
Strategy 2: plist-item CSS selectors — confirmed on real ukradiolive.com HTML (2026-06-06).
  Each song is a div[class*="plist-item"] with:
    span.txt2.mcolumn                         → "LIVE - DD.MM HH:MM" or "DD.MM HH:MM"
    span.txtsong.mcolumn span[itemprop="byArtist"] → artist
    span.txtsong.mcolumn span[itemprop="name"]     → title
    div[data-id]                              → source event ID
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, Tag

from app.infrastructure.parsers._json_utils import find_track_list

logger = logging.getLogger(__name__)

_LONDON = ZoneInfo("Europe/London")
_PLIST_TIME_RE = re.compile(r"(?:LIVE\s*-\s*)?(\d{1,2})\.(\d{2})\s+(\d{2}):(\d{2})")


@dataclass
class UKRadioLiveParseResult:
    title: str
    artist: str
    played_at: datetime
    source_event_id: str | None = field(default=None)


def _extract_played_at(item: dict) -> datetime:
    ts = (
        item.get("time") or item.get("timestamp")
        or item.get("playedAt") or item.get("startTime")
    )
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

    raw_tracks = find_track_list(data)
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


def _parse_plist_time(time_str: str, ref_year: int, ref_month: int) -> datetime:
    """Parse ukradiolive time format to UTC datetime.

    Accepts 'LIVE - DD.MM HH:MM' and 'DD.MM HH:MM'.
    Times are in Europe/London (handles BST/GMT automatically via ZoneInfo).
    """
    m = _PLIST_TIME_RE.search(time_str)
    if not m:
        raise ValueError(f"Cannot parse plist time: {time_str!r}")
    day = int(m.group(1))
    month = int(m.group(2))
    hour = int(m.group(3))
    minute = int(m.group(4))
    year = ref_year
    if month > ref_month:
        year -= 1
    dt_local = datetime(year, month, day, hour, minute, tzinfo=_LONDON)
    return dt_local.astimezone(UTC)


def _try_plist_items(
    soup: BeautifulSoup, ref_date: date | None = None
) -> list[UKRadioLiveParseResult] | None:
    """Strategy 2: plist-item CSS selectors (confirmed on real ukradiolive.com HTML)."""
    items = soup.select("div[class*='plist-item']")
    if not items:
        return None
    if not any(isinstance(item, Tag) and item.select_one("span.txtsong") for item in items):
        return None

    ref = ref_date or datetime.now(tz=UTC).date()
    results: list[UKRadioLiveParseResult] = []

    for item in items:
        if not isinstance(item, Tag):
            continue
        time_el = item.select_one("span.txt2.mcolumn")
        song_span = item.select_one("span.txtsong.mcolumn")
        if not time_el or not song_span:
            continue

        artist_el = song_span.select_one("span[itemprop='byArtist']")
        title_el = song_span.select_one("span[itemprop='name']")
        if not artist_el or not title_el:
            continue

        artist = artist_el.get_text(strip=True)
        title = title_el.get_text(strip=True)
        if not artist or not title:
            continue

        time_text = time_el.get_text(strip=True)
        try:
            played_at = _parse_plist_time(time_text, ref.year, ref.month)
        except ValueError as exc:
            logger.debug("ukradiolive plist time parse error: %s", exc)
            continue

        data_id = item.get("data-id")
        results.append(UKRadioLiveParseResult(
            title=title,
            artist=artist,
            played_at=played_at,
            source_event_id=str(data_id) if data_id else None,
        ))

    return results if results else None


def parse_ukradiolive_playlist(
    html: bytes | str,
    http_status: int | None = None,
    ref_date: date | None = None,
) -> list[UKRadioLiveParseResult]:
    """Parse ukradiolive.com playlist page into track records.

    Tries __NEXT_DATA__ JSON first, then plist-item CSS selectors.
    Returns an empty list when no known structure is found.
    """
    if http_status is not None and http_status >= 400:
        logger.warning("ukradiolive: HTTP %s — returning empty", http_status)
        return []

    soup = BeautifulSoup(html, "lxml")

    results = _try_next_data(soup)
    if results is not None:
        logger.info("ukradiolive: __NEXT_DATA__ strategy returned %d tracks", len(results))
        return results

    results = _try_plist_items(soup, ref_date)
    if results is not None:
        logger.info("ukradiolive: plist-item strategy returned %d tracks", len(results))
        return results

    logger.info("ukradiolive: no known structure found in HTML")
    return []
