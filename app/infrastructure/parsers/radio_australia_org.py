"""radio-australia.org weekly chart parser.

Parses https://www.radio-australia.org/{station-slug} pages.

The live recently-played section (latest-song / previous-songs) is CSR-loaded
and unavailable in static HTML. This parser extracts the *weekly top songs chart*
which IS rendered server-side as a ranked list.

Structure confirmed on real HTML (2026-06-06):
  div.radio-songs__list[data-period="7"] → weekly chart (10 items)
    li.radio-songs__item
      span.radio-songs__rank          → chart position (1-10)
      span.radio-songs__title-text    → song title
      span.radio-songs__artist        → artist name

NOTE: played_at is synthetic (collection timestamp). These are chart positions
reflecting plays over the preceding 7 days, not individual timed play events.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


@dataclass
class RadioAustraliaChartResult:
    title: str
    artist: str
    rank: int
    collected_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


def parse_radio_australia_chart(
    html: bytes | str,
    http_status: int | None = None,
    collected_at: datetime | None = None,
) -> list[RadioAustraliaChartResult]:
    """Parse radio-australia.org weekly chart into track records.

    The returned collected_at is synthetic (time of collection), not an
    actual broadcast time. Callers should record this distinction.

    Returns an empty list on HTTP error or if no chart structure is found.
    """
    if http_status is not None and http_status >= 400:
        logger.warning("radio_australia_org: HTTP %s — returning empty", http_status)
        return []

    _now = collected_at or datetime.now(tz=UTC)
    soup = BeautifulSoup(html, "lxml")

    weekly = soup.select_one("div.radio-songs__list[data-period='7']")
    if not isinstance(weekly, Tag):
        logger.info("radio_australia_org: no weekly chart found")
        return []

    items = weekly.select("li.radio-songs__item")
    if not items:
        logger.info("radio_australia_org: weekly chart empty")
        return []

    results: list[RadioAustraliaChartResult] = []
    for item in items:
        if not isinstance(item, Tag):
            continue
        rank_el = item.select_one("span.radio-songs__rank")
        title_el = item.select_one("span.radio-songs__title-text")
        artist_el = item.select_one("span.radio-songs__artist")

        if not title_el or not artist_el:
            continue

        title = title_el.get_text(strip=True)
        artist = artist_el.get_text(strip=True)
        if not title or not artist:
            continue

        rank_text = rank_el.get_text(strip=True) if rank_el else "0"
        try:
            rank = int(rank_text)
        except ValueError:
            rank = 0

        results.append(RadioAustraliaChartResult(
            title=title,
            artist=artist,
            rank=rank,
            collected_at=_now,
        ))

    logger.info("radio_australia_org: extracted %d chart items", len(results))
    return results
