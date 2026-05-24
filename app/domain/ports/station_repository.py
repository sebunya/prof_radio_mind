from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.domain.entities.station import Station


class StationRepository(ABC):
    @abstractmethod
    async def get_by_id(self, station_id: uuid.UUID) -> Station | None: ...

    @abstractmethod
    async def get_by_call_sign(self, call_sign: str) -> Station | None: ...

    @abstractmethod
    async def list_active(self) -> list[Station]: ...

    @abstractmethod
    async def save(self, station: Station) -> None: ...
