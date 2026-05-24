"""Report generation API — build and download daily airplay reports."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.auth import require_api_key

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportRequest(BaseModel):
    report_date: date
    top_n: int = 40


class ReportSummary(BaseModel):
    station_id: str
    report_date: str
    total_plays: int
    entry_count: int
    confidence_level: str
    confidence_score: float
    version: int
    generated_at: str


def _build_coverage(events: list) -> Any:
    from app.application.reports.confidence import SourceCoverage

    cov = SourceCoverage(total_plays=len(events))
    for ev in events:
        attr = getattr(ev, "attribution", None) or ""
        if attr == "radiowave":
            cov.radiowave_plays += 1
        elif attr == "iheart":
            cov.iheart_plays += 1
        elif attr == "manual_csv":
            cov.manual_csv_plays += 1
        else:
            # Automated source (unknown attribution) — treated as radiowave for confidence
            cov.radiowave_plays += 1
    return cov


async def _fetch_events(
    station_id: uuid.UUID, report_date: date
) -> list:
    from app.infrastructure.database.repositories.play_event_repo import SQLPlayEventRepository
    from app.infrastructure.database.session import _get_factory as _factory

    from_dt = datetime(report_date.year, report_date.month, report_date.day, tzinfo=UTC)
    to_dt = from_dt + timedelta(days=1)
    async with _factory()() as session:
        repo = SQLPlayEventRepository(session)
        return await repo.list_for_station(station_id, from_dt, to_dt)


@router.post(
    "/{station_id}/generate",
    response_model=ReportSummary,
    dependencies=[Depends(require_api_key)],
)
async def generate_report(
    station_id: uuid.UUID, body: ReportRequest
) -> ReportSummary:
    """Generate a daily airplay ranking for a station and persist a DailyReport record."""
    try:
        events = await _fetch_events(station_id, body.report_date)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No play events for station {station_id} on {body.report_date}",
        )

    from app.application.ranking.engine import build_snapshot
    from app.application.reports.confidence import compute_confidence
    from app.infrastructure.database.repositories.daily_report_repo import (
        SQLDailyReportRepository,
    )
    from app.infrastructure.database.session import _get_factory as _factory

    plays = [(e.raw_artist, e.raw_title) for e in events]
    snapshot = build_snapshot(plays, str(station_id), str(body.report_date), top_n=body.top_n)

    coverage = _build_coverage(events)
    confidence_score, confidence_level = compute_confidence(coverage)

    snapshot_rows = [
        {
            "position": e.position,
            "artist": e.song_key.artist,
            "title": e.song_key.title,
            "play_count": e.play_count,
        }
        for e in snapshot.entries
    ]

    try:
        async with _factory()() as session:
            report_repo = SQLDailyReportRepository(session)
            _report, version = await report_repo.upsert(
                station_id=station_id,
                report_date=body.report_date,
                confidence_level=confidence_level.value,
                confidence_score=float(confidence_score),
                total_plays=snapshot.total_plays,
                unique_songs=len(snapshot.entries),
                source_coverage=coverage.to_dict(),
                snapshot_rows=snapshot_rows,
            )
            await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    return ReportSummary(
        station_id=str(station_id),
        report_date=str(body.report_date),
        total_plays=snapshot.total_plays,
        entry_count=len(snapshot.entries),
        confidence_level=confidence_level.value,
        confidence_score=float(confidence_score),
        version=version,
        generated_at=datetime.now(UTC).isoformat(),
    )


@router.get(
    "/master/download",
    dependencies=[Depends(require_api_key)],
)
async def download_master_report(
    report_date: date,
    top_n: int = 40,
) -> StreamingResponse:
    """Download a cross-station master report as a single CSV file."""
    from app.application.ranking.engine import build_snapshot
    from app.application.reports.confidence import compute_confidence
    from app.application.reports.csv_exporter import (
        CSVExport,
        DailyReportRow,
        export_daily_report_csv,
    )
    from app.infrastructure.database.repositories.station_repo import SQLStationRepository
    from app.infrastructure.database.session import _get_factory as _factory

    try:
        async with _factory()() as session:
            station_repo = SQLStationRepository(session)
            stations = await station_repo.list_active()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    all_rows: list[DailyReportRow] = []
    for station in stations:
        try:
            events = await _fetch_events(station.id, report_date)
        except Exception:
            continue
        if not events:
            continue

        plays = [(e.raw_artist, e.raw_title) for e in events]
        snapshot = build_snapshot(
            plays, station.call_sign, str(report_date), top_n=top_n
        )
        coverage = _build_coverage(events)
        _score, level = compute_confidence(coverage)

        for entry in snapshot.entries:
            all_rows.append(
                DailyReportRow(
                    position=entry.position,
                    artist=entry.song_key.artist,
                    title=entry.song_key.title,
                    play_count=entry.play_count,
                    movement=entry.movement.value if entry.movement else "new_entry",
                    previous_position=entry.previous_position,
                    label=None,
                    confidence_level=level.value,
                )
            )

    if not all_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No play events found across any station on {report_date}",
        )

    export = CSVExport(
        station_call_sign="ALL_STATIONS",
        report_date=report_date,
        version=1,
        confidence_level="mixed",
        rows=all_rows,
    )
    csv_bytes = export_daily_report_csv(export)

    filename = f"rmias_master_{report_date}.csv"
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
        events = await _fetch_events(station_id, report_date)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No play events for station {station_id} on {report_date}",
        )

    from app.application.ranking.engine import build_snapshot
    from app.application.reports.confidence import compute_confidence
    from app.application.reports.csv_exporter import (
        CSVExport,
        DailyReportRow,
        export_daily_report_csv,
    )
    from app.infrastructure.database.repositories.daily_report_repo import (
        SQLDailyReportRepository,
    )
    from app.infrastructure.database.session import _get_factory as _factory

    plays = [(e.raw_artist, e.raw_title) for e in events]
    snapshot = build_snapshot(plays, str(station_id), str(report_date), top_n=top_n)

    coverage = _build_coverage(events)
    confidence_score, confidence_level = compute_confidence(coverage)

    snapshot_rows = [
        {
            "position": e.position,
            "artist": e.song_key.artist,
            "title": e.song_key.title,
            "play_count": e.play_count,
        }
        for e in snapshot.entries
    ]

    version = 1
    try:
        async with _factory()() as session:
            report_repo = SQLDailyReportRepository(session)
            _report, version = await report_repo.upsert(
                station_id=station_id,
                report_date=report_date,
                confidence_level=confidence_level.value,
                confidence_score=float(confidence_score),
                total_plays=snapshot.total_plays,
                unique_songs=len(snapshot.entries),
                source_coverage=coverage.to_dict(),
                snapshot_rows=snapshot_rows,
            )
            await session.commit()
    except Exception:
        pass

    rows = [
        DailyReportRow(
            position=entry.position,
            artist=entry.song_key.artist,
            title=entry.song_key.title,
            play_count=entry.play_count,
            movement=entry.movement.value if entry.movement else "new_entry",
            previous_position=entry.previous_position,
            label=None,
            confidence_level=confidence_level.value,
        )
        for entry in snapshot.entries
    ]

    export = CSVExport(
        station_call_sign=str(station_id),
        report_date=report_date,
        version=version,
        confidence_level=confidence_level.value,
        rows=rows,
    )
    csv_bytes = export_daily_report_csv(export)

    filename = f"rmias_{station_id}_{report_date}_v{version}.csv"
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
