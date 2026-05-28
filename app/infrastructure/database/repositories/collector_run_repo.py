"""SQLAlchemy implementation of CollectorRunRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.collector_run import CollectorRun as RunEntity
from app.domain.entities.collector_run import CollectorStatus
from app.domain.ports.collector_run_repository import CollectorRunRepository
from app.infrastructure.database.models.collector_runs import CollectorRun as RunModel
from app.infrastructure.database.pagination import paginate


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

    # ── Health dashboard helpers ──────────────────────────────────────────────

    async def list_page(
        self,
        *,
        status: str | None = None,
        station_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[RunModel], int]:
        """Return (model_rows, total_count) for the health dashboard."""
        stmt = select(RunModel).order_by(RunModel.created_at.desc())
        if status:
            stmt = stmt.where(RunModel.status == status)
        if station_id:
            stmt = stmt.where(RunModel.station_id == station_id)
        return await paginate(self._session, stmt, limit=limit, offset=offset)

    async def summary(self) -> dict:
        """Aggregated stats for the health-dashboard summary cards."""
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        since_24h = now - timedelta(hours=24)

        last_ok = (
            await self._session.execute(
                select(RunModel)
                .where(RunModel.status == "completed")
                .order_by(RunModel.completed_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        last_fail = (
            await self._session.execute(
                select(RunModel)
                .where(RunModel.status == "failed")
                .order_by(RunModel.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        runs_today: int = (
            await self._session.execute(
                select(func.count())
                .select_from(RunModel)
                .where(RunModel.created_at >= today_start)
            )
        ).scalar_one()

        running_count: int = (
            await self._session.execute(
                select(func.count())
                .select_from(RunModel)
                .where(RunModel.status.in_(["started", "scheduled"]))
            )
        ).scalar_one()

        agg_24h = (
            await self._session.execute(
                select(
                    func.count().label("total"),
                    func.count(case((RunModel.status == "completed", 1))).label("ok"),
                )
                .select_from(RunModel)
                .where(RunModel.created_at >= since_24h)
            )
        ).one()
        success_rate: int | None = (
            round(agg_24h.ok / agg_24h.total * 100) if agg_24h.total else None
        )

        return {
            "last_completed_at": last_ok.completed_at if last_ok else None,
            "last_completed_run_id": str(last_ok.id) if last_ok else None,
            "runs_today": runs_today,
            "running_count": running_count,
            "success_rate_24h": success_rate,
            "last_failed_at": last_fail.created_at if last_fail else None,
            "last_error_message": last_fail.error_message if last_fail else None,
        }
