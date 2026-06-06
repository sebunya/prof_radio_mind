"""iHeart web recently-played page parser.

Strategy 1: __NEXT_DATA__ JSON embedded in <script id="__NEXT_DATA__"> (Next.js SSR).
            Recursively searches for recentlyPlayedSongs / songs / tracks keys.
Strategy 2: figcaption CSS selectors — confirmed on real kiisfm.iheart.com HTML (2026-06-06).
            Each song is a <figcaption> with:
              a.track-title span  → title
              a.track-artist span → artist
              time.track-time[datetime]       → ISO 8601 (e.g. "2026-06-05T11:50:33")
              time.track-time[data-timezone]  → IANA tz (e.g. "America/Los_Angeles")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bs4 import BeautifulSoup, Tag

from app.infrastructure.parsers._json_utils import find_track_list

logger = logging.getLogger(__name__)


@dataclass
class IHeartWebParseResult:
    title: str
    artist: str
    played_at: datetime


def _extract_artist(item: dict) -> str:
    raw = item.get("artist") or item.get("artistName") or item.get("artistData") or ""
    if isinstance(raw, dict):
        raw = raw.get("name") or raw.get("artistName") or ""
    return str(raw).strip()


def _extract_played_at_from_dict(item: dict) -> datetime:
    ts = (
        item.get("startTime")
        or item.get("playedAt")
        or item.get("timestamp")
        or item.get("airtime")
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


def _try_next_data(soup: BeautifulSoup) -> list[IHeartWebParseResult] | None:
    script = soup.find("script", id="__NEXT_DATA__")
    if not isinstance(script, Tag):
        return None
    try:
        data = json.loads(script.string or "")
    except (json.JSONDecodeError, TypeError):
        logger.debug("iheart_web: __NEXT_DATA__ present but JSON is invalid")
        return None

    raw_tracks = find_track_list(data)
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
            played_at=_extract_played_at_from_dict(item),
        ))

    return results if results else None


def _parse_figcaption_time(time_el: Tag | None) -> datetime:
    """Parse <time class="track-time" datetime="ISO8601" data-timezone="..."> to UTC."""
    if not isinstance(time_el, Tag):
        return datetime.now(tz=UTC)
    dt_str = str(time_el.get("datetime") or "")
    tz_name = str(time_el.get("data-timezone") or "UTC")
    if not dt_str:
        return datetime.now(tz=UTC)
    try:
        dt_naive = datetime.fromisoformat(dt_str)
        tz = ZoneInfo(tz_name)
        return datetime(
            dt_naive.year, dt_naive.month, dt_naive.day,
            dt_naive.hour, dt_naive.minute, dt_naive.second,
            tzinfo=tz,
        ).astimezone(UTC)
    except (ValueError, ZoneInfoNotFoundError):
        logger.debug("iheart_web: cannot parse datetime %r tz %r", dt_str, tz_name)
        return datetime.now(tz=UTC)


def _try_figcaption(soup: BeautifulSoup) -> list[IHeartWebParseResult] | None:
    """Strategy 2: figcaption CSS selectors (confirmed on real iHeart HTML, 2026-06-06)."""
    figs = soup.select("figcaption")
    if not figs:
        return None
    if not any(isinstance(fig, Tag) and fig.select_one("a.track-title") for fig in figs):
        return None

    results: list[IHeartWebParseResult] = []
    for fig in figs:
        if not isinstance(fig, Tag):
            continue
        title_el = fig.select_one("a.track-title span")
        artist_el = fig.select_one("a.track-artist span")
        if not title_el or not artist_el:
            continue

        title = title_el.get_text(strip=True)
        artist = artist_el.get_text(strip=True)
        if not title or not artist:
            continue

        time_el = fig.select_one("time.track-time")
        played_at = _parse_figcaption_time(
            time_el if isinstance(time_el, Tag) else None
        )
        results.append(IHeartWebParseResult(title=title, artist=artist, played_at=played_at))

    return results if results else None


def parse_iheart_web_recently_played(
    html: bytes | str,
    http_status: int | None = None,
) -> list[IHeartWebParseResult]:
    """Parse iHeart recently-played web page into track records.

    Tries __NEXT_DATA__ JSON first, then figcaption CSS selectors.
    Returns an empty list when no known structure is found.
    """
    if http_status is not None and http_status >= 400:
        logger.warning("iheart_web: HTTP %s — returning empty", http_status)
        return []

    soup = BeautifulSoup(html, "lxml")

    results = _try_next_data(soup)
    if results is not None:
        logger.info("iheart_web: __NEXT_DATA__ strategy returned %d tracks", len(results))
        return results

    results = _try_figcaption(soup)
    if results is not None:
        logger.info("iheart_web: figcaption strategy returned %d tracks", len(results))
        return results

    logger.info("iheart_web: no known structure found in HTML")
    return []
