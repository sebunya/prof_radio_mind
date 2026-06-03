"""Online Radio Box HTML parser.

Parses now-playing and historical track metadata from Online Radio Box station pages.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time

from bs4 import BeautifulSoup, Tag


@dataclass
class OnlineRadioBoxParseResult:
    artist: str
    title: str
    played_at: datetime
    source_event_id: str | None = None
    parse_errors: list[str] = field(default_factory=list)


def split_artist_title(text: str) -> tuple[str, str]:
    """Fallback utility to split a raw string into artist and title.

    Splits by standard separators: ' - ', ' — ', etc.
    """
    parts = re.split(r"\s+[-—]\s+", text, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return "", text.strip()


def parse_online_radio_box_now_playing(
    html: bytes | str,
    http_status: int | None = None,
) -> OnlineRadioBoxParseResult | None:
    """Parse Online Radio Box HTML to extract currently playing (Live) track metadata.

    Returns None if http_status is 204 (commercial break or talk).
    Raises ValueError if HTML structure does not contain a schedule table.
    """
    if http_status == 204:
        return None

    if not html:
        raise ValueError("Empty HTML content")

    soup = BeautifulSoup(html, "lxml")

    # Try finding the schedule table
    table = soup.select_one("table.tablelist-schedule")
    if not table or not isinstance(table, Tag):
        raise ValueError("Could not find table.tablelist-schedule in HTML")

    # Find the live row (either has tr.active, or the time cell contains "Live")
    live_row = None
    for row in table.find_all("tr"):
        if not isinstance(row, Tag):
            continue
        time_span = row.select_one("span.time--schedule")
        if time_span and time_span.get_text(strip=True).lower() == "live":
            live_row = row
            break

    if not live_row:
        # Fall back to checking tr.active
        live_row = table.select_one("tr.active")

    if not live_row or not isinstance(live_row, Tag):
        # No live track playing currently
        return None

    track_td = live_row.find("td", class_="track_history_item")
    if not track_td or not isinstance(track_td, Tag):
        return None

    a_tag = track_td.find("a")
    if a_tag and not isinstance(a_tag, Tag):
        a_tag = None

    raw_text = a_tag.get_text(strip=True) if a_tag else track_td.get_text(strip=True)

    # Extract source_event_id from anchor href if available
    source_event_id = None
    if isinstance(a_tag, Tag):
        href = a_tag.get("href")
        if isinstance(href, str):
            match = re.search(r"/track/([^/]+)", href)
            if match:
                source_event_id = match.group(1)

    # Extract artist and title
    b_tag = a_tag.find("b") if a_tag else track_td.find("b")
    if b_tag and not isinstance(b_tag, Tag):
        b_tag = None

    if b_tag:
        artist = b_tag.get_text(strip=True)
        # Use a copy to decompose b tag without affecting the original tree if reused
        elem_copy = copy.copy(a_tag if a_tag else track_td)
        if isinstance(elem_copy, Tag):
            b_copy = elem_copy.find("b")
            if b_copy and isinstance(b_copy, Tag):
                b_copy.decompose()
            title = elem_copy.get_text(strip=True)
        else:
            title = raw_text
    else:
        artist, title = split_artist_title(raw_text)

    if not artist or not title:
        raise ValueError(
            "Online Radio Box live track missing artist or title: "
            f"artist={artist!r} title={title!r}"
        )

    # Live tracks get current UTC time
    played_at = datetime.now(tz=UTC)

    return OnlineRadioBoxParseResult(
        artist=artist,
        title=title,
        played_at=played_at,
        source_event_id=source_event_id,
    )


def parse_online_radio_box_history(
    html: bytes | str,
    base_date: date | None = None,
) -> list[OnlineRadioBoxParseResult]:
    """Parse all tracks from the Online Radio Box schedule/history table.

    Normalizes timestamps to UTC using base_date (defaults to today's UTC date).
    """
    if not html:
        return []

    if base_date is None:
        base_date = datetime.now(tz=UTC).date()

    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.tablelist-schedule")
    if not table or not isinstance(table, Tag):
        return []

    results: list[OnlineRadioBoxParseResult] = []

    for row in table.find_all("tr"):
        if not isinstance(row, Tag):
            continue

        time_span = row.select_one("span.time--schedule")
        if not time_span:
            continue

        time_text = time_span.get_text(strip=True)
        is_live = time_text.lower() == "live"

        track_td = row.find("td", class_="track_history_item")
        if not track_td or not isinstance(track_td, Tag):
            continue

        a_tag = track_td.find("a")
        if a_tag and not isinstance(a_tag, Tag):
            a_tag = None

        raw_text = a_tag.get_text(strip=True) if a_tag else track_td.get_text(strip=True)

        source_event_id = None
        if isinstance(a_tag, Tag):
            href = a_tag.get("href")
            if isinstance(href, str):
                match = re.search(r"/track/([^/]+)", href)
                if match:
                    source_event_id = match.group(1)

        b_tag = a_tag.find("b") if a_tag else track_td.find("b")
        if b_tag and not isinstance(b_tag, Tag):
            b_tag = None

        if b_tag:
            artist = b_tag.get_text(strip=True)
            elem_copy = copy.copy(a_tag if a_tag else track_td)
            if isinstance(elem_copy, Tag):
                b_copy = elem_copy.find("b")
                if b_copy and isinstance(b_copy, Tag):
                    b_copy.decompose()
                title = elem_copy.get_text(strip=True)
            else:
                title = raw_text
        else:
            artist, title = split_artist_title(raw_text)

        if not artist or not title:
            continue

        if is_live:
            played_at = datetime.now(tz=UTC)
        else:
            # Parse HH:MM format
            try:
                h, m = (int(p) for p in time_text.split(":"))
                played_at = datetime.combine(base_date, time(h, m)).replace(tzinfo=UTC)
            except (ValueError, AttributeError):
                # If time is not parseable, fallback to current time
                played_at = datetime.now(tz=UTC)

        results.append(
            OnlineRadioBoxParseResult(
                artist=artist,
                title=title,
                played_at=played_at,
                source_event_id=source_event_id,
            )
        )

    return results
