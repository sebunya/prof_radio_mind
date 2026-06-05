"""Radiowave diary HTML parser.

Two-strategy parser:
  Strategy 1 (CSS): Selects tr.diary-row with td.diary-time/artist/title/label.
                    Handles synthetic fixtures and any site that uses these classes.
  Strategy 2 (Table): Discovers the diary table by matching column header keywords
                    (time, artist, title). Handles ASP.NET GridView, Bootstrap
                    tables, and any rendering without custom CSS classes.

Both strategies use the same timezone-aware HH:MM → UTC conversion.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, Tag

from app.domain.entities.play_event import PlayEvent

_DRIFT_FRACTION = 0.5
_MIN_EXPECTED_ROWS = 4

_LABEL_TAG_RE = re.compile(r"\s*\[.*?\]\s*$")
_SYDNEY = ZoneInfo("Australia/Sydney")
_LOS_ANGELES = ZoneInfo("America/Los_Angeles")

# Header keywords for Strategy 2 column detection (lowercase, checked with `in`)
_TIME_KEYWORDS = ("time", "hour", "play time", "airtime")
_ARTIST_KEYWORDS = ("artist", "performer", "act")
_TITLE_KEYWORDS = ("title", "song", "track")
_LABEL_KEYWORDS = ("label", "record")


@dataclass
class RadiowaveParseResult:
    play_events: list[PlayEvent]
    drift_detected: bool = False
    drift_note: str = ""
    parse_errors: list[str] = field(default_factory=list)


def _strip_label_from_artist(artist_raw: str) -> str:
    """Remove trailing label annotation from artist field.

    'Tame Impala [Island Records]' → 'Tame Impala'
    """
    return _LABEL_TAG_RE.sub("", artist_raw).strip()


def _parse_time_cell(
    time_str: str, diary_date: date, station_timezone: ZoneInfo = _SYDNEY
) -> datetime:
    """Convert a time string + diary date to a UTC-aware datetime.

    Accepts: 'HH:MM', 'H:MM', 'HH:MM:SS', 'H:MM AM/PM'.
    """
    time_str = time_str.strip()

    # Try 12-hour AM/PM format first
    for fmt in ("%I:%M %p", "%I:%M:%S %p"):
        try:
            t = datetime.strptime(time_str.upper(), fmt)
            dt_local = datetime(
                diary_date.year, diary_date.month, diary_date.day,
                t.hour, t.minute, 0, tzinfo=station_timezone,
            )
            return dt_local.astimezone(UTC)
        except ValueError:
            pass

    # 24-hour format — take first two colon-separated parts
    parts = time_str.split(":")
    h = int(parts[0])
    m = int(parts[1].split()[0])  # handles "06:02:00" or "06:02 something"
    dt_local = datetime(
        diary_date.year, diary_date.month, diary_date.day, h, m, 0,
        tzinfo=station_timezone,
    )
    return dt_local.astimezone(UTC)


def _drift_check(
    rows_found: int,
    events_parsed: int,
    expected_min_rows: int,
) -> tuple[bool, str]:
    threshold = max(expected_min_rows * _DRIFT_FRACTION, 1)
    if rows_found and events_parsed < threshold:
        return True, (
            f"Drift detected: parsed {events_parsed} events from {rows_found} rows "
            f"(expected >= {threshold:.0f})"
        )
    return False, ""


# ---------------------------------------------------------------------------
# Strategy 1: CSS class selectors (diary-row / diary-time / diary-artist etc.)
# ---------------------------------------------------------------------------

def _parse_css_rows(
    rows: list[Tag],
    source_id: uuid.UUID,
    station_id: uuid.UUID,
    collector_run_id: uuid.UUID,
    diary_date: date,
    station_timezone: ZoneInfo,
    expected_min_rows: int,
) -> RadiowaveParseResult:
    play_events: list[PlayEvent] = []
    parse_errors: list[str] = []

    for row in rows:
        source_event_id = row.get("data-event-id")
        if isinstance(source_event_id, list):
            source_event_id = source_event_id[0] if source_event_id else None

        time_cell = row.select_one("td.diary-time")
        artist_cell = row.select_one("td.diary-artist")
        title_cell = row.select_one("td.diary-title")
        label_cell = row.select_one("td.diary-label")

        if not time_cell or not artist_cell or not title_cell:
            parse_errors.append(f"Row missing required cells: {source_event_id or 'unknown'}")
            continue

        for span in artist_cell.select("span.label-tag"):
            span.decompose()

        raw_artist = _strip_label_from_artist(artist_cell.get_text(strip=True))
        raw_title = title_cell.get_text(strip=True)
        raw_label = label_cell.get_text(strip=True) if label_cell else None

        try:
            played_at = _parse_time_cell(
                time_cell.get_text(strip=True), diary_date, station_timezone
            )
        except (ValueError, AttributeError) as exc:
            parse_errors.append(f"Time parse error for {source_event_id}: {exc}")
            continue

        if not raw_artist or not raw_title:
            parse_errors.append(f"Empty artist or title for {source_event_id}")
            continue

        play_events.append(
            PlayEvent.create(
                station_id=station_id,
                source_id=source_id,
                collector_run_id=collector_run_id,
                played_at=played_at,
                raw_artist=raw_artist,
                raw_title=raw_title,
                source_event_id=str(source_event_id) if source_event_id else None,
                raw_label=raw_label,
            )
        )

    drift_detected, drift_note = _drift_check(len(rows), len(play_events), expected_min_rows)
    return RadiowaveParseResult(
        play_events=play_events,
        drift_detected=drift_detected,
        drift_note=drift_note,
        parse_errors=parse_errors,
    )


# ---------------------------------------------------------------------------
# Strategy 2: Header-based table detection (ASP.NET GridView, Bootstrap, etc.)
# ---------------------------------------------------------------------------

def _parse_table_by_headers(
    soup: BeautifulSoup,
    source_id: uuid.UUID,
    station_id: uuid.UUID,
    collector_run_id: uuid.UUID,
    diary_date: date,
    expected_min_rows: int,
    station_timezone: ZoneInfo,
) -> RadiowaveParseResult | None:
    """Scan all tables and extract from the first one whose headers match."""
    for table in soup.find_all("table"):
        if not isinstance(table, Tag):
            continue

        all_rows = [r for r in table.find_all("tr") if isinstance(r, Tag)]
        if not all_rows:
            continue

        header_row = all_rows[0]
        header_cells = header_row.find_all(["th", "td"])
        headers = [c.get_text(strip=True).lower() for c in header_cells]
        if not headers:
            continue

        time_col = artist_col = title_col = label_col = None
        for i, h in enumerate(headers):
            if time_col is None and any(kw in h for kw in _TIME_KEYWORDS):
                time_col = i
            elif artist_col is None and any(kw in h for kw in _ARTIST_KEYWORDS):
                artist_col = i
            elif title_col is None and any(kw in h for kw in _TITLE_KEYWORDS):
                title_col = i
            elif label_col is None and any(kw in h for kw in _LABEL_KEYWORDS):
                label_col = i

        if time_col is None or artist_col is None or title_col is None:
            continue

        required_cols = max(time_col, artist_col, title_col) + 1
        play_events: list[PlayEvent] = []
        parse_errors: list[str] = []
        data_rows = all_rows[1:]

        for row in data_rows:
            cells = row.find_all("td")
            if len(cells) < required_cols:
                continue

            time_text = cells[time_col].get_text(strip=True)
            artist_text = _strip_label_from_artist(cells[artist_col].get_text(strip=True))
            title_text = cells[title_col].get_text(strip=True)
            label_text = (
                cells[label_col].get_text(strip=True)
                if label_col is not None and len(cells) > label_col
                else None
            )

            if not time_text or not artist_text or not title_text:
                continue

            try:
                played_at = _parse_time_cell(time_text, diary_date, station_timezone)
            except (ValueError, AttributeError) as exc:
                parse_errors.append(f"Time parse error: {exc}")
                continue

            play_events.append(
                PlayEvent.create(
                    station_id=station_id,
                    source_id=source_id,
                    collector_run_id=collector_run_id,
                    played_at=played_at,
                    raw_artist=artist_text,
                    raw_title=title_text,
                    source_event_id=None,
                    raw_label=label_text,
                )
            )

        drift_detected, drift_note = _drift_check(
            len(data_rows), len(play_events), expected_min_rows
        )
        return RadiowaveParseResult(
            play_events=play_events,
            drift_detected=drift_detected,
            drift_note=drift_note,
            parse_errors=parse_errors,
        )

    return None  # No matching table found


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_radiowave_diary(
    html: bytes | str,
    source_id: uuid.UUID,
    station_id: uuid.UUID,
    collector_run_id: uuid.UUID,
    diary_date: date | None = None,
    expected_min_rows: int = _MIN_EXPECTED_ROWS,
    station_timezone: ZoneInfo = _SYDNEY,
) -> RadiowaveParseResult:
    """Parse Radiowave diary HTML into PlayEvents.

    Tries two strategies in order:
      1. CSS class selectors (tr.diary-row etc.)
      2. Column-header table detection (handles ASP.NET GridView and any
         site without custom CSS classes)

    Args:
        html: Raw HTML bytes or string from the diary page.
        source_id: UUID of the source record.
        station_id: UUID of the station.
        collector_run_id: UUID of the current collector run.
        diary_date: Date to assign to parsed times (defaults to today UTC).
        expected_min_rows: Minimum rows expected; fewer triggers drift detection.
        station_timezone: Local timezone for HH:MM → UTC conversion.
            Defaults to Australia/Sydney (Nova 96.9).
            Pass ZoneInfo("America/Los_Angeles") for KIIS-FM 102.7.
    """
    if diary_date is None:
        diary_date = datetime.now(tz=UTC).date()

    soup = BeautifulSoup(html, "lxml")

    # Strategy 1: CSS class selectors
    css_rows = soup.select("tr.diary-row")
    if css_rows:
        return _parse_css_rows(
            [r for r in css_rows if isinstance(r, Tag)],
            source_id, station_id, collector_run_id,
            diary_date, station_timezone, expected_min_rows,
        )

    # Strategy 2: header-based table detection
    result = _parse_table_by_headers(
        soup, source_id, station_id, collector_run_id,
        diary_date, expected_min_rows, station_timezone,
    )
    if result is not None:
        return result

    return RadiowaveParseResult(
        play_events=[],
        parse_errors=["No diary table found — neither tr.diary-row CSS nor header-matched table"],
    )
