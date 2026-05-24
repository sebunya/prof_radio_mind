"""SQLAlchemy implementation of CollectorRunRepository."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.collector_run import CollectorRun as RunEntity
from app.domain.entities.collector_run import CollectorStatus
from app.domain.ports.collector_run_repository import CollectorRunRepository
from app.infrastructure.database.models.collector_runs import CollectorRun as RunModel


def _to_domain(row: RunModel) -> RunEntity:
    return RunEntity(
        id=row.id,
        source_id=row.source_id,
        station_id=row.station_id,
        status=CollectorStatus(row.status),
        started_at=row.started_at,
        completed_at=row.completed_at,
        rows_fetched=row.rows_fetched,
        rows_parsed=row.rows_parsed,
        rows_persisted=row.rows_persisted,
        error_message=row.error_message,
        meta=row.meta,
    )


class SQLCollectorRunRepository(CollectorRunRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, run_id: uuid.UUID) -> RunEntity | None:
        row = await self._session.get(RunModel, run_id)
        return _to_domain(row) if row else None

    async def save(self, run: RunEntity) -> None:
        self._session.add(
            RunModel(
                id=run.id,
                source_id=run.source_id,
                station_id=run.station_id,
                status=run.status.value,
                started_at=run.started_at,
                completed_at=run.completed_at,
                rows_fetched=run.rows_fetched,
                rows_parsed=run.rows_parsed,
                rows_persisted=run.rows_persisted,
                error_message=run.error_message,
                meta=run.meta,
            )
        )
        await self._session.flush()

    async def update_status(self, run: RunEntity) -> None:
        row = await self._session.get(RunModel, run.id)
        if row:
            row.status = run.status.value
            row.completed_at = run.completed_at
            row.rows_fetched = run.rows_fetched
            row.rows_parsed = run.rows_parsed
            row.rows_persisted = run.rows_persisted
            row.error_message = run.error_message
            row.meta = run.meta
            await self._session.flush()
