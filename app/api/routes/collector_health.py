"""Collector health dashboard API — summary stats and paginated run log."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.infrastructure.database.session import get_db

router = APIRouter(prefix="/collector-runs", tags=["collector-health"])


class CollectorRunResponse(BaseModel):
    id: str
    station_id: str
    source_id: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    rows_fetched: int | None
    rows_parsed: int | None
    rows_persisted: int | None
    error_message: str | None
    created_at: datetime


class CollectorSummaryResponse(BaseModel):
    last_completed_at: datetime | None
    last_completed_run_id: str | None
    runs_today: int
    running_count: int
    success_rate_24h: int | None
    last_failed_at: datetime | None
    last_error_message: str | None


def _to_response(row: object) -> CollectorRunResponse:
    return CollectorRunResponse(
        id=str(row.id),
        station_id=str(row.station_id),
        source_id=str(row.source_id),
        status=row.status,
        started_at=row.started_at,
        completed_at=row.completed_at,
        rows_fetched=row.rows_fetched,
        rows_parsed=row.rows_parsed,
        rows_persisted=row.rows_persisted,
        error_message=row.error_message,
        created_at=row.created_at,
    )


# ── GET /collector-runs/summary ───────────────────────────────────────────────
# Declared before /{run_id} so "summary" is never parsed as a UUID.

@router.get(
    "/summary",
    response_model=CollectorSummaryResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_collector_summary(
    session: AsyncSession = Depends(get_db),
) -> CollectorSummaryResponse:
    """Aggregated health stats for the dashboard summary cards."""
    from app.infrastructure.database.repositories.collector_run_repo import (
        SQLCollectorRunRepository,
    )

    repo = SQLCollectorRunRepository(session)
    data = await repo.summary()
    return CollectorSummaryResponse(**data)


# ── GET /collector-runs ───────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[CollectorRunResponse],
    dependencies=[Depends(require_api_key)],
)
async def list_collector_runs(
    response: Response,
    status: str | None = Query(
        None,
        description="Filter by status: scheduled | started | completed | failed",
    ),
    station_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> list[CollectorRunResponse]:
    """Paginated list of collector runs.  Total count in ``X-Total-Count`` header."""
    from app.infrastructure.database.repositories.collector_run_repo import (
        SQLCollectorRunRepository,
    )

    repo = SQLCollectorRunRepository(session)
    items, total = await repo.list_page(
        status=status, station_id=station_id, limit=limit, offset=offset
    )
    response.headers["X-Total-Count"] = str(total)
    return [_to_response(r) for r in items]


# ── GET /collector-runs/{run_id} ──────────────────────────────────────────────

@router.get(
    "/{run_id}",
    response_model=CollectorRunResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_collector_run(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> CollectorRunResponse:
    """Fetch a single collector run by ID."""
    from app.infrastructure.database.models.collector_runs import CollectorRun

    row = await session.get(CollectorRun, run_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"Collector run {run_id} not found"
        )
    return _to_response(row)
