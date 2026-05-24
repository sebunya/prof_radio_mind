"""Report correction and versioning.

When a daily report is corrected, a new ReportVersion is created.
The original is never deleted. Exports are re-generated with an
incremented export_version.

No database calls in this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from app.application.reports.csv_exporter import DailyReportRow


@dataclass
class ReportCorrectionRequest:
    daily_report_id: str
    correction_note: str
    corrected_rows: list[DailyReportRow]
    corrected_by: str = "operator"


@dataclass
class CorrectedReport:
    daily_report_id: str
    version_number: int
    correction_note: str
    corrected_by: str
    corrected_at: datetime
    snapshot_json: str


def apply_correction(
    request: ReportCorrectionRequest,
    current_version: int,
) -> CorrectedReport:
    """Create a new version record for a corrected report.

    Returns a CorrectedReport that can be persisted to report_versions.
    Does not touch the original DailyReport row — is_corrected must be
    set to True and correction_note updated by the caller.
    """
    snapshot = {
        "rows": [
            {
                "position": row.position,
                "artist": row.artist,
                "title": row.title,
                "play_count": row.play_count,
                "movement": row.movement,
                "label": row.label,
                "confidence_level": row.confidence_level,
            }
            for row in request.corrected_rows
        ]
    }

    return CorrectedReport(
        daily_report_id=request.daily_report_id,
        version_number=current_version + 1,
        correction_note=request.correction_note,
        corrected_by=request.corrected_by,
        corrected_at=datetime.now(tz=UTC),
        snapshot_json=json.dumps(snapshot, ensure_ascii=False),
    )
