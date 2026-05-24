from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.domain.entities.collector_run import CollectorRun


class CollectorRunRepository(ABC):
    @abstractmethod
    async def get_by_id(self, run_id: uuid.UUID) -> CollectorRun | None: ...

    @abstractmethod
    async def save(self, run: CollectorRun) -> None: ...

    @abstractmethod
    async def update_status(self, run: CollectorRun) -> None: ...
