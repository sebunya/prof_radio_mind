"""CSV exporter for daily station reports and master report.

Each export is versioned: if a report is corrected, a new version is
exported with an incremented version_number. The previous version is
never deleted — the full correction history is preserved.

No database calls in this module.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date

from app.application.ranking.engine import RankEntry


@dataclass
class DailyReportRow:
    position: int
    artist: str
    title: str
    play_count: int
    movement: str
    previous_position: int | None
    label: str | None
    confidence_level: str


@dataclass
class CSVExport:
    station_call_sign: str
    report_date: date
    version: int
    confidence_level: str
    rows: list[DailyReportRow] = field(default_factory=list)


def build_daily_report_rows(
    entries: list[RankEntry],
    confidence_level: str = "medium",
    label_map: dict[str, str] | None = None,
) -> list[DailyReportRow]:
    """Convert rank entries to report rows for CSV export."""
    label_map = label_map or {}
    rows = []
    for entry in entries:
        key = f"{entry.song_key.artist}|{entry.song_key.title}"
        label = label_map.get(key)
        rows.append(
            DailyReportRow(
                position=entry.position,
                artist=entry.song_key.artist,
                title=entry.song_key.title,
                play_count=entry.play_count,
                movement=entry.movement.value if entry.movement else "new_entry",
                previous_position=entry.previous_position,
                label=label,
                confidence_level=confidence_level,
            )
        )
    return rows


def export_daily_report_csv(export: CSVExport) -> bytes:
    """Serialise a CSVExport to CSV bytes.

    Column order is fixed — changes to this order require a version bump
    in the export schema.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")

    writer.writerow([
        "position",
        "artist",
        "title",
        "play_count",
        "movement",
        "previous_position",
        "label",
        "confidence_level",
        "station",
        "report_date",
        "export_version",
    ])

    for row in export.rows:
        writer.writerow([
            row.position,
            row.artist,
            row.title,
            row.play_count,
            row.movement,
            row.previous_position if row.previous_position is not None else "",
            row.label or "",
            row.confidence_level,
            export.station_call_sign,
            export.report_date.isoformat(),
            export.version,
        ])

    return buf.getvalue().encode("utf-8")
