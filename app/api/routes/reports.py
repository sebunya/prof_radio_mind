"""Report generation API — build and download daily airplay reports."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.auth import require_api_key

router = APIRouter(prefix="/reports", tags=["reports"])

UTC = UTC


class ReportRequest(BaseModel):
    report_date: date
    top_n: int = 40


class ReportSummary(BaseModel):
    station_id: str
    report_date: str
    total_plays: int
    entry_count: int
    generated_at: str


@router.post(
    "/{station_id}/generate",
    response_model=ReportSummary,
    dependencies=[Depends(require_api_key)],
)
async def generate_report(station_id: uuid.UUID, body: ReportRequest) -> ReportSummary:
    """Generate a daily airplay ranking for a station.

    Reads play_events from the DB for the given date, builds a ranking snapshot,
    and returns a summary. Use GET /{station_id}/download to fetch the CSV.
    """
    try:
        from app.infrastructure.database.repositories.play_event_repo import (
            SQLPlayEventRepository,
        )
        from app.infrastructure.database.session import _get_factory as _factory

        report_dt = body.report_date
        from_dt = datetime(report_dt.year, report_dt.month, report_dt.day, tzinfo=UTC)
        to_dt = from_dt + timedelta(days=1)

        async with _factory()() as session:
            repo = SQLPlayEventRepository(session)
            events = await repo.list_for_station(station_id, from_dt, to_dt)

    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No play events found for station {station_id} on {body.report_date}",
        )

    from app.application.ranking.engine import build_snapshot

    plays = [(e.raw_artist, e.raw_title) for e in events]
    snapshot = build_snapshot(plays, str(station_id), str(body.report_date), top_n=body.top_n)

    return ReportSummary(
        station_id=str(station_id),
        report_date=str(body.report_date),
        total_plays=snapshot.total_plays,
        entry_count=len(snapshot.entries),
        generated_at=datetime.now(UTC).isoformat(),
    )


@router.get(
    "/{station_id}/download",
    dependencies=[Depends(require_api_key)],
)
async def download_report(
    station_id: uuid.UUID,
    report_date: date,
    top_n: int = 40,
) -> StreamingResponse:
    """Download a daily report as a CSV file."""
    try:
        from app.infrastructure.database.repositories.play_event_repo import (
            SQLPlayEventRepository,
        )
        from app.infrastructure.database.session import _get_factory as _factory

        from_dt = datetime(report_date.year, report_date.month, report_date.day, tzinfo=UTC)
        to_dt = from_dt + timedelta(days=1)

        async with _factory()() as session:
            repo = SQLPlayEventRepository(session)
            events = await repo.list_for_station(station_id, from_dt, to_dt)

    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No play events for station {station_id} on {report_date}",
        )

    from app.application.ranking.engine import build_snapshot
    from app.application.reports.csv_exporter import (
        CSVExport,
        DailyReportRow,
        export_daily_report_csv,
    )

    plays = [(e.raw_artist, e.raw_title) for e in events]
    snapshot = build_snapshot(plays, str(station_id), str(report_date), top_n=top_n)

    rows = [
        DailyReportRow(
            position=entry.position,
            artist=entry.song_key.artist,
            title=entry.song_key.title,
            play_count=entry.play_count,
            movement=entry.movement.value if entry.movement else "new_entry",
            previous_position=entry.previous_position,
            label=None,
            confidence_level="high",
        )
        for entry in snapshot.entries
    ]

    export = CSVExport(
        station_call_sign=str(station_id),
        report_date=report_date,
        version=1,
        confidence_level="high",
        rows=rows,
    )
    csv_bytes = export_daily_report_csv(export)

    filename = f"rmias_{station_id}_{report_date}.csv"
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
