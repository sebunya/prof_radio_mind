"""SQLAlchemy persistence for NoTrackEvents."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.no_track_event import NoTrackEvent
from app.infrastructure.database.models.events import NoTrackEventDB


class SQLNoTrackEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, event: NoTrackEvent) -> None:
        self._session.add(
            NoTrackEventDB(
                id=event.id,
                station_id=event.station_id,
                source_id=event.source_id,
                collector_run_id=event.collector_run_id,
                observed_at=event.observed_at,
                reason=event.reason.value,
                raw_http_status=event.raw_http_status,
                notes=event.notes,
            )
        )
        await self._session.flush()
