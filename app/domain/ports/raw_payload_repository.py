from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.value_objects.raw_payload import RawPayload


class RawPayloadRepository(ABC):
    @abstractmethod
    async def save(self, payload: RawPayload) -> None: ...

    @abstractmethod
    async def exists_by_sha256(self, sha256: str) -> bool: ...
