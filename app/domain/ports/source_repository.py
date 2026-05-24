from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.domain.entities.source import Source


class SourceRepository(ABC):
    @abstractmethod
    async def get_by_id(self, source_id: uuid.UUID) -> Source | None: ...

    @abstractmethod
    async def list_active_for_station(self, station_id: uuid.UUID) -> list[Source]: ...

    @abstractmethod
    async def save(self, source: Source) -> None: ...
