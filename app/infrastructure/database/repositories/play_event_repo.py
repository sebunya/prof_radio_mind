"""SQLAlchemy implementation of PlayEventRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.play_event import PlayEvent
from app.domain.ports.play_event_repository import PlayEventRepository
from app.infrastructure.database.models.events import PlayEventDB


def _to_domain(row: PlayEventDB) -> PlayEvent:
    return PlayEvent(
        id=row.id,
        station_id=row.station_id,
        source_id=row.source_id,
        collector_run_id=row.collector_run_id,
        played_at=row.played_at,
        raw_artist=row.raw_artist,
        raw_title=row.raw_title,
        raw_label=row.raw_label,
        source_event_id=row.source_event_id,
        fingerprint=row.fingerprint,
    )


class SQLPlayEventRepository(PlayEventRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, event: PlayEvent) -> None:
        self._session.add(
            PlayEventDB(
                id=event.id,
                station_id=event.station_id,
                source_id=event.source_id,
                collector_run_id=event.collector_run_id,
                raw_artist=event.raw_artist,
                raw_title=event.raw_title,
                raw_label=event.raw_label,
                played_at=event.played_at,
                source_event_id=event.source_event_id,
                fingerprint=event.fingerprint,
            )
        )
        await self._session.flush()

    async def exists_by_source_event_id(
        self, station_id: uuid.UUID, source_event_id: str
    ) -> bool:
        stmt = (
            select(PlayEventDB.id)
            .where(
                PlayEventDB.station_id == station_id,
                PlayEventDB.source_event_id == source_event_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar() is not None

    async def exists_by_fingerprint(
        self,
        station_id: uuid.UUID,
        fingerprint: str,
        within_seconds: int = 300,
    ) -> bool:
        cutoff = datetime.now(UTC) - timedelta(seconds=within_seconds)
        stmt = (
            select(PlayEventDB.id)
            .where(
                PlayEventDB.station_id == station_id,
                PlayEventDB.fingerprint == fingerprint,
                PlayEventDB.played_at >= cutoff,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar() is not None

    async def list_for_station(
        self,
        station_id: uuid.UUID,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[PlayEvent]:
        stmt = (
            select(PlayEventDB)
            .where(
                PlayEventDB.station_id == station_id,
                PlayEventDB.played_at >= from_dt,
                PlayEventDB.played_at < to_dt,
                PlayEventDB.is_duplicate.is_(False),
            )
            .order_by(PlayEventDB.played_at)
        )
        result = await self._session.execute(stmt)
        return [_to_domain(r) for r in result.scalars().all()]
