"""Proof-of-Play API — generate and download airplay certificates."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.infrastructure.database.session import get_db

router = APIRouter(prefix="/proof-of-play", tags=["proof-of-play"])


class CertificateSummary(BaseModel):
    station_id: str
    report_date: str
    certificate_count: int
    certified_by: str
    generated_at: str


@router.get(
    "/{station_id}/certificates",
    response_model=CertificateSummary,
    dependencies=[Depends(require_api_key)],
)
async def get_certificate_summary(
    station_id: uuid.UUID,
    report_date: date,
    session: AsyncSession = Depends(get_db),
) -> CertificateSummary:
    """Return a summary of how many certificates would be generated for a station/date."""
    from app.infrastructure.database.repositories.play_event_repo import SQLPlayEventRepository
    from app.infrastructure.database.repositories.station_repo import SQLStationRepository

    station_repo = SQLStationRepository(session)
    station = await station_repo.get_by_id(station_id)
    if station is None:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")

    from_dt = datetime(report_date.year, report_date.month, report_date.day, tzinfo=UTC)
    to_dt = from_dt + timedelta(days=1)

    play_repo = SQLPlayEventRepository(session)
    events = await play_repo.list_for_station(station_id, from_dt, to_dt)

    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No play events for station {station_id} on {report_date}",
        )

    from collections import Counter

    counts: Counter[tuple[str, str]] = Counter()
    for ev in events:
        counts[(ev.raw_artist, ev.raw_title)] += 1

    return CertificateSummary(
        station_id=str(station_id),
        report_date=str(report_date),
        certificate_count=len(counts),
        certified_by="RMIAS",
        generated_at=datetime.now(UTC).isoformat(),
    )


@router.get(
    "/{station_id}/certificates/download",
    dependencies=[Depends(require_api_key)],
)
async def download_certificates(
    station_id: uuid.UUID,
    report_date: date,
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Download APRA/AMCOS-compatible airplay certificates as CSV."""
    from collections import Counter

    from app.application.proof_of_play.certificate_service import (
        export_certificates_csv,
        generate_certificates,
    )
    from app.infrastructure.database.repositories.play_event_repo import SQLPlayEventRepository
    from app.infrastructure.database.repositories.station_repo import SQLStationRepository

    station_repo = SQLStationRepository(session)
    station = await station_repo.get_by_id(station_id)
    if station is None:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")

    from_dt = datetime(report_date.year, report_date.month, report_date.day, tzinfo=UTC)
    to_dt = from_dt + timedelta(days=1)

    play_repo = SQLPlayEventRepository(session)
    events = await play_repo.list_for_station(station_id, from_dt, to_dt)

    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No play events for station {station_id} on {report_date}",
        )

    counts: Counter[tuple[str, str]] = Counter()
    for ev in events:
        counts[(ev.raw_artist, ev.raw_title)] += 1

    ranked = [(artist, title, count) for (artist, title), count in counts.most_common()]
    certs = generate_certificates(
        station_id=station_id,
        station_call_sign=station.call_sign,
        report_date=report_date,
        ranked_plays=ranked,
    )

    csv_bytes = export_certificates_csv(certs)
    filename = f"rmias_pop_{station.call_sign}_{report_date}.csv"
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
