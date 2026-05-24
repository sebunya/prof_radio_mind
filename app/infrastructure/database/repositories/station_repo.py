"""SQLAlchemy implementation of StationRepository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.station import Station as StationEntity
from app.domain.ports.station_repository import StationRepository
from app.infrastructure.database.models.stations import Station as StationModel


def _to_domain(row: StationModel) -> StationEntity:
    return StationEntity(
        id=row.id,
        name=row.name,
        call_sign=row.call_sign,
        frequency=row.frequency,
        city=row.city,
        country_code=row.country_code,
        is_active=row.is_active,
    )


class SQLStationRepository(StationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, station_id: uuid.UUID) -> StationEntity | None:
        row = await self._session.get(StationModel, station_id)
        return _to_domain(row) if row else None

    async def get_by_call_sign(self, call_sign: str) -> StationEntity | None:
        stmt = select(StationModel).where(StationModel.call_sign == call_sign)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_active(self) -> list[StationEntity]:
        stmt = select(StationModel).where(StationModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return [_to_domain(r) for r in result.scalars().all()]

    async def save(self, station: StationEntity) -> None:
        existing = await self._session.get(StationModel, station.id)
        if existing:
            existing.name = station.name
            existing.call_sign = station.call_sign
            existing.frequency = station.frequency
            existing.city = station.city
            existing.country_code = station.country_code
            existing.is_active = station.is_active
        else:
            self._session.add(
                StationModel(
                    id=station.id,
                    name=station.name,
                    call_sign=station.call_sign,
                    frequency=station.frequency,
                    city=station.city,
                    country_code=station.country_code,
                    is_active=station.is_active,
                )
            )
        await self._session.flush()
