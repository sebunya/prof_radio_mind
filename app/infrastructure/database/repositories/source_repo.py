"""SQLAlchemy implementation of SourceRepository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.source import Source as SourceEntity
from app.domain.entities.source import SourceType
from app.domain.ports.source_repository import SourceRepository
from app.infrastructure.database.models.sources import Source as SourceModel


def _to_domain(row: SourceModel) -> SourceEntity:
    return SourceEntity(
        id=row.id,
        station_id=row.station_id,
        source_type=SourceType(row.source_type),
        name=row.name,
        base_url=row.base_url,
        config=row.config,
        is_active=row.is_active,
    )


class SQLSourceRepository(SourceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, source_id: uuid.UUID) -> SourceEntity | None:
        row = await self._session.get(SourceModel, source_id)
        return _to_domain(row) if row else None

    async def list_active_for_station(self, station_id: uuid.UUID) -> list[SourceEntity]:
        stmt = (
            select(SourceModel)
            .where(SourceModel.station_id == station_id, SourceModel.is_active.is_(True))
            .order_by(SourceModel.id)
        )
        result = await self._session.execute(stmt)
        return [_to_domain(r) for r in result.scalars().all()]

    async def save(self, source: SourceEntity) -> None:
        existing = await self._session.get(SourceModel, source.id)
        if existing:
            existing.name = source.name
            existing.base_url = source.base_url
            existing.config = source.config
            existing.is_active = source.is_active
        else:
            self._session.add(
                SourceModel(
                    id=source.id,
                    station_id=source.station_id,
                    source_type=source.source_type.value,
                    name=source.name,
                    base_url=source.base_url,
                    config=source.config,
                    is_active=source.is_active,
                )
            )
        await self._session.flush()
