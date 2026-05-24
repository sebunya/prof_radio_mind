from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.play_event import PlayEvent


class PlayEventRepository(ABC):
    @abstractmethod
    async def save(self, event: PlayEvent) -> None: ...

    @abstractmethod
    async def exists_by_source_event_id(
        self, station_id: uuid.UUID, source_event_id: str
    ) -> bool: ...

    @abstractmethod
    async def exists_by_fingerprint(
        self, station_id: uuid.UUID, fingerprint: str, within_seconds: int = 300
    ) -> bool: ...

    @abstractmethod
    async def list_for_station(
        self,
        station_id: uuid.UUID,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[PlayEvent]: ...
