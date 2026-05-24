"""Manual CSV import pipeline — full implementation.

Imports play events from a manually-provided CSV file.
Used as the primary source for Capital FM and as emergency fallback
for Nova and KIIS when automated collectors fail.

Import steps:
1. Schema validation — required columns present
2. Row-level validation — date format, required fields non-empty
3. Play event creation — each valid row becomes a PlayEvent
4. Invalid rows produce error records, not silent drops
5. Attribution: source = manual_csv, confidence penalty applied

No live network calls at import time.
"""

from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.application.imports.manual_csv import (
    REQUIRED_CSV_COLUMNS,
    ImportBatch,
    ImportStatus,
)
from app.domain.entities.play_event import PlayEvent

# Confidence penalty for manually imported events (applied in report scoring)
MANUAL_IMPORT_CONFIDENCE_PENALTY = 0.10

# Accepted datetime formats in the CSV
_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
)

# Assume Sydney local time when no timezone info is present in the CSV
_SYDNEY_TZ = ZoneInfo("Australia/Sydney")


@dataclass
class RowError:
    row_number: int
    raw_row: dict
    error: str


@dataclass
class CSVImportResult:
    batch: ImportBatch
    play_events: list[PlayEvent] = field(default_factory=list)
    row_errors: list[RowError] = field(default_factory=list)


def _parse_played_at(value: str) -> datetime:
    """Parse played_at string to a UTC-aware datetime.

    Tries multiple formats. If no timezone is present in the string,
    treats as Sydney local time and converts to UTC.
    """
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            naive = datetime.strptime(value, fmt)
            local = naive.replace(tzinfo=_SYDNEY_TZ)
            return local.astimezone(UTC)
        except ValueError:
            continue
    raise ValueError(
        f"Cannot parse date/time: {value!r}. "
        f"Expected formats: YYYY-MM-DD HH:MM or DD/MM/YYYY HH:MM"
    )


def validate_csv_schema(headers: list[str]) -> list[str]:
    """Check that all required columns are present. Returns list of missing columns."""
    header_set = {h.strip().lower() for h in headers}
    return [col for col in REQUIRED_CSV_COLUMNS if col not in header_set]


def import_csv(
    csv_bytes: bytes,
    station_id: uuid.UUID,
    source_id: uuid.UUID,
    collector_run_id: uuid.UUID,
    filename: str = "manual_import.csv",
) -> CSVImportResult:
    """Parse and validate a CSV file, returning a CSVImportResult.

    Invalid rows are recorded in row_errors — they do NOT stop the import.
    The batch status is COMPLETED if any rows imported, FAILED if all rows fail,
    PARTIAL if some rows imported and some failed.
    """
    batch = ImportBatch.create(station_id, filename)
    batch.status = ImportStatus.VALIDATING

    try:
        text = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = csv_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        batch.status = ImportStatus.FAILED
        batch.errors.append("CSV file has no header row")
        return CSVImportResult(batch=batch)

    headers = [str(f) for f in reader.fieldnames]
    missing = validate_csv_schema(headers)
    if missing:
        batch.status = ImportStatus.FAILED
        batch.errors.append(f"Missing required columns: {', '.join(missing)}")
        return CSVImportResult(batch=batch)

    batch.status = ImportStatus.IMPORTING
    play_events: list[PlayEvent] = []
    row_errors: list[RowError] = []

    for row_num, row in enumerate(reader, start=2):
        # Normalise keys to lowercase
        norm = {k.strip().lower(): (v or "").strip() for k, v in row.items()}

        artist = norm.get("artist", "")
        title = norm.get("title", "")
        played_at_str = norm.get("played_at", "")

        errors = []
        if not artist:
            errors.append("artist is empty")
        if not title:
            errors.append("title is empty")
        if not played_at_str:
            errors.append("played_at is empty")

        if errors:
            row_errors.append(
                RowError(row_number=row_num, raw_row=dict(norm), error="; ".join(errors))
            )
            continue

        try:
            played_at = _parse_played_at(played_at_str)
        except ValueError as exc:
            row_errors.append(RowError(row_number=row_num, raw_row=dict(norm), error=str(exc)))
            continue

        source_event_id = norm.get("source_event_id") or None
        raw_label = norm.get("label") or None

        play_events.append(
            PlayEvent.create(
                station_id=station_id,
                source_id=source_id,
                collector_run_id=collector_run_id,
                played_at=played_at,
                raw_artist=artist,
                raw_title=title,
                source_event_id=source_event_id,
                raw_label=raw_label,
            )
        )

    batch.total_rows = len(play_events) + len(row_errors)
    batch.imported_rows = len(play_events)
    batch.error_rows = len(row_errors)

    if len(play_events) == 0 and len(row_errors) > 0:
        batch.status = ImportStatus.FAILED
    elif len(row_errors) > 0:
        batch.status = ImportStatus.PARTIAL
    else:
        batch.status = ImportStatus.COMPLETED

    return CSVImportResult(batch=batch, play_events=play_events, row_errors=row_errors)
