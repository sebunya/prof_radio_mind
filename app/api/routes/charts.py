"""Charts API — ARIA Singles chart ingestion and lookup."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import require_api_key

router = APIRouter(prefix="/charts", tags=["charts"])

# In-memory cache keyed by (chart_name, chart_date) — replace with DB repo in next pass.
_chart_cache: dict[tuple[str, str], list[dict]] = {}


class ChartEntryResponse(BaseModel):
    position: int
    artist: str
    title: str
    previous_position: int | None
    peak_position: int | None
    weeks_on_chart: int | None


class ChartResponse(BaseModel):
    chart_name: str
    chart_date: str
    entry_count: int
    fetched_at: str
    entries: list[ChartEntryResponse]


@router.post(
    "/aria/ingest",
    response_model=ChartResponse,
    dependencies=[Depends(require_api_key)],
)
async def ingest_aria_chart(
    chart_date: date | None = None,
) -> ChartResponse:
    """Fetch and cache the ARIA Singles chart for the given week-ending date.

    If chart_date is omitted, fetches the current week.
    This endpoint makes a live HTTP call to the ARIA website.
    """
    from app.infrastructure.collectors.aria_chart import fetch_aria_chart

    try:
        entries = await fetch_aria_chart(chart_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Failed to fetch ARIA chart: {exc}"
        ) from exc

    target_date = chart_date or entries[0].chart_date if entries else date.today()
    cache_key = ("ARIA Singles", str(target_date))
    _chart_cache[cache_key] = [
        {
            "position": e.position,
            "artist": e.artist,
            "title": e.title,
            "previous_position": e.previous_position,
            "peak_position": e.peak_position,
            "weeks_on_chart": e.weeks_on_chart,
        }
        for e in entries
    ]

    return ChartResponse(
        chart_name="ARIA Singles",
        chart_date=str(target_date),
        entry_count=len(entries),
        fetched_at=datetime.utcnow().isoformat(),
        entries=[
            ChartEntryResponse(
                position=e.position,
                artist=e.artist,
                title=e.title,
                previous_position=e.previous_position,
                peak_position=e.peak_position,
                weeks_on_chart=e.weeks_on_chart,
            )
            for e in entries
        ],
    )


@router.get(
    "/aria/latest",
    response_model=ChartResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_latest_aria_chart() -> ChartResponse:
    """Return the most recently ingested ARIA Singles chart."""
    if not _chart_cache:
        raise HTTPException(
            status_code=404,
            detail="No ARIA chart has been ingested yet. POST /charts/aria/ingest first.",
        )

    latest_key = max(_chart_cache.keys(), key=lambda k: k[1])
    chart_name, chart_date_str = latest_key
    entries_data = _chart_cache[latest_key]

    return ChartResponse(
        chart_name=chart_name,
        chart_date=chart_date_str,
        entry_count=len(entries_data),
        fetched_at=datetime.utcnow().isoformat(),
        entries=[ChartEntryResponse(**e) for e in entries_data],
    )
