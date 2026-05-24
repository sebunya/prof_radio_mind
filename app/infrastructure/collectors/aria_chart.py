"""ARIA Singles chart scraper.

Scrapes the weekly ARIA Singles chart from the ARIA website.
The HTML structure is checked against a known selector pattern.
If the structure changes, a parse error is raised and a review item created.

VAL-ARIA-001: ARIA chart URL and HTML selector — must be confirmed before enabling.
"""

from __future__ import annotations

import logging
import re
from datetime import date

from app.domain.entities.chart_entry import ChartEntry

logger = logging.getLogger(__name__)

_CHART_URL = "https://www.aria.com.au/charts/singles-chart/"
_REQUEST_TIMEOUT = 30.0


async def fetch_aria_chart(
    chart_date: date | None = None,
) -> list[ChartEntry]:
    """Fetch and parse the ARIA Singles chart for a given week-ending date.

    Args:
        chart_date: Week-ending date. If None, fetches the current week.

    Returns:
        List of ChartEntry objects sorted by position.

    Raises:
        ValueError: If the page cannot be parsed (schema changed).
    """
    from app.infrastructure.http.client import build_client

    url = _CHART_URL
    if chart_date:
        url = f"{_CHART_URL}{chart_date.isoformat()}/"

    async with await build_client(timeout=_REQUEST_TIMEOUT) as client:
        response = await client.get(url)

    if response.status_code != 200:
        raise ValueError(
            f"ARIA chart returned HTTP {response.status_code} for {url}"
        )

    return _parse_aria_html(response.text, chart_date or date.today())


def _parse_aria_html(html: str, chart_date: date) -> list[ChartEntry]:
    """Parse ARIA chart HTML into ChartEntry objects.

    The ARIA website uses a standard chart-list structure. This parser
    targets the most common layout — raise ValueError if selectors miss.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise ImportError("beautifulsoup4 is required for ARIA chart parsing") from exc

    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select(".chart-row, .chart-item, tr.chart-entry")

    if not rows:
        # Try alternative selectors
        rows = soup.select("li[class*='chart']")

    if not rows:
        raise ValueError(
            "ARIA chart HTML did not match any known selector — schema may have changed."
        )

    entries: list[ChartEntry] = []
    for row in rows:
        try:
            pos_el = row.select_one(".chart-row__position, .position, .chart-position")
            artist_el = row.select_one(".chart-row__artist, .artist, [class*='artist']")
            title_el = row.select_one(".chart-row__title, .title, [class*='title']")

            if not (pos_el and artist_el and title_el):
                continue

            pos_text = re.sub(r"\D", "", pos_el.get_text(strip=True))
            if not pos_text:
                continue
            position = int(pos_text)

            entry = ChartEntry.create(
                chart_name="ARIA Singles",
                chart_date=chart_date,
                position=position,
                artist=artist_el.get_text(strip=True),
                title=title_el.get_text(strip=True),
            )
            entries.append(entry)
        except (ValueError, AttributeError):
            continue

    if not entries:
        raise ValueError("ARIA chart parsed zero entries — likely a selector mismatch.")

    return sorted(entries, key=lambda e: e.position)
