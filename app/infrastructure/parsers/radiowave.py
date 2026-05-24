"""Radiowave diary HTML parser for Nova 96.9 (IDDS=11129).

Parses the diary HTML table into PlayEvent instances.

Key behaviours:
- Strips label annotation from artist field (text in [brackets] or <span class="label-tag">)
- source_event_id comes from data-event-id attribute on the row
- Missing detail link is handled gracefully (source_event_id derived from data-event-id)
- Drift detection: if fewer than DRIFT_THRESHOLD rows are returned from a non-empty page,
  a warning is attached to the result
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time

from bs4 import BeautifulSoup, Tag

from app.domain.entities.play_event import PlayEvent

# If parsed row count drops below this fraction of the expected row count, flag drift
_DRIFT_FRACTION = 0.5
_MIN_EXPECTED_ROWS = 4

_LABEL_TAG_RE = re.compile(r"\s*\[.*?\]\s*$")


@dataclass
class RadiowaveParseResult:
    play_events: list[PlayEvent]
    drift_detected: bool = False
    drift_note: str = ""
    parse_errors: list[str] = field(default_factory=list)


def _strip_label_from_artist(artist_raw: str) -> str:
    """Remove label annotation appended to artist field.

    Radiowave sometimes includes the label in the artist cell:
      'Tame Impala [Island Records]' → 'Tame Impala'
    """
    return _LABEL_TAG_RE.sub("", artist_raw).strip()


def _parse_time_cell(time_str: str, diary_date: date) -> datetime:
    """Convert 'HH:MM' string + diary date to a UTC-aware datetime.

    Radiowave times are Sydney local time. For MVP we store them as-is
    with UTC timezone marker; DST conversion is deferred to Pass 11.
    """
    h, m = (int(p) for p in time_str.strip().split(":"))
    naive = datetime.combine(diary_date, time(h, m))
    return naive.replace(tzinfo=UTC)


def parse_radiowave_diary(
    html: bytes | str,
    source_id: uuid.UUID,
    station_id: uuid.UUID,
    collector_run_id: uuid.UUID,
    diary_date: date | None = None,
    expected_min_rows: int = _MIN_EXPECTED_ROWS,
) -> RadiowaveParseResult:
    """Parse Radiowave diary HTML into PlayEvents.

    Args:
        html: Raw HTML bytes or string from the Radiowave diary page
        source_id: UUID of the Radiowave source record
        station_id: UUID of the station (Nova 96.9)
        collector_run_id: UUID of the current collector run
        diary_date: Date to assign to parsed times (defaults to today UTC)
        expected_min_rows: Minimum rows expected; fewer triggers drift detection
    """
    if diary_date is None:
        diary_date = datetime.now(tz=UTC).date()

    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("tr.diary-row")

    play_events: list[PlayEvent] = []
    parse_errors: list[str] = []

    for row in rows:
        if not isinstance(row, Tag):
            continue

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

        # Strip <span class="label-tag"> from artist cell before reading text
        for span in artist_cell.select("span.label-tag"):
            span.decompose()

        raw_artist = _strip_label_from_artist(artist_cell.get_text(strip=True))
        raw_title = title_cell.get_text(strip=True)
        raw_label = label_cell.get_text(strip=True) if label_cell else None

        try:
            played_at = _parse_time_cell(time_cell.get_text(strip=True), diary_date)
        except (ValueError, AttributeError) as exc:
            parse_errors.append(f"Could not parse time for {source_event_id}: {exc}")
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

    drift_detected = bool(rows) and len(play_events) < max(
        expected_min_rows * _DRIFT_FRACTION, 1
    )
    drift_note = (
        f"Drift detected: parsed {len(play_events)} events from {len(rows)} rows "
        f"(expected >= {expected_min_rows * _DRIFT_FRACTION:.0f})"
        if drift_detected
        else ""
    )

    return RadiowaveParseResult(
        play_events=play_events,
        drift_detected=drift_detected,
        drift_note=drift_note,
        parse_errors=parse_errors,
    )
